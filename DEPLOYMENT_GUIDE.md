# DetectifAI Deployment Guide (Free Tier Only)

> **Bottom line up front:** You can deploy the **frontend on Vercel (free)** and the **backend on Render (free)**. But the ML-heavy backend has hard limits on free tiers. This guide covers everything honestly — what works, what doesn't, and workarounds.

---

## Architecture Overview

```
┌─────────────┐       ┌──────────────┐       ┌───────────────┐
│   Frontend   │──────▶│   Backend    │──────▶│   Services    │
│  (Next.js)   │  API  │  (Flask)     │       │               │
│  Vercel Free │       │  Render Free │       │ MongoDB Atlas  │
└─────────────┘       │              │       │ (Free 512MB)   │
                      │  ML Models   │       │               │
                      │  ~305MB .pt  │       │ MinIO → must   │
                      │  +2GB runtime│       │ be replaced    │
                      └──────────────┘       └───────────────┘
```

---

## Component Inventory & Size Analysis

| Component | What it is | Size / RAM needed |
|---|---|---|
| **YOLO Models** (fire, weapon, wallclimb) | `.pt` files for object detection | ~26 MB on disk |
| **3D ResNet Models** (fight, accident) | Action recognition | ~253 MB on disk |
| **SVM Classifier + FAISS** | Face recognition index | ~21 MB on disk |
| **BLIP** (captioning) | `Salesforce/blip-image-captioning-base` — downloaded at runtime | ~1 GB download, ~1.5 GB RAM |
| **Sentence Transformers** | `all-mpnet-base-v2` + `all-MiniLM-L6-v2` — runtime | ~400 MB download, ~500 MB RAM |
| **FaceNet** (InceptionResnetV1) + MTCNN | Face detection & embedding — runtime | ~200 MB download, ~400 MB RAM |
| **LLM for Reports** | Qwen2.5-3B GGUF (~2 GB) — runtime download | ~2 GB download, ~3 GB RAM |
| **PyTorch + Ultralytics** | Core ML framework | ~800 MB installed |

### Total Backend RAM Needed: **~4-6 GB minimum** (all models loaded)

---

## The Hard Truth About Free Tiers

| Platform | Free Limit | Enough? |
|---|---|---|
| **Vercel** (Frontend) | Unlimited deploys, 100GB bandwidth | ✅ Perfect for Next.js |
| **Render** (Backend) | 512 MB RAM, spins down after 15 min idle | ❌ Not enough for all ML models |
| **Railway** | $5 free credit (no card), 512 MB RAM | ❌ Same RAM problem |
| **Fly.io** | 256 MB free VMs | ❌ Way too small |
| **Hugging Face Spaces** | Free CPU, 16 GB RAM, 2 vCPU | ✅ **Best option for ML backend** |
| **MongoDB Atlas** | 512 MB free (M0 cluster) | ✅ You already use this |
| **MinIO** | Self-hosted only — needs a server | ❌ Must be replaced |

### Recommended Stack (All Free, No Card)

| Layer | Platform | Card Required? |
|---|---|---|
| Frontend | **Vercel** | ❌ No card |
| Backend API | **Render** (lightweight routes) OR **Hugging Face Spaces** | ❌ No card |
| ML Processing | **Hugging Face Spaces** (Gradio/Docker) | ❌ No card |
| Database | **MongoDB Atlas** (already set up) | ❌ No card |
| Object Storage | **Cloudflare R2** (10 GB free) or **Supabase Storage** (1 GB free) | ❌ No card |

---

## Strategy: Split the Backend

Your Flask backend does two things:
1. **API routes** — auth, CRUD, search, serve results (lightweight)
2. **ML processing** — object detection, action recognition, captioning (heavy)

**Split approach:**
- Deploy API-only backend on **Render Free** (strip out ML imports, just serve data)
- Deploy ML processing on **Hugging Face Spaces** (has 16 GB RAM for free)
- Frontend calls Render for data, Render calls HF Space for processing

**OR simpler approach:**
- Deploy **everything** (API + ML) on a single **Hugging Face Space** with Docker
- Frontend on Vercel points to the HF Space URL

---

## Step-by-Step Deployment

### 1. Frontend → Vercel

**What:** Next.js 14 app with NextAuth, Stripe, Tailwind

**Steps:**
1. Go to [vercel.com](https://vercel.com) → Sign up with GitHub (no card)
2. Push your `frontend/` folder to a GitHub repo (or the whole project, set root directory)
3. Import repo on Vercel → Set **Root Directory** to `frontend`
4. Add **Environment Variables** on Vercel dashboard:

```env
MONGO_URI=mongodb+srv://detectifai_user:DetectifAI123@cluster0.6f9uj.mongodb.net/detectifai?retryWrites=true&w=majority&appName=Cluster0
GOOGLE_CLIENT_ID=941537919957-49r5roa8vlfdnf2gl722c93cuda8scl3.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
NEXTAUTH_SECRET=tx7CZwEL2Hhg0OynqYPTJV3SkBrWwoIEQYPM1J+jAMY=
NEXTAUTH_URL=https://your-app.vercel.app
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_51SsbwWBC7V4mGo7r...
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
```

5. Click **Deploy**

**Important changes needed:**
- Update `NEXTAUTH_URL` to your Vercel URL after first deploy  
- Update `NEXT_PUBLIC_API_URL` to wherever backend is deployed
- Update Google OAuth redirect URIs in Google Console to include Vercel URL

---

### 2. Replace MinIO with Cloud Storage

MinIO is local-only. You need a cloud replacement. **Best free options:**

#### Option A: Cloudflare R2 (10 GB free, no card, S3-compatible)
- Sign up at [dash.cloudflare.com](https://dash.cloudflare.com) — free, no card
- Create R2 bucket → get API keys
- **MinIO SDK is S3-compatible** so you just change the endpoint:

```python
# In backend/database/config.py — change MinIO config to:
self.minio_endpoint = "your-account-id.r2.cloudflarestorage.com"
self.minio_access_key = "your-r2-access-key"
self.minio_secret_key = "your-r2-secret-key"
self.minio_secure = True  # R2 uses HTTPS
```

#### Option B: Supabase Storage (1 GB free, no card)
- Would need more code changes — not recommended since R2 is S3-compatible

---

### 3. Backend → Hugging Face Spaces (Recommended for ML)

**Why HF Spaces:** 16 GB RAM free (CPU), supports Docker, no card needed.

**Steps:**

1. Go to [huggingface.co](https://huggingface.co) → Create account (free, no card)
2. Create new Space → Select **Docker** SDK → **CPU Basic (Free)**
3. Create a `Dockerfile` in your backend folder:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for OpenCV, WeasyPrint
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy model files
COPY models/ models/
COPY behavior_analysis/*.pt behavior_analysis/
COPY model/ /app/model/

# Expose port (HF Spaces expects 7860)
EXPOSE 7860

# Run Flask on port 7860
CMD ["python", "-c", "from app import app; app.run(host='0.0.0.0', port=7860)"]
```

4. Add a `README.md` at the Space root:

```yaml
---
title: DetectifAI Backend
emoji: 🔍
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
---
```

5. Push code + model files to the HF Space repo
6. Set env variables in HF Space Settings:

```
MONGO_URI=mongodb+srv://detectifai_user:...
MINIO_ENDPOINT=your-r2-endpoint
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_SECURE=true
JWT_SECRET=your-jwt-secret
STRIPE_SECRET_KEY=sk_test_...
```

7. Your backend URL becomes: `https://your-username-detectifai-backend.hf.space`

---

### 4. Alternative: Backend → Render (lighter deployment)

If you want to use Render but can't fit ML models in 512 MB:

**Option: Disable heavy ML features for demo**

Create a `render_config.py` that disables heavy models:

```python
# Disable features that need too much RAM
ENABLE_VIDEO_CAPTIONING = False  # Saves ~1.5 GB
ENABLE_BEHAVIOR_ANALYSIS = False  # Saves ~500 MB
ENABLE_REPORT_LLM = False  # Saves ~3 GB
ENABLE_FACIAL_RECOGNITION = False  # Saves ~400 MB
# Keep: Object detection (~200 MB), API routes, search
```

**Render steps:**
1. Go to [render.com](https://render.com) → Sign up with GitHub (no card)
2. New → Web Service → Connect repo
3. **Root Directory:** `backend`
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `python -c "from app import app; app.run(host='0.0.0.0', port=10000)"`
6. Set environment variables
7. Deploy

> ⚠️ Render free tier spins down after 15 min idle. First request after sleep takes ~30-60 seconds.

---

### 5. Database — MongoDB Atlas

**Already configured.** Your `.env` points to Atlas. Just make sure:
- Whitelist `0.0.0.0/0` in Atlas Network Access (allows all IPs — needed for Render/HF)
- Free M0 cluster = 512 MB. Should be fine for a demo.

---

## Changes Required Before Deployment

### Backend Code Changes

1. **Replace hardcoded `localhost` references:**
   - `MINIO_ENDPOINT` → cloud storage URL
   - `BACKEND_URL` → deployed URL
   - `FRONTEND_URL` → Vercel URL

2. **Make MinIO endpoint configurable:**
   Your code already reads from env vars — just update `.env` for production.

3. **Add CORS for Vercel domain:**
```python
# In app.py, update CORS:
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "https://your-app.vercel.app"
]}})
```

4. **Port configuration:**
```python
# HF Spaces needs port 7860, Render needs port from $PORT env
port = int(os.environ.get("PORT", 7860))
app.run(host="0.0.0.0", port=port)
```

### Frontend Code Changes

1. **Update API URL to env variable:**
   - All axios/fetch calls should use `process.env.NEXT_PUBLIC_API_URL`
   - You likely already do this — verify in `frontend/lib/` or `frontend/app/api/`

2. **Update NextAuth config:**
   - `NEXTAUTH_URL` must match your Vercel deployment URL

3. **Update Google OAuth:**
   - Add Vercel URL to authorized redirect URIs in Google Cloud Console

---

## Git Setup for Deployment

### Recommended Repo Structure

```
your-repo/
├── frontend/          ← Vercel deploys this
├── backend/           ← HF Space or Render deploys this
│   ├── Dockerfile     ← For HF Spaces
│   ├── requirements.txt
│   ├── models/        ← YOLO models (~31 MB)
│   ├── behavior_analysis/  ← ResNet models (~263 MB)
│   └── model/         ← FAISS index + SVM (~21 MB)
└── README.md
```

### Handle Large Model Files

Git has a 100 MB file limit. Your `accident_detection.pt` and `fight_detection.pt` are 126 MB each.

**Option A: Git LFS**
```bash
git lfs install
git lfs track "*.pt"
git lfs track "*.pkl"
git add .gitattributes
```
> GitHub free = 1 GB LFS storage. Enough for your models.

**Option B: Download models at startup (HF Spaces)**
Upload models to a HuggingFace model repo separately and download in Dockerfile:
```dockerfile
RUN pip install huggingface_hub
RUN python -c "from huggingface_hub import hf_hub_download; hf_hub_download('your-username/detectifai-models', 'fight_detection.pt', local_dir='behavior_analysis/')"
```

---

## Runtime Model Downloads (Important!)

These models get downloaded **automatically** at first startup:

| Model | Downloaded From | Size | When |
|---|---|---|---|
| `Salesforce/blip-image-captioning-base` | HuggingFace | ~1 GB | First captioning call |
| `sentence-transformers/all-mpnet-base-v2` | HuggingFace | ~420 MB | First search/event |
| `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace | ~80 MB | First captioning embed |
| `InceptionResnetV1 (vggface2)` | PyTorch Hub | ~200 MB | First face detection |
| `MTCNN` weights | facenet-pytorch | ~5 MB | First face detection |
| `Qwen2.5-3B GGUF` (report LLM) | HuggingFace | ~2 GB | First report generation |

**Total runtime downloads: ~3.7 GB**

On HF Spaces this is fine (persistent storage). On Render free, these re-download on every cold start (slow).

---

## Recommended Deployment Plan

### Phase 1: Get it online (Day 1)

1. ✅ Push code to GitHub
2. ✅ Deploy frontend on Vercel
3. ✅ Deploy backend on HF Spaces (Docker)
4. ✅ Sign up for Cloudflare R2, replace MinIO
5. ✅ Update env vars everywhere
6. ✅ Test basic flow: signup → upload → view results

### Phase 2: Optimize (Day 2-3)

1. Pre-download all runtime models in Dockerfile
2. Add health check endpoint
3. Test all features end-to-end
4. Handle CORS issues

### Phase 3: Demo prep

1. Pre-process a few videos so results are cached in MongoDB
2. Pre-populate face index so search works
3. Test on slow internet (HF Spaces can be slow on free CPU)

---

## Known Limitations on Free Tier

| Limitation | Impact | Workaround |
|---|---|---|
| **HF Spaces CPU is slow** | Video processing takes 5-10x longer | Pre-process demo videos locally, upload results to MongoDB |
| **No GPU** | PyTorch runs on CPU | Already configured for CPU fallback |
| **No live RTSP streaming** | Live monitoring won't work on serverless | Demo with webcam locally or disable live module |
| **Render cold starts** | 30-60s first request | Use HF Spaces instead |
| **512 MB MongoDB** | ~500K events max | Fine for demo |
| **R2 10 GB storage** | ~20 videos with keyframes | Fine for demo |
| **No persistent disk on Render** | Models re-download | Use HF Spaces (has persistent /data) |

---

## Environment Variables Checklist

### Frontend (Vercel)
```
MONGO_URI=<Atlas connection string>
GOOGLE_CLIENT_ID=<Google OAuth ID>
GOOGLE_CLIENT_SECRET=<Google OAuth secret>
NEXTAUTH_SECRET=<random secret>
NEXTAUTH_URL=https://detectifai.vercel.app
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_API_URL=https://your-backend.hf.space
```

### Backend (HF Spaces or Render)
```
MONGO_URI=<Atlas connection string>
MINIO_ENDPOINT=<R2 or Supabase endpoint>
MINIO_ACCESS_KEY=<storage key>
MINIO_SECRET_KEY=<storage secret>
MINIO_SECURE=true
JWT_SECRET=<shared secret>
STRIPE_SECRET_KEY=sk_test_...
FLASK_ENV=production
FRONTEND_URL=https://detectifai.vercel.app
PORT=7860
```

---

## Quick Reference Commands

```bash
# Push frontend to GitHub (Vercel auto-deploys)
cd frontend && git add . && git commit -m "deploy" && git push

# Build frontend locally to test
cd frontend && npm run build

# Test backend locally before deploying
cd backend && python app.py

# Check model sizes
du -sh backend/models/ backend/behavior_analysis/*.pt model/
```

---

## TL;DR Decision

| If you want... | Do this |
|---|---|
| **Easiest path** | Frontend → Vercel, Backend → HF Spaces (Docker), Storage → Cloudflare R2 |
| **Supervisor said Vercel** | Frontend on Vercel. Backend can't go on Vercel (it's Python/Flask). |
| **Everything free, no card** | Vercel + HF Spaces + MongoDB Atlas + Cloudflare R2 = all free, no card |
| **Quick demo** | Pre-process videos locally, push results to MongoDB, deploy lightweight API on Render |

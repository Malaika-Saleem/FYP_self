# Storage and Fetching Verification

## ✅ **CONFIRMED: All Files Are Stored in MinIO and Fetched Correctly**

### 1. **Original Video Files** ✅

**Storage:**
- **Location**: MinIO bucket `detectifai-videos`
- **Path**: `original/{video_id}/video.mp4`
- **When**: Uploaded immediately after MongoDB record creation
- **MongoDB Link**: Stored in `minio_object_key` and `meta_data.minio_original_path`

**Fetching:**
- **Endpoint**: `/api/video/compressed/{video_id}` (for compressed, original can be accessed via presigned URL)
- **Method**: Presigned URLs generated from MinIO
- **Status**: ✅ Working

---

### 2. **Compressed Video Files** ✅

**Storage:**
- **Location**: MinIO bucket `detectifai-videos`  
- **Path**: `compressed/{video_id}/video.mp4`
- **When**: Generated and uploaded after processing completes
- **MongoDB Link**: Stored in `meta_data.minio_compressed_path`

**Fetching:**
- **Endpoint**: `/api/video/compressed/{video_id}` or `/api/v2/video/compressed/{video_id}`
- **Method**: 
  1. First tries MinIO (gets from `meta_data.minio_compressed_path`)
  2. Falls back to local filesystem if MinIO unavailable
- **Status**: ✅ Working with MinIO-first approach

---

### 3. **Keyframes (ALL Keyframes)** ✅

**Storage:**
- **Location**: MinIO bucket `detectifai-keyframes`
- **Path**: `{video_id}/keyframes/frame_{frame_number:06d}.jpg`
- **When**: Extracted and uploaded during processing (Step 1)
- **MongoDB Link**: 
  - Full metadata in `meta_data.keyframe_info[]` (includes MinIO paths)
  - Quick access list in `meta_data.keyframes_minio_paths[]`
  - Count in `meta_data.keyframe_count`

**Important Note**: 
- **ALL keyframes are uploaded to MinIO** (not just those with detections)
- Filtering by detections happens when **fetching**, not when storing
- This allows flexibility to show all frames or only frames with detections

**Fetching:**
- **Endpoint**: `/api/v2/video/keyframes/{video_id}?filter_detections=true`
- **Method**: 
  1. Gets presigned URLs from MinIO for all keyframes
  2. Enhances with detection info from events
  3. Filters to show only frames with detections if `filter_detections=true`
- **Individual Keyframe**: `/api/video/{video_id}/keyframe/{filename}` or `/api/v2/video/keyframe/{video_id}/{filename}`
  - First tries MinIO
  - Falls back to local filesystem
- **Status**: ✅ Working with presigned URLs

---

## 📊 **Complete Data Flow**

```
1. Video Upload
   ↓
2. MongoDB Record Created (with metadata)
   ↓
3. Original Video → MinIO (original/{video_id}/video.mp4)
   ↓
4. MongoDB Updated with MinIO Path
   ↓
5. Keyframes Extracted
   ↓
6. ALL Keyframes → MinIO (keyframes/{video_id}/frame_*.jpg)
   ↓
7. MongoDB Updated with Keyframe MinIO Paths
   ↓
8. Object Detection (on keyframes)
   ↓
9. Events Created → MongoDB
   ↓
10. Facial Recognition (on frames with detections)
    ↓
11. Faces → MinIO + MongoDB
    ↓
12. Compressed Video Generated
    ↓
13. Compressed Video → MinIO (compressed/{video_id}/video.mp4)
    ↓
14. MongoDB Updated with Compressed Video Path
    ↓
15. Frontend Fetches:
    - Status (includes all MinIO paths)
    - Results (comprehensive data)
    - Keyframes (with presigned URLs from MinIO)
    - Faces (with MinIO paths)
    - Compressed Video (served from MinIO)
```

---

## ✅ **Verification Checklist**

- [x] Original videos stored in MinIO
- [x] Original video paths linked in MongoDB
- [x] Compressed videos stored in MinIO
- [x] Compressed video paths linked in MongoDB
- [x] ALL keyframes stored in MinIO
- [x] Keyframe paths linked in MongoDB
- [x] Presigned URLs generated for keyframes
- [x] Frontend fetches compressed video from MinIO
- [x] Frontend fetches keyframes with presigned URLs
- [x] Fallback mechanisms for local storage
- [x] All endpoints serve from MinIO first

---

## 🎯 **Summary**

**YES, everything is properly stored and fetched:**

1. ✅ **Original Videos** → MinIO + MongoDB linked
2. ✅ **Compressed Videos** → MinIO + MongoDB linked  
3. ✅ **ALL Keyframes** → MinIO + MongoDB linked (filtering happens on fetch)

All files are stored in MinIO with their paths properly linked in MongoDB metadata, and the frontend correctly fetches everything using presigned URLs or proxy endpoints.

"""nlp_search/query_retreival.py

Command-line utility to run a natural-language query against stored
captions in MongoDB and return the top-K matching keyframes/captions.

Behavior:
 - Connects to MongoDB (MONGO_URI via env)
 - Loads the SentenceTransformer model to encode the query
 - Loads caption embeddings from the `event_descriptions` collection
   (documents should include `description_id`, `caption`, `text_embedding`,
    `event_id`, and `video_reference`)
 - Computes cosine similarity between query embedding and stored embeddings
 - Returns top-K matches with: caption, similarity_score (0..1),
   event_id (if present), video reference, and timestamps (from `events` collection
   if an event with matching event_id exists)

Usage:
  python query_retreival.py --query "fire in building" --top_k 5

"""
#python query_retreival.py -q "dog sitting on grass" -k 3 --json
import os
import argparse
import json
from dotenv import load_dotenv
from pymongo import MongoClient
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise ImportError("Please install sentence-transformers: pip install sentence-transformers")


load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/detectifai")


def connect_db():
    client = MongoClient(MONGO_URI)
    db = client.get_default_database()
    return db


def load_caption_embeddings(db):
    """Load captions and embeddings from `event_descriptions`.

    Returns:
      docs: list of dicts with keys: description_id, caption, event_id, video_reference
      emb_matrix: np.ndarray shape (N, D) of float32 (normalized)
    """
    coll = db.get_collection("event_descriptions")
    cursor = coll.find({"text_embedding": {"$exists": True, "$ne": []}}, {
        "_id": 0,
        "description_id": 1,
        "caption": 1,
        "event_id": 1,
        "text_embedding": 1,
        "video_reference": 1
    })

    docs = []
    embeddings = []
    for doc in cursor:
        emb = doc.get("text_embedding")
        if not emb:
            continue
        try:
            arr = np.asarray(emb, dtype="float32")
            # Ensure normalized (safe to renormalize)
            norm = np.linalg.norm(arr)
            if norm == 0:
                continue
            arr = arr / norm
            embeddings.append(arr)
            docs.append({
                "description_id": doc.get("description_id"),
                "caption": doc.get("caption"),
                "event_id": doc.get("event_id"),
                "video_reference": doc.get("video_reference")
            })
        except Exception:
            continue

    if embeddings:
        emb_matrix = np.stack(embeddings, axis=0).astype("float32")
    else:
        emb_matrix = np.zeros((0, 0), dtype="float32")

    return docs, emb_matrix


def compute_similarities(q_emb, emb_matrix):
    """Compute cosine similarities between q_emb (D,) and emb_matrix (N, D)."""
    if emb_matrix.size == 0:
        return np.array([])
    # ensure normalized
    q = q_emb / (np.linalg.norm(q_emb) + 1e-12)
    sims = np.dot(emb_matrix, q.astype("float32"))
    return sims


def retrieve_top_k(db, query_text, top_k=5):
    model = SentenceTransformer("all-mpnet-base-v2")
    q_emb = model.encode(query_text, normalize_embeddings=True).astype("float32")

    docs, emb_matrix = load_caption_embeddings(db)

    if emb_matrix.size == 0:
        print("No caption embeddings found in database. Run upload_captions.py first.")
        return []

    sims = compute_similarities(q_emb, emb_matrix)

    # Get top_k indices
    idxs = np.argsort(-sims)[:top_k]

    results = []
    events_coll = db.get_collection("events")

    for idx in idxs:
        score = float(sims[idx])
        doc = docs[idx]
        # Attempt to fetch timestamps from events collection
        start_ts = None
        end_ts = None
        video_id = None
        if doc.get("event_id"):
            ev = events_coll.find_one({"event_id": doc.get("event_id")}, {"_id": 0, "start_timestamp_ms": 1, "end_timestamp_ms": 1, "video_id": 1})
            if ev:
                start_ts = ev.get("start_timestamp_ms")
                end_ts = ev.get("end_timestamp_ms")
                video_id = ev.get("video_id")

        result = {
            "description_id": doc.get("description_id"),
            "caption": doc.get("caption"),
            "event_id": doc.get("event_id"),
            "video_reference": doc.get("video_reference"),
            "video_id": video_id,
            "start_timestamp_ms": start_ts,
            "end_timestamp_ms": end_ts,
            "similarity": score
        }
        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Query NLP captions and retrieve matching keyframes/events from DB")
    parser.add_argument("--query", "-q", required=True, help="Query text")
    parser.add_argument("--top_k", "-k", type=int, default=5, help="Number of top results to return")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    args = parser.parse_args()

    db = connect_db()
    results = retrieve_top_k(db, args.query, top_k=args.top_k)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"Query: {args.query}\nTop {len(results)} matches:")
        for i, r in enumerate(results, 1):
            sim = r.get("similarity", 0.0)
            start = r.get("start_timestamp_ms")
            end = r.get("end_timestamp_ms")
            vidref = r.get("video_reference") or {}
            video_obj = vidref.get("object_name") if isinstance(vidref, dict) else None
            print(f"[{i}] Score: {sim:.4f} | Caption: {r.get('caption')} | Video Obj: {video_obj} | start_ms: {start} | end_ms: {end}")


if __name__ == "__main__":
    main()

"""
Upload Captions to MongoDB

This script uploads 10 hardcoded captions linked to videos stored in the
MinIO 'nlp-images' bucket. The captions are inserted into the MongoDB
'event_descriptions' collection.

Usage:
    python upload_captions.py
"""

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from minio import Minio
import logging
import numpy as np
import json

# Optional imports for embeddings and FAISS
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    SENTER_AVAILABLE = True
except Exception:
    SENTER_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/detectifai")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "adminpassword")

# MinIO bucket for NLP images/videos
NLP_IMAGES_BUCKET = "nlp-images"

# Hardcoded captions with video references
HARDCODED_CAPTIONS = [
    {
        "video_filename": "img1.webp",
        "caption": "Forty story building reported to be on fire with smoke visible from several floors",
        "confidence": 0.95
    },
    {
        "video_filename": "img2.jpg",
        "caption": "Smoke seen to be coming from a building next to tower by the road",
        "confidence": 0.87
    },
    {
        "video_filename": "img3.png",
        "caption": "Large flames visible on a local high-rise building with fire department on the scene",
        "confidence": 0.92
    },
    {
        "video_filename": "img4.png",
        "caption": "Wide parking of local school building with many parked cars",
        "confidence": 0.92
    },
    {
        "video_filename": "img5.jpg",
        "caption": "Smoke coming from skyscraper fire brigade on scene trying to extinguish the flames",
        "confidence": 0.89
    },
    {
        "video_filename": "img6.webp",
        "caption": "dog sitting on grass",
        "confidence": 0.91
    },
    {
        "video_filename": "img7.webp",
        "caption": "dog sitting infront of tree trunk in park",
        "confidence": 0.88
    },
    {
        "video_filename": "img8.webp",
        "caption": "dog out on a hike with owner",
        "confidence": 0.84
    },
    {
        "video_filename": "img9.jpg",
        "caption": "dog jumping over obstacle",
        "confidence": 0.96
    },
    {
        "video_filename": "img10.png",
        "caption": "puppy sleeping while hugging stuffed animal",
        "confidence": 0.79
    }
]

# Paths for FAISS index and id map
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss_captions.index")
FAISS_IDMAP_PATH = os.path.join(BASE_DIR, "faiss_captions_idmap.json")

def verify_minio_bucket():
    """Verify that the nlp-images bucket exists in MinIO"""
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        
        if client.bucket_exists(NLP_IMAGES_BUCKET):
            logger.info(f"✅ MinIO bucket '{NLP_IMAGES_BUCKET}' exists")
            return True
        else:
            logger.warning(f"⚠️ MinIO bucket '{NLP_IMAGES_BUCKET}' does not exist")
            logger.info(f"Creating bucket '{NLP_IMAGES_BUCKET}'...")
            client.make_bucket(NLP_IMAGES_BUCKET)
            logger.info(f"✅ MinIO bucket '{NLP_IMAGES_BUCKET}' created")
            return True
    except Exception as e:
        logger.error(f"❌ Error connecting to MinIO: {e}")
        return False


def list_objects_in_bucket():
    """List all objects in the nlp-images bucket"""
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        
        objects = client.list_objects(NLP_IMAGES_BUCKET)
        object_list = [obj.object_name for obj in objects]
        
        if object_list:
            logger.info(f"📁 Objects in '{NLP_IMAGES_BUCKET}' bucket:")
            for obj in object_list:
                logger.info(f"   - {obj}")
            return object_list
        else:
            logger.warning(f"⚠️ No objects found in '{NLP_IMAGES_BUCKET}' bucket")
            return []
    except Exception as e:
        logger.error(f"❌ Error listing objects: {e}")
        return []


def upload_captions_to_mongodb():
    """Upload captions to MongoDB event_descriptions collection"""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client.get_default_database()
        collection = db["event_descriptions"]
        
        logger.info(f"📊 Connected to MongoDB database")
        logger.info(f"📝 Uploading {len(HARDCODED_CAPTIONS)} captions to 'event_descriptions' collection...")
        
        inserted_count = 0
        inserted_documents = []

        # Prepare embedding model and lists for FAISS
        embeddings = []
        id_map = []  # maps faiss idx -> description_id

        if not SENTER_AVAILABLE:
            logger.warning("⚠️ sentence-transformers or faiss not available; captions will be stored without embeddings")
        else:
            # Load model once
            try:
                embed_model = SentenceTransformer("all-mpnet-base-v2")
                embed_dim = 768
                logger.info("✅ Loaded SentenceTransformer 'all-mpnet-base-v2' for embeddings")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                embed_model = None
        
        for i, caption_data in enumerate(HARDCODED_CAPTIONS, 1):
            # Generate unique IDs
            description_id = f"desc_{uuid.uuid4().hex[:12]}"
            event_id = f"event_{uuid.uuid4().hex[:12]}"
            
            # Compute embedding if available
            text_emb_list = []
            if SENTER_AVAILABLE and embed_model is not None:
                try:
                    emb = embed_model.encode(caption_data["caption"], normalize_embeddings=True).astype("float32")
                    text_emb_list = emb.tolist()
                    embeddings.append(emb)
                    id_map.append(description_id)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to compute embedding for caption {i}: {e}")

            # Create caption document
            caption_doc = {
                "description_id": description_id,
                "event_id": event_id,
                "caption": caption_data["caption"],
                "confidence": caption_data["confidence"],
                "text_embedding": text_emb_list,
                "video_reference": {
                    "bucket": NLP_IMAGES_BUCKET,
                    "object_name": caption_data["video_filename"],
                    "minio_path": f"{NLP_IMAGES_BUCKET}/{caption_data['video_filename']}"
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Insert into MongoDB
            result = collection.insert_one(caption_doc)
            inserted_count += 1
            inserted_documents.append({
                "index": i,
                "description_id": description_id,
                "event_id": event_id,
                "video": caption_data["video_filename"],
                "confidence": caption_data["confidence"]
            })
            
            logger.info(f"✅ [{i}/10] Inserted caption: {description_id}")

        logger.info(f"\n🎉 Successfully uploaded {inserted_count} captions to MongoDB")
        logger.info("\n📋 Inserted Captions Summary:")
        logger.info("=" * 80)

        for doc in inserted_documents:
            logger.info(
                f"[{doc['index']:2d}] ID: {doc['description_id']} | "
                f"Event: {doc['event_id']} | "
                f"Video: {doc['video']} | "
                f"Confidence: {doc['confidence']:.2f}"
            )

        logger.info("=" * 80)

        # Display summary statistics
        total_captions = collection.count_documents({})
        logger.info(f"\n📊 Total captions in collection: {total_captions}")

        # Build and persist FAISS index if embeddings were computed
        if SENTER_AVAILABLE and embeddings:
            try:
                emb_matrix = np.stack(embeddings, axis=0).astype("float32")
                dim = emb_matrix.shape[1]
                index = faiss.IndexFlatIP(dim)
                # Add embeddings
                index.add(emb_matrix)

                # Write index to disk
                faiss.write_index(index, FAISS_INDEX_PATH)

                # Save id map (index -> description_id)
                with open(FAISS_IDMAP_PATH, "w", encoding="utf-8") as f:
                    json.dump(id_map, f, indent=2)

                logger.info(f"✅ FAISS index saved to: {FAISS_INDEX_PATH}")
                logger.info(f"✅ FAISS id map saved to: {FAISS_IDMAP_PATH}")
            except Exception as e:
                logger.error(f"❌ Failed to build/save FAISS index: {e}")

        return True
        
    except Exception as e:
        logger.error(f"❌ Error uploading captions to MongoDB: {e}")
        return False


def verify_uploaded_captions():
    """Verify that captions were successfully uploaded"""
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_default_database()
        collection = db["event_descriptions"]
        
        # Find recently uploaded captions
        captions = list(collection.find(
            {"video_reference": {"$exists": True}},
            {"_id": 0, "description_id": 1, "caption": 1, "confidence": 1, "video_reference": 1}
        ).limit(10))
        
        if captions:
            logger.info(f"\n✅ Verification: Found {len(captions)} captions with video references")
            logger.info("\n📝 Sample Captions:")
            logger.info("=" * 80)
            for cap in captions[:3]:
                logger.info(f"ID: {cap['description_id']}")
                logger.info(f"Caption: {cap['caption']}")
                logger.info(f"Confidence: {cap['confidence']:.2f}")
                logger.info(f"Video: {cap['video_reference']['object_name']}")
                logger.info("-" * 80)
            return True
        else:
            logger.warning("⚠️ No captions found with video references")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verifying captions: {e}")
        return False


def main():
    """Main execution function"""
    logger.info("🚀 Starting Caption Upload Process")
    logger.info("=" * 80)
    
    # Step 1: Verify MinIO bucket
    logger.info("\n[Step 1/4] Verifying MinIO bucket...")
    if not verify_minio_bucket():
        logger.error("❌ Failed to verify MinIO bucket. Exiting.")
        return False
    
    # Step 2: List objects in bucket
    logger.info("\n[Step 2/4] Listing objects in MinIO bucket...")
    objects = list_objects_in_bucket()
    
    # Step 3: Upload captions to MongoDB
    logger.info("\n[Step 3/4] Uploading captions to MongoDB...")
    if not upload_captions_to_mongodb():
        logger.error("❌ Failed to upload captions. Exiting.")
        return False
    
    # Step 4: Verify upload
    logger.info("\n[Step 4/4] Verifying uploaded captions...")
    if not verify_uploaded_captions():
        logger.warning("⚠️ Verification encountered issues")
    
    logger.info("\n" + "=" * 80)
    logger.info("🎉 Caption Upload Process Completed Successfully!")
    logger.info("=" * 80)
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

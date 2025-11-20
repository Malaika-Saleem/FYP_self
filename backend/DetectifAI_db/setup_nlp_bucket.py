"""
Setup script to create the nlp-images bucket in MinIO
"""

import os
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "adminpassword")
NLP_IMAGES_BUCKET = "nlp-images"

def setup_nlp_bucket():
    """Create the nlp-images bucket if it doesn't exist"""
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        
        if client.bucket_exists(NLP_IMAGES_BUCKET):
            logger.info(f"✅ MinIO bucket '{NLP_IMAGES_BUCKET}' already exists")
            return True
        else:
            logger.info(f"Creating MinIO bucket '{NLP_IMAGES_BUCKET}'...")
            client.make_bucket(NLP_IMAGES_BUCKET)
            logger.info(f"✅ MinIO bucket '{NLP_IMAGES_BUCKET}' created successfully")
            return True
    except S3Error as e:
        if e.code == "BucketAlreadyOwnedByYou" or e.code == "BucketAlreadyExists":
            logger.info(f"✅ MinIO bucket '{NLP_IMAGES_BUCKET}' already exists")
            return True
        else:
            logger.error(f"❌ Error creating bucket: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Error connecting to MinIO: {e}")
        return False

if __name__ == "__main__":
    logger.info("Setting up nlp-images bucket...")
    success = setup_nlp_bucket()
    if success:
        logger.info("✅ Setup complete!")
    else:
        logger.error("❌ Setup failed!")
        exit(1)


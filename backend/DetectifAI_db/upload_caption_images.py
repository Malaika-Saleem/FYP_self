"""
Upload Caption Images to MinIO

This script uploads the image files referenced in the captions to the MinIO nlp-images bucket.
The images should be in a local directory (e.g., 'caption_images' folder).

Usage:
    python upload_caption_images.py [--image-dir <directory>]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error
import logging

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
NLP_IMAGES_BUCKET = "nlp-images"

# Expected image files from upload_captions.py
EXPECTED_IMAGES = [
    "img1.webp",
    "img2.jpg",
    "img3.png",
    "img4.png",
    "img5.jpg",
    "img6.webp",
    "img7.webp",
    "img8.webp",
    "img9.jpg",
    "img10.png"
]


def setup_minio_client():
    """Initialize MinIO client"""
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        return client
    except Exception as e:
        logger.error(f"❌ Error connecting to MinIO: {e}")
        return None


def ensure_bucket_exists(client, bucket_name):
    """Ensure the bucket exists, create if it doesn't"""
    try:
        if not client.bucket_exists(bucket_name):
            logger.info(f"Creating bucket: {bucket_name}")
            client.make_bucket(bucket_name)
            logger.info(f"✅ Created bucket: {bucket_name}")
        else:
            logger.info(f"✅ Bucket '{bucket_name}' already exists")
        return True
    except S3Error as e:
        if e.code == "BucketAlreadyOwnedByYou" or e.code == "BucketAlreadyExists":
            logger.info(f"✅ Bucket '{bucket_name}' already exists")
            return True
        logger.error(f"❌ Error creating bucket: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def upload_image(client, bucket_name, image_path, object_name):
    """Upload a single image file to MinIO"""
    try:
        if not os.path.exists(image_path):
            logger.warning(f"⚠️ Image file not found: {image_path}")
            return False
        
        file_size = os.path.getsize(image_path)
        
        # Determine content type based on extension
        ext = image_path.lower().split('.')[-1]
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
            'gif': 'image/gif'
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')
        
        with open(image_path, 'rb') as file_data:
            client.put_object(
                bucket_name,
                object_name,
                file_data,
                length=file_size,
                content_type=content_type
            )
        
        logger.info(f"✅ Uploaded: {object_name} ({file_size} bytes)")
        return True
    except S3Error as e:
        logger.error(f"❌ S3Error uploading {object_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error uploading {object_name}: {e}")
        return False


def find_image_directory():
    """Try to find the directory containing caption images"""
    # Common locations to check
    possible_dirs = [
        Path(__file__).parent / "caption_images",
        Path(__file__).parent.parent / "caption_images",
        Path(__file__).parent / "images",
        Path(__file__).parent.parent / "images",
        Path(__file__).parent / "DetectifAI_db" / "caption_images",
    ]
    
    for dir_path in possible_dirs:
        if dir_path.exists() and dir_path.is_dir():
            # Check if it contains any of the expected images
            files = [f.name for f in dir_path.iterdir() if f.is_file()]
            if any(img in files for img in EXPECTED_IMAGES):
                return dir_path
    
    return None


def upload_all_images(image_dir=None):
    """Upload all caption images to MinIO"""
    logger.info("🚀 Starting Caption Image Upload Process")
    logger.info("=" * 80)
    
    # Initialize MinIO client
    client = setup_minio_client()
    if not client:
        logger.error("❌ Failed to initialize MinIO client")
        return False
    
    # Ensure bucket exists
    if not ensure_bucket_exists(client, NLP_IMAGES_BUCKET):
        logger.error("❌ Failed to ensure bucket exists")
        return False
    
    # Find image directory
    if image_dir is None:
        image_dir = find_image_directory()
    
    if image_dir is None:
        logger.error("❌ Could not find image directory")
        logger.info("💡 Please provide the image directory path:")
        logger.info("   python upload_caption_images.py --image-dir <path>")
        logger.info("")
        logger.info("Expected image files:")
        for img in EXPECTED_IMAGES:
            logger.info(f"   - {img}")
        return False
    
    image_dir = Path(image_dir)
    if not image_dir.exists():
        logger.error(f"❌ Image directory does not exist: {image_dir}")
        return False
    
    logger.info(f"📁 Using image directory: {image_dir}")
    logger.info("")
    
    # Upload each image
    uploaded_count = 0
    failed_count = 0
    missing_count = 0
    
    for image_name in EXPECTED_IMAGES:
        image_path = image_dir / image_name
        
        if not image_path.exists():
            logger.warning(f"⚠️ Image not found: {image_name}")
            missing_count += 1
            continue
        
        if upload_image(client, NLP_IMAGES_BUCKET, str(image_path), image_name):
            uploaded_count += 1
        else:
            failed_count += 1
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Upload Summary:")
    logger.info(f"   ✅ Successfully uploaded: {uploaded_count}")
    logger.info(f"   ❌ Failed: {failed_count}")
    logger.info(f"   ⚠️ Missing: {missing_count}")
    logger.info(f"   📦 Total expected: {len(EXPECTED_IMAGES)}")
    logger.info("=" * 80)
    
    if uploaded_count > 0:
        logger.info("✅ Image upload process completed!")
        return True
    else:
        logger.error("❌ No images were uploaded")
        return False


def list_bucket_contents(client, bucket_name):
    """List all objects in the bucket"""
    try:
        logger.info(f"\n📦 Contents of '{bucket_name}' bucket:")
        objects = client.list_objects(bucket_name, recursive=True)
        count = 0
        for obj in objects:
            logger.info(f"   - {obj.object_name} ({obj.size} bytes)")
            count += 1
        if count == 0:
            logger.info("   (bucket is empty)")
        return count
    except Exception as e:
        logger.error(f"❌ Error listing bucket contents: {e}")
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload caption images to MinIO")
    parser.add_argument(
        "--image-dir",
        type=str,
        help="Directory containing the caption images"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List current contents of nlp-images bucket"
    )
    
    args = parser.parse_args()
    
    if args.list:
        client = setup_minio_client()
        if client:
            list_bucket_contents(client, NLP_IMAGES_BUCKET)
    else:
        success = upload_all_images(args.image_dir)
        sys.exit(0 if success else 1)


"""
MinIO Setup and Test Script for DetectifAI
"""
from minio import Minio
from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def setup_minio():
    """Setup MinIO with proper configuration"""
    try:
        # MinIO client setup
        client = Minio(
            "127.0.0.1:9000",
            access_key="admin",
            secret_key="adminpassword",
            secure=False
        )

        # Define required buckets
        buckets = [
            "detectifai-videos",
            "detectifai-keyframes",
            "detectifai-compressed"
        ]

        # Create buckets if they don't exist
        for bucket in buckets:
            found = client.bucket_exists(bucket)
            if not found:
                logger.info(f"Creating bucket: {bucket}")
                client.make_bucket(bucket)
                logger.info(f"✅ Created bucket: {bucket}")
            else:
                logger.info(f"✅ Bucket already exists: {bucket}")

        # Test upload to each bucket
        test_data = b"DetectifAI Test Data"
        for bucket in buckets:
            try:
                test_object = f"test_{bucket}.txt"
                client.put_object(
                    bucket,
                    test_object,
                    bytes(test_data),
                    len(test_data)
                )
                logger.info(f"✅ Test upload successful to {bucket}")

                # Clean up test file
                client.remove_object(bucket, test_object)

            except Exception as bucket_error:
                logger.error(f"❌ Failed to upload test file to {bucket}: {str(bucket_error)}")

        # List objects in each bucket
        logger.info("\nCurrent bucket contents:")
        for bucket in buckets:
            logger.info(f"\nBucket: {bucket}")
            try:
                objects = client.list_objects(bucket, recursive=True)
                for obj in objects:
                    logger.info(f"- {obj.object_name} (size: {obj.size} bytes)")
            except Exception as list_error:
                logger.error(f"❌ Failed to list objects in {bucket}: {str(list_error)}")

        return True, "MinIO setup completed successfully"

    except Exception as e:
        error_message = f"MinIO setup failed: {str(e)}"
        logger.error(f"❌ {error_message}")
        return False, error_message

if __name__ == "__main__":
    success, message = setup_minio()
    if success:
        logger.info("✅ MinIO setup completed successfully!")
    else:
        logger.error(f"❌ MinIO setup failed: {message}")
"""
Reset MinIO buckets and test storage paths for DetectifAI.

This script ensures that all required MinIO buckets and storage paths
are properly configured for video processing.
"""

from minio import Minio
from minio.error import S3Error
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MinIO configuration
MINIO_CONFIG = {
    "endpoint": "127.0.0.1:9000",
    "access_key": "admin",
    "secret_key": "adminpassword",
    "secure": False
}

# Bucket configuration with descriptions
BUCKETS = {
    "detectifai-videos": {
        "description": "Main bucket for video storage",
        "prefixes": {
            "original": "Original uploaded videos",
            "compressed": "Compressed video versions"
        }
    },
    "detectifai-keyframes": {
        "description": "Storage for extracted video frames",
        "prefixes": {
            "keyframes": "Extracted keyframes and annotated frames"
        }
    }
}

def reset_minio_storage():
    """Reset and verify MinIO storage configuration"""
    client = Minio(**MINIO_CONFIG)
    
    print("Checking MinIO connection and buckets...")
    
    for bucket_name, config in BUCKETS.items():
        try:
            # Check if bucket exists
            found = client.bucket_exists(bucket_name)
            if not found:
                print(f"Creating bucket: {bucket_name}")
                client.make_bucket(bucket_name)
            
            # Test each prefix path
            for prefix in config["prefixes"]:
                test_object = f"{prefix}/test.txt"
                test_data = f"Test data for {bucket_name}/{prefix}"
                
                print(f"\nTesting path: {bucket_name}/{test_object}")
                
                # Upload test object
                test_bytes = bytes(test_data, 'utf-8')
                from io import BytesIO
                test_stream = BytesIO(test_bytes)
                client.put_object(
                    bucket_name,
                    test_object,
                    test_stream,
                    len(test_bytes)
                )
                
                # Verify upload
                try:
                    client.stat_object(bucket_name, test_object)
                    print(f"✅ Test file uploaded successfully")
                    
                    # Clean up test file
                    client.remove_object(bucket_name, test_object)
                    print(f"✅ Test file removed")
                except:
                    print(f"❌ Could not verify test file")
            
            print(f"\nListing objects in {bucket_name}:")
            objects = client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                print(f"- {obj.object_name} (size: {obj.size} bytes)")
                
        except S3Error as e:
            print(f"❌ Error with bucket {bucket_name}: {e}")
            continue

if __name__ == "__main__":
    reset_minio_storage()
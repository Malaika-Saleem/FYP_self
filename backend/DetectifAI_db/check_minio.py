from minio import Minio
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MinIO client setup
client = Minio(
    "127.0.0.1:9000",
    access_key="admin",
    secret_key="adminpassword",
    secure=False
)

# Check if bucket exists
bucket_name = "detectifai-videos"
found = client.bucket_exists(bucket_name)
print(f"Bucket '{bucket_name}' exists: {found}")

if found:
    print("\nListing objects in bucket:")
    objects = client.list_objects(bucket_name, recursive=True)
    for obj in objects:
        print(f"- {obj.object_name} (size: {obj.size} bytes)")
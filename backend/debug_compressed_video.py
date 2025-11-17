"""
Debug script to check compressed video storage and retrieval
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database.config import DatabaseManager
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Initialize database manager
db_manager = DatabaseManager()

# Get video_id from command line or use test ID
video_id = sys.argv[1] if len(sys.argv) > 1 else "video_20251117_042457_d0293c86"

print(f"\n{'='*60}")
print(f"🔍 Debugging compressed video for: {video_id}")
print(f"{'='*60}\n")

# Check MongoDB
print("📊 Checking MongoDB...")
try:
    video_record = db_manager.db.video_file.find_one({"video_id": video_id})
    if video_record:
        print(f"✅ Found video record in MongoDB")
        print(f"   - minio_bucket: {video_record.get('minio_bucket')}")
        print(f"   - minio_object_key (original): {video_record.get('minio_object_key')}")
        
        meta_data = video_record.get('meta_data', {})
        print(f"\n📁 Metadata:")
        print(f"   - minio_compressed_path: {meta_data.get('minio_compressed_path')}")
        
        compression_info = meta_data.get('compression_info', {})
        if compression_info:
            print(f"   - compression_info.minio_path: {compression_info.get('minio_path')}")
            print(f"   - compression_info.local_path: {compression_info.get('local_path')}")
    else:
        print(f"❌ Video record not found in MongoDB")
except Exception as e:
    print(f"❌ Error checking MongoDB: {e}")

# Check MinIO
print(f"\n📦 Checking MinIO...")
try:
    bucket = video_record.get('minio_bucket') if video_record else db_manager.config.minio_video_bucket
    print(f"   Using bucket: {bucket}")
    
    # Try different possible paths
    possible_paths = [
        meta_data.get('minio_compressed_path') if video_record else None,
        f"compressed/{video_id}/video.mp4",
        f"compressed/{video_id}/compressed.mp4",
    ]
    
    # Remove None values
    possible_paths = [p for p in possible_paths if p]
    
    print(f"\n🔍 Checking paths:")
    for path in possible_paths:
        try:
            print(f"   Trying: {path}")
            obj = db_manager.minio_client.stat_object(bucket, path)
            print(f"   ✅ FOUND! Size: {obj.size} bytes, Modified: {obj.last_modified}")
        except Exception as e:
            print(f"   ❌ Not found: {str(e)[:100]}")
    
    # List all objects with compressed prefix
    print(f"\n📋 Listing all objects with 'compressed/{video_id}/' prefix:")
    objects = list(db_manager.minio_client.list_objects(bucket, prefix=f"compressed/{video_id}/", recursive=True))
    if objects:
        for obj in objects:
            print(f"   - {obj.object_name} ({obj.size} bytes)")
    else:
        print(f"   ❌ No objects found with this prefix")
        
except Exception as e:
    print(f"❌ Error checking MinIO: {e}")
    import traceback
    traceback.print_exc()

# Check local storage
print(f"\n💾 Checking local storage...")
possible_local_paths = [
    f"video_processing_outputs/compressed/{video_id}/video.mp4",
    f"backend/video_processing_outputs/compressed/{video_id}/video.mp4",
    f"./video_processing_outputs/compressed/{video_id}/video.mp4",
]

for path in possible_local_paths:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"   ✅ Found: {path} ({size} bytes)")
    else:
        print(f"   ❌ Not found: {path}")

print(f"\n{'='*60}\n")


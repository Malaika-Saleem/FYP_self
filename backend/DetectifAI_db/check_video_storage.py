"""
Utility script to validate and fix video storage
"""

import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import DatabaseManager
from database.models import VideoFileModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_video_storage():
    """Check and validate video storage in MongoDB and MinIO"""
    db_manager = DatabaseManager()
    
    # 1. Check MongoDB video records
    logger.info("Checking MongoDB video records...")
    video_collection = db_manager.db.video_file
    videos = list(video_collection.find({}))
    logger.info(f"Found {len(videos)} video records in MongoDB")
    
    # 2. Check MinIO storage
    logger.info("\nChecking MinIO storage...")
    try:
        # Check video bucket
        video_objects = list(db_manager.minio_client.list_objects(
            db_manager.config.minio_video_bucket, 
            recursive=True
        ))
        logger.info(f"Found {len(video_objects)} objects in video bucket")
        
        # Check keyframe bucket
        keyframe_objects = list(db_manager.minio_client.list_objects(
            db_manager.config.minio_keyframe_bucket, 
            recursive=True
        ))
        logger.info(f"Found {len(keyframe_objects)} objects in keyframe bucket")
        
        # Map MinIO objects to video IDs
        minio_video_ids = set()
        minio_keyframe_video_ids = set()
        
        for obj in video_objects:
            parts = obj.object_name.split('/')
            if len(parts) > 1:
                minio_video_ids.add(parts[1])  # original/{video_id}/video.mp4
                
        for obj in keyframe_objects:
            parts = obj.object_name.split('/')
            if len(parts) > 0:
                minio_keyframe_video_ids.add(parts[0])  # {video_id}/keyframes/...
        
        # 3. Cross-reference and find inconsistencies
        logger.info("\nCross-referencing storage...")
        mongo_video_ids = {str(v['video_id']) for v in videos}
        
        # Find mismatches
        missing_in_minio = mongo_video_ids - minio_video_ids
        missing_keyframes = mongo_video_ids - minio_keyframe_video_ids
        orphaned_in_minio = minio_video_ids - mongo_video_ids
        
        if missing_in_minio:
            logger.warning(f"\n⚠️ Found {len(missing_in_minio)} videos missing in MinIO:")
            for vid in missing_in_minio:
                logger.warning(f"- {vid}")
        
        if missing_keyframes:
            logger.warning(f"\n⚠️ Found {len(missing_keyframes)} videos missing keyframes:")
            for vid in missing_keyframes:
                logger.warning(f"- {vid}")
        
        if orphaned_in_minio:
            logger.warning(f"\n⚠️ Found {len(orphaned_in_minio)} orphaned videos in MinIO:")
            for vid in orphaned_in_minio:
                logger.warning(f"- {vid}")
        
        # 4. Check MongoDB metadata completeness
        logger.info("\nChecking metadata completeness...")
        incomplete_metadata = []
        for video in videos:
            if not video.get('meta_data'):
                incomplete_metadata.append(video['video_id'])
                continue
            
            meta = video['meta_data']
            required_fields = ['filename', 'processing_status', 'upload_date']
            missing_fields = [f for f in required_fields if f not in meta]
            
            if missing_fields:
                incomplete_metadata.append({
                    'video_id': video['video_id'],
                    'missing_fields': missing_fields
                })
        
        if incomplete_metadata:
            logger.warning(f"\n⚠️ Found {len(incomplete_metadata)} videos with incomplete metadata:")
            for item in incomplete_metadata:
                if isinstance(item, dict):
                    logger.warning(f"- {item['video_id']} (missing: {', '.join(item['missing_fields'])})")
                else:
                    logger.warning(f"- {item} (missing entire meta_data object)")
        
        return {
            'mongodb_videos': len(videos),
            'minio_videos': len(video_objects),
            'minio_keyframes': len(keyframe_objects),
            'missing_in_minio': list(missing_in_minio),
            'missing_keyframes': list(missing_keyframes),
            'orphaned_in_minio': list(orphaned_in_minio),
            'incomplete_metadata': incomplete_metadata
        }
        
    except Exception as e:
        logger.error(f"Error checking storage: {e}")
        raise

def fix_metadata():
    """Fix incomplete metadata in MongoDB records"""
    db_manager = DatabaseManager()
    video_collection = db_manager.db.video_file
    
    logger.info("Fixing incomplete metadata...")
    fixed_count = 0
    
    for video in video_collection.find({}):
        needs_update = False
        update_fields = {}
        
        # Ensure meta_data exists
        if 'meta_data' not in video:
            update_fields['meta_data'] = {
                'processing_status': 'unknown',
                'upload_date': video.get('upload_date', datetime.utcnow()),
                'filename': f"video_{video['video_id']}.mp4"
            }
            needs_update = True
        else:
            meta = video['meta_data']
            
            # Check and fix required fields
            if 'processing_status' not in meta:
                meta['processing_status'] = 'unknown'
                needs_update = True
            
            if 'upload_date' not in meta and 'upload_date' in video:
                meta['upload_date'] = video['upload_date']
                needs_update = True
            
            if 'filename' not in meta:
                meta['filename'] = f"video_{video['video_id']}.mp4"
                needs_update = True
            
            if needs_update:
                update_fields['meta_data'] = meta
        
        # Apply updates if needed
        if needs_update:
            try:
                video_collection.update_one(
                    {'_id': video['_id']},
                    {'$set': update_fields}
                )
                fixed_count += 1
                logger.info(f"Fixed metadata for video {video['video_id']}")
            except Exception as e:
                logger.error(f"Failed to fix metadata for {video['video_id']}: {e}")
    
    logger.info(f"\n✅ Fixed metadata for {fixed_count} videos")
    return fixed_count

if __name__ == "__main__":
    try:
        # First check storage
        results = check_video_storage()
        
        # If there are metadata issues, fix them
        if results['incomplete_metadata']:
            if input("\nFix incomplete metadata? (y/n): ").lower() == 'y':
                fixed = fix_metadata()
                print(f"\nFixed {fixed} video records")
        
        print("\nStorage check complete!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
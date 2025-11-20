"""
Repository Classes for DetectifAI Database Operations

This module provides data access layer for MongoDB and MinIO operations.
Each repository handles CRUD operations for specific collections.
"""

import os
import io
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo.collection import Collection
from minio import Minio
from minio.error import S3Error
import logging

from .models import (
    VideoFileModel, EventModel, EventDescriptionModel, DetectedFaceModel,
    prepare_for_mongodb, convert_objectid_to_string, convert_numpy_types,
    seconds_to_milliseconds
)

logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository class with common functionality"""
    
    def __init__(self, db_manager):
        self.db = db_manager.db
        self.minio = db_manager.minio_client
        self.video_bucket = db_manager.config.minio_video_bucket
        self.keyframe_bucket = db_manager.config.minio_keyframe_bucket

class VideoRepository(BaseRepository):
    """Repository for video_file collection operations"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.video_file
    
    def create_video_record(self, video_data: Dict) -> str:
        """Create new video record matching MongoDB schema exactly"""
        try:
            # Extract required fields
            video_id = video_data.get('video_id')
            user_id = video_data.get('user_id', 'system')
            file_path = video_data.get('file_path', f"videos/{video_id}.mp4")
            
            # Build schema-compliant record
            record = {
                "video_id": video_id,
                "user_id": user_id,
                "file_path": file_path,
                "upload_date": datetime.utcnow()
            }
            
            # Add optional schema fields
            if 'fps' in video_data:
                record['fps'] = float(video_data['fps'])  # Ensure double type
            else:
                record['fps'] = 30.0  # Default
            
            if 'duration' in video_data or 'duration_secs' in video_data:
                duration = video_data.get('duration_secs') or video_data.get('duration', 0)
                record['duration_secs'] = int(duration)  # Ensure integer
            
            if 'file_size' in video_data or 'file_size_bytes' in video_data:
                file_size = video_data.get('file_size_bytes') or video_data.get('file_size', 0)
                record['file_size_bytes'] = int(file_size)  # Ensure long
            
            if 'codec' in video_data:
                record['codec'] = str(video_data['codec'])
            
            if 'minio_object_key' in video_data:
                record['minio_object_key'] = video_data['minio_object_key']
            
            if 'minio_bucket' in video_data:
                record['minio_bucket'] = video_data['minio_bucket']
            
            # Build meta_data object for extra fields
            meta_data = {}
            extra_fields = [
                'processing_status', 'resolution', 'filename', 'keyframe_count',
                'event_count', 'compression_applied', 'enhancement_applied',
                'error_message', 'processing_config'
            ]
            
            for field in extra_fields:
                if field in video_data:
                    meta_data[field] = video_data[field]
            
            if meta_data:
                record['meta_data'] = meta_data
            
            # Convert numpy types and prepare for MongoDB
            record = prepare_for_mongodb(record)
            
            result = self.collection.insert_one(record)
            logger.info(f"✅ Created video record: {video_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to create video record: {e}")
            raise
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """Get video record by video_id"""
        try:
            doc = self.collection.find_one({"video_id": video_id})
            if doc:
                return convert_objectid_to_string(doc)
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get video {video_id}: {e}")
            return None
    
    def update_processing_status(self, video_id: str, status: str, metadata: Dict = None):
        """Update video processing status in meta_data field"""
        try:
            # Get current meta_data
            video = self.collection.find_one({"video_id": video_id})
            if not video:
                logger.warning(f"⚠️ Video not found for status update: {video_id}")
                return
            
            current_meta = video.get('meta_data', {})
            current_meta['processing_status'] = status
            current_meta['last_updated'] = datetime.utcnow().isoformat()
            
            # Add any additional metadata
            if metadata:
                current_meta.update(metadata)
            
            result = self.collection.update_one(
                {"video_id": video_id},
                {"$set": {"meta_data": current_meta}}
            )
            
            if result.matched_count > 0:
                logger.info(f"✅ Updated video status: {video_id} -> {status}")
            else:
                logger.warning(f"⚠️ Video not found for status update: {video_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to update video status: {e}")
            raise
    
    def update_metadata(self, video_id: str, metadata: Dict):
        """Update video meta_data field with processing information"""
        try:
            # Get current meta_data
            video = self.collection.find_one({"video_id": video_id})
            if not video:
                logger.warning(f"⚠️ Video not found: {video_id}")
                return
            
            current_meta = video.get('meta_data', {})
            current_meta.update(metadata)
            
            result = self.collection.update_one(
                {"video_id": video_id},
                {"$set": {"meta_data": current_meta}}
            )
            
            logger.info(f"✅ Updated video metadata: {video_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update video metadata: {e}")
            raise
    
    def upload_video_to_minio(self, local_path: str, video_id: str) -> str:
        """Upload video file to MinIO storage"""
        try:
            minio_path = f"original/{video_id}/video.mp4"
            
            with open(local_path, 'rb') as file_data:
                file_info = os.stat(local_path)
                self.minio.put_object(
                    self.video_bucket,
                    minio_path,
                    file_data,
                    length=file_info.st_size,
                    content_type='video/mp4'
                )
            
            logger.info(f"✅ Uploaded video to MinIO: {minio_path}")
            return minio_path
            
        except Exception as e:
            logger.error(f"❌ Failed to upload video to MinIO: {e}")
            raise
    
    def get_video_presigned_url(self, minio_path: str, expires: timedelta = timedelta(hours=1)) -> str:
        """Generate presigned URL for video access"""
        try:
            return self.minio.presigned_get_object(self.video_bucket, minio_path, expires=expires)
        except S3Error as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None

    def get_compressed_video_presigned_url(self, video_id: str, expires: timedelta = timedelta(hours=1)) -> str:
        """Generate presigned URL for compressed video access"""
        try:
            minio_path = f"compressed/{video_id}/video.mp4"
            return self.minio.presigned_get_object(self.video_bucket, minio_path, expires=expires)
        except S3Error as e:
            logger.error(f"❌ Failed to generate presigned URL for compressed video: {e}")
            return None


# ========================================
# Event Repository (Schema-Compliant)
# ========================================

class EventRepository(BaseRepository):
    """Repository for event collection operations - Schema Compliant"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.event
        self.event_description_collection = self.db.event_description
    
    def create_event(self, event_data: Dict) -> str:
        """Create event - alias for save_event for compatibility"""
        return self.save_event(event_data)
    
    def save_event(self, event_data: Dict) -> str:
        """Save event matching MongoDB schema exactly"""
        try:
            import uuid
            
            # Extract required fields
            event_id = event_data.get('event_id', str(uuid.uuid4()))
            video_id = event_data.get('video_id', event_data.get('camera_id', 'unknown'))
            
            # Convert timestamps: seconds (float) -> milliseconds (int)
            start_time = event_data.get('start_timestamp', 0.0)
            end_time = event_data.get('end_timestamp', 0.0)
            start_timestamp_ms = seconds_to_milliseconds(start_time)
            end_timestamp_ms = seconds_to_milliseconds(end_time)
            
            # Build schema-compliant event document
            event_doc = {
                "event_id": event_id,
                "video_id": video_id,
                "start_timestamp_ms": int(start_timestamp_ms),
                "end_timestamp_ms": int(end_timestamp_ms),
                "event_type": event_data.get('event_type', 'motion'),
                "confidence_score": float(event_data.get('confidence', 0.0)),
                "is_verified": False,
                "is_false_positive": False,
                "verified_at": None,
                "verified_by": None,
                "visual_embedding": [],
                "bounding_boxes": event_data.get('bounding_boxes', {})
            }
            
            # Convert numpy types
            event_doc = convert_numpy_types(event_doc)
            event_doc = prepare_for_mongodb(event_doc)
            
            result = self.collection.insert_one(event_doc)
            logger.info(f"✅ Saved event: {event_id} ({event_data.get('event_type')})")
            
            # If there's additional description info, save to event_description
            if event_data.get('description') or event_data.get('caption'):
                self._save_event_description(event_id, event_data)
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to save event: {e}")
            raise
    
    def save_detection_events(self, video_id: str, detection_groups: List[Dict]) -> List[str]:
        """Save object detection events with proper schema compliance"""
        event_ids = []
        
        try:
            for group in detection_groups:
                # Build bounding_boxes object
                bboxes = {
                    "detections": [
                        {
                            "class": det.get('class_name', ''),
                            "confidence": float(det.get('confidence', 0.0)),
                            "bbox": [float(x) for x in det.get('bbox', [0, 0, 0, 0])],
                            "timestamp": float(det.get('frame_timestamp', 0.0)),
                            "model": det.get('detection_model', '')
                        }
                        for det in group.get('detections', [])
                    ]
                }
                
                event_data = {
                    "video_id": video_id,
                    "start_timestamp": group.get('start_timestamp', 0.0),
                    "end_timestamp": group.get('end_timestamp', 0.0),
                    "event_type": f"object_detection_{group.get('class', 'unknown')}",
                    "confidence": group.get('max_confidence', 0.0),
                    "bounding_boxes": bboxes,
                    "description": f"Detected {len(group.get('detections', []))} {group.get('class', 'object')}(s)"
                }
                
                event_id = self.save_event(event_data)
                event_ids.append(event_id)
            
            logger.info(f"✅ Saved {len(event_ids)} detection events for video {video_id}")
            return event_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save detection events: {e}")
            raise
    
    def _save_event_description(self, event_id: str, event_data: Dict):
        """Save detailed event description to event_description collection"""
        try:
            import uuid
            
            description_text = event_data.get('description') or event_data.get('caption', '')
            
            if not description_text:
                return
            
            description_doc = {
                "description_id": str(uuid.uuid4()),
                "event_id": event_id,
                "caption": description_text,
                "text_embedding": [],  # TODO: Generate embedding in future
                "confidence": float(event_data.get('confidence', 0.0)),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            description_doc = prepare_for_mongodb(description_doc)
            self.event_description_collection.insert_one(description_doc)
            logger.info(f"✅ Saved event description for {event_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save event description: {e}")
    
    def get_events_by_video_id(self, video_id: str, event_type: str = None) -> List[Dict]:
        """Get events for a video with optional type filtering"""
        try:
            query = {"video_id": video_id}
            if event_type:
                query["event_type"] = event_type
            
            events = list(self.collection.find(query).sort("start_timestamp_ms", 1))
            
            # Convert ObjectIds to strings
            for event in events:
                event = convert_objectid_to_string(event)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Failed to get events for video {video_id}: {e}")
            return []
    
    def mark_as_false_positive(self, event_id: str):
        """Mark event as false positive (for deduplication)"""
        try:
            self.collection.update_one(
                {"event_id": event_id},
                {"$set": {"is_false_positive": True}}
            )
            logger.info(f"✅ Marked event {event_id} as false positive")
        except Exception as e:
            logger.error(f"❌ Failed to mark event as false positive: {e}")


# Remove KeyframeRepository - collection doesn't exist in schema
# Remove ProcessingJobRepository - collection doesn't exist in schema  
# Remove ObjectDetectionRepository - collection doesn't exist in schema

# Only VideoRepository and EventRepository are schema-compliant and remain above
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
    VideoFileModel, KeyframeModel, EventModel, ProcessingJobModel,
    ObjectDetectionModel, DetectedFaceModel, prepare_for_mongodb,
    convert_objectid_to_string
)

logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository class with common functionality"""
    
    def __init__(self, db_manager):
        self.db = db_manager.db
        self.minio = db_manager.minio_client
        self.bucket = db_manager.config.minio_bucket

class VideoRepository(BaseRepository):
    """Repository for video_file collection operations"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.video_file
    
    def create_video_record(self, video_data: Dict) -> str:
        """Create new video record in database"""
        try:
            # Ensure required fields are present with defaults
            if 'user_id' not in video_data or not video_data['user_id']:
                video_data['user_id'] = 'anonymous'  # Default user
            
            if 'file_path' not in video_data:
                video_data['file_path'] = f"videos/original/{video_data['video_id']}.mp4"
            
            video_model = VideoFileModel(**video_data)
            doc = prepare_for_mongodb(video_model.to_dict())
            
            result = self.collection.insert_one(doc)
            logger.info(f"✅ Created video record: {video_data['video_id']}")
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
        """Update video processing status and metadata"""
        try:
            update_data = {
                "processing_status": status,
                "updated_at": datetime.utcnow()
            }
            
            if metadata:
                update_data.update(metadata)
            
            result = self.collection.update_one(
                {"video_id": video_id},
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                logger.info(f"✅ Updated video status: {video_id} -> {status}")
            else:
                logger.warning(f"⚠️ Video not found for status update: {video_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to update video status: {e}")
            raise
    
    def upload_video_to_minio(self, local_path: str, video_id: str) -> str:
        """Upload video file to MinIO storage"""
        try:
            minio_path = f"videos/original/{video_id}.mp4"
            
            with open(local_path, 'rb') as file_data:
                file_info = os.stat(local_path)
                self.minio.put_object(
                    self.bucket,
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
            return self.minio.presigned_get_object(self.bucket, minio_path, expires=expires)
        except S3Error as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None

class KeyframeRepository(BaseRepository):
    """Repository for keyframes collection operations"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.keyframes
    
    def save_keyframes_batch(self, video_id: str, keyframes_data: List[Dict]) -> List[str]:
        """Save multiple keyframes to MinIO and MongoDB"""
        keyframe_ids = []
        
        try:
            for i, kf_data in enumerate(keyframes_data):
                # Extract frame data from keyframe result
                frame_data = kf_data.frame_data if hasattr(kf_data, 'frame_data') else kf_data
                
                # Upload keyframe image to MinIO
                minio_path = f"keyframes/{video_id}/frame_{frame_data['frame_number']:06d}.jpg"
                
                # Handle both file path and frame data scenarios
                if 'frame_path' in frame_data:
                    local_path = frame_data['frame_path']
                    if os.path.exists(local_path):
                        with open(local_path, 'rb') as img_file:
                            file_info = os.stat(local_path)
                            self.minio.put_object(
                                self.bucket,
                                minio_path,
                                img_file,
                                length=file_info.st_size,
                                content_type='image/jpeg'
                            )
                    else:
                        logger.warning(f"⚠️ Keyframe file not found: {local_path}")
                        continue
                
                # Create keyframe document
                keyframe_doc = {
                    "video_id": video_id,
                    "frame_number": frame_data.get('frame_number', i),
                    "timestamp": frame_data.get('timestamp', 0.0),
                    "quality_score": frame_data.get('quality_score', 0.0),
                    "motion_score": frame_data.get('motion_score', 0.0),
                    "minio_path": minio_path,
                    "enhancement_applied": frame_data.get('enhancement_applied', False),
                    "face_count": frame_data.get('face_count', 0),
                    "object_detections": [],
                    "created_at": datetime.utcnow()
                }
                
                result = self.collection.insert_one(keyframe_doc)
                keyframe_ids.append(str(result.inserted_id))
            
            logger.info(f"✅ Saved {len(keyframe_ids)} keyframes for video {video_id}")
            return keyframe_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save keyframes batch: {e}")
            raise
    
    def get_keyframes_by_video_id(self, video_id: str, has_detections: bool = False, 
                                limit: int = None) -> List[Dict]:
        """Get keyframes for a video with optional filtering"""
        try:
            query = {"video_id": video_id}
            
            if has_detections:
                query["object_detections"] = {"$exists": True, "$not": {"$size": 0}}
            
            cursor = self.collection.find(query).sort("timestamp", 1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            keyframes = list(cursor)
            
            # Convert ObjectIds to strings and add presigned URLs
            for kf in keyframes:
                kf = convert_objectid_to_string(kf)
                kf['presigned_url'] = self.minio.presigned_get_object(
                    self.bucket, 
                    kf['minio_path'], 
                    expires=timedelta(hours=1)
                )
            
            return keyframes
            
        except Exception as e:
            logger.error(f"❌ Failed to get keyframes for video {video_id}: {e}")
            return []
    
    def update_keyframe_detections(self, keyframe_id: str, detections: List[Dict]):
        """Update keyframe with object detection results"""
        try:
            self.collection.update_one(
                {"_id": ObjectId(keyframe_id)},
                {"$set": {
                    "object_detections": detections,
                    "updated_at": datetime.utcnow()
                }}
            )
            logger.info(f"✅ Updated keyframe {keyframe_id} with {len(detections)} detections")
        except Exception as e:
            logger.error(f"❌ Failed to update keyframe detections: {e}")

class EventRepository(BaseRepository):
    """Repository for event collection operations"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.event
    
    def save_motion_events(self, video_id: str, events: List[Dict]) -> List[str]:
        """Save motion-based events to database"""
        event_ids = []
        
        try:
            for event_data in events:
                event_doc = {
                    "video_id": video_id,
                    "event_type": "motion",
                    "start_timestamp": event_data.get('start_timestamp', 0.0),
                    "end_timestamp": event_data.get('end_timestamp', 0.0), 
                    "confidence": event_data.get('confidence', 0.0),
                    "importance_score": event_data.get('importance_score', 0.0),
                    "keyframe_paths": event_data.get('keyframes', []),
                    "threat_level": "low",
                    "is_canonical": False,
                    "created_at": datetime.utcnow()
                }
                
                result = self.collection.insert_one(event_doc)
                event_ids.append(str(result.inserted_id))
            
            logger.info(f"✅ Saved {len(event_ids)} motion events for video {video_id}")
            return event_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save motion events: {e}")
            raise
    
    def save_object_detection_events(self, video_id: str, detection_events: List[Dict]) -> List[str]:
        """Save object detection events to database"""
        event_ids = []
        
        try:
            for event_data in detection_events:
                # Calculate threat level based on detected objects
                threat_level = self._calculate_threat_level(event_data.get('object_class', ''))
                
                event_doc = {
                    "video_id": video_id,
                    "event_type": "object_detection",
                    "start_timestamp": event_data.get('start_timestamp', 0.0),
                    "end_timestamp": event_data.get('end_timestamp', 0.0),
                    "confidence": event_data.get('confidence', 0.0),
                    "importance_score": event_data.get('importance_score', 0.0),
                    "threat_level": threat_level,
                    "object_detections": event_data.get('detections', []),
                    "keyframe_paths": event_data.get('keyframe_paths', []),
                    "is_canonical": False,
                    "created_at": datetime.utcnow()
                }
                
                result = self.collection.insert_one(event_doc)
                event_ids.append(str(result.inserted_id))
            
            logger.info(f"✅ Saved {len(event_ids)} object detection events for video {video_id}")
            return event_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save object detection events: {e}")
            raise
    
    def get_events_by_video_id(self, video_id: str, event_type: str = None) -> List[Dict]:
        """Get events for a video with optional type filtering"""
        try:
            query = {"video_id": video_id}
            if event_type:
                query["event_type"] = event_type
            
            events = list(self.collection.find(query).sort("start_timestamp", 1))
            
            # Convert ObjectIds to strings
            for event in events:
                event = convert_objectid_to_string(event)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Failed to get events for video {video_id}: {e}")
            return []
    
    def _calculate_threat_level(self, object_class: str) -> str:
        """Calculate threat level based on detected object class"""
        threat_map = {
            'fire': 'critical',
            'gun': 'critical',
            'knife': 'high',
            'smoke': 'medium'
        }
        return threat_map.get(object_class.lower(), 'low')

class ProcessingJobRepository(BaseRepository):
    """Repository for processing_jobs collection operations"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.processing_jobs
    
    def create_processing_job(self, video_id: str, job_type: str = "complete_processing") -> str:
        """Create new processing job record"""
        try:
            job_doc = {
                "video_id": video_id,
                "job_type": job_type,
                "status": "queued",
                "progress": 0,
                "message": "Processing job queued",
                "created_at": datetime.utcnow()
            }
            
            result = self.collection.insert_one(job_doc)
            logger.info(f"✅ Created processing job: {video_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to create processing job: {e}")
            raise
    
    def update_job_progress(self, video_id: str, progress: int, message: str, status: str = None):
        """Update processing job progress and status"""
        try:
            update_data = {
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow()
            }
            
            if status:
                update_data["status"] = status
                if status == "processing" and not self.collection.find_one({"video_id": video_id, "started_at": {"$exists": True}}):
                    update_data["started_at"] = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    update_data["completed_at"] = datetime.utcnow()
            
            self.collection.update_one(
                {"video_id": video_id},
                {"$set": update_data}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to update job progress: {e}")
    
    def get_job_status(self, video_id: str) -> Optional[Dict]:
        """Get processing job status"""
        try:
            job = self.collection.find_one({"video_id": video_id})
            if job:
                return convert_objectid_to_string(job)
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get job status: {e}")
            return None

class ObjectDetectionRepository(BaseRepository):
    """Repository for object detection results"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.object_detections
    
    def save_detection_batch(self, video_id: str, detections: List[Dict]) -> List[str]:
        """Save object detection results"""
        detection_ids = []
        
        try:
            for detection in detections:
                detection_doc = {
                    "video_id": video_id,
                    "keyframe_id": ObjectId(detection.get('keyframe_id')) if detection.get('keyframe_id') else None,
                    "detection_id": f"{video_id}_{detection.get('frame_number', 0)}_{len(detection_ids)}",
                    "class_name": detection.get('class_name', ''),
                    "confidence": detection.get('confidence', 0.0),
                    "bbox": detection.get('bbox', [0, 0, 0, 0]),
                    "center_point": detection.get('center_point', [0, 0]),
                    "area": detection.get('area', 0.0),
                    "frame_timestamp": detection.get('frame_timestamp', 0.0),
                    "detection_model": detection.get('detection_model', ''),
                    "threat_level": self._calculate_threat_level(detection.get('class_name', '')),
                    "created_at": datetime.utcnow()
                }
                
                result = self.collection.insert_one(detection_doc)
                detection_ids.append(str(result.inserted_id))
            
            logger.info(f"✅ Saved {len(detection_ids)} detection results for video {video_id}")
            return detection_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save detection results: {e}")
            raise
    
    def get_detections_by_video_id(self, video_id: str, class_filter: str = None) -> List[Dict]:
        """Get object detections for a video"""
        try:
            query = {"video_id": video_id}
            if class_filter:
                query["class_name"] = class_filter
            
            detections = list(self.collection.find(query).sort("frame_timestamp", 1))
            
            # Convert ObjectIds to strings
            for detection in detections:
                detection = convert_objectid_to_string(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"❌ Failed to get detections for video {video_id}: {e}")
            return []
    
    def _calculate_threat_level(self, class_name: str) -> str:
        """Calculate threat level based on detected object class"""
        threat_map = {
            'fire': 'critical',
            'gun': 'critical',
            'knife': 'high',
            'smoke': 'medium'
        }
        return threat_map.get(class_name.lower(), 'low')
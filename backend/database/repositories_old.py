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
                
                # Upload keyframe image to MinIO using correct bucket path structure
                minio_path = f"{video_id}/frame_{frame_data['frame_number']:06d}.jpg"
                
                # Handle both file path and frame data scenarios
                if 'frame_path' in frame_data:
                    local_path = frame_data['frame_path']
                    if os.path.exists(local_path):
                        with open(local_path, 'rb') as img_file:
                            file_info = os.stat(local_path)
                            self.minio.put_object(
                                self.keyframe_bucket,
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
    """Repository for event collection operations - Schema Compliant"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.collection = self.db.event
        self.event_description_collection = self.db.event_description
    
    def save_event(self, event_data: Dict) -> str:
        """Save event matching MongoDB schema exactly"""
        try:
            import uuid
            
            # Extract required fields
            event_id = event_data.get('event_id', str(uuid.uuid4()))
            video_id = event_data['video_id']
            
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

# Keeping only repositories for schema-defined collections below:

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
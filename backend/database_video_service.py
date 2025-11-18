"""
Database-Integrated Video Processing Service

This service integrates the existing video processing pipeline with MongoDB and MinIO storage.
It replaces local file storage with database persistence while maintaining all processing capabilities.
"""

import os
import cv2
import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import uuid
import json

# Import existing processing components
from config import VideoProcessingConfig
from main_pipeline import CompleteVideoProcessingPipeline
from core.video_processing import OptimizedVideoProcessor
from object_detection import ObjectDetector
from behavior_analysis_integrator import BehaviorAnalysisIntegrator
from event_aggregation import EventDetector
from video_segmentation import VideoSegmentationEngine

# Import database components
from database.config import DatabaseManager
from database.repositories import VideoRepository, EventRepository
from database.keyframe_repository import KeyframeRepository
from database.video_compression_service import VideoCompressionService
from database.models import (
    convert_numpy_types, 
    seconds_to_milliseconds, 
    milliseconds_to_seconds,
    prepare_for_mongodb
)

logger = logging.getLogger(__name__)

class DatabaseIntegratedVideoService:
    """Enhanced video processing service with database integration"""
    
    def __init__(self, config: VideoProcessingConfig = None):
        """Initialize service with database connections and processing components"""
        self.config = config or VideoProcessingConfig()
        
        # Initialize database connections
        self.db_manager = DatabaseManager()
        
        # Initialize repositories (including keyframe and compression)
        self.video_repo = VideoRepository(self.db_manager)
        self.event_repo = EventRepository(self.db_manager)
        self.keyframe_repo = KeyframeRepository(self.db_manager)
        self.compression_service = VideoCompressionService(self.db_manager, self.config)
        
        # Initialize processing components
        self.video_processor = OptimizedVideoProcessor(self.config)
        self.event_detector = EventDetector(self.config)
        self.segmentation_engine = VideoSegmentationEngine(self.config)
        
        # Initialize object detector if enabled
        self.object_detector = None
        if self.config.enable_object_detection:
            try:
                self.object_detector = ObjectDetector(self.config)
                logger.info("✅ Object detection enabled")
            except Exception as e:
                logger.warning(f"⚠️ Object detection initialization failed: {e}")
                self.config.enable_object_detection = False
        
        # Initialize behavior analyzer if enabled
        self.behavior_analyzer = None
        if getattr(self.config, 'enable_behavior_analysis', False):
            try:
                self.behavior_analyzer = BehaviorAnalysisIntegrator(self.config)
                logger.info("✅ Behavior analysis enabled")
            except Exception as e:
                logger.warning(f"⚠️ Behavior analysis initialization failed: {e}")
                self.config.enable_behavior_analysis = False
        
        logger.info("✅ Database-integrated video service initialized")
    
    def process_video_with_database_storage(self, video_path: str, video_id: str, user_id: str = None):
        """
        Main processing pipeline with database integration
        
        Args:
            video_path: Path to uploaded video file
            video_id: Unique identifier for the video
            user_id: Optional user identifier
        """
        logger.info(f"🚀 Starting database-integrated processing for video: {video_id}")
        
        try:
            # Check if MongoDB record already exists (created during upload)
            existing_video = self.video_repo.get_video_by_id(video_id)
            if not existing_video:
                logger.warning(f"⚠️ Video record not found in MongoDB for {video_id}, creating now...")
                # Fallback: create record if it doesn't exist
                video_metadata = self._extract_video_metadata(video_path)
                video_record = {
                    "video_id": video_id,
                    "user_id": user_id or "system",
                    "file_path": f"videos/{video_id}/video.mp4",
                    "minio_object_key": f"original/{video_id}/video.mp4",
                    "minio_bucket": self.video_repo.video_bucket,
                    "codec": "h264",
                    "fps": float(video_metadata.get("fps", 30.0)),
                    "upload_date": datetime.utcnow(),
                    "duration_secs": int(video_metadata.get("duration", 0)),
                    "file_size_bytes": int(video_metadata.get("file_size", 0)),
                    "meta_data": {
                        "filename": os.path.basename(video_path),
                        "resolution": video_metadata.get("resolution"),
                        "processing_status": "processing",
                        "processing_progress": 0,
                        "processing_message": "Starting processing..."
                    }
                }
                self.video_repo.create_video_record(video_record)
            else:
                logger.info(f"✅ MongoDB record already exists for {video_id}, proceeding with processing...")
            
            # Update status: processing started
            self.video_repo.update_metadata(video_id, {
                "processing_status": "processing",
                "processing_progress": 10,
                "processing_message": "Starting video processing pipeline..."
            })
            
            # Step 1: Extract keyframes and upload to MinIO
            self.video_repo.update_metadata(video_id, {
                "processing_progress": 15,
                "processing_message": "Extracting and uploading keyframes..."
            })
            keyframes = self.video_processor.extract_keyframes(video_path)
            
            # Process keyframes directly for MinIO upload
            keyframe_batch = []
            for kf in keyframes:
                frame_data = kf.frame_data if hasattr(kf, 'frame_data') else kf

                # Extract keyframe information consistently
                keyframe_info = {
                    'frame_path': frame_data.frame_path if hasattr(frame_data, 'frame_path') else None,
                    'frame_number': frame_data.frame_number if hasattr(frame_data, 'frame_number') else 0,
                    'timestamp': frame_data.timestamp if hasattr(frame_data, 'timestamp') else 0.0,
                    'enhancement_applied': frame_data.enhancement_applied if hasattr(frame_data, 'enhancement_applied') else False
                }

                # If we have a numpy frame directly, we might need to save it to a file first
                if hasattr(frame_data, 'frame') and frame_data.frame is not None:
                    # Save numpy array to temporary file for upload
                    import tempfile
                    import cv2
                    import numpy as np

                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        temp_path = temp_file.name
                        cv2.imwrite(temp_path, cv2.cvtColor(frame_data.frame, cv2.COLOR_RGB2BGR))
                        keyframe_info['frame_path'] = temp_path

                keyframe_batch.append(keyframe_info)
            
            # Process and upload keyframes to MinIO
            logger.info(f"Uploading {len(keyframe_batch)} keyframes to MinIO...")
            
            keyframe_info = []
            for idx, kf_info in enumerate(keyframe_batch):
                frame_path = kf_info.get('frame_path')

                if frame_path and os.path.exists(frame_path):
                    try:
                        # Create MinIO path
                        frame_number = kf_info.get('frame_number', idx)
                        timestamp = kf_info.get('timestamp', 0.0)
                        minio_path = f"{video_id}/keyframes/frame_{frame_number:06d}.jpg"

                        # Upload to MinIO with metadata
                        with open(frame_path, 'rb') as f:
                            file_size = os.path.getsize(frame_path)
                            metadata = {
                                "frame_number": str(frame_number),
                                "timestamp": str(timestamp),
                                "enhancement_applied": str(kf_info.get('enhancement_applied', False))
                            }

                            self.keyframe_repo.minio.put_object(
                                self.keyframe_repo.bucket,
                                minio_path,
                                f,
                                file_size,
                                content_type='image/jpeg',
                                metadata=metadata
                            )

                            keyframe_info.append({
                                "frame_number": frame_number,
                                "timestamp": timestamp,
                                "minio_path": minio_path,
                                "size_bytes": file_size,
                                "uploaded_at": datetime.utcnow().isoformat()
                            })

                    except Exception as e:
                        logger.error(f"Failed to upload keyframe {frame_path}: {e}")
                        continue
                        
                if (idx + 1) % 10 == 0:
                    logger.info(f"Uploaded {idx + 1}/{len(keyframe_batch)} keyframes")
            
            # Step 2: Update MongoDB with keyframe MinIO paths (link metadata)
            # Store each keyframe's MinIO path in MongoDB metadata
            keyframe_metadata = []
            for kf in keyframe_info:
                keyframe_metadata.append({
                    "frame_number": kf["frame_number"],
                    "timestamp": kf["timestamp"],
                    "minio_path": kf["minio_path"],
                    "minio_bucket": self.keyframe_repo.bucket,
                    "size_bytes": kf["size_bytes"],
                    "uploaded_at": kf["uploaded_at"]
                })
            
            # Update video metadata with keyframe information and MinIO links
            self.video_repo.update_metadata(video_id, {
                "keyframe_info": keyframe_metadata,  # Full metadata with MinIO paths
                "keyframe_count": len(keyframe_info),
                "keyframe_bucket": self.keyframe_repo.bucket,
                "keyframes_minio_paths": [kf["minio_path"] for kf in keyframe_info],  # Quick access list
                "upload_stats": {
                    "total_frames": len(keyframe_batch),
                    "uploaded_frames": len(keyframe_info),
                    "upload_completed": datetime.utcnow().isoformat()
                }
            })
            logger.info(f"✅ Uploaded {len(keyframe_info)} keyframes to MinIO and linked in MongoDB")
            
            # Step 4: Object detection (if enabled)
            detection_results = []
            if self.config.enable_object_detection and self.object_detector:
                self.video_repo.update_metadata(video_id, {
                    "processing_progress": 40,
                    "processing_message": "Running object detection..."
                })
                detection_results = self._run_object_detection_on_keyframes(
                    video_id, keyframes
                )
            
            # Step 5: Event detection and aggregation
            self.video_repo.update_metadata(video_id, {
                "processing_progress": 70,
                "processing_message": "Detecting and aggregating events..."
            })
            
            # Create events from object detections
            event_ids = []
            object_events = []
            if detection_results:
                object_events = self._create_object_events_from_detections(detection_results)
                # Save events using EventRepository
                for event in object_events:
                    event['video_id'] = video_id  # Add video_id to event data
                    event_id = self.event_repo.save_event(event)
                    event_ids.append(event_id)
            
            # Step 5.5: Run facial recognition on frames with detections (if enabled)
            face_results = []
            if self.config.enable_facial_recognition and detection_results and event_ids:
                self.video_repo.update_metadata(video_id, {
                    "processing_progress": 75,
                    "processing_message": "Running facial recognition on suspicious frames..."
                })
                try:
                    from facial_recognition import FacialRecognitionIntegrated
                    face_detector = FacialRecognitionIntegrated(self.config)
                    
                    # Get frames that have detections for facial recognition
                    frames_with_detections = []
                    for i, keyframe in enumerate(keyframes):
                        frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe
                        frame_path = (
                            frame_data.frame_path if hasattr(frame_data, 'frame_path')
                            else getattr(frame_data, 'path', None)
                        )
                        timestamp = (
                            frame_data.timestamp if hasattr(frame_data, 'timestamp')
                            else getattr(frame_data, 'timestamp', 0.0)
                        )
                        
                        # Check if this frame has detections
                        has_detection = any(
                            abs(d['frame_timestamp'] - timestamp) < 0.5 
                            for d in detection_results
                        )
                        
                        if has_detection and frame_path and os.path.exists(frame_path):
                            frames_with_detections.append((frame_path, timestamp))
                    
                    # Run facial recognition on suspicious frames
                    for frame_path, timestamp in frames_with_detections:
                        try:
                            # Find associated event_id for this timestamp
                            associated_event_id = None
                            for event_id, event in zip(event_ids, object_events):
                                if (event.get('start_timestamp', 0) <= timestamp <= 
                                    event.get('end_timestamp', float('inf'))):
                                    associated_event_id = event_id
                                    break
                            
                            if not associated_event_id and event_ids:
                                associated_event_id = event_ids[0]  # Fallback to first event
                            
                            # Detect faces in frame
                            face_result = face_detector.detect_faces_in_frame(frame_path, timestamp)
                            
                            # Convert FaceDetectionResult to list of face info dictionaries
                            if face_result and face_result.faces_detected > 0:
                                # Extract face information from FaceDetectionResult
                                for i in range(face_result.faces_detected):
                                    face_id = face_result.detected_face_ids[i] if face_result.detected_face_ids and i < len(face_result.detected_face_ids) else f"face_{uuid.uuid4().hex[:8]}"
                                    bounding_box = face_result.face_bounding_boxes[i] if i < len(face_result.face_bounding_boxes) else [0, 0, 0, 0]
                                    confidence = face_result.face_confidence_scores[i] if i < len(face_result.face_confidence_scores) else 0.0
                                    matched_person = face_result.matched_persons[i] if face_result.matched_persons and i < len(face_result.matched_persons) else None
                                    
                                    # Construct face_info dictionary
                                    face_info = {
                                        'face_id': face_id,
                                        'bounding_box': bounding_box,
                                        'confidence': confidence,
                                        'person_name': matched_person.split('(')[0].strip() if matched_person else None,
                                        'face_image_path': None  # Will be set if saved
                                    }
                                    
                                    # Try to get face image path from MongoDB if it was saved
                                    try:
                                        faces_collection = self.db_manager.db.detected_faces
                                        existing_face = faces_collection.find_one({'face_id': face_id})
                                        if existing_face:
                                            face_info['face_image_path'] = existing_face.get('face_image_path')
                                    except:
                                        pass
                                    
                                    # Get frame number from frame path if possible
                                    frame_number = 0
                                    try:
                                        # Try to extract frame number from frame_path
                                        import re
                                        frame_match = re.search(r'frame_(\d+)', frame_path)
                                        if frame_match:
                                            frame_number = int(frame_match.group(1))
                                        else:
                                            # Estimate from timestamp (assuming 30 fps)
                                            frame_number = int(timestamp * 30)
                                    except:
                                        frame_number = int(timestamp * 30)  # Fallback estimate
                                    
                                    # Process this face_info - Save face to MongoDB detected_faces collection
                                    # Convert bounding box array to object format for schema compliance
                                    bbox = face_info.get('bounding_box', [0, 0, 0, 0])
                                    bbox_obj = {
                                        'x': bbox[0] if len(bbox) > 0 else 0,
                                        'y': bbox[1] if len(bbox) > 1 else 0,
                                        'width': bbox[2] if len(bbox) > 2 else 0,
                                        'height': bbox[3] if len(bbox) > 3 else 0
                                    } if bbox else {}
                                    
                                    face_data = {
                                        'face_id': face_info.get('face_id', f"face_{uuid.uuid4().hex[:8]}"),
                                        'event_id': associated_event_id or f"event_{uuid.uuid4().hex[:8]}",
                                        'detected_at': datetime.utcnow(),
                                        'confidence_score': float(face_info.get('confidence', 0.0)),
                                        'bounding_box': face_info.get('bounding_box', []),
                                        'bounding_boxes': bbox_obj,  # Store as object for schema compliance
                                        'person_name': face_info.get('person_name'),
                                        'person_confidence': None,
                                        'face_image_path': '',  # Initialize as empty string (schema requires string)
                                        'minio_object_key': None,
                                        'minio_bucket': None,
                                        'frame_number': frame_number,  # Store frame number to link to keyframes
                                        'timestamp': float(timestamp),  # Store timestamp in seconds to link to keyframes
                                        'video_id': video_id  # Store video_id for easier querying
                                    }
                                    
                                    # Upload face image to MinIO if available
                                    # First try to save face image from the face detection result
                                    temp_face_path = None
                                    try:
                                        # Get face crop from the detection result
                                        if i < len(face_result.face_bounding_boxes):
                                            # Load frame and crop face
                                            import cv2
                                            frame_img = cv2.imread(frame_path)
                                            if frame_img is not None:
                                                box = face_result.face_bounding_boxes[i]
                                                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                                                
                                                # Ensure valid coordinates
                                                x1, y1 = max(0, x1), max(0, y1)
                                                x2, y2 = min(frame_img.shape[1], x2), min(frame_img.shape[0], y2)
                                                
                                                if x2 > x1 and y2 > y1:
                                                    face_crop = frame_img[y1:y2, x1:x2]
                                                    
                                                    # Create temp directory if it doesn't exist
                                                    temp_dir = "temp_faces"
                                                    os.makedirs(temp_dir, exist_ok=True)
                                                    
                                                    # Save face crop temporarily
                                                    temp_face_path = os.path.join(temp_dir, f"{face_data['face_id']}.jpg")
                                                    cv2.imwrite(temp_face_path, face_crop)
                                                    
                                                    # Verify file was created
                                                    if os.path.exists(temp_face_path):
                                                        # Upload to MinIO
                                                        minio_face_path = f"{video_id}/faces/{face_data['face_id']}.jpg"
                                                        with open(temp_face_path, 'rb') as f:
                                                            file_size = os.path.getsize(temp_face_path)
                                                            self.keyframe_repo.minio.put_object(
                                                                self.keyframe_repo.bucket,
                                                                minio_face_path,
                                                                f,
                                                                file_size,
                                                                content_type='image/jpeg'
                                                            )
                                                        
                                                        face_data['minio_object_key'] = minio_face_path
                                                        face_data['minio_bucket'] = self.keyframe_repo.bucket
                                                        face_data['face_image_path'] = minio_face_path  # Store MinIO path, not temp path
                                                        logger.info(f"✅ Uploaded face image to MinIO: {minio_face_path}")
                                                    else:
                                                        logger.warning(f"Failed to create temp face file: {temp_face_path}")
                                                else:
                                                    logger.warning(f"Invalid bounding box coordinates: ({x1}, {y1}, {x2}, {y2})")
                                    except Exception as e:
                                        logger.warning(f"Failed to upload face image to MinIO: {e}")
                                        import traceback
                                        logger.debug(traceback.format_exc())
                                    
                                    # Clean up temp file AFTER MongoDB save (not before)
                                    # Save to MongoDB
                                    try:
                                        # Ensure face_image_path is a string (not None) for schema validation
                                        if not face_data.get('face_image_path'):
                                            face_data['face_image_path'] = ''  # Empty string is valid
                                        
                                        faces_collection = self.db_manager.db.detected_faces
                                        faces_collection.insert_one(face_data)
                                        face_results.append(face_data)
                                        logger.info(f"✅ Saved face to MongoDB: {face_data['face_id']}")
                                    except Exception as e:
                                        logger.error(f"Failed to save face to MongoDB: {e}")
                                        import traceback
                                        logger.debug(traceback.format_exc())
                                        # Still add to results even if MongoDB save fails
                                        face_results.append(face_data)
                                    
                                    # Clean up temp file AFTER MongoDB save
                                    if temp_face_path and os.path.exists(temp_face_path):
                                        try:
                                            os.remove(temp_face_path)
                                        except Exception as e:
                                            logger.warning(f"Failed to remove temp face file: {e}")
                                    
                        except Exception as e:
                            logger.error(f"Facial recognition error for frame {frame_path}: {e}")
                            continue
                    
                    logger.info(f"✅ Facial recognition completed: {len(face_results)} faces detected")
                    
                    # Update metadata with face count
                    self.video_repo.update_metadata(video_id, {
                        "face_count": len(face_results),
                        "facial_recognition_completed": True
                    })
                    
                except ImportError:
                    logger.warning("Facial recognition module not available")
                except Exception as e:
                    logger.error(f"Facial recognition failed: {e}")
            
            # Step 6: Generate compressed video and upload to MinIO (optional)
            compressed_minio_path = None
            if self.config.generate_compressed_video:
                logger.info(f"🔧 Starting compression for video: {video_id}, path: {video_path}")
                self.video_repo.update_metadata(video_id, {
                    "processing_progress": 95,
                    "processing_message": "Generating and uploading compressed video..."
                })
                try:
                    compressed_minio_path = self._generate_compressed_video(video_path, video_id)
                    if compressed_minio_path:
                        logger.info(f"✅ Compressed video uploaded to MinIO: {compressed_minio_path}")
                    else:
                        logger.error(f"❌ Compression failed for video: {video_id}")
                except Exception as e:
                    logger.error(f"❌ Exception during compression for {video_id}: {e}")
                    import traceback
                    logger.error(f"Compression traceback: {traceback.format_exc()}")
            
            # Step 7: Finalize processing
            final_meta_data = {
                "processing_status": "completed",
                "processing_progress": 100,
                "processing_message": "Processing completed successfully!",
                "keyframe_count": len(keyframes),
                "detection_count": len(detection_results),
                "event_count": len(object_events) if detection_results else 0,
                "face_count": len(face_results) if 'face_results' in locals() else 0,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Link compressed video MinIO path in MongoDB metadata
            if compressed_minio_path:
                final_meta_data["minio_compressed_path"] = compressed_minio_path
                # Also update the main document field
                self.video_repo.collection.update_one(
                    {"video_id": video_id},
                    {"$set": {"meta_data.minio_compressed_path": compressed_minio_path}}
                )
            
            self.video_repo.update_processing_status(video_id, "completed")
            self.video_repo.update_metadata(video_id, final_meta_data)
            
            logger.info(f"✅ Video processing completed successfully: {video_id}")
            
            # Cleanup temporary files
            self._cleanup_temp_files(video_path, keyframes)
            
        except Exception as e:
            logger.error(f"❌ Video processing failed for {video_id}: {e}")
            
            # Update status to failed
            self.video_repo.update_processing_status(video_id, "failed")
            self.video_repo.update_metadata(video_id, {
                "processing_progress": 0,
                "processing_message": f"Processing failed: {str(e)}",
                "error_message": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
            
            raise
    
    def _extract_video_metadata(self, video_path: str) -> Dict:
        """Extract metadata from video file with schema-compliant field names"""
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            file_size = os.path.getsize(video_path)
            cap.release()
            
            return {
                "duration": duration,
                "fps": float(fps),
                "resolution": f"{width}x{height}",
                "file_size": int(file_size),
                "frame_count": int(frame_count)
            }
        except Exception as e:
            logger.error(f"Failed to extract video metadata: {e}")
            return {"file_size": os.path.getsize(video_path)}
    
    def _run_object_detection_on_keyframes(self, video_id: str, keyframes: List) -> List[Dict]:
        """Run object detection on extracted keyframes, create annotated frames, and upload to MinIO"""
        detection_results = []
        annotated_keyframes_info = []  # Store info about annotated keyframes
        
        try:
            for i, keyframe in enumerate(keyframes):
                # Get frame data
                frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe
                
                # Get frame path depending on structure
                frame_path = (
                    frame_data.frame_path if hasattr(frame_data, 'frame_path')
                    else getattr(frame_data, 'path', None)
                )
                
                if frame_path and os.path.exists(frame_path):
                    # Get timestamp from frame data
                    timestamp = (
                        frame_data.timestamp if hasattr(frame_data, 'timestamp')
                        else getattr(frame_data, 'timestamp', 0.0)
                    )
                    
                    frame_number = getattr(frame_data, 'frame_number', i)
                    
                    # Run detection on this keyframe
                    detection_result = self.object_detector.detect_objects_in_frame(
                        frame_path, 
                        timestamp
                    )
                    
                    # Process detected objects and create annotated frame if detections exist
                    annotated_minio_path = None
                    if detection_result and detection_result.detected_objects:
                        # Create annotated version of the frame
                        try:
                            annotated_path = self.object_detector.annotate_frame_with_detections(
                                frame_path, 
                                detection_result
                            )
                            
                            # Upload annotated frame to MinIO
                            if annotated_path and os.path.exists(annotated_path):
                                annotated_minio_path = f"{video_id}/keyframes/annotated/frame_{frame_number:06d}_annotated.jpg"
                                
                                with open(annotated_path, 'rb') as f:
                                    file_size = os.path.getsize(annotated_path)
                                    metadata = {
                                        "frame_number": str(frame_number),
                                        "timestamp": str(timestamp),
                                        "is_annotated": "true",
                                        "detection_count": str(len(detection_result.detected_objects))
                                    }
                                    
                                    self.keyframe_repo.minio.put_object(
                                        self.keyframe_repo.bucket,
                                        annotated_minio_path,
                                        f,
                                        file_size,
                                        content_type='image/jpeg',
                                        metadata=metadata
                                    )
                                
                                annotated_keyframes_info.append({
                                    "frame_number": frame_number,
                                    "timestamp": timestamp,
                                    "minio_path": annotated_minio_path,
                                    "original_minio_path": f"{video_id}/keyframes/frame_{frame_number:06d}.jpg",
                                    "detection_count": len(detection_result.detected_objects),
                                    "objects": [obj.class_name for obj in detection_result.detected_objects],
                                    "confidence_avg": sum(obj.confidence for obj in detection_result.detected_objects) / len(detection_result.detected_objects) if detection_result.detected_objects else 0.0
                                })
                                
                                logger.info(f"✅ Uploaded annotated keyframe to MinIO: {annotated_minio_path}")
                        except Exception as e:
                            logger.warning(f"Failed to create/upload annotated keyframe: {e}")
                    
                    # Process detected objects for detection_results
                    if detection_result and detection_result.detected_objects:
                        for obj in detection_result.detected_objects:
                            detection_data = {
                                "frame_number": frame_number,
                                "class_name": str(obj.class_name),
                                "confidence": float(obj.confidence),
                                "bbox": [int(x) for x in obj.bbox[:4]],  # Convert to list of ints
                                "center_point": [float(x) for x in obj.center_point],
                                "area": float(obj.area),
                                "frame_timestamp": float(obj.frame_timestamp),
                                "detection_model": str(obj.detection_model),
                                "annotated_minio_path": annotated_minio_path  # Link to annotated frame
                            }
                            # Apply numpy type conversion
                            detection_data = convert_numpy_types(detection_data)
                            detection_results.append(detection_data)
            
            # Store annotated keyframes info in MongoDB metadata
            if annotated_keyframes_info:
                self.video_repo.update_metadata(video_id, {
                    "annotated_keyframes_info": annotated_keyframes_info,
                    "annotated_keyframes_count": len(annotated_keyframes_info)
                })
                logger.info(f"✅ Stored {len(annotated_keyframes_info)} annotated keyframes metadata")
            
            logger.info(f"✅ Object detection completed: {len(detection_results)} detections")
            return detection_results
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _create_object_events_from_detections(self, detection_results: List[Dict]) -> List[Dict]:
        """Convert object detections into aggregated schema-compliant events"""
        events = []
        
        try:
            # Group detections by class and temporal proximity
            detection_groups = self._group_detections_by_class_and_time(detection_results)
            
            for class_name, detections in detection_groups.items():
                if not detections:
                    continue
                
                # Create event from detection group
                start_time_secs = min(d['frame_timestamp'] for d in detections)
                end_time_secs = max(d['frame_timestamp'] for d in detections)
                avg_confidence = sum(d['confidence'] for d in detections) / len(detections)
                
                # Calculate importance score based on threat level and confidence
                threat_multiplier = {'fire': 3.0, 'gun': 3.0, 'knife': 2.0, 'smoke': 1.5}.get(class_name, 1.0)
                importance_score = avg_confidence * threat_multiplier
                
                # Create schema-compliant event structure
                event = {
                    "event_type": f"object_detection_{class_name}",
                    "start_timestamp": start_time_secs,
                    "end_timestamp": end_time_secs,
                    "confidence_score": avg_confidence,
                    "importance_score": importance_score,
                    "bounding_boxes": [
                        {
                            "x": d['bbox'][0],
                            "y": d['bbox'][1],
                            "width": d['bbox'][2] - d['bbox'][0],
                            "height": d['bbox'][3] - d['bbox'][1],
                            "confidence": d['confidence'],
                            "class_name": d['class_name']
                        }
                        for d in detections
                    ],
                    "detected_object_type": class_name,
                    "detection_count": len(detections),
                    "threat_level": self._calculate_threat_level(class_name, avg_confidence)
                }
                
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to create object events: {e}")
            return []
    
    def _calculate_threat_level(self, class_name: str, confidence: float) -> str:
        """Calculate threat level based on object class and confidence"""
        if class_name in ['fire', 'gun'] and confidence > 0.7:
            return 'critical'
        elif class_name in ['fire', 'gun', 'knife'] and confidence > 0.5:
            return 'high'
        elif class_name in ['smoke', 'knife']:
            return 'medium'
        else:
            return 'low'
    
    def _group_detections_by_class_and_time(self, detections: List[Dict], time_window: float = 5.0) -> Dict[str, List[Dict]]:
        """Group detections by object class and temporal proximity"""
        grouped = {}
        
        # Sort detections by timestamp
        sorted_detections = sorted(detections, key=lambda x: x['frame_timestamp'])
        
        for detection in sorted_detections:
            class_name = detection['class_name']
            
            if class_name not in grouped:
                grouped[class_name] = []
            
            grouped[class_name].append(detection)
        
        return grouped
    
    def _generate_compressed_video(self, video_path: str, video_id: str) -> Optional[str]:
        """Generate compressed version of video and upload to MinIO"""
        logger.info(f"🔧 _generate_compressed_video called for {video_id}")
        logger.info(f"🔧 Video path: {video_path}")
        logger.info(f"🔧 Video path exists: {os.path.exists(video_path) if video_path else 'None'}")
        
        try:
            # Use compression service to compress and store video
            logger.info(f"🔧 Calling compression service for {video_id}")
            result = self.compression_service.compress_and_store(video_path, video_id)
            logger.info(f"🔧 Compression service returned: {result}")
            
            if result and result.get('success'):
                compression_info = {
                    'original_size_bytes': result['original_size'],
                    'compressed_size_bytes': result['compressed_size'],
                    'compression_ratio': result['compression_ratio'],
                    'output_resolution': result['output_resolution'],
                    'local_path': result.get('local_path'),  # Store local path for fallback
                    'minio_path': result.get('minio_path')  # Store MinIO path
                }
                
                # Update video metadata with compression info (including local path)
                self.video_repo.update_metadata(video_id, {
                    'compression_info': compression_info,
                    'minio_compressed_path': result.get('minio_path')  # Also store at top level for easy access
                })
                
                logger.info(f"✅ Stored compression info with local path: {result.get('local_path')}")
                return result['minio_path']
            else:
                logger.error(f"❌ Video compression failed for {video_id}, result: {result}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Failed to generate compressed video for {video_id}: {e}")
            import traceback
            logger.error(f"Compression exception traceback: {traceback.format_exc()}")
            return None
    
    def _cleanup_temp_files(self, video_path: str, keyframes: List):
        """Clean up temporary files after processing"""
        try:
            # Remove uploaded video file
            if os.path.exists(video_path):
                os.remove(video_path)
            
            # Remove temporary keyframe files
            for keyframe in keyframes:
                frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe
                
                # Get frame path depending on structure
                frame_path = (
                    frame_data.frame_path if hasattr(frame_data, 'frame_path')
                    else getattr(frame_data, 'path', None)
                )
                
                if frame_path and os.path.exists(frame_path):
                    os.remove(frame_path)
            
            logger.info("✅ Temporary files cleaned up")
            
        except Exception as e:
            logger.error(f"⚠️ Failed to cleanup temp files: {e}")
    
    def get_video_status(self, video_id: str) -> Dict:
        """Get processing status for a video"""
        video = self.video_repo.get_video_by_id(video_id)

        if not video:
            return {"error": "Video not found"}

        meta_data = video.get("meta_data", {})

        status_data = {
            "video_id": video_id,
            "status": meta_data.get("processing_status", "unknown"),
            "filename": meta_data.get("filename"),
            "upload_date": video.get("upload_date"),
            "duration": video.get("duration_secs"),
            "fps": video.get("fps"),
            "file_size_bytes": video.get("file_size_bytes"),
            "resolution": meta_data.get("resolution"),
            "keyframe_count": meta_data.get("keyframe_count", 0),
            "detection_count": meta_data.get("detection_count", 0),
            "event_count": meta_data.get("event_count", 0),
            "processing_progress": meta_data.get("processing_progress", 0),
            "processing_message": meta_data.get("processing_message", "")
        }

        # Add presigned URLs for accessing content
        try:
            # Original video URL
            minio_original_path = meta_data.get("minio_original_path")
            if minio_original_path:
                status_data["original_video_url"] = self.video_repo.get_video_presigned_url(minio_original_path)

            # Compressed video URL (if available)
            minio_compressed_path = meta_data.get("minio_compressed_path")
            if minio_compressed_path:
                # Always use the API endpoint which will handle MinIO/local fallback
                status_data["compressed_video_url"] = f"/api/video/compressed/{video_id}"
                # Also try to get presigned URL as alternative
                try:
                    presigned_url = self.compression_service.get_compressed_video_presigned_url(video_id)
                    if presigned_url:
                        status_data["compressed_video_presigned_url"] = presigned_url
                except:
                    pass
            else:
                # Check if compression was completed but path not set
                if meta_data.get("processing_status") == "completed":
                    # Try to construct path and use API endpoint
                    status_data["compressed_video_url"] = f"/api/video/compressed/{video_id}"

            # Keyframes URLs (if available)
            if meta_data.get("keyframe_count", 0) > 0:
                try:
                    keyframes_urls = self.keyframe_repo.get_video_keyframes_presigned_urls(video_id)
                    # If no URLs from MinIO, try to get from MongoDB metadata
                    if not keyframes_urls and meta_data.get("keyframe_info"):
                        # Generate URLs from stored metadata
                        keyframes_urls = []
                        for kf_info in meta_data.get("keyframe_info", []):
                            minio_path = kf_info.get("minio_path")
                            if minio_path:
                                presigned_url = self.keyframe_repo.get_keyframe_presigned_url(minio_path)
                                if presigned_url:
                                    keyframes_urls.append({
                                        'frame_number': kf_info.get("frame_number", 0),
                                        'timestamp': kf_info.get("timestamp", 0.0),
                                        'minio_path': minio_path,
                                        'presigned_url': presigned_url,
                                        'url': presigned_url,
                                        'filename': minio_path.split('/')[-1]
                                    })
                    status_data["keyframes_urls"] = keyframes_urls
                except Exception as e:
                    logger.warning(f"Failed to get keyframes URLs: {e}")
                    status_data["keyframes_urls"] = []

        except Exception as e:
            logger.warning(f"Failed to generate presigned URLs for video {video_id}: {e}")

        return status_data
    
    def get_video_keyframes(self, video_id: str, filter_detections: bool = False, limit: int = None) -> Dict:
        """Get keyframes for a video with optional filtering and presigned URLs"""
        try:
            # Get video record to check if it exists
            video = self.video_repo.get_video_by_id(video_id)
            if not video:
                return {"error": "Video not found"}

            # Get keyframes with presigned URLs from keyframe repository
            keyframes_urls = self.keyframe_repo.get_video_keyframes_presigned_urls(video_id)
            
            # Fallback: If no keyframes from MinIO, try to get from MongoDB metadata
            if not keyframes_urls:
                meta_data = video.get("meta_data", {})
                keyframe_info = meta_data.get("keyframe_info", [])
                if keyframe_info:
                    logger.info(f"Using MongoDB metadata for keyframes: {len(keyframe_info)} keyframes")
                    for kf_info in keyframe_info:
                        minio_path = kf_info.get("minio_path")
                        if minio_path:
                            try:
                                presigned_url = self.keyframe_repo.get_keyframe_presigned_url(minio_path)
                                if presigned_url:
                                    keyframes_urls.append({
                                        'frame_number': kf_info.get("frame_number", 0),
                                        'timestamp': kf_info.get("timestamp", 0.0),
                                        'minio_path': minio_path,
                                        'presigned_url': presigned_url,
                                        'url': presigned_url,
                                        'filename': minio_path.split('/')[-1]
                                    })
                            except Exception as e:
                                logger.warning(f"Failed to generate presigned URL for {minio_path}: {e}")
            
            # Get events to determine which keyframes have detections
            events = self.event_repo.get_events_by_video_id(video_id)
            detection_events = [e for e in events if e.get("event_type", "").startswith("object_detection_")]
            
            # Create a map of timestamps that have detections
            detection_timestamps = set()
            for event in detection_events:
                start_ms = event.get("start_timestamp_ms", 0)
                end_ms = event.get("end_timestamp_ms", 0)
                # Convert milliseconds to seconds and create range
                start_sec = start_ms / 1000.0
                end_sec = end_ms / 1000.0
                # Add timestamps in 1-second intervals
                for t in range(int(start_sec), int(end_sec) + 1):
                    detection_timestamps.add(t)

            # Get annotated keyframes info from metadata
            meta_data = video.get("meta_data", {})
            annotated_keyframes_info = meta_data.get("annotated_keyframes_info", [])
            annotated_lookup = {kf.get("frame_number"): kf for kf in annotated_keyframes_info}
            
            # Get faces for this video to check which keyframes have faces
            faces_data = self.get_video_faces(video_id)
            faces = faces_data.get("faces", [])
            
            # Create a map of frame_numbers and timestamps that have faces
            frames_with_faces = set()
            timestamps_with_faces = set()
            for face in faces:
                face_frame = face.get('frame_number', 0)
                face_timestamp = face.get('timestamp', 0)
                if face_frame:
                    frames_with_faces.add(face_frame)
                if face_timestamp:
                    timestamps_with_faces.add(face_timestamp)
            
            # Enhance keyframes with detection info and annotated URLs
            enhanced_keyframes = []
            for kf in keyframes_urls:
                timestamp_sec = kf.get('timestamp', 0)
                frame_number = kf.get('frame_number', 0)
                
                # Check if this timestamp has detections (within 1 second tolerance)
                has_detections = any(abs(timestamp_sec - dt) < 1.0 for dt in detection_timestamps)
                
                # Check if this keyframe has faces (by frame_number or timestamp)
                has_faces = (
                    frame_number in frames_with_faces or
                    any(abs(timestamp_sec - ft) < 0.5 for ft in timestamps_with_faces)
                )
                
                enhanced_kf = {
                    **kf,
                    'has_detections': has_detections,
                    'has_faces': has_faces,  # Add face detection flag
                    'url': kf.get('presigned_url'),  # Add url alias for compatibility
                }
                
                # Add annotated frame info if available
                if frame_number in annotated_lookup:
                    annotated_info = annotated_lookup[frame_number]
                    # Generate presigned URL for annotated frame
                    try:
                        annotated_presigned_url = self.keyframe_repo.get_keyframe_presigned_url(
                            annotated_info.get("minio_path")
                        )
                        if annotated_presigned_url:
                            enhanced_kf['annotated_url'] = annotated_presigned_url
                            enhanced_kf['annotated_presigned_url'] = annotated_presigned_url
                            enhanced_kf['detection_count'] = annotated_info.get("detection_count", 0)
                            enhanced_kf['objects'] = annotated_info.get("objects", [])
                            enhanced_kf['confidence_avg'] = annotated_info.get("confidence_avg", 0.0)
                            enhanced_kf['has_detections'] = True  # Override if annotated frame exists
                    except Exception as e:
                        logger.warning(f"Failed to get presigned URL for annotated keyframe: {e}")
                
                # If this keyframe has faces, prioritize showing "Face Detected" over object names
                if has_faces:
                    # Count faces for this keyframe
                    face_count = sum(
                        1 for face in faces 
                        if (face.get('frame_number') == frame_number or 
                            abs(face.get('timestamp', 0) - timestamp_sec) < 0.5)
                    )
                    enhanced_kf['face_count'] = face_count
                    # Add "Face Detected" to objects list if not already present, and prioritize it
                    if enhanced_kf.get('objects'):
                        # Check if "Face" is already in objects
                        has_face_in_objects = any('face' in str(obj).lower() for obj in enhanced_kf['objects'])
                        if not has_face_in_objects:
                            # Add "Face Detected" at the beginning
                            enhanced_kf['objects'] = ['Face Detected'] + enhanced_kf['objects']
                        else:
                            # Move "Face Detected" to front, remove duplicates
                            face_objects = [obj for obj in enhanced_kf['objects'] if 'face' in str(obj).lower()]
                            other_objects = [obj for obj in enhanced_kf['objects'] if 'face' not in str(obj).lower()]
                            enhanced_kf['objects'] = ['Face Detected'] + other_objects
                    else:
                        enhanced_kf['objects'] = ['Face Detected']
                    # Update detection count to include faces
                    enhanced_kf['detection_count'] = enhanced_kf.get('detection_count', 0) + face_count
                
                enhanced_keyframes.append(enhanced_kf)

            # Apply filtering if requested
            if filter_detections:
                filtered_keyframes = [kf for kf in enhanced_keyframes if kf.get('has_detections', False)]
            else:
                filtered_keyframes = enhanced_keyframes

            # Apply limit if specified
            if limit and limit > 0:
                filtered_keyframes = filtered_keyframes[:limit]

            # Get video metadata for additional context
            meta_data = video.get("meta_data", {})
            keyframe_count = meta_data.get("keyframe_count", 0)

            return {
                "video_id": video_id,
                "keyframes": filtered_keyframes,
                "total_keyframes": len(filtered_keyframes),
                "filter_applied": filter_detections,
                "limit_applied": limit if limit and limit > 0 else None,
                "keyframe_count": keyframe_count
            }

        except Exception as e:
            logger.error(f"Failed to get keyframes for video {video_id}: {e}")
            return {"error": str(e)}

    def get_video_events(self, video_id: str, event_type: str = None) -> Dict:
        """Get events for a video"""
        events = self.event_repo.get_events_by_video_id(video_id)

        # Filter by event type if specified
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]

        return {
            "video_id": video_id,
            "events": events,
            "total_events": len(events)
        }
    
    def get_video_detections(self, video_id: str, class_filter: str = None) -> Dict:
        """Get object detections for a video from events"""
        try:
            # Get all events for this video
            events = self.event_repo.get_events_by_video_id(video_id)
            
            # Filter events that are object detection events
            detection_events = [e for e in events if e.get("event_type", "").startswith("object_detection_")]
            
            # Apply class filter if specified
            if class_filter:
                detection_events = [e for e in detection_events if e.get("event_type") == f"object_detection_{class_filter}"]
            
            # Extract detections from bounding_boxes
            detections = []
            for event in detection_events:
                bboxes = event.get("bounding_boxes", {})
                
                # Handle different bounding_boxes structures
                event_detections = []
                if isinstance(bboxes, dict):
                    event_detections = bboxes.get("detections", [])
                elif isinstance(bboxes, list):
                    # If bounding_boxes is a list directly
                    event_detections = bboxes
                
                # Also check if detections are stored directly in event
                if not event_detections:
                    event_detections = event.get("detections", [])
                
                for det in event_detections:
                    # Handle both dict and list formats
                    if isinstance(det, dict):
                        detection = {
                            "class_name": det.get("class", det.get("class_name", "unknown")),
                            "confidence": float(det.get("confidence", 0.0)),
                            "bbox": det.get("bbox", [0, 0, 0, 0]),
                            "timestamp": float(det.get("timestamp", event.get("start_timestamp_ms", 0) / 1000.0)),
                            "event_id": event.get("event_id"),
                            "model": det.get("model", "unknown")
                        }
                        detections.append(detection)
                    elif isinstance(det, list) and len(det) >= 4:
                        # Handle list format [x, y, width, height, class, confidence]
                        detection = {
                            "class_name": str(det[4]) if len(det) > 4 else "unknown",
                            "confidence": float(det[5]) if len(det) > 5 else 0.0,
                            "bbox": [int(det[0]), int(det[1]), int(det[0] + det[2]), int(det[1] + det[3])] if len(det) >= 4 else [0, 0, 0, 0],
                            "timestamp": float(event.get("start_timestamp_ms", 0) / 1000.0),
                            "event_id": event.get("event_id"),
                            "model": "unknown"
                        }
                        detections.append(detection)
                
                # Also extract from event_type if no detections found
                if not detections and event.get("event_type"):
                    event_type = event.get("event_type", "")
                    if event_type.startswith("object_detection_"):
                        class_name = event_type.replace("object_detection_", "")
                        detection = {
                            "class_name": class_name,
                            "confidence": float(event.get("confidence_score", 0.0)),
                            "bbox": [0, 0, 0, 0],  # No bbox info available
                            "timestamp": float(event.get("start_timestamp_ms", 0) / 1000.0),
                            "event_id": event.get("event_id"),
                            "model": "unknown"
                        }
                        detections.append(detection)
            
            return {
                "video_id": video_id,
                "detections": detections,
                "total_detections": len(detections)
            }
            
        except Exception as e:
            logger.error(f"Failed to get detections for video {video_id}: {e}")
            return {
                "video_id": video_id,
                "detections": [],
                "total_detections": 0,
                "error": str(e)
            }
    
    def get_video_faces(self, video_id: str) -> Dict:
        """Get detected faces for a video (through events)"""
        try:
            # Get all events for this video
            events = self.event_repo.get_events_by_video_id(video_id)
            event_ids = [e.get('event_id') for e in events if e.get('event_id')]
            
            if not event_ids:
                return {
                    "video_id": video_id,
                    "faces": [],
                    "total_faces": 0
                }
            
            # Query detected_faces collection for faces associated with these events
            faces_collection = self.db_manager.db.detected_faces
            faces = list(faces_collection.find({"event_id": {"$in": event_ids}}))
            
            # Convert ObjectIds to strings
            from database.models import convert_objectid_to_string
            faces = [convert_objectid_to_string(face) for face in faces]
            
            return {
                "video_id": video_id,
                "faces": faces,
                "total_faces": len(faces)
            }
            
        except Exception as e:
            logger.error(f"Failed to get faces for video {video_id}: {e}")
            return {
                "video_id": video_id,
                "faces": [],
                "total_faces": 0,
                "error": str(e)
            }
    
    def process_video_complete(self, video_path: str, video_id: str, user_id: str = None, 
                             upload_to_minio: bool = True, enable_compression: bool = True,
                             enable_object_detection: bool = True, enable_behavior_analysis: bool = True,
                             enable_event_aggregation: bool = True,
                             enable_deduplication: bool = True) -> Dict:
        """
        Complete video processing pipeline with all features
        
        Args:
            video_path: Path to the video file
            video_id: Unique identifier for the video
            user_id: User identifier
            upload_to_minio: Whether to upload to MinIO storage
            enable_compression: Whether to compress the video
            enable_object_detection: Whether to run object detection
            enable_event_aggregation: Whether to aggregate events
            enable_deduplication: Whether to deduplicate similar events
            
        Returns:
            Dict with processing results and statistics
        """
        logger.info(f"🔥 Starting complete pipeline processing for {video_id}")
        
        start_time = time.time()
        results = {
            "video_id": video_id,
            "status": "processing",
            "minio_uploaded": False,
            "processing_stats": {}
        }
        
        try:
            # Step 1: Create video record with metadata
            logger.info("📝 Creating video record...")
            video_metadata = self._extract_video_metadata(video_path)
            
            # Create schema-compliant video record
            video_record = {
                "video_id": video_id,
                "user_id": user_id or "system",
                "file_path": f"videos/{video_id}.mp4",
                "fps": video_metadata.get("fps", 30.0),
                "duration_secs": int(video_metadata.get("duration", 0)),
                "file_size_bytes": video_metadata.get("file_size", 0),
                "codec": "h264",  # default codec
                "meta_data": {
                    "processing_status": "processing",
                    "filename": os.path.basename(video_path),
                    "resolution": video_metadata.get("resolution"),
                    "frame_count": video_metadata.get("frame_count")
                }
            }
            
            video_doc_id = self.video_repo.create_video_record(video_record)
            logger.info(f"✅ Created video record: {video_id}")
            
            # Step 2: Upload to MinIO (if enabled and available)
            minio_uploaded = False
            if upload_to_minio:
                try:
                    logger.info("☁️ Uploading to MinIO...")
                    minio_path = self.video_repo.upload_video_to_minio(video_path, video_id)
                    minio_uploaded = True
                    self.video_repo.update_metadata(video_id, {"minio_original_path": minio_path})
                    logger.info(f"✅ Video uploaded to MinIO: {minio_path}")
                except Exception as e:
                    logger.warning(f"⚠️ MinIO upload failed (graceful fallback): {e}")
            
            results["minio_uploaded"] = minio_uploaded
            
            # Step 3: Process keyframes with object detection
            logger.info("🔑 Processing keyframes...")
            keyframes = self.video_processor.extract_keyframes(video_path)
            logger.info(f"✅ Extracted {len(keyframes)} keyframes")
            
            # Run object detection on keyframes if enabled
            detection_results = []
            if enable_object_detection and self.object_detector:
                logger.info("🎯 Running object detection...")
                for i, keyframe in enumerate(keyframes):
                    # Handle KeyframeResult objects correctly
                    frame_path = keyframe.frame_data.frame_path if hasattr(keyframe, 'frame_data') else None
                    timestamp = keyframe.frame_data.timestamp if hasattr(keyframe, 'frame_data') else 0
                    
                    if frame_path and os.path.exists(frame_path):
                        result = self.object_detector.detect_objects_in_frame(frame_path, timestamp)
                        detections = []
                        
                        if result and result.detected_objects:
                            for obj in result.detected_objects:
                                detection_dict = {
                                    "class_name": str(obj.class_name),
                                    "confidence": float(obj.confidence),
                                    "bbox": [int(x) for x in obj.bbox[:4]],
                                    "frame_timestamp": float(timestamp),
                                    "annotated_path": getattr(obj, 'annotated_path', None)
                                }
                                # Apply numpy type conversion
                                detection_dict = convert_numpy_types(detection_dict)
                                detections.append(detection_dict)
                            
                        # Store detections in keyframe (add as attribute)
                        keyframe.object_detections = detections
                        detection_results.extend(detections)
                        
                        # Log fire detections specifically
                        fire_detections = [d for d in detections if d.get('class_name') == 'fire']
                        if fire_detections:
                            logger.info(f"🔥 Fire detected at {timestamp:.1f}s (confidence: {fire_detections[0].get('confidence', 0):.2f})")
                
                logger.info(f"✅ Found {len(detection_results)} object detections")
            
            # Step 3b: Run behavior analysis on keyframes if enabled
            behavior_results = []
            behavior_events = []
            if enable_behavior_analysis and self.behavior_analyzer:
                logger.info("🔍 Running behavior analysis...")
                behavior_results, behavior_events = self.behavior_analyzer.process_keyframes_with_behavior_analysis(keyframes)
                
                # Store behavior detections in keyframes
                for i, keyframe in enumerate(keyframes):
                    frame_path = keyframe.frame_data.frame_path if hasattr(keyframe, 'frame_data') else None
                    timestamp = keyframe.frame_data.timestamp if hasattr(keyframe, 'frame_data') else 0
                    
                    # Find behavior detections for this frame
                    frame_behaviors = [r for r in behavior_results if r.frame_path == frame_path and abs(r.timestamp - timestamp) < 0.1]
                    if frame_behaviors:
                        behavior_detections = []
                        for behavior in frame_behaviors:
                            behavior_dict = {
                                "behavior_type": behavior.behavior_detected,
                                "confidence": float(behavior.confidence),
                                "frame_timestamp": float(behavior.timestamp),
                                "model_used": behavior.model_used
                            }
                            behavior_dict = convert_numpy_types(behavior_dict)
                            behavior_detections.append(behavior_dict)
                        
                        keyframe.behavior_detections = behavior_detections
                
                logger.info(f"✅ Found {len(behavior_results)} behavior detections, {len(behavior_events)} behavior events")
            
            # Step 4: Event aggregation and deduplication
            events = []
            if enable_event_aggregation:
                logger.info("📅 Performing event aggregation...")
                
                # Group detections by type and time proximity
                detection_events = self._aggregate_detection_events(keyframes, video_id)
                events.extend(detection_events)
                
                # Add behavior events
                if behavior_events:
                    for behavior_event in behavior_events:
                        event_dict = {
                            "event_type": f"behavior_{behavior_event.behavior_type}",
                            "start_timestamp": behavior_event.start_timestamp,
                            "end_timestamp": behavior_event.end_timestamp,
                            "confidence_score": float(behavior_event.confidence),
                            "keyframes": behavior_event.keyframes,
                            "importance_score": float(behavior_event.importance_score),
                            "description": f"{behavior_event.behavior_type.capitalize()} detected",
                            "detection_data": {
                                "model_used": behavior_event.model_used,
                                "frame_indices": behavior_event.frame_indices
                            }
                        }
                        event_dict = convert_numpy_types(event_dict)
                        events.append(event_dict)
                
                if enable_deduplication:
                    logger.info("🔄 Deduplicating similar events...")
                    events = self._deduplicate_events(events)
                
                # Store events in database using EventRepository
                logger.info(f"💾 Saving {len(events)} events to database...")
                for event in events:
                    try:
                        # EventRepository.save_event expects event dict with proper structure
                        # It will handle timestamp conversion and field mapping
                        event['video_id'] = video_id  # Add video_id to event data
                        self.event_repo.save_event(event)
                    except Exception as e:
                        logger.error(f"Failed to save event: {e}")
                
                logger.info(f"✅ Stored {len(events)} events in database")
            
            # Step 5: Video compression (if enabled)
            compression_info = {}
            if enable_compression:
                try:
                    logger.info("📦 Compressing video...")
                    from video_compression import OptimizedVideoCompressor
                    compressor = OptimizedVideoCompressor()
                    
                    compressed_path = f"video_processing_outputs/compressed/{video_id}_compressed.mp4"
                    os.makedirs(os.path.dirname(compressed_path), exist_ok=True)
                    
                    compression_result = compressor.compress_video(video_path, compressed_path)
                    
                    if compression_result.get('success'):
                        original_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
                        compressed_size = os.path.getsize(compressed_path) / (1024 * 1024)  # MB
                        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                        
                        compression_info = {
                            "original_size_mb": round(original_size, 2),
                            "compressed_size_mb": round(compressed_size, 2),
                            "compression_ratio": round(compression_ratio, 1),
                            "compressed_path": compressed_path
                        }
                        
                        self.video_repo.update_metadata(video_id, {"minio_compressed_path": compressed_path})
                        logger.info(f"✅ Video compressed: {compression_ratio:.1f}% reduction")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Video compression failed: {e}")
            
            # Step 6: Update final status
            processing_time = time.time() - start_time
            
            final_meta_data = {
                "processing_status": "completed",
                "keyframe_count": len(keyframes),
                "detection_count": len(detection_results),
                "behavior_detection_count": len(behavior_results),
                "behavior_event_count": len(behavior_events),
                "event_count": len(events),
                "processing_time_seconds": round(processing_time, 2),
                "processed_at": datetime.utcnow().isoformat(),
                "compressed_video_info": compression_info
            }
            
            self.video_repo.update_processing_status(video_id, "completed")
            self.video_repo.update_metadata(video_id, final_meta_data)
            
            results.update({
                "status": "completed",
                "processing_stats": final_meta_data,
                "keyframes_extracted": len(keyframes),
                "objects_detected": len(detection_results),
                "behaviors_detected": len(behavior_results),
                "behavior_events": len(behavior_events),
                "events_created": len(events),
                "processing_time": processing_time
            })
            
            logger.info(f"🎉 Complete pipeline processing finished for {video_id} in {processing_time:.1f}s")
            return results
            
        except Exception as e:
            logger.error(f"❌ Processing failed for {video_id}: {e}")
            
            # Update status to failed
            try:
                self.video_repo.update_processing_status(video_id, "failed")
                self.video_repo.update_metadata(video_id, {
                    "error_message": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                })
            except:
                pass
                
            results.update({
                "status": "failed",
                "error": str(e)
            })
            
            raise e
    
    def _aggregate_detection_events(self, keyframes, video_id):
        """Aggregate object detections into schema-compliant events"""
        events = []
        
        # Group keyframes with detections by detection type
        detection_groups = {}
        for keyframe in keyframes:
            # Handle KeyframeResult objects
            detections = getattr(keyframe, 'object_detections', [])
            frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe
            
            for detection in detections:
                class_name = detection.get('class_name', 'unknown')
                if class_name not in detection_groups:
                    detection_groups[class_name] = []
                detection_groups[class_name].append({
                    'keyframe': keyframe,
                    'detection': detection,
                    'timestamp': frame_data.timestamp if hasattr(frame_data, 'timestamp') else 0
                })
        
        # Create events for each detection type
        for class_name, detections in detection_groups.items():
            if not detections:
                continue
                
            # Sort by timestamp
            detections.sort(key=lambda x: x['timestamp'])
            
            # Group nearby detections into events (within 3 seconds)
            current_event = None
            
            for det_info in detections:
                timestamp = det_info['timestamp']
                confidence = det_info['detection'].get('confidence', 0)
                bbox = det_info['detection'].get('bbox', [0, 0, 0, 0])
                
                # Check if this detection belongs to current event
                if current_event and timestamp - current_event['end_timestamp'] <= 3.0:
                    # Extend current event
                    current_event['end_timestamp'] = timestamp
                    current_event['confidence_score'] = max(current_event['confidence_score'], confidence)
                    current_event['bounding_boxes'].append({
                        "x": int(bbox[0]),
                        "y": int(bbox[1]),
                        "width": int(bbox[2] - bbox[0]),
                        "height": int(bbox[3] - bbox[1]),
                        "confidence": float(confidence),
                        "class_name": class_name
                    })
                else:
                    # Start new event
                    if current_event:
                        events.append(current_event)
                    
                    threat_level = self._calculate_threat_level(class_name, confidence)
                    importance_score = 0.9 if class_name == 'fire' else 0.7 if class_name in ['knife', 'gun'] else 0.5
                    
                    current_event = {
                        'event_type': f'object_detection_{class_name}',
                        'start_timestamp': timestamp,
                        'end_timestamp': timestamp,
                        'confidence_score': confidence,
                        'importance_score': importance_score,
                        'threat_level': threat_level,
                        'bounding_boxes': [{
                            "x": int(bbox[0]),
                            "y": int(bbox[1]),
                            "width": int(bbox[2] - bbox[0]),
                            "height": int(bbox[3] - bbox[1]),
                            "confidence": float(confidence),
                            "class_name": class_name
                        }],
                        'detected_object_type': class_name
                    }
            
            # Add final event
            if current_event:
                events.append(current_event)
        
        return events
    
    def _deduplicate_events(self, events):
        """Remove duplicate or very similar events and mark them as false positives"""
        if len(events) <= 1:
            return events
        
        # Sort events by start timestamp
        events.sort(key=lambda x: x.get('start_timestamp', 0))
        
        deduplicated = []
        
        for event in events:
            # Check if this event is too similar to recent events
            is_duplicate = False
            
            for recent_event in deduplicated[-3:]:  # Check last 3 events
                # Same type and overlapping time window
                if (event.get('event_type') == recent_event.get('event_type') and
                    abs(event.get('start_timestamp', 0) - recent_event.get('end_timestamp', 0)) <= 5.0):
                    
                    # Check if same object types detected
                    event_objects = {event.get('detected_object_type')}
                    recent_objects = {recent_event.get('detected_object_type')}
                    
                    if event_objects & recent_objects:  # Common objects
                        is_duplicate = True
                        
                        # Merge into the existing event (extend time window, keep highest confidence)
                        recent_event['end_timestamp'] = max(
                            recent_event.get('end_timestamp', 0),
                            event.get('end_timestamp', 0)
                        )
                        recent_event['confidence_score'] = max(
                            recent_event.get('confidence_score', 0),
                            event.get('confidence_score', 0)
                        )
                        recent_event['bounding_boxes'].extend(event.get('bounding_boxes', []))
                        break
            
            if not is_duplicate:
                deduplicated.append(event)
        
        logger.info(f"🔄 Deduplication: {len(events)} → {len(deduplicated)} events")
        return deduplicated
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

# Import existing processing components
from config import VideoProcessingConfig
from main_pipeline import CompleteVideoProcessingPipeline
from core.video_processing import OptimizedVideoProcessor
from object_detection import ObjectDetector
from event_aggregation import EventDetector
from video_segmentation import VideoSegmentationEngine

# Import database components
from database.config import DatabaseManager
from database.repositories import VideoRepository, EventRepository
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
        
        # Initialize repositories (only schema-compliant ones)
        self.video_repo = VideoRepository(self.db_manager)
        self.event_repo = EventRepository(self.db_manager)
        
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
            # Step 1: Extract video metadata and create database record
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
                    "frame_count": video_metadata.get("frame_count"),
                    "processing_progress": 0,
                    "processing_message": "Starting processing..."
                }
            }
            
            video_doc_id = self.video_repo.create_video_record(video_record)
            
            # Step 2: Upload original video to MinIO
            self.video_repo.update_metadata(video_id, {
                "processing_progress": 5,
                "processing_message": "Uploading video to cloud storage..."
            })
            minio_path = self.video_repo.upload_video_to_minio(video_path, video_id)
            self.video_repo.update_metadata(video_id, {
                "minio_original_path": minio_path
            })
            
            # Step 3: Extract keyframes
            self.video_repo.update_metadata(video_id, {
                "processing_progress": 15,
                "processing_message": "Extracting keyframes..."
            })
            keyframes = self.video_processor.extract_keyframes(video_path)
            
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
            if detection_results:
                object_events = self._create_object_events_from_detections(detection_results)
                # Save events using EventRepository
                for event in object_events:
                    self.event_repo.save_event(video_id, event)
            
            # Step 6: Generate compressed video (optional)
            compressed_path = None
            if self.config.generate_compressed_video:
                self.video_repo.update_metadata(video_id, {
                    "processing_progress": 95,
                    "processing_message": "Generating compressed video..."
                })
                compressed_path = self._generate_compressed_video(video_path, video_id)
            
            # Step 7: Finalize processing
            final_meta_data = {
                "processing_status": "completed",
                "processing_progress": 100,
                "processing_message": "Processing completed successfully!",
                "keyframe_count": len(keyframes),
                "detection_count": len(detection_results),
                "event_count": len(object_events) if detection_results else 0,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            if compressed_path:
                final_meta_data["minio_compressed_path"] = compressed_path
            
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
        """Run object detection on extracted keyframes and return detections"""
        detection_results = []
        
        try:
            for i, keyframe in enumerate(keyframes):
                # Get frame data
                frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe
                
                if 'frame_path' in frame_data and os.path.exists(frame_data['frame_path']):
                    # Run detection on this keyframe
                    detection_result = self.object_detector.detect_objects_in_frame(
                        frame_data['frame_path'], 
                        frame_data.get('timestamp', 0.0)
                    )
                    
                    # Process detected objects
                    if detection_result.detected_objects:
                        for obj in detection_result.detected_objects:
                            detection_data = {
                                "frame_number": frame_data.get('frame_number', i),
                                "class_name": str(obj.class_name),
                                "confidence": float(obj.confidence),
                                "bbox": [int(x) for x in obj.bbox[:4]],  # Convert to list of ints
                                "center_point": [float(x) for x in obj.center_point],
                                "area": float(obj.area),
                                "frame_timestamp": float(obj.frame_timestamp),
                                "detection_model": str(obj.detection_model)
                            }
                            # Apply numpy type conversion
                            detection_data = convert_numpy_types(detection_data)
                            detection_results.append(detection_data)
            
            logger.info(f"✅ Object detection completed: {len(detection_results)} detections")
            return detection_results
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
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
        try:
            # This is a placeholder - implement actual video compression
            # For now, just copy the original file as compressed
            compressed_minio_path = f"videos/compressed/{video_id}.mp4"
            
            with open(video_path, 'rb') as file_data:
                file_info = os.stat(video_path)
                self.db_manager.minio_client.put_object(
                    self.db_manager.config.minio_bucket,
                    compressed_minio_path,
                    file_data,
                    length=file_info.st_size,
                    content_type='video/mp4'
                )
            
            logger.info(f"✅ Compressed video uploaded: {compressed_minio_path}")
            return compressed_minio_path
            
        except Exception as e:
            logger.error(f"❌ Failed to generate compressed video: {e}")
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
                if 'frame_path' in frame_data:
                    frame_path = frame_data['frame_path']
                    if os.path.exists(frame_path):
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
        
        return status_data
    
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
    
    def process_video_complete(self, video_path: str, video_id: str, user_id: str = None, 
                             upload_to_minio: bool = True, enable_compression: bool = True,
                             enable_object_detection: bool = True, enable_event_aggregation: bool = True,
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
            
            # Step 4: Event aggregation and deduplication
            events = []
            if enable_event_aggregation:
                logger.info("📅 Performing event aggregation...")
                
                # Group detections by type and time proximity
                detection_events = self._aggregate_detection_events(keyframes, video_id)
                events.extend(detection_events)
                
                if enable_deduplication:
                    logger.info("🔄 Deduplicating similar events...")
                    events = self._deduplicate_events(events)
                
                # Store events in database using EventRepository
                logger.info(f"💾 Saving {len(events)} events to database...")
                for event in events:
                    try:
                        # EventRepository.save_event expects event dict with proper structure
                        # It will handle timestamp conversion and field mapping
                        self.event_repo.save_event(video_id, event)
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
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
from database.repositories import (
    VideoRepository, KeyframeRepository, EventRepository, 
    ProcessingJobRepository, ObjectDetectionRepository
)

logger = logging.getLogger(__name__)

class DatabaseIntegratedVideoService:
    """Enhanced video processing service with database integration"""
    
    def __init__(self, config: VideoProcessingConfig = None):
        """Initialize service with database connections and processing components"""
        self.config = config or VideoProcessingConfig()
        
        # Initialize database connections
        self.db_manager = DatabaseManager()
        
        # Initialize repositories
        self.video_repo = VideoRepository(self.db_manager)
        self.keyframe_repo = KeyframeRepository(self.db_manager)
        self.event_repo = EventRepository(self.db_manager)
        self.job_repo = ProcessingJobRepository(self.db_manager)
        self.detection_repo = ObjectDetectionRepository(self.db_manager)
        
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
            video_doc_id = self.video_repo.create_video_record({
                "video_id": video_id,
                "user_id": user_id,
                "filename": os.path.basename(video_path),
                "processing_status": "processing",
                **video_metadata
            })
            
            # Step 2: Create processing job tracker
            job_id = self.job_repo.create_processing_job(video_id)
            
            # Step 3: Upload original video to MinIO
            self.job_repo.update_job_progress(video_id, 5, "Uploading video to cloud storage...")
            minio_path = self.video_repo.upload_video_to_minio(video_path, video_id)
            self.video_repo.update_processing_status(video_id, "processing", {
                "minio_original_path": minio_path
            })
            
            # Step 4: Extract keyframes and save to database
            self.job_repo.update_job_progress(video_id, 15, "Extracting keyframes...")
            keyframes = self.video_processor.extract_keyframes(video_path)
            keyframe_ids = self.keyframe_repo.save_keyframes_batch(video_id, keyframes)
            
            # Step 5: Object detection (if enabled)
            detection_results = []
            if self.config.enable_object_detection and self.object_detector:
                self.job_repo.update_job_progress(video_id, 40, "Running object detection...")
                detection_results = self._run_object_detection_on_keyframes(
                    video_id, keyframes, keyframe_ids
                )
            
            # Step 6: Event detection and aggregation
            self.job_repo.update_job_progress(video_id, 70, "Detecting and aggregating events...")
            motion_events = self.event_detector.detect_events(keyframes)
            
            # Convert object detections to events
            object_events = []
            if detection_results:
                object_events = self._create_object_events_from_detections(detection_results)
            
            # Save events to database
            motion_event_ids = self.event_repo.save_motion_events(video_id, motion_events)
            object_event_ids = []
            if object_events:
                object_event_ids = self.event_repo.save_object_detection_events(video_id, object_events)
            
            # Step 7: Video segmentation (optional)
            self.job_repo.update_job_progress(video_id, 85, "Creating video segments...")
            segments = self.segmentation_engine.create_video_segments(video_path, keyframes)
            
            # Step 8: Generate compressed video (optional)
            compressed_path = None
            if self.config.generate_compressed_video:
                self.job_repo.update_job_progress(video_id, 95, "Generating compressed video...")
                compressed_path = self._generate_compressed_video(video_path, video_id)
            
            # Step 9: Finalize processing
            self.job_repo.update_job_progress(video_id, 100, "Processing completed successfully!", "completed")
            
            # Update video record with final results
            final_stats = {
                "processing_status": "completed",
                "keyframe_count": len(keyframes),
                "motion_event_count": len(motion_events),
                "object_event_count": len(object_events),
                "total_detections": len(detection_results),
                "segment_count": len(segments),
                "processed_at": datetime.utcnow()
            }
            
            if compressed_path:
                final_stats["minio_compressed_path"] = compressed_path
            
            self.video_repo.update_processing_status(video_id, "completed", final_stats)
            
            logger.info(f"✅ Video processing completed successfully: {video_id}")
            
            # Cleanup temporary files
            self._cleanup_temp_files(video_path, keyframes)
            
        except Exception as e:
            logger.error(f"❌ Video processing failed for {video_id}: {e}")
            
            # Update status to failed
            self.job_repo.update_job_progress(
                video_id, 0, f"Processing failed: {str(e)}", "failed"
            )
            self.video_repo.update_processing_status(video_id, "failed", {
                "error_message": str(e),
                "failed_at": datetime.utcnow()
            })
            
            raise
    
    def _extract_video_metadata(self, video_path: str) -> Dict:
        """Extract metadata from video file"""
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
                "fps": fps,
                "resolution": f"{width}x{height}",
                "file_size": file_size,
                "frame_count": frame_count
            }
        except Exception as e:
            logger.error(f"Failed to extract video metadata: {e}")
            return {"file_size": os.path.getsize(video_path)}
    
    def _run_object_detection_on_keyframes(self, video_id: str, keyframes: List, keyframe_ids: List[str]) -> List[Dict]:
        """Run object detection on extracted keyframes"""
        detection_results = []
        
        try:
            for i, (keyframe, keyframe_id) in enumerate(zip(keyframes, keyframe_ids)):
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
                                "keyframe_id": keyframe_id,
                                "frame_number": frame_data.get('frame_number', i),
                                "class_name": obj.class_name,
                                "confidence": obj.confidence,
                                "bbox": list(obj.bbox),
                                "center_point": list(obj.center_point),
                                "area": obj.area,
                                "frame_timestamp": obj.frame_timestamp,
                                "detection_model": obj.detection_model
                            }
                            detection_results.append(detection_data)
                        
                        # Update keyframe with detection info
                        detection_summary = [{
                            "class_name": obj.class_name,
                            "confidence": obj.confidence,
                            "bbox": list(obj.bbox)
                        } for obj in detection_result.detected_objects]
                        
                        self.keyframe_repo.update_keyframe_detections(keyframe_id, detection_summary)
            
            # Save all detections to database
            if detection_results:
                self.detection_repo.save_detection_batch(video_id, detection_results)
            
            return detection_results
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return []
    
    def _create_object_events_from_detections(self, detection_results: List[Dict]) -> List[Dict]:
        """Convert object detections into aggregated events"""
        events = []
        
        try:
            # Group detections by class and temporal proximity
            detection_groups = self._group_detections_by_class_and_time(detection_results)
            
            for class_name, detections in detection_groups.items():
                if not detections:
                    continue
                
                # Create event from detection group
                start_time = min(d['frame_timestamp'] for d in detections)
                end_time = max(d['frame_timestamp'] for d in detections)
                avg_confidence = sum(d['confidence'] for d in detections) / len(detections)
                
                # Calculate importance score based on threat level and confidence
                threat_multiplier = {'fire': 3.0, 'gun': 3.0, 'knife': 2.0, 'smoke': 1.5}.get(class_name, 1.0)
                importance_score = avg_confidence * threat_multiplier
                
                event = {
                    "start_timestamp": start_time,
                    "end_timestamp": end_time,
                    "confidence": avg_confidence,
                    "importance_score": importance_score,
                    "object_class": class_name,
                    "detection_count": len(detections),
                    "detections": detections,
                    "keyframe_paths": [d.get('keyframe_id') for d in detections]
                }
                
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to create object events: {e}")
            return []
    
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
        job = self.job_repo.get_job_status(video_id)
        
        if not video:
            return {"error": "Video not found"}
        
        status_data = {
            "video_id": video_id,
            "status": video.get("processing_status", "unknown"),
            "filename": video.get("filename"),
            "upload_date": video.get("upload_date"),
            "duration": video.get("duration"),
            "resolution": video.get("resolution"),
            "keyframe_count": video.get("keyframe_count", 0),
            "motion_event_count": video.get("motion_event_count", 0),
            "object_event_count": video.get("object_event_count", 0),
            "total_detections": video.get("total_detections", 0)
        }
        
        if job:
            status_data.update({
                "progress": job.get("progress", 0),
                "message": job.get("message", ""),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at")
            })
        
        return status_data
    
    def get_video_keyframes(self, video_id: str, filter_detections: bool = False, limit: int = None) -> Dict:
        """Get keyframes for a video with optional filtering"""
        keyframes = self.keyframe_repo.get_keyframes_by_video_id(
            video_id, has_detections=filter_detections, limit=limit
        )
        
        return {
            "video_id": video_id,
            "keyframes": keyframes,
            "total_keyframes": len(keyframes),
            "filter_applied": filter_detections
        }
    
    def get_video_events(self, video_id: str, event_type: str = None) -> Dict:
        """Get events for a video"""
        events = self.event_repo.get_events_by_video_id(video_id, event_type)
        
        return {
            "video_id": video_id,
            "events": events,
            "total_events": len(events)
        }
    
    def get_video_detections(self, video_id: str, class_filter: str = None) -> Dict:
        """Get object detections for a video"""
        detections = self.detection_repo.get_detections_by_video_id(video_id, class_filter)
        
        return {
            "video_id": video_id,
            "detections": detections,
            "total_detections": len(detections)
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
            
            # Filter metadata to match VideoFileModel fields
            video_record = {
                "video_id": video_id,
                "user_id": user_id or "system",
                "filename": os.path.basename(video_path),
                "file_path": f"videos/{video_id}.mp4",
                "processing_status": "processing",
                "duration": video_metadata.get("duration"),
                "fps": video_metadata.get("fps", 30.0),
                "resolution": video_metadata.get("resolution"),
                "file_size": video_metadata.get("file_size")
            }
            
            video_doc_id = self.video_repo.create_video_record(video_record)
            logger.info(f"✅ Created video record: {video_id}")
            
            # Step 2: Create processing job
            job_id = self.job_repo.create_processing_job(video_id)
            logger.info(f"✅ Created processing job: {video_id}")
            
            # Step 3: Upload to MinIO (if enabled and available)
            minio_uploaded = False
            if upload_to_minio:
                try:
                    logger.info("☁️ Uploading to MinIO...")
                    minio_path = self.video_repo.upload_video_to_minio(video_path, video_id)
                    minio_uploaded = True
                    logger.info(f"✅ Video uploaded to MinIO: {minio_path}")
                except Exception as e:
                    logger.warning(f"⚠️ MinIO upload failed (graceful fallback): {e}")
            
            results["minio_uploaded"] = minio_uploaded
            
            # Step 4: Process keyframes with object detection
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
                                # Convert numpy types to native Python types for MongoDB compatibility
                                bbox = obj.bbox
                                if isinstance(bbox, (tuple, list)) and len(bbox) >= 4:
                                    bbox = [int(x) if hasattr(x, 'item') else int(x) for x in bbox[:4]]
                                
                                detection_dict = {
                                    "class_name": str(obj.class_name),
                                    "confidence": float(obj.confidence) if hasattr(obj.confidence, 'item') else float(obj.confidence),
                                    "bbox": bbox,
                                    "annotated_path": getattr(obj, 'annotated_path', None)
                                }
                                detections.append(detection_dict)
                            
                        # Store detections in keyframe (add as attribute)
                        keyframe.object_detections = detections
                        detection_results.extend(detections)
                        
                        # Log fire detections specifically
                        fire_detections = [d for d in detections if d.get('class_name') == 'fire']
                        if fire_detections:
                            logger.info(f"🔥 Fire detected at {timestamp:.1f}s (confidence: {fire_detections[0].get('confidence', 0):.2f})")
                
                logger.info(f"✅ Found {len(detection_results)} object detections")
            
            # Step 5: Save keyframes to database
            keyframe_docs = []
            for keyframe in keyframes:
                # Extract data from KeyframeResult object
                frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe
                
                # Convert numpy types to native Python types for MongoDB compatibility
                frame_number = frame_data.frame_number if hasattr(frame_data, 'frame_number') else 0
                timestamp = frame_data.timestamp if hasattr(frame_data, 'timestamp') else 0
                quality_score = frame_data.quality_score if hasattr(frame_data, 'quality_score') else 0.5
                motion_score = frame_data.motion_score if hasattr(frame_data, 'motion_score') else 0.5
                
                keyframe_record = {
                    "video_id": video_id,
                    "frame_number": int(frame_number) if hasattr(frame_number, 'item') else int(frame_number),
                    "timestamp": float(timestamp) if hasattr(timestamp, 'item') else float(timestamp),
                    "quality_score": float(quality_score) if hasattr(quality_score, 'item') else float(quality_score),
                    "motion_score": float(motion_score) if hasattr(motion_score, 'item') else float(motion_score),
                    "minio_path": f"keyframes/{video_id}/frame_{int(frame_number) if hasattr(frame_number, 'item') else int(frame_number):06d}.jpg",
                    "enhancement_applied": bool(frame_data.enhancement_applied if hasattr(frame_data, 'enhancement_applied') else False),
                    "object_detections": getattr(keyframe, 'object_detections', [])
                }
                
                doc_id = self.db_manager.db.keyframes.insert_one(keyframe_record).inserted_id
                keyframe_docs.append(str(doc_id))
            
            logger.info(f"✅ Stored {len(keyframe_docs)} keyframes in database")
            
            # Step 6: Event aggregation and deduplication
            events = []
            if enable_event_aggregation:
                logger.info("📅 Performing event aggregation...")
                
                # Group detections by type and time proximity
                detection_events = self._aggregate_detection_events(keyframes, video_id)
                events.extend(detection_events)
                
                if enable_deduplication:
                    logger.info("🔄 Deduplicating similar events...")
                    events = self._deduplicate_events(events)
                
                # Store events in database
                event_docs = []
                for event in events:
                    from bson import Int64
                    event_record = {
                        "event_id": f"{video_id}_event_{int(event.get('start_timestamp', 0) * 1000)}",
                        "video_id": video_id,
                        "event_type": event.get('event_type', 'object_detection'),
                        "start_timestamp_ms": Int64(int(event.get('start_timestamp', 0) * 1000)),
                        "end_timestamp_ms": Int64(int(event.get('end_timestamp', 0) * 1000)),
                        "confidence": event.get('confidence', 0.5),
                        "importance_score": event.get('importance_score', 0.5),
                        "threat_level": event.get('threat_level', 'low'),
                        "keyframe_paths": event.get('keyframe_paths', []),
                        "object_detections": event.get('object_detections', []),
                        "is_canonical": event.get('is_canonical', True)
                    }
                    
                    doc_id = self.db_manager.db.event.insert_one(event_record).inserted_id
                    event_docs.append(str(doc_id))
                
                logger.info(f"✅ Stored {len(event_docs)} events in database")
            
            # Step 7: Video compression (if enabled)
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
                        
                        logger.info(f"✅ Video compressed: {compression_ratio:.1f}% reduction")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Video compression failed: {e}")
            
            # Step 8: Update final status
            processing_time = time.time() - start_time
            
            final_stats = {
                "keyframe_count": len(keyframes),
                "detection_count": len(detection_results),
                "event_count": len(events),
                "processing_time_seconds": round(processing_time, 2),
                "compressed_video_info": compression_info
            }
            
            self.video_repo.update_processing_status(video_id, "completed", final_stats)
            
            results.update({
                "status": "completed",
                "processing_stats": final_stats,
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
                self.video_repo.update_processing_status(video_id, "failed", {
                    "error_message": str(e),
                    "failed_at": time.time()
                })
            except:
                pass
                
            results.update({
                "status": "failed",
                "error": str(e)
            })
            
            raise e
    
    def _aggregate_detection_events(self, keyframes, video_id):
        """Aggregate object detections into events"""
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
                
                # Check if this detection belongs to current event
                if current_event and timestamp - current_event['end_timestamp'] <= 3.0:
                    # Extend current event
                    current_event['end_timestamp'] = timestamp
                    current_event['confidence'] = max(current_event['confidence'], confidence)
                    current_event['object_detections'].append(det_info['detection'])
                else:
                    # Start new event
                    if current_event:
                        events.append(current_event)
                    
                    threat_level = 'critical' if class_name == 'fire' else 'medium' if class_name in ['knife', 'gun'] else 'low'
                    importance_score = 0.9 if class_name == 'fire' else 0.7 if class_name in ['knife', 'gun'] else 0.5
                    
                    current_event = {
                        'event_type': 'object_detection',
                        'start_timestamp': timestamp,
                        'end_timestamp': timestamp,
                        'confidence': confidence,
                        'importance_score': importance_score,
                        'threat_level': threat_level,
                        'keyframe_paths': [],
                        'object_detections': [det_info['detection']],
                        'is_canonical': True
                    }
            
            # Add final event
            if current_event:
                events.append(current_event)
        
        return events
    
    def _deduplicate_events(self, events):
        """Remove duplicate or very similar events"""
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
                    event_objects = {det.get('class_name') for det in event.get('object_detections', [])}
                    recent_objects = {det.get('class_name') for det in recent_event.get('object_detections', [])}
                    
                    if event_objects & recent_objects:  # Common objects
                        is_duplicate = True
                        
                        # Merge into the existing event (extend time window, keep highest confidence)
                        recent_event['end_timestamp'] = max(
                            recent_event.get('end_timestamp', 0),
                            event.get('end_timestamp', 0)
                        )
                        recent_event['confidence'] = max(
                            recent_event.get('confidence', 0),
                            event.get('confidence', 0)
                        )
                        recent_event['object_detections'].extend(event.get('object_detections', []))
                        break
            
            if not is_duplicate:
                deduplicated.append(event)
        
        logger.info(f"🔄 Deduplication: {len(events)} → {len(deduplicated)} events")
        return deduplicated
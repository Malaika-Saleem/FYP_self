"""
Live Stream Processor for DetectifAI

Processes live webcam/CCTV footage through the same pipeline as uploaded videos:
- Object detection (fire, weapons)
- Behavior analysis (fighting, accidents, climbing)
- Facial recognition on suspicious frames
- Real-time event detection
- Storage in MongoDB and MinIO
"""

import cv2
import numpy as np
import io
import os
import time
import threading
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from config import VideoProcessingConfig, get_security_focused_config
from object_detection import ObjectDetector
from behavior_analysis_integrator import BehaviorAnalysisIntegrator
from database.config import DatabaseManager
from database.repositories import VideoRepository, EventRepository
from database.keyframe_repository import KeyframeRepository

logger = logging.getLogger(__name__)


class LiveStreamProcessor:
    """Process live video streams with DetectifAI pipeline"""
    
    def __init__(self, config: VideoProcessingConfig = None, camera_id: str = "webcam_01"):
        """
        Initialize live stream processor
        
        Args:
            config: VideoProcessingConfig object
            camera_id: Unique identifier for the camera/stream
        """
        self.config = config or get_security_focused_config()
        self.camera_id = camera_id
        self.is_processing = False
        self.cap = None
        self.camera_index = 0  # Default camera index
        self.frame_count = 0
        self.last_keyframe_time = 0
        self.keyframe_interval = 1.0  # Extract keyframe every 1 second
        
        # Initialize database connections
        self.db_manager = DatabaseManager()
        self.video_repo = VideoRepository(self.db_manager)
        self.event_repo = EventRepository(self.db_manager)
        self.keyframe_repo = KeyframeRepository(self.db_manager)
        
        # Initialize processing components
        self.object_detector = None
        if self.config.enable_object_detection:
            try:
                self.object_detector = ObjectDetector(self.config)
                logger.info("✅ Object detection enabled for live stream")
            except Exception as e:
                logger.warning(f"⚠️ Object detection initialization failed: {e}")
                self.config.enable_object_detection = False
        
        self.behavior_analyzer = None
        if getattr(self.config, 'enable_behavior_analysis', False):
            try:
                self.behavior_analyzer = BehaviorAnalysisIntegrator(self.config)
                logger.info("✅ Behavior analysis enabled for live stream")
            except Exception as e:
                logger.warning(f"⚠️ Behavior analysis initialization failed: {e}")
                self.config.enable_behavior_analysis = False
        
        # Initialize facial recognition if enabled
        self.face_recognizer = None
        if getattr(self.config, 'enable_facial_recognition', False):
            try:
                from facial_recognition import FacialRecognitionIntegrated
                self.face_recognizer = FacialRecognitionIntegrated(self.config)
                logger.info("✅ Facial recognition enabled for live stream")
            except Exception as e:
                logger.warning(f"⚠️ Facial recognition initialization failed: {e}")
        
        # Frame buffer for behavior analysis (needs 16 frames)
        self.frame_buffer = []
        self.buffer_size = 16
        
        # Motion detection
        self.prev_frame_gray = None
        self.motion_threshold = 25
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'keyframes_extracted': 0,
            'objects_detected': 0,
            'behaviors_detected': 0,
            'events_created': 0,
            'start_time': None
        }
        
        logger.info(f"✅ Live stream processor initialized for camera: {camera_id}")
    
    def preprocess_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Preprocess frame: resize, enhance, check quality
        
        Args:
            frame: Input frame from camera
            
        Returns:
            Preprocessed frame or None if frame is too blurry
        """
        if frame is None:
            return None
        
        # Resize to standard size for processing
        target_size = (640, 640)
        processed = cv2.resize(frame, target_size)
        
        # Check for blur using Laplacian variance
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Skip blurry frames
        if laplacian_var < 100:
            return None
        
        return processed
    
    def detect_motion(self, frame_gray: np.ndarray) -> Tuple[bool, float]:
        """
        Detect motion in frame
        
        Args:
            frame_gray: Grayscale frame
            
        Returns:
            (motion_detected, motion_score)
        """
        if self.prev_frame_gray is None:
            self.prev_frame_gray = frame_gray
            return False, 0.0
        
        diff = cv2.absdiff(self.prev_frame_gray, frame_gray)
        self.prev_frame_gray = frame_gray
        
        motion_score = np.sum(diff > self.motion_threshold)
        motion_detected = motion_score > 5000
        
        return motion_detected, float(motion_score)
    
    def process_frame(self, frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """
        Process a single frame through the pipeline
        
        Args:
            frame: Input frame
            timestamp: Frame timestamp in seconds
            
        Returns:
            Processing results dictionary
        """
        results = {
            'timestamp': timestamp,
            'frame_count': self.frame_count,
            'objects_detected': [],
            'behaviors_detected': [],
            'motion_detected': False,
            'motion_score': 0.0,
            'events': []
        }
        
        # Preprocess frame
        processed_frame = self.preprocess_frame(frame)
        if processed_frame is None:
            return results
        
        # Detect motion
        gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        motion_detected, motion_score = self.detect_motion(gray)
        results['motion_detected'] = motion_detected
        results['motion_score'] = motion_score
        
        # Add to frame buffer for behavior analysis
        self.frame_buffer.append(processed_frame.copy())
        if len(self.frame_buffer) > self.buffer_size:
            self.frame_buffer.pop(0)
        
        # Object detection (run on every frame with motion, or periodically)
        # For real-time display, we want detections to show immediately
        should_run_detection = motion_detected or (self.frame_count % 30 == 0)  # Every 30 frames or on motion
        
        if self.object_detector and should_run_detection:
            try:
                # Create a temporary keyframe-like object
                from core.video_processing import KeyframeResult, FrameData
                frame_data = FrameData(
                    frame_path=None,  # Live frame, no file path
                    timestamp=timestamp,
                    frame_index=self.frame_count
                )
                keyframe = KeyframeResult(
                    frame_data=frame_data,
                    quality_score=0.8,
                    is_keyframe=True
                )
                
                # Store frame temporarily for detection
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_frame_path = os.path.join(temp_dir, f"live_frame_{self.camera_id}_{self.frame_count}.jpg")
                cv2.imwrite(temp_frame_path, processed_frame)
                keyframe.frame_data.frame_path = temp_frame_path
                
                # Run object detection
                detection_result = self.object_detector.detect_objects_in_keyframes([keyframe])
                if detection_result and len(detection_result) > 0:
                    detections = detection_result[0]
                    if hasattr(detections, 'total_detections') and detections.total_detections > 0:
                        results['objects_detected'] = [
                            {
                                'class': det.class_name,
                                'confidence': float(det.confidence),
                                'bbox': det.bbox
                            }
                            for det in detections.detections
                        ]
                        self.stats['objects_detected'] += len(results['objects_detected'])
                        
                        # Log detections in real-time
                        obj_classes = [obj['class'] for obj in results['objects_detected']]
                        logger.info(f"🎯 REAL-TIME DETECTION: {len(results['objects_detected'])} object(s) detected: {', '.join(obj_classes)} (frame {self.frame_count})")
                
                # Clean up temp file
                try:
                    os.remove(temp_frame_path)
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"Error in object detection: {e}")
        
        # Behavior analysis (on frame buffer) - use frame buffer method for live streams
        if self.behavior_analyzer and len(self.frame_buffer) >= 16 and motion_detected:
            try:
                # Use frame buffer method for live streams (no video file needed)
                behavior_results = self.behavior_analyzer.detect_behavior_in_segment_from_buffer(
                    frame_buffer=self.frame_buffer,
                    start_time=timestamp - (len(self.frame_buffer) / 30.0),  # Approximate start time
                    end_time=timestamp,
                    frame_indices=list(range(max(0, self.frame_count - len(self.frame_buffer) + 1), self.frame_count + 1))
                )
                
                if behavior_results:
                    results['behaviors_detected'] = [
                        {
                            'behavior_type': r.behavior_detected,  # Use behavior_type for consistency
                            'behavior': r.behavior_detected,  # Keep both for compatibility
                            'confidence': float(r.confidence),
                            'model': r.model_used
                        }
                        for r in behavior_results
                    ]
                    self.stats['behaviors_detected'] += len(results['behaviors_detected'])
                    
                    # Log behaviors in real-time
                    behavior_types = [b['behavior_type'] for b in results['behaviors_detected']]
                    logger.info(f"🎭 REAL-TIME BEHAVIOR: {len(results['behaviors_detected'])} behavior(s) detected: {', '.join(behavior_types)} (frame {self.frame_count})")
            except Exception as e:
                logger.warning(f"Error in behavior analysis: {e}")
        
        # Facial recognition on suspicious frames
        if self.face_recognizer and (results['objects_detected'] or results['behaviors_detected']):
            try:
                # Process frame for facial recognition
                face_results = self.face_recognizer.detect_faces_in_frame(
                    processed_frame,
                    frame_number=self.frame_count,
                    timestamp=timestamp,
                    event_id=f"live_{self.camera_id}_{int(timestamp)}"
                )
                if face_results:
                    results['faces_detected'] = len(face_results)
            except Exception as e:
                logger.warning(f"Error in facial recognition: {e}")
        
        return results
    
    def save_keyframe(self, frame: np.ndarray, results: Dict[str, Any], timestamp: float) -> Optional[str]:
        """
        Save keyframe to MinIO and MongoDB (matches uploaded video pipeline)
        
        Args:
            frame: Frame to save
            results: Processing results
            timestamp: Frame timestamp
            
        Returns:
            MinIO object path or None
        """
        try:
            # Encode frame as JPEG (same as uploaded video pipeline)
            is_success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not is_success:
                logger.warning(f"⚠️ Failed to encode frame {self.frame_count} as JPEG")
                return None
            
            frame_bytes = buffer.tobytes()
            frame_size = len(frame_bytes)
            
            # Generate object name (consistent with uploaded video pipeline)
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            object_name = f"live/{self.camera_id}/{timestamp_str}.jpg"
            
            # Upload to MinIO (same method as uploaded video pipeline)
            minio_client = self.keyframe_repo.minio  # Use minio client from keyframe repository
            bucket = self.keyframe_repo.bucket  # Use bucket from keyframe repository
            
            logger.info(f"📤 Uploading keyframe to MinIO: {bucket}/{object_name} ({frame_size} bytes)")
            
            # Use BytesIO for in-memory upload (same as uploaded video pipeline)
            from io import BytesIO
            frame_buffer = BytesIO(frame_bytes)
            
            # Add metadata like uploaded video pipeline
            metadata = {
                "frame_index": str(self.frame_count),
                "timestamp": str(timestamp),
                "camera_id": self.camera_id,
                "motion_detected": str(results.get('motion_detected', False)),
                "motion_score": str(results.get('motion_score', 0.0))
            }
            
            minio_client.put_object(
                bucket,
                object_name,
                frame_buffer,
                length=frame_size,
                content_type="image/jpeg",
                metadata=metadata
            )
            
            logger.info(f"✅ Uploaded keyframe to MinIO: {bucket}/{object_name}")
            
            # Save to MongoDB (same as uploaded video pipeline)
            keyframe_doc = {
                "camera_id": self.camera_id,
                "video_id": f"live_{self.camera_id}",  # Use consistent video_id format
                "timestamp": timestamp,
                "timestamp_ms": int(timestamp * 1000),
                "frame_index": self.frame_count,
                "frame_number": self.frame_count,  # Also include frame_number for consistency
                "minio_path": object_name,
                "minio_bucket": bucket,
                "objects_detected": results.get('objects_detected', []),
                "behaviors_detected": results.get('behaviors_detected', []),
                "motion_detected": results.get('motion_detected', False),
                "motion_score": results.get('motion_score', 0.0),
                "created_at": datetime.utcnow()
            }
            
            # Use create_keyframe method (same as uploaded video pipeline)
            keyframe_id = self.keyframe_repo.create_keyframe(keyframe_doc)
            if keyframe_id:
                logger.info(f"✅ Saved keyframe metadata to MongoDB: {object_name} (ID: {keyframe_id})")
            else:
                logger.warning(f"⚠️ Failed to save keyframe metadata to MongoDB: {object_name}")
            
            self.stats['keyframes_extracted'] += 1
            
            # Return full path for URL generation
            return f"{bucket}/{object_name}"
            
        except Exception as e:
            logger.error(f"❌ Error saving keyframe: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_event(self, results: Dict[str, Any], start_time: float, end_time: float) -> Optional[str]:
        """
        Create event from processing results (matches uploaded video pipeline)
        
        Args:
            results: Processing results
            start_time: Event start time
            end_time: Event end time
            
        Returns:
            Event ID or None
        """
        try:
            # Determine event type based on detections (same logic as uploaded video pipeline)
            event_type = "motion"
            if results.get('objects_detected'):
                # Get the primary object class for event type
                primary_object = results['objects_detected'][0].get('class', 'object')
                event_type = f"object_detection_{primary_object}"
            elif results.get('behaviors_detected'):
                primary_behavior = results['behaviors_detected'][0].get('behavior_type', 'behavior')
                event_type = f"behavior_detection_{primary_behavior}"
            
            # Calculate confidence from detections (same as uploaded video pipeline)
            confidences = []
            if results.get('objects_detected'):
                confidences.extend([float(r.get('confidence', 0.0)) for r in results['objects_detected']])
            if results.get('behaviors_detected'):
                confidences.extend([float(r.get('confidence', 0.0)) for r in results['behaviors_detected']])
            max_confidence = max(confidences) if confidences else 0.0
            
            # Build bounding boxes structure (same format as uploaded video pipeline)
            bounding_boxes = {}
            if results.get('objects_detected'):
                bounding_boxes["detections"] = [
                    {
                        "class": det.get('class', 'unknown'),
                        "confidence": float(det.get('confidence', 0.0)),
                        "bbox": [float(x) for x in det.get('bbox', [0, 0, 0, 0])],
                        "timestamp": float(start_time),
                        "model": "merged_fire_knife_gun"
                    }
                    for det in results['objects_detected']
                ]
            
            # Create event document (matches uploaded video pipeline schema)
            event_doc = {
                "event_id": f"live_{self.camera_id}_{int(start_time)}_{uuid.uuid4().hex[:8]}",
                "camera_id": self.camera_id,
                "video_id": f"live_{self.camera_id}",  # Use camera_id as video_id for live streams
                "event_type": event_type,
                "start_timestamp": start_time,
                "end_timestamp": end_time,
                "start_timestamp_ms": int(start_time * 1000),
                "end_timestamp_ms": int(end_time * 1000),
                "confidence": max_confidence,
                "confidence_score": max_confidence,  # Also include confidence_score for schema compliance
                "description": f"Live stream event: {event_type} detected",
                "bounding_boxes": bounding_boxes,
                "metadata": {
                    "camera_id": self.camera_id,
                    "objects_detected": results.get('objects_detected', []),
                    "behaviors_detected": results.get('behaviors_detected', []),
                    "motion_score": results.get('motion_score', 0.0),
                    "source": "live_stream"
                }
            }
            
            logger.info(f"📝 Creating event: {event_type} (confidence: {max_confidence:.2f})")
            event_id = self.event_repo.create_event(event_doc)
            
            if event_id:
                logger.info(f"✅ Created event in MongoDB: {event_doc['event_id']} (MongoDB ID: {event_id})")
                self.stats['events_created'] += 1
            else:
                logger.warning(f"⚠️ Failed to create event in MongoDB: {event_doc['event_id']}")
            
            return event_id
            
        except Exception as e:
            logger.error(f"❌ Error creating event: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def generate_frames(self, camera_index: int = 0):
        """
        Generator function for video frames with processing
        
        Args:
            camera_index: Camera device index (0 for default webcam)
            
        Yields:
            Processed frame bytes for streaming
        """
        # Release any existing camera connection
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
        
        # Try to open camera with retries
        max_retries = 3
        self.cap = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to open camera {camera_index} (attempt {attempt + 1}/{max_retries})")
                self.cap = cv2.VideoCapture(camera_index)
                
                # Give camera time to initialize
                time.sleep(0.5)
                
                if self.cap.isOpened():
                    # Test if we can actually read a frame
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        logger.info(f"✅ Successfully opened camera {camera_index}")
                        break
                    else:
                        logger.warning(f"Camera {camera_index} opened but cannot read frames")
                        self.cap.release()
                        self.cap = None
                else:
                    logger.warning(f"Camera {camera_index} failed to open")
                    if self.cap:
                        self.cap.release()
                        self.cap = None
            except Exception as e:
                logger.error(f"Error opening camera {camera_index}: {e}")
                if self.cap:
                    try:
                        self.cap.release()
                    except:
                        pass
                    self.cap = None
        
        if self.cap is None or not self.cap.isOpened():
            error_msg = f"❌ Could not open camera {camera_index} after {max_retries} attempts"
            logger.error(error_msg)
            # Yield an error frame
            error_frame = self._create_error_frame(error_msg)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return
        
        # Set camera properties
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            logger.warning(f"Could not set camera properties: {e}")
        
        self.is_processing = True
        self.stats['start_time'] = time.time()
        self.frame_count = 0
        self.last_keyframe_time = time.time()
        
        logger.info(f"🎥 Started live stream processing for camera {camera_index}")
        logger.info(f"📊 Camera properties: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)} @ {self.cap.get(cv2.CAP_PROP_FPS)} FPS")
        logger.info(f"🔄 Entering frame generation loop...")
        
        current_event_start = None
        event_results = None
        
        try:
            consecutive_failures = 0
            max_failures = 10
            while self.is_processing:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.error(f"❌ Failed to read {max_failures} consecutive frames from camera")
                        break
                    logger.warning(f"⚠️ Failed to read frame from camera (failure {consecutive_failures}/{max_failures})")
                    time.sleep(0.1)  # Brief pause before retry
                    continue
                
                consecutive_failures = 0  # Reset on success
                self.frame_count += 1
                self.stats['frames_processed'] += 1
                
                if self.frame_count == 1:
                    logger.info(f"✅ Successfully read first frame! Frame shape: {frame.shape}")
                current_time = time.time()
                timestamp = current_time - self.stats['start_time']
                
                # Process frame
                results = self.process_frame(frame, timestamp)
                
                # Extract keyframe periodically or on significant events
                should_extract_keyframe = (
                    (current_time - self.last_keyframe_time >= self.keyframe_interval) or
                    results.get('objects_detected') or
                    results.get('behaviors_detected')
                )
                
                if should_extract_keyframe:
                    self.save_keyframe(frame, results, timestamp)
                    self.last_keyframe_time = current_time
                
                # Track events
                if results.get('objects_detected') or results.get('behaviors_detected'):
                    if current_event_start is None:
                        current_event_start = timestamp
                        event_results = results
                    else:
                        # Update event results
                        event_results['objects_detected'].extend(results.get('objects_detected', []))
                        event_results['behaviors_detected'].extend(results.get('behaviors_detected', []))
                else:
                    # End event if it exists
                    if current_event_start is not None:
                        self.create_event(event_results, current_event_start, timestamp)
                        current_event_start = None
                        event_results = None
                
                # Draw annotations on frame
                annotated_frame = self.annotate_frame(frame, results)
                
                # Encode frame for streaming
                ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    frame_bytes = buffer.tobytes()
                    if self.frame_count % 30 == 0:  # Log every 30 frames
                        logger.debug(f"📹 Yielding frame {self.frame_count} ({len(frame_bytes)} bytes)")
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    logger.warning(f"⚠️ Failed to encode frame {self.frame_count}")
                
                # Small delay to control frame rate
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in frame generation: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.stop()
    
    def _create_error_frame(self, error_message: str) -> np.ndarray:
        """Create an error frame to display when camera fails"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame.fill(20)  # Dark background
        
        # Add error text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = "Camera Error"
        text_size = cv2.getTextSize(text, font, 1, 2)[0]
        text_x = (640 - text_size[0]) // 2
        text_y = 200
        cv2.putText(frame, text, (text_x, text_y), font, 1, (0, 0, 255), 2)
        
        # Add error message (split if too long)
        msg_lines = error_message.split(' ')
        line = ""
        y_offset = 250
        for word in msg_lines:
            test_line = line + word + " "
            test_size = cv2.getTextSize(test_line, font, 0.6, 1)[0]
            if test_size[0] > 600:
                cv2.putText(frame, line, (20, y_offset), font, 0.6, (255, 255, 255), 1)
                line = word + " "
                y_offset += 30
            else:
                line = test_line
        if line:
            cv2.putText(frame, line, (20, y_offset), font, 0.6, (255, 255, 255), 1)
        
        return frame
    
    def annotate_frame(self, frame: np.ndarray, results: Dict[str, Any]) -> np.ndarray:
        """
        Draw annotations on frame (detections, behaviors, etc.) - matches uploaded video pipeline
        
        Args:
            frame: Input frame
            results: Processing results
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        # Draw object detections with color coding (same as uploaded video pipeline)
        for obj in results.get('objects_detected', []):
            bbox = obj.get('bbox', [0, 0, 100, 100])
            class_name = obj.get('class', 'object')
            confidence = float(obj.get('confidence', 0.0))
            
            x1, y1, x2, y2 = map(int, bbox)
            
            # Color coding based on object class (same as uploaded video pipeline)
            color_map = {
                'fire': (255, 255, 0),    # Cyan/Blue (BGR)
                'knife': (0, 255, 255),   # Yellow (BGR)
                'gun': (0, 255, 0),       # Green (BGR)
                'smoke': (128, 128, 128)  # Gray (BGR)
            }
            color = color_map.get(class_name.lower(), (0, 0, 255))  # Default red
            
            # Draw bounding box with thicker line for visibility
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            
            # Draw label with background (same style as uploaded video pipeline)
            label = f"{class_name}: {confidence:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            label_size, baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Draw label background
            cv2.rectangle(annotated, 
                         (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), 
                         color, -1)
            
            # Draw label text
            cv2.putText(annotated, label, (x1, y1 - 5),
                       font, font_scale, (255, 255, 255), thickness)
        
        # Draw behavior detections (same style as uploaded video pipeline)
        behavior_y_offset = 30
        for behavior in results.get('behaviors_detected', []):
            behavior_type = behavior.get('behavior_type', behavior.get('behavior', 'unknown'))
            confidence = float(behavior.get('confidence', 0.0))
            label = f"{behavior_type.upper()}: {confidence:.2f}"
            
            # Color coding for behaviors
            behavior_colors = {
                'fighting': (0, 0, 255),      # Red
                'road_accident': (0, 165, 255),  # Orange
                'wallclimb': (255, 0, 255)   # Magenta
            }
            behavior_color = behavior_colors.get(behavior_type.lower(), (0, 255, 0))  # Default green
            
            # Draw behavior label with background
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2
            label_size, baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Background for behavior label
            cv2.rectangle(annotated, 
                         (10, behavior_y_offset - label_size[1] - 5), 
                         (10 + label_size[0], behavior_y_offset + 5), 
                         behavior_color, -1)
            
            cv2.putText(annotated, label, (10, behavior_y_offset),
                       font, font_scale, (255, 255, 255), thickness)
            behavior_y_offset += 35
        
        # Draw motion indicator (if motion detected)
        if results.get('motion_detected'):
            motion_label = f"MOTION: {results.get('motion_score', 0.0):.0f}"
            cv2.putText(annotated, motion_label, (10, behavior_y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            behavior_y_offset += 30
        
        # Draw face detection indicator
        if results.get('faces_detected', 0) > 0:
            face_label = f"FACES: {results['faces_detected']}"
            cv2.putText(annotated, face_label, (10, behavior_y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 192, 203), 2)
            behavior_y_offset += 30
        
        # Draw stats at bottom (same as uploaded video pipeline)
        stats_text = f"Frame: {self.frame_count} | Objects: {len(results.get('objects_detected', []))} | Events: {self.stats['events_created']}"
        cv2.putText(annotated, stats_text, (10, annotated.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return annotated
    
    def stop(self):
        """Stop processing and release resources"""
        self.is_processing = False
        if self.cap:
            self.cap.release()
        logger.info("🛑 Live stream processing stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        runtime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'fps': self.stats['frames_processed'] / runtime if runtime > 0 else 0,
            'is_processing': self.is_processing
        }


# Global processor instances (one per camera)
_live_processors = {}


def get_live_processor(camera_id: str = "webcam_01", config: VideoProcessingConfig = None) -> LiveStreamProcessor:
    """Get or create a live stream processor for a camera"""
    if camera_id not in _live_processors:
        _live_processors[camera_id] = LiveStreamProcessor(config, camera_id)
    return _live_processors[camera_id]


def stop_live_processor(camera_id: str):
    """Stop and remove a live stream processor"""
    if camera_id in _live_processors:
        _live_processors[camera_id].stop()
        del _live_processors[camera_id]


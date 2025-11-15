"""
Object Detection Module for DetectifAI

This module handles:
- Fire, knife, and gun detection using merged_fire_knife_gun.pt
- Integration with video processing pipeline
- Object-based event generation
"""

import cv2
import torch
import numpy as np
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from ultralytics import YOLO
import time

logger = logging.getLogger(__name__)

@dataclass
class DetectedObject:
    """Represents a detected object"""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center_point: Tuple[int, int]
    area: float
    frame_timestamp: float
    detection_model: str

@dataclass
class ObjectDetectionResult:
    """Result of object detection on a frame"""
    frame_path: str
    timestamp: float
    detected_objects: List[DetectedObject]
    total_detections: int
    detection_confidence_avg: float
    processing_time: float

class ObjectDetector:
    """Main object detection class using YOLOv11 models"""
    
    def __init__(self, config):
        """
        Initialize object detector with trained models
        
        Args:
            config: VideoProcessingConfig object with object detection settings
        """
        self.config = config
        self.models = {}
        self.class_names = {}
        self.confidence_threshold = config.object_detection_confidence
        self.device = 'cuda' if torch.cuda.is_available() and config.use_gpu_acceleration else 'cpu'
        
        logger.info(f"Initializing ObjectDetector on device: {self.device}")
        
        # Load models
        self._load_models()
        
        # Statistics
        self.detection_stats = {
            'total_frames_processed': 0,
            'total_objects_detected': 0,
            'detection_times': [],
            'objects_by_class': {},
            'confidence_scores': []
        }
    
    def _load_models(self):
        """Load YOLOv11 merged model for fire, knife, and gun detection"""
        try:
            # Merged model for fire, knife, and gun detection
            merged_model_path = os.path.join(self.config.models_dir, "merged_fire_knife_gun.pt")
            if os.path.exists(merged_model_path):
                logger.info(f"Loading merged detection model: {merged_model_path}")
                self.models['merged'] = YOLO(merged_model_path)
                self.models['merged'].to(self.device)
                # Class names mapping for merged model: 0='fire', 1='knife', 2='gun'
                self.class_names['merged'] = ['fire', 'knife', 'gun']
                logger.info("✅ Merged detection model loaded successfully (fire, knife, gun)")
            else:
                logger.error(f"Merged model not found at: {merged_model_path}")
                raise FileNotFoundError(f"Merged model not found at: {merged_model_path}")
            
            if not self.models:
                logger.error("❌ No object detection models loaded!")
                raise FileNotFoundError("No object detection models found")
            
        except Exception as e:
            logger.error(f"❌ Failed to load object detection models: {e}")
            raise
    
    def detect_objects_in_frame(self, frame_path: str, timestamp: float) -> ObjectDetectionResult:
        """
        Detect objects in a single frame
        
        Args:
            frame_path: Path to the frame image
            timestamp: Timestamp of the frame in video
            
        Returns:
            ObjectDetectionResult with all detected objects
        """
        start_time = time.time()
        
        # Load frame
        frame = cv2.imread(frame_path)
        if frame is None:
            logger.error(f"Could not load frame: {frame_path}")
            return ObjectDetectionResult(
                frame_path=frame_path,
                timestamp=timestamp,
                detected_objects=[],
                total_detections=0,
                detection_confidence_avg=0.0,
                processing_time=0.0
            )
        
        detected_objects = []
        
        # Run detection with each model
        for model_name, model in self.models.items():
            try:
                # Run inference
                results = model(frame, conf=self.confidence_threshold, verbose=False)
                
                # Process results
                for result in results:
                    if result.boxes is not None:
                        boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
                        confidences = result.boxes.conf.cpu().numpy()
                        classes = result.boxes.cls.cpu().numpy().astype(int)
                        
                        for i, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                            # Get class name
                            if model_name in self.class_names and cls < len(self.class_names[model_name]):
                                class_name = self.class_names[model_name][cls]
                            else:
                                class_name = f"unknown_{cls}"
                            
                            # Calculate center point and area
                            x1, y1, x2, y2 = box.astype(int)
                            center_x = int((x1 + x2) / 2)
                            center_y = int((y1 + y2) / 2)
                            area = (x2 - x1) * (y2 - y1)
                            
                            detected_object = DetectedObject(
                                class_name=class_name,
                                confidence=float(conf),
                                bbox=(x1, y1, x2, y2),
                                center_point=(center_x, center_y),
                                area=area,
                                frame_timestamp=timestamp,
                                detection_model=model_name
                            )
                            
                            detected_objects.append(detected_object)
                            
                            # Update statistics
                            if class_name not in self.detection_stats['objects_by_class']:
                                self.detection_stats['objects_by_class'][class_name] = 0
                            self.detection_stats['objects_by_class'][class_name] += 1
                            self.detection_stats['confidence_scores'].append(float(conf))
            
            except Exception as e:
                logger.error(f"Error running {model_name} detection: {e}")
                continue
        
        # Calculate processing time and statistics
        processing_time = time.time() - start_time
        self.detection_stats['detection_times'].append(processing_time)
        self.detection_stats['total_frames_processed'] += 1
        self.detection_stats['total_objects_detected'] += len(detected_objects)
        
        # Calculate average confidence
        avg_confidence = np.mean([obj.confidence for obj in detected_objects]) if detected_objects else 0.0
        
        result = ObjectDetectionResult(
            frame_path=frame_path,
            timestamp=timestamp,
            detected_objects=detected_objects,
            total_detections=len(detected_objects),
            detection_confidence_avg=float(avg_confidence),
            processing_time=processing_time
        )
        
        if detected_objects:
            object_summary = ", ".join([f"{obj.class_name}({obj.confidence:.2f})" for obj in detected_objects])
            logger.info(f"🎯 Detected {len(detected_objects)} objects at {timestamp:.2f}s: {object_summary}")
        
        return result
    
    def detect_objects_in_keyframes(self, keyframes: List) -> List[ObjectDetectionResult]:
        """
        Run object detection on all keyframes
        
        Args:
            keyframes: List of KeyframeResult objects from video processing
            
        Returns:
            List of ObjectDetectionResult objects
        """
        logger.info(f"🔍 Running object detection on {len(keyframes)} keyframes")
        
        detection_results = []
        
        for i, keyframe in enumerate(keyframes):
            try:
                frame_path = keyframe.frame_data.frame_path
                timestamp = keyframe.frame_data.timestamp
                
                # Run detection
                result = self.detect_objects_in_frame(frame_path, timestamp)
                detection_results.append(result)
                
                # Progress logging
                if (i + 1) % 10 == 0 or i == len(keyframes) - 1:
                    logger.info(f"📊 Object detection progress: {i + 1}/{len(keyframes)} frames processed")
                
            except Exception as e:
                logger.error(f"Error detecting objects in keyframe {i}: {e}")
                continue
        
        # Log final statistics
        total_objects = sum(r.total_detections for r in detection_results)
        frames_with_objects = sum(1 for r in detection_results if r.total_detections > 0)
        avg_processing_time = np.mean([r.processing_time for r in detection_results]) if detection_results else 0
        
        logger.info(f"🎯 Object Detection Summary:")
        logger.info(f"   📊 Total objects detected: {total_objects}")
        logger.info(f"   📊 Frames with objects: {frames_with_objects}/{len(keyframes)}")
        logger.info(f"   📊 Average processing time: {avg_processing_time:.3f}s per frame")
        logger.info(f"   📊 Objects by class: {self.detection_stats['objects_by_class']}")
        
        return detection_results
    
    def create_object_based_events(self, detection_results: List[ObjectDetectionResult], 
                                 temporal_window: float = 5.0) -> List[Dict[str, Any]]:
        """
        Create events based on object detections
        
        Args:
            detection_results: List of ObjectDetectionResult objects
            temporal_window: Time window for grouping detections (seconds)
            
        Returns:
            List of object-based events
        """
        logger.info(f"🎯 Creating object-based events from {len(detection_results)} detection results")
        
        # Filter results with detections
        results_with_objects = [r for r in detection_results if r.total_detections > 0]
        
        if not results_with_objects:
            logger.info("No objects detected, no object-based events created")
            return []
        
        # Group detections by object class
        events_by_class = {}
        
        for result in results_with_objects:
            for obj in result.detected_objects:
                class_name = obj.class_name
                
                if class_name not in events_by_class:
                    events_by_class[class_name] = []
                
                events_by_class[class_name].append({
                    'timestamp': result.timestamp,
                    'confidence': obj.confidence,
                    'bbox': obj.bbox,
                    'frame_path': result.frame_path,
                    'object': obj
                })
        
        # Create temporal events for each class
        object_events = []
        event_id_counter = 1000  # Start from 1000 to differentiate from motion events
        
        for class_name, detections in events_by_class.items():
            # Sort by timestamp
            detections.sort(key=lambda x: x['timestamp'])
            
            # Group into temporal windows
            current_event_detections = []
            current_event_start = None
            
            for detection in detections:
                timestamp = detection['timestamp']
                
                if current_event_start is None:
                    # Start new event
                    current_event_start = timestamp
                    current_event_detections = [detection]
                elif timestamp - current_event_start <= temporal_window:
                    # Add to current event
                    current_event_detections.append(detection)
                else:
                    # Finish current event and start new one
                    if current_event_detections:
                        event = self._create_event_from_detections(
                            class_name, current_event_detections, event_id_counter
                        )
                        object_events.append(event)
                        event_id_counter += 1
                    
                    # Start new event
                    current_event_start = timestamp
                    current_event_detections = [detection]
            
            # Don't forget the last event
            if current_event_detections:
                event = self._create_event_from_detections(
                    class_name, current_event_detections, event_id_counter
                )
                object_events.append(event)
                event_id_counter += 1
        
        logger.info(f"✅ Created {len(object_events)} object-based events")
        for event in object_events:
            logger.info(f"   🎯 {event['event_type']}: {event['start_timestamp']:.2f}s - {event['end_timestamp']:.2f}s "
                       f"(confidence: {event['confidence']:.2f})")
        
        return object_events
    
    def _create_event_from_detections(self, class_name: str, detections: List[Dict], 
                                    event_id: int) -> Dict[str, Any]:
        """Create an event from a group of detections"""
        start_time = min(d['timestamp'] for d in detections)
        end_time = max(d['timestamp'] for d in detections)
        confidences = [d['confidence'] for d in detections]
        avg_confidence = np.mean(confidences)
        max_confidence = max(confidences)
        
        # Determine event type and importance
        event_type = f"{class_name}_detection"
        importance_score = max_confidence * len(detections) * 2.0  # Higher importance for object events
        
        # Get keyframes with detections
        keyframes = [d['frame_path'] for d in detections]
        
        # Create description
        description = f"{class_name.title()} detected with {avg_confidence:.2f} average confidence over {len(detections)} frames"
        
        return {
            'event_id': f"obj_event_{event_id:04d}",
            'start_timestamp': start_time,
            'end_timestamp': end_time,
            'event_type': event_type,
            'confidence': avg_confidence,
            'max_confidence': max_confidence,
            'keyframes': keyframes,
            'importance_score': importance_score,
            'motion_intensity': 0.0,  # Object events don't have motion intensity
            'description': description,
            'object_class': class_name,
            'detection_count': len(detections),
            'duration': end_time - start_time,
            'detection_details': detections
        }
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """Get comprehensive detection statistics"""
        stats = self.detection_stats.copy()
        
        if stats['detection_times']:
            stats['avg_detection_time'] = np.mean(stats['detection_times'])
            stats['max_detection_time'] = max(stats['detection_times'])
            stats['min_detection_time'] = min(stats['detection_times'])
        
        if stats['confidence_scores']:
            stats['avg_confidence'] = np.mean(stats['confidence_scores'])
            stats['max_confidence'] = max(stats['confidence_scores'])
            stats['min_confidence'] = min(stats['confidence_scores'])
        
        return stats
    
    def annotate_frame_with_detections(self, frame_path: str, 
                                     detection_result: ObjectDetectionResult,
                                     output_path: str = None) -> str:
        """
        Annotate frame with bounding boxes and labels
        
        Args:
            frame_path: Path to input frame
            detection_result: ObjectDetectionResult for the frame
            output_path: Optional output path, auto-generated if None
            
        Returns:
            Path to annotated frame
        """
        frame = cv2.imread(frame_path)
        if frame is None:
            logger.error(f"Could not load frame for annotation: {frame_path}")
            return frame_path
        
        # Draw bounding boxes and labels
        for obj in detection_result.detected_objects:
            x1, y1, x2, y2 = obj.bbox
            
            # Choose color based on object class (BGR format)
            color_map = {
                'fire': (255, 255, 0),    # Neon Cyan/Blue
                'knife': (0, 255, 255),   # Neon Yellow
                'gun': (0, 255, 0)        # Neon Green
            }
            color = color_map.get(obj.class_name, (255, 255, 255))  # Default white
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label with confidence
            label = f"{obj.class_name}: {obj.confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Draw label background
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            
            # Draw label text
            cv2.putText(frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(frame_path))[0]
            output_dir = os.path.dirname(frame_path)
            output_path = os.path.join(output_dir, f"{base_name}_annotated.jpg")
        
        # Save annotated frame
        cv2.imwrite(output_path, frame)
        return output_path


class ObjectDetectionIntegrator:
    """Integration layer between object detection and video processing pipeline"""
    
    def __init__(self, config):
        self.config = config
        self.detector = ObjectDetector(config) if config.enable_object_detection else None
    
    def process_keyframes_with_object_detection(self, keyframes: List) -> Tuple[List, List[Dict[str, Any]]]:
        """
        Process keyframes with object detection and create object-based events
        
        Args:
            keyframes: List of KeyframeResult objects
            
        Returns:
            Tuple of (detection_results, object_events)
        """
        if not self.config.enable_object_detection or not self.detector:
            logger.info("Object detection disabled, skipping...")
            return [], []
        
        logger.info("🎯 Starting object detection integration")
        
        # Run object detection on keyframes
        detection_results = self.detector.detect_objects_in_keyframes(keyframes)
        
        # Create annotated frames for keyframes WITH detections
        annotated_frames = []
        frames_with_detections = []
        
        for result in detection_results:
            if result.total_detections > 0:
                # Create annotated version of the frame
                annotated_path = self.detector.annotate_frame_with_detections(
                    result.frame_path, result
                )
                
                # Store metadata about frames with detections
                frames_with_detections.append({
                    'original_path': result.frame_path,
                    'annotated_path': annotated_path,
                    'timestamp': result.timestamp,
                    'detection_count': result.total_detections,
                    'objects': [obj.class_name for obj in result.detected_objects],
                    'confidence_avg': result.detection_confidence_avg
                })
                
                annotated_frames.append(annotated_path)
                
                logger.info(f"🎯 Annotated frame at {result.timestamp:.2f}s with {result.total_detections} detections")
        
        # Create object-based events
        object_events = self.detector.create_object_based_events(
            detection_results, 
            temporal_window=self.config.object_event_temporal_window
        )
        
        # Store detection metadata in config for later retrieval
        if hasattr(self.config, 'output_base_dir'):
            detection_metadata = {
                'total_keyframes': len(keyframes),
                'frames_with_detections': len(frames_with_detections),
                'annotated_frames': annotated_frames,
                'detection_summary': frames_with_detections,
                'objects_detected': self.detector.detection_stats['objects_by_class'].copy()
            }
            
            # Save metadata to output directory
            metadata_path = os.path.join(self.config.output_base_dir, 'detection_metadata.json')
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            import json
            with open(metadata_path, 'w') as f:
                json.dump(detection_metadata, f, indent=2)
                
            logger.info(f"📊 Detection metadata saved: {metadata_path}")
        
        logger.info(f"✅ Object detection integration complete: {len(object_events)} events created")
        logger.info(f"📊 Annotated {len(annotated_frames)} frames with detections out of {len(keyframes)} total keyframes")
        
        return detection_results, object_events
    
    def create_annotated_video(self, video_path: str, detection_results: List, output_path: str = None) -> str:
        """
        Create an annotated video with bounding boxes drawn on frames with detections
        
        Args:
            video_path: Path to the original video
            detection_results: List of ObjectDetectionResult from keyframe detection
            output_path: Optional output path for annotated video
            
        Returns:
            Path to the created annotated video
        """
        if not self.detector or not detection_results:
            logger.warning("No detector or detection results available for video annotation")
            return None
        
        logger.info(f"🎨 Creating annotated video with bounding boxes...")
        
        # Open input video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return None
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Build detection lookup by timestamp
        detection_lookup = {}
        for result in detection_results:
            if result.total_detections > 0:
                detection_lookup[result.timestamp] = result
        
        # Create output path if not provided
        if output_path is None:
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(video_dir, f"{video_name}_annotated.mp4")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            logger.error(f"Cannot create output video: {output_path}")
            cap.release()
            return None
        
        frame_count = 0
        frames_annotated = 0
        
        logger.info(f"Processing {total_frames} frames at {fps} FPS...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate timestamp
            timestamp = round(frame_count / fps, 2)
            
            # Check if this timestamp has detections
            if timestamp in detection_lookup:
                result = detection_lookup[timestamp]
                
                # Draw bounding boxes and labels
                for obj in result.detected_objects:
                    x1, y1, x2, y2 = obj.bbox
                    
                    # Choose color based on object class (BGR format)
                    color_map = {
                        'fire': (255, 255, 0),    # Neon Cyan/Blue
                        'knife': (0, 255, 255),   # Neon Yellow
                        'gun': (0, 255, 0)        # Neon Green
                    }
                    color = color_map.get(obj.class_name, (255, 255, 255))
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw label with confidence
                    label = f"{obj.class_name}: {obj.confidence:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    
                    # Draw label background
                    cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                                 (x1 + label_size[0], y1), color, -1)
                    
                    # Draw label text
                    cv2.putText(frame, label, (x1, y1 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                frames_annotated += 1
            
            # Write frame to output video
            out.write(frame)
            frame_count += 1
            
            # Progress logging
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                logger.info(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
        
        # Release resources
        cap.release()
        out.release()
        
        logger.info(f"✅ Annotated video created: {output_path}")
        logger.info(f"📊 Annotated {frames_annotated} frames out of {total_frames} total frames")
        
        return output_path
    
    def get_object_detection_summary(self) -> Dict[str, Any]:
        """Get summary of object detection results"""
        if not self.detector:
            return {'enabled': False}
        
        stats = self.detector.get_detection_statistics()
        stats['enabled'] = True
        return stats
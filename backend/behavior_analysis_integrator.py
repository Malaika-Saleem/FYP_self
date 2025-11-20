"""
Behavior Analysis Integrator for DetectifAI

This module integrates behavior analysis (action recognition) into the video processing pipeline.
It processes video segments/keyframes to detect suspicious behaviors like fighting, accidents, and climbing.
Similar to ObjectDetectionIntegrator, it creates behavior-based events and identifies suspicious frames
for facial recognition processing.
"""

import os
import cv2
import time
import logging
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import numpy as np

# Import behavior analysis module
from behavior_analysis.action_recognition import (
    load_model, preprocess_clip, interpret_prediction,
    MODEL_PATHS, RESNET_MODELS, YOLO_MODELS, ActionPrediction
)

logger = logging.getLogger(__name__)


@dataclass
class BehaviorDetectionResult:
    """Result of behavior detection on a frame or segment"""
    frame_path: str
    timestamp: float
    frame_index: int
    behavior_detected: str  # "fighting", "accident", "climbing", or "no_action"
    confidence: float
    model_used: str
    processing_time: float


@dataclass
class BehaviorEvent:
    """Behavior-based event created from detections"""
    event_id: str
    behavior_type: str
    start_timestamp: float
    end_timestamp: float
    confidence: float
    frame_indices: List[int]
    keyframes: List[str]
    model_used: str
    importance_score: float


class BehaviorAnalysisIntegrator:
    """Integration layer between behavior analysis and video processing pipeline"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = getattr(config, 'enable_behavior_analysis', False)
        
        logger.info(f"🔍 Initializing BehaviorAnalysisIntegrator - enabled: {self.enabled}")
        
        # Initialize models if enabled
        self.models = {}
        self.device = None
        
        if self.enabled:
            try:
                import torch
                self.device = torch.device("cuda" if (torch.cuda.is_available() and getattr(config, 'use_gpu_acceleration', True)) else "cpu")
                
                # Load all available models
                logger.info(f"🔧 Attempting to load models from: {MODEL_PATHS}")
                for model_name, model_path in MODEL_PATHS.items():
                    logger.info(f"📁 Checking model {model_name} at: {model_path}")
                    if os.path.exists(model_path):
                        try:
                            logger.info(f"⏳ Loading {model_name}...")
                            self.models[model_name] = load_model(model_path, self.device)
                            logger.info(f"✅ Loaded behavior analysis model: {model_name}")
                        except Exception as e:
                            logger.error(f"❌ Failed to load {model_name}: {e}")
                    else:
                        logger.error(f"❌ Model file not found: {model_path}")
                
                if not self.models:
                    logger.warning("⚠️ No behavior analysis models loaded, disabling behavior analysis")
                    self.enabled = False
                else:
                    logger.info(f"✅ Behavior analysis initialized with {len(self.models)} models")
                    
            except ImportError:
                logger.warning("⚠️ PyTorch not available, disabling behavior analysis")
                self.enabled = False
        else:
            logger.info("Behavior analysis disabled in config")
    
    def detect_behavior_in_frame(self, frame_path: str, timestamp: float, frame_index: int = 0) -> List[BehaviorDetectionResult]:
        """
        Detect behaviors in a single frame
        
        Args:
            frame_path: Path to frame image
            timestamp: Timestamp in seconds
            frame_index: Frame index number
            
        Returns:
            List of BehaviorDetectionResult objects (one per model)
        """
        if not self.enabled or not self.models:
            return []
        
        if not os.path.exists(frame_path):
            logger.warning(f"Frame not found: {frame_path}")
            return []
        
        results = []
        frame = cv2.imread(frame_path)
        if frame is None:
            logger.warning(f"Failed to read frame: {frame_path}")
            return []
        
        for model_name, model in self.models.items():
            try:
                start_time = time.time()
                
                # YOLO models (wallclimb)
                if model_name in YOLO_MODELS:
                    output = model.predict(frame, verbose=False)
                    confidence_threshold = getattr(self.config, 'behavior_detection_confidence', 0.5)
                    label, conf = interpret_prediction(model, output, model_name, confidence_threshold)
                    
                    logger.info(f"🔍 YOLO model {model_name} prediction: {label} (confidence: {conf:.3f}, threshold: {confidence_threshold})")
                    
                    if label != "no_action":
                        result = BehaviorDetectionResult(
                            frame_path=frame_path,
                            timestamp=timestamp,
                            frame_index=frame_index,
                            behavior_detected=label,
                            confidence=conf,
                            model_used=model_name,
                            processing_time=time.time() - start_time
                        )
                        results.append(result)
                
                # 3D-ResNet models need clips of 16 frames
                # For single frame detection, we'll need to handle this differently
                # For now, skip 3D-ResNet models for single frame detection
                # They should be used with video segments instead
                
            except Exception as e:
                logger.error(f"Error detecting behavior with {model_name}: {e}")
                continue
        
        return results
    
    def detect_behavior_in_segment(self, video_path: str, start_time: float, end_time: float, 
                                   frame_indices: List[int] = None) -> List[BehaviorDetectionResult]:
        """
        Detect behaviors in a video segment (for 3D-ResNet models that need temporal context)
        
        Args:
            video_path: Path to video file
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            frame_indices: Optional list of frame indices to process
            
        Returns:
            List of BehaviorDetectionResult objects
        """
        if not self.enabled or not self.models:
            return []
        
        if not os.path.exists(video_path):
            logger.warning(f"Video not found: {video_path}")
            return []
        
        results = []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return []
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        
        # Read frames for the segment
        frame_buffer = []
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        for idx in range(start_frame, min(end_frame, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))):
            ret, frame = cap.read()
            if not ret:
                break
            frame_buffer.append(frame)
        
        cap.release()
        
        # Calculate mid frame index
        mid_frame_idx = (start_frame + end_frame) // 2 if end_frame > start_frame else start_frame
        return self._process_frame_buffer(frame_buffer, start_time, end_time, mid_frame_idx, video_path)
    
    def detect_behavior_in_segment_from_buffer(self, frame_buffer: List[np.ndarray], 
                                               start_time: float, end_time: float,
                                               frame_indices: List[int] = None) -> List[BehaviorDetectionResult]:
        """
        Detect behaviors in a frame buffer (for live streams)
        
        Args:
            frame_buffer: List of frames (numpy arrays)
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            frame_indices: Optional list of frame indices
            
        Returns:
            List of BehaviorDetectionResult objects
        """
        if not self.enabled or not self.models:
            return []
        
        if len(frame_buffer) < 16:
            logger.debug(f"Frame buffer too short ({len(frame_buffer)} frames), skipping 3D-ResNet models")
            return []
        
        # Use last 16 frames from buffer
        frames_to_process = frame_buffer[-16:] if len(frame_buffer) >= 16 else frame_buffer
        mid_frame_idx = len(frame_buffer) // 2 if frame_indices is None else (frame_indices[len(frame_indices) // 2] if frame_indices else len(frame_buffer) // 2)
        
        return self._process_frame_buffer(frames_to_process, start_time, end_time, mid_frame_idx, "live_stream")
    
    def _process_frame_buffer(self, frame_buffer: List[np.ndarray], start_time: float, 
                             end_time: float, frame_index: int, video_path: str = "live_stream") -> List[BehaviorDetectionResult]:
        """
        Process frame buffer with behavior analysis models
        
        Args:
            frame_buffer: List of frames (numpy arrays)
            start_time: Start timestamp
            end_time: End timestamp
            frame_index: Frame index for result
            video_path: Path to video file or "live_stream" for live streams
            
        Returns:
            List of BehaviorDetectionResult objects
        """
        if len(frame_buffer) < 16:
            return []
        
        results = []
        
        # Process with 3D-ResNet models (need 16-frame clips)
        for model_name, model in self.models.items():
            if model_name not in RESNET_MODELS:
                continue
            
            try:
                start_time_proc = time.time()
                
                # Process last 16 frames from buffer
                clip = preprocess_clip(frame_buffer[-16:], self.device)
                
                import torch
                model.eval()
                with torch.no_grad():
                    output = model(clip)
                
                confidence_threshold = getattr(self.config, 'behavior_detection_confidence', 0.5)
                label, conf = interpret_prediction(model, output, model_name, confidence_threshold)
                
                logger.info(f"🔍 Model {model_name} prediction: {label} (confidence: {conf:.3f}, threshold: {confidence_threshold})")
                
                if label != "no_action":
                    # Use middle timestamp of the segment
                    mid_timestamp = (start_time + end_time) / 2
                    
                    result = BehaviorDetectionResult(
                        frame_path="live_stream",  # Live stream identifier
                        timestamp=mid_timestamp,
                        frame_index=frame_index,
                        behavior_detected=label,
                        confidence=conf,
                        model_used=model_name,
                        processing_time=time.time() - start_time_proc
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error detecting behavior with {model_name} in segment: {e}")
                continue
        
        return results
    
    def detect_behavior_in_keyframes(self, keyframes: List, video_path: str = None) -> List[BehaviorDetectionResult]:
        """
        Detect behaviors in keyframes
        
        Args:
            keyframes: List of KeyframeResult objects
            video_path: Optional path to video file (needed for 3D-ResNet models)
            
        Returns:
            List of BehaviorDetectionResult objects
        """
        if not self.enabled:
            logger.info("🚫 Behavior analysis disabled, skipping")
            return []
            
        logger.info(f"🎬 Starting behavior detection on {len(keyframes)} keyframes")
        logger.info(f"📹 Video path provided: {video_path}")
        logger.info(f"🤖 Available models: {list(self.models.keys())}")
        
        logger.info(f"🔍 Running behavior analysis on {len(keyframes)} keyframes...")
        
        all_results = []
        
        # Process YOLO models (single frame) - wallclimb
        yolo_models_available = [m for m in self.models.keys() if m in YOLO_MODELS]
        logger.info(f"🎯 Processing YOLO models (single frame): {yolo_models_available}")
        
        for i, keyframe in enumerate(keyframes):
            # Extract frame path and timestamp
            frame_path = None
            timestamp = 0.0
            frame_index = i
            
            if hasattr(keyframe, 'frame_data'):
                frame_path = keyframe.frame_data.frame_path if hasattr(keyframe.frame_data, 'frame_path') else None
                timestamp = keyframe.frame_data.timestamp if hasattr(keyframe.frame_data, 'timestamp') else 0.0
            elif hasattr(keyframe, 'frame_path'):
                frame_path = keyframe.frame_path
                timestamp = getattr(keyframe, 'timestamp', 0.0)
            
            if frame_path and os.path.exists(frame_path):
                # Detect with YOLO models (single frame) - wallclimb
                frame_results = self.detect_behavior_in_frame(frame_path, timestamp, frame_index)
                all_results.extend(frame_results)
        
        # Process 3D-ResNet models (need 16-frame clips) - fighting, road_accident
        if video_path and os.path.exists(video_path) and RESNET_MODELS:
            resnet_models_available = [m for m in self.models.keys() if m in RESNET_MODELS]
            logger.info(f"🎬 Processing 3D-ResNet models using video segments...")
            logger.info(f"📊 Available ResNet models: {resnet_models_available}")
            logger.info(f"📊 Total ResNet models to process: {len(resnet_models_available)}")
            
            # Group keyframes into temporal segments for 3D-ResNet processing
            # Process segments of ~1 second (16 frames at ~30fps) around each keyframe
            segment_window = 1.0  # 1 second window
            
            processed_segments = set()  # Track processed segments to avoid duplicates
            
            for keyframe in keyframes:
                timestamp = 0.0
                if hasattr(keyframe, 'frame_data'):
                    timestamp = keyframe.frame_data.timestamp if hasattr(keyframe.frame_data, 'timestamp') else 0.0
                elif hasattr(keyframe, 'timestamp'):
                    timestamp = getattr(keyframe, 'timestamp', 0.0)
                
                if timestamp > 0:
                    # Create segment around this keyframe
                    start_time = max(0, timestamp - segment_window / 2)
                    end_time = timestamp + segment_window / 2
                    
                    # Round to avoid processing same segment multiple times
                    segment_key = (int(start_time * 10), int(end_time * 10))
                    
                    if segment_key not in processed_segments:
                        processed_segments.add(segment_key)
                        
                        try:
                            logger.info(f"🎥 Processing video segment: {start_time:.1f}s - {end_time:.1f}s")
                            # Process segment with 3D-ResNet models
                            segment_results = self.detect_behavior_in_segment(
                                video_path=video_path,
                                start_time=start_time,
                                end_time=end_time,
                                frame_indices=None
                            )
                            logger.info(f"📈 Segment results: {len(segment_results)} detections")
                            for result in segment_results:
                                logger.info(f"🔍 Detected: {result.behavior_detected} (conf: {result.confidence:.3f})")
                            all_results.extend(segment_results)
                        except Exception as e:
                            logger.error(f"❌ Error processing segment {start_time:.1f}s-{end_time:.1f}s: {e}")
                            continue
        
        logger.info(f"✅ Behavior analysis complete: {len(all_results)} behaviors detected")
        return all_results
    
    def create_behavior_events(self, detection_results: List[BehaviorDetectionResult], 
                              temporal_window: float = 5.0) -> List[BehaviorEvent]:
        """
        Create behavior-based events from detection results
        
        Args:
            detection_results: List of BehaviorDetectionResult objects
            temporal_window: Time window in seconds for grouping detections
            
        Returns:
            List of BehaviorEvent objects
        """
        if not detection_results:
            return []
        
        # Group detections by behavior type and temporal proximity
        events = []
        sorted_results = sorted(detection_results, key=lambda x: x.timestamp)
        
        current_event = None
        event_id_counter = 0
        
        for result in sorted_results:
            if result.behavior_detected == "no_action":
                continue
            
            if current_event is None:
                # Start new event
                event_id_counter += 1
                current_event = {
                    'event_id': f"behavior_{result.behavior_detected}_{event_id_counter}",
                    'behavior_type': result.behavior_detected,
                    'start_timestamp': result.timestamp,
                    'end_timestamp': result.timestamp,
                    'confidences': [result.confidence],
                    'frame_indices': [result.frame_index],
                    'keyframes': [result.frame_path],
                    'model_used': result.model_used
                }
            elif (result.behavior_detected == current_event['behavior_type'] and 
                  result.timestamp - current_event['end_timestamp'] <= temporal_window):
                # Extend current event
                current_event['end_timestamp'] = result.timestamp
                current_event['confidences'].append(result.confidence)
                current_event['frame_indices'].append(result.frame_index)
                current_event['keyframes'].append(result.frame_path)
            else:
                # Finalize current event and start new one
                avg_confidence = sum(current_event['confidences']) / len(current_event['confidences'])
                importance = avg_confidence * (current_event['end_timestamp'] - current_event['start_timestamp'] + 1)
                
                behavior_event = BehaviorEvent(
                    event_id=current_event['event_id'],
                    behavior_type=current_event['behavior_type'],
                    start_timestamp=current_event['start_timestamp'],
                    end_timestamp=current_event['end_timestamp'],
                    confidence=avg_confidence,
                    frame_indices=current_event['frame_indices'],
                    keyframes=current_event['keyframes'],
                    model_used=current_event['model_used'],
                    importance_score=importance
                )
                events.append(behavior_event)
                
                # Start new event
                event_id_counter += 1
                current_event = {
                    'event_id': f"behavior_{result.behavior_detected}_{event_id_counter}",
                    'behavior_type': result.behavior_detected,
                    'start_timestamp': result.timestamp,
                    'end_timestamp': result.timestamp,
                    'confidences': [result.confidence],
                    'frame_indices': [result.frame_index],
                    'keyframes': [result.frame_path],
                    'model_used': result.model_used
                }
        
        # Finalize last event
        if current_event:
            avg_confidence = sum(current_event['confidences']) / len(current_event['confidences'])
            importance = avg_confidence * (current_event['end_timestamp'] - current_event['start_timestamp'] + 1)
            
            behavior_event = BehaviorEvent(
                event_id=current_event['event_id'],
                behavior_type=current_event['behavior_type'],
                start_timestamp=current_event['start_timestamp'],
                end_timestamp=current_event['end_timestamp'],
                confidence=avg_confidence,
                frame_indices=current_event['frame_indices'],
                keyframes=current_event['keyframes'],
                model_used=current_event['model_used'],
                importance_score=importance
            )
            events.append(behavior_event)
        
        logger.info(f"✅ Created {len(events)} behavior-based events")
        return events
    
    def process_keyframes_with_behavior_analysis(self, keyframes: List, video_path: str = None) -> Tuple[List[BehaviorDetectionResult], List[BehaviorEvent]]:
        """
        Process keyframes with behavior analysis and create behavior-based events
        
        Args:
            keyframes: List of KeyframeResult objects
            video_path: Optional path to video file (needed for 3D-ResNet models)
            
        Returns:
            Tuple of (detection_results, behavior_events)
        """
        if not self.enabled:
            logger.info("🚫 Behavior analysis disabled, skipping...")
            return [], []
            
        logger.info("🚀 ===== STARTING BEHAVIOR ANALYSIS INTEGRATION =====")
        logger.info(f"📊 Input: {len(keyframes)} keyframes, video_path: {video_path}")
        logger.info(f"🤖 Loaded models: {list(self.models.keys())}")
        logger.info(f"⚙️ Confidence threshold: {getattr(self.config, 'behavior_detection_confidence', 0.5)}")
        
        logger.info("🔍 Starting behavior analysis integration")
        
        # Run behavior detection on keyframes (with video_path for 3D-ResNet models)
        detection_results = self.detect_behavior_in_keyframes(keyframes, video_path=video_path)
        
        # Create behavior-based events
        temporal_window = getattr(self.config, 'behavior_event_temporal_window', 5.0)
        logger.info(f"📅 Creating behavior events with temporal window: {temporal_window}s")
        logger.info(f"📊 Total detections to process: {len(detection_results)}")
        
        positive_detections = [r for r in detection_results if r.behavior_detected != "no_action"]
        logger.info(f"✅ Positive detections: {len(positive_detections)}")
        for detection in positive_detections:
            logger.info(f"   🎯 {detection.behavior_detected} at {detection.timestamp:.1f}s (conf: {detection.confidence:.3f})")
            
        behavior_events = self.create_behavior_events(detection_results, temporal_window)
        
        # Store detection metadata
        if hasattr(self.config, 'output_base_dir') and detection_results:
            detection_metadata = {
                'total_keyframes': len(keyframes),
                'frames_with_behaviors': len([r for r in detection_results if r.behavior_detected != "no_action"]),
                'behaviors_detected': {
                    'fighting': len([r for r in detection_results if r.behavior_detected == "fighting"]),
                    'accident': len([r for r in detection_results if r.behavior_detected == "accident"]),
                    'climbing': len([r for r in detection_results if r.behavior_detected == "climbing"])
                },
                'total_events': len(behavior_events),
                'detection_summary': [asdict(r) for r in detection_results[:10]]  # First 10 for summary
            }
            
            metadata_path = os.path.join(self.config.output_base_dir, 'behavior_analysis_metadata.json')
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            with open(metadata_path, 'w') as f:
                json.dump(detection_metadata, f, indent=2, default=str)
            
            logger.info(f"📊 Behavior analysis metadata saved: {metadata_path}")
        
        logger.info("🏁 ===== BEHAVIOR ANALYSIS INTEGRATION COMPLETE =====")
        logger.info(f"📈 Summary:")
        logger.info(f"   📊 Total detections: {len(detection_results)}")
        logger.info(f"   ✅ Positive detections: {len([r for r in detection_results if r.behavior_detected != 'no_action'])}")
        logger.info(f"   📅 Events created: {len(behavior_events)}")
        
        for event in behavior_events:
            logger.info(f"   🎬 Event: {event.behavior_type} ({event.start_timestamp:.1f}s-{event.end_timestamp:.1f}s, conf: {event.confidence:.3f})")
        
        return detection_results, behavior_events
    
    def get_suspicious_frames(self, detection_results: List[BehaviorDetectionResult]) -> List[BehaviorDetectionResult]:
        """
        Get frames with suspicious behaviors (for facial recognition processing)
        
        Args:
            detection_results: List of BehaviorDetectionResult objects
            
        Returns:
            List of suspicious BehaviorDetectionResult objects
        """
        suspicious = [r for r in detection_results if r.behavior_detected != "no_action"]
        logger.info(f"🔍 Identified {len(suspicious)} suspicious frames from behavior analysis")
        return suspicious
    
    def get_behavior_analysis_summary(self) -> Dict[str, Any]:
        """Get summary statistics of behavior analysis"""
        return {
            'enabled': self.enabled,
            'models_loaded': list(self.models.keys()) if self.models else [],
            'device': str(self.device) if self.device else None
        }


"""
Webcam Integration Module

This module provides real-time webcam processing capabilities integrated with the
existing video preprocessing pipeline. It captures frames from webcam, applies
the same preprocessing as file-based processing, detects motion/events, and
can stream processed video or save keyframes.
"""

import cv2
import numpy as np
import os
import io
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Generator
from dataclasses import dataclass
import logging
import threading
import queue

from video_processing import AdaptiveFrameEnhancer, MotionDetector, QualityAssessment, BurstDetector, FrameData, KeyframeResult

logger = logging.getLogger(__name__)

@dataclass
class WebcamConfig:
    """Configuration for webcam processing"""
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps_target: int = 30
    enable_streaming: bool = True
    enable_keyframe_saving: bool = True
    motion_upload_threshold: float = 25.0  # pixel diff threshold
    blur_threshold: int = 100  # Laplacian variance threshold
    fps_low: int = 1
    fps_high: int = 8
    frame_size: Tuple[int, int] = (640, 640)  # For YOLO/model input

class WebcamProcessor:
    """Real-time webcam processing with integrated preprocessing pipeline"""

    def __init__(self, config, video_config):
        """
        Initialize webcam processor

        Args:
            config: WebcamConfig object
            video_config: VideoProcessingConfig from main pipeline
        """
        self.config = config
        self.video_config = video_config

        # Initialize processing components from existing pipeline
        self.enhancer = AdaptiveFrameEnhancer(
            enable_clahe=video_config.enable_clahe,
            clahe_clip_limit=video_config.clahe_clip_limit,
            enable_denoising=video_config.enable_denoising,
            denoise_strength=video_config.denoise_strength
        )

        self.motion_detector = MotionDetector(video_config.motion_threshold)
        self.quality_assessor = QualityAssessment()
        self.burst_detector = BurstDetector(video_config.motion_threshold * 1.5)

        # Webcam-specific state
        self.cap = None
        self.is_running = False
        self.frame_queue = queue.Queue(maxsize=30)
        self.processed_frames_dir = os.path.join(video_config.output_base_dir, "webcam_frames")
        os.makedirs(self.processed_frames_dir, exist_ok=True)

        # Motion detection state (matching the provided code)
        self.prev_frame_gray = None
        self.frame_skip_counter = 0

        logger.info("WebcamProcessor initialized")

    def start_capture(self) -> bool:
        """Start webcam capture"""
        try:
            self.cap = cv2.VideoCapture(self.config.camera_index)

            if not self.cap.isOpened():
                logger.error(f"Could not open webcam at index {self.config.camera_index}")
                return False

            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps_target)

            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(f"Webcam opened: {actual_width}x{actual_height} @ {actual_fps} FPS")
            self.is_running = True

            return True

        except Exception as e:
            logger.error(f"Failed to start webcam capture: {e}")
            return False

    def stop_capture(self):
        """Stop webcam capture"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        logger.info("Webcam capture stopped")

    def preprocess_frame(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        """
        Apply preprocessing to frame (matching the provided code logic)

        Args:
            frame: Input frame

        Returns:
            Tuple of (processed_frame, should_process)
        """
        try:
            # Convert to grayscale for blur detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply CLAHE (contrast enhancement)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            # Merge back to 3 channels
            processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            # Resize to model size
            processed = cv2.resize(processed, self.config.frame_size)

            # Skip blurry frames
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if lap_var < self.config.blur_threshold:
                return None, False

            return processed, True

        except Exception as e:
            logger.error(f"Frame preprocessing failed: {e}")
            return None, False

    def detect_motion(self, frame_gray: np.ndarray) -> Tuple[bool, float]:
        """
        Detect motion using frame differencing (matching provided code)

        Args:
            frame_gray: Grayscale frame

        Returns:
            Tuple of (motion_detected, motion_score)
        """
        try:
            if self.prev_frame_gray is None:
                self.prev_frame_gray = frame_gray
                return False, 0

            diff = cv2.absdiff(self.prev_frame_gray, frame_gray)
            self.prev_frame_gray = frame_gray

            motion_score = np.sum(diff > self.config.motion_upload_threshold)
            motion_detected = motion_score > 5000

            return motion_detected, motion_score

        except Exception as e:
            logger.error(f"Motion detection failed: {e}")
            return False, 0

    def process_frame(self, frame: np.ndarray, timestamp: float) -> Optional[KeyframeResult]:
        """
        Process a single frame through the complete pipeline

        Args:
            frame: Input frame
            timestamp: Frame timestamp

        Returns:
            KeyframeResult if frame should be saved, None otherwise
        """
        try:
            # Apply preprocessing
            processed_frame, should_process = self.preprocess_frame(frame)
            if not should_process or processed_frame is None:
                return None

            # Convert to grayscale for motion detection
            frame_gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)

            # Detect motion
            motion_detected, motion_score = self.detect_motion(frame_gray)

            # Update burst detector
            is_burst = self.burst_detector.update_motion_history(motion_score / 10000.0)  # Normalize

            # Calculate quality score
            quality_score = self.quality_assessor.calculate_quality_score(processed_frame)

            # Determine if frame should be saved
            should_save = (
                quality_score >= self.video_config.base_quality_threshold or
                motion_detected or
                is_burst
            )

            if should_save and self.config.enable_keyframe_saving:
                # Save frame
                frame_filename = f"webcam_{int(timestamp * 1000)}.jpg"
                frame_path = os.path.join(self.processed_frames_dir, frame_filename)

                cv2.imwrite(frame_path, processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

                # Create frame data
                frame_data = FrameData(
                    frame_path=frame_path,
                    timestamp=timestamp,
                    frame_number=int(timestamp * self.config.fps_target),
                    quality_score=quality_score,
                    motion_score=motion_score / 10000.0,  # Normalize to 0-1 range
                    burst_active=is_burst,
                    enhancement_applied=True
                )

                # Calculate keyframe score
                keyframe_score = quality_score
                if motion_detected:
                    keyframe_score += (motion_score / 10000.0) * 0.5
                if is_burst:
                    keyframe_score *= self.video_config.burst_weight

                selection_reason = "Motion Detected" if motion_detected else "High Quality"

                return KeyframeResult(
                    frame_data=frame_data,
                    keyframe_score=min(keyframe_score, 2.0),
                    selection_reason=selection_reason
                )

            return None

        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            return None

    def gen_frames(self) -> Generator[bytes, None, None]:
        """
        Generate processed frames for streaming (matching provided code structure)

        Yields:
            JPEG encoded frames as bytes
        """
        if not self.is_running:
            self.start_capture()

        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.error("Could not read frame from webcam")
                    break

                # Get timestamp
                timestamp = time.time()

                # Process frame
                processed_frame, should_process = self.preprocess_frame(frame)

                if processed_frame is not None:
                    # Encode for streaming
                    ret, buffer = cv2.imencode('.jpg', processed_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

                # Small delay to prevent overwhelming
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in frame generation: {e}")
                break

        self.stop_capture()
        logger.info("Frame generation stopped")

    def capture_keyframes(self, duration_seconds: int = 30) -> List[KeyframeResult]:
        """
        Capture keyframes for a specified duration

        Args:
            duration_seconds: How long to capture keyframes

        Returns:
            List of captured keyframes
        """
        if not self.is_running:
            self.start_capture()

        keyframes = []
        start_time = time.time()
        frame_count = 0

        logger.info(f"Starting keyframe capture for {duration_seconds} seconds")

        try:
            while self.is_running and (time.time() - start_time) < duration_seconds:
                ret, frame = self.cap.read()
                if not ret:
                    break

                timestamp = time.time() - start_time
                keyframe = self.process_frame(frame, timestamp)

                if keyframe:
                    keyframes.append(keyframe)

                frame_count += 1

                # Progress logging
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"Captured {len(keyframes)} keyframes in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"Keyframe capture failed: {e}")
        finally:
            self.stop_capture()

        logger.info(f"Keyframe capture complete: {len(keyframes)} frames captured")
        return keyframes

    def get_webcam_info(self) -> Dict[str, Any]:
        """Get information about the webcam"""
        if not self.cap:
            return {"status": "not_initialized"}

        try:
            return {
                "status": "active" if self.is_running else "inactive",
                "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": self.cap.get(cv2.CAP_PROP_FPS),
                "backend": self.cap.get(cv2.CAP_PROP_BACKEND),
                "frames_processed": getattr(self, '_frames_processed', 0)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

class WebcamIntegrationManager:
    """Manager class for webcam integration with the main pipeline"""

    def __init__(self, video_config):
        self.video_config = video_config
        self.webcam_config = WebcamConfig()
        self.processor = WebcamProcessor(self.webcam_config, video_config)
        self.captured_keyframes = []

    def start_webcam_processing(self) -> bool:
        """Start webcam processing"""
        return self.processor.start_capture()

    def stop_webcam_processing(self):
        """Stop webcam processing"""
        self.processor.stop_capture()

    def capture_session(self, duration: int = 30) -> List[KeyframeResult]:
        """Capture a session of keyframes from webcam"""
        keyframes = self.processor.capture_keyframes(duration)
        self.captured_keyframes.extend(keyframes)
        return keyframes

    def get_stream_generator(self):
        """Get frame generator for streaming"""
        return self.processor.gen_frames()

    def get_captured_keyframes(self) -> List[KeyframeResult]:
        """Get all captured keyframes"""
        return self.captured_keyframes

    def clear_captured_keyframes(self):
        """Clear captured keyframes buffer"""
        self.captured_keyframes.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            "webcam_info": self.processor.get_webcam_info(),
            "captured_keyframes": len(self.captured_keyframes),
            "config": {
                "camera_index": self.webcam_config.camera_index,
                "frame_size": self.webcam_config.frame_size,
                "motion_threshold": self.webcam_config.motion_upload_threshold
            }
        }

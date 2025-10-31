"""
Video Processing Core Components

This module contains the core video processing classes for:
- Adaptive frame enhancement
- Keyframe extraction with motion detection
- Burst sampling for high-activity periods
"""

import cv2
import numpy as np
import os
import uuid
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FrameData:
    """Data structure for frame information"""
    frame_path: str
    timestamp: float
    frame_number: int
    quality_score: float
    motion_score: float
    burst_active: bool
    enhancement_applied: bool
    face_count: int = 0
    object_count: int = 0

@dataclass
class KeyframeResult:
    """Result structure for keyframe extraction"""
    frame_data: FrameData
    keyframe_score: float
    selection_reason: str

class AdaptiveFrameEnhancer:
    """Adaptive frame enhancement using CLAHE and denoising"""
    
    def __init__(self, enable_clahe: bool = True, clahe_clip_limit: float = 2.0,
                 enable_denoising: bool = True, denoise_strength: int = 5):
        self.enable_clahe = enable_clahe
        self.enable_denoising = enable_denoising
        self.denoise_strength = denoise_strength
        
        # Initialize CLAHE
        if enable_clahe:
            self.clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=(8, 8))
        
        logger.info(f"AdaptiveFrameEnhancer initialized - CLAHE: {enable_clahe}, Denoising: {enable_denoising}")
    
    def enhance_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Enhance a single frame with adaptive techniques
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Tuple of (enhanced_frame, enhancement_applied)
        """
        try:
            enhanced = frame.copy()
            enhancement_applied = False
            
            # Convert to different color spaces for processing
            if len(frame.shape) == 3:
                # Color frame
                lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
                l_channel = lab[:, :, 0]
                
                # Apply CLAHE to L channel
                if self.enable_clahe:
                    l_enhanced = self.clahe.apply(l_channel)
                    lab[:, :, 0] = l_enhanced
                    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                    enhancement_applied = True
                
                # Apply denoising
                if self.enable_denoising:
                    enhanced = cv2.fastNlMeansDenoisingColored(
                        enhanced, None, self.denoise_strength, self.denoise_strength, 7, 21
                    )
                    enhancement_applied = True
                    
            else:
                # Grayscale frame
                if self.enable_clahe:
                    enhanced = self.clahe.apply(enhanced)
                    enhancement_applied = True
                
                if self.enable_denoising:
                    enhanced = cv2.fastNlMeansDenoising(
                        enhanced, None, self.denoise_strength, 7, 21
                    )
                    enhancement_applied = True
            
            return enhanced, enhancement_applied
            
        except Exception as e:
            logger.error(f"Frame enhancement failed: {e}")
            return frame, False

class MotionDetector:
    """Motion detection for keyframe extraction"""
    
    def __init__(self, motion_threshold: float = 0.01):
        self.motion_threshold = motion_threshold
        self.prev_frame = None
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True, varThreshold=50
        )
        
    def calculate_motion_score(self, frame: np.ndarray) -> float:
        """
        Calculate motion score for a frame
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Motion score (0.0 to 1.0+)
        """
        try:
            # Convert to grayscale if needed
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Apply Gaussian blur to reduce noise
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            motion_score = 0.0
            
            # Method 1: Frame difference
            if self.prev_frame is not None:
                diff = cv2.absdiff(self.prev_frame, gray)
                motion_score = np.mean(diff) / 255.0
            
            # Method 2: Background subtraction
            fg_mask = self.background_subtractor.apply(gray)
            bg_motion = np.sum(fg_mask > 0) / (frame.shape[0] * frame.shape[1])
            
            # Combine both methods
            motion_score = max(motion_score, bg_motion)
            
            self.prev_frame = gray.copy()
            
            return min(motion_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Motion calculation failed: {e}")
            return 0.0

class QualityAssessment:
    """Frame quality assessment using multiple metrics"""
    
    def __init__(self):
        self.weights = {
            'sharpness': 0.3,
            'contrast': 0.25,
            'brightness': 0.2,
            'saturation': 0.15,
            'noise': 0.1
        }
    
    def calculate_sharpness(self, frame: np.ndarray) -> float:
        """Calculate frame sharpness using Laplacian variance"""
        try:
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = laplacian.var()
            
            # Normalize to 0-1 range
            return min(sharpness / 1000.0, 1.0)
            
        except Exception as e:
            logger.error(f"Sharpness calculation failed: {e}")
            return 0.0
    
    def calculate_contrast(self, frame: np.ndarray) -> float:
        """Calculate frame contrast"""
        try:
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            contrast = gray.std() / 128.0
            return min(contrast, 1.0)
            
        except Exception as e:
            logger.error(f"Contrast calculation failed: {e}")
            return 0.0
    
    def calculate_brightness(self, frame: np.ndarray) -> float:
        """Calculate frame brightness quality (penalize over/under exposure)"""
        try:
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            mean_brightness = np.mean(gray) / 255.0
            
            # Optimal brightness is around 0.4-0.6
            if 0.4 <= mean_brightness <= 0.6:
                return 1.0
            elif mean_brightness < 0.2 or mean_brightness > 0.8:
                return 0.3  # Severely under/over exposed
            else:
                return 0.7  # Slightly under/over exposed
                
        except Exception as e:
            logger.error(f"Brightness calculation failed: {e}")
            return 0.5
    
    def calculate_saturation(self, frame: np.ndarray) -> float:
        """Calculate color saturation quality"""
        try:
            if len(frame.shape) != 3:
                return 0.5  # Grayscale
            
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1]) / 255.0
            
            return min(saturation * 1.5, 1.0)  # Boost saturation score
            
        except Exception as e:
            logger.error(f"Saturation calculation failed: {e}")
            return 0.5
    
    def calculate_noise_level(self, frame: np.ndarray) -> float:
        """Calculate noise level (lower is better)"""
        try:
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Use median filter to estimate noise
            filtered = cv2.medianBlur(gray, 5)
            noise = np.mean(np.abs(gray.astype(float) - filtered.astype(float)))
            
            # Return inverted noise score (lower noise = higher quality)
            noise_score = 1.0 - min(noise / 50.0, 1.0)
            return noise_score
            
        except Exception as e:
            logger.error(f"Noise calculation failed: {e}")
            return 0.7
    
    def calculate_quality_score(self, frame: np.ndarray) -> float:
        """
        Calculate overall quality score for a frame
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        try:
            metrics = {
                'sharpness': self.calculate_sharpness(frame),
                'contrast': self.calculate_contrast(frame),
                'brightness': self.calculate_brightness(frame),
                'saturation': self.calculate_saturation(frame),
                'noise': self.calculate_noise_level(frame)
            }
            
            # Calculate weighted average
            quality_score = sum(
                metrics[metric] * self.weights[metric] 
                for metric in metrics
            )
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 0.0

class BurstDetector:
    """Detect burst periods of high activity"""
    
    def __init__(self, burst_threshold: float = 0.015, window_size: int = 5):
        self.burst_threshold = burst_threshold
        self.window_size = window_size
        self.motion_history = []
        
    def update_motion_history(self, motion_score: float) -> bool:
        """
        Update motion history and detect if current frame is in burst period
        
        Args:
            motion_score: Current frame motion score
            
        Returns:
            True if frame is in burst period
        """
        self.motion_history.append(motion_score)
        
        # Keep only recent history
        if len(self.motion_history) > self.window_size * 2:
            self.motion_history = self.motion_history[-self.window_size * 2:]
        
        # Need minimum history for burst detection
        if len(self.motion_history) < self.window_size:
            return False
        
        # Check if recent frames show high activity
        recent_motion = self.motion_history[-self.window_size:]
        avg_recent_motion = np.mean(recent_motion)
        
        # Check if current motion is significantly higher than recent average
        is_burst = (
            motion_score > self.burst_threshold and
            motion_score > avg_recent_motion * 1.5
        )
        
        return is_burst

class OptimizedVideoProcessor:
    """Main video processing class combining all components"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize components
        self.enhancer = AdaptiveFrameEnhancer(
            enable_clahe=config.enable_clahe,
            clahe_clip_limit=config.clahe_clip_limit,
            enable_denoising=config.enable_denoising,
            denoise_strength=config.denoise_strength
        )
        
        self.motion_detector = MotionDetector(config.motion_threshold)
        self.quality_assessor = QualityAssessment()
        self.burst_detector = BurstDetector(config.motion_threshold * 1.5)
        
        # Create output directories
        self.frames_dir = os.path.join(config.output_base_dir, "frames")
        os.makedirs(self.frames_dir, exist_ok=True)
        
        logger.info("OptimizedVideoProcessor initialized")
    
    def extract_keyframes(self, video_path: str) -> List[KeyframeResult]:
        """
        Extract keyframes from video with adaptive enhancement
        
        Args:
            video_path: Path to input video file
            
        Returns:
            List of KeyframeResult objects
        """
        logger.info(f"Starting keyframe extraction from: {video_path}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        logger.info(f"Video properties: {total_frames} frames, {fps:.2f} FPS, {duration:.2f}s")
        
        keyframes = []
        frame_number = 0
        sample_interval = int(fps * self.config.frame_sampling_interval)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Sample frames at specified interval
                if frame_number % sample_interval == 0:
                    timestamp = frame_number / fps
                    
                    # Calculate motion score
                    motion_score = self.motion_detector.calculate_motion_score(frame)
                    
                    # Detect burst activity
                    is_burst = self.burst_detector.update_motion_history(motion_score)
                    
                    # Calculate base quality score
                    quality_score = self.quality_assessor.calculate_quality_score(frame)
                    
                    # Apply adaptive enhancement
                    enhanced_frame, enhancement_applied = self.enhancer.enhance_frame(frame)
                    
                    # Save frame if it meets quality or activity criteria
                    should_save = (
                        quality_score >= self.config.base_quality_threshold or
                        motion_score >= self.config.motion_threshold or
                        is_burst
                    )
                    
                    if should_save:
                        # Save enhanced frame
                        frame_id = str(uuid.uuid4())
                        frame_path = os.path.join(self.frames_dir, f"{frame_id}.jpg")
                        
                        cv2.imwrite(frame_path, enhanced_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        
                        # Create frame data
                        frame_data = FrameData(
                            frame_path=frame_path,
                            timestamp=timestamp,
                            frame_number=frame_number,
                            quality_score=quality_score,
                            motion_score=motion_score,
                            burst_active=is_burst,
                            enhancement_applied=enhancement_applied
                        )
                        
                        # Calculate keyframe score
                        keyframe_score = self._calculate_keyframe_score(
                            quality_score, motion_score, is_burst
                        )
                        
                        # Determine selection reason
                        selection_reason = self._get_selection_reason(
                            quality_score, motion_score, is_burst
                        )
                        
                        keyframes.append(KeyframeResult(
                            frame_data=frame_data,
                            keyframe_score=keyframe_score,
                            selection_reason=selection_reason
                        ))
                
                frame_number += 1
                
                # Progress logging
                if frame_number % 1000 == 0:
                    progress = (frame_number / total_frames) * 100
                    logger.info(f"Processing progress: {progress:.1f}% ({len(keyframes)} keyframes)")
        
        finally:
            cap.release()
        
        logger.info(f"Keyframe extraction complete: {len(keyframes)} frames extracted")
        return keyframes
    
    def _calculate_keyframe_score(self, quality_score: float, motion_score: float, 
                                is_burst: bool) -> float:
        """Calculate combined keyframe importance score"""
        score = quality_score
        
        # Add motion bonus
        if motion_score > self.config.motion_threshold:
            score += motion_score * 0.5
        
        # Add burst bonus
        if is_burst:
            score *= self.config.burst_weight
        
        return min(score, 2.0)  # Cap at 2.0
    
    def _get_selection_reason(self, quality_score: float, motion_score: float, 
                            is_burst: bool) -> str:
        """Determine why frame was selected"""
        if is_burst:
            return "Burst Activity"
        elif motion_score >= self.config.motion_threshold:
            return "High Motion"
        elif quality_score >= self.config.base_quality_threshold:
            return "High Quality"
        else:
            return "Context Frame"
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "total_frames_processed": getattr(self, '_total_frames', 0),
            "keyframes_extracted": getattr(self, '_keyframes_count', 0),
            "enhancement_rate": getattr(self, '_enhancement_rate', 0.0),
            "burst_frames": getattr(self, '_burst_frames', 0),
            "high_motion_frames": getattr(self, '_high_motion_frames', 0)
        }
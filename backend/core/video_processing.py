"""
Optimized Video Processing for DetectifAI

This module contains optimized video processing components focusing on:
- Efficient keyframe extraction for security footage
- Selective frame enhancement only when needed
- Memory-optimized processing for large surveillance videos
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

class OptimizedFrameEnhancer:
    """Optimized frame enhancement for DetectifAI - only enhance when necessary"""
    
    def __init__(self, enable_clahe: bool = True, clahe_clip_limit: float = 2.0):
        self.enable_clahe = enable_clahe
        
        # Initialize CLAHE (skip denoising for performance)
        if enable_clahe:
            self.clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=(8, 8))
        
        logger.info(f"OptimizedFrameEnhancer initialized - CLAHE: {enable_clahe}")
    
    def enhance_frame_if_needed(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Enhance frame only if quality is poor (DetectifAI optimization)
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Tuple of (enhanced_frame, enhancement_applied)
        """
        try:
            # Quick quality assessment
            if not self._needs_enhancement(frame):
                return frame, False
            
            enhanced = frame.copy()
            
            # Apply CLAHE only to L channel for color frames
            if len(frame.shape) == 3 and self.enable_clahe:
                lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
                l_channel = lab[:, :, 0]
                l_enhanced = self.clahe.apply(l_channel)
                lab[:, :, 0] = l_enhanced
                enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                return enhanced, True
                
            elif len(frame.shape) == 2 and self.enable_clahe:
                # Grayscale frame
                enhanced = self.clahe.apply(enhanced)
                return enhanced, True
            
            return frame, False
            
        except Exception as e:
            logger.error(f"Error enhancing frame: {e}")
            return frame, False
    
    def _needs_enhancement(self, frame: np.ndarray) -> bool:
        """
        Quick quality check - only enhance genuinely poor quality frames
        """
        try:
            # Convert to grayscale for analysis
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Check brightness and contrast
            mean_brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Only enhance if frame has quality issues
            return (
                mean_brightness < 50 or    # Too dark
                mean_brightness > 200 or   # Too bright  
                contrast < 30             # Low contrast
            )
            
        except Exception:
            return False

class OptimizedVideoProcessor:
    """
    Optimized video processor for DetectifAI surveillance footage
    """
    
    def __init__(self, config=None):
        self.config = config
        self.frame_enhancer = OptimizedFrameEnhancer(
            enable_clahe=getattr(config, 'enable_adaptive_processing', True)
        )
        
        # Processing statistics
        self.processing_stats = {
            'frames_processed': 0,
            'frames_enhanced': 0,
            'keyframes_extracted': 0,
            'total_processing_time': 0.0
        }
        
        logger.info("OptimizedVideoProcessor initialized")
    
    def extract_keyframes_optimized(self, video_path: str, output_dir: str,
                                   fps_interval: float = 1.0) -> List[KeyframeResult]:
        """
        Extract keyframes with optimized processing for surveillance video

        Args:
            video_path: Path to input video
            output_dir: Directory to save keyframes
            fps_interval: Seconds between keyframes (default: 1 frame per second)

        Returns:
            List of KeyframeResult objects
        """
        start_time = time.time()
        keyframes = []

        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return []

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            logger.info(f"Video properties: {total_frames} frames, {fps:.2f} FPS, {duration:.2f}s")

            # Calculate frame interval
            frame_interval = int(fps * fps_interval) if fps > 0 else 30

            # Create output directory
            frames_dir = os.path.join(output_dir, 'frames')
            os.makedirs(frames_dir, exist_ok=True)

            frame_count = 0
            extracted_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Extract keyframes at specified intervals
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / fps if fps > 0 else frame_count

                    # Assess frame quality
                    quality_score = self._assess_frame_quality(frame)

                    # Enhance frame if needed
                    enhanced_frame, enhancement_applied = self.frame_enhancer.enhance_frame_if_needed(frame)

                    # Use consistent naming pattern for MinIO storage
                    frame_filename = f"frame_{frame_count:06d}.jpg"
                    frame_path = os.path.join(frames_dir, frame_filename)

                    cv2.imwrite(frame_path, enhanced_frame)

                    # Create frame data
                    frame_data = FrameData(
                        frame_path=frame_path,
                        timestamp=timestamp,
                        frame_number=frame_count,
                        quality_score=quality_score,
                        motion_score=0.0,  # Can be calculated if needed
                        burst_active=False,
                        enhancement_applied=enhancement_applied
                    )

                    keyframe_result = KeyframeResult(
                        frame_data=frame_data,
                        keyframe_score=quality_score,
                        selection_reason="Regular interval extraction"
                    )

                    keyframes.append(keyframe_result)
                    extracted_count += 1

                    # Update stats
                    if enhancement_applied:
                        self.processing_stats['frames_enhanced'] += 1

                frame_count += 1
                self.processing_stats['frames_processed'] += 1

                # Progress logging
                if frame_count % 1000 == 0:
                    progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                    logger.info(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")

            cap.release()

            # Update final statistics
            processing_time = time.time() - start_time
            self.processing_stats['keyframes_extracted'] = extracted_count
            self.processing_stats['total_processing_time'] = processing_time

            logger.info(f"✅ Keyframe extraction complete:")
            logger.info(f"   📊 Extracted {extracted_count} keyframes from {frame_count} frames")
            logger.info(f"   ⚡ Enhanced {self.processing_stats['frames_enhanced']} frames")
            logger.info(f"   ⏱️  Processing time: {processing_time:.2f}s")

            return keyframes

        except Exception as e:
            logger.error(f"Error in keyframe extraction: {e}")
            return []
    
    def _assess_frame_quality(self, frame: np.ndarray) -> float:
        """
        Quick frame quality assessment for keyframe selection
        """
        try:
            # Convert to grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Calculate Laplacian variance (focus measure)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize to 0-1 scale (higher = better quality)
            quality_score = min(laplacian_var / 1000.0, 1.0)
            
            return quality_score
            
        except Exception:
            return 0.5  # Default quality score
    
    def extract_keyframes(self, video_path: str) -> List[KeyframeResult]:
        """
        Main keyframe extraction method for DetectifAI pipeline compatibility
        
        Args:
            video_path: Path to input video file
            
        Returns:
            List of KeyframeResult objects
        """
        if not self.config:
            logger.error("No configuration provided for keyframe extraction")
            return []
        
        # Use output directory from config
        output_dir = getattr(self.config, 'output_base_dir', 'video_processing_outputs')
        fps_interval = getattr(self.config, 'keyframe_extraction_fps', 1.0)
        
        return self.extract_keyframes_optimized(video_path, output_dir, fps_interval)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.processing_stats.copy()

class StreamingVideoProcessor:
    """
    Streaming processor for large surveillance videos to reduce memory usage
    """
    
    def __init__(self, config=None):
        self.config = config
        self.chunk_size = getattr(config, 'video_chunk_size', 1000)  # Process 1000 frames at a time
        
    def process_video_in_chunks(self, video_path: str, output_dir: str, 
                               chunk_processor_func) -> Dict[str, Any]:
        """
        Process large videos in chunks to manage memory usage
        
        Args:
            video_path: Path to input video
            output_dir: Output directory
            chunk_processor_func: Function to process each chunk
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'total_frames': 0,
            'processing_time': 0.0
        }
        
        start_time = time.time()
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return results
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            results['total_frames'] = total_frames
            results['total_chunks'] = (total_frames + self.chunk_size - 1) // self.chunk_size
            
            logger.info(f"Processing video in {results['total_chunks']} chunks of {self.chunk_size} frames")
            
            frame_count = 0
            chunk_count = 0
            
            while frame_count < total_frames:
                # Process chunk
                chunk_frames = []
                chunk_start = frame_count
                
                # Read chunk frames
                for i in range(self.chunk_size):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    chunk_frames.append({
                        'frame': frame,
                        'frame_number': frame_count,
                        'timestamp': frame_count / fps if fps > 0 else frame_count
                    })
                    frame_count += 1
                
                if chunk_frames:
                    # Process chunk
                    chunk_processor_func(chunk_frames, chunk_count, output_dir)
                    chunk_count += 1
                    results['processed_chunks'] += 1
                    
                    # Clear memory
                    del chunk_frames
                    
                    logger.info(f"Processed chunk {chunk_count}/{results['total_chunks']}")
            
            cap.release()
            results['processing_time'] = time.time() - start_time
            
            logger.info(f"✅ Streaming processing complete in {results['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in streaming processing: {e}")
        
        return results

def create_optimized_processor(config=None):
    """Factory function to create optimized video processor"""
    return OptimizedVideoProcessor(config)
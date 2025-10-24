"""
Video Compression Module

This module handles:
- Video compression with configurable quality settings
- Resolution scaling
- Format conversion
- Compression statistics and reporting
"""

import os
import subprocess
import json
import cv2
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VideoCompressor:
    """Handle video compression and format conversion"""
    
    def __init__(self, config):
        self.config = config
        self.compressed_dir = os.path.join(config.output_base_dir, "compressed")
        os.makedirs(self.compressed_dir, exist_ok=True)
        
        # Verify FFmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
        
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            available = result.returncode == 0
            logger.info(f"FFmpeg available: {available}")
            return available
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.warning(f"FFmpeg not available: {e}")
            return False
    
    def compress_video(self, input_path: str, output_filename: str = None) -> str:
        """
        Compress video with configured settings
        
        Args:
            input_path: Path to input video
            output_filename: Optional custom output filename
            
        Returns:
            Path to compressed video
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        # Generate output path
        if output_filename is None:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{base_name}_compressed.{self.config.video_output_format}"
        
        output_path = os.path.join(self.compressed_dir, output_filename)
        
        logger.info(f"Compressing video: {input_path} -> {output_path}")
        
        if self.ffmpeg_available:
            return self._compress_with_ffmpeg(input_path, output_path)
        else:
            return self._compress_with_opencv(input_path, output_path)
    
    def _compress_with_ffmpeg(self, input_path: str, output_path: str) -> str:
        """Compress video using FFmpeg"""
        try:
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command(input_path, output_path)
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run compression
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                if os.path.exists(output_path):
                    # Get compression statistics
                    stats = self._get_compression_stats(input_path, output_path)
                    logger.info(f"✅ Compression successful: {stats}")
                    return output_path
                else:
                    logger.error("FFmpeg completed but output file not found")
                    return ""
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg compression timed out")
            return ""
        except Exception as e:
            logger.error(f"FFmpeg compression failed: {e}")
            return ""
    
    def _build_ffmpeg_command(self, input_path: str, output_path: str) -> list:
        """Build FFmpeg command with configured parameters"""
        cmd = ['ffmpeg', '-y', '-i', input_path]
        
        # Video codec and quality settings
        cmd.extend(['-c:v', 'libx264'])
        cmd.extend(['-preset', self.config.compression_preset])
        cmd.extend(['-crf', str(self.config.compression_crf)])
        
        # Resolution scaling
        if self.config.output_resolution != "original":
            scale_filter = self._get_scale_filter()
            if scale_filter:
                cmd.extend(['-vf', scale_filter])
        
        # Audio settings (copy or remove)
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        
        # Output optimizations
        cmd.extend(['-movflags', '+faststart'])
        
        cmd.append(output_path)
        
        return cmd
    
    def _get_scale_filter(self) -> str:
        """Get FFmpeg scale filter for resolution"""
        resolution_map = {
            "720p": "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "1080p": "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "480p": "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2"
        }
        
        return resolution_map.get(self.config.output_resolution, "")
    
    def _compress_with_opencv(self, input_path: str, output_path: str) -> str:
        """Fallback compression using OpenCV"""
        logger.info("Using OpenCV for video compression (fallback)")
        
        try:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                logger.error(f"Cannot open input video: {input_path}")
                return ""
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Adjust resolution if needed
            output_width, output_height = self._get_output_dimensions(width, height)
            
            # Set up video writer with H.264 codec for better browser compatibility
            # Try multiple codecs in order of preference
            codec_options = [
                'avc1',  # H.264 (best browser support)
                'H264',  # H.264 alternative
                'X264',  # H.264 alternative
                'mp4v'   # MPEG-4 fallback
            ]
            
            out = None
            for codec in codec_options:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    out = cv2.VideoWriter(output_path, fourcc, fps, (output_width, output_height))
                    if out.isOpened():
                        logger.info(f"Using codec: {codec}")
                        break
                    out.release()
                except Exception as e:
                    logger.warning(f"Codec {codec} failed: {e}")
                    continue
            
            if not out or not out.isOpened():
                logger.error("Cannot create output video writer with any codec")
                cap.release()
                return ""
            
            # Process frames
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize frame if needed
                if (output_width, output_height) != (width, height):
                    frame = cv2.resize(frame, (output_width, output_height))
                
                out.write(frame)
                frame_count += 1
                
                # Progress logging
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"Compression progress: {progress:.1f}%")
            
            cap.release()
            out.release()
            
            if os.path.exists(output_path):
                stats = self._get_compression_stats(input_path, output_path)
                logger.info(f"✅ OpenCV compression successful: {stats}")
                return output_path
            else:
                logger.error("OpenCV compression failed - output file not created")
                return ""
                
        except Exception as e:
            logger.error(f"OpenCV compression failed: {e}")
            return ""
    
    def _get_output_dimensions(self, input_width: int, input_height: int) -> Tuple[int, int]:
        """Calculate output dimensions based on configuration"""
        if self.config.output_resolution == "original":
            return input_width, input_height
        
        resolution_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "480p": (854, 480)
        }
        
        target_width, target_height = resolution_map.get(
            self.config.output_resolution, 
            (input_width, input_height)
        )
        
        # Maintain aspect ratio
        aspect_ratio = input_width / input_height
        
        if aspect_ratio > target_width / target_height:
            # Width-constrained
            output_width = target_width
            output_height = int(target_width / aspect_ratio)
        else:
            # Height-constrained
            output_height = target_height
            output_width = int(target_height * aspect_ratio)
        
        # Ensure even dimensions (required for some codecs)
        output_width = (output_width // 2) * 2
        output_height = (output_height // 2) * 2
        
        return output_width, output_height
    
    def _get_compression_stats(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Get compression statistics"""
        try:
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            
            compression_ratio = input_size / output_size if output_size > 0 else 0
            size_reduction = ((input_size - output_size) / input_size) * 100
            
            # Get video properties
            input_cap = cv2.VideoCapture(input_path)
            output_cap = cv2.VideoCapture(output_path)
            
            stats = {
                'input_size_mb': round(input_size / (1024*1024), 2),
                'output_size_mb': round(output_size / (1024*1024), 2),
                'compression_ratio': round(compression_ratio, 2),
                'size_reduction_percent': round(size_reduction, 1),
                'input_resolution': f"{int(input_cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(input_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
                'output_resolution': f"{int(output_cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(output_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
                'input_fps': round(input_cap.get(cv2.CAP_PROP_FPS), 2),
                'output_fps': round(output_cap.get(cv2.CAP_PROP_FPS), 2)
            }
            
            input_cap.release()
            output_cap.release()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get compression stats: {e}")
            return {}
    
    def batch_compress(self, input_directory: str, output_directory: str = None) -> Dict[str, str]:
        """
        Compress multiple videos in a directory
        
        Args:
            input_directory: Directory containing videos to compress
            output_directory: Optional output directory (uses compressed_dir by default)
            
        Returns:
            Dictionary mapping input paths to output paths
        """
        if output_directory is None:
            output_directory = self.compressed_dir
        
        os.makedirs(output_directory, exist_ok=True)
        
        # Find video files
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
        video_files = []
        
        for filename in os.listdir(input_directory):
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                video_files.append(os.path.join(input_directory, filename))
        
        logger.info(f"Found {len(video_files)} videos to compress")
        
        results = {}
        
        for video_path in video_files:
            try:
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_filename = f"{base_name}_compressed.{self.config.video_output_format}"
                output_path = os.path.join(output_directory, output_filename)
                
                compressed_path = self._compress_with_ffmpeg(video_path, output_path) if self.ffmpeg_available else self._compress_with_opencv(video_path, output_path)
                
                if compressed_path:
                    results[video_path] = compressed_path
                    logger.info(f"✅ Compressed: {os.path.basename(video_path)}")
                else:
                    logger.error(f"❌ Failed to compress: {os.path.basename(video_path)}")
                    
            except Exception as e:
                logger.error(f"Error compressing {video_path}: {e}")
        
        logger.info(f"Batch compression complete: {len(results)}/{len(video_files)} successful")
        return results
    
    def save_compression_report(self, compression_results: Dict[str, Any], 
                              output_path: str) -> bool:
        """Save compression report to JSON file"""
        try:
            report = {
                'compression_info': {
                    'timestamp': datetime.now().isoformat(),
                    'config': {
                        'output_resolution': self.config.output_resolution,
                        'compression_crf': self.config.compression_crf,
                        'compression_preset': self.config.compression_preset,
                        'video_output_format': self.config.video_output_format
                    }
                },
                'results': compression_results
            }
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Compression report saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save compression report: {e}")
            return False
    
    def estimate_compression_time(self, input_path: str) -> Optional[float]:
        """Estimate compression time based on video properties"""
        try:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            cap.release()
            
            # Rough estimation: 0.1-0.5x realtime depending on preset
            preset_multipliers = {
                'ultrafast': 0.1,
                'fast': 0.2,
                'medium': 0.3,
                'slow': 0.5
            }
            
            multiplier = preset_multipliers.get(self.config.compression_preset, 0.3)
            estimated_time = duration * multiplier
            
            return estimated_time
            
        except Exception as e:
            logger.error(f"Failed to estimate compression time: {e}")
            return None
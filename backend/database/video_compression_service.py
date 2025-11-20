"""
Video Compression and Storage Service for DetectifAI

This module handles video compression and MinIO storage for compressed videos.
"""

import os
import cv2
import subprocess
import logging
from io import BytesIO
from typing import Dict, Optional
from datetime import timedelta
from minio.error import S3Error

logger = logging.getLogger(__name__)

class VideoCompressionService:
    """Service for compressing videos and storing in MinIO"""

    def __init__(self, db_manager, config=None):
        self.minio = db_manager.minio_client
        self.bucket = db_manager.config.minio_video_bucket  # Store compressed videos in the videos bucket
        self.config = config

        # Default compression settings
        self.output_resolution = "720p"  # 720p for web delivery
        self.compression_crf = 23  # 0-51, lower = better quality (23 is default)
        self.compression_preset = "medium"  # ultrafast to veryslow

        # Check if FFmpeg is available
        self.ffmpeg_available = self._check_ffmpeg_available()

    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def compress_and_store(self, input_path: str, video_id: str) -> Optional[Dict]:
        """Compress video and store in MinIO and locally"""
        try:
            # Create local storage directory
            local_dir = os.path.join("video_processing_outputs", "compressed", video_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, "video.mp4")

            # Use BytesIO for in-memory compression
            from io import BytesIO
            compressed_buffer = BytesIO()

            # Try FFmpeg first if available, otherwise use OpenCV
            if self.ffmpeg_available:
                success = self._compress_with_ffmpeg_to_buffer(input_path, compressed_buffer)
                if not success:
                    logger.warning("FFmpeg compression failed, falling back to OpenCV")
                    compressed_buffer.seek(0)  # Reset buffer position
                    success = self._compress_with_opencv_to_buffer(input_path, compressed_buffer)
            else:
                logger.info("FFmpeg not available, using OpenCV compression")
                success = self._compress_with_opencv_to_buffer(input_path, compressed_buffer)

            if not success:
                logger.error("Both compression methods failed")
                return None

            # Get buffer contents
            compressed_buffer.seek(0)
            compressed_data = compressed_buffer.getvalue()
            compressed_size = len(compressed_data)

            # Save locally
            with open(local_path, 'wb') as f:
                f.write(compressed_data)
            logger.info(f"✅ Video saved locally: {local_path}")

            # Calculate compression stats
            original_size = os.path.getsize(input_path)
            compression_ratio = ((original_size - compressed_size) / original_size) * 100

            # Upload directly to MinIO using consistent path structure
            minio_path = f"compressed/{video_id}/video.mp4"
            compressed_buffer.seek(0)  # Reset buffer for MinIO upload
            self.minio.put_object(
                self.bucket,
                minio_path,
                compressed_buffer,
                length=compressed_size,
                content_type='video/mp4'
            )

            result = {
                'success': True,
                'minio_path': minio_path,
                'local_path': local_path,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': round(compression_ratio, 2),
                'output_resolution': self.output_resolution
            }

            logger.info(f"✅ Video compressed and stored: {compression_ratio:.1f}% reduction")
            return result

        except Exception as e:
            logger.error(f"❌ Compression and storage failed: {e}")
            return None

    def get_compressed_video_presigned_url(self, video_id: str, expires: timedelta = timedelta(hours=1)) -> str:
        """Generate presigned URL for compressed video access"""
        try:
            minio_path = f"compressed/{video_id}/video.mp4"
            return self.minio.presigned_get_object(self.bucket, minio_path, expires=expires)
        except S3Error as e:
            logger.error(f"❌ Failed to generate presigned URL for compressed video: {e}")
            return None
    
    def _compress_with_ffmpeg(self, input_path: str, output_path: str) -> bool:
        """Compress video using FFmpeg"""
        try:
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',  # H.264 codec
                '-crf', str(self.compression_crf),
                '-preset', self.compression_preset,
                '-movflags', '+faststart',  # Enable web playback
                '-y'  # Overwrite output file
            ]
            
            # Add resolution scaling if needed
            if self.output_resolution == "720p":
                cmd.extend(['-vf', 'scale=1280:720:force_original_aspect_ratio=decrease'])  # Scale to 720p preserving aspect ratio
            elif self.output_resolution == "480p":
                cmd.extend(['-vf', 'scale=854:480:force_original_aspect_ratio=decrease'])  # Scale to 480p preserving aspect ratio
            
            cmd.append(output_path)
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info("✅ FFmpeg compression successful")
                return True
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"FFmpeg compression failed: {e}")
            return False
    
    def _compress_with_ffmpeg_to_buffer(self, input_path: str, output_buffer: BytesIO) -> bool:
        """Compress video using FFmpeg with temporary file (more reliable than pipe)"""
        import tempfile
        try:
            # Create temporary file for FFmpeg output
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Build FFmpeg command to output to temporary file
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',  # H.264 codec
                '-crf', str(self.compression_crf),
                '-preset', self.compression_preset,
                '-movflags', '+faststart',  # Enable web playback (safe for file output)
                '-y'  # Overwrite output
            ]
            
            # Add resolution scaling if needed
            if self.output_resolution == "720p":
                cmd.extend(['-vf', 'scale=1280:720:force_original_aspect_ratio=decrease'])  # Scale to 720p preserving aspect ratio
            elif self.output_resolution == "480p":
                cmd.extend(['-vf', 'scale=854:480:force_original_aspect_ratio=decrease'])  # Scale to 480p preserving aspect ratio
            
            # Add output file
            cmd.append(temp_path)
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and os.path.exists(temp_path):
                # Read temporary file into buffer
                with open(temp_path, 'rb') as f:
                    output_buffer.write(f.read())
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                logger.info("✅ FFmpeg compression to buffer successful")
                return True
            else:
                # Clean up temporary file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                logger.error(f"FFmpeg error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"FFmpeg compression to buffer failed: {e}")
            return False
    
    def _compress_with_opencv_to_buffer(self, input_path: str, output_buffer: BytesIO) -> bool:
        """Fallback compression using OpenCV directly to a buffer"""
        try:
            # Open input video
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                logger.error(f"Cannot open input video: {input_path}")
                return False
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Calculate new dimensions
            if self.output_resolution == "720p":
                new_height = 720
                new_width = int((width / height) * new_height)
            elif self.output_resolution == "480p":
                new_height = 480
                new_width = int((width / height) * new_height)
            else:
                new_width, new_height = width, height
            
            # Create temporary file for OpenCV (required for VideoWriter)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                temp_path,
                fourcc,
                fps,
                (new_width, new_height)
            )
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize frame if needed
                if (new_width, new_height) != (width, height):
                    frame = cv2.resize(frame, (new_width, new_height))
                
                out.write(frame)
            
            cap.release()
            out.release()
            
            # Read compressed file into buffer
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    output_buffer.write(f.read())
                os.unlink(temp_path)  # Delete temporary file
                logger.info("✅ OpenCV compression to buffer successful")
                return True
            else:
                logger.error("OpenCV compression failed - output file not created")
                return False
                
        except Exception as e:
            logger.error(f"OpenCV compression to buffer failed: {e}")
            return False
    
    def _compress_with_opencv(self, input_path: str, output_path: str) -> bool:
        """Fallback compression using OpenCV"""
        try:
            # Open input video
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                logger.error(f"Cannot open input video: {input_path}")
                return False
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Calculate new dimensions
            if self.output_resolution == "720p":
                new_height = 720
                new_width = int((width / height) * new_height)
            elif self.output_resolution == "480p":
                new_height = 480
                new_width = int((width / height) * new_height)
            else:
                new_width, new_height = width, height
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_path,
                fourcc,
                fps,
                (new_width, new_height)
            )
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize frame
                if (new_width, new_height) != (width, height):
                    frame = cv2.resize(frame, (new_width, new_height))
                
                out.write(frame)
            
            cap.release()
            out.release()
            
            if os.path.exists(output_path):
                logger.info("✅ OpenCV compression successful")
                return True
            else:
                logger.error("OpenCV compression failed - output file not created")
                return False
                
        except Exception as e:
            logger.error(f"OpenCV compression failed: {e}")
            return False
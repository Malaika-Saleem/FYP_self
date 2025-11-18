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
        logger.info(f"🔧 compress_and_store called for {video_id}")
        logger.info(f"🔧 Input path: {input_path}")
        logger.info(f"🔧 Input path exists: {os.path.exists(input_path) if input_path else 'None'}")
        
        try:
            # Create local storage directory
            local_dir = os.path.join("video_processing_outputs", "compressed", video_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, "video.mp4")
            logger.info(f"🔧 Local directory created: {local_dir}")
            logger.info(f"🔧 Target local path: {local_path}")

            # Use BytesIO for in-memory compression
            from io import BytesIO
            compressed_buffer = BytesIO()
            logger.info(f"🔧 FFmpeg available: {self.ffmpeg_available}")

            # Try FFmpeg first if available, otherwise use OpenCV
            if self.ffmpeg_available:
                logger.info("🔧 Attempting FFmpeg compression...")
                success = self._compress_with_ffmpeg_to_buffer(input_path, compressed_buffer)
                logger.info(f"🔧 FFmpeg compression result: {success}")
                if not success:
                    logger.warning("FFmpeg compression failed, falling back to OpenCV")
                    compressed_buffer.seek(0)  # Reset buffer position
                    compressed_buffer.truncate(0)  # Clear buffer
                    logger.info("🔧 Attempting OpenCV fallback compression...")
                    success = self._compress_with_opencv_to_buffer(input_path, compressed_buffer)
                    logger.info(f"🔧 OpenCV fallback compression result: {success}")
            else:
                logger.info("FFmpeg not available, using OpenCV compression")
                logger.info("🔧 Attempting OpenCV compression...")
                success = self._compress_with_opencv_to_buffer(input_path, compressed_buffer)
                logger.info(f"🔧 OpenCV compression result: {success}")

            if not success:
                logger.error("Both compression methods failed")
                return None

            # Get buffer contents
            compressed_buffer.seek(0)
            compressed_data = compressed_buffer.getvalue()
            compressed_size = len(compressed_data)

            # Validate that we have a valid compressed video
            if compressed_size < 1000:  # Less than 1KB is definitely invalid
                logger.error(f"Compressed video too small ({compressed_size} bytes) - compression likely failed")
                return None

            # Save locally
            with open(local_path, 'wb') as f:
                f.write(compressed_data)
            logger.info(f"✅ Video saved locally: {local_path}")

            # Validate the local file is playable using OpenCV
            try:
                test_cap = cv2.VideoCapture(local_path)
                if test_cap.isOpened():
                    frame_count = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    test_cap.release()
                    if frame_count > 0:
                        logger.info(f"✅ Compressed video validated ({frame_count} frames)")
                    else:
                        logger.error("Compressed video has no frames - invalid")
                        return None
                else:
                    logger.error("Compressed video cannot be opened - invalid format")
                    return None
            except Exception as e:
                logger.warning(f"Could not validate compressed video: {e}")
                # Continue anyway as validation might fail but video could still be playable

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
                cmd.extend(['-vf', 'scale=-1:720'])  # Scale to 720p preserving aspect ratio
            elif self.output_resolution == "480p":
                cmd.extend(['-vf', 'scale=-1:480'])  # Scale to 480p preserving aspect ratio
            
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
        """Compress video using FFmpeg directly to a buffer"""
        logger.info("🔧 Starting FFmpeg compression to buffer...")
        try:
            # Build FFmpeg command to output to pipe
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',  # H.264 codec
                '-c:a', 'aac',      # AAC audio codec  
                '-crf', str(self.compression_crf),
                '-preset', self.compression_preset,
                '-movflags', 'frag_keyframe+empty_moov',  # Enable streaming/pipe output
            ]
            
            # Add resolution scaling if needed
            if self.output_resolution == "720p":
                cmd.extend(['-vf', 'scale=-1:720'])  # Scale to 720p preserving aspect ratio
            elif self.output_resolution == "480p":
                cmd.extend(['-vf', 'scale=-1:480'])  # Scale to 480p preserving aspect ratio
            
            # Add output format and pipe - use fragmented MP4 for pipe output
            cmd.extend(['-f', 'mp4', '-y', 'pipe:1'])
            
            logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg with pipe output
            logger.info("🔧 Starting FFmpeg process...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"🔧 FFmpeg process started with PID: {process.pid}")
            
            # Use threading to read stdout and stderr simultaneously to avoid deadlock
            import threading
            import queue
            
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()
            
            def read_stdout():
                """Read stdout in a separate thread"""
                try:
                    chunk_size = 8192
                    bytes_read = 0
                    while True:
                        chunk = process.stdout.read(chunk_size)
                        if not chunk:
                            logger.info("🔧 No more chunks to read from FFmpeg stdout")
                            break
                        stdout_queue.put(chunk)
                        bytes_read += len(chunk)
                        if bytes_read % 500000 == 0:  # Log every 500KB
                            logger.info(f"🔧 Read {bytes_read} bytes so far...")
                except Exception as e:
                    logger.error(f"Error reading stdout: {e}")
                finally:
                    stdout_queue.put(None)  # Signal end of data
            
            def read_stderr():
                """Read stderr in a separate thread"""
                try:
                    stderr_data = process.stderr.read()
                    stderr_queue.put(stderr_data)
                except Exception as e:
                    logger.error(f"Error reading stderr: {e}")
                    stderr_queue.put(b'')
            
            # Start reading threads
            logger.info("🔧 Starting stdout and stderr reading threads...")
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Read stdout data as it becomes available
            logger.info("🔧 Reading FFmpeg output from queue...")
            total_bytes = 0
            while True:
                try:
                    chunk = stdout_queue.get(timeout=5)  # 5 second timeout per chunk
                    if chunk is None:  # End of data
                        logger.info("🔧 Finished reading all FFmpeg output chunks")
                        break
                    output_buffer.write(chunk)
                    total_bytes += len(chunk)
                except queue.Empty:
                    # Check if process is still running
                    if process.poll() is not None:
                        logger.info("🔧 FFmpeg process completed, checking for remaining data...")
                        # Process finished, get any remaining data
                        try:
                            while True:
                                chunk = stdout_queue.get_nowait()
                                if chunk is None:
                                    break
                                output_buffer.write(chunk)
                                total_bytes += len(chunk)
                        except queue.Empty:
                            break
                        break
                    else:
                        logger.warning("🔧 No data from FFmpeg for 5 seconds, but process still running...")
                        continue
            
            # Wait for threads to complete
            logger.info("🔧 Waiting for reading threads to complete...")
            stdout_thread.join(timeout=10)
            stderr_thread.join(timeout=10)
            
            # Get stderr data
            try:
                stderr_data = stderr_queue.get(timeout=1)
            except queue.Empty:
                stderr_data = b''
            
            # Wait for process to complete
            logger.info("🔧 Waiting for FFmpeg process to complete...")
            try:
                return_code = process.wait(timeout=10)  # Shorter timeout since we've read the data
                logger.info(f"🔧 FFmpeg process completed with return code: {return_code}")
            except subprocess.TimeoutExpired:
                logger.error("🔧 FFmpeg process timed out after reading data")
                process.kill()
                process.wait()
                return False
            
            if return_code == 0:
                logger.info(f"✅ FFmpeg compression to buffer successful ({total_bytes} bytes)")
                return True
            else:
                stderr_text = stderr_data.decode() if stderr_data else 'No error details'
                logger.error(f"FFmpeg failed with return code {return_code}: {stderr_text}")
                return False
                
        except Exception as e:
            logger.error(f"FFmpeg compression to buffer failed: {e}")
            import traceback
            logger.error(f"FFmpeg exception traceback: {traceback.format_exc()}")
            return False
    
    def _compress_with_opencv_to_buffer(self, input_path: str, output_buffer: BytesIO) -> bool:
        """Fallback compression using OpenCV directly to a buffer"""
        logger.info("🔧 Starting OpenCV compression to buffer...")
        try:
            # Open input video
            logger.info(f"🔧 Opening input video: {input_path}")
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
            
            # Create video writer with web-compatible codec
            # For MP4 container, we need H.264 compatible codec
            # Change temp file to .avi to use XVID, then convert to MP4
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.avi', delete=False) as avi_temp:
                avi_temp_path = avi_temp.name
            
            # Use XVID with AVI container (more reliable than MP4 with OpenCV)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(
                avi_temp_path,
                fourcc,
                fps,
                (new_width, new_height)
            )
            
            if not out.isOpened():
                logger.error("Could not initialize video writer with XVID codec")
                cap.release()
                return False
            
            logger.info("Using XVID codec with AVI container")
            
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
            
            # Convert AVI to MP4 using FFmpeg for web compatibility
            if os.path.exists(avi_temp_path):
                try:
                    # Use FFmpeg to convert AVI to web-compatible MP4
                    convert_cmd = [
                        'ffmpeg',
                        '-i', avi_temp_path,
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-preset', 'fast',
                        '-movflags', '+faststart',  # Enable web playback
                        '-f', 'mp4',
                        temp_path,
                        '-y'  # Overwrite
                    ]
                    
                    result = subprocess.run(convert_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0 and os.path.exists(temp_path):
                        # Read the converted MP4 file
                        with open(temp_path, 'rb') as f:
                            output_buffer.write(f.read())
                        os.unlink(temp_path)  # Delete MP4 temp file
                        os.unlink(avi_temp_path)  # Delete AVI temp file
                        logger.info("✅ OpenCV + FFmpeg conversion to buffer successful")
                        return True
                    else:
                        logger.warning(f"FFmpeg conversion failed: {result.stderr}")
                        # Fallback: use AVI file directly (less compatible but working)
                        with open(avi_temp_path, 'rb') as f:
                            output_buffer.write(f.read())
                        os.unlink(avi_temp_path)
                        logger.info("✅ OpenCV compression to buffer successful (AVI format)")
                        return True
                        
                except Exception as convert_err:
                    logger.warning(f"Failed to convert to MP4: {convert_err}")
                    # Fallback: use AVI file
                    with open(avi_temp_path, 'rb') as f:
                        output_buffer.write(f.read())
                    os.unlink(avi_temp_path)
                    logger.info("✅ OpenCV compression to buffer successful (AVI format)")
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
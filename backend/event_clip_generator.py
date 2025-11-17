"""
Event Clip Generator

Generates video clips from events for viewing, playing, and downloading.
Extracts clips from the original or compressed video based on event timestamps.
Supports annotation with face bounding boxes for person search results.
"""

import os
import cv2
import subprocess
import logging
import uuid
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class EventClipGenerator:
    """Generate video clips from events"""
    
    def __init__(self, output_dir: str = "video_processing_outputs/clips"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def extract_clip(self, video_path: str, start_time: float, end_time: float, 
                   event_id: str, video_id: str = None) -> Optional[str]:
        """
        Extract a video clip from a video file
        
        Args:
            video_path: Path to source video
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            event_id: Event identifier
            video_id: Optional video identifier for organizing clips
            
        Returns:
            Path to extracted clip file, or None if extraction failed
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        
        try:
            # Create clip filename
            clip_id = f"{event_id}_{uuid.uuid4().hex[:8]}"
            clip_filename = f"{clip_id}.mp4"
            
            # Create output directory for this video if video_id provided
            if video_id:
                clip_dir = os.path.join(self.output_dir, video_id)
                os.makedirs(clip_dir, exist_ok=True)
                clip_path = os.path.join(clip_dir, clip_filename)
            else:
                clip_path = os.path.join(self.output_dir, clip_filename)
            
            # Calculate duration
            duration = end_time - start_time
            
            # Use ffmpeg to extract clip (more reliable than OpenCV)
            try:
                # Try ffmpeg first (faster and more reliable)
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-c', 'copy',  # Copy codec (fast, no re-encoding)
                    '-avoid_negative_ts', 'make_zero',
                    '-y',  # Overwrite output file
                    clip_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60  # 60 second timeout
                )
                
                if result.returncode == 0 and os.path.exists(clip_path):
                    logger.info(f"✅ Extracted clip: {clip_path} ({duration:.2f}s)")
                    return clip_path
                else:
                    logger.warning(f"FFmpeg extraction failed, trying OpenCV fallback: {result.stderr}")
                    # Fallback to OpenCV
                    return self._extract_clip_opencv(video_path, start_time, end_time, clip_path)
                    
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
                logger.warning(f"FFmpeg not available or failed: {e}, using OpenCV fallback")
                # Fallback to OpenCV
                return self._extract_clip_opencv(video_path, start_time, end_time, clip_path)
                
        except Exception as e:
            logger.error(f"Error extracting clip: {e}")
            return None
    
    def _extract_clip_opencv(self, video_path: str, start_time: float, 
                            end_time: float, output_path: str) -> Optional[str]:
        """Extract clip using OpenCV (fallback method)"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate frame numbers
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            # Set starting position
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            frame_count = start_frame
            while frame_count <= end_frame:
                ret, frame = cap.read()
                if not ret:
                    break
                
                out.write(frame)
                frame_count += 1
            
            cap.release()
            out.release()
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"✅ Extracted clip using OpenCV: {output_path}")
                return output_path
            else:
                logger.error(f"OpenCV extraction failed: output file is empty or missing")
                return None
                
        except Exception as e:
            logger.error(f"OpenCV clip extraction error: {e}")
            return None
    
    def extract_annotated_clip(self, video_path: str, start_time: float, end_time: float,
                              face_id: str, face_detections: List[Dict[str, Any]],
                              video_id: str = None, person_name: str = None) -> Optional[str]:
        """
        Extract and annotate a video clip with bounding boxes for a specific person
        
        Args:
            video_path: Path to source video
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            face_id: Face identifier to highlight
            face_detections: List of face detection records with bounding boxes and timestamps
            video_id: Optional video identifier
            person_name: Optional person name to display on annotations
            
        Returns:
            Path to annotated clip file, or None if extraction failed
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        
        try:
            # Create annotated clip filename
            clip_id = f"annotated_{face_id}_{uuid.uuid4().hex[:8]}"
            clip_filename = f"{clip_id}.mp4"
            
            # Create output directory
            if video_id:
                clip_dir = os.path.join(self.output_dir, video_id, "annotated")
                os.makedirs(clip_dir, exist_ok=True)
                clip_path = os.path.join(clip_dir, clip_filename)
            else:
                annotated_dir = os.path.join(self.output_dir, "annotated")
                os.makedirs(annotated_dir, exist_ok=True)
                clip_path = os.path.join(annotated_dir, clip_filename)
            
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate frame numbers
            start_frame = int(start_time * fps)
            end_frame = min(int(end_time * fps), total_frames - 1)
            
            # Create a map of frame_number -> bounding boxes for quick lookup
            frame_bbox_map = {}
            for detection in face_detections:
                if detection.get('face_id') == face_id:
                    # Try multiple timestamp fields
                    timestamp = (
                        detection.get('timestamp') or 
                        detection.get('detected_at') or
                        (detection.get('detected_at').timestamp() if isinstance(detection.get('detected_at'), type(datetime.now())) else 0) or
                        0
                    )
                    
                    # If timestamp is a datetime object, convert to seconds
                    if hasattr(timestamp, 'timestamp'):
                        timestamp = timestamp.timestamp()
                    
                    frame_num = int(timestamp * fps) if timestamp > 0 else 0
                    
                    # Try multiple bbox field names
                    bbox = (
                        detection.get('bounding_box') or 
                        detection.get('bounding_boxes') or
                        None
                    )
                    
                    if bbox:
                        # Handle different bbox formats: [x1, y1, x2, y2] or {"x1": ..., "y1": ..., ...}
                        try:
                            if isinstance(bbox, dict):
                                x1 = int(bbox.get('x1', bbox.get(0, 0)))
                                y1 = int(bbox.get('y1', bbox.get(1, 0)))
                                x2 = int(bbox.get('x2', bbox.get(2, 0)))
                                y2 = int(bbox.get('y2', bbox.get(3, 0)))
                            elif isinstance(bbox, list) and len(bbox) >= 4:
                                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                            else:
                                continue
                            
                            # Validate bounding box coordinates
                            if x1 >= 0 and y1 >= 0 and x2 > x1 and y2 > y1:
                                # Store for multiple nearby frames to handle timestamp inaccuracies
                                for offset in range(-2, 3):  # ±2 frames tolerance
                                    frame_bbox_map[frame_num + offset] = (x1, y1, x2, y2)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid bounding box format: {bbox}, error: {e}")
                            continue
            
            # Set starting position
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
            
            frame_count = start_frame
            frames_annotated = 0
            
            while frame_count <= end_frame:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Check if this frame has a bounding box for this face
                if frame_count in frame_bbox_map:
                    x1, y1, x2, y2 = frame_bbox_map[frame_count]
                    
                    # Draw bounding box (green for person detection)
                    color = (0, 255, 0)  # Green in BGR
                    thickness = 3
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                    
                    # Draw label
                    label = person_name if person_name else "Detected Person"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                    
                    # Draw label background
                    cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                                 (x1 + label_size[0] + 10, y1), color, -1)
                    
                    # Draw label text
                    cv2.putText(frame, label, (x1 + 5, y1 - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    frames_annotated += 1
                
                out.write(frame)
                frame_count += 1
            
            cap.release()
            out.release()
            
            if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                logger.info(f"✅ Created annotated clip: {clip_path} ({frames_annotated} frames annotated)")
                return clip_path
            else:
                logger.error(f"Annotated clip creation failed: output file is empty or missing")
                return None
                
        except Exception as e:
            logger.error(f"Error creating annotated clip: {e}")
            return None
    
    def get_clip_info(self, clip_path: str) -> Dict[str, Any]:
        """Get information about a clip file"""
        if not os.path.exists(clip_path):
            return {}
        
        try:
            cap = cv2.VideoCapture(clip_path)
            if not cap.isOpened():
                return {}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            file_size = os.path.getsize(clip_path)
            
            cap.release()
            
            return {
                'duration': duration,
                'fps': fps,
                'frame_count': frame_count,
                'resolution': f"{width}x{height}",
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Error getting clip info: {e}")
            return {}


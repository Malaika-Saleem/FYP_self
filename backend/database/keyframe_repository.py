"""
Keyframe Repository for DetectifAI Database Operations

This module provides MinIO storage and database operations for keyframes.
"""

import os
import io
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from minio.error import S3Error

logger = logging.getLogger(__name__)

class KeyframeRepository:
    """Repository for keyframe operations with MinIO storage and MongoDB"""
    
    def __init__(self, db_manager):
        self.minio = db_manager.minio_client
        self.db = db_manager.db
        self.bucket = db_manager.config.minio_keyframe_bucket  # Use dedicated keyframes bucket
        self.collection = self.db.keyframes  # MongoDB collection for keyframe metadata
    
    def save_keyframe_to_minio(self, video_id: str, frame_data: bytes, frame_number: int, timestamp: float) -> Optional[str]:
        """Save a single keyframe directly to MinIO storage"""
        try:
            minio_path = f"{video_id}/frame_{frame_number:06d}.jpg"  # Use consistent naming pattern
            
            # Upload bytes directly to MinIO using BytesIO
            from io import BytesIO
            buffer = BytesIO(frame_data)
            
            self.minio.put_object(
                self.bucket,
                minio_path,
                buffer,
                length=len(frame_data),
                content_type='image/jpeg'
            )
            logger.info(f"✅ Uploaded keyframe to MinIO: {minio_path}")
            return minio_path
            
        except Exception as e:
            logger.error(f"❌ Failed to upload keyframe to MinIO: {e}")
            return None
    
    def save_keyframes_batch(self, video_id: str, keyframes: List) -> List[Dict]:
        """Save multiple keyframes directly to MinIO and locally, return their storage info"""
        keyframe_info = []

        try:
            # Create local storage directory
            local_dir = os.path.join("video_processing_outputs", "keyframes", video_id)
            os.makedirs(local_dir, exist_ok=True)

            for keyframe in keyframes:
                # Handle KeyframeResult objects
                frame_data = keyframe.frame_data if hasattr(keyframe, 'frame_data') else keyframe

                frame = frame_data.get('frame')  # numpy array
                frame_number = frame_data.get('frame_number', 0)
                timestamp = frame_data.get('timestamp', 0.0)

                if frame is not None:
                    # Convert numpy array to jpg bytes
                    is_success, buffer = cv2.imencode('.jpg', frame)
                    if not is_success:
                        continue

                    frame_bytes = buffer.tobytes()

                    # Save locally
                    local_filename = f"frame_{frame_number:06d}.jpg"
                    local_path = os.path.join(local_dir, local_filename)
                    with open(local_path, 'wb') as f:
                        f.write(frame_bytes)
                    logger.info(f"✅ Keyframe saved locally: {local_path}")

                    # Upload bytes directly to MinIO
                    minio_path = self.save_keyframe_to_minio(
                        video_id, frame_bytes, frame_number, timestamp
                    )

                    if minio_path:
                        info = {
                            'frame_number': frame_number,
                            'timestamp': timestamp,
                            'minio_path': minio_path,
                            'local_path': local_path,
                            'quality_score': frame_data.get('quality_score', 0.0),
                            'enhancement_applied': frame_data.get('enhancement_applied', False)
                        }
                        keyframe_info.append(info)

            logger.info(f"✅ Uploaded {len(keyframe_info)} keyframes to MinIO and saved locally for video {video_id}")
            return keyframe_info

        except Exception as e:
            logger.error(f"❌ Failed to upload keyframes batch: {e}")
            return keyframe_info  # Return whatever was successful

    def get_keyframe_presigned_url(self, minio_path: str, expires: timedelta = timedelta(hours=1)) -> str:
        """Generate presigned URL for keyframe access"""
        try:
            return self.minio.presigned_get_object(self.bucket, minio_path, expires=expires)
        except S3Error as e:
            logger.error(f"❌ Failed to generate presigned URL for keyframe: {e}")
            return None

    def get_video_keyframes_presigned_urls(self, video_id: str, expires: timedelta = timedelta(hours=1)) -> List[Dict]:
        """Get presigned URLs for all keyframes of a video"""
        try:
            # List all objects in the video's keyframe directory
            # Keyframes are stored at: {video_id}/keyframes/frame_*.jpg
            logger.info(f"🔍 Looking for keyframes in bucket '{self.bucket}' with prefix '{video_id}/keyframes/'")
            objects = list(self.minio.list_objects(self.bucket, prefix=f"{video_id}/keyframes/", recursive=True))
            logger.info(f"📦 Found {len(objects)} objects in MinIO for keyframes")

            keyframes_urls = []
            for obj in objects:
                if obj.object_name.endswith('.jpg'):
                    # Extract frame number and timestamp from filename
                    filename = obj.object_name.split('/')[-1]  # e.g., "frame_000001.jpg"
                    frame_number = 0
                    timestamp = 0.0

                    try:
                        # Parse frame number from filename like "frame_000001.jpg"
                        if 'frame_' in filename:
                            frame_str = filename.split('_')[1].split('.')[0]
                            frame_number = int(frame_str)
                            # Estimate timestamp from frame number (assuming 30 fps)
                            timestamp = frame_number / 30.0
                    except (ValueError, IndexError):
                        pass
                    
                    # Try to get metadata from MinIO object
                    try:
                        obj_stat = self.minio.stat_object(self.bucket, obj.object_name)
                        if obj_stat.metadata:
                            # Extract timestamp from metadata if available
                            if 'timestamp' in obj_stat.metadata:
                                try:
                                    timestamp = float(obj_stat.metadata['timestamp'])
                                except:
                                    pass
                            if 'frame_number' in obj_stat.metadata:
                                try:
                                    frame_number = int(obj_stat.metadata['frame_number'])
                                except:
                                    pass
                    except:
                        pass

                    # Generate presigned URL and API URL
                    presigned_url = self.get_keyframe_presigned_url(obj.object_name, expires=expires)
                    # Also provide API endpoint URL for direct serving
                    api_url = f"/api/minio/image/{self.bucket}/{obj.object_name}"

                    if presigned_url:
                        keyframes_urls.append({
                            'frame_number': frame_number,
                            'timestamp': timestamp,
                            'minio_path': obj.object_name,
                            'presigned_url': presigned_url,
                            'url': api_url,  # Use API endpoint for better reliability
                            'api_url': api_url,
                            'filename': filename
                        })

            # Sort by frame number
            keyframes_urls.sort(key=lambda x: x['frame_number'])

            logger.info(f"✅ Generated {len(keyframes_urls)} presigned URLs for video {video_id} keyframes")
            return keyframes_urls

        except Exception as e:
            logger.error(f"❌ Failed to get keyframes presigned URLs for video {video_id}: {e}")
            return []
    
    def create_keyframe(self, keyframe_doc: Dict[str, Any]) -> Optional[str]:
        """
        Save keyframe metadata to MongoDB
        
        Args:
            keyframe_doc: Dictionary containing keyframe metadata:
                - camera_id: Camera identifier (for live streams)
                - video_id: Video identifier (for uploaded videos, optional)
                - timestamp: Frame timestamp in seconds
                - timestamp_ms: Frame timestamp in milliseconds
                - frame_index: Frame number/index
                - minio_path: Path to keyframe in MinIO
                - objects_detected: List of detected objects
                - behaviors_detected: List of detected behaviors
                - motion_detected: Whether motion was detected
                - motion_score: Motion detection score
                - created_at: Creation timestamp
        
        Returns:
            MongoDB document ID or None
        """
        try:
            # Ensure required fields
            if 'created_at' not in keyframe_doc:
                keyframe_doc['created_at'] = datetime.utcnow()
            
            # Convert numpy types if present
            try:
                from database.models import convert_numpy_types, prepare_for_mongodb
                keyframe_doc = convert_numpy_types(keyframe_doc)
                keyframe_doc = prepare_for_mongodb(keyframe_doc)
            except ImportError:
                # Fallback if models not available
                pass
            
            # Insert into MongoDB
            result = self.collection.insert_one(keyframe_doc)
            logger.info(f"✅ Saved keyframe metadata to MongoDB: {keyframe_doc.get('minio_path', 'unknown')}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to save keyframe metadata to MongoDB: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

"""
Data Models for DetectifAI Database Integration

This module defines data models that map EXACTLY to the MongoDB collections
defined in DetectifAI_db/database_setup.py schema.

CRITICAL: Only use fields defined in the MongoDB schema validators.
Extra fields must go in meta_data for video_file or use related collections.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from dataclasses import dataclass, asdict
import json
import numpy as np

@dataclass
class VideoFileModel:
    """Maps EXACTLY to video_file collection schema in MongoDB Atlas"""
    # Required fields (from schema)
    video_id: str
    user_id: str
    file_path: str  # MinIO path or local path
    
    # Optional fields (from schema)
    minio_object_key: Optional[str] = None
    minio_bucket: Optional[str] = None
    codec: Optional[str] = None
    fps: Optional[float] = 30.0  # bsonType: double - must be float
    upload_date: Optional[datetime] = None
    duration_secs: Optional[int] = None  # bsonType: int - must be INTEGER not float
    file_size_bytes: Optional[int] = None  # bsonType: long
    meta_data: Optional[Dict] = None  # Store ALL extra fields here (processing_status, resolution, etc.)
    
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB insertion with proper type conversion"""
        data = asdict(self)
        
        # Set defaults
        if data.get('upload_date') is None:
            data['upload_date'] = datetime.utcnow()
        if data.get('fps') is None:
            data['fps'] = 30.0
        
        # Ensure duration is integer (MongoDB schema requires int)
        if data.get('duration_secs') is not None:
            data['duration_secs'] = int(data['duration_secs'])
        
        # Ensure file_size is integer (MongoDB schema requires long)
        if data.get('file_size_bytes') is not None:
            data['file_size_bytes'] = int(data['file_size_bytes'])
        
        # Ensure fps is float (MongoDB schema requires double)
        if data.get('fps') is not None:
            data['fps'] = float(data['fps'])
        
        return data

@dataclass 
class DetectedFaceModel:
    """Maps to existing detected_faces collection"""
    video_id: str
    frame_timestamp: float
    face_bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    face_encoding: Optional[List[float]] = None
    keyframe_minio_path: Optional[str] = None
    keyframe_id: Optional[ObjectId] = None
    person_id: Optional[str] = None
    is_suspicious: bool = False
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class EventModel:
    """Maps EXACTLY to event collection schema in MongoDB Atlas"""
    # Required fields (from schema)
    event_id: str
    video_id: str
    start_timestamp_ms: int  # bsonType: long - MUST be milliseconds as INTEGER
    end_timestamp_ms: int    # bsonType: long - MUST be milliseconds as INTEGER
    
    # Optional fields (from schema)
    event_type: Optional[str] = None  # 'object_detection', 'motion', 'fire', 'weapon', etc.
    confidence_score: Optional[float] = None  # bsonType: double (NOT 'confidence')
    is_verified: bool = False
    is_false_positive: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    visual_embedding: Optional[List[float]] = None  # For future FAISS integration
    bounding_boxes: Optional[Dict] = None  # Store detection bboxes here as object
    
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB insertion with proper type conversion"""
        data = asdict(self)
        
        # Ensure timestamps are integers (milliseconds) - CRITICAL for MongoDB long type
        data['start_timestamp_ms'] = int(data['start_timestamp_ms'])
        data['end_timestamp_ms'] = int(data['end_timestamp_ms'])
        
        # Ensure confidence_score is float
        if data.get('confidence_score') is not None:
            data['confidence_score'] = float(data['confidence_score'])
        
        # Set default empty arrays/objects for schema compliance
        if data.get('visual_embedding') is None:
            data['visual_embedding'] = []
        if data.get('bounding_boxes') is None:
            data['bounding_boxes'] = {}
        
        return data

@dataclass
class EventCaptionModel:
    """Maps to existing event_caption collection"""
    event_id: ObjectId
    video_id: str
    caption_text: str
    generated_by: str = "system"  # system, user, ai
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

@dataclass
class EventClipModel:
    """Maps to existing event_clip collection"""
    event_id: ObjectId
    video_id: str
    clip_start_timestamp: float
    clip_end_timestamp: float
    minio_clip_path: str
    clip_duration: float
    frame_count: int
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

@dataclass
class EventDescriptionModel:
    """Maps to existing event_description collection"""
    event_id: ObjectId
    video_id: str
    description_text: str
    description_type: str = "automatic"  # automatic, manual, ai_generated
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

@dataclass
class FaceMatchModel:
    """Maps to existing face_matches collection"""
    video_id: str
    face_1_id: ObjectId
    face_2_id: ObjectId
    similarity_score: float
    match_confidence: float
    is_match: bool
    person_id: Optional[str] = None
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

# New models for video processing pipeline

@dataclass
class KeyframeModel:
    """New collection for extracted keyframes"""
    video_id: str
    frame_number: int
    timestamp: float
    quality_score: float
    motion_score: float
    minio_path: str
    enhancement_applied: bool = False
    face_count: int = 0
    object_detections: Optional[List[Dict]] = None
    processing_metadata: Optional[Dict] = None
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        if data.get('object_detections') is None:
            data['object_detections'] = []
        return data

@dataclass
class VideoSegmentModel:
    """New collection for video segments"""
    video_id: str
    segment_id: int
    start_timestamp: float
    end_timestamp: float
    duration: float
    start_frame: int
    end_frame: int
    keyframe_ids: List[ObjectId]
    activity_level: str  # low, medium, high
    motion_statistics: Optional[Dict] = None
    segment_minio_path: Optional[str] = None
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

@dataclass
class ProcessingJobModel:
    """New collection for tracking processing jobs"""
    video_id: str
    job_type: str = "complete_processing"  # complete_processing, keyframe_extraction, object_detection
    status: str = "queued"  # queued, processing, completed, failed
    progress: int = 0  # 0-100
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_stats: Optional[Dict] = None
    error_details: Optional[Dict] = None
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

@dataclass
class ObjectDetectionModel:
    """Detailed object detection results"""
    video_id: str
    keyframe_id: ObjectId
    detection_id: str
    class_name: str  # fire, smoke, knife, gun
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    center_point: List[float]  # [x, y]
    area: float
    frame_timestamp: float
    detection_model: str  # fire_yolo11, yolov11_knife_gun
    threat_level: str = "low"
    created_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        return data

class ModelFactory:
    """Factory class for creating model instances from database documents"""
    
    @staticmethod
    def create_video_file(doc: Dict) -> VideoFileModel:
        """Create VideoFileModel from MongoDB document"""
        return VideoFileModel(**doc)
    
    @staticmethod
    def create_keyframe(doc: Dict) -> KeyframeModel:
        """Create KeyframeModel from MongoDB document"""
        return KeyframeModel(**doc)
    
    @staticmethod
    def create_event(doc: Dict) -> EventModel:
        """Create EventModel from MongoDB document"""
        return EventModel(**doc)
    
    @staticmethod
    def create_processing_job(doc: Dict) -> ProcessingJobModel:
        """Create ProcessingJobModel from MongoDB document"""
        return ProcessingJobModel(**doc)

# Helper functions for database operations

def prepare_for_mongodb(data: Dict) -> Dict:
    """Prepare data dictionary for MongoDB insertion"""
    # Remove None ObjectId fields
    cleaned_data = {}
    for key, value in data.items():
        if key == '_id' and value is None:
            continue
        cleaned_data[key] = value
    return cleaned_data

def convert_objectid_to_string(doc: Dict) -> Dict:
    """Convert ObjectId fields to strings for JSON serialization"""
    if isinstance(doc, dict):
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, list):
                doc[key] = [convert_objectid_to_string(item) if isinstance(item, dict) else str(item) if isinstance(item, ObjectId) else item for item in value]
            elif isinstance(value, dict):
                doc[key] = convert_objectid_to_string(value)
    return doc
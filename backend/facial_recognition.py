"""
Facial Recognition Module for DetectifAI

This module handles facial recognition for suspicious activity frames:
- Face detection using MTCNN (primary) or OpenCV Haar cascades (fallback)
- Face embeddings using FaceNet (primary) or histogram-based (fallback)
- FAISS vector similarity search (primary) or cosine similarity (fallback)
- MongoDB metadata storage with local JSON fallback
- Integration with suspicious activity detection pipeline

Workflow (matches activity diagram):
1. Receive frame from suspicious event (object detection)
2. Run face detection
3. If faces detected: crop faces, generate embeddings, store in FAISS/index
4. Upload face crops to storage, save metadata to MongoDB/JSON
5. Search for similar embeddings, link with previous incidents
6. Assign new person ID if no match found

Author: DetectifAI Team
"""

import os
import cv2
import numpy as np
import logging
import json
import uuid
import time
import warnings
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Advanced imports (with fallbacks)
try:
    import torch
    from facenet_pytorch import MTCNN, InceptionResnetV1
    import faiss
    from pymongo import MongoClient
    from dotenv import load_dotenv
    ADVANCED_AVAILABLE = True
    load_dotenv()
except ImportError:
    ADVANCED_AVAILABLE = False

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# ========================================
# Configuration
# ========================================

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") if ADVANCED_AVAILABLE else None
MONGO_DB_NAME = "detectifai"

# FAISS Configuration
FAISS_INDEX_PATH = "model/faiss_face_index.bin"
FAISS_ID_MAP_PATH = "model/faiss_id_map.json"
EMBEDDING_DIM = 512  # InceptionResnetV1 produces 512-dim embeddings

# Simple fallback configuration
SIMPLE_INDEX_PATH = "model/simple_face_index.json"

# Face storage
FACES_DIR = "model/faces"

# ========================================
# Data Models
# ========================================

@dataclass
class FaceDetectionResult:
    """Result of face detection in a frame"""
    frame_path: str
    timestamp: float
    faces_detected: int
    face_embeddings: List[np.ndarray]
    face_bounding_boxes: List[Tuple[int, int, int, int]]
    face_confidence_scores: List[float]
    processing_time: float
    detected_face_ids: List[str] = None
    matched_persons: List[str] = None

@dataclass 
class SuspiciousPerson:
    """Information about a suspicious person"""
    person_id: str
    first_detected: float  # timestamp
    last_seen: float       # timestamp
    face_embedding: Optional[np.ndarray]
    associated_events: List[str]  # event IDs where this person appeared
    threat_level: str
    notes: str
    detection_count: int
    face_id: str = ""  # Primary face_id

# ========================================
# Advanced Implementation (FAISS + FaceNet)
# ========================================

class AdvancedFaceDetector:
    """Advanced face detector using MTCNN"""
    
    def __init__(self, device='cpu', min_face_size=20):
        self.device = torch.device(device)
        self.mtcnn = MTCNN(
            image_size=160,
            margin=20,
            min_face_size=min_face_size,
            thresholds=[0.5, 0.6, 0.6],
            factor=0.709,
            keep_all=True,
            device=self.device
        )
        logger.info(f"[AdvancedFaceDetector] Initialized MTCNN on {device}")
    
    def detect_faces(self, frame: np.ndarray) -> Tuple[List[np.ndarray], List[np.ndarray], List[float]]:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, probs = self.mtcnn.detect(rgb_frame, landmarks=False)

        if boxes is None:
            return [], [], []
        
        faces = self.mtcnn.extract(rgb_frame, boxes, save_path=None)
        if faces is None:
            return [], [], []
        
        valid_faces, valid_boxes, valid_probs = [], [], []
        for face, prob, box in zip(faces, probs, boxes):
            if face is not None and prob > 0.5:
                valid_faces.append(face)
                valid_boxes.append(box)
                valid_probs.append(prob)
        
        return valid_faces, valid_boxes, valid_probs

class AdvancedFaceEmbedder:
    """Advanced face embedder using FaceNet"""
    
    def __init__(self, device='cpu', weights='vggface2'):
        self.device = torch.device(device)
        self.model = InceptionResnetV1(pretrained=weights).eval().to(self.device)
        logger.info(f"[AdvancedFaceEmbedder] Loaded InceptionResnetV1 on {device}")
    
    def generate_embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            face_tensor = face_tensor.to(self.device).unsqueeze(0)
            embedding = self.model(face_tensor).cpu().numpy().flatten()
        return embedding

class FAISSFaceIndex:
    """FAISS index manager for fast similarity search"""
    
    def __init__(self, embedding_dim: int = 512, index_path: str = FAISS_INDEX_PATH, 
                 id_map_path: str = FAISS_ID_MAP_PATH):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.id_map_path = id_map_path
        self.index = None
        self.id_map = {}
        self.reverse_map = {}
        
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        if os.path.exists(self.index_path) and os.path.exists(self.id_map_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.id_map_path, 'r') as f:
                    data = json.load(f)
                    self.id_map = {int(k): v for k, v in data.items()}
                    self.reverse_map = {v: int(k) for k, v in self.id_map.items()}
                logger.info(f"[FAISS] Loaded index with {self.index.ntotal} embeddings")
            except Exception as e:
                logger.warning(f"[FAISS] Error loading index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.id_map = {}
        self.reverse_map = {}
        logger.info(f"[FAISS] Created new index (dim={self.embedding_dim})")
    
    def add_embedding(self, face_id: str, embedding: np.ndarray) -> int:
        if face_id in self.reverse_map:
            return self.reverse_map[face_id]
        
        embedding = embedding.astype('float32').reshape(1, -1)
        embedding = embedding / np.linalg.norm(embedding)
        
        idx = self.index.ntotal
        self.index.add(embedding)
        
        self.id_map[idx] = face_id
        self.reverse_map[face_id] = idx
        
        return idx
    
    def search(self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.6) -> List[Tuple[str, float]]:
        if self.index.ntotal == 0:
            return []
        
        query_embedding = query_embedding.astype('float32').reshape(1, -1)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        similarities, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx in self.id_map and sim >= threshold:
                results.append((self.id_map[idx], float(sim)))
        
        return results
    
    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.id_map_path, 'w') as f:
            json.dump(self.id_map, f)

class MongoDBFaceStorage:
    """MongoDB storage for face metadata"""
    
    def __init__(self, mongo_uri: str, db_name: str = MONGO_DB_NAME):
        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[db_name]
            self.faces_collection = self.db['detected_faces']
            self.client.server_info()  # Test connection
            self.enabled = True
            logger.info("[MongoDB] Connected successfully")
        except Exception as e:
            logger.warning(f"[MongoDB] Connection failed: {e}")
            self.enabled = False
    
    def save_face(self, data: Dict) -> str:
        if not self.enabled:
            return ""
        
        data['detected_at'] = datetime.utcnow()
        if 'face_embedding' in data:
            del data['face_embedding']  # Don't store embeddings in MongoDB
        data['face_embedding'] = []
        
        try:
            result = self.faces_collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"[MongoDB] Error saving face: {e}")
            return ""
    
    def close(self):
        if hasattr(self, 'client'):
            self.client.close()

# ========================================
# Simple Implementation (OpenCV + Histograms)
# ========================================

class SimpleFaceDetector:
    """Simple face detector using OpenCV Haar cascades"""
    
    def __init__(self, device='cpu'):
        self.device = device
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        logger.info(f"[SimpleFaceDetector] Initialized with OpenCV Haar cascades")
    
    def detect_faces(self, frame: np.ndarray) -> Tuple[List[np.ndarray], List[np.ndarray], List[float]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
        
        face_crops = []
        boxes = []
        confidences = []
        
        for (x, y, w, h) in faces:
            face_crop = frame[y:y+h, x:x+w]
            face_crops.append(face_crop)
            boxes.append([x, y, x+w, y+h])
            confidences.append(0.8)
        
        return face_crops, boxes, confidences

class SimpleFaceEmbedder:
    """Simple face embedder using histograms"""
    
    def __init__(self, device='cpu'):
        self.device = device
        logger.info(f"[SimpleFaceEmbedder] Using histogram-based embeddings")
    
    def generate_embedding(self, face_crop: np.ndarray) -> np.ndarray:
        if isinstance(face_crop, np.ndarray) and len(face_crop.shape) == 3:
            face_resized = cv2.resize(face_crop, (64, 64))
            hsv = cv2.cvtColor(face_resized, cv2.COLOR_BGR2HSV)
            
            hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256])
            
            embedding = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
            return embedding / np.linalg.norm(embedding)
        else:
            return np.random.rand(48) / np.linalg.norm(np.random.rand(48))

class SimpleFaceIndex:
    """Simple face index using cosine similarity"""
    
    def __init__(self, index_path: str = SIMPLE_INDEX_PATH):
        self.index_path = index_path
        self.faces_db = {}
        
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        self._load_index()
    
    def _load_index(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    data = json.load(f)
                    self.faces_db = {face_id: np.array(embedding) 
                                   for face_id, embedding in data.items()}
                logger.info(f"[SimpleFaceIndex] Loaded {len(self.faces_db)} faces")
            except Exception as e:
                logger.warning(f"[SimpleFaceIndex] Error loading: {e}")
                self.faces_db = {}
        else:
            self.faces_db = {}
    
    def add_embedding(self, face_id: str, embedding: np.ndarray) -> int:
        if face_id in self.faces_db:
            return len(self.faces_db)
        
        self.faces_db[face_id] = embedding
        return len(self.faces_db)
    
    def search(self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.6) -> List[Tuple[str, float]]:
        if not self.faces_db:
            return []
        
        similarities = []
        for face_id, stored_embedding in self.faces_db.items():
            similarity = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding))
            
            if similarity >= threshold:
                similarities.append((face_id, float(similarity)))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]
    
    def save(self):
        try:
            data = {face_id: embedding.tolist() 
                   for face_id, embedding in self.faces_db.items()}
            
            with open(self.index_path, 'w') as f:
                json.dump(data, f)
            
            logger.debug(f"[SimpleFaceIndex] Saved {len(self.faces_db)} faces")
        except Exception as e:
            logger.error(f"[SimpleFaceIndex] Error saving: {e}")

# ========================================
# Main Facial Recognition Class
# ========================================

class FacialRecognitionIntegrated:
    """
    Unified facial recognition system for DetectifAI.
    
    Automatically uses advanced implementation (MTCNN + FaceNet + FAISS + MongoDB) 
    if available, otherwise falls back to simple implementation (OpenCV + Histograms + JSON).
    
    Applies facial recognition ONLY to suspicious frames detected by object detection.
    """
    
    def __init__(self, config):
        self.config = config
        self.enabled = getattr(config, 'enable_facial_recognition', False)
        self.confidence_threshold = getattr(config, 'face_recognition_confidence', 0.7)
        self.similarity_threshold = 0.6
        self.device = 'cuda' if torch.cuda.is_available() and getattr(config, 'use_gpu_acceleration', False) else 'cpu'
        
        # Create faces directory
        self.faces_dir = Path(FACES_DIR)
        self.faces_dir.mkdir(exist_ok=True, parents=True)
        
        # Determine implementation mode
        self.advanced_mode = ADVANCED_AVAILABLE and self.enabled
        
        # Initialize components only if enabled
        if self.enabled:
            self._initialize_components()
        
        # Detection statistics
        self.detection_stats = {
            'implementation_mode': 'advanced' if self.advanced_mode else 'simple',
            'frames_processed': 0,
            'faces_detected': 0,
            'suspicious_persons_tracked': 0,
            'reoccurrences_detected': 0,
            'new_faces_added': 0,
            'face_matches_found': 0
        }
        
        # Suspicious persons database
        self.suspicious_persons_db = {}
        
        if not self.enabled:
            logger.info("[FacialRecognition] Disabled - skipping initialization")
        else:
            mode = "Advanced (MTCNN + FaceNet + FAISS)" if self.advanced_mode else "Simple (OpenCV + Histograms)"
            logger.info(f"[FacialRecognition] ✅ Initialized in {mode} mode")
    
    def _initialize_components(self):
        """Initialize facial recognition components based on available dependencies"""
        try:
            if self.advanced_mode:
                # Advanced implementation
                self.detector = AdvancedFaceDetector(self.device)
                self.embedder = AdvancedFaceEmbedder(self.device)
                self.face_index = FAISSFaceIndex()
                
                # MongoDB storage (optional)
                if MONGO_URI:
                    self.mongodb_storage = MongoDBFaceStorage(MONGO_URI)
                else:
                    self.mongodb_storage = None
                    logger.info("[FacialRecognition] MongoDB not configured, using local storage only")
                
            else:
                # Simple implementation
                self.detector = SimpleFaceDetector()
                self.embedder = SimpleFaceEmbedder()
                self.face_index = SimpleFaceIndex()
                self.mongodb_storage = None
                
        except Exception as e:
            logger.error(f"[FacialRecognition] ❌ Initialization failed: {e}")
            self.enabled = False
            raise
    
    def _generate_face_id(self, frame_number: int, face_index: int, person_name: Optional[str] = None, event_id: str = "unknown") -> str:
        """Generate unique face ID"""
        prefix = f"{person_name.replace(' ', '_')}" if person_name else "unknown"
        unique_id = str(uuid.uuid4())[:8]
        return f"face_{prefix}_event_{event_id}_{frame_number:06d}_{face_index:02d}_{unique_id}"
    
    def _save_face_image(self, face_data, face_id: str) -> str:
        """Save face image to disk"""
        try:
            path = self.faces_dir / f"{face_id}.jpg"
            
            if self.advanced_mode and hasattr(face_data, 'permute'):
                # Convert tensor to numpy array
                face_np = face_data.permute(1, 2, 0).numpy()
                face_np = (face_np * 255).astype(np.uint8)
                face_bgr = cv2.cvtColor(face_np, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(path), face_bgr)
            else:
                # Direct numpy array
                cv2.imwrite(str(path), face_data)
                
            return str(path)
        except Exception as e:
            logger.error(f"[FacialRecognition] Error saving face image: {e}")
            return ""
    
    def detect_faces_in_frame(self, frame_path: str, timestamp: float) -> FaceDetectionResult:
        """
        Detect faces in a single frame (for suspicious frames only).
        
        Args:
            frame_path: Path to the frame image
            timestamp: Timestamp of the frame in video
            
        Returns:
            FaceDetectionResult with detected faces and metadata
        """
        if not self.enabled:
            return FaceDetectionResult(
                frame_path=frame_path,
                timestamp=timestamp,
                faces_detected=0,
                face_embeddings=[],
                face_bounding_boxes=[],
                face_confidence_scores=[],
                processing_time=0.0
            )
        
        start_time = time.time()
        
        try:
            # Load frame
            frame = cv2.imread(frame_path)
            if frame is None:
                logger.error(f"Could not load frame: {frame_path}")
                return FaceDetectionResult(
                    frame_path=frame_path,
                    timestamp=timestamp,
                    faces_detected=0,
                    face_embeddings=[],
                    face_bounding_boxes=[],
                    face_confidence_scores=[],
                    processing_time=0.0
                )
            
            # Detect faces
            faces, boxes, probs = self.detector.detect_faces(frame)
            
            # Generate embeddings and process faces
            face_embeddings = []
            detected_face_ids = []
            matched_persons = []
            
            for i, (face, box, prob) in enumerate(zip(faces, boxes, probs)):
                # Generate embedding
                embedding = self.embedder.generate_embedding(face)
                face_embeddings.append(embedding)
                
                # Search for similar faces
                matches = self.face_index.search(embedding, k=1, threshold=self.similarity_threshold)
                
                if matches:
                    # Found matching face
                    matched_face_id, similarity = matches[0]
                    detected_face_ids.append(matched_face_id)
                    matched_persons.append(f"person_{matched_face_id}")
                    self.detection_stats['face_matches_found'] += 1
                    logger.info(f"👤 Face match found: {matched_face_id} (similarity: {similarity:.3f})")
                else:
                    # New face
                    frame_number = int(timestamp * 30)  # Estimate frame number
                    new_face_id = self._generate_face_id(frame_number, i, event_id=f"obj_detection_{int(timestamp)}")
                    
                    # Add to index
                    self.face_index.add_embedding(new_face_id, embedding)
                    
                    # Save face image
                    face_path = self._save_face_image(face, new_face_id)
                    
                    # Save metadata to MongoDB if available
                    if self.mongodb_storage and self.mongodb_storage.enabled:
                        face_metadata = {
                            'face_id': new_face_id,
                            'frame_path': frame_path,
                            'timestamp': timestamp,
                            'confidence': float(prob),
                            'bounding_box': [int(x) for x in box],
                            'face_image_path': face_path
                        }
                        self.mongodb_storage.save_face(face_metadata)
                    
                    detected_face_ids.append(new_face_id)
                    matched_persons.append(f"new_person_{new_face_id}")
                    self.detection_stats['new_faces_added'] += 1
                    logger.info(f"👤 New face detected: {new_face_id}")
            
            # Save face index
            self.face_index.save()
            
            processing_time = time.time() - start_time
            self.detection_stats['frames_processed'] += 1
            self.detection_stats['faces_detected'] += len(faces)
            
            # Convert boxes to expected format
            face_bounding_boxes = [(int(box[0]), int(box[1]), int(box[2]), int(box[3])) for box in boxes]
            
            result = FaceDetectionResult(
                frame_path=frame_path,
                timestamp=timestamp,
                faces_detected=len(faces),
                face_embeddings=face_embeddings,
                face_bounding_boxes=face_bounding_boxes,
                face_confidence_scores=probs,
                processing_time=processing_time,
                detected_face_ids=detected_face_ids,
                matched_persons=matched_persons
            )
            
            if faces:
                logger.info(f"👤 Processed {len(faces)} faces in suspicious frame at {timestamp:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"[FacialRecognition] Error processing frame {frame_path}: {e}")
            return FaceDetectionResult(
                frame_path=frame_path,
                timestamp=timestamp,
                faces_detected=0,
                face_embeddings=[],
                face_bounding_boxes=[],
                face_confidence_scores=[],
                processing_time=time.time() - start_time
            )
    
    def track_suspicious_persons(self, face_results: List[FaceDetectionResult], 
                               detectifai_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Track suspicious persons and detect re-occurrences."""
        if not self.enabled or not face_results:
            logger.info("👤 Facial recognition disabled or no face results - skipping person tracking")
            return []
        
        logger.info(f"👤 Tracking suspicious persons across {len(face_results)} face detection results")
        
        reoccurrence_events = []
        person_timeline = {}  # face_id -> list of timestamps
        
        # Build person timeline from face results
        for face_result in face_results:
            if face_result.detected_face_ids:
                for face_id in face_result.detected_face_ids:
                    if face_id not in person_timeline:
                        person_timeline[face_id] = []
                    person_timeline[face_id].append(face_result.timestamp)
        
        # Look for re-occurrences (same person appearing multiple times)
        for face_id, timestamps in person_timeline.items():
            if len(timestamps) > 1:
                # Create re-occurrence event
                timestamps.sort()
                reoccurrence_event = {
                    'event_id': f"reoccurrence_{face_id}_{int(timestamps[-1])}",
                    'start_timestamp': timestamps[0],
                    'end_timestamp': timestamps[-1],
                    'event_type': 'suspicious_person_reoccurrence',
                    'confidence': 0.85,
                    'max_confidence': 0.85,
                    'keyframes': [r.frame_path for r in face_results if face_id in (r.detected_face_ids or [])],
                    'importance_score': 4.0,
                    'description': f"Suspicious person {face_id} appeared {len(timestamps)} times",
                    'detection_details': {
                        'person_id': face_id,
                        'appearances': len(timestamps),
                        'time_span': timestamps[-1] - timestamps[0],
                        'timestamps': timestamps
                    }
                }
                reoccurrence_events.append(reoccurrence_event)
                self.detection_stats['reoccurrences_detected'] += 1
        
        # Save face index
        if self.face_index:
            self.face_index.save()
        
        # Update statistics
        self.detection_stats['suspicious_persons_tracked'] = len(person_timeline)
        
        logger.info(f"👤 Person tracking complete: {len(person_timeline)} unique persons, {len(reoccurrence_events)} re-occurrences")
        
        return reoccurrence_events
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get facial recognition detection statistics"""
        stats = self.detection_stats.copy()
        if hasattr(self, 'face_index'):
            if self.advanced_mode:
                stats['total_faces_in_database'] = self.face_index.index.ntotal if self.face_index.index else 0
            else:
                stats['total_faces_in_database'] = len(self.face_index.faces_db) if self.face_index else 0
        return stats
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'face_index'):
            self.face_index.save()
        if hasattr(self, 'mongodb_storage') and self.mongodb_storage:
            self.mongodb_storage.close()
        logger.info("[FacialRecognition] Cleanup completed")

# For backward compatibility
FacialRecognitionPlaceholder = FacialRecognitionIntegrated
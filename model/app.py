"""
DetectifAI - Facial Recognition with FAISS + MongoDB Integration
Embeddings stored in FAISS, metadata stored in MongoDB, linked by face_id.

Author: AI Assistant
"""

import os
import json
import uuid
import numpy as np
import cv2
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
import warnings
import joblib
import faiss
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId

warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

# ========================================
# Configuration
# ========================================

TRAINED_MODEL_DIR = "trained_models"
CLASSIFIER_PATH = os.path.join(TRAINED_MODEL_DIR, "classifier_svm.pkl")
ENCODER_PATH = os.path.join(TRAINED_MODEL_DIR, "label_encoder.pkl")

ENABLE_PERSON_ID = True
CONFIDENCE_THRESHOLD = 0.5

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = "detectifai"

# FAISS Configuration
FAISS_INDEX_PATH = "faiss_face_index.bin"
FAISS_ID_MAP_PATH = "faiss_id_map.json"
EMBEDDING_DIM = 512  # InceptionResnetV1 produces 512-dim embeddings


# ========================================
# Helper Functions from data_models.py
# ========================================

def convert_numpy_types(obj):
    """Recursively convert numpy types to native Python types for MongoDB compatibility."""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj


def prepare_for_mongodb(data: Dict) -> Dict:
    """Prepare data dictionary for MongoDB insertion."""
    data = convert_numpy_types(data)
    cleaned_data = {}
    for key, value in data.items():
        if key == '_id' and value is None:
            continue
        cleaned_data[key] = value
    return cleaned_data


def seconds_to_milliseconds(seconds: float) -> int:
    """Convert seconds (float) to milliseconds (int) for MongoDB long type"""
    return int(seconds * 1000)


# ========================================
# Person Classifier
# ========================================

class PersonClassifier:
    def __init__(self, classifier_path: str, encoder_path: str, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.enabled = False
        
        try:
            self.classifier = joblib.load(classifier_path)
            self.label_encoder = joblib.load(encoder_path)
            self.enabled = True
            print(f"[PersonClassifier] ✅ Model loaded, {len(self.label_encoder.classes_)} identities recognized.")
        except Exception as e:
            print(f"[PersonClassifier] ⚠️ Failed to load model: {e}")
    
    def identify_person(self, embedding: np.ndarray) -> Tuple[Optional[str], float]:
        if not self.enabled:
            return None, 0.0
        try:
            probs = self.classifier.predict_proba(embedding.reshape(1, -1))[0]
            best_idx = np.argmax(probs)
            conf = probs[best_idx]
            if conf >= self.confidence_threshold:
                return self.label_encoder.classes_[best_idx], float(conf)
            return None, float(conf)
        except Exception as e:
            print(f"[PersonClassifier] Error: {e}")
            return None, 0.0


# ========================================
# Face Detection and Embedding
# ========================================

class FaceDetector:
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
        print(f"[FaceDetector] Initialized on {device}")
    
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
            if prob > 0.1:
                valid_faces.append(face)
                valid_boxes.append(box)
                valid_probs.append(float(prob))
        return valid_faces, valid_boxes, valid_probs


class FaceEmbedder:
    def __init__(self, device='cpu', weights='vggface2'):
        self.device = torch.device(device)
        self.model = InceptionResnetV1(pretrained=weights).eval().to(self.device)
        print(f"[FaceEmbedder] Loaded InceptionResnetV1 on {device}")
    
    def generate_embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            face_tensor = face_tensor.unsqueeze(0).to(self.device)
            embedding = self.model(face_tensor).cpu().numpy().flatten()
            embedding = embedding / np.linalg.norm(embedding)
        return embedding


# ========================================
# FAISS Index Manager (Embeddings Only)
# ========================================

class FAISSFaceIndex:
    """
    FAISS index manager for fast similarity search of face embeddings.
    Stores ONLY embeddings in FAISS, metadata goes to MongoDB.
    """
    
    def __init__(self, embedding_dim: int = 512, index_path: str = FAISS_INDEX_PATH, 
                 id_map_path: str = FAISS_ID_MAP_PATH):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.id_map_path = id_map_path
        self.index = None
        self.id_map = {}  # Maps FAISS index position -> face_id
        self.reverse_map = {}  # Maps face_id -> FAISS index position
        
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        if os.path.exists(self.index_path) and os.path.exists(self.id_map_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.id_map_path, 'r') as f:
                    # Load as list of tuples and convert back to dict
                    id_list = json.load(f)
                    self.id_map = {int(k): v for k, v in id_list}
                    self.reverse_map = {v: int(k) for k, v in id_list}
                print(f"[FAISS] ✅ Loaded index with {self.index.ntotal} embeddings")
            except Exception as e:
                print(f"[FAISS] ⚠️ Error loading index: {e}. Creating new index.")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create new FAISS index using IndexFlatIP for cosine similarity (Inner Product)"""
        # Using IndexFlatIP for cosine similarity on normalized vectors
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.id_map = {}
        self.reverse_map = {}
        print(f"[FAISS] ✅ Created new index (dim={self.embedding_dim}, metric=InnerProduct)")
    
    def add_embedding(self, face_id: str, embedding: np.ndarray) -> int:
        """
        Add face embedding to FAISS index.
        Returns the FAISS index position.
        """
        if face_id in self.reverse_map:
            print(f"[FAISS] ⚠️ Face {face_id} already in index, skipping")
            return self.reverse_map[face_id]
        
        # Ensure embedding is normalized and correct shape
        embedding = embedding.astype('float32').reshape(1, -1)
        embedding = embedding / np.linalg.norm(embedding)
        
        # Add to FAISS index
        idx = self.index.ntotal
        self.index.add(embedding)
        
        # Update mappings
        self.id_map[idx] = face_id
        self.reverse_map[face_id] = idx
        
        print(f"[FAISS] Added {face_id} at index {idx}")
        return idx
    
    def search(self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """
        Search for similar faces in FAISS index using cosine similarity.
        
        Args:
            query_embedding: Face embedding to search for
            k: Number of nearest neighbors to return
            threshold: Minimum similarity score (0-1)
        
        Returns:
            List of (face_id, similarity_score) tuples
        """
        if self.index.ntotal == 0:
            return []
        
        # Prepare query - normalize for cosine similarity
        query_embedding = query_embedding.astype('float32').reshape(1, -1)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search FAISS index (IndexFlatIP returns inner product = cosine similarity for normalized vectors)
        similarities, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        # Filter by threshold and return results
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for invalid results
                continue
            similarity = float(sim)  # Already cosine similarity
            if similarity >= threshold:
                face_id = self.id_map[idx]
                results.append((face_id, similarity))
        
        return results
    
    def get_embedding(self, face_id: str) -> Optional[np.ndarray]:
        """Retrieve embedding from FAISS by face_id"""
        if face_id not in self.reverse_map:
            return None
        
        idx = self.reverse_map[face_id]
        embedding = self.index.reconstruct(int(idx))
        return embedding
    
    def save(self):
        """Save FAISS index and ID mappings to disk"""
        faiss.write_index(self.index, self.index_path)
        with open(self.id_map_path, 'w') as f:
            # Convert to list of tuples for JSON serialization
            id_list = [[k, v] for k, v in self.id_map.items()]
            json.dump(id_list, f)
        print(f"[FAISS] 💾 Saved index ({self.index.ntotal} embeddings)")
    
    def rebuild_from_mongodb(self, mongo_db):
        """
        Rebuild FAISS index from MongoDB detected_faces collection.
        NOTE: This requires embeddings to be stored in MongoDB temporarily,
        or you need to re-extract embeddings from face images.
        """
        print("[FAISS] 🔄 Rebuilding index from MongoDB...")
        self._create_new_index()
        
        faces_collection = mongo_db['detected_faces']
        count = 0
        
        # Only works if face_embedding exists in MongoDB
        for face_doc in faces_collection.find({"face_embedding": {"$exists": True, "$ne": []}}):
            face_id = face_doc['face_id']
            embedding = np.array(face_doc['face_embedding'], dtype=np.float32)
            
            if len(embedding) == self.embedding_dim:
                self.add_embedding(face_id, embedding)
                count += 1
        
        self.save()
        print(f"[FAISS] ✅ Rebuilt index with {count} faces from MongoDB")


# ========================================
# MongoDB Storage Handler (Metadata Only)
# ========================================

class MongoDBFaceStorage:
    """
    Stores face metadata in MongoDB Atlas (NO embeddings).
    Embeddings are stored in FAISS only.
    """
    
    def __init__(self, mongo_uri: str, db_name: str = MONGO_DB_NAME):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.faces_collection = self.db['detected_faces']
        self.matches_collection = self.db['face_matches']
        self.events_collection = self.db['event']
        print(f"[MongoDB] ✅ Connected to {db_name}")
    
    def save_face(self, data: Dict) -> str:
        """
        Save detected face metadata to MongoDB (NO embedding).
        Embedding is stored in FAISS separately.
        """
        data['detected_at'] = datetime.utcnow()
        
        # Remove embedding if present - it goes to FAISS only
        if 'face_embedding' in data:
            del data['face_embedding']
        
        # Set empty face_embedding array as per schema (required field)
        data['face_embedding'] = []
        
        data = prepare_for_mongodb(data)
        
        result = self.faces_collection.insert_one(data)
        print(f"[MongoDB] Face saved: {data['face_id']} (metadata only)")
        return str(result.inserted_id)
    
    def save_face_match(self, match_data: Dict) -> str:
        """Save face match to MongoDB"""
        match_data['matched_at'] = datetime.utcnow()
        match_data = prepare_for_mongodb(match_data)
        
        result = self.matches_collection.insert_one(match_data)
        print(f"[MongoDB] Match saved: {match_data['match_id']}")
        return str(result.inserted_id)
    
    def save_event(self, event_data: Dict) -> str:
        """Save event to MongoDB"""
        event_data = prepare_for_mongodb(event_data)
        
        result = self.events_collection.insert_one(event_data)
        print(f"[MongoDB] Event saved: {event_data['event_id']}")
        return str(result.inserted_id)
    
    def get_face_by_id(self, face_id: str) -> Optional[Dict]:
        """Retrieve face metadata by face_id (no embedding)"""
        return self.faces_collection.find_one({"face_id": face_id})
    
    def update_face_metadata(self, face_id: str, update_data: Dict):
        """Update face metadata in MongoDB"""
        update_data = prepare_for_mongodb(update_data)
        self.faces_collection.update_one(
            {"face_id": face_id},
            {"$set": update_data}
        )
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


# ========================================
# Main DetectifAI Pipeline
# ========================================

class DetectifAI:
    def __init__(self, video_path: str, event_id: str, frame_skip: int = 5,
                 output_faces_dir: str = "faces", device: str = "cpu",
                 output_video_path: Optional[str] = "output_annotated.mp4",
                 enable_person_id: bool = True, classifier_path=None, encoder_path=None,
                 similarity_threshold: float = 0.6):
        
        self.video_path = video_path
        self.event_id = event_id
        self.frame_skip = frame_skip
        self.output_faces_dir = Path(output_faces_dir)
        self.output_faces_dir.mkdir(exist_ok=True)
        self.output_video_path = output_video_path
        self.similarity_threshold = similarity_threshold

        # Initialize ML components
        self.detector = FaceDetector(device=device)
        self.embedder = FaceEmbedder(device=device)
        
        # Initialize FAISS (embeddings) + MongoDB (metadata)
        self.faiss_index = FAISSFaceIndex()
        self.storage = MongoDBFaceStorage(MONGO_URI)
        
        # Initialize person classifier
        self.person_classifier = None
        if enable_person_id and classifier_path and encoder_path:
            self.person_classifier = PersonClassifier(classifier_path, encoder_path)
    
    def _generate_face_id(self, frame_number: int, face_index: int, person_name: Optional[str] = None) -> str:
        """Generate unique face ID"""
        prefix = f"{person_name.replace(' ', '_')}" if person_name else "unknown"
        unique_id = str(uuid.uuid4())[:8]
        return f"face_{prefix}_{self.event_id}_{frame_number:06d}_{face_index:02d}_{unique_id}"
    
    def _save_face_image(self, face_tensor: torch.Tensor, face_id: str) -> str:
        """Save face image to disk"""
        face_np = face_tensor.permute(1, 2, 0).numpy()
        face_np = ((face_np + 1) / 2 * 255).astype(np.uint8)
        face_bgr = cv2.cvtColor(face_np, cv2.COLOR_RGB2BGR)
        path = self.output_faces_dir / f"{face_id}.jpg"
        cv2.imwrite(str(path), face_bgr)
        return str(path)
    
    def process_video(self):
        """
        Process video: detect faces, store embeddings in FAISS, metadata in MongoDB, annotate video.
        
        Workflow:
        1. Detect faces and generate embeddings
        2. Search FAISS for similar faces
        3. If match: Link to existing face_id, save match to MongoDB
        4. If new: Save metadata to MongoDB, save embedding to FAISS
        5. Annotate video frame with results
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        
        # Setup video writer
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_secs = total_frames / fps if fps > 0 else 0
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.output_video_path, fourcc, fps, (width, height))

        # Save event metadata to MongoDB
        event_data = {
            'event_id': self.event_id,
            'video_id': f"video_{self.event_id}",
            'start_timestamp_ms': 0,
            'end_timestamp_ms': seconds_to_milliseconds(duration_secs),
            'event_type': 'face_detection',
            'confidence_score': 0.0,
            'is_verified': False,
            'is_false_positive': False,
            'bounding_boxes': {}
        }
        self.storage.save_event(event_data)

        frame_number = 0
        new_faces = 0
        total_matches = 0
        
        print(f"\n[DetectifAI] 🎬 Processing video: {self.video_path}")
        print(f"[DetectifAI] 📊 Total frames: {total_frames}, FPS: {fps}, Duration: {duration_secs:.2f}s")
        print(f"[DetectifAI] 🔍 Similarity threshold: {self.similarity_threshold}")
        print(f"[DetectifAI] 📦 Storage: FAISS (embeddings) + MongoDB (metadata)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_number += 1
            
            # Progress indicator
            if frame_number % 100 == 0:
                progress = (frame_number / total_frames) * 100
                print(f"[DetectifAI] Processing... {progress:.1f}% ({frame_number}/{total_frames})")
            
            if frame_number % self.frame_skip != 0:
                out.write(frame)
                continue
            
            # Detect faces
            faces, boxes, probs = self.detector.detect_faces(frame)
            
            for i, (face, box, prob) in enumerate(zip(faces, boxes, probs)):
                # Generate embedding
                embedding = self.embedder.generate_embedding(face)
                
                # Identify person (if classifier enabled)
                person_name, conf = (None, 0.0)
                if self.person_classifier and self.person_classifier.enabled:
                    person_name, conf = self.person_classifier.identify_person(embedding)
                
                # Search FAISS for similar faces (embeddings stored in FAISS only)
                matches = self.faiss_index.search(embedding, k=1, threshold=self.similarity_threshold)
                
                if matches:
                    # Face match found - link to existing face
                    matched_face_id, similarity = matches[0]
                    face_id = matched_face_id
                    
                    # Save match to MongoDB
                    match_id = str(uuid.uuid4())
                    match_data = {
                        'match_id': match_id,
                        'face_id_1': matched_face_id,
                        'face_id_2': f"detection_{self.event_id}_{frame_number:06d}_{i:02d}",
                        'similarity_score': float(similarity)
                    }
                    self.storage.save_face_match(match_data)
                    total_matches += 1
                    
                    # Update existing face metadata (e.g., last seen)
                    self.storage.update_face_metadata(
                        matched_face_id,
                        {'last_seen_frame': frame_number, 'last_seen_at': datetime.utcnow()}
                    )
                    
                else:
                    # New face detected
                    face_id = self._generate_face_id(frame_number, i, person_name)
                    face_path = self._save_face_image(face, face_id)
                    
                    # Save metadata to MongoDB (NO embedding)
                    face_data = {
                        'face_id': face_id,
                        'event_id': self.event_id,
                        'detected_at': datetime.utcnow(),
                        'confidence_score': float(conf) if person_name else float(prob),
                        'face_image_path': face_path,
                        'bounding_boxes': {
                            'x1': int(box[0]),
                            'y1': int(box[1]),
                            'x2': int(box[2]),
                            'y2': int(box[3])
                        },
                        'first_seen_frame': frame_number,
                        'last_seen_frame': frame_number,
                        'person_name': person_name,
                        'person_confidence': float(conf) if person_name else None
                    }
                    self.storage.save_face(face_data)
                    
                    # Save embedding to FAISS ONLY
                    faiss_idx = self.faiss_index.add_embedding(face_id, embedding)
                    new_faces += 1
                    similarity = 0.0

                # Draw annotations on frame
                (x1, y1, x2, y2) = map(int, box)
                
                # Color coding:
                # Green = Identified person (classifier)
                # Orange = Matched face (FAISS)
                # Red = New face
                if person_name:
                    color = (0, 255, 0)  # Green
                    label = f"{person_name} ({conf:.2f})"
                elif similarity > 0:
                    color = (0, 165, 255)  # Orange
                    label = f"Match ({similarity:.2f})"
                else:
                    color = (0, 0, 255)  # Red
                    label = f"New Face"
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            out.write(frame)
        
        cap.release()
        out.release()
        
        # Save FAISS index to disk
        self.faiss_index.save()
        
        # Close MongoDB connection
        self.storage.close()
        
        print(f"\n[DetectifAI] ✅ Processing complete!")
        print(f"[DetectifAI] 📊 Statistics:")
        print(f"  - New faces detected: {new_faces}")
        print(f"  - Face matches found: {total_matches}")
        print(f"  - Total faces in FAISS index: {self.faiss_index.index.ntotal}")
        print(f"[DetectifAI] 🎥 Annotated video: {self.output_video_path}")
        print(f"[DetectifAI] 💾 FAISS index saved: {FAISS_INDEX_PATH}")
        print(f"[DetectifAI] 🗄️  Metadata stored in MongoDB Atlas")


# ========================================
# Example Usage
# ========================================

if __name__ == "__main__":
    VIDEO_PATH = "suspicious_activity.mp4"
    EVENT_ID = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    print("="*60)
    print("DetectifAI - FAISS (Embeddings) + MongoDB (Metadata)")
    print("="*60)
    
    detectif = DetectifAI(
        video_path=VIDEO_PATH,
        event_id=EVENT_ID,
        frame_skip=5,
        device=DEVICE,
        enable_person_id=ENABLE_PERSON_ID,
        classifier_path=CLASSIFIER_PATH,
        encoder_path=ENCODER_PATH,
        similarity_threshold=0.6
    )
    
    detectif.process_video()
    
    print("\n✅ All done!")
    print("📦 Embeddings: Stored in FAISS (faiss_face_index.bin)")
    print("🗄️  Metadata: Stored in MongoDB Atlas")
    print("🔗 Linked by: face_id")
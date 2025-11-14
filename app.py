"""
DetectifAI - Facial Recognition and Tagging System for CCTV Footage
MongoDB Integration Version

Author: AI Assistant
Description: Modular system for detecting, embedding, and tracking individuals across video frames
             Integrates with existing MongoDB schemas (detected_faces, face_matches collections)
"""

import os
import numpy as np
import cv2
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from sklearn.metrics.pairwise import cosine_similarity
import warnings
from bson import ObjectId
from dataclasses import dataclass, asdict
import uuid

warnings.filterwarnings('ignore')

# ========================================
# MongoDB Schema Models (from your document)
# ========================================

@dataclass
class DetectedFaceModel:
    """Maps EXACTLY to detected_faces collection schema"""
    # Required fields
    face_id: str
    event_id: str
    detected_at: datetime
    
    # Optional fields
    confidence_score: Optional[float] = None
    face_embedding: Optional[List[float]] = None
    minio_object_key: Optional[str] = None
    minio_bucket: Optional[str] = None
    face_image_path: Optional[str] = None
    bounding_boxes: Optional[Dict] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('face_embedding') is None:
            data['face_embedding'] = []
        # Remove None optional fields to avoid schema validation errors
        if data.get('minio_object_key') is None:
            data.pop('minio_object_key', None)
        if data.get('minio_bucket') is None:
            data.pop('minio_bucket', None)
        # Remove None _id
        if data.get('_id') is None:
            data.pop('_id', None)
        return data

@dataclass
class FaceMatchModel:
    """Maps EXACTLY to face_matches collection schema"""
    # Required fields
    match_id: str
    face_id_1: str
    face_id_2: str
    similarity_score: float
    
    # Optional fields
    matched_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('matched_at') is None:
            data['matched_at'] = datetime.utcnow()
        # Remove None _id
        if data.get('_id') is None:
            data.pop('_id', None)
        return data

# ========================================
# Helper Functions for Type Safety
# ========================================

def convert_numpy_types(obj):
    """
    Recursively convert numpy types to native Python types for MongoDB compatibility.
    """
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
    """
    Prepare data dictionary for MongoDB insertion.
    - Convert numpy types to Python natives
    """
    return convert_numpy_types(data)

# ========================================
# Face Detection and Embedding
# ========================================

class FaceDetector:
    """Detects faces in video frames using MTCNN."""
    
    def __init__(self, device='cpu', min_face_size=20):
        """
        Initialize MTCNN face detector.

        Args:
            device: 'cuda' or 'cpu'
            min_face_size: Minimum face size to detect in pixels
        """
        self.device = torch.device(device)
        self.mtcnn = MTCNN(
            image_size=160,
            margin=20,
            min_face_size=min_face_size,
            thresholds=[0.5, 0.6, 0.6],
            factor=0.709,
            post_process=True,
            device=self.device,
            keep_all=True
        )
        print(f"[FaceDetector] Initialized on {device}")
    
    def detect_faces(self, frame: np.ndarray) -> Tuple[List[np.ndarray], List[np.ndarray], List[float]]:
        """
        Detect faces in a frame.

        Args:
            frame: BGR image from OpenCV

        Returns:
            Tuple of (face_tensors, bounding_boxes, probabilities)
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # First, detect bounding boxes and probabilities
        boxes, probs = self.mtcnn.detect(rgb_frame, landmarks=False)

        if boxes is None or len(boxes) == 0:
            return [], [], []

        # Extract faces using the detected boxes
        faces = self.mtcnn.extract(rgb_frame, boxes, save_path=None)

        if faces is None:
            return [], [], []

        # Filter by confidence
        valid_faces = []
        valid_boxes = []
        valid_probs = []

        # Debug: Print raw detections before filtering
        print(f"[DEBUG] Raw detections: {len(faces)} faces")
        for i, (face, prob, box) in enumerate(zip(faces, probs, boxes)):
            print(f"[DEBUG] Face {i}: prob={prob:.3f}, box={box}")

        for face, prob, box in zip(faces, probs, boxes):
            if prob > 0.1:  # Very low confidence threshold for testing
                valid_faces.append(face)
                valid_boxes.append(box)
                valid_probs.append(float(prob))

        print(f"[DEBUG] After filtering: {len(valid_faces)} valid faces")
        return valid_faces, valid_boxes, valid_probs


class FaceEmbedder:
    """Generates 512-D embeddings for face images."""
    
    def __init__(self, device='cpu', weights='vggface2'):
        """
        Initialize InceptionResnetV1 for embedding generation.
        
        Args:
            device: 'cuda' or 'cpu'
            weights: 'vggface2' or 'casia-webface'
        """
        self.device = torch.device(device)
        self.model = InceptionResnetV1(pretrained=weights).eval().to(self.device)
        print(f"[FaceEmbedder] Loaded InceptionResnetV1 with {weights} weights on {device}")
    
    def generate_embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        """
        Generate 512-D embedding for a face.
        
        Args:
            face_tensor: Preprocessed face tensor from MTCNN
            
        Returns:
            Normalized 512-D embedding vector
        """
        with torch.no_grad():
            face_tensor = face_tensor.unsqueeze(0).to(self.device)
            embedding = self.model(face_tensor).cpu().numpy().flatten()
            # Normalize the embedding
            embedding = embedding / np.linalg.norm(embedding)
        return embedding


# ========================================
# MongoDB Database Interface
# ========================================

class FaceDatabase:
    """Manages MongoDB database for storing detected faces and matches."""
    
    def __init__(self, mongo_db):
        """
        Initialize database connection.
        
        Args:
            mongo_db: MongoDB database instance from pymongo
        """
        self.db = mongo_db
        self.detected_faces = self.db['detected_faces']
        self.face_matches = self.db['face_matches']
        print(f"[FaceDatabase] Connected to MongoDB database: {mongo_db.name}")
    
    def add_detected_face(self, face_id: str, event_id: str, 
                         embedding: np.ndarray, face_image_path: str,
                         bounding_box: Dict, confidence: float) -> str:
        """
        Add a new detected face to the database.
        
        Args:
            face_id: Unique face identifier
            event_id: Associated event ID
            embedding: 512-D face embedding vector
            face_image_path: Path to saved face image
            bounding_box: Dict with x1, y1, x2, y2 coordinates
            confidence: Detection confidence score
            
        Returns:
            Inserted document's _id as string
        """
        face_model = DetectedFaceModel(
            face_id=face_id,
            event_id=event_id,
            detected_at=datetime.utcnow(),
            confidence_score=float(confidence),
            face_embedding=embedding.tolist(),
            face_image_path=face_image_path,
            bounding_boxes=bounding_box
        )
        
        # Convert to dict and prepare for MongoDB
        face_data = prepare_for_mongodb(face_model.to_dict())
        
        # Insert into MongoDB
        result = self.detected_faces.insert_one(face_data)
        return str(result.inserted_id)
    
    def add_face_match(self, face_id_1: str, face_id_2: str, 
                      similarity_score: float) -> str:
        """
        Record a face match between two detected faces.
        
        Args:
            face_id_1: First face ID
            face_id_2: Second face ID (matched face)
            similarity_score: Cosine similarity score
            
        Returns:
            Inserted document's _id as string
        """
        match_id = f"match_{uuid.uuid4().hex[:12]}"
        
        match_model = FaceMatchModel(
            match_id=match_id,
            face_id_1=face_id_1,
            face_id_2=face_id_2,
            similarity_score=float(similarity_score)
        )
        
        # Convert to dict and prepare for MongoDB
        match_data = prepare_for_mongodb(match_model.to_dict())
        
        # Insert into MongoDB
        result = self.face_matches.insert_one(match_data)
        return str(result.inserted_id)
    
    def get_all_face_embeddings(self, event_id: Optional[str] = None) -> List[Tuple[str, np.ndarray]]:
        """
        Retrieve all face embeddings from database.
        
        Args:
            event_id: Optional event_id to filter by
            
        Returns:
            List of (face_id, embedding) tuples
        """
        query = {}
        if event_id:
            query['event_id'] = event_id
        
        faces = self.detected_faces.find(
            query,
            {'face_id': 1, 'face_embedding': 1}
        )
        
        results = []
        for face in faces:
            if face.get('face_embedding'):
                embedding = np.array(face['face_embedding'], dtype=np.float32)
                results.append((face['face_id'], embedding))
        
        return results
    
    def get_face_by_id(self, face_id: str) -> Optional[Dict]:
        """Get face document by face_id."""
        return self.detected_faces.find_one({'face_id': face_id})
    
    def get_matches_for_face(self, face_id: str) -> List[Dict]:
        """Get all matches for a specific face."""
        matches = self.face_matches.find({
            '$or': [
                {'face_id_1': face_id},
                {'face_id_2': face_id}
            ]
        })
        return list(matches)
    
    def count_detected_faces(self, event_id: Optional[str] = None) -> int:
        """Count total detected faces, optionally filtered by event."""
        query = {}
        if event_id:
            query['event_id'] = event_id
        return self.detected_faces.count_documents(query)
    
    def count_face_matches(self) -> int:
        """Count total face matches."""
        return self.face_matches.count_documents({})


# ========================================
# Face Matching
# ========================================

class FaceMatcher:
    """Matches face embeddings using cosine similarity, prevents duplicate saving."""
    
    def __init__(self, threshold: float = 0.6, memory_ttl: int = 50):
        """
        Args:
            threshold: Cosine similarity threshold for a match
            memory_ttl: Number of frames to remember recent matches to prevent duplicates
        """
        self.threshold = threshold
        self.embeddings_cache = []  # (face_id, embedding)
        self.recent_faces = {}      # {face_id: frame_number}
        self.memory_ttl = memory_ttl
        print(f"[FaceMatcher] Initialized with threshold={threshold}, memory_ttl={memory_ttl}")
    
    def load_embeddings(self, database: 'FaceDatabase', event_id: Optional[str] = None):
        self.embeddings_cache = database.get_all_face_embeddings(event_id)
        print(f"[FaceMatcher] Loaded {len(self.embeddings_cache)} embeddings from DB")

    def find_match(self, new_embedding: np.ndarray, current_frame: int) -> Tuple[Optional[str], float]:
        """Find a matching face or return None."""
        if not self.embeddings_cache:
            return None, 0.0

        stored_embeddings = np.array([emb for _, emb in self.embeddings_cache])
        similarities = cosine_similarity([new_embedding], stored_embeddings)[0]

        max_idx = np.argmax(similarities)
        max_similarity = similarities[max_idx]

        if max_similarity >= self.threshold:
            matched_face_id = self.embeddings_cache[max_idx][0]

            # Prevent re-saving same face if seen again recently
            if matched_face_id in self.recent_faces:
                if current_frame - self.recent_faces[matched_face_id] < self.memory_ttl:
                    # Recently seen → skip re-saving
                    return matched_face_id, max_similarity

            # Update recent memory
            self.recent_faces[matched_face_id] = current_frame
            return matched_face_id, max_similarity

        return None, 0.0
    
    def add_embedding(self, face_id: str, embedding: np.ndarray, current_frame: int):
        """Add new embedding to cache and remember it."""
        self.embeddings_cache.append((face_id, embedding))
        self.recent_faces[face_id] = current_frame



# ========================================
# Main DetectifAI Pipeline
# ========================================

class DetectifAI:
    """Main pipeline for facial recognition in CCTV footage with MongoDB integration."""
    
    def __init__(self, video_path: str, mongo_db, event_id: str,
                 camera_id: str = "CAM001", frame_skip: int = 5,
                 output_faces_dir: str = "faces", device: str = "cpu",
                 visualize: bool = False, output_video_path: Optional[str] = None,
                 minio_client=None, minio_bucket: Optional[str] = None):
        """
        Initialize DetectifAI system.
        
        Args:
            video_path: Path to input video file
            mongo_db: MongoDB database instance
            event_id: Event ID to associate faces with
            camera_id: Camera identifier
            frame_skip: Process every Nth frame (5 = every 5th frame)
            output_faces_dir: Directory to save face images
            device: 'cuda' or 'cpu'
            visualize: Whether to draw bounding boxes and save annotated video
            output_video_path: Path for annotated output video
            minio_client: MinIO client instance (optional)
            minio_bucket: MinIO bucket name for cloud storage (optional)
        """
        self.video_path = video_path
        self.event_id = event_id
        self.camera_id = camera_id
        self.frame_skip = frame_skip
        self.output_faces_dir = Path(output_faces_dir)
        self.visualize = visualize
        self.output_video_path = output_video_path
        self.minio_client = minio_client
        self.minio_bucket = minio_bucket
        
        # Create output directory
        self.output_faces_dir.mkdir(exist_ok=True)
        
        # Initialize components
        print("[DetectifAI] Initializing system...")
        self.detector = FaceDetector(device=device)
        self.embedder = FaceEmbedder(device=device)
        self.database = FaceDatabase(mongo_db=mongo_db)
        self.matcher = FaceMatcher(threshold=0.6)

        # Load all existing embeddings to prevent duplicates across events
        self.matcher.load_embeddings(self.database, event_id=None)
        
        print("[DetectifAI] System ready!")
    
    def _generate_face_id(self, frame_number: int, face_index: int) -> str:
        """Generate unique face ID."""
        return f"face_{self.event_id}_{frame_number:06d}_{face_index:02d}"
    
    def _save_face_image(self, face_tensor: torch.Tensor, face_id: str) -> str:
        """Save face image to disk."""
        face_np = face_tensor.permute(1, 2, 0).numpy()
        face_np = ((face_np + 1) / 2 * 255).astype(np.uint8)
        face_bgr = cv2.cvtColor(face_np, cv2.COLOR_RGB2BGR)
        
        filename = f"{face_id}.jpg"
        filepath = self.output_faces_dir / filename
        cv2.imwrite(str(filepath), face_bgr)
        
        return str(filepath)
    
    def _box_to_dict(self, box: np.ndarray) -> Dict:
        """Convert bounding box array to dictionary."""
        return {
            'x1': float(box[0]),
            'y1': float(box[1]),
            'x2': float(box[2]),
            'y2': float(box[3])
        }
    
    def process_video(self):
        """Process video and detect/track faces."""
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {self.video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"\n[DetectifAI] Processing video: {self.video_path}")
        print(f"[DetectifAI] Event ID: {self.event_id}")
        print(f"[DetectifAI] Total frames: {total_frames}, FPS: {fps}, Resolution: {width}x{height}")
        print(f"[DetectifAI] Processing every {self.frame_skip} frames\n")
        
        # Video writer for visualization
        out = None
        if self.visualize and self.output_video_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.output_video_path, fourcc, fps, (width, height))
        
        frame_number = 0
        processed_count = 0
        new_faces_count = 0
        matched_faces_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_number += 1
                
                # Skip frames
                if frame_number % self.frame_skip != 0:
                    if self.visualize and out:
                        out.write(frame)
                    continue
                
                processed_count += 1
                
                # Detect faces
                faces, boxes, probs = self.detector.detect_faces(frame)
                
                if not faces:
                    if self.visualize and out:
                        out.write(frame)
                    continue
                
                # Process each detected face
                for face_idx, (face_tensor, box, prob) in enumerate(zip(faces, boxes, probs)):
                    # Generate embedding
                    embedding = self.embedder.generate_embedding(face_tensor)

                    # Try to match with existing faces
                    matched_face_id, similarity = self.matcher.find_match(embedding, frame_number)


                    if matched_face_id:
                        # Existing face matched, do not store again
                        matched_faces_count += 1
                        print(f"Frame {frame_number:6d} | Face matched with {matched_face_id} | Similarity: {similarity:.2f}")
                        label = f"Match: {matched_face_id[:15]}.. ({similarity:.2f})"
                        color = (0, 255, 0)  # Green for matches
                    else:
                        # New unique face, generate ID, save image, add to database and cache
                        face_id = self._generate_face_id(frame_number, face_idx)

                        # Save face image
                        face_path = self._save_face_image(face_tensor, face_id)

                        # Convert bounding box to dict
                        bbox_dict = self._box_to_dict(box)

                        # Add to database
                        self.database.add_detected_face(
                            face_id=face_id,
                            event_id=self.event_id,
                            embedding=embedding,
                            face_image_path=face_path,
                            bounding_box=bbox_dict,
                            confidence=prob
                        )

                        # Add to matcher cache
                        self.matcher.add_embedding(face_id, embedding, frame_number)
                        new_faces_count += 1
                        print(f"Frame {frame_number:6d} | New Face {face_id} | Confidence: {prob:.2f}")
                        label = f"New: {face_id[:20]}"
                        color = (0, 165, 255)  # Orange for new faces
                    
                    # Draw bounding box if visualization enabled
                    if self.visualize:
                        x1, y1, x2, y2 = [int(coord) for coord in box]
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        
                        # Draw label background
                        (text_width, text_height), _ = cv2.getTextSize(
                            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                        )
                        cv2.rectangle(frame, (x1, y1 - text_height - 10), 
                                    (x1 + text_width, y1), color, -1)
                        cv2.putText(frame, label, (x1, y1 - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                
                if self.visualize and out:
                    out.write(frame)
                
                # Progress indicator
                if processed_count % 10 == 0:
                    progress = (frame_number / total_frames) * 100
                    print(f"[Progress] {progress:.1f}% ({frame_number}/{total_frames} frames)")
        
        finally:
            cap.release()
            if out:
                out.release()
            
        print(f"\n[DetectifAI] Processing complete!")
        print(f"[DetectifAI] Processed {processed_count} frames out of {total_frames} total frames")
        print(f"[DetectifAI] New faces detected: {new_faces_count}")
        print(f"[DetectifAI] Face matches found: {matched_faces_count}")
        print(f"[DetectifAI] Face images saved to: {self.output_faces_dir}")
        if self.visualize and self.output_video_path:
            print(f"[DetectifAI] Annotated video saved to: {self.output_video_path}")
    
    def get_statistics(self) -> Dict:
        """Get statistics about detected faces and matches."""
        total_faces = self.database.count_detected_faces(event_id=self.event_id)
        total_matches = self.database.count_face_matches()
        
        return {
            "event_id": self.event_id,
            "total_faces_detected": total_faces,
            "total_matches": total_matches,
            "database": self.database.db.name
        }


# ========================================
# Example Usage
# ========================================

def main():
    """Example usage of DetectifAI system with MongoDB."""
    
    # Import required libraries
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
    except ImportError:
        print("ERROR: Required libraries not installed.")
        print("Run: pip install pymongo python-dotenv")
        return
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration from environment variables
    MONGO_URI = os.getenv('MONGO_URI')
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
    MINIO_VIDEO_BUCKET = os.getenv('MINIO_VIDEO_BUCKET', 'detectifai-videos')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
    
    # Validate required environment variables
    if not MONGO_URI:
        print("ERROR: MONGO_URI not found in .env file")
        return
    
    # Extract database name from MongoDB URI
    # Format: mongodb+srv://user:pass@host/database?params
    try:
        db_name = MONGO_URI.split('/')[-1].split('?')[0]
        if not db_name:
            db_name = "detectifai"
    except:
        db_name = "detectifai"
    
    # Application configuration
    VIDEO_PATH = "suspicious_activity.mp4"  # Replace with your video path
    EVENT_ID = "event_001"  # Event ID to associate faces with
    CAMERA_ID = "CAM001"
    FRAME_SKIP = 5
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    VISUALIZE = True
    OUTPUT_VIDEO = "output_detected.mp4"
    
    print("=" * 70)
    print("DetectifAI - Facial Recognition System with MongoDB")
    print("=" * 70)
    print(f"Device: {DEVICE}")
    print(f"Input Video: {VIDEO_PATH}")
    print(f"MongoDB Database: {db_name}")
    print(f"Event ID: {EVENT_ID}")
    print(f"MinIO Endpoint: {MINIO_ENDPOINT}")
    print(f"MinIO Video Bucket: {MINIO_VIDEO_BUCKET}")
    print("=" * 70 + "\n")
    
    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[db_name]
        # Test connection
        client.server_info()
        print(f"[MongoDB] Connected successfully to {db_name}")
    except Exception as e:
        print(f"ERROR: Failed to connect to MongoDB: {e}")
        return
    
    # Initialize and run DetectifAI
    detectif = DetectifAI(
        video_path=VIDEO_PATH,
        mongo_db=db,
        event_id=EVENT_ID,
        camera_id=CAMERA_ID,
        frame_skip=FRAME_SKIP,
        device=DEVICE,
        visualize=VISUALIZE,
        output_video_path=OUTPUT_VIDEO if VISUALIZE else None
    )
    
    try:
        # Process video
        detectif.process_video()
        
        # Print statistics
        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)
        stats = detectif.get_statistics()
        print(f"Event ID: {stats['event_id']}")
        print(f"Total Faces Detected: {stats['total_faces_detected']}")
        print(f"Total Face Matches: {stats['total_matches']}")
        print(f"MongoDB Database: {stats['database']}")
        print("=" * 70)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("[MongoDB] Connection closed")


if __name__ == "__main__":
    main()
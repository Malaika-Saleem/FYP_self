"""
DetectifAI - Facial Recognition (Local Mode with Annotated Video)
Stores all faces and metadata locally, draws annotations on frames.

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
from sklearn.metrics.pairwise import cosine_similarity
import warnings
import joblib

warnings.filterwarnings('ignore')

# ========================================
# Configuration
# ========================================

TRAINED_MODEL_DIR = "trained_models"
CLASSIFIER_PATH = os.path.join(TRAINED_MODEL_DIR, "classifier_svm.pkl")
ENCODER_PATH = os.path.join(TRAINED_MODEL_DIR, "label_encoder.pkl")

ENABLE_PERSON_ID = True
CONFIDENCE_THRESHOLD = 0.5


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
# Local Storage Handler
# ========================================

class LocalFaceStorage:
    """Stores detected faces and matches locally as JSON"""
    def __init__(self, output_dir="faces_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.faces_json = self.output_dir / "detected_faces.json"
        if not self.faces_json.exists():
            with open(self.faces_json, "w") as f:
                json.dump([], f)
    
    def save_face(self, data: Dict):
        data["timestamp"] = datetime.utcnow().isoformat()
        with open(self.faces_json, "r+") as f:
            content = json.load(f)
            content.append(data)
            f.seek(0)
            json.dump(content, f, indent=2)
        print(f"[LocalStorage] Face saved: {data['face_id']}")


# ========================================
# Face Matcher
# ========================================

class FaceMatcher:
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.embeddings_cache = []
    
    def find_match(self, new_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        if not self.embeddings_cache:
            return None, 0.0
        stored_embeddings = np.array([emb for _, emb in self.embeddings_cache])
        similarities = cosine_similarity([new_embedding], stored_embeddings)[0]
        max_idx = np.argmax(similarities)
        max_similarity = similarities[max_idx]
        if max_similarity >= self.threshold:
            face_id = self.embeddings_cache[max_idx][0]
            return face_id, max_similarity
        return None, 0.0
    
    def add_embedding(self, face_id: str, embedding: np.ndarray):
        self.embeddings_cache.append((face_id, embedding))


# ========================================
# Main DetectifAI Pipeline (Annotated Video)
# ========================================

class DetectifAI:
    def __init__(self, video_path: str, event_id: str, frame_skip: int = 5,
                 output_faces_dir: str = "faces", device: str = "cpu",
                 output_video_path: Optional[str] = "output_annotated.mp4",
                 enable_person_id: bool = True, classifier_path=None, encoder_path=None):
        
        self.video_path = video_path
        self.event_id = event_id
        self.frame_skip = frame_skip
        self.output_faces_dir = Path(output_faces_dir)
        self.output_faces_dir.mkdir(exist_ok=True)
        self.output_video_path = output_video_path

        self.detector = FaceDetector(device=device)
        self.embedder = FaceEmbedder(device=device)
        self.matcher = FaceMatcher()
        self.storage = LocalFaceStorage()

        self.person_classifier = None
        if enable_person_id and classifier_path and encoder_path:
            self.person_classifier = PersonClassifier(classifier_path, encoder_path)
    
    def _generate_face_id(self, frame_number: int, face_index: int, person_name: Optional[str] = None) -> str:
        prefix = f"{person_name.replace(' ', '_')}" if person_name else "unknown"
        return f"face_{prefix}_{self.event_id}_{frame_number:06d}_{face_index:02d}"
    
    def _save_face_image(self, face_tensor: torch.Tensor, face_id: str) -> str:
        face_np = face_tensor.permute(1, 2, 0).numpy()
        face_np = ((face_np + 1) / 2 * 255).astype(np.uint8)
        face_bgr = cv2.cvtColor(face_np, cv2.COLOR_RGB2BGR)
        path = self.output_faces_dir / f"{face_id}.jpg"
        cv2.imwrite(str(path), face_bgr)
        return str(path)
    
    def process_video(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        
        # Setup video writer
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.output_video_path, fourcc, fps, (width, height))

        frame_number = 0
        new_faces = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_number += 1
            if frame_number % self.frame_skip != 0:
                out.write(frame)
                continue
            
            faces, boxes, probs = self.detector.detect_faces(frame)
            for i, (face, box, prob) in enumerate(zip(faces, boxes, probs)):
                embedding = self.embedder.generate_embedding(face)
                person_name, conf = (None, 0.0)
                
                if self.person_classifier and self.person_classifier.enabled:
                    person_name, conf = self.person_classifier.identify_person(embedding)
                
                matched_id, sim = self.matcher.find_match(embedding)
                if not matched_id:
                    face_id = self._generate_face_id(frame_number, i, person_name)
                    face_path = self._save_face_image(face, face_id)
                    self.matcher.add_embedding(face_id, embedding)
                    self.storage.save_face({
                        "face_id": face_id,
                        "person_name": person_name,
                        "confidence": float(conf),
                        "similarity": float(sim),
                        "image_path": face_path
                    })
                    new_faces += 1

                # Draw box & label
                (x1, y1, x2, y2) = map(int, box)
                color = (0, 255, 0) if person_name else (0, 0, 255)
                label = f"{person_name or 'Unknown'} ({conf:.2f})"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            out.write(frame)
        
        cap.release()
        out.release()
        print(f"\n[DetectifAI] ✅ Done! {new_faces} new faces saved locally.")
        print(f"[DetectifAI] 🎥 Annotated video saved as: {self.output_video_path}")


# ========================================
# Example Usage
# ========================================

if __name__ == "__main__":
    VIDEO_PATH = "suspicious_activity.mp4"
    EVENT_ID = "event_001"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    detectif = DetectifAI(
        video_path=VIDEO_PATH,
        event_id=EVENT_ID,
        frame_skip=5,
        device=DEVICE,
        enable_person_id=ENABLE_PERSON_ID,
        classifier_path=CLASSIFIER_PATH,
        encoder_path=ENCODER_PATH
    )
    detectif.process_video()

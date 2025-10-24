import faiss
import numpy as np
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pickle
from typing import List, Dict, Tuple, Optional
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FAISSIndexManager:
    """Manages FAISS indices for text and visual embeddings"""
    
    def __init__(self, mongo_uri: str, db_name: str = None):
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client.get_default_database() if not db_name else self.mongo_client[db_name]
        
        # Collection references
        self.event_descriptions = self.db.event_description
        self.events = self.db.event
        
        # FAISS indices
        self.text_index = None
        self.visual_index = None
        
        # Index metadata
        self.text_index_metadata = {}  # Maps FAISS ID to MongoDB document ID
        self.visual_index_metadata = {}  # Maps FAISS ID to MongoDB document ID
        
        # Embedding dimensions (adjust based on your embedding model)
        self.text_embedding_dim = 384  # Common for sentence-transformers
        self.visual_embedding_dim = 512  # Common for visual embeddings
        
        # Index file paths
        self.text_index_path = "faiss_text_index.bin"
        self.visual_index_path = "faiss_visual_index.bin"
        self.text_metadata_path = "faiss_text_metadata.pkl"
        self.visual_metadata_path = "faiss_visual_metadata.pkl"
        
        self._initialize_indices()
    
    def _initialize_indices(self):
        """Initialize or load existing FAISS indices"""
        try:
            # Try to load existing indices
            if os.path.exists(self.text_index_path) and os.path.exists(self.text_metadata_path):
                self._load_text_index()
                logger.info("Loaded existing text index")
            else:
                self._create_text_index()
                logger.info("Created new text index")
            
            if os.path.exists(self.visual_index_path) and os.path.exists(self.visual_metadata_path):
                self._load_visual_index()
                logger.info("Loaded existing visual index")
            else:
                self._create_visual_index()
                logger.info("Created new visual index")
                
        except Exception as e:
            logger.error(f"Error initializing indices: {e}")
            # Fallback to creating new indices
            self._create_text_index()
            self._create_visual_index()
    
    def _create_text_index(self):
        """Create a new FAISS index for text embeddings"""
        self.text_index = faiss.IndexFlatIP(self.text_embedding_dim)  # Inner product for cosine similarity
        self.text_index_metadata = {}
        self._save_text_index()
    
    def _create_visual_index(self):
        """Create a new FAISS index for visual embeddings"""
        self.visual_index = faiss.IndexFlatIP(self.visual_embedding_dim)  # Inner product for cosine similarity
        self.visual_index_metadata = {}
        self._save_visual_index()
    
    def _load_text_index(self):
        """Load text index from disk"""
        self.text_index = faiss.read_index(self.text_index_path)
        with open(self.text_metadata_path, 'rb') as f:
            self.text_index_metadata = pickle.load(f)
    
    def _load_visual_index(self):
        """Load visual index from disk"""
        self.visual_index = faiss.read_index(self.visual_index_path)
        with open(self.visual_metadata_path, 'rb') as f:
            self.visual_index_metadata = pickle.load(f)
    
    def _save_text_index(self):
        """Save text index to disk"""
        if self.text_index is not None:
            faiss.write_index(self.text_index, self.text_index_path)
            with open(self.text_metadata_path, 'wb') as f:
                pickle.dump(self.text_index_metadata, f)
    
    def _save_visual_index(self):
        """Save visual index to disk"""
        if self.visual_index is not None:
            faiss.write_index(self.visual_index, self.visual_index_path)
            with open(self.visual_metadata_path, 'wb') as f:
                pickle.dump(self.visual_index_metadata, f)
    
    def rebuild_text_index(self):
        """Rebuild text index from MongoDB data"""
        logger.info("Rebuilding text index from MongoDB...")
        
        # Create new index
        self._create_text_index()
        
        # Fetch all event descriptions with embeddings
        cursor = self.event_descriptions.find(
            {"text_embedding": {"$exists": True, "$ne": []}},
            {"_id": 0, "description_id": 1, "text_embedding": 1}
        )
        
        embeddings = []
        metadata = {}
        
        for doc in cursor:
            embedding = np.array(doc["text_embedding"], dtype=np.float32)
            if len(embedding) == self.text_embedding_dim:
                faiss_id = len(embeddings)
                embeddings.append(embedding)
                metadata[faiss_id] = doc["description_id"]
        
        if embeddings:
            embeddings_array = np.vstack(embeddings)
            self.text_index.add(embeddings_array)
            self.text_index_metadata = metadata
            self._save_text_index()
            logger.info(f"Rebuilt text index with {len(embeddings)} embeddings")
        else:
            logger.warning("No text embeddings found in MongoDB")
    
    def rebuild_visual_index(self):
        """Rebuild visual index from MongoDB data"""
        logger.info("Rebuilding visual index from MongoDB...")
        
        # Create new index
        self._create_visual_index()
        
        # Fetch all events with visual embeddings
        cursor = self.events.find(
            {"visual_embedding": {"$exists": True, "$ne": []}},
            {"_id": 0, "event_id": 1, "visual_embedding": 1}
        )
        
        embeddings = []
        metadata = {}
        
        for doc in cursor:
            embedding = np.array(doc["visual_embedding"], dtype=np.float32)
            if len(embedding) == self.visual_embedding_dim:
                faiss_id = len(embeddings)
                embeddings.append(embedding)
                metadata[faiss_id] = doc["event_id"]
        
        if embeddings:
            embeddings_array = np.vstack(embeddings)
            self.visual_index.add(embeddings_array)
            self.visual_index_metadata = metadata
            self._save_visual_index()
            logger.info(f"Rebuilt visual index with {len(embeddings)} embeddings")
        else:
            logger.warning("No visual embeddings found in MongoDB")
    
    def add_text_embedding(self, description_id: str, embedding: List[float]) -> bool:
        """Add a text embedding to the index"""
        try:
            embedding_array = np.array(embedding, dtype=np.float32).reshape(1, -1)
            
            if embedding_array.shape[1] != self.text_embedding_dim:
                logger.error(f"Text embedding dimension mismatch: expected {self.text_embedding_dim}, got {embedding_array.shape[1]}")
                return False
            
            faiss_id = self.text_index.ntotal
            self.text_index.add(embedding_array)
            self.text_index_metadata[faiss_id] = description_id
            self._save_text_index()
            
            logger.info(f"Added text embedding for description_id: {description_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding text embedding: {e}")
            return False
    
    def add_visual_embedding(self, event_id: str, embedding: List[float]) -> bool:
        """Add a visual embedding to the index"""
        try:
            embedding_array = np.array(embedding, dtype=np.float32).reshape(1, -1)
            
            if embedding_array.shape[1] != self.visual_embedding_dim:
                logger.error(f"Visual embedding dimension mismatch: expected {self.visual_embedding_dim}, got {embedding_array.shape[1]}")
                return False
            
            faiss_id = self.visual_index.ntotal
            self.visual_index.add(embedding_array)
            self.visual_index_metadata[faiss_id] = event_id
            self._save_visual_index()
            
            logger.info(f"Added visual embedding for event_id: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding visual embedding: {e}")
            return False
    
    def search_text_embeddings(self, query_embedding: List[float], k: int = 10) -> List[Dict]:
        """Search for similar text embeddings"""
        try:
            if self.text_index.ntotal == 0:
                return []
            
            query_array = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            
            if query_array.shape[1] != self.text_embedding_dim:
                logger.error(f"Query embedding dimension mismatch: expected {self.text_embedding_dim}, got {query_array.shape[1]}")
                return []
            
            # Search FAISS
            scores, indices = self.text_index.search(query_array, min(k, self.text_index.ntotal))
            
            # Fetch corresponding documents from MongoDB
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx in self.text_index_metadata:
                    description_id = self.text_index_metadata[idx]
                    doc = self.event_descriptions.find_one(
                        {"description_id": description_id},
                        {"_id": 0}
                    )
                    if doc:
                        doc["similarity_score"] = float(score)
                        results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching text embeddings: {e}")
            return []
    
    def search_visual_embeddings(self, query_embedding: List[float], k: int = 10) -> List[Dict]:
        """Search for similar visual embeddings"""
        try:
            if self.visual_index.ntotal == 0:
                return []
            
            query_array = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            
            if query_array.shape[1] != self.visual_embedding_dim:
                logger.error(f"Query embedding dimension mismatch: expected {self.visual_embedding_dim}, got {query_array.shape[1]}")
                return []
            
            # Search FAISS
            scores, indices = self.visual_index.search(query_array, min(k, self.visual_index.ntotal))
            
            # Fetch corresponding documents from MongoDB
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx in self.visual_index_metadata:
                    event_id = self.visual_index_metadata[idx]
                    doc = self.events.find_one(
                        {"event_id": event_id},
                        {"_id": 0}
                    )
                    if doc:
                        doc["similarity_score"] = float(score)
                        results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching visual embeddings: {e}")
            return []
    
    def get_index_stats(self) -> Dict:
        """Get statistics about the indices"""
        return {
            "text_index_size": self.text_index.ntotal if self.text_index else 0,
            "visual_index_size": self.visual_index.ntotal if self.visual_index else 0,
            "text_embedding_dim": self.text_embedding_dim,
            "visual_embedding_dim": self.visual_embedding_dim
        }
    
    def close(self):
        """Close the index manager and save indices"""
        self._save_text_index()
        self._save_visual_index()
        self.mongo_client.close()

# Global instance
faiss_manager = None

def get_faiss_manager() -> FAISSIndexManager:
    """Get the global FAISS manager instance"""
    global faiss_manager
    if faiss_manager is None:
        mongo_uri = os.getenv("MONGO_URI")
        faiss_manager = FAISSIndexManager(mongo_uri)
    return faiss_manager

def generate_text_embedding(text: str) -> List[float]:
    """
    Placeholder function to generate text embeddings.
    Replace this with your actual embedding model (e.g., sentence-transformers).
    """
    # For now, return a random embedding of the correct dimension
    # In production, use a proper embedding model like:
    # from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer('all-MiniLM-L6-v2')
    # return model.encode(text).tolist()
    
    np.random.seed(hash(text) % 2**32)  # Deterministic based on text
    return np.random.randn(384).astype(np.float32).tolist()

def generate_visual_embedding(image_data: bytes = None) -> List[float]:
    """
    Placeholder function to generate visual embeddings.
    Replace this with your actual visual embedding model.
    """
    # For now, return a random embedding of the correct dimension
    # In production, use a proper visual embedding model
    
    np.random.seed(42)  # Fixed seed for demo
    return np.random.randn(512).astype(np.float32).tolist()

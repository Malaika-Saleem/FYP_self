"""
Caption Search Module for DetectifAI

This module provides caption-based search functionality using FAISS index
and MongoDB for retrieving video descriptions based on text queries.
"""

import os
import json
import logging
import numpy as np
import faiss
from typing import List, Dict, Optional, Tuple
from pymongo import MongoClient
from dotenv import load_dotenv

# Optional import for sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available - caption search will not work")

load_dotenv()

logger = logging.getLogger(__name__)

# Paths for FAISS index and id map
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss_captions.index")
FAISS_IDMAP_PATH = os.path.join(BASE_DIR, "faiss_captions_idmap.json")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/detectifai")

# Embedding model name
EMBEDDING_MODEL = "all-mpnet-base-v2"
EMBEDDING_DIM = 768  # Dimension for all-mpnet-base-v2


class CaptionSearchEngine:
    """Search engine for caption-based video search using FAISS"""
    
    def __init__(self):
        """Initialize the caption search engine"""
        self.faiss_index = None
        self.id_map = {}  # Maps FAISS index -> description_id
        self.embedding_model = None
        self.mongo_client = None
        self.db = None
        self.collection = None
        
        # Initialize components
        self._load_faiss_index()
        self._load_embedding_model()
        self._connect_mongodb()
    
    def _load_faiss_index(self):
        """Load FAISS index and id map from disk"""
        try:
            if os.path.exists(FAISS_INDEX_PATH):
                self.faiss_index = faiss.read_index(FAISS_INDEX_PATH)
                logger.info(f"✅ Loaded FAISS index from {FAISS_INDEX_PATH}")
                logger.info(f"   Index size: {self.faiss_index.ntotal} vectors")
            else:
                logger.warning(f"⚠️ FAISS index not found at {FAISS_INDEX_PATH}")
                return
            
            if os.path.exists(FAISS_IDMAP_PATH):
                with open(FAISS_IDMAP_PATH, 'r', encoding='utf-8') as f:
                    id_map_list = json.load(f)
                    # Convert list to dict: index -> description_id
                    self.id_map = {i: desc_id for i, desc_id in enumerate(id_map_list)}
                logger.info(f"✅ Loaded FAISS id map from {FAISS_IDMAP_PATH}")
                logger.info(f"   Mapped {len(self.id_map)} indices")
            else:
                logger.warning(f"⚠️ FAISS id map not found at {FAISS_IDMAP_PATH}")
                
        except Exception as e:
            logger.error(f"❌ Error loading FAISS index: {e}")
            self.faiss_index = None
    
    def _load_embedding_model(self):
        """Load sentence transformer model for generating query embeddings"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("⚠️ sentence-transformers not available - cannot generate embeddings")
            return
        
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}...")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"✅ Loaded embedding model: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"❌ Error loading embedding model: {e}")
            self.embedding_model = None
    
    def _connect_mongodb(self):
        """Connect to MongoDB"""
        try:
            self.mongo_client = MongoClient(MONGO_URI)
            self.db = self.mongo_client.get_default_database()
            self.collection = self.db["event_descriptions"]
            logger.info("✅ Connected to MongoDB")
        except Exception as e:
            logger.error(f"❌ Error connecting to MongoDB: {e}")
            self.mongo_client = None
    
    def is_ready(self) -> bool:
        """Check if the search engine is ready to use"""
        return (
            self.faiss_index is not None and
            self.embedding_model is not None and
            self.mongo_client is not None and
            self.faiss_index.ntotal > 0
        )
    
    def search(self, query_text: str, top_k: int = 10, min_score: float = 0.0) -> List[Dict]:
        """
        Search for captions similar to the query text
        
        Args:
            query_text: Text query to search for
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of result dictionaries with caption, video reference, and similarity score
        """
        if not self.is_ready():
            logger.warning("⚠️ Search engine not ready - missing components")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                query_text,
                normalize_embeddings=True,
                show_progress_bar=False
            ).astype("float32")
            
            # Reshape for FAISS (1, dim)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Search FAISS index
            k = min(top_k, self.faiss_index.ntotal)
            scores, indices = self.faiss_index.search(query_embedding, k)
            
            # Process results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx not in self.id_map:
                    continue
                
                if score < min_score:
                    continue
                
                description_id = self.id_map[idx]
                
                # Fetch document from MongoDB
                doc = self.collection.find_one(
                    {"description_id": description_id},
                    {"_id": 0}
                )
                
                if doc:
                    result = {
                        "description_id": doc.get("description_id"),
                        "event_id": doc.get("event_id"),
                        "caption": doc.get("caption"),
                        "confidence": doc.get("confidence", 0.0),
                        "similarity_score": float(score),
                        "video_reference": doc.get("video_reference", {}),
                        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
                    }
                    results.append(result)
            
            logger.info(f"✅ Found {len(results)} results for query: '{query_text[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get statistics about the search engine"""
        return {
            "faiss_index_loaded": self.faiss_index is not None,
            "faiss_index_size": self.faiss_index.ntotal if self.faiss_index else 0,
            "id_map_size": len(self.id_map),
            "embedding_model_loaded": self.embedding_model is not None,
            "embedding_model": EMBEDDING_MODEL if self.embedding_model else None,
            "embedding_dim": EMBEDDING_DIM,
            "mongodb_connected": self.mongo_client is not None,
            "ready": self.is_ready()
        }


# Global instance
_caption_search_engine = None


def get_caption_search_engine() -> CaptionSearchEngine:
    """Get the global caption search engine instance"""
    global _caption_search_engine
    if _caption_search_engine is None:
        _caption_search_engine = CaptionSearchEngine()
    return _caption_search_engine


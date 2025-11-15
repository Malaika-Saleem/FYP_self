#!/usr/bin/env python3
"""
DetectifAI Facial Recognition Setup Script

This script helps set up the facial recognition system:
1. Creates necessary directories
2. Initializes FAISS index
3. Tests MongoDB connection
4. Validates facial recognition dependencies

Run with: python setup_facial_recognition.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def setup_logging():
    """Setup logging for the setup script"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/setup_facial_recognition.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed"""
    logger = logging.getLogger(__name__)
    
    required_packages = [
        'torch',
        'torchvision', 
        'facenet_pytorch',
        'faiss',
        'pymongo',
        'cv2',
        'numpy',
        'PIL'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'PIL':
                from PIL import Image
            elif package == 'faiss':
                import faiss
            else:
                __import__(package)
            logger.info(f"OK {package} is installed")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"MISSING {package} is NOT installed")
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.error("Please install missing packages with: pip install -r backend/requirements.txt")
        return False
    
    logger.info("OK All required packages are installed")
    return True

def create_directories():
    """Create necessary directories for facial recognition"""
    logger = logging.getLogger(__name__)
    
    directories = [
        'model',
        'model/faces',
        'model/faces_data',
        'model/trained_models',
        'logs'
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")
    
    logger.info("✅ All directories created successfully")

def initialize_faiss_index():
    """Initialize an empty FAISS index"""
    logger = logging.getLogger(__name__)
    
    try:
        import faiss
        import json
        
        # Create FAISS index
        embedding_dim = 512  # InceptionResnetV1 embedding dimension
        index = faiss.IndexFlatIP(embedding_dim)
        
        # Save index
        index_path = "model/faiss_face_index.bin"
        faiss.write_index(index, index_path)
        
        # Save empty ID mapping
        id_map_path = "model/faiss_id_map.json"
        with open(id_map_path, 'w') as f:
            json.dump([], f)
        
        logger.info(f"✅ Initialized FAISS index at {index_path}")
        logger.info(f"✅ Initialized ID mapping at {id_map_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize FAISS index: {e}")
        return False

def test_mongodb_connection():
    """Test MongoDB connection"""
    logger = logging.getLogger(__name__)
    
    try:
        from dotenv import load_dotenv
        from pymongo import MongoClient
        
        # Load environment variables
        load_dotenv()
        
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            logger.warning("⚠️ MONGO_URI not found in environment variables")
            logger.warning("Please configure MongoDB in .env file for facial recognition metadata storage")
            return False
        
        # Test connection
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # Will raise exception if connection fails
        
        # Test database operations
        db = client['detectifai']
        collection = db['test_connection']
        collection.insert_one({'test': 'connection', 'timestamp': '2024-01-01'})
        collection.delete_one({'test': 'connection'})
        
        client.close()
        
        logger.info("✅ MongoDB connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        logger.error("Please check your MONGO_URI in .env file")
        return False

def test_facial_recognition():
    """Test facial recognition system"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import the facial recognition module
        from backend.facial_recognition import FacialRecognitionIntegrated
        from backend.config import VideoProcessingConfig
        
        # Create test config
        config = VideoProcessingConfig()
        config.enable_facial_recognition = True
        config.output_base_dir = "test_output"
        
        # Initialize facial recognition
        face_system = FacialRecognitionIntegrated(config)
        
        if face_system.enabled:
            logger.info("✅ Facial recognition system initialized successfully")
            logger.info(f"Device: {face_system.device}")
            logger.info(f"FAISS index size: {face_system.faiss_index.index.ntotal if face_system.faiss_index.index else 0}")
            
            # Clean up
            face_system.cleanup()
            return True
        else:
            logger.error("❌ Facial recognition system failed to initialize")
            return False
            
    except Exception as e:
        logger.error(f"❌ Facial recognition test failed: {e}")
        return False

def create_sample_env():
    """Create .env file from template if it doesn't exist"""
    logger = logging.getLogger(__name__)
    
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            logger.info("✅ Created .env file from template")
            logger.warning("⚠️ Please edit .env file and configure MONGO_URI")
        else:
            logger.warning("⚠️ .env.example not found, cannot create .env file")
    else:
        logger.info("✅ .env file already exists")

def main():
    """Main setup function"""
    print("="*60)
    print("DetectifAI Facial Recognition Setup")
    print("="*60)
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting DetectifAI facial recognition setup...")
    
    # Step 1: Check dependencies
    print("\n1. Checking dependencies...")
    if not check_dependencies():
        print("❌ Dependency check failed. Please install required packages.")
        return False
    
    # Step 2: Create directories
    print("\n2. Creating directories...")
    create_directories()
    
    # Step 3: Create .env file
    print("\n3. Setting up environment file...")
    create_sample_env()
    
    # Step 4: Initialize FAISS
    print("\n4. Initializing FAISS index...")
    if not initialize_faiss_index():
        print("❌ FAISS initialization failed.")
        return False
    
    # Step 5: Test MongoDB (optional)
    print("\n5. Testing MongoDB connection...")
    mongodb_ok = test_mongodb_connection()
    if not mongodb_ok:
        print("⚠️ MongoDB connection failed - facial recognition will work but metadata won't be stored")
    
    # Step 6: Test facial recognition system
    print("\n6. Testing facial recognition system...")
    if not test_facial_recognition():
        print("❌ Facial recognition system test failed.")
        return False
    
    # Success summary
    print("\n" + "="*60)
    print("✅ DetectifAI Facial Recognition Setup Complete!")
    print("="*60)
    print("\nSystem Status:")
    print(f"✅ Dependencies: Installed")
    print(f"✅ Directories: Created")
    print(f"✅ FAISS Index: Initialized")
    print(f"{'✅' if mongodb_ok else '⚠️'} MongoDB: {'Connected' if mongodb_ok else 'Not configured'}")
    print(f"✅ Facial Recognition: Ready")
    
    if not mongodb_ok:
        print("\n⚠️ IMPORTANT: Configure MongoDB in .env file for metadata storage")
        print("Edit .env file and set MONGO_URI to your MongoDB connection string")
    
    print("\nYou can now run DetectifAI with facial recognition enabled!")
    print("The system will apply facial recognition to suspicious activity frames only.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
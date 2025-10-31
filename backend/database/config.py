"""
Database Configuration for DetectifAI Backend

This module handles connections to MongoDB Atlas and local MinIO for the DetectifAI system.
It provides centralized configuration and connection management.
"""

import os
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv
import logging
from datetime import timedelta

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Configuration class for database connections"""
    
    def __init__(self):
        # MongoDB Atlas connection (same as frontend)
        self.mongo_uri = os.getenv(
            'MONGO_URI', 
            'mongodb+srv://detectifai_user:DetectifAI123@cluster0.6f9uj.mongodb.net/detectifai?retryWrites=true&w=majority&appName=Cluster0'
        )
        self.mongo_db_name = 'detectifai'
        
        # MinIO Local connection
        self.minio_endpoint = os.getenv('MINIO_ENDPOINT', '127.0.0.1:9000')  # Use IP address instead of localhost
        self.minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'admin')
        self.minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'adminpassword')
        self.minio_video_bucket = os.getenv('MINIO_VIDEO_BUCKET', 'detectifai-videos')
        self.minio_keyframe_bucket = os.getenv('MINIO_KEYFRAME_BUCKET', 'detectifai-keyframes')
        self.minio_secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

class DatabaseManager:
    """Central database manager for MongoDB and MinIO connections"""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self._mongodb_client = None
        self._db = None
        self._minio_client = None
        
    @property
    def mongo_client(self):
        """Lazy loading MongoDB client"""
        if self._mongodb_client is None:
            try:
                self._mongodb_client = MongoClient(self.config.mongo_uri)
                # Test connection
                self._mongodb_client.admin.command('ping')
                logger.info("✅ MongoDB connection established successfully")
            except Exception as e:
                logger.error(f"❌ Failed to connect to MongoDB: {e}")
                raise
        return self._mongodb_client
    
    @property  
    def db(self):
        """Get MongoDB database instance"""
        if self._db is None:
            self._db = self.mongo_client[self.config.mongo_db_name]
        return self._db
    
    @property
    def minio_client(self):
        """Lazy loading MinIO client"""
        if self._minio_client is None:
            try:
                self._minio_client = Minio(
                    self.config.minio_endpoint,
                    access_key=self.config.minio_access_key,
                    secret_key=self.config.minio_secret_key,
                    secure=self.config.minio_secure
                )
                
                # Test connection and ensure bucket exists
                self._ensure_bucket_exists()
                logger.info("✅ MinIO connection established successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to MinIO: {e}")
                raise
        return self._minio_client
    
    def _ensure_bucket_exists(self):
        """Ensure the detectifai buckets exist"""
        try:
            # Ensure video bucket exists
            if not self._minio_client.bucket_exists(self.config.minio_video_bucket):
                self._minio_client.make_bucket(self.config.minio_video_bucket)
                logger.info(f"✅ Created MinIO video bucket: {self.config.minio_video_bucket}")
            else:
                logger.info(f"✅ MinIO video bucket exists: {self.config.minio_video_bucket}")
                
            # Ensure keyframe bucket exists
            if not self._minio_client.bucket_exists(self.config.minio_keyframe_bucket):
                self._minio_client.make_bucket(self.config.minio_keyframe_bucket)
                logger.info(f"✅ Created MinIO keyframe bucket: {self.config.minio_keyframe_bucket}")
            else:
                logger.info(f"✅ MinIO keyframe bucket exists: {self.config.minio_keyframe_bucket}")
        except S3Error as e:
            logger.error(f"❌ Failed to create/check MinIO buckets: {e}")
            raise
    
    def test_connections(self):
        """Test both MongoDB and MinIO connections"""
        mongodb_success = False
        minio_success = False
        
        try:
            # Test MongoDB
            self.mongo_client.admin.command('ping')
            collections = self.db.list_collection_names()
            logger.info(f"✅ MongoDB test successful. Collections: {collections}")
            print(f"✅ MongoDB connected successfully. Collections: {collections}")
            mongodb_success = True
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            print(f"❌ MongoDB connection failed: {e}")
        
        try:
            # Test MinIO
            buckets = self.minio_client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            logger.info(f"✅ MinIO test successful. Buckets: {bucket_names}")
            print(f"✅ MinIO connected successfully. Buckets: {bucket_names}")
            minio_success = True
            
        except Exception as e:
            logger.error(f"❌ MinIO connection failed: {e}")
            print(f"❌ MinIO connection failed: {e}")
            print("💡 Note: MinIO server may not be running. Start MinIO server for full functionality.")
        
        return mongodb_success  # At minimum, we need MongoDB working
    
    def close_connections(self):
        """Close database connections"""
        if self._mongodb_client:
            self._mongodb_client.close()
            logger.info("MongoDB connection closed")

def get_presigned_url(minio_client, bucket_name: str, object_name: str, expires: timedelta = timedelta(hours=1)):
    """Generate presigned URL for MinIO object access"""
    try:
        return minio_client.presigned_get_object(bucket_name, object_name, expires=expires)
    except S3Error as e:
        logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
        return None

if __name__ == "__main__":
    # Test connections
    db_manager = DatabaseManager()
    if db_manager.test_connections():
        print("✅ All database connections working!")
    else:
        print("❌ Database connection issues detected")
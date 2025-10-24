"""
MongoDB Integration Test - Actual Database Write & Schema Validation
Tests that records can be written to MongoDB and pass schema validators
"""

import os
import sys
import logging
from datetime import datetime
import uuid

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database.config import DatabaseManager
from database.models import VideoFileModel, EventModel, prepare_for_mongodb
from pymongo.errors import WriteError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MongoDBIntegrationTest:
    """Test actual writes to MongoDB"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.db
        self.test_video_id = f"test_{uuid.uuid4().hex[:8]}"
        self.test_event_id = f"evt_{uuid.uuid4().hex[:8]}"
        
    def cleanup(self):
        """Remove test data"""
        try:
            self.db.video_file.delete_many({"video_id": {"$regex": "^test_"}})
            self.db.event.delete_many({"event_id": {"$regex": "^evt_"}})
            logger.info("🧹 Cleanup complete")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
    
    def test_video_insert(self):
        """Test inserting a video record"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Insert Video to MongoDB")
        logger.info("="*60)
        
        try:
            # Create video model
            video = VideoFileModel(
                video_id=self.test_video_id,
                user_id="test_user_001",
                file_path=f"uploads/{self.test_video_id}.mp4",
                fps=30.0,
                duration_secs=120,
                file_size_bytes=15728640,
                codec="h264",
                meta_data={
                    "processing_status": "completed",
                    "original_filename": "test_video.mp4",
                    "resolution": "1920x1080"
                }
            )
            
            # Convert to dict and prepare for MongoDB
            video_dict = prepare_for_mongodb(video.to_dict())
            
            # Insert into MongoDB
            result = self.db.video_file.insert_one(video_dict)
            
            logger.info(f"✅ Video inserted with _id: {result.inserted_id}")
            
            # Verify we can retrieve it
            retrieved = self.db.video_file.find_one({"video_id": self.test_video_id})
            assert retrieved is not None, "Could not retrieve inserted video"
            assert retrieved["video_id"] == self.test_video_id
            assert retrieved["fps"] == 30.0
            assert retrieved["duration_secs"] == 120
            assert isinstance(retrieved["duration_secs"], int), "duration_secs should be int"
            
            logger.info("✅ Video retrieved successfully")
            logger.info("✅ Field types validated (fps=double, duration_secs=int)")
            logger.info("✅ MongoDB schema validator accepted the record")
            logger.info("✅ TEST PASSED\n")
            return True
            
        except WriteError as e:
            logger.error(f"❌ MongoDB WriteError (schema validation failed): {e}")
            logger.error("This means the data doesn't match the collection's schema validator")
            return False
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_event_insert(self):
        """Test inserting an event record"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Insert Event to MongoDB")
        logger.info("="*60)
        
        try:
            # Create event model
            event = EventModel(
                event_id=self.test_event_id,
                video_id=self.test_video_id,
                start_timestamp_ms=5000,
                end_timestamp_ms=10000,
                event_type="object_detection_fire",
                confidence_score=0.95,
                bounding_boxes={
                    "detections": [
                        {
                            "x": 100,
                            "y": 150,
                            "width": 50,
                            "height": 80,
                            "confidence": 0.95,
                            "class_name": "fire"
                        }
                    ]
                }
            )
            
            # Convert to dict and prepare for MongoDB
            event_dict = prepare_for_mongodb(event.to_dict())
            
            # Insert into MongoDB
            result = self.db.event.insert_one(event_dict)
            
            logger.info(f"✅ Event inserted with _id: {result.inserted_id}")
            
            # Verify we can retrieve it
            retrieved = self.db.event.find_one({"event_id": self.test_event_id})
            assert retrieved is not None, "Could not retrieve inserted event"
            assert retrieved["event_id"] == self.test_event_id
            assert retrieved["start_timestamp_ms"] == 5000
            assert retrieved["end_timestamp_ms"] == 10000
            assert isinstance(retrieved["start_timestamp_ms"], int), "start_timestamp_ms should be int (long)"
            assert isinstance(retrieved["end_timestamp_ms"], int), "end_timestamp_ms should be int (long)"
            
            logger.info("✅ Event retrieved successfully")
            logger.info("✅ Timestamp fields are int (bsonType: long)")
            logger.info("✅ MongoDB schema validator accepted the record")
            logger.info("✅ TEST PASSED\n")
            return True
            
        except WriteError as e:
            logger.error(f"❌ MongoDB WriteError (schema validation failed): {e}")
            logger.error("This means the data doesn't match the collection's schema validator")
            return False
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_invalid_video_rejected(self):
        """Test that invalid video is rejected by schema validator"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Invalid Video Should Be Rejected")
        logger.info("="*60)
        
        try:
            # Try to insert video with wrong field types
            invalid_video = {
                "video_id": f"test_invalid_{uuid.uuid4().hex[:8]}",
                "user_id": "test_user",
                "file_path": "test.mp4",
                "fps": "30",  # WRONG: Should be float, not string
                "duration_secs": "120"  # WRONG: Should be int, not string
            }
            
            try:
                self.db.video_file.insert_one(invalid_video)
                logger.error("❌ Invalid video was NOT rejected - schema validator may be disabled!")
                return False
            except WriteError as e:
                logger.info(f"✅ MongoDB correctly rejected invalid video: {e.details['errInfo']['details']}")
                logger.info("✅ Schema validator is working")
                logger.info("✅ TEST PASSED\n")
                return True
                
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            return False
    
    def test_invalid_event_rejected(self):
        """Test that invalid event is rejected by schema validator"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Invalid Event Should Be Rejected")
        logger.info("="*60)
        
        try:
            # Try to insert event with wrong timestamp type
            invalid_event = {
                "event_id": f"evt_invalid_{uuid.uuid4().hex[:8]}",
                "video_id": self.test_video_id,
                "start_timestamp_ms": 5.5,  # WRONG: Should be int (long), not float
                "end_timestamp_ms": 10.5,  # WRONG: Should be int (long), not float
                "event_type": "test_event"
            }
            
            try:
                self.db.event.insert_one(invalid_event)
                logger.error("❌ Invalid event was NOT rejected - schema validator may be disabled!")
                return False
            except WriteError as e:
                logger.info(f"✅ MongoDB correctly rejected invalid event: {e.details['errInfo']['details']}")
                logger.info("✅ Schema validator enforcing timestamp_ms as int (long)")
                logger.info("✅ TEST PASSED\n")
                return True
                
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            return False
    
    def run_all_tests(self):
        """Run all MongoDB integration tests"""
        logger.info("\n" + "="*80)
        logger.info("🗄️  MONGODB INTEGRATION TESTS")
        logger.info("="*80)
        logger.info("Testing actual database writes and schema validation\n")
        
        # Check connection
        try:
            self.db.command('ping')
            logger.info("✅ MongoDB connection successful")
            logger.info(f"Database: {self.db.name}\n")
        except Exception as e:
            logger.error(f"❌ Cannot connect to MongoDB: {e}")
            return False
        
        passed = 0
        failed = 0
        
        tests = [
            ("Insert Video", self.test_video_insert),
            ("Insert Event", self.test_event_insert),
            ("Reject Invalid Video", self.test_invalid_video_rejected),
            ("Reject Invalid Event", self.test_invalid_event_rejected)
        ]
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"❌ {test_name} crashed: {e}")
                failed += 1
        
        # Cleanup
        self.cleanup()
        
        # Summary
        total = passed + failed
        logger.info("\n" + "="*80)
        logger.info("📊 MONGODB INTEGRATION TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"Success Rate: {(passed/total*100):.1f}%")
        logger.info("="*80 + "\n")
        
        return failed == 0


def main():
    """Run MongoDB integration tests"""
    try:
        test_suite = MongoDBIntegrationTest()
        all_passed = test_suite.run_all_tests()
        
        if all_passed:
            logger.info("🎉 ALL MONGODB TESTS PASSED!")
            logger.info("✅ Schema validators are working correctly")
            logger.info("✅ Field types are correct")
            logger.info("✅ Invalid data is rejected")
            return 0
        else:
            logger.error("⚠️ SOME TESTS FAILED - Check MongoDB schema validators")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

"""
Integration Tests for DetectifAI Database Schema Compliance

Tests all phases of database integration to ensure:
1. Models match MongoDB schema exactly
2. Repositories store data correctly
3. Video service creates schema-compliant records
4. Type conversions work properly
5. No MongoDB validation errors occur
"""

import os
import sys
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database.config import DatabaseManager
from database.repositories import VideoRepository, EventRepository
from database.models import (
    VideoFileModel,
    EventModel,
    convert_numpy_types,
    seconds_to_milliseconds,
    milliseconds_to_seconds,
    prepare_for_mongodb
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseIntegrationTests:
    """Test suite for database integration"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        
        # For testing, we'll use MongoDB directly without MinIO
        # This allows us to test schema compliance without MinIO credentials
        try:
            self.video_repo = VideoRepository(self.db_manager)
            self.event_repo = EventRepository(self.db_manager)
        except Exception as e:
            # If MinIO fails, use database directly for testing
            logger.warning(f"⚠️ MinIO unavailable, using direct DB access: {e}")
            self.video_repo = None
            self.event_repo = None
            self.db = self.db_manager.db
        
        self.test_video_id = "test_video_integration_001"
        self.test_user_id = "test_user_001"
        
    def cleanup_test_data(self):
        """Remove test data from database"""
        try:
            self.db_manager.db.video_file.delete_many({"video_id": self.test_video_id})
            self.db_manager.db.event.delete_many({"video_id": self.test_video_id})
            self.db_manager.db.event_description.delete_many({"event_id": {"$regex": f"^{self.test_video_id}"}})
            logger.info("✅ Test data cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def test_type_conversions(self):
        """Test 1: Type conversion helpers"""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Type Conversion Helpers")
        logger.info("="*60)
        
        try:
            # Test numpy type conversions
            test_data = {
                "int_value": np.int64(42),
                "float_value": np.float32(3.14),
                "array_value": np.array([1, 2, 3, 4]),
                "nested": {
                    "numpy_int": np.int32(100),
                    "numpy_float": np.float64(2.718)
                },
                "list_with_numpy": [np.int64(10), np.float32(20.5)],
                "normal_int": 50,
                "normal_float": 1.5
            }
            
            converted = convert_numpy_types(test_data)
            
            # Verify conversions
            assert isinstance(converted["int_value"], int), "numpy int64 not converted"
            assert isinstance(converted["float_value"], float), "numpy float32 not converted"
            assert isinstance(converted["array_value"], list), "numpy array not converted"
            assert isinstance(converted["nested"]["numpy_int"], int), "nested numpy int not converted"
            assert isinstance(converted["nested"]["numpy_float"], float), "nested numpy float not converted"
            assert all(isinstance(x, (int, float)) for x in converted["list_with_numpy"]), "list items not converted"
            
            logger.info("✅ NumPy type conversions: PASSED")
            
            # Test timestamp conversions
            test_seconds = 10.5
            test_ms = seconds_to_milliseconds(test_seconds)
            assert test_ms == 10500, f"Expected 10500ms, got {test_ms}"
            assert isinstance(test_ms, int), "Milliseconds should be int"
            
            back_to_seconds = milliseconds_to_seconds(test_ms)
            assert abs(back_to_seconds - test_seconds) < 0.001, "Timestamp roundtrip failed"
            
            logger.info("✅ Timestamp conversions: PASSED")
            
            # Test prepare_for_mongodb
            mongo_ready = prepare_for_mongodb(test_data)
            assert isinstance(mongo_ready["int_value"], int), "prepare_for_mongodb failed"
            
            logger.info("✅ prepare_for_mongodb: PASSED")
            logger.info("✅ TEST 1: PASSED - All type conversions working\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 1 FAILED: {e}")
            return False
    
    def test_video_model(self):
        """Test 2: VideoFileModel schema compliance"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: VideoFileModel Schema Compliance")
        logger.info("="*60)
        
        try:
            # Create video model with schema-compliant fields
            video_model = VideoFileModel(
                video_id=self.test_video_id,
                user_id=self.test_user_id,
                file_path=f"videos/{self.test_video_id}.mp4",
                fps=30.0,
                duration_secs=120,
                file_size_bytes=15728640,
                codec="h264",
                meta_data={
                    "processing_status": "testing",
                    "filename": "test_video.mp4",
                    "resolution": "1920x1080",
                    "keyframe_count": 45
                }
            )
            
            # Convert to dict
            video_dict = video_model.to_dict()
            
            # Verify required fields present
            required_fields = ["video_id", "user_id", "file_path"]
            for field in required_fields:
                assert field in video_dict, f"Missing required field: {field}"
            
            # Verify field types
            assert isinstance(video_dict["fps"], float), "fps should be float"
            assert isinstance(video_dict["duration_secs"], int), "duration_secs should be int"
            assert isinstance(video_dict["file_size_bytes"], int), "file_size_bytes should be int"
            assert isinstance(video_dict["meta_data"], dict), "meta_data should be dict"
            
            # Verify no invalid fields
            invalid_fields = ["filename", "resolution", "processing_status", "keyframe_count"]
            for field in invalid_fields:
                assert field not in video_dict or field == "meta_data", f"Invalid top-level field: {field}"
            
            logger.info("✅ VideoFileModel structure: PASSED")
            logger.info("✅ TEST 2: PASSED - VideoFileModel is schema-compliant\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 2 FAILED: {e}")
            return False
    
    def test_event_model(self):
        """Test 3: EventModel schema compliance"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: EventModel Schema Compliance")
        logger.info("="*60)
        
        try:
            # Create event model with schema-compliant fields
            event_model = EventModel(
                event_id=f"{self.test_video_id}_event_001",
                video_id=self.test_video_id,
                start_timestamp_ms=5000,
                end_timestamp_ms=10000,
                event_type="object_detection_fire",
                confidence_score=0.95,
                is_verified=False,
                is_false_positive=False,
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
            
            # Convert to dict
            event_dict = event_model.to_dict()
            
            # Verify required fields
            required_fields = ["event_id", "video_id", "start_timestamp_ms", "end_timestamp_ms"]
            for field in required_fields:
                assert field in event_dict, f"Missing required field: {field}"
            
            # Verify field types
            assert isinstance(event_dict["start_timestamp_ms"], int), "start_timestamp_ms should be int"
            assert isinstance(event_dict["end_timestamp_ms"], int), "end_timestamp_ms should be int"
            assert isinstance(event_dict["confidence_score"], float), "confidence_score should be float"
            assert isinstance(event_dict["bounding_boxes"], dict), "bounding_boxes should be dict"
            
            # Verify no invalid fields (old field names)
            invalid_fields = ["start_timestamp", "end_timestamp", "confidence"]
            for field in invalid_fields:
                assert field not in event_dict, f"Invalid field present: {field}"
            
            logger.info("✅ EventModel structure: PASSED")
            logger.info("✅ TEST 3: PASSED - EventModel is schema-compliant\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 3 FAILED: {e}")
            return False
    
    def test_video_repository_create(self):
        """Test 4: VideoRepository creates schema-compliant records"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: VideoRepository Record Creation")
        logger.info("="*60)
        
        try:
            # Cleanup first
            self.cleanup_test_data()
            
            # Create video record
            video_data = {
                "video_id": self.test_video_id,
                "user_id": self.test_user_id,
                "file_path": f"videos/{self.test_video_id}.mp4",
                "fps": 30.0,
                "duration_secs": 120,
                "file_size_bytes": 15728640,
                "codec": "h264",
                "meta_data": {
                    "processing_status": "testing",
                    "filename": "test_video.mp4",
                    "resolution": "1920x1080"
                }
            }
            
            doc_id = self.video_repo.create_video_record(video_data)
            assert doc_id is not None, "Failed to create video record"
            
            # Retrieve and verify
            retrieved = self.video_repo.get_video_by_id(self.test_video_id)
            assert retrieved is not None, "Failed to retrieve video record"
            
            # Verify schema compliance
            assert retrieved["video_id"] == self.test_video_id
            assert retrieved["user_id"] == self.test_user_id
            assert retrieved["file_path"] == f"videos/{self.test_video_id}.mp4"
            assert isinstance(retrieved["fps"], float)
            assert isinstance(retrieved["duration_secs"], int)
            assert isinstance(retrieved["file_size_bytes"], int)
            assert "meta_data" in retrieved
            assert retrieved["meta_data"]["processing_status"] == "testing"
            
            logger.info("✅ Video record created successfully")
            logger.info("✅ Video record retrieved successfully")
            logger.info("✅ TEST 4: PASSED - VideoRepository working correctly\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 4 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_repository_metadata_update(self):
        """Test 5: VideoRepository metadata updates"""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: VideoRepository Metadata Updates")
        logger.info("="*60)
        
        try:
            # Update metadata
            new_metadata = {
                "processing_status": "completed",
                "processing_progress": 100,
                "keyframe_count": 45,
                "event_count": 3
            }
            
            self.video_repo.update_metadata(self.test_video_id, new_metadata)
            
            # Retrieve and verify
            retrieved = self.video_repo.get_video_by_id(self.test_video_id)
            assert retrieved["meta_data"]["processing_status"] == "completed"
            assert retrieved["meta_data"]["keyframe_count"] == 45
            assert retrieved["meta_data"]["event_count"] == 3
            
            logger.info("✅ Metadata updated successfully")
            logger.info("✅ TEST 5: PASSED - Metadata updates working\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 5 FAILED: {e}")
            return False
    
    def test_event_repository_create(self):
        """Test 6: EventRepository creates schema-compliant events"""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: EventRepository Event Creation")
        logger.info("="*60)
        
        try:
            # Create event with seconds (should be converted to milliseconds)
            event_data = {
                "event_type": "object_detection_fire",
                "start_timestamp": 5.5,  # seconds
                "end_timestamp": 10.2,   # seconds
                "confidence_score": 0.95,
                "bounding_boxes": {
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
                },
                "detected_object_type": "fire"
            }
            
            event_id = self.event_repo.save_event(self.test_video_id, event_data)
            assert event_id is not None, "Failed to create event"
            
            # Retrieve and verify
            events = self.event_repo.get_events_by_video_id(self.test_video_id)
            assert len(events) > 0, "No events retrieved"
            
            event = events[0]
            
            # Verify schema compliance
            assert "event_id" in event
            assert event["video_id"] == self.test_video_id
            assert "start_timestamp_ms" in event
            assert "end_timestamp_ms" in event
            assert isinstance(event["start_timestamp_ms"], int), "start_timestamp_ms should be int"
            assert isinstance(event["end_timestamp_ms"], int), "end_timestamp_ms should be int"
            assert event["start_timestamp_ms"] == 5500, f"Expected 5500ms, got {event['start_timestamp_ms']}"
            assert event["end_timestamp_ms"] == 10200, f"Expected 10200ms, got {event['end_timestamp_ms']}"
            assert "confidence_score" in event
            assert "bounding_boxes" in event
            
            # Verify no invalid fields
            assert "confidence" not in event or "confidence_score" in event, "Should use confidence_score, not confidence"
            assert "start_timestamp" not in event or "start_timestamp_ms" in event, "Should use start_timestamp_ms"
            
            logger.info("✅ Event created successfully")
            logger.info("✅ Timestamps converted to milliseconds")
            logger.info("✅ Event retrieved successfully")
            logger.info("✅ TEST 6: PASSED - EventRepository working correctly\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 6 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_numpy_detection_data(self):
        """Test 7: NumPy detection data handling"""
        logger.info("\n" + "="*60)
        logger.info("TEST 7: NumPy Detection Data Handling")
        logger.info("="*60)
        
        try:
            # Simulate detection data with numpy types (as from OpenCV/YOLO)
            detection_data = {
                "event_type": "object_detection_smoke",
                "start_timestamp": float(np.float32(15.5)),
                "end_timestamp": float(np.float32(18.2)),
                "confidence_score": float(np.float32(0.87)),
                "bounding_boxes": {
                    "detections": [
                        {
                            "x": int(np.int64(200)),
                            "y": int(np.int64(300)),
                            "width": int(np.int64(60)),
                            "height": int(np.int64(90)),
                            "confidence": float(np.float32(0.87)),
                            "class_name": "smoke"
                        }
                    ]
                },
                "detected_object_type": "smoke"
            }
            
            # Apply type conversion
            converted = convert_numpy_types(detection_data)
            
            # Save event
            event_id = self.event_repo.save_event(self.test_video_id, converted)
            assert event_id is not None, "Failed to save event with numpy data"
            
            logger.info("✅ NumPy detection data converted and saved")
            logger.info("✅ TEST 7: PASSED - NumPy data handling working\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 7 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_event_aggregation_structure(self):
        """Test 8: Event aggregation creates proper structure"""
        logger.info("\n" + "="*60)
        logger.info("TEST 8: Event Aggregation Structure")
        logger.info("="*60)
        
        try:
            # Simulate aggregated event with multiple detections
            aggregated_event = {
                "event_type": "object_detection_fire",
                "start_timestamp": 20.0,
                "end_timestamp": 25.0,
                "confidence_score": 0.92,
                "bounding_boxes": {
                    "detections": [
                        {
                            "x": 100,
                            "y": 200,
                            "width": 50,
                            "height": 70,
                            "confidence": 0.92,
                            "class_name": "fire"
                        },
                        {
                            "x": 105,
                            "y": 205,
                            "width": 55,
                            "height": 75,
                            "confidence": 0.89,
                            "class_name": "fire"
                        },
                        {
                            "x": 110,
                            "y": 210,
                            "width": 52,
                            "height": 72,
                            "confidence": 0.94,
                            "class_name": "fire"
                        }
                    ]
                },
                "detected_object_type": "fire"
            }
            
            event_id = self.event_repo.save_event(self.test_video_id, aggregated_event)
            assert event_id is not None, "Failed to save aggregated event"
            
            # Verify structure
            events = self.event_repo.get_events_by_video_id(self.test_video_id)
            fire_events = [e for e in events if e.get("event_type") == "object_detection_fire"]
            
            assert len(fire_events) > 0, "No fire events found"
            
            latest_event = fire_events[-1]
            assert "bounding_boxes" in latest_event
            assert "detections" in latest_event["bounding_boxes"]
            assert len(latest_event["bounding_boxes"]["detections"]) == 3
            
            logger.info("✅ Aggregated event structure correct")
            logger.info("✅ TEST 8: PASSED - Event aggregation structure working\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 8 FAILED: {e}")
            return False
    
    def test_schema_validation(self):
        """Test 9: MongoDB schema validation (no errors)"""
        logger.info("\n" + "="*60)
        logger.info("TEST 9: MongoDB Schema Validation")
        logger.info("="*60)
        
        try:
            # Retrieve all test data
            video = self.video_repo.get_video_by_id(self.test_video_id)
            events = self.event_repo.get_events_by_video_id(self.test_video_id)
            
            # Verify video structure
            video_required = ["video_id", "user_id", "file_path"]
            for field in video_required:
                assert field in video, f"Video missing required field: {field}"
            
            # Verify event structures
            event_required = ["event_id", "video_id", "start_timestamp_ms", "end_timestamp_ms"]
            for event in events:
                for field in event_required:
                    assert field in event, f"Event missing required field: {field}"
            
            logger.info(f"✅ Video record validated: {len(video.keys())} fields")
            logger.info(f"✅ {len(events)} events validated")
            logger.info("✅ TEST 9: PASSED - All records match MongoDB schema\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 9 FAILED: {e}")
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("\n" + "="*80)
        logger.info("🚀 DETECTIFAI DATABASE INTEGRATION TEST SUITE")
        logger.info("="*80 + "\n")
        
        tests = [
            ("Type Conversions", self.test_type_conversions),
            ("VideoFileModel", self.test_video_model),
            ("EventModel", self.test_event_model),
            ("VideoRepository Create", self.test_video_repository_create),
            ("VideoRepository Metadata", self.test_video_repository_metadata_update),
            ("EventRepository Create", self.test_event_repository_create),
            ("NumPy Data Handling", self.test_numpy_detection_data),
            ("Event Aggregation", self.test_event_aggregation_structure),
            ("Schema Validation", self.test_schema_validation)
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, result))
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"❌ Test '{name}' crashed: {e}")
                results.append((name, False))
                failed += 1
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*80)
        
        for name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status}: {name}")
        
        logger.info("\n" + "-"*80)
        logger.info(f"Total Tests: {len(tests)}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"Success Rate: {(passed/len(tests)*100):.1f}%")
        logger.info("="*80 + "\n")
        
        # Cleanup
        self.cleanup_test_data()
        
        return passed == len(tests)


def main():
    """Run integration tests"""
    try:
        test_suite = DatabaseIntegrationTests()
        all_passed = test_suite.run_all_tests()
        
        if all_passed:
            logger.info("🎉 ALL TESTS PASSED - Database integration is working correctly!")
            return 0
        else:
            logger.error("⚠️ SOME TESTS FAILED - Please review the failures above")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

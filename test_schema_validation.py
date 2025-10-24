"""
Simple Database Schema Validation Tests
Tests core database models and schema compliance without requiring MinIO
"""

import os
import sys
import logging
import numpy as np
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database.models import (
    VideoFileModel,
    EventModel,
    convert_numpy_types,
    seconds_to_milliseconds,
    milliseconds_to_seconds,
    prepare_for_mongodb
)
from database.config import DatabaseConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SimpleSchemaTests:
    """Test suite for database schema compliance"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        
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
                "list_with_numpy": [np.int64(10), np.float32(20.5)]
            }
            
            converted = convert_numpy_types(test_data)
            
            # Verify conversions
            assert isinstance(converted["int_value"], int), "numpy int64 not converted"
            assert isinstance(converted["float_value"], float), "numpy float32 not converted"
            assert isinstance(converted["array_value"], list), "numpy array not converted"
            assert isinstance(converted["nested"]["numpy_int"], int), "nested numpy int not converted"
            
            logger.info("✅ NumPy type conversions: PASSED")
            
            # Test timestamp conversions
            test_seconds = 10.5
            test_ms = seconds_to_milliseconds(test_seconds)
            assert test_ms == 10500, f"Expected 10500ms, got {test_ms}"
            assert isinstance(test_ms, int), "Milliseconds should be int"
            
            back_to_seconds = milliseconds_to_seconds(test_ms)
            assert abs(back_to_seconds - test_seconds) < 0.001, "Timestamp roundtrip failed"
            
            logger.info("✅ Timestamp conversions: PASSED")
            logger.info("✅ TEST 1: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 1 FAILED: {e}")
            self.failed += 1
            return False
    
    def test_video_file_model(self):
        """Test 2: VideoFileModel schema compliance"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: VideoFileModel Schema Compliance")
        logger.info("="*60)
        
        try:
            # Create video model with schema-compliant fields
            video_model = VideoFileModel(
                video_id="test_001",
                user_id="user_001",
                file_path="videos/test_001.mp4",
                fps=30.0,
                duration_secs=120,
                file_size_bytes=15728640,
                codec="h264",
                meta_data={
                    "processing_status": "completed",
                    "filename": "test_video.mp4",
                    "resolution": "1920x1080"
                }
            )
            
            # Convert to dict
            video_dict = video_model.to_dict()
            
            # Verify required fields
            required_fields = ["video_id", "user_id", "file_path"]
            for field in required_fields:
                assert field in video_dict, f"Missing required field: {field}"
            
            # Verify field types
            assert isinstance(video_dict["fps"], float), "fps should be float"
            assert isinstance(video_dict["duration_secs"], int), "duration_secs should be int"
            assert isinstance(video_dict["file_size_bytes"], int), "file_size_bytes should be int"
            
            # Verify no invalid top-level fields
            invalid_top_level = ["filename", "resolution", "processing_status", "keyframe_count"]
            for field in invalid_top_level:
                if field in video_dict and field != "meta_data":
                    raise AssertionError(f"Invalid top-level field: {field}")
            
            # Verify meta_data contains extras
            assert "meta_data" in video_dict, "meta_data object missing"
            assert video_dict["meta_data"]["processing_status"] == "completed"
            
            logger.info("✅ All required fields present")
            logger.info("✅ Field types correct")
            logger.info("✅ No invalid top-level fields")
            logger.info("✅ meta_data structure correct")
            logger.info("✅ TEST 2: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 2 FAILED: {e}")
            self.failed += 1
            return False
    
    def test_event_model(self):
        """Test 3: EventModel schema compliance"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: EventModel Schema Compliance")
        logger.info("="*60)
        
        try:
            # Create event model
            event_model = EventModel(
                event_id="evt_001",
                video_id="test_001",
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
            
            # Verify NO old field names
            assert "start_timestamp" not in event_dict, "Old field 'start_timestamp' should not exist"
            assert "end_timestamp" not in event_dict, "Old field 'end_timestamp' should not exist"
            assert "confidence" not in event_dict or "confidence_score" in event_dict, "Should use 'confidence_score'"
            
            # Verify timestamp values are in milliseconds
            assert event_dict["start_timestamp_ms"] == 5000, "Timestamp should be in milliseconds"
            
            logger.info("✅ All required fields present")
            logger.info("✅ Field types correct (timestamps as int)")
            logger.info("✅ No old field names present")
            logger.info("✅ confidence_score (not confidence)")
            logger.info("✅ TEST 3: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 3 FAILED: {e}")
            self.failed += 1
            return False
    
    def test_numpy_detection_simulation(self):
        """Test 4: Simulated detection with numpy types"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: NumPy Detection Data Simulation")
        logger.info("="*60)
        
        try:
            # Simulate OpenCV/YOLO detection output with numpy types
            detection_raw = {
                "bbox": np.array([100.5, 200.3, 150.8, 250.2]),
                "confidence": np.float32(0.95),
                "class_id": np.int32(1),
                "frame_number": np.int64(145),
                "timestamp": np.float64(5.834)
            }
            
            # Convert for MongoDB
            detection_converted = convert_numpy_types(detection_raw)
            
            # Verify all types are Python native
            assert isinstance(detection_converted["bbox"], list), "bbox should be list"
            assert all(isinstance(x, float) for x in detection_converted["bbox"]), "bbox values should be float"
            assert isinstance(detection_converted["confidence"], float), "confidence should be float"
            assert isinstance(detection_converted["class_id"], int), "class_id should be int"
            assert isinstance(detection_converted["frame_number"], int), "frame_number should be int"
            assert isinstance(detection_converted["timestamp"], float), "timestamp should be float"
            
            logger.info("✅ NumPy arrays converted to lists")
            logger.info("✅ NumPy scalars converted to Python types")
            logger.info("✅ TEST 4: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 4 FAILED: {e}")
            self.failed += 1
            return False
    
    def test_event_bounding_boxes_structure(self):
        """Test 5: Event bounding_boxes structure"""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Event Bounding Boxes Structure")
        logger.info("="*60)
        
        try:
            # Create event with multiple bounding boxes (aggregated detections)
            event_data = {
                "event_id": "evt_002",
                "video_id": "test_001",
                "start_timestamp_ms": 15000,
                "end_timestamp_ms": 20000,
                "event_type": "object_detection_fire",
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
                        }
                    ]
                }
            }
            
            # Verify structure
            assert "bounding_boxes" in event_data, "bounding_boxes field missing"
            assert "detections" in event_data["bounding_boxes"], "detections array missing"
            assert len(event_data["bounding_boxes"]["detections"]) == 2, "Should have 2 detections"
            
            # Verify bbox structure
            for bbox in event_data["bounding_boxes"]["detections"]:
                required_bbox_fields = ["x", "y", "width", "height", "confidence", "class_name"]
                for field in required_bbox_fields:
                    assert field in bbox, f"Bbox missing field: {field}"
            
            logger.info("✅ bounding_boxes structure correct")
            logger.info("✅ detections array present")
            logger.info("✅ All bbox fields present (x, y, width, height, confidence, class_name)")
            logger.info("✅ TEST 5: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 5 FAILED: {e}")
            self.failed += 1
            return False
    
    def test_prepare_for_mongodb(self):
        """Test 6: prepare_for_mongodb comprehensive conversion"""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: prepare_for_mongodb() Function")
        logger.info("="*60)
        
        try:
            # Complex nested structure with numpy types
            complex_data = {
                "video_info": {
                    "duration": np.int32(120),
                    "fps": np.float64(30.0),
                    "frames": np.int64(3600)
                },
                "detections": [
                    {
                        "bbox": np.array([10, 20, 30, 40]),
                        "confidence": np.float32(0.95)
                    },
                    {
                        "bbox": np.array([50, 60, 70, 80]),
                        "confidence": np.float32(0.88)
                    }
                ]
            }
            
            prepared = prepare_for_mongodb(complex_data)
            
            # Verify all numpy types converted
            assert isinstance(prepared["video_info"]["duration"], int)
            assert isinstance(prepared["video_info"]["fps"], float)
            assert isinstance(prepared["detections"][0]["bbox"], list)
            assert isinstance(prepared["detections"][0]["confidence"], float)
            
            logger.info("✅ Complex nested structures converted")
            logger.info("✅ All numpy types converted to Python types")
            logger.info("✅ TEST 6: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 6 FAILED: {e}")
            self.failed += 1
            return False
    
    def test_timestamp_edge_cases(self):
        """Test 7: Timestamp conversion edge cases"""
        logger.info("\n" + "="*60)
        logger.info("TEST 7: Timestamp Edge Cases")
        logger.info("="*60)
        
        try:
            # Test various timestamp values
            test_cases = [
                (0.0, 0),
                (1.0, 1000),
                (0.001, 1),
                (10.5, 10500),
                (60.0, 60000),
                (123.456, 123456)
            ]
            
            for seconds, expected_ms in test_cases:
                result = seconds_to_milliseconds(seconds)
                assert result == expected_ms, f"Failed for {seconds}s: expected {expected_ms}ms, got {result}ms"
                assert isinstance(result, int), f"Result should be int, got {type(result)}"
            
            # Test roundtrip
            for seconds, _ in test_cases:
                ms = seconds_to_milliseconds(seconds)
                back = milliseconds_to_seconds(ms)
                # Allow small floating point error
                assert abs(back - seconds) < 0.001, f"Roundtrip failed for {seconds}s"
            
            logger.info("✅ All timestamp conversions correct")
            logger.info("✅ Roundtrip conversions accurate")
            logger.info("✅ TEST 7: PASSED\n")
            self.passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST 7 FAILED: {e}")
            self.failed += 1
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "="*80)
        logger.info("🚀 DETECTIFAI DATABASE SCHEMA VALIDATION TESTS")
        logger.info("="*80)
        
        tests = [
            self.test_type_conversions,
            self.test_video_file_model,
            self.test_event_model,
            self.test_numpy_detection_simulation,
            self.test_event_bounding_boxes_structure,
            self.test_prepare_for_mongodb,
            self.test_timestamp_edge_cases
        ]
        
        for test_func in tests:
            test_func()
        
        # Print summary
        total = self.passed + self.failed
        logger.info("\n" + "="*80)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {self.passed}")
        logger.info(f"❌ Failed: {self.failed}")
        logger.info(f"Success Rate: {(self.passed/total*100):.1f}%")
        logger.info("="*80 + "\n")
        
        return self.failed == 0


def main():
    """Run tests"""
    try:
        logger.info("Starting schema validation tests...")
        logger.info("These tests validate models and type conversions without requiring MongoDB connection\n")
        
        test_suite = SimpleSchemaTests()
        all_passed = test_suite.run_all_tests()
        
        if all_passed:
            logger.info("🎉 ALL TESTS PASSED - Models and type conversions are correct!")
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

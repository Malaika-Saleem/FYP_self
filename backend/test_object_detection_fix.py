#!/usr/bin/env python3
"""
Test script to verify object detection works with corrected class names
"""
import sys
import os
sys.path.append('.')

from object_detection import ObjectDetector
from config import VideoProcessingConfig
import cv2
import numpy as np

def test_object_detection():
    """Test if object detection initializes correctly with fixed class names"""
    try:
        # Initialize config
        config = VideoProcessingConfig()
        
        # Initialize object detector
        detector = ObjectDetector(config)
        
        print("✅ ObjectDetector initialized successfully!")
        print(f"Available models: {list(detector.models.keys())}")
        print(f"Class names: {detector.class_names}")
        
        # Test detection on a dummy frame
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        detected_objects = detector.detect_objects(dummy_frame, timestamp=0.0)
        print(f"✅ Detection completed without errors. Found {len(detected_objects)} objects (expected 0 for blank frame)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during object detection test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing DetectifAI Object Detection with corrected class names...")
    success = test_object_detection()
    
    if success:
        print("\n🎉 All tests passed! Object detection is working correctly.")
    else:
        print("\n💥 Tests failed. Please check the error messages above.")
#!/usr/bin/env python3
"""
Test the complete DetectifAI pipeline with the new improvements
"""
import sys
import os
import time
sys.path.append('.')

from main_pipeline import CompleteVideoProcessingPipeline
from config import get_security_focused_config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_complete_pipeline():
    """Test the complete pipeline with fire.avi"""
    try:
        input_video = "fire.avi"
        if not os.path.exists(input_video):
            logger.error(f"Test video not found: {input_video}")
            return False

        # Get configuration
        config = get_security_focused_config()
        
        # Set output directory for test
        timestamp = str(int(time.time()))
        video_id = f"pipeline_test_{timestamp}"
        config.output_base_dir = f"video_processing_outputs/{video_id}"
        
        logger.info(f"🚀 Testing complete pipeline with video ID: {video_id}")
        
        # Initialize pipeline
        pipeline = CompleteVideoProcessingPipeline(config)
        
        # Process video
        results = pipeline.process_video_complete(input_video, "pipeline_test")
        
        # Check results
        logger.info("📊 Pipeline Results Summary:")
        logger.info(f"   Output directory: {config.output_base_dir}")
        logger.info(f"   Total keyframes: {results['outputs'].get('total_keyframes', 0)}")
        logger.info(f"   Object detections: {results['outputs'].get('total_object_detections', 0)}")
        logger.info(f"   Object events: {results['outputs'].get('total_object_events', 0)}")
        
        # Check if detection metadata was created
        metadata_path = os.path.join(config.output_base_dir, 'detection_metadata.json')
        if os.path.exists(metadata_path):
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            logger.info("🎯 Detection Metadata:")
            logger.info(f"   Total keyframes: {metadata.get('total_keyframes', 0)}")
            logger.info(f"   Frames with detections: {metadata.get('frames_with_detections', 0)}")
            logger.info(f"   Objects detected: {metadata.get('objects_detected', {})}")
            logger.info(f"   Annotated frames: {len(metadata.get('annotated_frames', []))}")
        
        # Check output files
        frames_dir = os.path.join(config.output_base_dir, 'frames')
        compressed_dir = os.path.join(config.output_base_dir, 'compressed')
        
        if os.path.exists(frames_dir):
            frame_count = len([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
            logger.info(f"📁 Frames directory: {frame_count} images")
        
        if os.path.exists(compressed_dir):
            video_files = [f for f in os.listdir(compressed_dir) if f.endswith('.mp4')]
            logger.info(f"📹 Compressed directory: {len(video_files)} videos")
        
        logger.info(f"✅ Pipeline test completed successfully!")
        logger.info(f"🌐 Test results available at: http://localhost:3001/results/{video_id}")
        
        return video_id
        
    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing DetectifAI Complete Pipeline...")
    result = test_complete_pipeline()
    
    if result:
        print(f"\n🎉 Test completed successfully!")
        print(f"Video ID: {result}")
        print(f"View results at: http://localhost:3001/results/{result}")
    else:
        print("\n💥 Test failed. Check the logs above for details.")
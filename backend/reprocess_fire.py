#!/usr/bin/env python3
"""
Reprocess fire.avi with corrected class names to generate new results
"""
import sys
import os
sys.path.append('.')

from main_pipeline import CompleteVideoProcessingPipeline
from config import get_security_focused_config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reprocess_fire_video():
    """Reprocess fire.avi with corrected class names"""
    try:
        # Input video path
        input_video = "fire.avi"
        
        if not os.path.exists(input_video):
            logger.error(f"Video file not found: {input_video}")
            return False
        
        # Get configuration
        config = get_security_focused_config()
        
        # Initialize pipeline
        logger.info("Initializing DetectifAI pipeline...")
        pipeline = CompleteVideoProcessingPipeline(config)
        
        # Process video
        logger.info(f"Processing {input_video} with corrected fire/smoke detection...")
        results = pipeline.process_video_complete(
            video_path=input_video,
            output_name="fire_reprocessed_" + str(int(time.time()))
        )
        
        if results and 'input_video' in results:
            logger.info(f"✅ Video reprocessed successfully!")
            logger.info(f"Input video: {results.get('input_video', 'N/A')}")
            logger.info(f"Output name: {results.get('output_name', 'N/A')}")
            logger.info(f"Processing stats: {results.get('processing_stats', {})}")
            return True
        else:
            logger.error(f"❌ Processing failed: Invalid results format")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error reprocessing video: {str(e)}")
        return False

if __name__ == "__main__":
    import time
    
    print("🔥 Reprocessing fire.avi with corrected fire/smoke detection...")
    success = reprocess_fire_video()
    
    if success:
        print("\n🎉 Fire.avi reprocessed successfully with correct labels!")
        print("Check the video_processing_outputs directory for new results.")
    else:
        print("\n💥 Reprocessing failed. Check the logs above for details.")
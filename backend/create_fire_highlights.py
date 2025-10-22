#!/usr/bin/env python3
"""
Create a highlight video showing fire detection moments using existing annotated keyframes
"""
import sys
import os
import cv2
import numpy as np
import json
sys.path.append('.')

import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_fire_highlight_video():
    """Create a highlight video from existing fire detection keyframes"""
    try:
        # Use the latest fire reprocessed video ID
        video_id = "fire_reprocessed_1760285107"
        video_dir = f"video_processing_outputs/{video_id}"
        frames_dir = f"{video_dir}/frames"
        
        if not os.path.exists(frames_dir):
            logger.error(f"Frames directory not found: {frames_dir}")
            return False
            
        # Get all keyframe files
        keyframe_files = []
        for filename in sorted(os.listdir(frames_dir)):
            if filename.endswith('.jpg'):
                keyframe_files.append(os.path.join(frames_dir, filename))
        
        if not keyframe_files:
            logger.error("No keyframes found")
            return False
            
        logger.info(f"Found {len(keyframe_files)} annotated keyframes")
        
        # Read first frame to get dimensions
        first_frame = cv2.imread(keyframe_files[0])
        if first_frame is None:
            logger.error("Cannot read first keyframe")
            return False
            
        height, width = first_frame.shape[:2]
        fps = 2  # 2 seconds per keyframe for better viewing
        
        # Create timestamp for unique video ID
        timestamp = str(int(time.time()))
        video_id_new = f"fire_highlights_{timestamp}"
        
        # Create output directories
        output_dir = f"video_processing_outputs/{video_id_new}"
        os.makedirs(f"{output_dir}/compressed", exist_ok=True)
        os.makedirs(f"{output_dir}/frames", exist_ok=True)
        
        # Output video path
        output_path = f"{output_dir}/compressed/{video_id_new}_compressed.mp4"
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            logger.error("Cannot create video writer")
            return False
        
        logger.info(f"🎬 Creating fire highlights video: {width}x{height} at {fps} FPS")
        
        # Add each keyframe to the video (hold each frame for 1 second)
        for i, keyframe_path in enumerate(keyframe_files):
            frame = cv2.imread(keyframe_path)
            if frame is None:
                logger.warning(f"Cannot read keyframe: {keyframe_path}")
                continue
                
            # Resize if necessary
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            
            # Add frame multiple times to hold it for duration
            hold_frames = fps  # Hold each keyframe for 1 second
            for _ in range(hold_frames):
                out.write(frame)
            
            # Copy keyframe to new directory for frontend display
            keyframe_filename = f"keyframe_{i*2:.2f}s_frame_{i}.jpg"
            keyframe_dest = f"{output_dir}/frames/{keyframe_filename}"
            cv2.imwrite(keyframe_dest, frame)
            
            logger.info(f"Added keyframe {i+1}/{len(keyframe_files)}: {os.path.basename(keyframe_path)}")
        
        # Release video writer
        out.release()
        
        # Verify output file
        if not os.path.exists(output_path):
            logger.error("Output video was not created")
            return False
            
        file_size = os.path.getsize(output_path)
        logger.info(f"✅ Fire highlights video created: {output_path} ({file_size} bytes)")
        
        # Add title frame at the beginning
        create_title_frame(output_dir, width, height)
        
        logger.info(f"🌐 Frontend URL: http://localhost:3000/results/{video_id_new}")
        
        return video_id_new
        
    except Exception as e:
        logger.error(f"❌ Error creating fire highlights video: {str(e)}")
        return False

def create_title_frame(output_dir, width, height):
    """Create a title frame for the highlight video"""
    try:
        # Create black frame
        title_frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add title text
        title_text = "DetectifAI Fire Detection Highlights"
        subtitle_text = "Corrected Fire/Smoke Classification"
        
        # Calculate text position for centering
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = min(width, height) / 800  # Scale based on video size
        thickness = max(1, int(font_scale * 2))
        
        # Get text sizes
        title_size = cv2.getTextSize(title_text, font, font_scale, thickness)[0]
        subtitle_size = cv2.getTextSize(subtitle_text, font, font_scale * 0.7, thickness)[0]
        
        # Calculate positions
        title_x = (width - title_size[0]) // 2
        title_y = (height - title_size[1]) // 2 - 30
        
        subtitle_x = (width - subtitle_size[0]) // 2
        subtitle_y = title_y + title_size[1] + 40
        
        # Draw text
        cv2.putText(title_frame, title_text, (title_x, title_y), 
                   font, font_scale, (0, 0, 255), thickness)  # Red color
        cv2.putText(title_frame, subtitle_text, (subtitle_x, subtitle_y), 
                   font, font_scale * 0.7, (255, 255, 255), thickness)  # White color
        
        # Save title frame
        title_path = f"{output_dir}/frames/title_frame.jpg"
        cv2.imwrite(title_path, title_frame)
        
        logger.info("Title frame created")
        
    except Exception as e:
        logger.warning(f"Could not create title frame: {str(e)}")

if __name__ == "__main__":
    print("🎥 Creating fire detection highlights from annotated keyframes...")
    result = create_fire_highlight_video()
    
    if result:
        print(f"\n🎉 Fire highlights video created successfully!")
        print(f"Video ID: {result}")
        print(f"View at: http://localhost:3000/results/{result}")
        print("\n💡 This video shows the key fire detection moments with correct labels!")
    else:
        print("\n💥 Failed to create highlights video. Check the logs above for details.")
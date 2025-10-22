#!/usr/bin/env python3
"""
Create an annotated video with corrected fire detection labels
"""
import sys
import os
import cv2
import numpy as np
sys.path.append('.')

from object_detection import ObjectDetector
from config import get_security_focused_config
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_annotated_fire_video():
    """Create an annotated version of fire.avi with correct fire detection labels"""
    try:
        input_video = "fire.avi"
        if not os.path.exists(input_video):
            logger.error(f"Video file not found: {input_video}")
            return False

        # Get configuration and initialize detector
        config = get_security_focused_config()
        detector = ObjectDetector(config)
        
        # Open input video
        cap = cv2.VideoCapture(input_video)
        if not cap.isOpened():
            logger.error(f"Cannot open video file: {input_video}")
            return False
            
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Video properties: {width}x{height}, {fps} FPS, {total_frames} frames")
        
        # Create output video writer
        timestamp = str(int(time.time()))
        output_path = f"video_processing_outputs/compressed/fire_annotated_{timestamp}_compressed.mp4"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        logger.info("🎬 Processing frames with fire detection...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Calculate timestamp
            timestamp = frame_count / fps
            
            # Save frame temporarily for detection
            temp_frame_path = f"temp_frame_{frame_count}.jpg"
            cv2.imwrite(temp_frame_path, frame)
            
            try:
                # Run object detection on frame
                detection_result = detector.detect_objects_in_frame(temp_frame_path, timestamp)
                
                # Annotate frame if objects detected
                if detection_result.detected_objects:
                    annotated_frame = frame.copy()
                    
                    for obj in detection_result.detected_objects:
                        x1, y1, x2, y2 = obj.bbox
                        
                        # Choose color based on object class
                        color_map = {
                            'fire': (0, 0, 255),      # Red
                            'smoke': (128, 128, 128), # Gray
                            'knife': (0, 165, 255),   # Orange
                            'gun': (0, 0, 139)        # Dark Red
                        }
                        color = color_map.get(obj.class_name, (255, 255, 255))
                        
                        # Draw bounding box
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                        
                        # Draw label with confidence
                        label = f"{obj.class_name}: {obj.confidence:.2f}"
                        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        
                        # Draw label background
                        cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                     (x1 + label_size[0], y1), color, -1)
                        
                        # Draw label text
                        cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    frame = annotated_frame
                    logger.info(f"🔥 Frame {frame_count}: Detected {len(detection_result.detected_objects)} objects")
                
                # Write frame to output video
                out.write(frame)
                
                # Progress update
                if frame_count % 30 == 0:  # Every second at 30fps
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
                    
            finally:
                # Clean up temp frame
                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)
                    
            frame_count += 1
        
        # Release resources
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        logger.info(f"✅ Annotated video created: {output_path}")
        
        # Create proper directory structure
        video_id = f"fire_annotated_{timestamp}"
        video_dir = f"video_processing_outputs/{video_id}"
        os.makedirs(f"{video_dir}/compressed", exist_ok=True)
        os.makedirs(f"{video_dir}/frames", exist_ok=True)
        
        # Move video to proper location
        final_path = f"{video_dir}/compressed/{video_id}_compressed.mp4"
        os.rename(output_path, final_path)
        
        logger.info(f"✅ Video available at: {final_path}")
        logger.info(f"🌐 Frontend URL: http://localhost:3000/results/{video_id}")
        
        return video_id
        
    except Exception as e:
        logger.error(f"❌ Error creating annotated video: {str(e)}")
        return False

if __name__ == "__main__":
    print("🎨 Creating annotated fire.avi with corrected detection labels...")
    result = create_annotated_fire_video()
    
    if result:
        print(f"\n🎉 Annotated video created successfully!")
        print(f"Video ID: {result}")
        print(f"View at: http://localhost:3000/results/{result}")
    else:
        print("\n💥 Failed to create annotated video. Check the logs above for details.")
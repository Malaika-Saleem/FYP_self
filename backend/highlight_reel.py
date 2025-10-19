"""
Highlight Reel Generation Module

This module creates video summaries and highlight reels using various strategies:
- Event-aware summarization
- Ultra-comprehensive coverage
- Quality-focused highlights
- Motion-based highlights
"""

import cv2
import os
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class HighlightReelGenerator:
    """Generate highlight reels from processed video segments"""
    
    def __init__(self, config):
        self.config = config
        self.highlights_dir = os.path.join(config.output_base_dir, "highlights")
        os.makedirs(self.highlights_dir, exist_ok=True)
    
    def create_event_aware_highlight_reel(self, segments: List, canonical_events: List = None) -> str:
        """
        Create highlight reel focusing on detected events
        
        Args:
            segments: List of video segments
            canonical_events: List of canonical events (optional)
            
        Returns:
            Path to generated highlight reel
        """
        logger.info("Creating event-aware highlight reel")
        
        output_path = os.path.join(self.highlights_dir, "event_aware_highlights.mp4")
        
        # Detect event segments
        event_segments = self._detect_event_segments(segments)
        
        # Select keyframes with event priority
        selected_keyframes = self._select_event_aware_keyframes(
            segments, event_segments, canonical_events
        )
        
        # Create video
        success = self._create_highlight_video(
            selected_keyframes, 
            output_path,
            "Event-Aware Highlights"
        )
        
        if success:
            logger.info(f"Event-aware highlight reel created: {output_path}")
            return output_path
        else:
            logger.error("Failed to create event-aware highlight reel")
            return ""
    
    def create_ultra_comprehensive_highlight_reel(self, segments: List) -> str:
        """
        Create comprehensive highlight reel capturing maximum important moments
        
        Args:
            segments: List of video segments
            
        Returns:
            Path to generated highlight reel
        """
        logger.info("Creating ultra-comprehensive highlight reel")
        
        output_path = os.path.join(self.highlights_dir, "ultra_comprehensive_highlights.mp4")
        
        # Use ultra-sensitive selection
        selected_keyframes = self._select_ultra_comprehensive_keyframes(segments)
        
        # Create video
        success = self._create_highlight_video(
            selected_keyframes,
            output_path,
            "Ultra-Comprehensive Highlights"
        )
        
        if success:
            logger.info(f"Ultra-comprehensive highlight reel created: {output_path}")
            return output_path
        else:
            logger.error("Failed to create ultra-comprehensive highlight reel")
            return ""
    
    def create_quality_focused_highlight_reel(self, segments: List) -> str:
        """
        Create highlight reel focusing on highest quality frames
        
        Args:
            segments: List of video segments
            
        Returns:
            Path to generated highlight reel
        """
        logger.info("Creating quality-focused highlight reel")
        
        output_path = os.path.join(self.highlights_dir, "quality_focused_highlights.mp4")
        
        # Select highest quality keyframes
        selected_keyframes = self._select_quality_focused_keyframes(segments)
        
        # Create video
        success = self._create_highlight_video(
            selected_keyframes,
            output_path,
            "Quality-Focused Highlights"
        )
        
        if success:
            logger.info(f"Quality-focused highlight reel created: {output_path}")
            return output_path
        else:
            logger.error("Failed to create quality-focused highlight reel")
            return ""
    
    def _detect_event_segments(self, segments: List) -> List[int]:
        """Detect which segments contain significant events"""
        event_segments = []
        
        for segment in segments:
            keyframes = segment.get('keyframes', [])
            if not keyframes:
                continue
            
            # Calculate segment activity metrics
            motion_scores = [kf['frame_data']['motion_score'] for kf in keyframes]
            burst_count = sum(1 for kf in keyframes if kf['frame_data']['burst_active'])
            max_motion = max(motion_scores) if motion_scores else 0
            avg_motion = sum(motion_scores) / len(motion_scores) if motion_scores else 0
            
            # Event detection criteria
            is_event_segment = (
                max_motion > self.config.motion_threshold or
                avg_motion > self.config.motion_threshold * 0.5 or
                burst_count >= 1
            )
            
            if is_event_segment:
                segment_id = segment.get('segment_id', len(event_segments))
                event_segments.append(segment_id)
        
        return event_segments
    
    def _select_event_aware_keyframes(self, segments: List, event_segments: List[int], 
                                    canonical_events: List = None) -> List[Dict]:
        """Select keyframes with event awareness"""
        selected_keyframes = []
        
        for segment in segments:
            keyframes = segment.get('keyframes', [])
            if not keyframes:
                continue
                
            segment_id = segment.get('segment_id', 0)
            
            if segment_id in event_segments:
                # Event segment: select multiple keyframes
                scored_keyframes = []
                
                for kf in keyframes:
                    frame_data = kf['frame_data']
                    base_score = kf['keyframe_score']
                    motion_score = frame_data['motion_score']
                    is_burst = frame_data['burst_active']
                    
                    # Event-aware scoring
                    event_score = base_score
                    if motion_score > self.config.motion_threshold:
                        event_score += motion_score * 0.5
                    if is_burst:
                        event_score *= self.config.burst_weight
                    
                    scored_keyframes.append({
                        'keyframe_data': kf,
                        'event_score': event_score,
                        'timestamp': frame_data['timestamp'],
                        'is_event': True,
                        'segment_id': segment_id
                    })
                
                # Select top keyframes from event segment
                scored_keyframes.sort(key=lambda x: x['event_score'], reverse=True)
                num_select = min(3, max(2, len([kf for kf in keyframes if kf['frame_data']['burst_active']])))
                selected_keyframes.extend(scored_keyframes[:num_select])
                
            else:
                # Regular segment: select best keyframe
                best_kf = max(keyframes, key=lambda x: x['keyframe_score'])
                if best_kf['keyframe_score'] >= self.config.base_quality_threshold:
                    selected_keyframes.append({
                        'keyframe_data': best_kf,
                        'event_score': best_kf['keyframe_score'],
                        'timestamp': best_kf['frame_data']['timestamp'],
                        'is_event': False,
                        'segment_id': segment_id
                    })
        
        # Sort by timestamp and limit
        selected_keyframes.sort(key=lambda x: x['timestamp'])
        
        if len(selected_keyframes) > self.config.max_summary_frames:
            # Prioritize by event score
            selected_keyframes.sort(key=lambda x: x['event_score'], reverse=True)
            selected_keyframes = selected_keyframes[:self.config.max_summary_frames]
            selected_keyframes.sort(key=lambda x: x['timestamp'])
        
        return selected_keyframes
    
    def _select_ultra_comprehensive_keyframes(self, segments: List) -> List[Dict]:
        """Select keyframes with ultra-comprehensive coverage"""
        all_important_frames = []
        
        # Ultra-low thresholds for comprehensive coverage
        ultra_motion_threshold = self.config.motion_threshold * 0.5
        ultra_quality_threshold = self.config.base_quality_threshold * 0.8
        
        for segment in segments:
            keyframes = segment.get('keyframes', [])
            segment_id = segment.get('segment_id', 0)
            
            for kf in keyframes:
                frame_data = kf['frame_data']
                base_score = kf['keyframe_score']
                motion_score = frame_data['motion_score']
                is_burst = frame_data['burst_active']
                timestamp = frame_data['timestamp']
                
                # Ultra-comprehensive scoring
                importance = base_score
                
                # Any motion is important
                if motion_score > ultra_motion_threshold:
                    importance += motion_score * 1.0
                elif motion_score > 0:
                    importance += motion_score * 0.5
                
                # Burst frames are critical
                if is_burst:
                    importance *= 3.0
                
                # Quality bonus
                if base_score > self.config.base_quality_threshold * 1.1:
                    importance += 0.1
                
                # Include frame if it meets any importance criteria
                include_frame = (
                    importance > 0.20 or
                    motion_score > ultra_motion_threshold or
                    is_burst or
                    base_score > ultra_quality_threshold
                )
                
                if include_frame:
                    all_important_frames.append({
                        'keyframe_data': kf,
                        'importance_score': importance,
                        'motion_score': motion_score,
                        'is_burst': is_burst,
                        'timestamp': timestamp,
                        'segment_id': segment_id
                    })
        
        # Sort by importance and ensure temporal diversity
        all_important_frames.sort(key=lambda x: x['importance_score'], reverse=True)
        
        selected_frames = []
        covered_timeframes = set()
        
        for frame in all_important_frames:
            timestamp = frame['timestamp']
            timeframe = int(timestamp // 5) * 5  # 5-second bins
            
            if timeframe not in covered_timeframes or len(selected_frames) < self.config.max_summary_frames:
                selected_frames.append({
                    'keyframe_data': frame['keyframe_data'],
                    'event_score': frame['importance_score'],
                    'timestamp': timestamp,
                    'is_event': frame['is_burst'] or frame['motion_score'] > self.config.motion_threshold,
                    'segment_id': frame['segment_id']
                })
                covered_timeframes.add(timeframe)
                
                if len(selected_frames) >= self.config.max_summary_frames:
                    break
        
        # Sort by timestamp
        selected_frames.sort(key=lambda x: x['timestamp'])
        return selected_frames
    
    def _select_quality_focused_keyframes(self, segments: List) -> List[Dict]:
        """Select keyframes focusing on quality"""
        all_quality_frames = []
        
        for segment in segments:
            keyframes = segment.get('keyframes', [])
            segment_id = segment.get('segment_id', 0)
            
            for kf in keyframes:
                frame_data = kf['frame_data']
                quality_score = frame_data['quality_score']
                
                # Only include high-quality frames
                if quality_score >= self.config.base_quality_threshold * 1.2:
                    all_quality_frames.append({
                        'keyframe_data': kf,
                        'event_score': quality_score,
                        'timestamp': frame_data['timestamp'],
                        'is_event': False,
                        'segment_id': segment_id
                    })
        
        # Sort by quality score and limit
        all_quality_frames.sort(key=lambda x: x['event_score'], reverse=True)
        
        # Ensure temporal diversity
        selected_frames = []
        last_timestamp = -float('inf')
        min_gap = 3.0  # Minimum 3 seconds between frames
        
        for frame in all_quality_frames:
            if frame['timestamp'] - last_timestamp >= min_gap:
                selected_frames.append(frame)
                last_timestamp = frame['timestamp']
                
                if len(selected_frames) >= self.config.max_summary_frames:
                    break
        
        # Sort by timestamp
        selected_frames.sort(key=lambda x: x['timestamp'])
        return selected_frames
    
    def _create_highlight_video(self, selected_keyframes: List[Dict], output_path: str, 
                              title: str = "Highlight Reel") -> bool:
        """Create highlight video from selected keyframes"""
        if not selected_keyframes:
            logger.error("No keyframes selected for highlight reel")
            return False
        
        try:
            # Read first frame to get dimensions
            first_frame_path = selected_keyframes[0]['keyframe_data']['frame_data']['frame_path']
            first_image = cv2.imread(first_frame_path)
            
            if first_image is None:
                logger.error(f"Cannot read first frame: {first_frame_path}")
                return False
            
            height, width = first_image.shape[:2]
            
            # Set up video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = self.config.summary_fps
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error("Cannot create video writer")
                return False
            
            # Add frames to video
            frames_added = 0
            logger.info(f"Creating {title} with {len(selected_keyframes)} frames")
            
            for kf in selected_keyframes:
                frame_path = kf['keyframe_data']['frame_data']['frame_path']
                
                if os.path.exists(frame_path):
                    frame = cv2.imread(frame_path)
                    if frame is not None:
                        # Resize frame if needed
                        if frame.shape[:2] != (height, width):
                            frame = cv2.resize(frame, (width, height))
                        
                        out.write(frame)
                        frames_added += 1
                        
                        # Log frame info
                        timestamp = kf['timestamp']
                        mins = int(timestamp // 60)
                        secs = timestamp % 60
                        event_type = "EVENT" if kf['is_event'] else "QUALITY"
                        logger.debug(f"Added frame: {mins:02d}:{secs:04.1f} - {event_type}")
                    else:
                        logger.warning(f"Cannot read frame: {frame_path}")
                else:
                    logger.warning(f"Frame not found: {frame_path}")
            
            out.release()
            
            # Verify output
            if frames_added > 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024*1024)
                duration = frames_added / fps
                
                logger.info(f"✅ {title} created successfully!")
                logger.info(f"📁 Path: {output_path}")
                logger.info(f"📊 {frames_added} frames, {duration:.1f}s duration, {file_size:.1f} MB")
                
                return True
            else:
                logger.error("Failed to create video file")
                return False
                
        except Exception as e:
            logger.error(f"Error creating highlight video: {e}")
            return False
    
    def create_custom_highlight_reel(self, segments: List, selection_criteria: Dict[str, Any]) -> str:
        """
        Create custom highlight reel based on specific criteria
        
        Args:
            segments: List of video segments
            selection_criteria: Custom criteria for frame selection
            
        Returns:
            Path to generated highlight reel
        """
        logger.info(f"Creating custom highlight reel with criteria: {selection_criteria}")
        
        output_path = os.path.join(self.highlights_dir, "custom_highlights.mp4")
        
        # Apply custom selection
        selected_keyframes = self._apply_custom_selection(segments, selection_criteria)
        
        # Create video
        success = self._create_highlight_video(
            selected_keyframes,
            output_path,
            "Custom Highlights"
        )
        
        if success:
            logger.info(f"Custom highlight reel created: {output_path}")
            return output_path
        else:
            logger.error("Failed to create custom highlight reel")
            return ""
    
    def _apply_custom_selection(self, segments: List, criteria: Dict[str, Any]) -> List[Dict]:
        """Apply custom selection criteria"""
        selected_keyframes = []
        
        # Extract criteria
        min_motion = criteria.get('min_motion_score', 0.0)
        min_quality = criteria.get('min_quality_score', self.config.base_quality_threshold)
        require_burst = criteria.get('require_burst', False)
        max_frames = criteria.get('max_frames', self.config.max_summary_frames)
        time_range = criteria.get('time_range', None)  # (start, end) tuple
        
        for segment in segments:
            keyframes = segment.get('keyframes', [])
            
            for kf in keyframes:
                frame_data = kf['frame_data']
                timestamp = frame_data['timestamp']
                motion_score = frame_data['motion_score']
                quality_score = frame_data['quality_score']
                is_burst = frame_data['burst_active']
                
                # Apply criteria
                meets_criteria = True
                
                if motion_score < min_motion:
                    meets_criteria = False
                
                if quality_score < min_quality:
                    meets_criteria = False
                
                if require_burst and not is_burst:
                    meets_criteria = False
                
                if time_range:
                    start_time, end_time = time_range
                    if not (start_time <= timestamp <= end_time):
                        meets_criteria = False
                
                if meets_criteria:
                    selected_keyframes.append({
                        'keyframe_data': kf,
                        'event_score': kf['keyframe_score'],
                        'timestamp': timestamp,
                        'is_event': is_burst or motion_score > self.config.motion_threshold,
                        'segment_id': segment.get('segment_id', 0)
                    })
        
        # Sort and limit
        selected_keyframes.sort(key=lambda x: x['event_score'], reverse=True)
        selected_keyframes = selected_keyframes[:max_frames]
        selected_keyframes.sort(key=lambda x: x['timestamp'])
        
        return selected_keyframes
    
    def generate_highlight_reel_metadata(self, selected_keyframes: List[Dict], 
                                       output_path: str) -> bool:
        """Generate metadata file for highlight reel"""
        try:
            metadata = {
                'generation_info': {
                    'timestamp': datetime.now().isoformat(),
                    'total_frames': len(selected_keyframes),
                    'selection_config': {
                        'max_summary_frames': self.config.max_summary_frames,
                        'summary_fps': self.config.summary_fps,
                        'motion_threshold': self.config.motion_threshold,
                        'quality_threshold': self.config.base_quality_threshold
                    }
                },
                'frame_details': []
            }
            
            for i, kf in enumerate(selected_keyframes):
                frame_detail = {
                    'sequence_number': i + 1,
                    'timestamp': kf['timestamp'],
                    'is_event_frame': kf['is_event'],
                    'segment_id': kf['segment_id'],
                    'event_score': kf['event_score'],
                    'frame_path': kf['keyframe_data']['frame_data']['frame_path']
                }
                metadata['frame_details'].append(frame_detail)
            
            with open(output_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Highlight reel metadata saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save highlight reel metadata: {e}")
            return False
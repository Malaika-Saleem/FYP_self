"""
Video Segmentation Module

This module handles:
- Temporal video segmentation
- Segment-wise keyframe extraction
- Segment metadata generation
- Segment-based event detection
"""

import os
import json
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class VideoSegment:
    """Represents a temporal video segment"""
    segment_id: int
    start_timestamp: float
    end_timestamp: float
    duration: float
    start_frame: int
    end_frame: int
    keyframes: List[Dict[str, Any]]
    segment_type: str
    activity_level: str
    motion_statistics: Dict[str, float]
    quality_statistics: Dict[str, float]

class VideoSegmentationEngine:
    """Handle video segmentation and segment analysis"""
    
    def __init__(self, config):
        self.config = config
        self.segments_dir = os.path.join(config.output_base_dir, "segments")
        os.makedirs(self.segments_dir, exist_ok=True)
        
    def create_video_segments(self, video_path: str, keyframes: List) -> List[VideoSegment]:
        """
        Create temporal segments from video and associated keyframes
        
        Args:
            video_path: Path to source video
            keyframes: List of extracted keyframes
            
        Returns:
            List of VideoSegment objects
        """
        logger.info(f"Creating video segments from: {video_path}")
        
        # Get video properties
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        cap.release()
        
        logger.info(f"Video duration: {duration:.2f}s, FPS: {fps:.2f}")
        
        # Create temporal segments
        segments = []
        segment_duration = self.config.segment_duration
        num_segments = int(np.ceil(duration / segment_duration))
        
        logger.info(f"Creating {num_segments} segments of {segment_duration}s each")
        
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration)
            
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            # Find keyframes in this segment
            segment_keyframes = self._get_keyframes_in_segment(
                keyframes, start_time, end_time
            )
            
            # Analyze segment
            segment_analysis = self._analyze_segment(segment_keyframes)
            
            segment = VideoSegment(
                segment_id=i,
                start_timestamp=start_time,
                end_timestamp=end_time,
                duration=end_time - start_time,
                start_frame=start_frame,
                end_frame=end_frame,
                keyframes=segment_keyframes,
                segment_type=segment_analysis['segment_type'],
                activity_level=segment_analysis['activity_level'],
                motion_statistics=segment_analysis['motion_statistics'],
                quality_statistics=segment_analysis['quality_statistics']
            )
            
            segments.append(segment)
        
        logger.info(f"Created {len(segments)} video segments")
        return segments
    
    def _get_keyframes_in_segment(self, keyframes: List, start_time: float, 
                                end_time: float) -> List[Dict[str, Any]]:
        """Get keyframes that fall within a segment's time range"""
        segment_keyframes = []
        
        for kf in keyframes:
            timestamp = kf.frame_data.timestamp
            if start_time <= timestamp < end_time:
                # Convert keyframe to serializable format
                kf_dict = {
                    'frame_data': {
                        'frame_path': kf.frame_data.frame_path,
                        'timestamp': kf.frame_data.timestamp,
                        'frame_number': kf.frame_data.frame_number,
                        'quality_score': kf.frame_data.quality_score,
                        'motion_score': kf.frame_data.motion_score,
                        'burst_active': kf.frame_data.burst_active,
                        'enhancement_applied': kf.frame_data.enhancement_applied
                    },
                    'keyframe_score': kf.keyframe_score,
                    'selection_reason': kf.selection_reason
                }
                segment_keyframes.append(kf_dict)
        
        # Sort by timestamp
        segment_keyframes.sort(key=lambda x: x['frame_data']['timestamp'])
        
        # Limit keyframes per segment if configured
        if len(segment_keyframes) > self.config.keyframes_per_segment:
            # Select top keyframes by score
            segment_keyframes.sort(key=lambda x: x['keyframe_score'], reverse=True)
            segment_keyframes = segment_keyframes[:self.config.keyframes_per_segment]
            # Re-sort by timestamp
            segment_keyframes.sort(key=lambda x: x['frame_data']['timestamp'])
        
        return segment_keyframes
    
    def _analyze_segment(self, keyframes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze segment characteristics"""
        if not keyframes:
            return {
                'segment_type': 'empty',
                'activity_level': 'none',
                'motion_statistics': {'min': 0, 'max': 0, 'mean': 0, 'std': 0},
                'quality_statistics': {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
            }
        
        # Extract metrics
        motion_scores = [kf['frame_data']['motion_score'] for kf in keyframes]
        quality_scores = [kf['frame_data']['quality_score'] for kf in keyframes]
        burst_count = sum(1 for kf in keyframes if kf['frame_data']['burst_active'])
        
        # Motion statistics
        motion_stats = {
            'min': float(np.min(motion_scores)),
            'max': float(np.max(motion_scores)),
            'mean': float(np.mean(motion_scores)),
            'std': float(np.std(motion_scores))
        }
        
        # Quality statistics
        quality_stats = {
            'min': float(np.min(quality_scores)),
            'max': float(np.max(quality_scores)),
            'mean': float(np.mean(quality_scores)),
            'std': float(np.std(quality_scores))
        }
        
        # Determine segment type
        segment_type = self._classify_segment_type(motion_stats, quality_stats, burst_count)
        
        # Determine activity level
        activity_level = self._classify_activity_level(motion_stats, burst_count)
        
        return {
            'segment_type': segment_type,
            'activity_level': activity_level,
            'motion_statistics': motion_stats,
            'quality_statistics': quality_stats
        }
    
    def _classify_segment_type(self, motion_stats: Dict, quality_stats: Dict, 
                             burst_count: int) -> str:
        """Classify segment type based on characteristics"""
        avg_motion = motion_stats['mean']
        max_motion = motion_stats['max']
        avg_quality = quality_stats['mean']
        
        if burst_count >= 2:
            return 'burst_activity'
        elif max_motion > self.config.motion_threshold * 2:
            return 'high_motion'
        elif avg_motion > self.config.motion_threshold:
            return 'moderate_motion'
        elif avg_quality > self.config.base_quality_threshold * 1.2:
            return 'high_quality'
        else:
            return 'static'
    
    def _classify_activity_level(self, motion_stats: Dict, burst_count: int) -> str:
        """Classify activity level of segment"""
        avg_motion = motion_stats['mean']
        max_motion = motion_stats['max']
        
        if burst_count >= 3 or max_motion > self.config.motion_threshold * 3:
            return 'very_high'
        elif burst_count >= 2 or max_motion > self.config.motion_threshold * 2:
            return 'high'
        elif burst_count >= 1 or avg_motion > self.config.motion_threshold:
            return 'moderate'
        elif avg_motion > self.config.motion_threshold * 0.5:
            return 'low'
        else:
            return 'very_low'
    
    def save_segments_metadata(self, segments: List[VideoSegment], output_path: str) -> bool:
        """Save segment metadata to JSON file"""
        try:
            segments_data = {
                'metadata': {
                    'total_segments': len(segments),
                    'segment_duration': self.config.segment_duration,
                    'keyframes_per_segment': self.config.keyframes_per_segment,
                    'generation_timestamp': datetime.now().isoformat()
                },
                'segments': [asdict(segment) for segment in segments]
            }
            
            with open(output_path, 'w') as f:
                json.dump(segments_data, f, indent=2)
            
            logger.info(f"Segments metadata saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save segments metadata: {e}")
            return False
    
    def save_individual_segment_files(self, segments: List[VideoSegment]) -> bool:
        """Save individual JSON files for each segment"""
        try:
            for segment in segments:
                segment_file = os.path.join(
                    self.segments_dir, 
                    f"segment_{segment.segment_id:03d}.json"
                )
                
                segment_data = {
                    'segment_info': asdict(segment),
                    'keyframe_details': segment.keyframes
                }
                
                with open(segment_file, 'w') as f:
                    json.dump(segment_data, f, indent=2)
            
            logger.info(f"Individual segment files saved to: {self.segments_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save individual segment files: {e}")
            return False
    
    def generate_segment_summary(self, segments: List[VideoSegment]) -> Dict[str, Any]:
        """Generate summary statistics for all segments"""
        if not segments:
            return {}
        
        # Aggregate statistics
        total_keyframes = sum(len(seg.keyframes) for seg in segments)
        activity_levels = [seg.activity_level for seg in segments]
        segment_types = [seg.segment_type for seg in segments]
        
        # Count by activity level
        activity_counts = {}
        for level in activity_levels:
            activity_counts[level] = activity_counts.get(level, 0) + 1
        
        # Count by segment type
        type_counts = {}
        for seg_type in segment_types:
            type_counts[seg_type] = type_counts.get(seg_type, 0) + 1
        
        # Motion statistics across all segments
        all_motion_means = [seg.motion_statistics['mean'] for seg in segments]
        all_quality_means = [seg.quality_statistics['mean'] for seg in segments]
        
        summary = {
            'total_segments': len(segments),
            'total_keyframes': total_keyframes,
            'average_keyframes_per_segment': total_keyframes / len(segments),
            'activity_level_distribution': activity_counts,
            'segment_type_distribution': type_counts,
            'overall_motion_statistics': {
                'min': float(np.min(all_motion_means)),
                'max': float(np.max(all_motion_means)),
                'mean': float(np.mean(all_motion_means)),
                'std': float(np.std(all_motion_means))
            },
            'overall_quality_statistics': {
                'min': float(np.min(all_quality_means)),
                'max': float(np.max(all_quality_means)),
                'mean': float(np.mean(all_quality_means)),
                'std': float(np.std(all_quality_means))
            }
        }
        
        return summary
    
    def get_high_activity_segments(self, segments: List[VideoSegment]) -> List[VideoSegment]:
        """Get segments with high activity levels"""
        high_activity_levels = {'high', 'very_high'}
        return [seg for seg in segments if seg.activity_level in high_activity_levels]
    
    def get_segments_by_type(self, segments: List[VideoSegment], 
                           segment_type: str) -> List[VideoSegment]:
        """Get segments of a specific type"""
        return [seg for seg in segments if seg.segment_type == segment_type]
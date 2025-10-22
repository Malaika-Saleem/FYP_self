"""
JSON Reports Generation Module

This module handles:
- Processing results JSON reports
- Canonical events JSON
- Segment analysis reports
- Performance statistics
- HTML gallery generation
"""

import json
import os
import cv2
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate comprehensive JSON reports and HTML galleries"""
    
    def __init__(self, config):
        self.config = config
        self.reports_dir = os.path.join(config.output_base_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_processing_results_report(self, 
                                         keyframes: List,
                                         events: List,
                                         canonical_events: List,
                                         segments: List,
                                         processing_stats: Dict[str, Any]) -> str:
        """Generate comprehensive processing results report"""
        
        logger.info("Generating processing results report")
        
        report = {
            'metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'report_version': '1.0',
                'processing_config': self._get_config_summary()
            },
            'summary': {
                'total_keyframes_extracted': len(keyframes),
                'total_events_detected': len(events),
                'canonical_events_created': len(canonical_events),
                'video_segments_created': len(segments),
                'processing_duration': processing_stats.get('total_processing_time', 0)
            },
            'keyframe_analysis': self._analyze_keyframes(keyframes),
            'event_analysis': self._analyze_events(events),
            'canonical_event_analysis': self._analyze_canonical_events(canonical_events),
            'segment_analysis': self._analyze_segments(segments),
            'performance_statistics': processing_stats,
            'quality_metrics': self._calculate_quality_metrics(keyframes, events)
        }
        
        # Save report
        output_path = os.path.join(self.reports_dir, "processing_results.json")
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Processing results report saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save processing results report: {e}")
            return ""
    
    def generate_canonical_events_report(self, canonical_events: List) -> str:
        """Generate canonical events JSON report"""
        
        logger.info("Generating canonical events report")
        
        report = {
            'metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'total_canonical_events': len(canonical_events),
                'deduplication_threshold': self.config.similarity_threshold
            },
            'canonical_events': []
        }
        
        for event in canonical_events:
            event_data = {
                'canonical_id': event.canonical_id,
                'event_type': event.event_type,
                'representative_frame': event.representative_frame,
                'time_range': {
                    'start_time': event.start_time,
                    'end_time': event.end_time,
                    'duration': event.duration
                },
                'confidence': event.confidence,
                'frame_count': event.frame_count,
                'aggregated_events': event.aggregated_events,
                'description': event.description,
                'similarity_cluster': event.similarity_cluster
            }
            report['canonical_events'].append(event_data)
        
        # Save report
        output_path = os.path.join(self.reports_dir, "canonical_events.json")
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Canonical events report saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save canonical events report: {e}")
            return ""
    
    def generate_segments_report(self, segments: List) -> str:
        """Generate video segments analysis report"""
        
        logger.info("Generating video segments report")
        
        report = {
            'metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'total_segments': len(segments),
                'segment_duration': self.config.segment_duration,
                'keyframes_per_segment': self.config.keyframes_per_segment
            },
            'summary_statistics': self._get_segments_summary(segments),
            'segments': []
        }
        
        for segment in segments:
            segment_data = {
                'segment_id': segment.segment_id,
                'time_range': {
                    'start_timestamp': segment.start_timestamp,
                    'end_timestamp': segment.end_timestamp,
                    'duration': segment.duration
                },
                'frame_range': {
                    'start_frame': segment.start_frame,
                    'end_frame': segment.end_frame
                },
                'segment_classification': {
                    'segment_type': segment.segment_type,
                    'activity_level': segment.activity_level
                },
                'statistics': {
                    'motion_statistics': segment.motion_statistics,
                    'quality_statistics': segment.quality_statistics,
                    'keyframe_count': len(segment.keyframes)
                },
                'keyframes': segment.keyframes
            }
            report['segments'].append(segment_data)
        
        # Save report
        output_path = os.path.join(self.reports_dir, "video_segments.json")
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Video segments report saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save video segments report: {e}")
            return ""
    
    def generate_html_gallery(self, keyframes: List, canonical_events: List = None, 
                            segments: List = None, title: str = "Video Processing Gallery") -> str:
        """Generate interactive HTML gallery of keyframes and events"""
        
        logger.info("Generating HTML gallery")
        
        html_content = self._create_html_gallery(keyframes, canonical_events, segments, title)
        
        # Save HTML gallery
        output_path = os.path.join(self.reports_dir, "canonical_gallery.html")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML gallery saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save HTML gallery: {e}")
            return ""
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """Get summary of configuration settings"""
        return {
            'base_quality_threshold': self.config.base_quality_threshold,
            'motion_threshold': self.config.motion_threshold,
            'event_importance_threshold': self.config.event_importance_threshold,
            'similarity_threshold': self.config.similarity_threshold,
            'segment_duration': self.config.segment_duration,
            'max_summary_frames': self.config.max_summary_frames,
            'output_resolution': self.config.output_resolution,
            'enable_clahe': self.config.enable_clahe,
            'enable_denoising': self.config.enable_denoising
        }
    
    def _analyze_keyframes(self, keyframes: List) -> Dict[str, Any]:
        """Analyze keyframe extraction results"""
        if not keyframes:
            return {}
        
        # Extract metrics
        quality_scores = [kf.frame_data.quality_score for kf in keyframes]
        motion_scores = [kf.frame_data.motion_score for kf in keyframes]
        selection_reasons = [kf.selection_reason for kf in keyframes]
        burst_frames = [kf for kf in keyframes if kf.frame_data.burst_active]
        enhanced_frames = [kf for kf in keyframes if kf.frame_data.enhancement_applied]
        
        # Count selection reasons
        reason_counts = {}
        for reason in selection_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # Calculate statistics
        analysis = {
            'total_keyframes': len(keyframes),
            'quality_statistics': {
                'min': float(min(quality_scores)),
                'max': float(max(quality_scores)),
                'mean': float(sum(quality_scores) / len(quality_scores)),
                'std': float(np.std(quality_scores))
            },
            'motion_statistics': {
                'min': float(min(motion_scores)),
                'max': float(max(motion_scores)),
                'mean': float(sum(motion_scores) / len(motion_scores)),
                'std': float(np.std(motion_scores))
            },
            'selection_reason_distribution': reason_counts,
            'burst_frames_count': len(burst_frames),
            'enhanced_frames_count': len(enhanced_frames),
            'enhancement_rate': len(enhanced_frames) / len(keyframes) * 100
        }
        
        return analysis
    
    def _analyze_events(self, events: List) -> Dict[str, Any]:
        """Analyze detected events"""
        if not events:
            return {}
        
        # Event type distribution
        event_types = [event.event_type for event in events]
        type_counts = {}
        for event_type in event_types:
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # Confidence statistics
        confidences = [event.confidence for event in events]
        importance_scores = [event.importance_score for event in events]
        durations = [event.end_timestamp - event.start_timestamp for event in events]
        
        analysis = {
            'total_events': len(events),
            'event_type_distribution': type_counts,
            'confidence_statistics': {
                'min': float(min(confidences)),
                'max': float(max(confidences)),
                'mean': float(sum(confidences) / len(confidences))
            },
            'importance_statistics': {
                'min': float(min(importance_scores)),
                'max': float(max(importance_scores)),
                'mean': float(sum(importance_scores) / len(importance_scores))
            },
            'duration_statistics': {
                'min': float(min(durations)),
                'max': float(max(durations)),
                'mean': float(sum(durations) / len(durations))
            }
        }
        
        return analysis
    
    def _analyze_canonical_events(self, canonical_events: List) -> Dict[str, Any]:
        """Analyze canonical events"""
        if not canonical_events:
            return {}
        
        # Type distribution
        event_types = [event.event_type for event in canonical_events]
        type_counts = {}
        for event_type in event_types:
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # Statistics
        durations = [event.duration for event in canonical_events]
        frame_counts = [event.frame_count for event in canonical_events]
        confidences = [event.confidence for event in canonical_events]
        
        analysis = {
            'total_canonical_events': len(canonical_events),
            'event_type_distribution': type_counts,
            'duration_statistics': {
                'min': float(min(durations)),
                'max': float(max(durations)),
                'mean': float(sum(durations) / len(durations))
            },
            'frame_count_statistics': {
                'min': int(min(frame_counts)),
                'max': int(max(frame_counts)),
                'mean': float(sum(frame_counts) / len(frame_counts))
            },
            'confidence_statistics': {
                'min': float(min(confidences)),
                'max': float(max(confidences)),
                'mean': float(sum(confidences) / len(confidences))
            }
        }
        
        return analysis
    
    def _analyze_segments(self, segments: List) -> Dict[str, Any]:
        """Analyze video segments"""
        if not segments:
            return {}
        
        # Type and activity distribution
        segment_types = [seg.segment_type for seg in segments]
        activity_levels = [seg.activity_level for seg in segments]
        
        type_counts = {}
        for seg_type in segment_types:
            type_counts[seg_type] = type_counts.get(seg_type, 0) + 1
        
        activity_counts = {}
        for activity in activity_levels:
            activity_counts[activity] = activity_counts.get(activity, 0) + 1
        
        analysis = {
            'total_segments': len(segments),
            'segment_type_distribution': type_counts,
            'activity_level_distribution': activity_counts,
            'average_segment_duration': float(sum(seg.duration for seg in segments) / len(segments)),
            'total_keyframes': sum(len(seg.keyframes) for seg in segments)
        }
        
        return analysis
    
    def _calculate_quality_metrics(self, keyframes: List, events: List) -> Dict[str, Any]:
        """Calculate overall quality metrics"""
        if not keyframes:
            return {}
        
        # Coverage metrics
        total_frames_extracted = len(keyframes)
        burst_frames = len([kf for kf in keyframes if kf.frame_data.burst_active])
        high_quality_frames = len([kf for kf in keyframes if kf.frame_data.quality_score > self.config.base_quality_threshold * 1.2])
        high_motion_frames = len([kf for kf in keyframes if kf.frame_data.motion_score > self.config.motion_threshold])
        
        # Event coverage
        event_coverage = len(events) / total_frames_extracted if total_frames_extracted > 0 else 0
        
        metrics = {
            'frame_extraction_efficiency': {
                'total_frames_extracted': total_frames_extracted,
                'burst_frame_rate': burst_frames / total_frames_extracted * 100,
                'high_quality_frame_rate': high_quality_frames / total_frames_extracted * 100,
                'high_motion_frame_rate': high_motion_frames / total_frames_extracted * 100
            },
            'event_detection_efficiency': {
                'events_per_keyframe': event_coverage,
                'total_events_detected': len(events)
            },
            'processing_quality_score': self._calculate_overall_quality_score(keyframes, events)
        }
        
        return metrics
    
    def _calculate_overall_quality_score(self, keyframes: List, events: List) -> float:
        """Calculate overall processing quality score (0-100)"""
        if not keyframes:
            return 0.0
        
        # Component scores
        avg_quality = sum(kf.frame_data.quality_score for kf in keyframes) / len(keyframes)
        avg_motion = sum(kf.frame_data.motion_score for kf in keyframes) / len(keyframes)
        burst_rate = len([kf for kf in keyframes if kf.frame_data.burst_active]) / len(keyframes)
        event_rate = len(events) / len(keyframes) if len(keyframes) > 0 else 0
        
        # Weighted combination
        quality_score = (
            avg_quality * 40 +       # 40% weight on frame quality
            avg_motion * 30 +        # 30% weight on motion detection
            burst_rate * 20 +        # 20% weight on burst detection
            event_rate * 10          # 10% weight on event detection
        ) * 100
        
        return min(100.0, quality_score)
    
    def _get_segments_summary(self, segments: List) -> Dict[str, Any]:
        """Get summary statistics for segments"""
        if not segments:
            return {}
        
        # Activity level distribution
        activity_levels = [seg.activity_level for seg in segments]
        activity_counts = {}
        for level in activity_levels:
            activity_counts[level] = activity_counts.get(level, 0) + 1
        
        # Segment type distribution
        segment_types = [seg.segment_type for seg in segments]
        type_counts = {}
        for seg_type in segment_types:
            type_counts[seg_type] = type_counts.get(seg_type, 0) + 1
        
        return {
            'total_segments': len(segments),
            'activity_level_distribution': activity_counts,
            'segment_type_distribution': type_counts
        }
    
    def _create_html_gallery(self, keyframes: List, canonical_events: List = None, 
                           segments: List = None, title: str = "Video Processing Gallery") -> str:
        """Create HTML gallery content"""
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .stats {{ display: flex; justify-content: space-around; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .frame-card {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .frame-image {{ width: 100%; height: 200px; object-fit: cover; }}
        .frame-info {{ padding: 15px; }}
        .frame-info h3 {{ margin: 0 0 10px 0; color: #333; }}
        .frame-info p {{ margin: 5px 0; color: #666; font-size: 14px; }}
        .event-badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; color: white; margin-right: 5px; }}
        .burst-activity {{ background-color: #e74c3c; }}
        .high-motion {{ background-color: #f39c12; }}
        .high-quality {{ background-color: #27ae60; }}
        .context-frame {{ background-color: #3498db; }}
        .timestamp {{ font-weight: bold; color: #2c3e50; }}
        .score {{ color: #8e44ad; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Keyframes</h3>
            <p>{len(keyframes)} extracted</p>
        </div>
        <div class="stat-card">
            <h3>Events</h3>
            <p>{len(canonical_events) if canonical_events else 0} canonical</p>
        </div>
        <div class="stat-card">
            <h3>Segments</h3>
            <p>{len(segments) if segments else 0} temporal</p>
        </div>
    </div>
    
    <div class="gallery">
"""
        
        # Add keyframes to gallery
        for i, kf in enumerate(keyframes[:50]):  # Limit to first 50 for performance
            try:
                frame_path = kf.frame_data.frame_path
                
                # Convert image to base64 for embedding
                image_data = ""
                if os.path.exists(frame_path):
                    try:
                        with open(frame_path, 'rb') as img_file:
                            image_data = base64.b64encode(img_file.read()).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Could not encode image {frame_path}: {e}")
                
                # Format timestamp
                timestamp = kf.frame_data.timestamp
                mins = int(timestamp // 60)
                secs = timestamp % 60
                time_str = f"{mins:02d}:{secs:04.1f}"
                
                # Determine badge class
                badge_class = "context-frame"
                if kf.frame_data.burst_active:
                    badge_class = "burst-activity"
                elif kf.frame_data.motion_score > self.config.motion_threshold:
                    badge_class = "high-motion"
                elif kf.frame_data.quality_score > self.config.base_quality_threshold * 1.2:
                    badge_class = "high-quality"
                
                html_template += f"""
        <div class="frame-card">
            {"<img class='frame-image' src='data:image/jpeg;base64," + image_data + "' alt='Keyframe " + str(i+1) + "'>" if image_data else "<div class='frame-image' style='background-color: #ddd; display: flex; align-items: center; justify-content: center;'>Image not available</div>"}
            <div class="frame-info">
                <h3>Frame {i+1}</h3>
                <p><span class="timestamp">Time: {time_str}</span></p>
                <p>Quality: <span class="score">{kf.frame_data.quality_score:.3f}</span></p>
                <p>Motion: <span class="score">{kf.frame_data.motion_score:.4f}</span></p>
                <p>Keyframe Score: <span class="score">{kf.keyframe_score:.3f}</span></p>
                <p><span class="event-badge {badge_class}">{kf.selection_reason}</span></p>
                {"<p>✨ Enhanced</p>" if kf.frame_data.enhancement_applied else ""}
            </div>
        </div>
"""
                
            except Exception as e:
                logger.warning(f"Error processing keyframe {i}: {e}")
        
        html_template += """
    </div>
</body>
</html>
"""
        
        return html_template

# Import numpy for statistics
import numpy as np
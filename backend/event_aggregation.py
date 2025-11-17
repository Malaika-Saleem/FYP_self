"""
Event Aggregation and Deduplication Module

This module handles:
- Event detection and clustering
- Temporal aggregation of related events
- Duplicate frame removal using similarity detection
- Canonical event generation
"""

import numpy as np
import cv2
import json
import os
from typing import List, Dict, Tuple, Set, Any, Optional
from dataclasses import dataclass, asdict
import imagehash
from PIL import Image
from collections import defaultdict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """Represents a detected event"""
    event_id: str
    start_timestamp: float
    end_timestamp: float
    event_type: str
    confidence: float
    keyframes: List[str]  # Frame paths
    importance_score: float
    motion_intensity: float
    description: str = ""
    # Object detection specific fields
    object_class: str = ""           # For object-based events (fire, knife, gun)
    detection_count: int = 0         # Number of detections in this event
    max_confidence: float = 0.0      # Highest confidence detection
    is_object_event: bool = False    # Flag to identify object-based events
    detection_details: List = None   # Raw detection data

@dataclass
class CanonicalEvent:
    """Canonical representation of aggregated events"""
    canonical_id: str
    event_type: str
    representative_frame: str
    start_time: float
    end_time: float
    duration: float
    confidence: float
    frame_count: int
    aggregated_events: List[str]  # Event IDs
    description: str
    similarity_cluster: int
    # Enhanced object detection fields
    contains_objects: bool = False           # Whether this canonical event has object detections
    detected_object_classes: List[str] = None  # List of detected object classes
    object_detection_summary: Dict = None      # Summary of object detections
    threat_level: str = "low"                # Threat assessment: low, medium, high, critical

class SimilarityCalculator:
    """Calculate similarity between frames using multiple methods"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        
    def calculate_histogram_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate histogram-based similarity"""
        try:
            # Convert to HSV for better color comparison
            hsv1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2HSV)
            
            # Calculate histograms
            hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
            hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
            
            # Calculate correlation
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return max(0.0, correlation)
            
        except Exception as e:
            logger.error(f"Histogram similarity calculation failed: {e}")
            return 0.0
    
    def calculate_perceptual_hash_similarity(self, frame1_path: str, frame2_path: str) -> float:
        """Calculate perceptual hash similarity"""
        try:
            # Load images with PIL for imagehash
            img1 = Image.open(frame1_path)
            img2 = Image.open(frame2_path)
            
            # Calculate perceptual hashes
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
            
            # Calculate similarity (lower hash difference = higher similarity)
            hash_diff = hash1 - hash2
            similarity = 1.0 - (hash_diff / 64.0)  # Normalize to 0-1
            
            return max(0.0, similarity)
            
        except Exception as e:
            logger.error(f"Perceptual hash similarity calculation failed: {e}")
            return 0.0
    
    def calculate_structural_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate structural similarity using template matching"""
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # Resize to same dimensions if needed
            if gray1.shape != gray2.shape:
                h, w = min(gray1.shape[0], gray2.shape[0]), min(gray1.shape[1], gray2.shape[1])
                gray1 = cv2.resize(gray1, (w, h))
                gray2 = cv2.resize(gray2, (w, h))
            
            # Calculate normalized cross-correlation
            result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
            similarity = result[0, 0]
            
            return max(0.0, similarity)
            
        except Exception as e:
            logger.error(f"Structural similarity calculation failed: {e}")
            return 0.0
    
    def calculate_combined_similarity(self, frame1_path: str, frame2_path: str) -> float:
        """Calculate combined similarity score using multiple methods"""
        try:
            # Load frames
            frame1 = cv2.imread(frame1_path)
            frame2 = cv2.imread(frame2_path)
            
            if frame1 is None or frame2 is None:
                return 0.0
            
            # Calculate different similarity metrics
            hist_sim = self.calculate_histogram_similarity(frame1, frame2)
            hash_sim = self.calculate_perceptual_hash_similarity(frame1_path, frame2_path)
            struct_sim = self.calculate_structural_similarity(frame1, frame2)
            
            # Weighted combination
            combined_similarity = (
                hist_sim * 0.4 +      # Histogram similarity
                hash_sim * 0.4 +      # Perceptual hash similarity
                struct_sim * 0.2      # Structural similarity
            )
            
            return min(1.0, combined_similarity)
            
        except Exception as e:
            logger.error(f"Combined similarity calculation failed: {e}")
            return 0.0

class EventDetector:
    """Detect events from keyframes"""
    
    def __init__(self, config):
        self.config = config
        self.event_types = {
            'high_motion': {'motion_threshold': config.motion_threshold * 2},
            'burst_activity': {'requires_burst': True},
            'scene_change': {'change_threshold': config.scene_change_threshold},
            'quality_peak': {'quality_threshold': config.base_quality_threshold * 1.5}
        }
    
    def detect_events(self, keyframes: List) -> List[Event]:
        """Detect events from keyframes"""
        logger.info(f"Detecting events from {len(keyframes)} keyframes")
        
        events = []
        event_id_counter = 1
        
        # Temporal clustering for event detection
        clusters = self._create_temporal_clusters(keyframes)
        
        for cluster in clusters:
            if len(cluster) == 0:
                continue
                
            # Analyze cluster for event types
            cluster_events = self._analyze_cluster_for_events(cluster, event_id_counter)
            events.extend(cluster_events)
            event_id_counter += len(cluster_events)
        
        logger.info(f"Detected {len(events)} events")
        return events
    
    def _create_temporal_clusters(self, keyframes: List) -> List[List]:
        """Create temporal clusters of keyframes"""
        if not keyframes:
            return []
        
        # Sort keyframes by timestamp
        sorted_keyframes = sorted(keyframes, key=lambda x: x.frame_data.timestamp)
        
        clusters = []
        current_cluster = [sorted_keyframes[0]]
        
        for i in range(1, len(sorted_keyframes)):
            current_kf = sorted_keyframes[i]
            last_kf = current_cluster[-1]
            
            time_gap = current_kf.frame_data.timestamp - last_kf.frame_data.timestamp
            
            # If gap is within clustering window, add to current cluster
            if time_gap <= self.config.temporal_clustering_window:
                current_cluster.append(current_kf)
            else:
                # Start new cluster
                if len(current_cluster) > 0:
                    clusters.append(current_cluster)
                current_cluster = [current_kf]
        
        # Don't forget the last cluster
        if len(current_cluster) > 0:
            clusters.append(current_cluster)
        
        return clusters
    
    def _analyze_cluster_for_events(self, cluster: List, start_event_id: int) -> List[Event]:
        """Analyze a temporal cluster for different event types"""
        events = []
        
        if not cluster:
            return events
        
        # Calculate cluster metrics
        motion_scores = [kf.frame_data.motion_score for kf in cluster]
        quality_scores = [kf.frame_data.quality_score for kf in cluster]
        burst_frames = [kf for kf in cluster if kf.frame_data.burst_active]
        
        start_time = min(kf.frame_data.timestamp for kf in cluster)
        end_time = max(kf.frame_data.timestamp for kf in cluster)
        
        max_motion = max(motion_scores) if motion_scores else 0
        avg_motion = sum(motion_scores) / len(motion_scores) if motion_scores else 0
        max_quality = max(quality_scores) if quality_scores else 0
        
        # High motion event
        if max_motion > self.config.motion_threshold * 2:
            event = Event(
                event_id=f"event_{start_event_id:04d}",
                start_timestamp=start_time,
                end_timestamp=end_time,
                event_type="high_motion",
                confidence=min(max_motion * 2, 1.0),
                keyframes=[kf.frame_data.frame_path for kf in cluster],
                importance_score=max_motion + (avg_motion * 0.5),
                motion_intensity=max_motion,
                description=f"High motion event with peak intensity {max_motion:.3f}"
            )
            events.append(event)
            start_event_id += 1
        
        # Burst activity event
        if len(burst_frames) >= 2:
            event = Event(
                event_id=f"event_{start_event_id:04d}",
                start_timestamp=start_time,
                end_timestamp=end_time,
                event_type="burst_activity",
                confidence=min(len(burst_frames) / len(cluster), 1.0),
                keyframes=[kf.frame_data.frame_path for kf in burst_frames],
                importance_score=len(burst_frames) * 0.3 + avg_motion,
                motion_intensity=max_motion,
                description=f"Burst activity with {len(burst_frames)} active frames"
            )
            events.append(event)
            start_event_id += 1
        
        # Quality peak event
        if max_quality > self.config.base_quality_threshold * 1.5:
            high_quality_frames = [kf for kf in cluster if kf.frame_data.quality_score > self.config.base_quality_threshold * 1.3]
            if high_quality_frames:
                event = Event(
                    event_id=f"event_{start_event_id:04d}",
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                    event_type="quality_peak",
                    confidence=max_quality,
                    keyframes=[kf.frame_data.frame_path for kf in high_quality_frames],
                    importance_score=max_quality + (len(high_quality_frames) * 0.1),
                    motion_intensity=max_motion,
                    description=f"High quality event with peak score {max_quality:.3f}"
                )
                events.append(event)
        
        return events
    
    def convert_object_events_to_standard_format(self, object_events: List[Dict]) -> List[Event]:
        """Convert object events from object detection module to standard Event format"""
        standard_events = []
        
        for obj_event in object_events:
            # Convert object event dict to Event dataclass
            event = Event(
                event_id=obj_event['event_id'],
                start_timestamp=obj_event['start_timestamp'],
                end_timestamp=obj_event['end_timestamp'],
                event_type=obj_event['event_type'],
                confidence=obj_event['confidence'],
                keyframes=obj_event['keyframes'],
                importance_score=obj_event['importance_score'],
                motion_intensity=obj_event.get('motion_intensity', 0.0),
                description=obj_event['description'],
                # Object-specific fields
                object_class=obj_event.get('object_class', ''),
                detection_count=obj_event.get('detection_count', 0),
                max_confidence=obj_event.get('max_confidence', obj_event['confidence']),
                is_object_event=True,
                detection_details=obj_event.get('detection_details', [])
            )
            standard_events.append(event)
        
        return standard_events
    
    def convert_behavior_events_to_standard_format(self, behavior_events: List) -> List[Event]:
        """Convert behavior events from behavior analysis module to standard Event format"""
        standard_events = []
        
        for behavior_event in behavior_events:
            # Handle both dataclass and dict formats
            if hasattr(behavior_event, 'behavior_type'):
                # Dataclass format (from BehaviorEvent)
                event = Event(
                    event_id=behavior_event.event_id,
                    start_timestamp=behavior_event.start_timestamp,
                    end_timestamp=behavior_event.end_timestamp,
                    event_type=f"behavior_{behavior_event.behavior_type}",
                    confidence=behavior_event.confidence,
                    keyframes=behavior_event.keyframes,
                    importance_score=behavior_event.importance_score,
                    motion_intensity=0.0,  # Behavior events don't have motion intensity
                    description=f"{behavior_event.behavior_type.capitalize()} detected (confidence: {behavior_event.confidence:.2f})",
                    # Use object_class field to store behavior type for consistency
                    object_class=behavior_event.behavior_type,
                    detection_count=len(behavior_event.frame_indices),
                    max_confidence=behavior_event.confidence,
                    is_object_event=False,  # Behavior events are separate from object events
                    detection_details=[{
                        'model_used': behavior_event.model_used,
                        'frame_indices': behavior_event.frame_indices
                    }]
                )
            else:
                # Dict format (fallback)
                event = Event(
                    event_id=behavior_event.get('event_id', f"behavior_{len(standard_events)}"),
                    start_timestamp=behavior_event.get('start_timestamp', 0.0),
                    end_timestamp=behavior_event.get('end_timestamp', 0.0),
                    event_type=f"behavior_{behavior_event.get('behavior_type', 'unknown')}",
                    confidence=behavior_event.get('confidence', 0.0),
                    keyframes=behavior_event.get('keyframes', []),
                    importance_score=behavior_event.get('importance_score', 0.0),
                    motion_intensity=0.0,
                    description=behavior_event.get('description', 'Behavior detected'),
                    object_class=behavior_event.get('behavior_type', ''),
                    detection_count=len(behavior_event.get('frame_indices', [])),
                    max_confidence=behavior_event.get('confidence', 0.0),
                    is_object_event=False,
                    detection_details=[{
                        'model_used': behavior_event.get('model_used', 'unknown'),
                        'frame_indices': behavior_event.get('frame_indices', [])
                    }]
                )
            
            standard_events.append(event)
        
        return standard_events
    
    def assess_threat_level(self, event: Event) -> str:
        """Assess threat level for events, particularly object-based events"""
        if not event.is_object_event:
            # For motion events, use motion intensity and burst activity
            if event.event_type == "high_motion" and event.motion_intensity > 0.015:
                return "medium"
            elif event.event_type == "burst_activity":
                return "medium"
            else:
                return "low"
        
        # Object-based threat assessment
        threat_map = {
            'fire': {
                'low': 0.3,      # Confidence thresholds
                'medium': 0.5,
                'high': 0.7,
                'critical': 0.85
            },
            'gun': {
                'low': 0.4,
                'medium': 0.6,
                'high': 0.8,
                'critical': 0.9
            },
            'knife': {
                'low': 0.4,
                'medium': 0.6,
                'high': 0.75,
                'critical': 0.85
            }
        }
        
        obj_class = event.object_class.lower()
        confidence = event.max_confidence
        
        if obj_class in threat_map:
            thresholds = threat_map[obj_class]
            if confidence >= thresholds['critical']:
                return "critical"
            elif confidence >= thresholds['high']:
                return "high"
            elif confidence >= thresholds['medium']:
                return "medium"
            else:
                return "low"
        
        return "medium"  # Default for unknown object types

class EventDeduplicationEngine:
    """Remove duplicate events and create canonical representations"""
    
    def __init__(self, config):
        self.config = config
        self.similarity_calculator = SimilarityCalculator(config.similarity_threshold)
    
    def deduplicate_events(self, events: List[Event]) -> Tuple[List[CanonicalEvent], Dict[str, Any]]:
        """
        Deduplicate events and create canonical representations
        
        Returns:
            Tuple of (canonical_events, deduplication_stats)
        """
        logger.info(f"Deduplicating {len(events)} events")
        
        if not events:
            return [], {}
        
        # Group events by type first
        events_by_type = defaultdict(list)
        for event in events:
            events_by_type[event.event_type].append(event)
        
        canonical_events = []
        dedup_stats = {
            'original_events': len(events),
            'canonical_events': 0,
            'duplicates_removed': 0,
            'similarity_clusters': 0
        }
        
        canonical_id_counter = 1
        
        # Process each event type separately
        for event_type, type_events in events_by_type.items():
            type_canonical = self._deduplicate_events_by_type(
                type_events, event_type, canonical_id_counter
            )
            canonical_events.extend(type_canonical)
            canonical_id_counter += len(type_canonical)
        
        # Update stats
        dedup_stats['canonical_events'] = len(canonical_events)
        dedup_stats['duplicates_removed'] = dedup_stats['original_events'] - dedup_stats['canonical_events']
        dedup_stats['similarity_clusters'] = len(canonical_events)
        
        logger.info(f"Deduplication complete: {len(canonical_events)} canonical events created")
        return canonical_events, dedup_stats
    
    def _deduplicate_events_by_type(self, events: List[Event], event_type: str, 
                                  start_canonical_id: int) -> List[CanonicalEvent]:
        """Deduplicate events of the same type"""
        if not events:
            return []
        
        # Create similarity matrix
        similarity_matrix = self._create_similarity_matrix(events)
        
        # Cluster similar events
        clusters = self._cluster_similar_events(events, similarity_matrix)
        
        # Create canonical events from clusters
        canonical_events = []
        for i, cluster in enumerate(clusters):
            canonical_event = self._create_canonical_event(
                cluster, event_type, start_canonical_id + i, i
            )
            canonical_events.append(canonical_event)
        
        return canonical_events
    
    def _create_similarity_matrix(self, events: List[Event]) -> np.ndarray:
        """Create similarity matrix between events"""
        n = len(events)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i, j] = 1.0
                else:
                    # Calculate similarity between representative frames
                    sim_score = self._calculate_event_similarity(events[i], events[j])
                    similarity_matrix[i, j] = sim_score
                    similarity_matrix[j, i] = sim_score
        
        return similarity_matrix
    
    def _calculate_event_similarity(self, event1: Event, event2: Event) -> float:
        """Calculate similarity between two events (enhanced for object events)"""
        try:
            # Object events similarity
            if event1.is_object_event and event2.is_object_event:
                return self._calculate_object_event_similarity(event1, event2)
            elif event1.is_object_event != event2.is_object_event:
                # Different event types (object vs motion) - lower similarity
                return 0.1
            
            # Motion events similarity (original logic)
            # Time overlap similarity
            time_overlap = self._calculate_time_overlap(event1, event2)
            
            # Frame content similarity (use representative frames)
            frame1 = event1.keyframes[0] if event1.keyframes else None
            frame2 = event2.keyframes[0] if event2.keyframes else None
            
            content_similarity = 0.0
            if frame1 and frame2 and os.path.exists(frame1) and os.path.exists(frame2):
                content_similarity = self.similarity_calculator.calculate_combined_similarity(frame1, frame2)
            
            # Motion intensity similarity
            motion_sim = 1.0 - abs(event1.motion_intensity - event2.motion_intensity)
            
            # Combined similarity
            combined_similarity = (
                time_overlap * 0.3 +
                content_similarity * 0.5 +
                motion_sim * 0.2
            )
            
            return combined_similarity
            
        except Exception as e:
            logger.error(f"Event similarity calculation failed: {e}")
            return 0.0
    
    def _calculate_object_event_similarity(self, event1: Event, event2: Event) -> float:
        """Calculate similarity between two object events"""
        try:
            # Object class similarity (must be same class)
            if event1.object_class != event2.object_class:
                return 0.0  # Different object types are not similar
            
            # Time proximity
            time_gap = abs(event1.start_timestamp - event2.start_timestamp)
            time_similarity = max(0.0, 1.0 - (time_gap / self.config.object_event_temporal_window))
            
            # Confidence similarity
            conf_diff = abs(event1.confidence - event2.confidence)
            conf_similarity = max(0.0, 1.0 - conf_diff)
            
            # Detection count similarity
            count_diff = abs(event1.detection_count - event2.detection_count)
            count_similarity = max(0.0, 1.0 - (count_diff / max(event1.detection_count, event2.detection_count, 1)))
            
            # Frame content similarity
            frame1 = event1.keyframes[0] if event1.keyframes else None
            frame2 = event2.keyframes[0] if event2.keyframes else None
            
            content_similarity = 0.0
            if frame1 and frame2 and os.path.exists(frame1) and os.path.exists(frame2):
                content_similarity = self.similarity_calculator.calculate_combined_similarity(frame1, frame2)
            
            # Combined similarity for object events
            combined_similarity = (
                time_similarity * 0.4 +      # Time proximity is important
                content_similarity * 0.3 +    # Visual similarity
                conf_similarity * 0.2 +       # Confidence similarity
                count_similarity * 0.1        # Detection count similarity
            )
            
            return combined_similarity
            
        except Exception as e:
            logger.error(f"Object event similarity calculation failed: {e}")
            return 0.0
    
    def _calculate_time_overlap(self, event1: Event, event2: Event) -> float:
        """Calculate temporal overlap between events"""
        start1, end1 = event1.start_timestamp, event1.end_timestamp
        start2, end2 = event2.start_timestamp, event2.end_timestamp
        
        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start >= overlap_end:
            return 0.0
        
        overlap_duration = overlap_end - overlap_start
        total_duration = max(end1, end2) - min(start1, start2)
        
        return overlap_duration / total_duration if total_duration > 0 else 0.0
    
    def _cluster_similar_events(self, events: List[Event], similarity_matrix: np.ndarray) -> List[List[Event]]:
        """Cluster similar events using similarity threshold"""
        n = len(events)
        visited = [False] * n
        clusters = []
        
        for i in range(n):
            if visited[i]:
                continue
            
            # Start new cluster
            cluster = [events[i]]
            visited[i] = True
            
            # Find similar events
            for j in range(i + 1, n):
                if not visited[j] and similarity_matrix[i, j] >= self.config.similarity_threshold:
                    cluster.append(events[j])
                    visited[j] = True
            
            clusters.append(cluster)
        
        return clusters
    
    def _create_canonical_event(self, cluster: List[Event], event_type: str, 
                              canonical_id: int, cluster_id: int) -> CanonicalEvent:
        """Create canonical event from cluster of similar events"""
        if not cluster:
            raise ValueError("Cannot create canonical event from empty cluster")
        
        # Find representative event (highest importance score)
        representative = max(cluster, key=lambda e: e.importance_score)
        
        # Aggregate properties
        start_time = min(e.start_timestamp for e in cluster)
        end_time = max(e.end_timestamp for e in cluster)
        duration = end_time - start_time
        
        avg_confidence = sum(e.confidence for e in cluster) / len(cluster)
        
        # Collect all keyframes
        all_keyframes = []
        for event in cluster:
            all_keyframes.extend(event.keyframes)
        
        # Remove duplicate frame paths
        unique_keyframes = list(set(all_keyframes))
        
        # Check if this cluster contains object events
        object_events = [e for e in cluster if e.is_object_event]
        contains_objects = len(object_events) > 0
        
        # Object detection summary
        detected_classes = []
        object_summary = None
        threat_level = "low"
        
        if contains_objects:
            # Collect detected object classes
            detected_classes = list(set(e.object_class for e in object_events if e.object_class))
            
            # Calculate object detection summary
            total_detections = sum(e.detection_count for e in object_events)
            max_confidence = max(e.max_confidence for e in object_events)
            avg_obj_confidence = sum(e.confidence for e in object_events) / len(object_events)
            
            object_summary = {
                'total_detections': total_detections,
                'max_confidence': max_confidence,
                'average_confidence': avg_obj_confidence,
                'detected_classes': detected_classes,
                'object_events_count': len(object_events)
            }
            
            # Assess threat level based on object classes and confidence
            threat_level = self._assess_canonical_threat_level(object_events)
        
        # Create enhanced description
        if contains_objects:
            objects_str = ", ".join(detected_classes)
            description = f"{event_type.replace('_', ' ').title()} with {objects_str} detected - {len(cluster)} events aggregated"
        else:
            description = f"{event_type.replace('_', ' ').title()} event aggregated from {len(cluster)} similar events"
        
        canonical_event = CanonicalEvent(
            canonical_id=f"canonical_{canonical_id:04d}",
            event_type=event_type,
            representative_frame=representative.keyframes[0] if representative.keyframes else "",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            confidence=avg_confidence,
            frame_count=len(unique_keyframes),
            aggregated_events=[e.event_id for e in cluster],
            description=description,
            similarity_cluster=cluster_id,
            # Enhanced object detection fields
            contains_objects=contains_objects,
            detected_object_classes=detected_classes,
            object_detection_summary=object_summary,
            threat_level=threat_level
        )
        
        return canonical_event
    
    def _assess_canonical_threat_level(self, object_events: List[Event]) -> str:
        """Assess threat level for canonical event containing object events"""
        if not object_events:
            return "low"
        
        # Get highest threat level from individual events
        threat_levels = ["low", "medium", "high", "critical"]
        max_threat_index = 0
        
        for event in object_events:
            event_threat = self._assess_individual_threat_level(event)
            threat_index = threat_levels.index(event_threat) if event_threat in threat_levels else 0
            max_threat_index = max(max_threat_index, threat_index)
        
        # Additional factors for canonical events
        max_confidence = max(e.max_confidence for e in object_events)
        total_detections = sum(e.detection_count for e in object_events)
        unique_classes = len(set(e.object_class for e in object_events))
        
        # Escalate threat if multiple factors present
        if unique_classes > 1:  # Multiple types of objects detected
            max_threat_index = min(max_threat_index + 1, len(threat_levels) - 1)
        
        if total_detections > 10:  # Many detections
            max_threat_index = min(max_threat_index + 1, len(threat_levels) - 1)
        
        if max_confidence > 0.9:  # Very high confidence
            max_threat_index = min(max_threat_index + 1, len(threat_levels) - 1)
        
        return threat_levels[max_threat_index]
    
    def _assess_individual_threat_level(self, event: Event) -> str:
        """Assess threat level for individual event (duplicate of EventDetector method)"""
        if not event.is_object_event:
            # For motion events, use motion intensity and burst activity
            if event.event_type == "high_motion" and event.motion_intensity > 0.015:
                return "medium"
            elif event.event_type == "burst_activity":
                return "medium"
            else:
                return "low"
        
        # Object-based threat assessment
        threat_map = {
            'fire': {
                'low': 0.3,      # Confidence thresholds
                'medium': 0.5,
                'high': 0.7,
                'critical': 0.85
            },
            'gun': {
                'low': 0.4,
                'medium': 0.6,
                'high': 0.8,
                'critical': 0.9
            },
            'knife': {
                'low': 0.4,
                'medium': 0.6,
                'high': 0.75,
                'critical': 0.85
            }
        }
        
        obj_class = event.object_class.lower()
        confidence = event.max_confidence
        
        if obj_class in threat_map:
            thresholds = threat_map[obj_class]
            if confidence >= thresholds['critical']:
                return "critical"
            elif confidence >= thresholds['high']:
                return "high"
            elif confidence >= thresholds['medium']:
                return "medium"
            else:
                return "low"
        
        return "medium"  # Default for unknown object types
    
    def save_canonical_events(self, canonical_events: List[CanonicalEvent], 
                            output_path: str) -> bool:
        """Save canonical events to JSON file"""
        try:
            # Convert to serializable format
            events_data = {
                'metadata': {
                    'total_canonical_events': len(canonical_events),
                    'generation_timestamp': datetime.now().isoformat(),
                    'deduplication_threshold': self.config.similarity_threshold
                },
                'canonical_events': [asdict(event) for event in canonical_events]
            }
            
            with open(output_path, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.info(f"Canonical events saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save canonical events: {e}")
            return False
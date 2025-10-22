"""
DetectifAI Security Event System

This module defines the specific security event types and processing logic
according to DetectifAI's scope: assault/fighting, weapons, fire, jumping over wall,
road accidents, and suspicious person re-occurrence.
"""

import os
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

class DetectifAIEventType(Enum):
    """DetectifAI-specific security event types"""
    FIRE_DETECTION = "fire_detection"
    WEAPON_DETECTION = "weapon_detection"  # knife, gun
    PHYSICAL_ASSAULT = "physical_assault"  # fighting, violence
    WALL_JUMPING = "wall_jumping"         # perimeter breach
    ROAD_ACCIDENT = "road_accident"       # vehicle collision
    SUSPICIOUS_PERSON_REOCCURRENCE = "suspicious_person_reoccurrence"
    GENERAL_MOTION = "general_motion"     # fallback for unclassified motion

class ThreatLevel(Enum):
    """Security threat levels for DetectifAI events"""
    CRITICAL = "critical"  # Immediate response required (fire, weapons)
    HIGH = "high"         # Urgent attention needed (assault, suspicious person)
    MEDIUM = "medium"     # Monitor closely (wall jumping, accidents)
    LOW = "low"          # General awareness (motion)

@dataclass
class DetectifAIEvent:
    """Enhanced event structure specific to DetectifAI security requirements"""
    event_id: str
    event_type: DetectifAIEventType
    threat_level: ThreatLevel
    start_timestamp: float
    end_timestamp: float
    duration: float
    confidence: float
    
    # Location and detection details
    keyframes: List[str]
    detection_details: Dict[str, Any]  # Specific to event type
    
    # Security-specific fields
    requires_immediate_response: bool
    investigation_priority: int  # 1-10 scale
    
    # Person tracking (for applicable events)
    persons_detected: List[Dict] = None
    is_person_reoccurrence: bool = False
    
    # Context and description
    description: str = ""
    security_notes: str = ""
    
    # Metadata
    processing_timestamp: float = None
    detection_model_used: str = ""

@dataclass
class DetectifAICanonicalEvent:
    """Canonical representation of aggregated DetectifAI security events"""
    canonical_id: str
    event_type: DetectifAIEventType
    threat_level: ThreatLevel
    
    # Temporal information
    start_time: float
    end_time: float
    total_duration: float
    
    # Aggregation details
    aggregated_events_count: int
    aggregated_event_ids: List[str]
    representative_frame: str
    all_keyframes: List[str]
    
    # Security assessment
    max_confidence: float
    average_confidence: float
    investigation_priority: int
    requires_immediate_response: bool
    
    # Detection summary
    total_detections: int
    detection_summary: Dict[str, Any]
    
    # Person tracking summary
    unique_persons_count: int = 0
    suspicious_persons: List[Dict] = None
    person_reoccurrences: int = 0
    
    # Investigation details
    description: str = ""
    security_assessment: str = ""
    recommended_actions: List[str] = None

class DetectifAIEventProcessor:
    """Process and classify events according to DetectifAI security requirements"""
    
    def __init__(self, config):
        self.config = config
        
        # DetectifAI-specific thresholds
        self.threat_thresholds = {
            DetectifAIEventType.FIRE_DETECTION: {
                ThreatLevel.CRITICAL: 0.7,
                ThreatLevel.HIGH: 0.5,
                ThreatLevel.MEDIUM: 0.3,
                ThreatLevel.LOW: 0.1
            },
            DetectifAIEventType.WEAPON_DETECTION: {
                ThreatLevel.CRITICAL: 0.8,
                ThreatLevel.HIGH: 0.6,
                ThreatLevel.MEDIUM: 0.4,
                ThreatLevel.LOW: 0.2
            },
            DetectifAIEventType.PHYSICAL_ASSAULT: {
                ThreatLevel.CRITICAL: 0.9,
                ThreatLevel.HIGH: 0.7,
                ThreatLevel.MEDIUM: 0.5,
                ThreatLevel.LOW: 0.3
            },
            DetectifAIEventType.WALL_JUMPING: {
                ThreatLevel.HIGH: 0.8,
                ThreatLevel.MEDIUM: 0.6,
                ThreatLevel.LOW: 0.4
            },
            DetectifAIEventType.ROAD_ACCIDENT: {
                ThreatLevel.HIGH: 0.8,
                ThreatLevel.MEDIUM: 0.6,
                ThreatLevel.LOW: 0.4
            },
            DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE: {
                ThreatLevel.HIGH: 0.9,
                ThreatLevel.MEDIUM: 0.7,
                ThreatLevel.LOW: 0.5
            }
        }
        
        # Processing statistics
        self.processing_stats = {
            'motion_events_processed': 0,
            'object_events_processed': 0,
            'detectifai_events_created': 0,
            'facial_recognition_events': 0,
            'placeholder_events_created': 0
        }
        
        logger.info("DetectifAI Event Processor initialized")
    
    def process_security_events(self, keyframes: List, motion_events: List, object_events: List = None) -> List[DetectifAIEvent]:
        """Main method to process all security events and convert to DetectifAI format"""
        logger.info("🔍 Processing security events for DetectifAI system")
        
        detectifai_events = []
        
        # Convert object detection events
        if object_events:
            object_detectifai_events = self.convert_object_detection_to_detectifai_events(object_events)
            detectifai_events.extend(object_detectifai_events)
            self.processing_stats['object_events_processed'] = len(object_events)
        
        # Create placeholder events from motion
        placeholder_events = self.create_placeholder_events(keyframes, motion_events)
        detectifai_events.extend(placeholder_events)
        self.processing_stats['motion_events_processed'] = len(motion_events)
        self.processing_stats['placeholder_events_created'] = len(placeholder_events)
        
        # Update final count
        self.processing_stats['detectifai_events_created'] = len(detectifai_events)
        
        logger.info(f"✅ DetectifAI processing complete: {len(detectifai_events)} security events created")
        return detectifai_events
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.processing_stats.copy()
    
    def convert_object_detection_to_detectifai_events(self, object_events: List[Dict]) -> List[DetectifAIEvent]:
        """Convert object detection events to DetectifAI security events"""
        detectifai_events = []
        
        for obj_event in object_events:
            # Determine DetectifAI event type
            object_class = obj_event.get('object_class', '').lower()
            
            if object_class == 'fire':
                event_type = DetectifAIEventType.FIRE_DETECTION
            elif object_class in ['knife', 'gun']:
                event_type = DetectifAIEventType.WEAPON_DETECTION
            else:
                event_type = DetectifAIEventType.GENERAL_MOTION
            
            # Assess threat level
            confidence = obj_event.get('confidence', 0.0)
            threat_level = self._assess_threat_level(event_type, confidence)
            
            # Create DetectifAI event
            detectifai_event = DetectifAIEvent(
                event_id=f"detectifai_{obj_event['event_id']}",
                event_type=event_type,
                threat_level=threat_level,
                start_timestamp=obj_event['start_timestamp'],
                end_timestamp=obj_event['end_timestamp'],
                duration=obj_event['end_timestamp'] - obj_event['start_timestamp'],
                confidence=confidence,
                keyframes=obj_event.get('keyframes', []),
                detection_details={
                    'object_class': object_class,
                    'detection_count': obj_event.get('detection_count', 0),
                    'max_confidence': obj_event.get('max_confidence', confidence),
                    'detection_data': obj_event.get('detection_details', [])
                },
                requires_immediate_response=threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH],
                investigation_priority=self._calculate_investigation_priority(event_type, threat_level, confidence),
                description=self._generate_detectifai_description(event_type, object_class, confidence),
                processing_timestamp=time.time(),
                detection_model_used=f"object_detection_{object_class}"
            )
            
            detectifai_events.append(detectifai_event)
        
        logger.info(f"Converted {len(object_events)} object events to {len(detectifai_events)} DetectifAI events")
        return detectifai_events
    
    def create_placeholder_events(self, keyframes: List, motion_events: List) -> List[DetectifAIEvent]:
        """Create placeholder events for unimplemented DetectifAI modules"""
        placeholder_events = []
        
        # Convert high-motion events to potential security events (placeholders)
        for motion_event in motion_events:
            if hasattr(motion_event, 'motion_intensity') and motion_event.motion_intensity > 0.015:
                # High motion could be assault/fighting (placeholder)
                placeholder_event = DetectifAIEvent(
                    event_id=f"placeholder_assault_{motion_event.event_id}",
                    event_type=DetectifAIEventType.PHYSICAL_ASSAULT,
                    threat_level=ThreatLevel.MEDIUM,  # Conservative for placeholder
                    start_timestamp=motion_event.start_timestamp,
                    end_timestamp=motion_event.end_timestamp,
                    duration=motion_event.end_timestamp - motion_event.start_timestamp,
                    confidence=0.5,  # Placeholder confidence
                    keyframes=motion_event.keyframes,
                    detection_details={
                        'placeholder': True,
                        'motion_intensity': motion_event.motion_intensity,
                        'original_event_type': motion_event.event_type
                    },
                    requires_immediate_response=False,
                    investigation_priority=5,
                    description=f"Potential physical assault detected (placeholder) - High motion intensity: {motion_event.motion_intensity:.3f}",
                    security_notes="PLACEHOLDER: Requires fight detection module implementation",
                    processing_timestamp=time.time(),
                    detection_model_used="placeholder_fight_detection"
                )
                placeholder_events.append(placeholder_event)
        
        # Add other placeholder event types based on analysis
        # Wall jumping, road accidents, etc. can be added here based on scene analysis
        
        logger.info(f"Created {len(placeholder_events)} placeholder DetectifAI events")
        return placeholder_events
    
    def _assess_threat_level(self, event_type: DetectifAIEventType, confidence: float) -> ThreatLevel:
        """Assess threat level based on event type and confidence"""
        if event_type not in self.threat_thresholds:
            return ThreatLevel.LOW
        
        thresholds = self.threat_thresholds[event_type]
        
        for threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH, ThreatLevel.MEDIUM, ThreatLevel.LOW]:
            if threat_level in thresholds and confidence >= thresholds[threat_level]:
                return threat_level
        
        return ThreatLevel.LOW
    
    def _calculate_investigation_priority(self, event_type: DetectifAIEventType, 
                                        threat_level: ThreatLevel, confidence: float) -> int:
        """Calculate investigation priority (1-10 scale)"""
        base_priorities = {
            DetectifAIEventType.FIRE_DETECTION: 9,
            DetectifAIEventType.WEAPON_DETECTION: 8,
            DetectifAIEventType.PHYSICAL_ASSAULT: 7,
            DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE: 6,
            DetectifAIEventType.WALL_JUMPING: 5,
            DetectifAIEventType.ROAD_ACCIDENT: 4,
            DetectifAIEventType.GENERAL_MOTION: 2
        }
        
        base_priority = base_priorities.get(event_type, 2)
        
        # Adjust based on threat level
        threat_multipliers = {
            ThreatLevel.CRITICAL: 1.0,
            ThreatLevel.HIGH: 0.9,
            ThreatLevel.MEDIUM: 0.7,
            ThreatLevel.LOW: 0.5
        }
        
        adjusted_priority = int(base_priority * threat_multipliers[threat_level])
        
        # Boost for high confidence
        if confidence > 0.8:
            adjusted_priority = min(10, adjusted_priority + 1)
        
        return max(1, min(10, adjusted_priority))
    
    def _generate_detectifai_description(self, event_type: DetectifAIEventType, 
                                       object_class: str, confidence: float) -> str:
        """Generate DetectifAI-specific event descriptions"""
        descriptions = {
            DetectifAIEventType.FIRE_DETECTION: f"🔥 Fire detected with {confidence:.1%} confidence - Immediate evacuation may be required",
            DetectifAIEventType.WEAPON_DETECTION: f"⚠️ Weapon ({object_class}) detected with {confidence:.1%} confidence - Security alert triggered",
            DetectifAIEventType.PHYSICAL_ASSAULT: f"👊 Physical assault detected with {confidence:.1%} confidence - Intervention may be needed",
            DetectifAIEventType.WALL_JUMPING: f"🧗 Perimeter breach (wall jumping) detected with {confidence:.1%} confidence",
            DetectifAIEventType.ROAD_ACCIDENT: f"🚗 Road accident detected with {confidence:.1%} confidence - Emergency services may be needed",
            DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE: f"👤 Suspicious person re-occurrence detected with {confidence:.1%} confidence",
            DetectifAIEventType.GENERAL_MOTION: f"📊 General motion activity detected"
        }
        
        return descriptions.get(event_type, f"Security event detected: {event_type.value}")

class DetectifAIEventAggregator:
    """Simplified event aggregation focused on DetectifAI security requirements"""
    
    def __init__(self, config):
        self.config = config
        self.temporal_window = getattr(config, 'detectifai_temporal_window', 10.0)  # seconds
        
    def aggregate_detectifai_events(self, events: List[DetectifAIEvent]) -> List[DetectifAICanonicalEvent]:
        """Aggregate DetectifAI events into canonical security events"""
        logger.info(f"Aggregating {len(events)} DetectifAI events")
        
        if not events:
            return []
        
        # Group events by type for focused aggregation
        events_by_type = {}
        for event in events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)
        
        canonical_events = []
        canonical_id_counter = 1
        
        # Process each event type separately with DetectifAI-specific logic
        for event_type, type_events in events_by_type.items():
            type_canonical = self._aggregate_by_detectifai_type(
                event_type, type_events, canonical_id_counter
            )
            canonical_events.extend(type_canonical)
            canonical_id_counter += len(type_canonical)
        
        # Sort by investigation priority
        canonical_events.sort(key=lambda e: e.investigation_priority, reverse=True)
        
        logger.info(f"Created {len(canonical_events)} canonical DetectifAI events")
        return canonical_events
    
    def _aggregate_by_detectifai_type(self, event_type: DetectifAIEventType, 
                                    events: List[DetectifAIEvent], 
                                    start_id: int) -> List[DetectifAICanonicalEvent]:
        """Aggregate events of specific DetectifAI type"""
        if not events:
            return []
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.start_timestamp)
        
        # Group events within temporal window
        clusters = []
        current_cluster = [events[0]]
        
        for i in range(1, len(events)):
            current_event = events[i]
            last_in_cluster = current_cluster[-1]
            
            # Check if events should be clustered
            time_gap = current_event.start_timestamp - last_in_cluster.end_timestamp
            
            if time_gap <= self.temporal_window:
                current_cluster.append(current_event)
            else:
                clusters.append(current_cluster)
                current_cluster = [current_event]
        
        # Don't forget the last cluster
        if current_cluster:
            clusters.append(current_cluster)
        
        # Create canonical events from clusters
        canonical_events = []
        for i, cluster in enumerate(clusters):
            canonical_event = self._create_detectifai_canonical_event(
                event_type, cluster, start_id + i
            )
            canonical_events.append(canonical_event)
        
        return canonical_events
    
    def _create_detectifai_canonical_event(self, event_type: DetectifAIEventType, 
                                         cluster: List[DetectifAIEvent], 
                                         canonical_id: int) -> DetectifAICanonicalEvent:
        """Create canonical event from DetectifAI event cluster"""
        # Find highest priority event as representative
        representative = max(cluster, key=lambda e: e.investigation_priority)
        
        # Aggregate temporal information
        start_time = min(e.start_timestamp for e in cluster)
        end_time = max(e.end_timestamp for e in cluster)
        total_duration = end_time - start_time
        
        # Aggregate confidence and priority
        max_confidence = max(e.confidence for e in cluster)
        avg_confidence = sum(e.confidence for e in cluster) / len(cluster)
        max_priority = max(e.investigation_priority for e in cluster)
        
        # Collect all keyframes
        all_keyframes = []
        for event in cluster:
            all_keyframes.extend(event.keyframes)
        unique_keyframes = list(set(all_keyframes))
        
        # Aggregate detection information
        total_detections = sum(
            event.detection_details.get('detection_count', 1) for event in cluster
        )
        
        # Determine if immediate response required
        requires_immediate_response = any(e.requires_immediate_response for e in cluster)
        
        # Get highest threat level
        threat_levels = [ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        max_threat_level = max((e.threat_level for e in cluster), key=lambda t: threat_levels.index(t))
        
        # Create detection summary
        detection_summary = {
            'total_events_aggregated': len(cluster),
            'detection_methods': list(set(e.detection_model_used for e in cluster)),
            'confidence_range': {
                'min': min(e.confidence for e in cluster),
                'max': max_confidence,
                'average': avg_confidence
            },
            'detection_details': [e.detection_details for e in cluster]
        }
        
        # Generate description and assessment
        description = self._generate_canonical_description(event_type, cluster, max_confidence)
        security_assessment = self._generate_security_assessment(event_type, max_threat_level, len(cluster))
        recommended_actions = self._get_recommended_actions(event_type, max_threat_level)
        
        canonical_event = DetectifAICanonicalEvent(
            canonical_id=f"detectifai_canonical_{canonical_id:04d}",
            event_type=event_type,
            threat_level=max_threat_level,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            aggregated_events_count=len(cluster),
            aggregated_event_ids=[e.event_id for e in cluster],
            representative_frame=representative.keyframes[0] if representative.keyframes else "",
            all_keyframes=unique_keyframes,
            max_confidence=max_confidence,
            average_confidence=avg_confidence,
            investigation_priority=max_priority,
            requires_immediate_response=requires_immediate_response,
            total_detections=total_detections,
            detection_summary=detection_summary,
            description=description,
            security_assessment=security_assessment,
            recommended_actions=recommended_actions
        )
        
        return canonical_event
    
    def _generate_canonical_description(self, event_type: DetectifAIEventType, 
                                      cluster: List[DetectifAIEvent], confidence: float) -> str:
        """Generate description for canonical DetectifAI event"""
        event_count = len(cluster)
        duration = max(e.end_timestamp for e in cluster) - min(e.start_timestamp for e in cluster)
        
        base_descriptions = {
            DetectifAIEventType.FIRE_DETECTION: f"Fire incident - {event_count} detections over {duration:.1f}s",
            DetectifAIEventType.WEAPON_DETECTION: f"Weapon threat - {event_count} detections over {duration:.1f}s",
            DetectifAIEventType.PHYSICAL_ASSAULT: f"Physical assault incident - {event_count} events over {duration:.1f}s",
            DetectifAIEventType.WALL_JUMPING: f"Perimeter breach - {event_count} wall jumping events over {duration:.1f}s",
            DetectifAIEventType.ROAD_ACCIDENT: f"Road accident - {event_count} incidents over {duration:.1f}s",
            DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE: f"Suspicious person alert - {event_count} re-occurrences",
            DetectifAIEventType.GENERAL_MOTION: f"Motion activity - {event_count} events over {duration:.1f}s"
        }
        
        return base_descriptions.get(event_type, f"Security event: {event_type.value}")
    
    def _generate_security_assessment(self, event_type: DetectifAIEventType, 
                                    threat_level: ThreatLevel, event_count: int) -> str:
        """Generate security assessment for canonical event"""
        assessments = {
            (DetectifAIEventType.FIRE_DETECTION, ThreatLevel.CRITICAL): "CRITICAL: Immediate evacuation and fire response required",
            (DetectifAIEventType.WEAPON_DETECTION, ThreatLevel.CRITICAL): "CRITICAL: Armed threat present - immediate security intervention",
            (DetectifAIEventType.PHYSICAL_ASSAULT, ThreatLevel.HIGH): "HIGH: Violence in progress - security response needed",
            (DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE, ThreatLevel.HIGH): "HIGH: Known suspicious individual returned - monitor closely"
        }
        
        specific_assessment = assessments.get((event_type, threat_level))
        if specific_assessment:
            return specific_assessment
        
        # Generic assessment based on threat level
        generic_assessments = {
            ThreatLevel.CRITICAL: f"CRITICAL threat level - immediate response required",
            ThreatLevel.HIGH: f"HIGH priority security event - urgent attention needed", 
            ThreatLevel.MEDIUM: f"MEDIUM priority - monitor and assess situation",
            ThreatLevel.LOW: f"LOW priority - general awareness sufficient"
        }
        
        return generic_assessments.get(threat_level, "Security event requires assessment")
    
    def _get_recommended_actions(self, event_type: DetectifAIEventType, 
                               threat_level: ThreatLevel) -> List[str]:
        """Get recommended actions for DetectifAI event types"""
        actions_map = {
            DetectifAIEventType.FIRE_DETECTION: [
                "Verify fire location and extent",
                "Initiate evacuation procedures if confirmed",
                "Contact fire department",
                "Monitor spread and safety of personnel"
            ],
            DetectifAIEventType.WEAPON_DETECTION: [
                "Verify weapon type and threat level",
                "Alert security personnel immediately",
                "Consider lockdown procedures",
                "Contact law enforcement if confirmed threat"
            ],
            DetectifAIEventType.PHYSICAL_ASSAULT: [
                "Assess severity of altercation",
                "Dispatch security to location",
                "Consider medical assistance",
                "Document incident for investigation"
            ],
            DetectifAIEventType.WALL_JUMPING: [
                "Verify perimeter breach",
                "Check intruder location and intent",
                "Review security footage",
                "Assess security protocol effectiveness"
            ],
            DetectifAIEventType.ROAD_ACCIDENT: [
                "Assess severity of accident",
                "Check for injuries",
                "Contact emergency services if needed",
                "Manage traffic flow around incident"
            ],
            DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE: [
                "Review person's previous incidents",
                "Monitor current activities closely",
                "Alert security personnel",
                "Consider preventive measures"
            ]
        }
        
        base_actions = actions_map.get(event_type, ["Monitor situation", "Assess threat level", "Take appropriate action"])
        
        # Add threat-level specific actions
        if threat_level == ThreatLevel.CRITICAL:
            base_actions.insert(0, "IMMEDIATE ACTION REQUIRED")
        elif threat_level == ThreatLevel.HIGH:
            base_actions.insert(0, "URGENT: Prioritize response")
        
        return base_actions
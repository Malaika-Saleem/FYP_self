"""
Configuration settings for the Video Event Detection and Preprocessing Pipeline.

This file contains all configurable parameters that can be tweaked to control:
- Keyframe extraction sensitivity
- Event detection thresholds
- Video quality settings
- Output formats and paths
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class VideoProcessingConfig:
    """Main configuration class for video processing pipeline"""
    
    # ===== KEYFRAME EXTRACTION PARAMETERS =====
    # Control how many keyframes are extracted
    
    # Base quality threshold (0.1-0.3): Lower = more keyframes, Higher = fewer but better quality
    base_quality_threshold: float = 0.15
    
    # Motion detection threshold (0.005-0.02): Lower = more motion-sensitive, Higher = only significant motion
    motion_threshold: float = 0.008
    
    # Burst sampling rate (1-10): Higher = more frames during high activity periods
    burst_sampling_rate: int = 3
    
    # Frame sampling interval in seconds (0.5-3.0): Lower = more frequent sampling
    frame_sampling_interval: float = 1.0
    
    # ===== EVENT DETECTION PARAMETERS =====
    # Control how events are detected and prioritized
    
    # Event importance threshold (0.2-0.5): Lower = more events detected
    event_importance_threshold: float = 0.25
    
    # Burst activity weight (1.5-3.0): Higher = burst frames get higher priority
    burst_weight: float = 2.5
    
    # Temporal clustering window in seconds (10-30): Frames within this window are clustered
    temporal_clustering_window: float = 15.0
    
    # Scene change detection threshold (0.01-0.05): Lower = more scene changes detected
    scene_change_threshold: float = 0.02
    
    # ===== VIDEO SEGMENTATION PARAMETERS =====
    # Control how video is divided into segments
    
    # Segment duration in seconds (30-60): Length of each temporal segment
    segment_duration: float = 45.0
    
    # Keyframes per segment (3-8): How many keyframes to extract per segment
    keyframes_per_segment: int = 5
    
    # ===== HIGHLIGHT REEL PARAMETERS =====
    # Control the final summary video creation
    
    # Maximum summary duration in seconds (15-60): Total length of highlight reel
    max_summary_duration: float = 25.0
    
    # Frame display duration in seconds (0.5-3.0): How long each frame is shown
    frame_display_duration: float = 1.5
    
    # Maximum frames in summary (10-30): Total number of frames in highlight reel
    max_summary_frames: int = 18
    
    # Summary video FPS (0.4-1.0): Playback speed of summary
    summary_fps: float = 0.6
    
    # ===== DEDUPLICATION PARAMETERS =====
    # Control duplicate frame removal
    
    # Similarity threshold (0.80-0.95): Higher = stricter deduplication
    similarity_threshold: float = 0.85
    
    # Minimum time gap between frames in seconds (1-5): Prevents frames too close in time
    min_frame_gap: float = 2.0
    
    # ===== COMPRESSION PARAMETERS =====
    # Control video compression settings
    
    # Output resolution (720p, 1080p, or original)
    output_resolution: str = "720p"
    
    # Compression quality (18-28): Lower = better quality, larger files
    compression_crf: int = 23
    
    # Compression preset (ultrafast, fast, medium, slow): Affects encoding speed vs efficiency
    compression_preset: str = "fast"
    
    # ===== ADAPTIVE ENHANCEMENT PARAMETERS =====
    # Control image enhancement
    
    # Enable adaptive histogram equalization
    enable_clahe: bool = True
    
    # CLAHE clip limit (1.0-4.0): Higher = more contrast enhancement
    clahe_clip_limit: float = 2.0
    
    # Enable denoising
    enable_denoising: bool = True
    
    # Denoising strength (3-10): Higher = more denoising
    denoise_strength: int = 5
    
    # ===== OUTPUT SETTINGS =====
    # Control output files and formats
    
    # Base output directory
    output_base_dir: str = "video_processing_outputs"
    
    # Enable various output formats
    generate_json_reports: bool = True
    generate_html_gallery: bool = True
    generate_compressed_video: bool = True
    generate_segments: bool = True
    generate_highlight_reels: bool = False  # Disabled for security focus - saves processing time
    
    # Video output format (mp4, avi, mov)
    video_output_format: str = "mp4"
    
    # ===== ADVANCED PARAMETERS =====
    # Fine-tuning for specific use cases
    
    # Enable GPU acceleration if available
    use_gpu_acceleration: bool = True
    
    # Enable face detection for human-centric events
    enable_face_detection: bool = False
    
    # Enable object detection for context-aware processing
    enable_object_detection: bool = False
    
    # Enable facial recognition for suspicious person tracking (FULL implementation with FAISS + MongoDB)
    enable_facial_recognition: bool = True
    
    # Face recognition confidence threshold (0.5-0.95)
    face_recognition_confidence: float = 0.7
    
    # Face detection model to use (MTCNN for detection, FaceNet for embeddings)
    face_detection_model: str = "mtcnn"
    
    # Face recognition model to use (InceptionResnetV1 with FAISS similarity search)
    face_recognition_model: str = "facenet_faiss"
    
    # Enable suspicious person database and tracking
    suspicious_person_tracking: bool = True
    
    # Face database settings
    face_database_enabled: bool = True
    
    # ===== OBJECT DETECTION PARAMETERS =====
    # Configuration for fire, knife, gun detection
    
    # Models directory path (relative to backend directory when running from project root)
    models_dir: str = os.path.join(os.path.dirname(__file__), "models")
    
    # Object detection confidence threshold (0.1-0.9)
    object_detection_confidence: float = 0.5
    
    # Temporal window for grouping object detections into events (seconds)
    object_event_temporal_window: float = 5.0
    
    # Enable annotation of detected objects on keyframes
    enable_object_annotation: bool = True
    
    # Object detection specific thresholds
    fire_detection_confidence: float = 0.4     # Lower threshold for fire (safety critical)
    weapon_detection_confidence: float = 0.6   # Higher threshold for weapons (reduce false positives)
    
    # Enable specific object types
    enable_fire_detection: bool = True
    enable_weapon_detection: bool = True
    
    # Object event importance multiplier
    object_event_importance_multiplier: float = 2.0
    
    # ===== BEHAVIOR ANALYSIS PARAMETERS =====
    # Configuration for behavior/action recognition (fighting, accidents, climbing)
    
    # Enable behavior analysis
    enable_behavior_analysis: bool = False
    
    # Behavior analysis models directory
    behavior_models_dir: str = os.path.join(os.path.dirname(__file__), "behavior_analysis")
    
    # Behavior detection confidence threshold (0.3-0.8)
    behavior_detection_confidence: float = 0.5
    
    # Temporal window for grouping behavior detections into events (seconds)
    behavior_event_temporal_window: float = 5.0
    
    # Behavior event importance multiplier
    behavior_event_importance_multiplier: float = 2.5
    
    # Enable specific behavior types
    enable_fighting_detection: bool = True
    enable_accident_detection: bool = True
    enable_climbing_detection: bool = True
    
    # Parallel processing workers (1-8): More workers = faster but more memory
    num_workers: int = 4

    def __post_init__(self):
        """Validate configuration parameters"""
        # Ensure output directory exists
        os.makedirs(self.output_base_dir, exist_ok=True)
        
        # Validate thresholds
        assert 0.1 <= self.base_quality_threshold <= 0.3, "Quality threshold must be between 0.1-0.3"
        assert 0.005 <= self.motion_threshold <= 0.02, "Motion threshold must be between 0.005-0.02"
        assert 0.8 <= self.similarity_threshold <= 0.95, "Similarity threshold must be between 0.8-0.95"

# ===== PRESET CONFIGURATIONS =====

def get_high_recall_config() -> VideoProcessingConfig:
    """Configuration optimized for capturing more events (more keyframes)"""
    return VideoProcessingConfig(
        base_quality_threshold=0.12,      # Lower quality threshold
        motion_threshold=0.005,           # Very sensitive motion detection
        event_importance_threshold=0.20,   # Lower event threshold
        max_summary_frames=25,            # More frames in summary
        frame_sampling_interval=0.8,      # More frequent sampling
        temporal_clustering_window=20.0,   # Wider clustering window
        burst_weight=3.0,                 # Higher burst priority
        keyframes_per_segment=6           # More keyframes per segment
    )

def get_high_precision_config() -> VideoProcessingConfig:
    """Configuration optimized for quality over quantity (fewer but better keyframes)"""
    return VideoProcessingConfig(
        base_quality_threshold=0.20,      # Higher quality threshold
        motion_threshold=0.015,           # Less sensitive motion detection
        event_importance_threshold=0.35,   # Higher event threshold
        max_summary_frames=12,            # Fewer frames in summary
        frame_sampling_interval=1.5,      # Less frequent sampling
        temporal_clustering_window=10.0,   # Tighter clustering
        burst_weight=2.0,                 # Moderate burst priority
        keyframes_per_segment=4           # Fewer keyframes per segment
    )

def get_balanced_config() -> VideoProcessingConfig:
    """Balanced configuration for general use"""
    return VideoProcessingConfig()  # Uses default values

# Removed robbery detection config - using security_focused_config instead

def get_security_focused_config() -> VideoProcessingConfig:
    """Configuration optimized specifically for security and threat detection"""
    return VideoProcessingConfig(
        base_quality_threshold=0.12,
        motion_threshold=0.005,           # Very sensitive
        event_importance_threshold=0.20,
        burst_weight=3.0,                 # Highest priority for burst activity
        temporal_clustering_window=20.0,
        max_summary_frames=25,
        frame_display_duration=2.0,
        similarity_threshold=0.82,
        enable_clahe=True,
        clahe_clip_limit=3.0,
        # Enhanced object detection for security
        enable_object_detection=True,
        object_detection_confidence=0.4,  # Lower threshold for better recall
        fire_detection_confidence=0.3,    # Very sensitive for fire
        weapon_detection_confidence=0.5,  # Balanced for weapons
        object_event_temporal_window=8.0, # Longer window for complex events
        enable_object_annotation=True,
        object_event_importance_multiplier=3.0,  # High importance for security events
        # Enhanced behavior analysis for security
        enable_behavior_analysis=True,
        behavior_detection_confidence=0.4,  # Lower threshold for better recall
        behavior_event_temporal_window=8.0,  # Longer window for complex events
        behavior_event_importance_multiplier=3.0  # High importance for security events
    )

# ===== PARAMETER ADJUSTMENT GUIDE =====

PARAMETER_GUIDE = {
    "More Keyframes": {
        "base_quality_threshold": "Decrease (0.10-0.12)",
        "motion_threshold": "Decrease (0.005-0.008)",
        "event_importance_threshold": "Decrease (0.20-0.25)",
        "max_summary_frames": "Increase (20-30)",
        "keyframes_per_segment": "Increase (6-8)",
        "frame_sampling_interval": "Decrease (0.5-1.0)"
    },
    "Fewer Keyframes": {
        "base_quality_threshold": "Increase (0.18-0.25)",
        "motion_threshold": "Increase (0.012-0.020)",
        "event_importance_threshold": "Increase (0.30-0.40)",
        "max_summary_frames": "Decrease (8-15)",
        "keyframes_per_segment": "Decrease (3-4)",
        "frame_sampling_interval": "Increase (1.5-2.5)"
    },
    "Better Quality": {
        "base_quality_threshold": "Increase (0.18-0.25)",
        "compression_crf": "Decrease (18-20)",
        "enable_clahe": "True",
        "enable_denoising": "True",
        "output_resolution": "'1080p'"
    },
    "Faster Processing": {
        "compression_preset": "'ultrafast'",
        "num_workers": "Increase (6-8)",
        "enable_face_detection": "False",
        "enable_object_detection": "False",
        "keyframes_per_segment": "Decrease (3-4)"
    },
    "More Sensitive Event Detection": {
        "motion_threshold": "Decrease (0.005-0.008)",
        "burst_weight": "Increase (2.5-3.0)",
        "event_importance_threshold": "Decrease (0.20-0.25)",
        "temporal_clustering_window": "Increase (15-25)"
    }
}

def print_parameter_guide():
    """Print parameter adjustment guide"""
    print("🔧 VIDEO PROCESSING PARAMETER ADJUSTMENT GUIDE")
    print("=" * 60)
    
    for goal, params in PARAMETER_GUIDE.items():
        print(f"\n🎯 {goal}:")
        for param, adjustment in params.items():
            print(f"   • {param}: {adjustment}")
    
    print(f"\n📝 Available Preset Configurations:")
    print(f"   • get_high_recall_config() - More keyframes, sensitive detection")
    print(f"   • get_high_precision_config() - Fewer but higher quality keyframes")
    print(f"   • get_balanced_config() - General purpose settings")
    print(f"   • get_security_focused_config() - Optimized for security/threat detection")

if __name__ == "__main__":
    print_parameter_guide()
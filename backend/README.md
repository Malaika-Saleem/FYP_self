# Video Event Detection and Preprocessing Pipeline

A comprehensive Python pipeline for video preprocessing, event detection, aggregation, deduplication, and highlight reel generation. This system is designed to automatically process videos and extract meaningful events while creating high-quality summaries.

## 🚀 Features

### Core Processing
- **Adaptive Frame Enhancement** - CLAHE contrast enhancement and noise reduction
- **Intelligent Keyframe Extraction** - Motion-aware sampling with quality assessment
- **Event Detection & Aggregation** - Automatic detection of high-activity periods
- **Smart Deduplication** - Remove similar frames using multiple similarity metrics
- **Temporal Segmentation** - Divide video into meaningful temporal segments

### Output Generation
- **Multiple Highlight Reels** - Event-aware, comprehensive, and quality-focused summaries
- **Video Compression** - Configurable quality and resolution settings
- **Comprehensive Reports** - JSON reports with detailed statistics
- **Interactive HTML Gallery** - Visual browser-based results viewer
- **Segment Analysis** - Individual segment metadata and keyframes

### Advanced Features
- **Configurable Parameters** - Easily adjust sensitivity and quality thresholds
- **Multiple Processing Modes** - Robbery detection, high-recall, precision-focused
- **Burst Detection** - Identify periods of intense activity
- **Quality Assessment** - Multi-metric frame quality evaluation
- **Performance Monitoring** - Detailed timing and memory usage statistics

## 📦 Installation

### Requirements
```bash
pip install opencv-python numpy pillow imagehash
```

### Optional Dependencies
For better performance and features:
```bash
# For GPU acceleration (optional)
pip install torch torchvision

# For face detection (optional)
pip install face-recognition

# For advanced similarity detection (optional)
pip install faiss-cpu

# FFmpeg for video compression (recommended)
# Download from: https://ffmpeg.org/download.html
```

## 🎯 Quick Start

### Basic Usage
```python
from main_pipeline import CompleteVideoProcessingPipeline
from config import get_robbery_detection_config

# Create pipeline with robbery detection config
config = get_robbery_detection_config()
pipeline = CompleteVideoProcessingPipeline(config)

# Process video
results = pipeline.process_video_complete("your_video.mp4")

print(f"Keyframes extracted: {results['outputs']['total_keyframes']}")
print(f"Events detected: {results['outputs']['total_events']}")
```

### Configuration Presets
```python
from config import (
    get_robbery_detection_config,  # Optimized for crime/event detection
    get_high_recall_config,        # More keyframes, sensitive detection
    get_high_precision_config,     # Fewer but higher quality keyframes
    get_balanced_config           # General purpose settings
)

# Use different presets for different needs
config = get_high_recall_config()  # For comprehensive coverage
pipeline = CompleteVideoProcessingPipeline(config)
```

### Custom Configuration
```python
from config import VideoProcessingConfig

custom_config = VideoProcessingConfig(
    # Keyframe extraction
    base_quality_threshold=0.12,      # Lower = more keyframes
    motion_threshold=0.006,           # Lower = more motion sensitive
    max_summary_frames=25,            # More frames in highlight reel
    
    # Enhancement settings
    enable_clahe=True,                # Enhanced contrast
    enable_denoising=True,            # Noise reduction
    
    # Output settings
    output_resolution="1080p",        # High resolution
    compression_crf=20,               # Better quality compression
)

pipeline = CompleteVideoProcessingPipeline(custom_config)
```

## 🔧 Parameter Tuning Guide

### For MORE Keyframes
```python
config = VideoProcessingConfig(
    base_quality_threshold=0.10,     # Lower threshold
    motion_threshold=0.005,          # More sensitive motion
    max_summary_frames=30,           # More frames in summary
    frame_sampling_interval=0.5,     # More frequent sampling
    keyframes_per_segment=8          # More per segment
)
```

### For FEWER but BETTER Keyframes
```python
config = VideoProcessingConfig(
    base_quality_threshold=0.22,     # Higher quality requirement
    motion_threshold=0.015,          # Less sensitive motion
    max_summary_frames=12,           # Fewer frames in summary
    frame_sampling_interval=2.0,     # Less frequent sampling
    keyframes_per_segment=3          # Fewer per segment
)
```

### For BETTER Event Detection
```python
config = VideoProcessingConfig(
    motion_threshold=0.006,          # More sensitive
    burst_weight=3.0,                # Higher burst priority
    event_importance_threshold=0.20, # Lower event threshold
    temporal_clustering_window=25.0  # Wider clustering
)
```

### For FASTER Processing
```python
config = VideoProcessingConfig(
    compression_preset="ultrafast",  # Faster encoding
    num_workers=8,                   # More parallel processing
    keyframes_per_segment=3,         # Fewer keyframes
    enable_face_detection=False,     # Disable heavy features
    enable_object_detection=False
)
```

## 📁 Output Structure

The pipeline creates a comprehensive output directory structure:

```
video_processing_outputs/
├── frames/                    # Extracted keyframe images
│   ├── frame_001.jpg
│   ├── frame_002.jpg
│   └── ...
├── compressed/                # Compressed videos
│   └── input_video_compressed.mp4
├── highlights/                # Generated highlight reels
│   ├── event_aware_highlights.mp4
│   ├── ultra_comprehensive_highlights.mp4
│   └── quality_focused_highlights.mp4
├── reports/                   # JSON reports and HTML gallery
│   ├── processing_results.json
│   ├── canonical_events.json
│   ├── video_segments.json
│   └── canonical_gallery.html
└── segments/                  # Individual segment files
    ├── segment_000.json
    ├── segment_001.json
    └── ...
```

## 📊 Key Parameters Reference

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `base_quality_threshold` | 0.15 | 0.1-0.3 | Lower = more keyframes |
| `motion_threshold` | 0.008 | 0.005-0.02 | Lower = more motion sensitive |
| `max_summary_frames` | 18 | 10-30 | Number of frames in highlight reel |
| `burst_weight` | 2.5 | 1.5-3.0 | Priority boost for burst frames |
| `similarity_threshold` | 0.85 | 0.8-0.95 | Deduplication strictness |
| `segment_duration` | 45.0 | 30-60 | Length of each segment (seconds) |
| `compression_crf` | 23 | 18-28 | Video quality (lower = better) |

## 🎬 Multiple Video Processing

```python
# Process all videos in a directory
results = pipeline.process_multiple_videos("path/to/video/directory")

# Process specific videos
video_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
for video in video_files:
    results = pipeline.process_video_complete(video)
```

## 📈 Performance Monitoring

The pipeline provides detailed performance statistics:

```python
results = pipeline.process_video_complete("video.mp4")

# Get processing summary
summary = pipeline.get_processing_summary()
print(f"Total time: {summary['total_processing_time']:.2f}s")
print(f"Component times: {summary['component_times']}")
```

## 🔍 Output Analysis

### JSON Reports
- **processing_results.json** - Comprehensive processing statistics
- **canonical_events.json** - Detected and deduplicated events
- **video_segments.json** - Temporal segment analysis

### Highlight Reels
- **event_aware_highlights.mp4** - Focused on detected events
- **ultra_comprehensive_highlights.mp4** - Maximum coverage
- **quality_focused_highlights.mp4** - Best quality frames only

### HTML Gallery
- **canonical_gallery.html** - Interactive browser-based viewer

## 🛠️ Advanced Usage

### Custom Event Detection
```python
from event_aggregation import EventDetector

# Create custom event detector
detector = EventDetector(config)
events = detector.detect_events(keyframes)
```

### Custom Highlight Generation
```python
from highlight_reel import HighlightReelGenerator

generator = HighlightReelGenerator(config)

# Create custom highlight with specific criteria
custom_criteria = {
    'min_motion_score': 0.01,
    'min_quality_score': 0.18,
    'require_burst': True,
    'time_range': (60, 180),  # 1-3 minutes
    'max_frames': 15
}

highlight_path = generator.create_custom_highlight_reel(segments, custom_criteria)
```

## 🐛 Troubleshooting

### Common Issues

**"FFmpeg not found"**
- Install FFmpeg from https://ffmpeg.org/download.html
- Add FFmpeg to your system PATH
- The pipeline will fall back to OpenCV if FFmpeg is unavailable

**"Out of memory errors"**
- Reduce `num_workers` parameter
- Lower `max_summary_frames`
- Process videos in smaller batches

**"No keyframes extracted"**
- Lower `base_quality_threshold` (try 0.10)
- Lower `motion_threshold` (try 0.005)
- Check if input video is valid

### Performance Tips

1. **Use GPU acceleration** when available
2. **Adjust worker count** based on CPU cores
3. **Use appropriate presets** for your use case
4. **Monitor memory usage** for large videos
5. **Use FFmpeg** for better compression performance

## 📝 Example Use Cases

### Security/Surveillance Analysis
```python
config = get_robbery_detection_config()
config.motion_threshold = 0.005  # Very sensitive
config.burst_weight = 3.0        # High burst priority
```

### Sports/Action Video Highlights
```python
config = get_high_recall_config()
config.max_summary_frames = 30   # More highlights
config.frame_display_duration = 1.2  # Faster playback
```

### Quality Archival
```python
config = get_high_precision_config()
config.output_resolution = "1080p"
config.compression_crf = 18      # High quality
config.enable_clahe = True       # Enhancement
```

## 🤝 Contributing

This pipeline is designed to be modular and extensible. Key extension points:

- **Custom event detectors** in `event_aggregation.py`
- **Additional similarity metrics** in similarity calculation
- **New highlight generation strategies** in `highlight_reel.py`
- **Custom enhancement algorithms** in `video_processing.py`

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

Built using OpenCV, NumPy, PIL, and other open-source libraries.

---

**Need help?** Check the `quick_start.py` file for comprehensive examples and parameter tuning guidance!
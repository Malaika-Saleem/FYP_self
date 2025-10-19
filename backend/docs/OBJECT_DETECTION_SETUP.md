# Object Detection Integration Setup Guide

## Installation Steps

### 1. Install Required Dependencies

Open PowerShell in the backend directory and run:

```powershell
# Install PyTorch (choose appropriate version for your system)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install Ultralytics for YOLOv11
pip install ultralytics

# Install additional dependencies
pip install Pillow opencv-python imagehash scipy

# Or install all at once from requirements file
pip install -r requirements_update.txt
```

### 2. Verify Model Files

Ensure your trained models are in the `models/` directory:
- `models/fire_yolo11.pt` - Fire detection model
- `models/yolov11_knife_gun.pt` - Knife and gun detection model

### 3. Test Object Detection Integration

Run the demo script:

```powershell
python demo_object_detection.py
```

## Configuration Options

### Security Focused Configuration (Recommended for Demo)
- Object detection enabled
- Lower confidence thresholds for better recall
- Enhanced threat assessment

```python
from config import get_security_focused_config
config = get_security_focused_config()
```

### Robbery Detection Configuration
- Object detection enabled with balanced settings
- Optimized for crime scene analysis

```python
from config import get_robbery_detection_config
config = get_robbery_detection_config()
```

## API Usage

### Upload with Object Detection

```bash
curl -X POST http://localhost:5000/api/upload \
  -F "video=@your_video.mp4" \
  -F "config_type=security"
```

Available config types:
- `security` - Security focused with object detection
- `robbery` - Robbery detection optimized
- `high_recall` - High sensitivity motion detection
- `balanced` - General purpose

### Check Processing Status

```bash
curl http://localhost:5000/api/status/VIDEO_ID
```

### Get Results with Object Detection Data

```bash
curl http://localhost:5000/api/results/VIDEO_ID
```

The response will include:
- `total_object_events` - Number of object-based events
- `total_object_detections` - Total object detections
- `object_detection_enabled` - Whether object detection was used

## Expected Output Structure

```
video_processing_outputs/VIDEO_ID/
├── frames/                    # Extracted keyframes
├── reports/
│   ├── processing_results.json
│   ├── canonical_events.json
│   ├── object_detection.json  # NEW: Object detection report
│   └── html_gallery.html     # Enhanced with object annotations
├── highlights/               # Event-aware highlight reels
└── compressed/              # Compressed video
```

## Troubleshooting

### Model Loading Issues
- Ensure models are in correct format (.pt files)
- Verify model file permissions
- Check GPU availability with `torch.cuda.is_available()`

### Performance Optimization
- Use GPU acceleration when available
- Adjust confidence thresholds based on your needs
- Consider reducing video resolution for faster processing

### Memory Issues
- Reduce batch size in configuration
- Process shorter video segments
- Monitor system memory usage

## Manual Testing Checklist

- [ ] Models load successfully
- [ ] Object detection runs on test video
- [ ] Events are created for detected objects
- [ ] Canonical events include object information
- [ ] Reports contain object detection data
- [ ] API endpoints return enhanced results
- [ ] Threat levels are assessed correctly
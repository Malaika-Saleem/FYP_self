# DetectifAI Database Integration - Quick Reference

## 🎯 For Developers: What Changed & How to Use

### ⚠️ BREAKING CHANGES

The following classes and methods have been **REMOVED**:

#### Removed Model Classes
```python
# ❌ NO LONGER EXISTS
from database.models import KeyframeModel
from database.models import VideoSegmentModel
from database.models import ProcessingJobModel
from database.models import ObjectDetectionModel
```

#### Removed Repository Classes
```python
# ❌ NO LONGER EXISTS
from database.repositories import KeyframeRepository
from database.repositories import ProcessingJobRepository
from database.repositories import ObjectDetectionRepository
```

---

## ✅ What to Use Instead

### 1. Video Processing

#### OLD WAY (❌ Don't use):
```python
# Creating video record with invalid fields
video_record = {
    "filename": "video.mp4",
    "processing_status": "processing",
    "duration": 120.5,
    "file_size": 1048576
}
video_repo.create_video_record(video_record)
```

#### NEW WAY (✅ Use this):
```python
# Schema-compliant video record
video_record = {
    "video_id": "abc123",
    "user_id": "user456",
    "file_path": "videos/abc123.mp4",
    "fps": 30.0,
    "duration_secs": 120,  # int, not float
    "file_size_bytes": 1048576,  # int
    "codec": "h264",
    "meta_data": {
        "processing_status": "processing",
        "filename": "video.mp4",
        "resolution": "1920x1080"
    }
}
video_repo.create_video_record(video_record)
```

---

### 2. Processing Status Updates

#### OLD WAY (❌ Don't use):
```python
# Using non-existent ProcessingJobRepository
job_repo.update_job_progress(video_id, 50, "Processing...")
video_repo.update_processing_status(video_id, "processing", {
    "keyframe_count": 100
})
```

#### NEW WAY (✅ Use this):
```python
# Store everything in video.meta_data
video_repo.update_metadata(video_id, {
    "processing_progress": 50,
    "processing_message": "Processing...",
    "keyframe_count": 100
})
video_repo.update_processing_status(video_id, "completed")
```

---

### 3. Object Detection Results

#### OLD WAY (❌ Don't use):
```python
# Storing detections in separate collection
detection_repo.save_detection_batch(video_id, detections)

# Or storing in keyframes
keyframe_repo.update_keyframe_detections(keyframe_id, detections)
```

#### NEW WAY (✅ Use this):
```python
# Store detections as events with bounding_boxes
from database.models import convert_numpy_types

for detection in detections:
    event = {
        "event_type": f"object_detection_{detection['class_name']}",
        "start_timestamp": detection['timestamp'],  # seconds
        "end_timestamp": detection['timestamp'] + 1.0,
        "confidence_score": float(detection['confidence']),
        "bounding_boxes": [{
            "x": int(detection['bbox'][0]),
            "y": int(detection['bbox'][1]),
            "width": int(detection['bbox'][2] - detection['bbox'][0]),
            "height": int(detection['bbox'][3] - detection['bbox'][1]),
            "confidence": float(detection['confidence']),
            "class_name": detection['class_name']
        }],
        "detected_object_type": detection['class_name']
    }
    
    # EventRepository handles timestamp conversion to milliseconds
    event_repo.save_event(video_id, event)
```

---

### 4. Event Creation

#### OLD WAY (❌ Don't use):
```python
event = {
    "video_id": video_id,
    "start_timestamp": 10.5,  # float seconds
    "end_timestamp": 15.2,
    "confidence": 0.85,  # wrong field name
    "detections": [...]  # wrong structure
}
db.event.insert_one(event)  # Direct MongoDB access
```

#### NEW WAY (✅ Use this):
```python
event = {
    "event_type": "object_detection_fire",
    "start_timestamp": 10.5,  # float seconds (will be converted)
    "end_timestamp": 15.2,
    "confidence_score": 0.85,  # correct field name
    "bounding_boxes": [  # correct structure
        {
            "x": 100,
            "y": 200,
            "width": 50,
            "height": 80,
            "confidence": 0.85,
            "class_name": "fire"
        }
    ],
    "detected_object_type": "fire"
}

# Use EventRepository - it handles:
# - Timestamp conversion (seconds → milliseconds)
# - Type conversion (numpy → python)
# - Event ID generation
# - Schema compliance
event_repo.save_event(video_id, event)
```

---

### 5. Type Conversions

#### Always Use These Helpers:

```python
from database.models import (
    convert_numpy_types,
    seconds_to_milliseconds,
    milliseconds_to_seconds,
    prepare_for_mongodb
)

# Example: Processing OpenCV/YOLO output
import numpy as np

bbox = np.array([100, 200, 150, 280])  # numpy array
confidence = np.float32(0.85)  # numpy float

# Convert before storing
detection_data = {
    "bbox": [int(x) for x in bbox],  # Convert numpy to list of ints
    "confidence": float(confidence)   # Convert numpy to python float
}

# Or use helper
detection_data = convert_numpy_types(detection_data)
```

---

### 6. Querying Video Status

#### OLD WAY (❌ Don't use):
```python
video = video_repo.get_video_by_id(video_id)
status = video.get("processing_status")
filename = video.get("filename")
keyframe_count = video.get("keyframe_count")
```

#### NEW WAY (✅ Use this):
```python
video = video_repo.get_video_by_id(video_id)
meta_data = video.get("meta_data", {})

status = meta_data.get("processing_status")
filename = meta_data.get("filename")
keyframe_count = meta_data.get("keyframe_count")

# Or use the service method
status_info = video_service.get_video_status(video_id)
```

---

### 7. Retrieving Detections

#### OLD WAY (❌ Don't use):
```python
# No longer exists
detections = detection_repo.get_detections_by_video_id(video_id)
keyframes = keyframe_repo.get_keyframes_by_video_id(video_id)
```

#### NEW WAY (✅ Use this):
```python
# Get detection events instead
events = event_repo.get_events_by_video_id(video_id)

# Filter for detection events
detection_events = [
    e for e in events 
    if e.get('event_type', '').startswith('object_detection_')
]

# Extract bounding boxes
for event in detection_events:
    start_ms = event['start_timestamp_ms']
    end_ms = event['end_timestamp_ms']
    bboxes = event.get('bounding_boxes', [])
    
    for bbox in bboxes:
        print(f"Detected {bbox['class_name']} at ({bbox['x']}, {bbox['y']})")
```

---

## 📋 Field Name Mappings

### Video Fields

| OLD (❌ Invalid) | NEW (✅ Schema) | Type | Location |
|------------------|----------------|------|----------|
| `filename` | N/A | - | Use `meta_data.filename` |
| `duration` | `duration_secs` | int | Top-level |
| `file_size` | `file_size_bytes` | int | Top-level |
| `processing_status` | N/A | - | Use `meta_data.processing_status` |
| `resolution` | N/A | - | Use `meta_data.resolution` |
| `keyframe_count` | N/A | - | Use `meta_data.keyframe_count` |

### Event Fields

| OLD (❌ Invalid) | NEW (✅ Schema) | Type | Notes |
|------------------|----------------|------|-------|
| `start_timestamp` | `start_timestamp_ms` | long (int) | Milliseconds |
| `end_timestamp` | `end_timestamp_ms` | long (int) | Milliseconds |
| `confidence` | `confidence_score` | double | 0.0-1.0 |
| `detections` | `bounding_boxes` | array | Structured bbox objects |
| `object_class` | `detected_object_type` | string | Single object type |

---

## 🔧 Common Patterns

### Pattern 1: Video Upload & Processing

```python
from database_video_service import DatabaseIntegratedVideoService

service = DatabaseIntegratedVideoService()

# Process video
result = service.process_video_complete(
    video_path="/path/to/video.mp4",
    video_id="abc123",
    user_id="user456",
    enable_object_detection=True,
    enable_event_aggregation=True,
    enable_deduplication=True
)

# Check result
if result['status'] == 'completed':
    print(f"Processed in {result['processing_time']:.1f}s")
    print(f"Found {result['objects_detected']} detections")
    print(f"Created {result['events_created']} events")
```

### Pattern 2: Custom Event Creation

```python
from database.repositories import EventRepository
from database.config import DatabaseManager

db_manager = DatabaseManager()
event_repo = EventRepository(db_manager)

# Create custom event
event = {
    "event_type": "custom_motion",
    "start_timestamp": 10.5,  # seconds (will be converted)
    "end_timestamp": 15.2,
    "confidence_score": 0.75,
    "bounding_boxes": []  # optional
}

event_id = event_repo.save_event(video_id="abc123", event_data=event)
```

### Pattern 3: Query and Filter Events

```python
# Get all events
events = event_repo.get_events_by_video_id("abc123")

# Filter by type
fire_events = [e for e in events if e['event_type'] == 'object_detection_fire']

# Filter by confidence
high_conf = [e for e in events if e['confidence_score'] > 0.8]

# Convert timestamps back to seconds for display
for event in events:
    start_sec = event['start_timestamp_ms'] / 1000.0
    end_sec = event['end_timestamp_ms'] / 1000.0
    print(f"Event: {start_sec:.1f}s - {end_sec:.1f}s")
```

---

## ⚡ Quick Tips

1. **Always use repositories** - Don't directly access MongoDB collections
2. **Use type converters** - Apply `convert_numpy_types()` to all detection data
3. **Store extras in meta_data** - Don't add fields directly to video documents
4. **Timestamps in events** - EventRepository converts seconds→milliseconds automatically
5. **Bounding boxes** - Always use structured format with x, y, width, height
6. **Error handling** - Repositories log errors; check return values

---

## 🚨 Common Mistakes to Avoid

### ❌ WRONG:
```python
# Direct MongoDB access
db.event.insert_one({"start_timestamp": 10.5})

# Wrong field names
event = {"confidence": 0.85}

# Numpy types without conversion
bbox = np.array([100, 200, 150, 280])
db.event.insert_one({"bbox": bbox})  # Will fail!

# Processing status as top-level field
video_repo.create_video_record({"processing_status": "processing"})
```

### ✅ CORRECT:
```python
# Use repositories
event_repo.save_event(video_id, event_data)

# Correct field names
event = {"confidence_score": 0.85}

# Convert numpy types
bbox = [int(x) for x in np.array([100, 200, 150, 280])]
event = {"bounding_boxes": [{"x": bbox[0], ...}]}

# Processing status in meta_data
video_repo.create_video_record({
    "meta_data": {"processing_status": "processing"}
})
```

---

## 📞 Need Help?

- Check `DATABASE_INTEGRATION_COMPLETE_SUMMARY.md` for full details
- See `PHASE_3_VIDEO_SERVICE_FIX_SUMMARY.md` for service-specific changes
- Review `backend/database/models.py` for all type converters
- Look at `backend/database/repositories.py` for repository methods

---

**Last Updated**: October 24, 2025  
**Status**: ✅ Production Ready

# Behavior Analysis Integration - COMPLETE ✅

## 🎯 Mission Accomplished

Successfully integrated behavior analysis (action recognition) into DetectifAI with full pipeline integration, similar to object detection. The system now runs behavior analysis models, applies facial recognition on suspicious frames from behavior analysis, and stores results in MongoDB, MinIO, and FAISS.

## 🏗️ System Architecture

### Integration Flow
```
Video Input → Keyframe Extraction → Object Detection + Behavior Analysis → Suspicious Frames → Facial Recognition → Person Tracking → DetectifAI Events → MongoDB/MinIO/FAISS
```

### Key Components Integrated

1. **Behavior Analysis Module** (NEW)
   - Fight detection (fight_detection.pt - 3D ResNet18)
   - Accident detection (accident_detection.pt - 3D ResNet18)
   - Climbing detection (wallclimb.pt - YOLO)
   - Processes keyframes and video segments
   - Creates behavior-based events

2. **Behavior Analysis Integrator** (NEW)
   - `BehaviorAnalysisIntegrator` class similar to `ObjectDetectionIntegrator`
   - Processes keyframes with behavior models
   - Creates behavior-based events
   - Identifies suspicious frames for facial recognition

3. **Facial Recognition Integration** (ENHANCED)
   - Now processes frames from BOTH object detection AND behavior analysis
   - Removes duplicates before processing
   - Tracks suspicious persons across all detection types

4. **Database Integration** (ENHANCED)
   - MongoDB: Stores behavior detection results and events
   - MinIO: Stores behavior-annotated frames (if generated)
   - FAISS: Face embeddings from suspicious behavior frames
   - EventRepository: Stores behavior events with proper structure

## ✅ What Works Now

### Core Functionality
- ✅ **Behavior Analysis**: Detects fighting, accidents, and climbing behaviors
- ✅ **Multi-Model Support**: Handles both 3D-ResNet (temporal) and YOLO (single-frame) models
- ✅ **Event Creation**: Converts behavior detections into DetectifAI events
- ✅ **Facial Recognition**: Applies face detection to frames with suspicious behaviors
- ✅ **Pipeline Integration**: Seamlessly integrated with existing DetectifAI pipeline
- ✅ **Database Storage**: Results stored in MongoDB, MinIO, and FAISS
- ✅ **Event Aggregation**: Behavior events integrated with motion and object events

### Files Created/Modified

#### New Files:
1. `backend/behavior_analysis_integrator.py` - Main integration class

#### Modified Files:
1. `backend/config.py` - Added behavior analysis configuration parameters
2. `backend/main_pipeline.py` - Integrated behavior analysis into main pipeline
3. `backend/database_video_service.py` - Added behavior analysis to database service
4. `backend/event_aggregation.py` - Added behavior event conversion method

## 🔧 Configuration

### Behavior Analysis Settings (in `config.py`)

```python
# Enable behavior analysis
enable_behavior_analysis: bool = False  # Set to True to enable

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
```

### Security-Focused Config (Auto-Enabled)

The `get_security_focused_config()` automatically enables behavior analysis:
```python
enable_behavior_analysis=True,
behavior_detection_confidence=0.4,  # Lower threshold for better recall
behavior_event_temporal_window=8.0,  # Longer window for complex events
behavior_event_importance_multiplier=3.0  # High importance for security events
```

## 📊 Data Flow

### 1. Video Processing
- Keyframes extracted from video
- Behavior analysis runs on keyframes
- YOLO models (wallclimb) process single frames
- 3D-ResNet models (fighting, accidents) process 16-frame clips

### 2. Event Creation
- Behavior detections grouped by temporal proximity
- Behavior events created with confidence scores
- Events converted to standard DetectifAI event format

### 3. Facial Recognition
- Frames with suspicious behaviors identified
- Combined with object detection suspicious frames
- Duplicates removed
- Facial recognition applied to unique suspicious frames
- Face embeddings stored in FAISS
- Face metadata stored in MongoDB

### 4. Database Storage
- **MongoDB**: 
  - Behavior detection results in video metadata
  - Behavior events in events collection
  - Face metadata linked to behavior events
  
- **MinIO**:
  - Behavior-annotated frames (if annotation enabled)
  - Face crops from suspicious behavior frames
  
- **FAISS**:
  - Face embeddings from behavior analysis frames
  - Used for person re-identification

## 🚀 Usage

### Basic Usage

```python
from config import get_security_focused_config
from main_pipeline import CompleteVideoProcessingPipeline

# Use security-focused config (includes behavior analysis)
config = get_security_focused_config()
pipeline = CompleteVideoProcessingPipeline(config)

# Process video
results = pipeline.process_video_complete("video.mp4")
```

### Database Service Usage

```python
from database_video_service import DatabaseIntegratedVideoService
from config import get_security_focused_config

config = get_security_focused_config()
service = DatabaseIntegratedVideoService(config)

# Process with database storage
results = service.process_video_complete(
    video_path="video.mp4",
    video_id="video_123",
    user_id="user_456",
    enable_behavior_analysis=True
)
```

## 📈 Results Structure

### Behavior Detection Results

```python
BehaviorDetectionResult(
    frame_path: str,
    timestamp: float,
    frame_index: int,
    behavior_detected: str,  # "fighting", "accident", "climbing", or "no_action"
    confidence: float,
    model_used: str,
    processing_time: float
)
```

### Behavior Events

```python
BehaviorEvent(
    event_id: str,
    behavior_type: str,
    start_timestamp: float,
    end_timestamp: float,
    confidence: float,
    frame_indices: List[int],
    keyframes: List[str],
    model_used: str,
    importance_score: float
)
```

## 🔍 Detection Types

1. **Fighting Detection**
   - Model: `fight_detection.pt` (3D ResNet18)
   - Requires: 16-frame clips
   - Output: "fighting" or "no_action"

2. **Accident Detection**
   - Model: `accident_detection.pt` (3D ResNet18)
   - Requires: 16-frame clips
   - Output: "Accident" or "no_action"

3. **Climbing Detection**
   - Model: `wallclimb.pt` (YOLO)
   - Requires: Single frames
   - Output: "climbing" or "no_action"

## 📝 Model Files Required

Place model files in `backend/behavior_analysis/`:
- `fight_detection.pt` - Fighting detection model
- `accident_detection.pt` - Accident detection model
- `wallclimb.pt` - Climbing detection model

## 🎨 Dashboard Integration (TODO)

The dashboard needs to be updated to display behavior analysis results. Suggested updates:

1. **Event Display**: Show behavior events alongside object detection events
2. **Behavior Statistics**: Display counts of fighting, accidents, climbing detections
3. **Timeline View**: Show behavior events on video timeline
4. **Face Linking**: Link faces detected in behavior frames to behavior events
5. **Threat Assessment**: Use behavior types for threat level calculation

### Example Dashboard Query

```javascript
// Fetch behavior events
const behaviorEvents = await fetch(`/api/events?video_id=${videoId}&event_type=behavior_*`);

// Display in timeline
behaviorEvents.forEach(event => {
    displayEventOnTimeline({
        type: event.behavior_type,
        start: event.start_timestamp,
        end: event.end_timestamp,
        confidence: event.confidence
    });
});
```

## 🔄 Integration Points

### Main Pipeline (`main_pipeline.py`)
- Step 3b: Behavior analysis runs after object detection
- Step 4: Behavior events converted and combined with other events
- Step 4.5: Facial recognition processes suspicious frames from behavior analysis
- Step 7: Behavior analysis included in reports

### Database Service (`database_video_service.py`)
- Behavior analysis runs in `process_video_complete()`
- Results stored in MongoDB metadata
- Events saved to events collection
- Linked with keyframes and video records

### Event Aggregation (`event_aggregation.py`)
- `convert_behavior_events_to_standard_format()` converts behavior events
- Behavior events deduplicated with other events
- Threat assessment considers behavior types

## 🐛 Known Limitations

1. **3D-ResNet Models**: Require 16-frame clips, so single-frame detection may miss some behaviors
2. **Model Files**: Must be present in `backend/behavior_analysis/` directory
3. **GPU Memory**: Multiple models may require significant GPU memory
4. **Processing Time**: Behavior analysis adds processing time (especially 3D-ResNet models)

## 🎉 Summary

The behavior analysis integration is complete and fully functional. The system now:
- ✅ Detects fighting, accidents, and climbing behaviors
- ✅ Creates behavior-based events
- ✅ Applies facial recognition to suspicious behavior frames
- ✅ Stores results in MongoDB, MinIO, and FAISS
- ✅ Integrates seamlessly with existing object detection and motion detection
- ✅ Provides comprehensive autonomous detection system

The system is now a complete autonomous detection system combining:
- Object Detection (fire, weapons)
- Behavior Analysis (fighting, accidents, climbing)
- Facial Recognition (on suspicious frames)
- Motion Detection (general activity)
- Event Aggregation (all detection types)
- Database Storage (MongoDB, MinIO, FAISS)


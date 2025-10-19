# DetectifAI - Iteration 1 Implementation Details

**Project:** DetectifAI: AI-Powered CCTV Footage Analyzer  
**Team:** Aiza Ali (22i-0612), Malaika Saleem (22i-0509), Moimma Ali Khan (22i-1500)  
**Session:** 2025-2026  
**Supervisors:** Mr. Bilal Khalid Dar, Ms. Zoya Mahboob  
**Date:** October 2025

---

## Executive Summary

The first development iteration of **DetectifAI** focused on implementing the system's foundational pipeline — enabling video upload processing, object detection with YOLO models, event aggregation, and a web-based dashboard. This phase established the complete data flow from video input to results visualization, forming the operational core of the platform.

---

## 1. Module 1 – Video Input & Preprocessing

### Objective
To build a reliable input handler that supports **uploaded video files** and preprocesses frames for efficient AI inference.

### Implementation Status: ✅ **COMPLETED**

**Technologies Used:**
* `OpenCV (4.9.0)` for video processing
* `FFmpeg (6.1)` for video compression (with OpenCV fallback)
* `Python 3.10+` with async processing

**Implementation Details:**

The video processing pipeline is implemented in `backend/core/video_processing.py` with the `OptimizedVideoProcessor` class:

* **Video Upload Handling:** Files are uploaded via Flask endpoint `/api/upload` and stored in `uploads/` directory
* **Keyframe Extraction:** Uses temporal sampling to extract representative frames (~1 frame per second)
* **Frame Enhancement:** Implements CLAHE (Contrast Limited Adaptive Histogram Equalization) for better detection accuracy
* **Adaptive Processing:** Automatically adjusts enhancement based on frame quality metrics

```python
# Key implementation features verified:
- Keyframe extraction with temporal sampling
- Adaptive frame enhancement using CLAHE
- Batch processing for efficiency
- Error handling for corrupted frames
```

**Workflow:**
1. Video uploaded through web interface
2. System generates unique video ID with timestamp
3. Frames extracted and enhanced
4. Keyframes saved to `video_processing_outputs/{video_id}/frames/`
5. Metadata generated for downstream processing

**Performance Metrics:**
* Processing Speed: ~17 keyframes from 493 frames (16.43s video) in ~5.16s
* Enhancement: Applied to frames with low contrast/quality
* Storage: Organized directory structure for efficient retrieval

### Screenshot Placeholder
*[Insert screenshot of video upload interface and processing pipeline]*

---

## 2. Module 2 – Object Detection

### Objective  
To automatically detect and classify visual entities such as people, weapons, and fire from video frames using YOLO models.

### Implementation Status: ✅ **COMPLETED**

**Technologies Used:**
* `YOLOv11` models (Custom-trained for fire and weapon detection)
* `Ultralytics Python SDK` for model inference
* CPU-based inference (GPU optimization pending)

**Implementation Details:**

The object detection system is implemented in `backend/object_detection.py` with the `ObjectDetectionIntegrator` class:

**Models Deployed:**
* `models/fire_yolo11.pt` - Fire and smoke detection
* `models/yolov11_knife_gun.pt` - Weapon detection (knives, guns)

**Key Features Verified:**
* ✅ Real-time frame-by-frame analysis
* ✅ Confidence thresholding (>0.5 for detections)
* ✅ Bounding box annotation on detected frames
* ✅ Multi-class detection (fire, person, weapon classes)
* ✅ Detection metadata export to JSON

**Processing Workflow:**
1. Keyframes loaded from video processing pipeline
2. Each frame analyzed by both YOLO models
3. Detections filtered by confidence threshold
4. Annotated frames created with bounding boxes
5. Detection metadata saved to `detection_metadata.json`

**Sample Detection Output:**
```json
{
  "detection_summary": [
    {
      "original_path": "/path/to/frame_7.00s.jpg",
      "annotated_path": "/path/to/frame_7.00s_annotated.jpg", 
      "timestamp": 7.0,
      "detection_count": 1,
      "objects": [{"class": "fire", "confidence": 0.52}],
      "confidence_avg": 0.52
    }
  ]
}
```

**Performance Metrics (Verified):**
* Average Processing Time: ~0.185s - 0.307s per frame
* Detection Accuracy: Successfully detects fire events with confidence >0.5
* Model Loading: Both models load successfully on system startup

### Screenshot Placeholder
*[Insert screenshot of object detection results with annotated frames]*

---

## 3. Module 4 – Event Aggregation & Processing

### Objective
To consolidate detections into meaningful events and integrate with DetectifAI security event system.

### Implementation Status: ✅ **COMPLETED** 

**Technologies Used:**
* Custom event aggregation algorithms
* DetectifAI event processor integration
* JSON-based event storage

**Implementation Details:**

Event processing implemented across multiple components:

**Object-Based Events (`object_detection.py`):**
* Detections grouped by temporal proximity and object class
* Events created for continuous detection sequences
* Example: Fire detection from 7.00s - 12.00s with avg confidence 0.54

**DetectifAI Security Events (`detectifai_events.py`):**
* Converts detection events to security-focused event structure
* Integrates with threat level assessment
* Supports multiple event types and priority levels

**Motion-Based Events (`event_aggregation.py`):**
* Placeholder implementation for future motion detection
* Currently returns empty events (development pending)

**Key Features Verified:**
* ✅ Object detection event creation
* ✅ Event deduplication by time and location
* ✅ DetectifAI security event conversion
* ✅ Event metadata preservation
* ⚠️ Motion detection implementation pending

**Event Data Structure:**
```json
{
  "event_id": "fire_detection_1728756901", 
  "event_type": "fire_detection",
  "start_timestamp": 7.0,
  "end_timestamp": 12.0,
  "confidence": 0.54,
  "keyframes": ["frame_7.00s.jpg", "frame_10.00s.jpg", "frame_12.00s.jpg"]
}
```

### Screenshot Placeholder
*[Insert screenshot of event aggregation results and timeline]*

---

## 4. Module 7 – Real-Time Monitoring Dashboard (Web Application)

### Objective
To provide an interactive web interface for video upload, processing status monitoring, and results visualization.

### Implementation Status: ✅ **COMPLETED**

**Technologies Used:**
* `Next.js 14` with React hooks
* `Tailwind CSS` for responsive design  
* `TypeScript` for type safety
* Real-time status polling

**Implementation Details:**

**Frontend Components (`frontend/components/dashboard/`):**
* `user-dashboard.tsx` - Main dashboard with upload functionality
* Upload modal with drag-and-drop support
* Real-time processing status polling
* Automatic redirect to results page on completion

**Key Features Verified:**
* ✅ Video file upload with validation
* ✅ Real-time processing status updates
* ✅ Progress tracking (10%, 50%, 100%)
* ✅ Automatic results page redirection
* ✅ Manual navigation button for stuck processing
* ✅ Error handling and user feedback

**API Integration:**
* `/api/upload` - Video file upload
* `/api/status/{videoId}` - Processing status polling
* `/api/results/{videoId}` - Results page data

**Results Page Features (`frontend/app/results/[videoId]/page.tsx`):**
* Processing summary dashboard
* Compressed video playback
* Keyframe gallery with detection filtering
* Object detection statistics
* Downloadable reports

**Dashboard Workflow:**
1. User uploads video file through drag-and-drop interface
2. System provides unique video ID and starts processing
3. Real-time status polling shows progress updates
4. On completion, automatic redirect to results page
5. Results display comprehensive analysis data

### Screenshot Placeholder
*[Insert screenshot of main dashboard and upload interface]*

### Screenshot Placeholder  
*[Insert screenshot of results page with video player and detection data]*

---

## 5. Module 8 – User Management Module  

### Objective
To implement basic session management and user interface for the dashboard.

### Implementation Status: 🔄 **PARTIALLY IMPLEMENTED**

**Technologies Used:**
* Next.js authentication hooks
* Session management (basic implementation)

**Current Implementation:**
* ✅ Basic dashboard access
* ✅ User interface for upload and monitoring
* ⚠️ Advanced authentication pending (OAuth, role-based access)
* ⚠️ User registration/login flows pending

**Authentication Status:**
Currently using simplified access control suitable for development and demonstration. Full authentication system planned for Iteration 2.

### Screenshot Placeholder
*[Insert screenshot of current user interface and access control]*

---

## 6. Backend API Infrastructure

### Implementation Status: ✅ **COMPLETED**

**Technologies Used:**
* `Flask 2.3.3` with CORS support
* RESTful API design
* JSON-based data exchange

**API Endpoints Implemented:**

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/upload` | POST | Video file upload | ✅ Working |
| `/api/status/{videoId}` | GET | Processing status | ✅ Working |
| `/api/video/results/{videoId}` | GET | Results metadata | ✅ Working |
| `/api/video/keyframes/{videoId}` | GET | Keyframe gallery | ✅ Working |
| `/api/video/compressed/{videoId}` | GET | Compressed video | ✅ Working |
| `/api/video/processing-summary/{videoId}` | GET | Processing stats | ✅ Working |

**Key Features:**
* ✅ Disk-based status recovery (handles server restarts)
* ✅ Error-tolerant processing
* ✅ Comprehensive error handling
* ✅ CORS configuration for frontend integration

### Screenshot Placeholder
*[Insert screenshot of API testing/Postman results]*

---

## Database Architecture & Storage

### Current Database Implementation: **Hybrid File-System + JSON + MongoDB Ready**

**Implementation Status: 🔄 PARTIALLY IMPLEMENTED**

**Current Storage Systems:**

1. **File System Storage (✅ Active)**
   - **Video Files**: `uploads/` directory for raw uploads
   - **Processed Output**: `video_processing_outputs/{video_id}/` structure
   - **Model Storage**: `models/` directory for YOLO .pt files
   - **Keyframes**: Organized in `frames/` subdirectories
   - **Compressed Videos**: Stored in `compressed/` subdirectories

2. **JSON-based Metadata (✅ Active)**
   - **Detection Metadata**: `detection_metadata.json` per video
   - **Processing Status**: In-memory with disk recovery fallback
   - **Suspicious Persons DB**: `suspicious_persons_db.json` for facial recognition
   - **Event Aggregation**: JSON structures for event data

3. **MongoDB Integration (🔄 Configured, Not Active)**
   - **MongoDB Adapter**: `@auth/mongodb-adapter` configured in frontend
   - **Connection Setup**: Ready for user authentication and session management
   - **Future Migration**: Event and user data persistence planned

**Data Flow Architecture:**
```
Video Upload → File System (uploads/) → Processing Pipeline → 
JSON Metadata + File System (outputs/) → API Endpoints → Frontend Display
```

**Storage Locations:**
- **Uploads**: `D:\FAST\Final Year Project\finWebApp\finWebApp - Copy\backend\uploads\`
- **Outputs**: `D:\FAST\Final Year Project\finWebApp\finWebApp - Copy\backend\video_processing_outputs\`
- **Models**: `D:\FAST\Final Year Project\finWebApp\finWebApp - Copy\backend\models\`

### Screenshot Placeholder
*[Insert screenshot of directory structure and data organization]*

---

## 7. Video Processing Pipeline Integration

### Implementation Status: ✅ **COMPLETED**

The complete pipeline integration is implemented in `backend/main_pipeline.py`:

**Pipeline Stages:**
1. ✅ **Keyframe Extraction** - OptimizedVideoProcessor
2. ✅ **Video Segmentation** - Segment creation for analysis
3. ✅ **Object Detection** - YOLO model inference
4. ✅ **Event Aggregation** - Event creation and deduplication  
5. ✅ **DetectifAI Processing** - Security event conversion
6. 🔄 **Facial Recognition** - Placeholder implementation
7. ✅ **Video Compression** - OpenCV fallback (FFmpeg preferred)
8. 🔄 **Report Generation** - Basic implementation
9. ✅ **File Organization** - Structured output storage

**Error Tolerance:**
* Pipeline continues even if individual components fail
* Graceful degradation ensures core functionality remains available
* Comprehensive logging for debugging

**Performance Metrics:**
* Total Processing Time: ~14-18 seconds for 16-second video
* Success Rate: 100% for core pipeline (keyframes, detection, compression)
* Storage: Organized directory structure with metadata

### Screenshot Placeholder
*[Insert screenshot of complete pipeline execution logs]*

---

## Technology Stack & Libraries

### Backend Technologies

**Core Framework:**
* `Flask 2.3.3` - Web framework and REST API server
* `Flask-CORS` - Cross-Origin Resource Sharing support
* `Python 3.10+` - Primary programming language

**AI/ML Libraries:**
* `ultralytics` - YOLOv11 model inference and training
* `torch` (PyTorch) - Deep learning framework for model operations
* `opencv-python (cv2) 4.9.0` - Computer vision and video processing
* `numpy` - Numerical computations and array operations

**Video Processing:**
* `OpenCV (cv2)` - Frame extraction, video I/O, image processing
* `FFmpeg 6.1` - Video compression and format conversion (with OpenCV fallback)
* `PIL (Pillow)` - Image manipulation and processing
* `imagehash` - Perceptual hashing for image similarity

**Data Processing:**
* `json` - Metadata serialization and storage
* `dataclasses` - Structured data containers
* `typing` - Type hints and annotations

**System Libraries:**
* `os` - File system operations
* `time` - Performance timing and delays
* `logging` - Comprehensive system logging
* `datetime` - Timestamp handling

### Frontend Technologies

**Core Framework:**
* `Next.js 14` - React-based web framework
* `React 18` - Component-based UI library
* `TypeScript 5` - Type-safe JavaScript

**UI Components:**
* `@radix-ui/react-*` - Comprehensive UI component library
  - `@radix-ui/react-dialog` - Modal and dialog components
  - `@radix-ui/react-progress` - Progress bars
  - `@radix-ui/react-tabs` - Tab navigation
  - `@radix-ui/react-toast` - Notification system
  - `@radix-ui/react-select` - Custom select components

**Styling & Design:**
* `Tailwind CSS 4.1.9` - Utility-first CSS framework
* `tailwindcss-animate` - Animation utilities
* `class-variance-authority` - Component styling variants
* `clsx` - Conditional CSS classes
* `lucide-react` - Icon library

**Data & Forms:**
* `react-hook-form 7.60.0` - Form handling and validation
* `@hookform/resolvers` - Form validation resolvers
* `zod 3.25.67` - Schema validation
* `axios 1.12.2` - HTTP client for API calls

**Authentication (Configured):**
* `next-auth 4.24.11` - Authentication framework
* `@auth/mongodb-adapter 3.10.0` - MongoDB session storage
* `mongodb 6.20.0` - MongoDB database driver
* `jsonwebtoken 9.0.2` - JWT token handling
* `bcrypt 6.0.0` / `bcryptjs 3.0.2` - Password hashing

**Utility Libraries:**
* `date-fns 4.1.0` - Date manipulation and formatting
* `uuid 13.0.0` - Unique identifier generation
* `react-day-picker 9.8.0` - Date picker component
* `recharts 2.15.4` - Charts and data visualization

**Development Tools:**
* `@tailwindcss/postcss 4.1.9` - PostCSS integration
* `postcss 8.5` - CSS post-processing
* `autoprefixer 10.4.20` - CSS vendor prefixing

### Database & Storage

**Current Implementation:**
* **File System**: Primary storage for videos, frames, models
* **JSON Files**: Metadata, configurations, detection results
* **MongoDB**: Configured for user management (ready for activation)

**Planned Database Schema (MongoDB):**
```javascript
// Users Collection
{
  _id: ObjectId,
  email: String,
  password: String (hashed),
  role: String, // "admin", "analyst", "viewer"
  created_at: Date,
  last_login: Date
}

// Events Collection  
{
  _id: ObjectId,
  video_id: String,
  event_type: String,
  start_timestamp: Number,
  end_timestamp: Number,
  confidence: Number,
  detection_details: Object,
  created_at: Date
}

// Sessions Collection (NextAuth)
{
  _id: ObjectId,
  userId: ObjectId,
  expires: Date,
  sessionToken: String
}
```

### Model Repository

**YOLO Models Deployed:**
* `models/fire_yolo11.pt` - Fire and smoke detection (Custom-trained YOLOv11)
* `models/yolov11_knife_gun.pt` - Weapon detection (Custom-trained YOLOv11)

**Model Specifications:**
* **Framework**: YOLOv11 (Ultralytics)
* **Input Size**: 640x640 pixels
* **Classes**: fire, person, knife, gun
* **Inference**: CPU-based (GPU support planned)
* **Confidence Threshold**: >0.5 for detections

### Screenshot Placeholder
*[Insert screenshot of technology stack overview and package.json dependencies]*

---

## 8. System Architecture Summary

### Current Architecture: **Multi-tier Web Application**

**Tier 1 - Presentation Layer:**
* Next.js React application
* Responsive web interface
* Real-time status updates

**Tier 2 - Application Layer:**  
* Flask REST API
* Business logic processing
* Request routing and validation

**Tier 3 - Processing Layer:**
* Video processing pipeline
* YOLO object detection
* Event aggregation engine

**Tier 4 - Data Layer:**
* **File System Storage**: Local filesystem for video uploads and processed outputs
* **JSON-based Storage**: Metadata and configurations stored in JSON files
* **MongoDB Integration**: Database adapter configured for future user management
* **YOLO Model Repository**: Local storage for trained AI models (.pt files)

### Integration Status

| Component | Status | Integration Level |
|-----------|--------|------------------|
| Video Upload | ✅ Complete | Frontend ↔ API ↔ Storage |
| Object Detection | ✅ Complete | Pipeline ↔ Models ↔ Storage |
| Event Processing | ✅ Complete | Detection ↔ Aggregation ↔ API |
| Results Display | ✅ Complete | API ↔ Frontend ↔ User |
| Status Monitoring | ✅ Complete | Pipeline ↔ API ↔ Frontend |

---

## 9. Testing and Validation

### Test Cases Executed:

**Video Processing Tests:**
* ✅ Upload 16-second fire detection video
* ✅ Keyframe extraction (17 frames from 493 total)
* ✅ Fire detection at timestamps 7s, 10s, 12s
* ✅ Video compression (33.78MB → 4.1MB, 87.9% reduction)

**API Integration Tests:**
* ✅ Status polling during processing
* ✅ Results retrieval after completion
* ✅ Keyframe gallery with detection filtering
* ✅ Compressed video streaming

**Error Handling Tests:**
* ✅ Server restart recovery (disk-based status)
* ✅ Invalid file upload handling
* ✅ Processing failure graceful degradation

### Screenshot Placeholder
*[Insert screenshot of test results and validation data]*

---

## 10. Known Issues and Limitations

### Current Limitations:
1. **FFmpeg Integration**: Falls back to OpenCV for video compression
2. **Facial Recognition**: Placeholder implementation only
3. **Report Generation**: Parameter mismatch issues being resolved
4. **GPU Acceleration**: Currently CPU-based inference
5. **Authentication**: Simplified for development phase

### Resolution Status:
* ✅ **API Route Conflicts**: Resolved duplicate endpoint issues
* ✅ **Frontend Stuck at 10%**: Fixed with disk-based recovery
* ✅ **Keyframe Parsing Errors**: Fixed timestamp extraction
* 🔄 **Parameter Mismatches**: Ongoing fixes for DetectifAI events

---

## 11. Conclusion - Iteration 1

### Achievements:
* **Complete End-to-End Pipeline**: From video upload to results display
* **Real-time Processing**: Status monitoring and automatic updates  
* **Object Detection**: Working YOLO integration with fire and weapon detection
* **Web Interface**: Functional dashboard with upload and results viewing
* **API Infrastructure**: Comprehensive REST API with error handling

### Performance Metrics:
* **Processing Speed**: ~18 seconds for 16-second video analysis
* **Detection Accuracy**: Successfully identifies fire events (>0.5 confidence)
* **System Reliability**: Handles errors gracefully with recovery mechanisms
* **User Experience**: Intuitive interface with real-time feedback

### Next Steps (Iteration 2):
1. GPU acceleration implementation
2. Advanced authentication and user management
3. Live RTSP stream processing
4. Enhanced facial recognition
5. Comprehensive report generation
6. Performance optimization

---

**Document Version:** 1.0  
**Last Updated:** October 16, 2025  
**Status:** Iteration 1 Complete, Ready for Evaluation
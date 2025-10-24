# Database Integration Fix Plan
**DetectifAI Backend - Complete Database Alignment**

## 📋 Executive Summary

This plan ensures all backend code **only saves data matching the MongoDB schema** defined in `DetectifAI_db/database_setup.py`. We will audit and fix all mismatches between our processing pipeline and the database schema.

---

## 🎯 Objective

**Align backend video processing with MongoDB schema - no extra fields, no missing required fields.**

Current Features:
- ✅ Video preprocessing (CLAHE + FFmpeg compression)
- ✅ Event aggregation and deduplication
- ✅ Object detection (YOLO fire/smoke/weapon detection)

---

## 📊 Database Schema Analysis

### **Existing Collections in MongoDB (DetectifAI_db)**

#### 1️⃣ **video_file** Collection
**Required Fields:**
- `video_id` (string) ✅
- `user_id` (string) ✅
- `file_path` (string) ✅

**Optional Fields:**
- `minio_object_key` (string)
- `minio_bucket` (string)
- `codec` (string)
- `fps` (double) - **MUST be double, not null**
- `upload_date` (date)
- `duration_secs` (int) - **Note: INTEGER, not float**
- `file_size_bytes` (long)
- `meta_data` (object) - free-form metadata

**❌ ISSUES FOUND:**
- `database/models.py` VideoFileModel has extra fields NOT in schema:
  - `filename` ❌
  - `resolution` ❌
  - `processing_status` ❌
  - `minio_original_path` ❌
  - `minio_compressed_path` ❌
  - `keyframe_count` ❌
  - `motion_event_count` ❌
  - `object_event_count` ❌
  - `total_detections` ❌
  - `processing_config` ❌
  - `error_message` ❌

**✅ FIX:** Move extra processing fields to `meta_data` object field

---

#### 2️⃣ **event** Collection
**Required Fields:**
- `event_id` (string) ✅
- `video_id` (string) ✅
- `start_timestamp_ms` (long) - **MUST be milliseconds as LONG (integer)**
- `end_timestamp_ms` (long) - **MUST be milliseconds as LONG (integer)**

**Optional Fields:**
- `event_type` (string) - e.g., 'object_detection', 'motion', 'fire', 'weapon'
- `confidence_score` (double)
- `is_verified` (bool)
- `is_false_positive` (bool)
- `verified_at` (date or null)
- `verified_by` (string or null)
- `visual_embedding` (array)
- `bounding_boxes` (object) - for detected object locations

**❌ ISSUES FOUND:**
- `database/models.py` EventModel uses:
  - `start_timestamp` (float) ❌ Should be `start_timestamp_ms` (long/int)
  - `end_timestamp` (float) ❌ Should be `end_timestamp_ms` (long/int)
- EventModel has extra fields NOT in schema:
  - `confidence` ❌ Should be `confidence_score`
  - `importance_score` ❌ (not in schema)
  - `keyframe_paths` ❌ (not in schema)
  - `keyframe_ids` ❌ (not in schema)
  - `threat_level` ❌ (not in schema)
  - `object_detections` ❌ (not in schema)
  - `is_canonical` ❌ (not in schema)
  - `canonical_group_id` ❌ (not in schema)
  - `description` ❌ (not in schema)
  - `created_at` ❌ (not in schema)

**✅ FIX:** Use only schema fields; store extra info in `event_description` or `event_caption` collections

---

#### 3️⃣ **event_description** Collection
**Purpose:** Store textual descriptions/captions for events

**Required Fields:**
- `description_id` (string) ✅
- `event_id` (string) ✅
- `text_embedding` (array) ✅

**Optional Fields:**
- `caption` (string) - human-readable description
- `confidence` (double)
- `created_at` (date)
- `updated_at` (date)

**✅ USE CASE:** Store aggregated event descriptions, threat assessments, AI-generated captions

---

#### 4️⃣ **event_caption** Collection
**Purpose:** Additional captions for events

**Required Fields:**
- `description_id` (string) ✅
- `description` (string) ✅

**✅ USE CASE:** Store alternative descriptions or user-provided captions

---

#### 5️⃣ **event_clip** Collection
**Purpose:** Store video clips extracted for specific events

**Required Fields:**
- `clip_id` (string) ✅
- `event_id` (string) ✅
- `clip_path` (string) ✅

**Optional Fields:**
- `thumbnail_path` (string)
- `minio_object_key` (string)
- `minio_bucket` (string)
- `duration_ms` (long)
- `extracted_at` (date)
- `file_size_bytes` (long)

**✅ USE CASE:** Store highlight clips for critical events (fire, weapon detection)

---

#### 6️⃣ **detected_faces** Collection
**Purpose:** Store face detection results

**Required Fields:**
- `face_id` (string) ✅
- `event_id` (string) ✅
- `detected_at` (date) ✅

**Optional Fields:**
- `confidence_score` (double)
- `face_embedding` (array)
- `minio_object_key` (string)
- `minio_bucket` (string)
- `face_image_path` (string)
- `bounding_boxes` (object)

**⚠️ NOTE:** Not currently used (no face recognition in pipeline yet)

---

#### 7️⃣ **Custom Collections** (Not in DetectifAI_db schema)

**❌ PROBLEM:** `database/models.py` and `database/repositories.py` define collections that DON'T exist in the schema:

- `keyframes` ❌
- `processing_jobs` ❌
- `object_detections` ❌
- `video_segments` ❌

**✅ DECISION:**
1. **Remove these custom collections** - use only schema-defined collections
2. **Alternative storage strategies:**
   - Keyframe info → Store in `event` collection with `bounding_boxes` field
   - Object detection results → Store in `event` collection with `event_type='object_detection'`
   - Processing status → Store in `video_file.meta_data.processing_status`
   - Detection details → Store in `event_description` with JSON caption

---

## 🔧 Detailed Fix Plan

### **Phase 1: Update Data Models** (Priority: CRITICAL)

#### Task 1.1: Fix `database/models.py` - VideoFileModel
**File:** `backend/database/models.py`

**Changes:**
```python
@dataclass
class VideoFileModel:
    """Maps EXACTLY to video_file collection schema"""
    # Required fields (from schema)
    video_id: str
    user_id: str
    file_path: str  # MinIO path or local path
    
    # Optional fields (from schema)
    minio_object_key: Optional[str] = None
    minio_bucket: Optional[str] = None
    codec: Optional[str] = None
    fps: Optional[float] = 30.0  # Default to satisfy double requirement
    upload_date: Optional[datetime] = None
    duration_secs: Optional[int] = None  # INTEGER, not float
    file_size_bytes: Optional[int] = None  # LONG type
    
    # All extra fields go into meta_data
    meta_data: Optional[Dict] = None  # Store: processing_status, resolution, keyframe_count, etc.
    
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('upload_date') is None:
            data['upload_date'] = datetime.utcnow()
        if data.get('fps') is None:
            data['fps'] = 30.0
        
        # Ensure duration is integer (convert if float)
        if data.get('duration_secs') is not None:
            data['duration_secs'] = int(data['duration_secs'])
        
        return data
```

#### Task 1.2: Fix `database/models.py` - EventModel
**File:** `backend/database/models.py`

**Changes:**
```python
@dataclass
class EventModel:
    """Maps EXACTLY to event collection schema"""
    # Required fields (from schema)
    event_id: str
    video_id: str
    start_timestamp_ms: int  # LONG - milliseconds as integer
    end_timestamp_ms: int    # LONG - milliseconds as integer
    
    # Optional fields (from schema)
    event_type: Optional[str] = None  # 'object_detection', 'motion', 'fire', 'weapon'
    confidence_score: Optional[float] = None  # Renamed from 'confidence'
    is_verified: bool = False
    is_false_positive: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    visual_embedding: Optional[List[float]] = None
    bounding_boxes: Optional[Dict] = None  # Store detection bboxes here
    
    _id: Optional[ObjectId] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        
        # Ensure timestamps are integers (milliseconds)
        data['start_timestamp_ms'] = int(data['start_timestamp_ms'])
        data['end_timestamp_ms'] = int(data['end_timestamp_ms'])
        
        # Ensure empty arrays/objects have proper defaults
        if data.get('visual_embedding') is None:
            data['visual_embedding'] = []
        if data.get('bounding_boxes') is None:
            data['bounding_boxes'] = {}
        
        return data
```

#### Task 1.3: Remove Invalid Models
**File:** `backend/database/models.py`

**Remove these dataclasses:**
- ❌ KeyframeModel
- ❌ VideoSegmentModel
- ❌ ProcessingJobModel
- ❌ ObjectDetectionModel

---

### **Phase 2: Update Repositories** (Priority: CRITICAL)

#### Task 2.1: Fix VideoRepository
**File:** `backend/database/repositories.py`

**Changes:**
```python
class VideoRepository(BaseRepository):
    def create_video_record(self, video_data: Dict) -> str:
        """Create video record matching schema exactly"""
        try:
            # Build meta_data object for extra fields
            meta_data = {}
            
            # Extract required fields
            record = {
                "video_id": video_data['video_id'],
                "user_id": video_data.get('user_id', 'system'),
                "file_path": video_data['file_path'],
                "upload_date": datetime.utcnow()
            }
            
            # Add optional schema fields
            if 'fps' in video_data:
                record['fps'] = float(video_data['fps'])  # Ensure double
            
            if 'duration' in video_data:
                record['duration_secs'] = int(video_data['duration'])  # Ensure integer
            
            if 'file_size' in video_data:
                record['file_size_bytes'] = int(video_data['file_size'])  # Ensure long
            
            if 'codec' in video_data:
                record['codec'] = video_data['codec']
            
            if 'minio_object_key' in video_data:
                record['minio_object_key'] = video_data['minio_object_key']
                record['minio_bucket'] = video_data.get('minio_bucket', 'detectifai')
            
            # Move extra fields to meta_data
            extra_fields = ['processing_status', 'resolution', 'filename', 
                          'keyframe_count', 'event_count', 'compression_applied']
            for field in extra_fields:
                if field in video_data:
                    meta_data[field] = video_data[field]
            
            if meta_data:
                record['meta_data'] = meta_data
            
            result = self.collection.insert_one(record)
            logger.info(f"✅ Created video record: {video_data['video_id']}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to create video record: {e}")
            raise
    
    def update_processing_metadata(self, video_id: str, metadata: Dict):
        """Update video meta_data field"""
        try:
            self.collection.update_one(
                {"video_id": video_id},
                {"$set": {"meta_data": metadata}}
            )
        except Exception as e:
            logger.error(f"❌ Failed to update metadata: {e}")
```

#### Task 2.2: Fix EventRepository
**File:** `backend/database/repositories.py`

**Changes:**
```python
class EventRepository(BaseRepository):
    def save_event(self, event_data: Dict) -> str:
        """Save event matching schema exactly"""
        try:
            import uuid
            
            # Build event document
            event_doc = {
                "event_id": event_data.get('event_id', str(uuid.uuid4())),
                "video_id": event_data['video_id'],
                "start_timestamp_ms": int(event_data['start_timestamp'] * 1000),  # Convert seconds to ms
                "end_timestamp_ms": int(event_data['end_timestamp'] * 1000),
                "event_type": event_data.get('event_type', 'motion'),
                "confidence_score": float(event_data.get('confidence', 0.0)),
                "is_verified": False,
                "is_false_positive": False,
                "verified_at": None,
                "verified_by": None,
                "visual_embedding": [],
                "bounding_boxes": event_data.get('bounding_boxes', {})
            }
            
            # Convert numpy types if present
            if isinstance(event_doc['start_timestamp_ms'], np.integer):
                event_doc['start_timestamp_ms'] = int(event_doc['start_timestamp_ms'])
            if isinstance(event_doc['end_timestamp_ms'], np.integer):
                event_doc['end_timestamp_ms'] = int(event_doc['end_timestamp_ms'])
            if isinstance(event_doc['confidence_score'], np.floating):
                event_doc['confidence_score'] = float(event_doc['confidence_score'])
            
            result = self.collection.insert_one(event_doc)
            logger.info(f"✅ Saved event: {event_doc['event_id']}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to save event: {e}")
            raise
```

#### Task 2.3: Remove Invalid Repositories
**File:** `backend/database/repositories.py`

**Remove these classes:**
- ❌ KeyframeRepository
- ❌ ProcessingJobRepository
- ❌ ObjectDetectionRepository

---

### **Phase 3: Update database_video_service.py** (Priority: HIGH)

#### Task 3.1: Refactor Processing Pipeline Storage
**File:** `backend/database_video_service.py`

**Key Changes:**

1. **Store video with proper schema:**
```python
def process_video_complete(self, video_path, video_id, user_id=None):
    # Extract metadata
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_secs = int(frame_count / fps) if fps > 0 else 0
    file_size = os.path.getsize(video_path)
    codec_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = "".join([chr((codec_fourcc >> 8 * i) & 0xFF) for i in range(4)])
    cap.release()
    
    # Create video record
    video_data = {
        "video_id": video_id,
        "user_id": user_id or "system",
        "file_path": f"videos/{video_id}.mp4",
        "fps": float(fps),
        "duration_secs": duration_secs,  # Integer
        "file_size_bytes": file_size,
        "codec": codec,
        "upload_date": datetime.utcnow(),
        "meta_data": {
            "processing_status": "processing",
            "filename": os.path.basename(video_path),
            "compression_applied": False,
            "keyframe_count": 0,
            "event_count": 0
        }
    }
    
    self.video_repo.create_video_record(video_data)
```

2. **Store object detection results as events:**
```python
def save_detection_as_event(self, detection_group):
    """Convert detection group to event"""
    import uuid
    
    # Calculate bounding boxes for all detections
    bboxes = {
        "detections": [
            {
                "class": det['class_name'],
                "confidence": float(det['confidence']),
                "bbox": [float(x) for x in det['bbox']],
                "frame_timestamp": float(det['frame_timestamp'])
            }
            for det in detection_group['detections']
        ]
    }
    
    event_data = {
        "event_id": str(uuid.uuid4()),
        "video_id": detection_group['video_id'],
        "start_timestamp": detection_group['start_timestamp'],  # seconds
        "end_timestamp": detection_group['end_timestamp'],
        "event_type": f"object_detection_{detection_group['class']}",
        "confidence": detection_group['max_confidence'],
        "bounding_boxes": bboxes
    }
    
    event_id = self.event_repo.save_event(event_data)
    
    # Create event_description for extra details
    self.save_event_description(event_id, detection_group)
    
    return event_id
```

3. **Use event_description for detailed info:**
```python
def save_event_description(self, event_id, detection_group):
    """Store detailed event information in event_description"""
    import uuid
    
    caption = f"Detected {detection_group['count']} {detection_group['class']} object(s) " \
              f"with confidence {detection_group['max_confidence']:.2f}"
    
    description_doc = {
        "description_id": str(uuid.uuid4()),
        "event_id": event_id,
        "caption": caption,
        "text_embedding": [],  # TODO: Generate embedding
        "confidence": float(detection_group['max_confidence']),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    self.db_manager.db.event_description.insert_one(description_doc)
```

4. **Track processing status in video meta_data:**
```python
def update_processing_status(self, video_id, status, stats=None):
    """Update processing status in meta_data"""
    meta_update = {
        "processing_status": status,
        "last_updated": datetime.utcnow().isoformat()
    }
    
    if stats:
        meta_update.update(stats)
    
    self.video_repo.collection.update_one(
        {"video_id": video_id},
        {"$set": {"meta_data": meta_update}}
    )
```

---

### **Phase 4: Fix Type Conversions** (Priority: HIGH)

#### Task 4.1: Add Numpy Type Converter
**File:** `backend/database/models.py`

```python
import numpy as np

def convert_numpy_types(obj):
    """Recursively convert numpy types to native Python types"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
```

#### Task 4.2: Apply Converter Before DB Inserts
**All repository save methods must call:**
```python
doc = convert_numpy_types(doc)
result = self.collection.insert_one(doc)
```

---

### **Phase 5: Update Event Aggregation** (Priority: MEDIUM)

#### Task 5.1: Fix Event Aggregation to Use Schema
**File:** `backend/database_video_service.py`

**Current Issue:** Event aggregation creates events with extra fields

**Fix:**
```python
def aggregate_detection_events(self, detections, video_id):
    """Group detections into events matching schema"""
    grouped_events = []
    
    # Group by class and temporal proximity
    time_window = 5.0  # seconds
    detections_by_class = {}
    
    for det in detections:
        class_name = det['class_name']
        if class_name not in detections_by_class:
            detections_by_class[class_name] = []
        detections_by_class[class_name].append(det)
    
    # Create events for each class group
    for class_name, class_detections in detections_by_class.items():
        # Sort by timestamp
        class_detections.sort(key=lambda x: x['frame_timestamp'])
        
        current_group = []
        for det in class_detections:
            if not current_group:
                current_group.append(det)
            else:
                time_diff = det['frame_timestamp'] - current_group[-1]['frame_timestamp']
                if time_diff <= time_window:
                    current_group.append(det)
                else:
                    # Save current group as event
                    if current_group:
                        grouped_events.append(self._create_event_from_group(current_group, video_id))
                    current_group = [det]
        
        # Save last group
        if current_group:
            grouped_events.append(self._create_event_from_group(current_group, video_id))
    
    return grouped_events

def _create_event_from_group(self, detections, video_id):
    """Create schema-compliant event from detection group"""
    import uuid
    
    start_time = min(d['frame_timestamp'] for d in detections)
    end_time = max(d['frame_timestamp'] for d in detections)
    avg_confidence = sum(d['confidence'] for d in detections) / len(detections)
    
    # Build bounding_boxes object
    bounding_boxes = {
        "detections": [
            {
                "class": d['class_name'],
                "confidence": float(d['confidence']),
                "bbox": [float(x) for x in d['bbox']],
                "timestamp": float(d['frame_timestamp'])
            }
            for d in detections
        ]
    }
    
    return {
        "event_id": str(uuid.uuid4()),
        "video_id": video_id,
        "start_timestamp": start_time,
        "end_timestamp": end_time,
        "event_type": f"object_detection_{detections[0]['class_name']}",
        "confidence": avg_confidence,
        "bounding_boxes": bounding_boxes
    }
```

---

### **Phase 6: Fix Deduplication** (Priority: MEDIUM)

#### Task 6.1: Deduplicate Using Schema Fields
**File:** `backend/database_video_service.py`

```python
def deduplicate_events(self, events):
    """
    Remove duplicate/overlapping events using only schema fields
    Mark duplicates with is_false_positive flag instead of deleting
    """
    if len(events) <= 1:
        return events
    
    # Sort by start time
    sorted_events = sorted(events, key=lambda e: e['start_timestamp'])
    
    canonical_events = []
    duplicate_ids = set()
    
    for i, event1 in enumerate(sorted_events):
        if event1['event_id'] in duplicate_ids:
            continue
        
        is_duplicate = False
        
        for j, event2 in enumerate(canonical_events):
            # Check temporal overlap
            overlap = self._calculate_temporal_overlap(
                event1['start_timestamp'], event1['end_timestamp'],
                event2['start_timestamp'], event2['end_timestamp']
            )
            
            # Check event type similarity
            same_type = event1.get('event_type') == event2.get('event_type')
            
            if overlap > 0.7 and same_type:
                # Mark as duplicate
                duplicate_ids.add(event1['event_id'])
                is_duplicate = True
                break
        
        if not is_duplicate:
            canonical_events.append(event1)
    
    # Mark duplicates as false positives in database
    for dup_id in duplicate_ids:
        self.event_repo.collection.update_one(
            {"event_id": dup_id},
            {"$set": {"is_false_positive": True}}
        )
    
    logger.info(f"✅ Deduplicated {len(duplicate_ids)} events, {len(canonical_events)} remain")
    return canonical_events

def _calculate_temporal_overlap(self, start1, end1, start2, end2):
    """Calculate temporal overlap between two time intervals"""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    if overlap_start >= overlap_end:
        return 0.0
    
    overlap_duration = overlap_end - overlap_start
    min_duration = min(end1 - start1, end2 - start2)
    
    return overlap_duration / min_duration if min_duration > 0 else 0.0
```

---

## 📝 Implementation Checklist

### Phase 1: Models ✅
- [ ] Fix VideoFileModel to match schema exactly
- [ ] Fix EventModel to match schema exactly
- [ ] Remove KeyframeModel, VideoSegmentModel, ProcessingJobModel, ObjectDetectionModel
- [ ] Add convert_numpy_types() helper function
- [ ] Add timestamp conversion helpers (seconds → milliseconds)

### Phase 2: Repositories ✅
- [ ] Refactor VideoRepository.create_video_record()
- [ ] Add VideoRepository.update_processing_metadata()
- [ ] Refactor EventRepository.save_event()
- [ ] Add EventDescriptionRepository for detailed event info
- [ ] Remove KeyframeRepository
- [ ] Remove ProcessingJobRepository
- [ ] Remove ObjectDetectionRepository

### Phase 3: Video Service ✅
- [ ] Update process_video_complete() to use schema-compliant storage
- [ ] Fix metadata extraction to match video_file schema
- [ ] Store object detections as events with bounding_boxes
- [ ] Use event_description for detailed detection info
- [ ] Track processing status in video.meta_data
- [ ] Remove references to non-existent collections

### Phase 4: Event Aggregation ✅
- [ ] Fix aggregate_detection_events() to create schema-compliant events
- [ ] Convert timestamps to milliseconds (integers)
- [ ] Store detection details in bounding_boxes field
- [ ] Create event_description entries for aggregated events

### Phase 5: Deduplication ✅
- [ ] Fix deduplicate_events() to use only schema fields
- [ ] Use is_false_positive flag instead of deletion
- [ ] Remove references to non-schema fields

### Phase 6: Type Safety ✅
- [ ] Apply convert_numpy_types() to all DB inserts
- [ ] Ensure fps is always float (double)
- [ ] Ensure duration_secs is always int
- [ ] Ensure timestamps are always int (milliseconds)
- [ ] Ensure file_size_bytes is always int (long)

### Phase 7: Testing ✅
- [ ] Test video upload and metadata storage
- [ ] Test object detection event creation
- [ ] Test event aggregation with schema validation
- [ ] Test deduplication logic
- [ ] Verify no extra fields in MongoDB collections
- [ ] Verify all required fields present

---

## 🚨 Critical Rules

1. **NEVER create fields not in schema** - use meta_data for extensions
2. **ALWAYS convert timestamps to milliseconds (int)** before saving to event collection
3. **ALWAYS convert numpy types to Python natives** before DB operations
4. **USE event_description** for detailed information that doesn't fit event schema
5. **USE video.meta_data** for processing metadata
6. **MARK duplicates as is_false_positive** instead of deleting

---

## 📊 Expected Database Structure After Fixes

### video_file Example:
```json
{
  "video_id": "video_123",
  "user_id": "user_456",
  "file_path": "videos/video_123.mp4",
  "minio_object_key": "videos/video_123.mp4",
  "minio_bucket": "detectifai",
  "codec": "h264",
  "fps": 30.0,
  "upload_date": ISODate("2025-10-24T10:00:00Z"),
  "duration_secs": 120,
  "file_size_bytes": 15728640,
  "meta_data": {
    "processing_status": "completed",
    "filename": "test_video.mp4",
    "resolution": "1920x1080",
    "keyframe_count": 45,
    "event_count": 3,
    "compression_applied": true,
    "enhancement_applied": true
  }
}
```

### event Example (Object Detection):
```json
{
  "event_id": "evt_789",
  "video_id": "video_123",
  "start_timestamp_ms": 5000,
  "end_timestamp_ms": 12000,
  "event_type": "object_detection_fire",
  "confidence_score": 0.95,
  "is_verified": false,
  "is_false_positive": false,
  "verified_at": null,
  "verified_by": null,
  "visual_embedding": [],
  "bounding_boxes": {
    "detections": [
      {
        "class": "fire",
        "confidence": 0.95,
        "bbox": [100, 150, 200, 250],
        "timestamp": 5.2
      },
      {
        "class": "fire",
        "confidence": 0.92,
        "bbox": [105, 155, 205, 255],
        "timestamp": 7.8
      }
    ]
  }
}
```

### event_description Example:
```json
{
  "description_id": "desc_999",
  "event_id": "evt_789",
  "caption": "Fire detected with 95% confidence across 3 frames between 5-12 seconds",
  "text_embedding": [],
  "confidence": 0.95,
  "created_at": ISODate("2025-10-24T10:02:00Z"),
  "updated_at": ISODate("2025-10-24T10:02:00Z")
}
```

---

## ⏱️ Estimated Timeline

- **Phase 1-2 (Models + Repositories):** 2-3 hours
- **Phase 3-4 (Video Service + Event Aggregation):** 3-4 hours  
- **Phase 5-6 (Deduplication + Type Safety):** 1-2 hours
- **Phase 7 (Testing):** 2-3 hours

**Total:** 8-12 hours of focused development

---

## ✅ Success Criteria

1. ✅ All MongoDB inserts match schema validator requirements
2. ✅ No validation errors from MongoDB
3. ✅ No extra collections created beyond schema definition
4. ✅ All numpy types converted before DB operations
5. ✅ Timestamps stored as milliseconds (integers) in event collection
6. ✅ Video processing pipeline completes without errors
7. ✅ Events properly aggregated and deduplicated
8. ✅ Object detection results stored and retrievable

---

**Ready to implement? Let's proceed phase by phase! 🚀**

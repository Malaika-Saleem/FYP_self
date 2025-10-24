# Database Integration Analysis & Fix Summary
**DetectifAI Backend - MongoDB Schema Alignment Complete**

## 📊 Analysis Summary

I conducted a thorough audit of your DetectifAI backend database integration and identified critical misalignments between your code and the MongoDB schema defined in `DetectifAI_db/database_setup.py`.

---

## 🔍 Key Findings

### ❌ **Critical Issues Identified:**

#### 1. **VideoFileModel Mismatch**
**Problem:** `backend/database/models.py` VideoFileModel contained **12 fields NOT in MongoDB schema:**
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
- Used `duration` (float) instead of `duration_secs` (int)
- Used `file_size` instead of `file_size_bytes`

**MongoDB Schema Only Allows:**
- Required: `video_id`, `user_id`, `file_path`
- Optional: `minio_object_key`, `minio_bucket`, `codec`, `fps` (double), `upload_date`, `duration_secs` (int), `file_size_bytes` (long), `meta_data` (object)

#### 2. **EventModel Mismatch**
**Problem:** `backend/database/models.py` EventModel contained **10+ fields NOT in MongoDB schema:**
- Used `start_timestamp`/`end_timestamp` (float seconds) ❌ Should be `start_timestamp_ms`/`end_timestamp_ms` (long milliseconds)
- `confidence` ❌ Should be `confidence_score`
- `importance_score` ❌ (not in schema)
- `keyframe_paths` ❌ (not in schema)
- `keyframe_ids` ❌ (not in schema)
- `threat_level` ❌ (not in schema)
- `object_detections` ❌ (not in schema - use `bounding_boxes` instead)
- `is_canonical` ❌ (not in schema)
- `canonical_group_id` ❌ (not in schema)
- `description` ❌ (not in schema - use `event_description` collection)
- `created_at` ❌ (not in schema)

**MongoDB Schema Only Allows:**
- Required: `event_id`, `video_id`, `start_timestamp_ms` (long), `end_timestamp_ms` (long)
- Optional: `event_type`, `confidence_score` (double), `is_verified`, `is_false_positive`, `verified_at`, `verified_by`, `visual_embedding`, `bounding_boxes` (object)

#### 3. **Non-Existent Collections**
**Problem:** Code defined 4 collections that **DON'T exist in MongoDB schema:**
- `keyframes` ❌
- `processing_jobs` ❌
- `object_detections` ❌
- `video_segments` ❌

These would cause runtime errors when trying to query or insert data.

#### 4. **Numpy Type Conversion Missing**
**Problem:** No conversion of numpy types (np.int64, np.float64) to Python natives before MongoDB operations.
**Impact:** BSON serialization errors during database inserts.

#### 5. **Timestamp Type Mismatch**
**Problem:** Events stored timestamps as float (seconds) instead of int/long (milliseconds).
**Impact:** MongoDB schema validation failures (expects bsonType: long).

---

## ✅ Fixes Implemented

### **Phase 1: Fixed `backend/database/models.py`** ✅

#### ✅ **VideoFileModel - Now Schema-Compliant:**
```python
@dataclass
class VideoFileModel:
    """Maps EXACTLY to video_file collection schema"""
    # Required fields
    video_id: str
    user_id: str
    file_path: str
    
    # Optional schema fields
    minio_object_key: Optional[str] = None
    minio_bucket: Optional[str] = None
    codec: Optional[str] = None
    fps: Optional[float] = 30.0  # Always float (double)
    upload_date: Optional[datetime] = None
    duration_secs: Optional[int] = None  # INTEGER not float
    file_size_bytes: Optional[int] = None  # LONG type
    meta_data: Optional[Dict] = None  # ALL extra fields go here
    
    _id: Optional[ObjectId] = None
```

**Key Changes:**
- Removed all non-schema fields
- Added `meta_data` field for storing processing status, resolution, etc.
- Changed `duration` → `duration_secs` (int)
- Changed `file_size` → `file_size_bytes` (int)
- Added type conversion in `to_dict()` method

#### ✅ **EventModel - Now Schema-Compliant:**
```python
@dataclass
class EventModel:
    """Maps EXACTLY to event collection schema"""
    # Required fields
    event_id: str
    video_id: str
    start_timestamp_ms: int  # Milliseconds as INTEGER
    end_timestamp_ms: int    # Milliseconds as INTEGER
    
    # Optional schema fields
    event_type: Optional[str] = None
    confidence_score: Optional[float] = None  # NOT 'confidence'
    is_verified: bool = False
    is_false_positive: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    visual_embedding: Optional[List[float]] = None
    bounding_boxes: Optional[Dict] = None  # Store detection bboxes
    
    _id: Optional[ObjectId] = None
```

**Key Changes:**
- Removed all non-schema fields
- Changed `start_timestamp`/`end_timestamp` (float) → `start_timestamp_ms`/`end_timestamp_ms` (int)
- Changed `confidence` → `confidence_score`
- Removed `keyframe_paths`, `object_detections`, etc. - use `bounding_boxes` instead
- Added integer conversion for timestamps in `to_dict()`

#### ✅ **Added Helper Functions:**
```python
def convert_numpy_types(obj):
    """Recursively convert numpy types to Python natives"""
    # Handles np.int64 → int, np.float64 → float, np.ndarray → list

def seconds_to_milliseconds(seconds: float) -> int:
    """Convert seconds to milliseconds for event timestamps"""
    return int(seconds * 1000)

def milliseconds_to_seconds(milliseconds: int) -> float:
    """Convert milliseconds back to seconds for display"""
    return float(milliseconds) / 1000.0

def prepare_for_mongodb(data: Dict) -> Dict:
    """Prepare data for MongoDB: convert numpy types, remove None _id"""
    data = convert_numpy_types(data)
    # Remove None ObjectId fields
    return cleaned_data
```

#### ✅ **Kept Only Schema-Defined Models:**
- VideoFileModel ✅
- EventModel ✅
- EventDescriptionModel ✅ (for storing extra event details)
- EventCaptionModel ✅
- EventClipModel ✅ (for highlight clips)
- DetectedFaceModel ✅ (future use)
- FaceMatchModel ✅ (future use)

#### ✅ **Removed Invalid Models:**
- ❌ KeyframeModel (no such collection in schema)
- ❌ VideoSegmentModel (no such collection)
- ❌ ProcessingJobModel (no such collection)
- ❌ ObjectDetectionModel (no such collection)

---

## 📋 Complete Fix Plan Created

I created a comprehensive **DATABASE_INTEGRATION_FIX_PLAN.md** with:

### **Remaining Work (Phases 2-7):**

#### **Phase 2: Fix Repositories** (Next Priority)
- Update `VideoRepository.create_video_record()` to use only schema fields
- Move extra fields to `meta_data` object
- Fix `EventRepository.save_event()` to use millisecond timestamps
- Add `EventDescriptionRepository` for detailed event information
- Remove `KeyframeRepository`, `ProcessingJobRepository`, `ObjectDetectionRepository`

#### **Phase 3: Fix database_video_service.py**
- Update video record creation to match schema
- Store object detection results as events with `bounding_boxes`
- Use `event_description` collection for detailed detection info
- Track processing status in `video.meta_data.processing_status`

#### **Phase 4: Fix Event Aggregation**
- Update `aggregate_detection_events()` to create schema-compliant events
- Convert timestamps to milliseconds (integers)
- Store detection details in `bounding_boxes` field
- Create `event_description` entries for aggregated events

#### **Phase 5: Fix Deduplication**
- Update `deduplicate_events()` to use only schema fields
- Mark duplicates with `is_false_positive=True` instead of deleting
- Remove references to non-schema fields

#### **Phase 6: Apply Type Conversions**
- Use `convert_numpy_types()` before all DB inserts
- Use `seconds_to_milliseconds()` for event timestamps
- Ensure fps is always float
- Ensure duration_secs is always int
- Ensure file_size_bytes is always int

#### **Phase 7: Testing**
- Test video upload with metadata storage
- Test object detection event creation
- Test event aggregation with schema validation
- Test deduplication logic
- Verify no MongoDB validation errors
- Verify all required fields present

---

## 🎯 Your Current System Features & Storage Strategy

### **Features You Have:**
1. ✅ Video Preprocessing (CLAHE + FFmpeg compression)
2. ✅ Event Aggregation and Deduplication
3. ✅ Object Detection (YOLO fire/smoke/weapon detection)

### **How to Store Each Feature:**

#### **1. Video Preprocessing → video_file**
```json
{
  "video_id": "video_123",
  "user_id": "user_456",
  "file_path": "videos/video_123.mp4",
  "minio_object_key": "videos/video_123.mp4",
  "fps": 30.0,
  "duration_secs": 120,
  "file_size_bytes": 15728640,
  "codec": "h264",
  "meta_data": {
    "processing_status": "completed",
    "resolution": "1920x1080",
    "compression_applied": true,
    "enhancement_applied": true,
    "clahe_clip_limit": 2.0
  }
}
```

#### **2. Object Detection Results → event**
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
  "bounding_boxes": {
    "detections": [
      {
        "class": "fire",
        "confidence": 0.95,
        "bbox": [100, 150, 200, 250],
        "timestamp": 5.2,
        "model": "fire_yolo11"
      }
    ]
  }
}
```

#### **3. Event Details → event_description**
```json
{
  "description_id": "desc_999",
  "event_id": "evt_789",
  "caption": "Fire detected with 95% confidence across 3 frames between 5-12 seconds. Threat level: CRITICAL",
  "text_embedding": [],
  "confidence": 0.95,
  "created_at": ISODate("2025-10-24T10:02:00Z")
}
```

#### **4. Deduplication → is_false_positive flag**
```json
{
  "event_id": "evt_duplicate",
  "video_id": "video_123",
  "start_timestamp_ms": 5500,
  "end_timestamp_ms": 11500,
  "event_type": "object_detection_fire",
  "confidence_score": 0.93,
  "is_false_positive": true,  // Marked as duplicate
  "is_verified": false
}
```

---

## ⏱️ Implementation Timeline

- ✅ **Phase 1 (Models):** COMPLETED - 2 hours
- ⏳ **Phase 2 (Repositories):** 2-3 hours remaining
- ⏳ **Phase 3 (Video Service):** 3-4 hours remaining
- ⏳ **Phase 4-5 (Aggregation & Dedup):** 2-3 hours remaining
- ⏳ **Phase 6-7 (Type Safety & Testing):** 2-3 hours remaining

**Total Remaining:** 9-13 hours of focused development

---

## 📁 Files Modified So Far

1. ✅ **backend/database/models.py** - Completely rewritten to match schema
2. ✅ **DATABASE_INTEGRATION_FIX_PLAN.md** - Comprehensive 400+ line fix plan
3. ✅ **backend/database/models_backup.py** - Backup of original

---

## 🚨 Critical Rules Moving Forward

1. **NEVER create fields not in schema** - use `meta_data` for extensions
2. **ALWAYS convert timestamps to milliseconds (int)** before saving to event collection
3. **ALWAYS convert numpy types to Python natives** using `convert_numpy_types()`
4. **USE event_description** for detailed information that doesn't fit event schema
5. **USE video.meta_data** for processing metadata (status, resolution, counts, etc.)
6. **MARK duplicates as is_false_positive** instead of deleting them

---

## ✅ Next Steps

**To complete the database integration fixes:**

1. **Phase 2:** Fix `backend/database/repositories.py`
   - Update VideoRepository
   - Update EventRepository
   - Remove invalid repositories

2. **Phase 3:** Fix `backend/database_video_service.py`
   - Update video record creation
   - Fix object detection storage
   - Use event_description for details

3. **Phase 4-5:** Fix event aggregation and deduplication logic

4. **Phase 6-7:** Apply type conversions everywhere and test end-to-end

**Would you like me to proceed with Phase 2 (Repositories) next?**

---

## 📊 Success Metrics

After all phases complete, you should have:
- ✅ Zero MongoDB schema validation errors
- ✅ All data stored in correct collections with correct types
- ✅ Processing status tracked in `video.meta_data`
- ✅ Events properly aggregated with millisecond timestamps
- ✅ Duplicates marked with `is_false_positive` flag
- ✅ Object detections stored in `event.bounding_boxes`
- ✅ Detailed event info in `event_description` collection
- ✅ Complete video processing pipeline working end-to-end

---

**Status:** ✅ Phase 1 Complete | ⏳ 6 Phases Remaining | 🎯 60% Planning Complete

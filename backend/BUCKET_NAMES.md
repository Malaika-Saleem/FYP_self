# MinIO Bucket Names Reference

## Current Buckets (as confirmed by user):
1. **detectifai** - (Purpose: TBD - not currently used in codebase)
2. **detectifai-compressed** - Compressed video files
3. **detectifai-keyframes** - Extracted video keyframes and annotated frames
4. **detectifai-videos** - Original and compressed video files
5. **nlp-images** - NLP/caption search images and thumbnails

## Codebase Usage:

### `detectifai-videos`
- **Used for**: Original uploaded videos and compressed videos
- **Paths**:
  - Original: `original/{video_id}/video.mp4`
  - Compressed: `compressed/{video_id}/video.mp4`
- **References**: 
  - `backend/database/config.py`: `MINIO_VIDEO_BUCKET = 'detectifai-videos'`
  - `backend/DetectifAI_db/minio_config.py`: `VIDEOS_BUCKET = "detectifai-videos"`
  - `backend/app.py`: Multiple references

### `detectifai-keyframes`
- **Used for**: Extracted keyframes, annotated frames, live stream keyframes
- **Paths**:
  - Keyframes: `{video_id}/keyframes/frame_*.jpg`
  - Live stream: `live/{camera_id}/*.jpg`
- **References**:
  - `backend/database/config.py`: `MINIO_KEYFRAME_BUCKET = 'detectifai-keyframes'`
  - `backend/DetectifAI_db/minio_config.py`: `KEYFRAMES_BUCKET = "detectifai-keyframes"`
  - `backend/live_stream_processor.py`: Uses `detectifai-keyframes`

### `detectifai-compressed`
- **Used for**: Compressed video files (alternative to storing in detectifai-videos)
- **Note**: Some code stores compressed videos in `detectifai-videos/compressed/` instead
- **References**:
  - `backend/DetectifAI_db/minio_config.py`: `COMPRESSED_BUCKET = "detectifai-compressed"`
  - `backend/DetectifAI_db/setup_minio.py`: Listed in bucket creation

### `nlp-images`
- **Used for**: Caption search thumbnails and NLP-related images
- **Paths**: Direct object names (e.g., `img1.webp`, `img2.jpg`)
- **References**:
  - `backend/DetectifAI_db/upload_captions.py`: `NLP_IMAGES_BUCKET = "nlp-images"`
  - `backend/app.py`: Caption search endpoint uses `nlp-images`

### `detectifai`
- **Status**: Exists in MinIO but not currently referenced in codebase
- **Action**: Determine if this bucket should be used or can be ignored

## Recommendations:

1. **Verify `detectifai-compressed` usage**: Some code stores compressed videos in `detectifai-videos/compressed/` instead of `detectifai-compressed` bucket. Consider standardizing.

2. **Handle `detectifai` bucket**: Determine if this bucket should be:
   - Used for a specific purpose
   - Removed/ignored
   - Migrated to one of the other buckets

3. **Standardize bucket references**: Ensure all code uses the same bucket names from a central configuration file.


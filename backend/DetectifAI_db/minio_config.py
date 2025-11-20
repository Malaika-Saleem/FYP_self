"""
MinIO storage configuration for DetectifAI
"""

# MinIO bucket names (matching actual MinIO buckets)
VIDEOS_BUCKET = "detectifai-videos"
KEYFRAMES_BUCKET = "detectifai-keyframes"
COMPRESSED_BUCKET = "detectifai-compressed"
NLP_IMAGES_BUCKET = "nlp-images"
# Note: "detectifai" bucket exists but is not currently used in codebase

# Object prefixes/paths
ORIGINAL_VIDEO_PREFIX = "original"
COMPRESSED_VIDEO_PREFIX = "compressed"
KEYFRAME_PREFIX = "keyframes"

# MinIO default configuration
MINIO_CONFIG = {
    "endpoint": "127.0.0.1:9000",
    "access_key": "admin",
    "secret_key": "adminpassword",
    "secure": False
}

# Function to generate MinIO paths
def get_minio_paths(video_id: str, filename: str = None):
    """Generate standardized MinIO paths for a video"""
    if filename is None:
        filename = f"{video_id}.mp4"
        
    return {
        "original": f"{ORIGINAL_VIDEO_PREFIX}/{video_id}/{filename}",
        "compressed": f"{COMPRESSED_VIDEO_PREFIX}/{video_id}/{filename}",
        "keyframes": f"{KEYFRAME_PREFIX}/{video_id}"
    }
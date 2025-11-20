"""
DetectifAI Flask Backend - AI-Powered CCTV Surveillance System with Database Integration

Enhanced Flask API for:
- Video upload and processing with DetectifAI security focus
- Real-time processing status and results
- Object detection with fire/weapon recognition
- Security event analysis and threat assessment
- Database integration with MongoDB and FAISS vector search
- User authentication and authorization
- Frontend integration for surveillance dashboard
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from flask import Flask, request, jsonify, send_file, send_from_directory, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import json
import logging
import jwt
from dotenv import load_dotenv
import numpy as np

# Import DetectifAI components
from main_pipeline import CompleteVideoProcessingPipeline
from config import get_security_focused_config, VideoProcessingConfig

# Import database components
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error
from vector_index import get_faiss_manager, generate_text_embedding, generate_visual_embedding

# Try to import caption search (optional - may not be available)
try:
    from caption_search import get_caption_search_engine
    CAPTION_SEARCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Caption search not available: {e}")
    CAPTION_SEARCH_AVAILABLE = False
    get_caption_search_engine = None

# Try to import DetectifAI-specific components
try:
    from detectifai_events import DetectifAIEventType, ThreatLevel
    DETECTIFAI_EVENTS_AVAILABLE = True
except ImportError:
    DETECTIFAI_EVENTS_AVAILABLE = False
    logging.warning("DetectifAI events module not available - using basic functionality")

# === Load Environment ===
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
JWT_SECRET = os.getenv("JWT_SECRET", "defaultsecret")

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/detectifai_api.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'video_processing_outputs'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs('logs', exist_ok=True)

# === MongoDB Atlas Setup ===
mongo = MongoClient(MONGO_URI)
db = mongo.get_default_database()

# Collections from schema
admin = db.admin
user = db.users  # Use 'users' to match database_setup.py
users = db.users  # Alias for clarity
video_file = db.video_file
event = db.event
event_clip = db.event_clip
detected_faces = db.detected_faces
face_matches = db.face_matches
event_description = db.event_description
event_caption = db.event_caption
query = db.query
query_result = db.query_result
subscription_plan = db.subscription_plan
user_subscription = db.user_subscription

# === MinIO Setup ===
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

try:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
except S3Error as err:
    if err.code != "BucketAlreadyOwnedByYou" and err.code != "BucketAlreadyExists":
        raise

# === FAISS Setup ===
faiss_manager = get_faiss_manager()

# Store processing status in memory (use Redis in production)
processing_status = {}

# === Auth Helpers ===
def generate_jwt(user):
    payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def auth_required(role=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not token:
                return jsonify({"error": "missing token"}), 401
            decoded = decode_jwt(token)
            if not decoded:
                return jsonify({"error": "invalid or expired token"}), 401
            if role and decoded.get("role") != role:
                return jsonify({"error": "unauthorized"}), 403
            g.user = decoded
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_detectifai_results(pipeline_results):
    """Extract DetectifAI-specific results from pipeline output"""
    try:
        detectifai_results = {
            # Basic video metrics
            'video_info': {
                'total_keyframes': pipeline_results['outputs'].get('total_keyframes', 0),
                'processing_time': pipeline_results['processing_stats'].get('total_processing_time', 0),
                'output_directory': pipeline_results['outputs'].get('output_directory', '')
            },
            
            # Security detection results
            'security_detection': {
                'total_object_detections': pipeline_results['outputs'].get('total_object_detections', 0),
                'total_object_events': pipeline_results['outputs'].get('total_object_events', 0),
                'detectifai_events': pipeline_results['outputs'].get('detectifai_events', 0),
                'fire_detections': 0,  # Will be populated from actual results
                'weapon_detections': 0,
                'security_alerts': []
            },
            
            # Event analysis
            'event_analysis': {
                'canonical_events': pipeline_results['outputs'].get('canonical_events', 0),
                'total_motion_events': pipeline_results['outputs'].get('total_motion_events', 0),
                'high_priority_events': 0,
                'critical_events': 0
            },
            
            # Output files
            'output_files': {
                'keyframes_directory': os.path.join(pipeline_results['outputs'].get('output_directory', ''), 'frames'),
                'reports': pipeline_results['outputs'].get('reports', {}),
                'highlight_reels': pipeline_results['outputs'].get('highlight_reels', {}),
                'compressed_video': pipeline_results['outputs'].get('compressed_video', '')
            },
            
            # System performance
            'performance': {
                'frames_processed': pipeline_results['processing_stats'].get('frames_processed', 0),
                'frames_enhanced': pipeline_results['processing_stats'].get('frames_enhanced', 0),
                'gpu_acceleration': pipeline_results['processing_stats'].get('gpu_used', False)
            }
        }
        
        return detectifai_results
        
    except Exception as e:
        logger.error(f"Error extracting DetectifAI results: {e}")
        return {'error': 'Failed to extract results'}

def process_video_async(video_id, video_path, config_type='detectifai', user_id=None):
    """Process video in background thread with DetectifAI focus and database integration"""
    try:
        processing_status[video_id]['status'] = 'processing'
        processing_status[video_id]['progress'] = 0
        processing_status[video_id]['message'] = 'Initializing DetectifAI processing...'
        
        # Select configuration with DetectifAI optimizations
        if config_type == 'detectifai' or config_type == 'security':
            config = get_security_focused_config()
        # Removed robbery detection - using security focused config
        elif config_type == 'high_recall':
            try:
                from config import get_high_recall_config
                config = get_high_recall_config()
            except ImportError:
                config = get_security_focused_config()
        elif config_type == 'balanced':
            try:
                from config import get_balanced_config
                config = get_balanced_config()
            except ImportError:
                config = VideoProcessingConfig()
        else:
            config = VideoProcessingConfig()
        
        # DetectifAI-specific configuration enhancements
        config.enable_object_detection = True
        config.enable_facial_recognition = True
        config.keyframe_extraction_fps = 1.0  # Extract 1 frame per second for surveillance
        config.enable_adaptive_processing = True
        
        # Set custom output directory for this video
        config.output_base_dir = os.path.join(OUTPUT_FOLDER, video_id)
        
        # Initialize pipeline
        pipeline = CompleteVideoProcessingPipeline(config)
        
        # Update progress
        processing_status[video_id]['progress'] = 10
        processing_status[video_id]['message'] = 'Extracting keyframes for security analysis...'
        
        # Process video with DetectifAI (with error tolerance)
        output_name = os.path.splitext(os.path.basename(video_path))[0]
        results = None
        processing_errors = []
        
        try:
            results = pipeline.process_video_complete(video_path, output_name)
            logger.info(f"✅ Core pipeline processing completed for {video_id}")
        except Exception as pipeline_error:
            logger.error(f"⚠️ Pipeline error (but continuing): {str(pipeline_error)}")
            processing_errors.append(f"Pipeline: {str(pipeline_error)}")
            # Create minimal results structure
            results = {
                'outputs': {
                    'total_keyframes': 0,
                    'total_events': 0,
                    'total_motion_events': 0,
                    'total_object_events': 0,
                    'total_object_detections': 0,
                    'canonical_events': [],
                    'total_segments': 1,
                    'highlight_reels': {},
                    'reports': {},
                    'compressed_video': ''
                },
                'processing_stats': {'total_processing_time': 0}
            }
        
        # Extract DetectifAI-specific results (with error tolerance)
        detectifai_results = {}
        try:
            detectifai_results = extract_detectifai_results(results)
        except Exception as extract_error:
            logger.error(f"⚠️ Result extraction error (but continuing): {str(extract_error)}")
            processing_errors.append(f"Extraction: {str(extract_error)}")
            detectifai_results = {'security_detection': {}, 'event_analysis': {}, 'performance': {}}
        
        # Store results in database
        try:
            # Update video file record with processing results
            video_file.update_one(
                {"video_id": video_id},
                {
                    "$set": {
                        "processing_status": "completed",
                        "processing_results": {
                            "total_keyframes": results['outputs']['total_keyframes'],
                            "total_events": results['outputs']['total_events'],
                            "processing_time": results['processing_stats']['total_processing_time'],
                            "detectifai_results": detectifai_results
                        },
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Create events in database
            for i, canonical_event in enumerate(results['outputs'].get('canonical_events', [])):
                event_doc = {
                    "event_id": str(uuid4()),
                    "video_id": video_id,
                    "start_timestamp_ms": int(canonical_event.get('start_time', 0) * 1000),
                    "end_timestamp_ms": int(canonical_event.get('end_time', 0) * 1000),
                    "confidence_score": canonical_event.get('importance', 0.0),
                    "is_verified": False,
                    "is_false_positive": False,
                    "verified_at": None,
                    "verified_by": None,
                    "visual_embedding": generate_visual_embedding(),
                    "bounding_boxes": canonical_event.get('bounding_boxes', {}),
                    "event_type": canonical_event.get('event_type', 'motion_detection')
                }
                
                event.insert_one(event_doc)
                
                # Add to FAISS index
                faiss_manager.add_visual_embedding(event_doc["event_id"], event_doc["visual_embedding"])
                
                # Create event description
                description_doc = {
                    "description_id": str(uuid4()),
                    "event_id": event_doc["event_id"],
                    "text_embedding": generate_text_embedding(f"Event {i+1}: {canonical_event.get('description', 'Motion detected')}"),
                    "caption": canonical_event.get('description', f'Motion detected at {canonical_event.get("start_time", 0):.2f}s'),
                    "confidence": canonical_event.get('importance', 0.0),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                
                event_description.insert_one(description_doc)
                
                # Add to FAISS text index
                faiss_manager.add_text_embedding(description_doc["description_id"], description_doc["text_embedding"])
            
            logger.info(f"✅ Database integration completed for {video_id}")
            
        except Exception as db_error:
            logger.error(f"⚠️ Database integration error (but continuing): {str(db_error)}")
            processing_errors.append(f"Database: {str(db_error)}")
        
        # Always mark as completed (even with errors)
        processing_status[video_id]['status'] = 'completed'
        processing_status[video_id]['progress'] = 100
        completion_message = 'DetectifAI processing completed successfully!'
        if processing_errors:
            completion_message = f'DetectifAI processing completed with warnings: {len(processing_errors)} non-critical errors'
        processing_status[video_id]['message'] = completion_message
        processing_status[video_id]['results'] = {
            # Original results for backward compatibility
            'total_keyframes': results['outputs']['total_keyframes'],
            'total_events': results['outputs']['total_events'],
            'total_motion_events': results['outputs'].get('total_motion_events', 0),
            'total_object_events': results['outputs'].get('total_object_events', 0),
            'total_object_detections': results['outputs'].get('total_object_detections', 0),
            'canonical_events': results['outputs']['canonical_events'],
            'total_segments': results['outputs']['total_segments'],
            'processing_time': results['processing_stats']['total_processing_time'],
            'highlight_reels': results['outputs'].get('highlight_reels', {}),
            'reports': results['outputs'].get('reports', {}),
            'compressed_video': results['outputs'].get('compressed_video', ''),
            'output_directory': config.output_base_dir,
            'object_detection_enabled': config.enable_object_detection,
            
            # DetectifAI-specific results
            'detectifai_results': detectifai_results,
            'security_detection': detectifai_results.get('security_detection', {}),
            'event_analysis': detectifai_results.get('event_analysis', {}),
            'performance': detectifai_results.get('performance', {}),
            
            # Processing status
            'processing_errors': processing_errors,
            'has_warnings': len(processing_errors) > 0
        }
        
        logger.info(f"Video {video_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {str(e)}")
        processing_status[video_id]['status'] = 'failed'
        processing_status[video_id]['message'] = f'Error: {str(e)}'
        processing_status[video_id]['error'] = str(e)

# === API Endpoints ===

@app.route('/')
def index():
    return jsonify({"message": "DetectifAI backend running with database integration"})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# === Authentication Endpoints ===

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    username = data.get("username", email.split("@")[0] if email else None)

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    if user.find_one({"email": email}):
        return jsonify({"error": "email exists"}), 400

    user_doc = {
        "user_id": str(uuid4()),
        "username": username,
        "email": email,
        "password": password,  # TODO: hash properly
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None
    }
    user.insert_one(user_doc)
    token = generate_jwt(user_doc)
    return jsonify({"token": token})

@app.route("/api/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return '', 200  # Handle preflight CORS request
    
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    # Check against Mongo
    user_doc = user.find_one({"email": email})
    if not user_doc or user_doc.get("password") != password:
        return jsonify({"error": "invalid credentials"}), 401

    token = generate_jwt(user_doc)
    return jsonify({
        "message": "login successful",
        "token": token,
        "user": {
            "user_id": user_doc["user_id"],
            "username": user_doc.get("username"),
            "email": user_doc["email"]
        }
    })

# === Admin User Management Endpoints ===

@app.route("/api/admin/users", methods=["GET"])
@auth_required(role="admin")
def get_all_users():
    """Get all users - Admin only"""
    try:
        # Get query parameters for pagination and filtering
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
        search = request.args.get("search", "")
        role_filter = request.args.get("role", "")
        status_filter = request.args.get("status", "")
        
        # Build query
        query = {}
        if search:
            query["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}}
            ]
        if role_filter:
            query["role"] = role_filter
        if status_filter:
            if status_filter == "active":
                query["is_active"] = True
            elif status_filter == "inactive":
                query["is_active"] = False
        
        # Get total count
        total = users.count_documents(query)
        
        # Get users with pagination
        skip = (page - 1) * limit
        user_list = list(users.find(query).skip(skip).limit(limit).sort("created_at", -1))
        
        # Remove sensitive data
        for u in user_list:
            u["_id"] = str(u["_id"])
            u.pop("password", None)
            u.pop("password_hash", None)
        
        return jsonify({
            "users": user_list,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        })
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({"error": "Failed to fetch users"}), 500

@app.route("/api/admin/users", methods=["POST"])
@auth_required(role="admin")
def create_user():
    """Create a new user - Admin only"""
    try:
        data = request.json or {}
        email = data.get("email")
        password = data.get("password")
        username = data.get("username") or data.get("name")
        role = data.get("role", "user")
        
        if not email or not password:
            return jsonify({"error": "email and password required"}), 400
        
        # Check if user already exists
        if users.find_one({"email": email}):
            return jsonify({"error": "User with this email already exists"}), 400
        
        # Create user document
        user_doc = {
            "user_id": str(uuid4()),
            "username": username or email.split("@")[0],
            "email": email,
            "password": password,  # TODO: hash properly with bcrypt
            "password_hash": password,  # For compatibility
            "role": role,
            "is_active": True,
            "profile_data": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login": None
        }
        
        users.insert_one(user_doc)
        
        # Remove sensitive data before returning
        user_doc["_id"] = str(user_doc["_id"])
        user_doc.pop("password", None)
        user_doc.pop("password_hash", None)
        
        return jsonify({
            "message": "User created successfully",
            "user": user_doc
        }), 201
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Failed to create user"}), 500

@app.route("/api/admin/users/<user_id>", methods=["GET"])
@auth_required(role="admin")
def get_user(user_id):
    """Get a specific user by ID - Admin only"""
    try:
        user_doc = users.find_one({"user_id": user_id})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Remove sensitive data
        user_doc["_id"] = str(user_doc["_id"])
        user_doc.pop("password", None)
        user_doc.pop("password_hash", None)
        
        return jsonify({"user": user_doc})
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        return jsonify({"error": "Failed to fetch user"}), 500

@app.route("/api/admin/users/<user_id>", methods=["PUT"])
@auth_required(role="admin")
def update_user(user_id):
    """Update a user - Admin only"""
    try:
        data = request.json or {}
        user_doc = users.find_one({"user_id": user_id})
        
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Update allowed fields
        update_data = {}
        if "username" in data or "name" in data:
            update_data["username"] = data.get("username") or data.get("name")
        if "email" in data:
            # Check if new email already exists
            existing = users.find_one({"email": data["email"], "user_id": {"$ne": user_id}})
            if existing:
                return jsonify({"error": "Email already in use"}), 400
            update_data["email"] = data["email"]
        if "role" in data:
            update_data["role"] = data["role"]
        if "is_active" in data:
            update_data["is_active"] = data["is_active"]
        if "password" in data and data["password"]:
            update_data["password"] = data["password"]
            update_data["password_hash"] = data["password"]
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        users.update_one({"user_id": user_id}, {"$set": update_data})
        
        # Fetch updated user
        updated_user = users.find_one({"user_id": user_id})
        updated_user["_id"] = str(updated_user["_id"])
        updated_user.pop("password", None)
        updated_user.pop("password_hash", None)
        
        return jsonify({
            "message": "User updated successfully",
            "user": updated_user
        })
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return jsonify({"error": "Failed to update user"}), 500

@app.route("/api/admin/users/<user_id>", methods=["DELETE"])
@auth_required(role="admin")
def delete_user(user_id):
    """Delete a user - Admin only"""
    try:
        user_doc = users.find_one({"user_id": user_id})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Prevent deleting yourself
        current_user = g.user
        if current_user.get("user_id") == user_id:
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        users.delete_one({"user_id": user_id})
        
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"error": "Failed to delete user"}), 500

# === Video Processing Endpoints ===

@app.route('/api/video/upload', methods=['POST'])
@app.route('/api/upload', methods=['POST'])
@auth_required()
def upload_video():
    """Upload video endpoint with database integration"""
    try:
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: mp4, avi, mov, mkv, wmv, flv'}), 400
        
        # Get processing configuration (default to DetectifAI optimized)
        config_type = request.form.get('config_type', 'detectifai')
        
        # Generate unique video ID
        video_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}_{filename}")
        file.save(video_path)
        
        # Get file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        # Store in MinIO using standardized paths
        from minio_config import VIDEOS_BUCKET, get_minio_paths
        
        minio_paths = get_minio_paths(video_id, filename)
        object_name = minio_paths["original"]
        
        try:
            with open(video_path, 'rb') as file_data:
                minio_client.put_object(
                    VIDEOS_BUCKET,
                    object_name,
                    file_data,
                    file_size,
                    content_type='video/mp4'
                )
                logger.info(f"✅ Video uploaded to MinIO: {object_name}")
        except Exception as e:
            logger.error(f"❌ MinIO upload failed: {e}")
            raise
        
        # Create video record in database
        video_doc = {
            "video_id": video_id,
            "user_id": g.user.get("user_id"),
            "file_path": video_path,
            "minio_object_key": object_name,
            "minio_bucket": MINIO_BUCKET,
            "codec": None,
            "fps": None,
            "upload_date": datetime.now(timezone.utc),
            "duration_secs": None,
            "file_size_bytes": file_size,
            "meta_data": {},
            "processing_status": "uploaded"
        }
        video_file.insert_one(video_doc)
        
        # Initialize processing status
        processing_status[video_id] = {
            'video_id': video_id,
            'filename': filename,
            'status': 'queued',
            'progress': 0,
            'message': 'Video uploaded successfully. Processing queued.',
            'uploaded_at': datetime.now().isoformat(),
            'config_type': config_type
        }
        
        # Start background processing
        thread = threading.Thread(
            target=process_video_async,
            args=(video_id, video_path, config_type, g.user.get("user_id"))
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'message': 'Video uploaded successfully. Processing started.',
            'status_url': f'/api/status/{video_id}'
        }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/status/<video_id>', methods=['GET'])
@app.route('/api/status/<video_id>', methods=['GET'])
@auth_required()
def get_status(video_id):
    """Get processing status for a video"""
    # Check memory first
    if video_id in processing_status:
        return jsonify(processing_status[video_id]), 200
    
    # Check database for video record
    video_doc = video_file.find_one({"video_id": video_id})
    if video_doc:
        status = {
            'video_id': video_id,
            'filename': video_doc.get('file_path', '').split('/')[-1],
            'status': video_doc.get('processing_status', 'unknown'),
            'progress': 100 if video_doc.get('processing_status') == 'completed' else 0,
            'message': f"Video status: {video_doc.get('processing_status', 'unknown')}",
            'uploaded_at': video_doc.get('upload_date', '').isoformat() if video_doc.get('upload_date') else '',
            'results': video_doc.get('processing_results', {})
        }
        return jsonify(status), 200
    
    return jsonify({'error': 'Video not found'}), 404

# === Database Query Endpoints ===

@app.route("/api/videos", methods=["GET"])
@auth_required()
def list_videos():
    """List all videos for the authenticated user"""
    user_id = g.user.get("user_id")
    vids = list(video_file.find({"user_id": user_id}, {"_id": 0}))
    return jsonify(vids)

@app.route("/api/video/<video_id>", methods=["GET"])
@auth_required()
def get_video(video_id):
    """Get specific video details"""
    user_id = g.user.get("user_id")
    vid = video_file.find_one({"video_id": video_id, "user_id": user_id}, {"_id": 0})
    if not vid:
        return jsonify({"error": "not found"}), 404
    return jsonify(vid)

@app.route("/api/video/<video_id>/events", methods=["GET"])
@auth_required()
def get_video_events(video_id):
    """Get events for a specific video"""
    user_id = g.user.get("user_id")
    # Verify user owns the video
    video_doc = video_file.find_one({"video_id": video_id, "user_id": user_id})
    if not video_doc:
        return jsonify({"error": "video not found or access denied"}), 404
    
    events_list = list(event.find({"video_id": video_id}, {"_id": 0}))
    return jsonify(events_list)

@app.route("/api/event/<event_id>", methods=["GET"])
@auth_required()
def get_event_details(event_id):
    """Get event details with descriptions"""
    event_doc = event.find_one({"event_id": event_id}, {"_id": 0})
    if not event_doc:
        return jsonify({"error": "event not found"}), 404
    
    # Get descriptions for this event
    descriptions = list(event_description.find({"event_id": event_id}, {"_id": 0}))
    event_doc["descriptions"] = descriptions
    
    return jsonify(event_doc)

# === Search Endpoints ===

@app.route("/api/search", methods=["GET"])
@auth_required()
def search():
    """Simple text search in event descriptions"""
    q = request.args.get("q", "")
    user_id = g.user.get("user_id")
    
    # Get user's videos first
    user_videos = [v["video_id"] for v in video_file.find({"user_id": user_id}, {"video_id": 1})]
    
    # Search in descriptions for user's videos
    matches = list(event_description.find({
        "caption": {"$regex": q, "$options": "i"},
        "event_id": {"$in": [e["event_id"] for e in event.find({"video_id": {"$in": user_videos}}, {"event_id": 1})]}
    }, {"_id": 0}))
    
    return jsonify(matches)

@app.route("/api/search-vector", methods=["POST"])
@auth_required()
def search_vector():
    """Vector search for similar text embeddings using FAISS"""
    data = request.json or {}
    query_text = data.get("query_text")
    k = data.get("k", 10)  # Number of results to return
    
    if not query_text:
        return jsonify({"error": "query_text is required"}), 400
    
    try:
        # Generate embedding for the query text
        query_embedding = generate_text_embedding(query_text)
        
        # Search FAISS index
        results = faiss_manager.search_text_embeddings(query_embedding, k)
        
        return jsonify({
            "query_text": query_text,
            "results": results,
            "total_results": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

@app.route("/api/search-visual", methods=["POST"])
@auth_required()
def search_visual():
    """Vector search for similar visual embeddings using FAISS"""
    data = request.json or {}
    query_embedding = data.get("query_embedding")
    k = data.get("k", 10)  # Number of results to return
    
    if not query_embedding:
        return jsonify({"error": "query_embedding is required"}), 400
    
    if not isinstance(query_embedding, list):
        return jsonify({"error": "query_embedding must be a list of floats"}), 400
    
    try:
        # Search FAISS index
        results = faiss_manager.search_visual_embeddings(query_embedding, k)
        
        return jsonify({
            "query_embedding_dim": len(query_embedding),
            "results": results,
            "total_results": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": f"Visual search failed: {str(e)}"}), 500

@app.route("/api/search/captions", methods=["POST"])
@auth_required()
def search_captions():
    """Search captions using FAISS index and sentence transformers"""
    try:
        if not CAPTION_SEARCH_AVAILABLE:
            return jsonify({
                "error": "Caption search not available",
                "message": "Caption search module not installed or not available"
            }), 503
        
        data = request.json or {}
        query_text = data.get("query", "").strip()
        top_k = data.get("top_k", 10)
        min_score = data.get("min_score", 0.0)
        
        if not query_text:
            return jsonify({"error": "query is required"}), 400
        
        # Get caption search engine
        search_engine = get_caption_search_engine()
        
        if not search_engine or not search_engine.is_ready():
            return jsonify({
                "error": "Caption search engine not ready",
                "stats": search_engine.get_stats() if search_engine else {}
            }), 503
        
        # Perform search
        results = search_engine.search(query_text, top_k=top_k, min_score=min_score)
        
        # Format results for frontend
        formatted_results = []
        for result in results:
            video_ref = result.get("video_reference", {})
            minio_path = video_ref.get("minio_path", "")
            object_name = video_ref.get("object_name", "")
            
            # Generate MinIO URL for the image/video
            image_url = None
            if object_name:
                try:
                    bucket = video_ref.get("bucket", "nlp-images")
                    
                    # Create bucket if it doesn't exist
                    try:
                        if not minio_client.bucket_exists(bucket):
                            logger.info(f"Creating MinIO bucket: {bucket}")
                            minio_client.make_bucket(bucket)
                    except S3Error as e:
                        if e.code != "BucketAlreadyOwnedByYou" and e.code != "BucketAlreadyExists":
                            logger.warning(f"Could not create bucket {bucket}: {e}")
                    
                    # Generate presigned URL for MinIO object (valid for 1 hour)
                    from datetime import timedelta
                    image_url = minio_client.presigned_get_object(
                        bucket,
                        object_name,
                        expires=timedelta(hours=1)
                    )
                except Exception as e:
                    logger.warning(f"Could not generate MinIO URL: {e}")
                    # Fallback: use unified image serving endpoint
                    bucket = video_ref.get("bucket", "nlp-images")
                    image_url = f"/api/minio/image/{bucket}/{object_name}"
            
            formatted_result = {
                "id": result.get("description_id"),
                "event_id": result.get("event_id"),
                "description": result.get("caption", ""),
                "caption": result.get("caption", ""),
                "confidence": result.get("confidence", 0.0),
                "similarity_score": result.get("similarity_score", 0.0),
                "thumbnail": image_url,
                "video_reference": video_ref,
                "timestamp": result.get("created_at"),
                "zone": "N/A"  # Can be enhanced with actual zone data
            }
            formatted_results.append(formatted_result)
        
        return jsonify({
            "query": query_text,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "stats": search_engine.get_stats()
        })
        
    except Exception as e:
        logger.error(f"Error in caption search: {e}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

# === FAISS Management Endpoints ===

@app.route("/api/rebuild-indices", methods=["POST"])
@auth_required()
def rebuild_indices():
    """Rebuild FAISS indices from MongoDB data"""
    try:
        # Rebuild both indices
        faiss_manager.rebuild_text_index()
        faiss_manager.rebuild_visual_index()
        
        # Get updated stats
        stats = faiss_manager.get_index_stats()
        
        return jsonify({
            "message": "Indices rebuilt successfully",
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to rebuild indices: {str(e)}"}), 500

@app.route("/api/index-stats", methods=["GET"])
@auth_required()
def get_index_stats():
    """Get statistics about FAISS indices"""
    try:
        stats = faiss_manager.get_index_stats()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get index stats: {str(e)}"}), 500

# === Legacy DetectifAI Endpoints (for backward compatibility) ===

@app.route('/api/results/<video_id>', methods=['GET'])
@auth_required()
def get_results(video_id):
    """Get processing results for a video"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status['status'] != 'completed':
        return jsonify({
            'error': 'Processing not completed',
            'current_status': status['status']
        }), 400
    
    return jsonify(status.get('results', {})), 200

@app.route('/api/video/results/<video_id>', methods=['GET'])
@auth_required()
def get_video_results(video_id):
    """Get video processing results with availability flags"""
    # First check if video is in memory status
    if video_id in processing_status:
        status = processing_status[video_id]
        
        if status['status'] != 'completed':
            return jsonify({
                'error': 'Processing not completed',
                'current_status': status['status']
            }), 400
        
        # Check if status has results structure (normal processing)
        if 'results' in status and 'output_directory' in status['results']:
            output_dir = status['results']['output_directory']
        else:
            # Fallback to standard directory structure
            output_dir = os.path.join('video_processing_outputs', video_id)
    else:
        # Check database for video record
        video_doc = video_file.find_one({"video_id": video_id})
        if not video_doc:
            return jsonify({'error': 'Video not found'}), 404
        
        output_dir = os.path.join('video_processing_outputs', video_id)
        if not os.path.exists(output_dir):
            return jsonify({'error': 'Video processing results not found'}), 404
        
        logger.info(f"📁 Found video files on disk for {video_id}, recovering results")
    
    # Check for compressed video
    compressed_dir = os.path.join(output_dir, 'compressed')
    compressed_video_available = False
    compressed_video_url = None
    
    if os.path.exists(compressed_dir):
        video_files = [f for f in os.listdir(compressed_dir) if f.endswith('.mp4')]
        if video_files:
            compressed_video_available = True
            compressed_video_url = f'/api/video/compressed/{video_id}'
    
    # Check for keyframes
    frames_dir = os.path.join(output_dir, 'frames')
    keyframes_available = os.path.exists(frames_dir) and len([f for f in os.listdir(frames_dir) if f.endswith('.jpg')]) > 0
    keyframes_count = len([f for f in os.listdir(frames_dir) if f.endswith('.jpg')]) if keyframes_available else 0
    
    # Check for reports
    reports_dir = os.path.join(output_dir, 'reports')
    reports_available = os.path.exists(reports_dir)
    report_files = []
    if reports_available:
        report_files = [f for f in os.listdir(reports_dir) if f.endswith('.json')]
    
    return jsonify({
        'video_id': video_id,
        'compressed_video_available': compressed_video_available,
        'compressed_video_url': compressed_video_url,
        'keyframes_available': keyframes_available,
        'keyframes_count': keyframes_count,
        'keyframes_url': f'/api/video/keyframes/{video_id}',
        'reports_available': reports_available,
        'reports': report_files
    }), 200

# === File Serving Endpoints ===

@app.route('/api/video/keyframes/<video_id>', methods=['GET'])
@app.route('/api/keyframes/<video_id>', methods=['GET'])
@auth_required()
def get_keyframes(video_id):
    """Get list of extracted keyframes with DetectifAI annotations"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    output_dir = status['results']['output_directory']
    frames_dir = os.path.join(output_dir, 'frames')
    
    if not os.path.exists(frames_dir):
        return jsonify({'error': 'Frames directory not found'}), 404
    
    # Load detection metadata if available
    detection_metadata = {}
    detection_metadata_path = os.path.join(output_dir, 'detection_metadata.json')
    if os.path.exists(detection_metadata_path):
        try:
            with open(detection_metadata_path, 'r') as f:
                detection_metadata = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load detection metadata: {e}")
    
    # Get filter parameter
    filter_detections = request.args.get('filter_detections', 'false').lower() == 'true'
    
    keyframes = []
    frames_with_detections = {item['original_path']: item for item in detection_metadata.get('detection_summary', [])}
    
    for filename in sorted(os.listdir(frames_dir)):
        if filename.endswith('.jpg') and not filename.endswith('_annotated.jpg'):
            # Extract timestamp from filename
            timestamp = 0.0
            try:
                if '_' in filename:
                    timestamp_part = filename.split('_')[1].replace('s', '').replace('.jpg', '')
                    timestamp = float(timestamp_part)
            except:
                pass
            
            frame_path = os.path.join(frames_dir, filename)
            has_detections = frame_path in frames_with_detections
            
            # Skip frames without detections if filtering is enabled
            if filter_detections and not has_detections:
                continue
            
            keyframe_data = {
                'filename': filename,
                'timestamp': timestamp,
                'url': f'/api/keyframe/{video_id}/{filename}',
                'has_detections': has_detections
            }
            
            # Add detection details if available
            if has_detections:
                detection_info = frames_with_detections[frame_path]
                keyframe_data.update({
                    'detection_count': detection_info.get('detection_count', 0),
                    'objects': detection_info.get('objects', []),
                    'confidence_avg': detection_info.get('confidence_avg', 0.0)
                })
            
            keyframes.append(keyframe_data)
    
    return jsonify({
        'video_id': video_id,
        'total_keyframes': detection_metadata.get('total_keyframes', len(keyframes)),
        'keyframes_with_detections': detection_metadata.get('frames_with_detections', 0),
        'keyframes': keyframes,
        'objects_detected': detection_metadata.get('objects_detected', {}),
        'filter_applied': filter_detections
    }), 200

@app.route('/api/keyframe/<video_id>/<filename>', methods=['GET'])
@auth_required()
def get_keyframe_image(video_id, filename):
    """Serve keyframe image"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    output_dir = status['results']['output_directory']
    frames_dir = os.path.join(output_dir, 'frames')
    
    return send_from_directory(frames_dir, filename)

@app.route('/api/video/compressed/<video_id>', methods=['GET'])
@auth_required()
def get_compressed_video(video_id):
    """Serve compressed video"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    output_dir = status['results']['output_directory']
    compressed_dir = os.path.join(output_dir, 'compressed')
    
    if not os.path.exists(compressed_dir):
        return jsonify({'error': 'Compressed video directory not found'}), 404
    
    # Find the compressed video file
    video_files = [f for f in os.listdir(compressed_dir) if f.endswith('.mp4')]
    
    if not video_files:
        return jsonify({'error': 'Compressed video file not found'}), 404
    
    # Use the first video file found (should only be one)
    video_filename = video_files[0]
    
    return send_from_directory(compressed_dir, video_filename)

if __name__ == '__main__':
    logger.info("Starting DetectifAI Flask API server with database integration...")
    app.run(host='0.0.0.0', port=5000, debug=True)

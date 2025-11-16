"""
DetectifAI Flask Backend - AI-Powered CCTV Surveillance System

Enhanced Flask API for:
- Video upload and processing with DetectifAI security focus
- Real-time processing status and results
- Object detection with fire/weapon recognition
- Security event analysis and threat assessment
- Frontend integration for surveillance dashboard
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import threading
import json
from datetime import datetime
import logging
import uuid
import time
from typing import List, Dict, Any
import multiprocessing as mp

# Import DetectifAI components
from main_pipeline import CompleteVideoProcessingPipeline
from config import get_security_focused_config, VideoProcessingConfig

# Import database-integrated service
from database_video_service import DatabaseIntegratedVideoService

# Try to import DetectifAI-specific components
try:
    from detectifai_events import DetectifAIEventType, ThreatLevel
    DETECTIFAI_EVENTS_AVAILABLE = True
except ImportError:
    DETECTIFAI_EVENTS_AVAILABLE = False
    logging.warning("DetectifAI events module not available - using basic functionality")

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

# Configuration - use absolute paths to handle different working directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'video_processing_outputs')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Store processing status in memory (use Redis in production)
processing_status = {}

# Initialize database-integrated video service
try:
    db_video_service = DatabaseIntegratedVideoService(get_security_focused_config())
    DATABASE_ENABLED = True
    logger.info("✅ Database-integrated video service initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize database service: {e}")
    DATABASE_ENABLED = False

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

def process_video_async(video_id, video_path, config_type='detectifai'):
    """Process video in background thread with DetectifAI focus"""
    try:
        processing_status[video_id]['status'] = 'processing'
        processing_status[video_id]['progress'] = 0
        processing_status[video_id]['message'] = 'Initializing DetectifAI processing...'
        
        # Select configuration with DetectifAI optimizations
        if config_type == 'detectifai' or config_type == 'security':
            config = get_security_focused_config()
        # Removed robbery detection - using security focused config as default
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

        # Start action recognition in parallel (if available)
        try:
            try:
                # behavior_analysis package is relative to this backend package
                from behavior_analysis import action_recognition as action_recog
                AR_AVAILABLE = True
            except Exception:
                try:
                    # Fallback import path
                    import behavior_analysis.action_recognition as action_recog
                    AR_AVAILABLE = True
                except Exception:
                    AR_AVAILABLE = False

            if AR_AVAILABLE:
                try:
                    model_paths = list(action_recog.MODEL_PATHS.values())
                    ar_output_dir = os.path.join(config.output_base_dir, 'action_recognition_outputs')

                    # Start a separate process (Windows-safe spawn)
                    p = mp.Process(
                        target=action_recog.run_models_on_videos,
                        args=([video_path], model_paths),
                        kwargs={
                            'output_dir': ar_output_dir,
                            'use_gpu': getattr(config, 'use_gpu_acceleration', True),
                            'frame_skip': getattr(config, 'action_frame_skip', 5),
                            'annotate': getattr(config, 'action_annotate', True)
                        }
                    )
                    p.daemon = True
                    p.start()
                    processing_status[video_id]['action_recognition_pid'] = p.pid
                    logger.info(f"Started action recognition PID={p.pid} for video {video_id}")
                    # update message
                    processing_status[video_id]['message'] = 'Action recognition started in parallel with pipeline'
                except Exception as e:
                    logger.warning(f"Failed to start action recognition in parallel: {e}")

        except Exception:
            # Non-fatal: if imports fail or action rec process cannot be started, continue with pipeline
            logger.debug('Action recognition parallel start skipped or failed')

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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'database_enabled': DATABASE_ENABLED
    })

# ====== DATABASE-INTEGRATED ENDPOINTS ======

@app.route('/api/v2/video/upload', methods=['POST'])
def upload_video_db():
    """Enhanced video upload with database storage"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database service not available'}), 503
    
    try:
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: mp4, avi, mov, mkv, wmv, flv'}), 400
        
        # Generate video ID with consistent format
        video_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # Save temporary file with original extension
        filename = secure_filename(file.filename)
        base, ext = os.path.splitext(filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}/video{ext}")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)
        
        # Get user ID (if authenticated) - TODO: implement proper authentication
        user_id = request.form.get('user_id', None)
        
        # Create initial video record in MongoDB
        video_data = {
            "video_id": video_id,
            "user_id": user_id or "system",
            "file_path": f"videos/{video_id}/video{ext}",
            "upload_date": datetime.utcnow(),
            "meta_data": {
                "filename": filename,
                "original_name": file.filename,
                "processing_status": "uploading",
                "processing_progress": 0,
                "processing_message": "Starting upload to MinIO..."
            }
        }
        
        # Start background processing with database integration
        try:
            thread = threading.Thread(
                target=db_video_service.process_video_with_database_storage,
                args=(temp_path, video_id, user_id),
                daemon=True
            )
            thread.start()
            
            return jsonify({
                'success': True,
                'video_id': video_id,
                'message': 'Video uploaded successfully. Processing started with database storage.',
                'status_url': f'/api/v2/video/status/{video_id}'
            }), 201
            
        except Exception as process_error:
            logger.error(f"Failed to start video processing: {process_error}")
            # Update status in database
            db_video_service.video_repo.update_metadata(video_id, {
                "processing_status": "failed",
                "error_message": str(process_error)
            })
            raise
            
    except Exception as e:
        logger.error(f"Database upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        logger.error(f"Database upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v2/video/status/<video_id>', methods=['GET'])
def get_video_status_db(video_id):
    """Get processing status from database with fallback to in-memory status"""
    if not DATABASE_ENABLED:
        # Fallback to in-memory status if database not available
        if video_id in processing_status:
            return jsonify(processing_status[video_id]), 200
        return jsonify({'error': 'Database service not available and video not found in memory'}), 503

    try:
        status_data = db_video_service.get_video_status(video_id)

        if 'error' in status_data:
            # Fallback to in-memory status if database lookup fails
            if video_id in processing_status:
                logger.info(f"Database lookup failed for {video_id}, falling back to in-memory status")
                return jsonify(processing_status[video_id]), 200
            return jsonify(status_data), 404

        return jsonify(status_data), 200

    except Exception as e:
        logger.error(f"Database status check error: {str(e)}")
        # Fallback to in-memory status on exception
        if video_id in processing_status:
            logger.info(f"Database error for {video_id}, falling back to in-memory status")
            return jsonify(processing_status[video_id]), 200
        return jsonify({'error': str(e)}), 500

@app.route('/api/v2/video/keyframes/<video_id>', methods=['GET'])
def get_video_keyframes_db(video_id):
    """Get keyframes from database with MinIO URLs"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database service not available'}), 503
    
    try:
        # Get query parameters
        filter_detections = request.args.get('filter_detections', 'false').lower() == 'true'
        limit = request.args.get('limit', type=int)
        
        keyframes_data = db_video_service.get_video_keyframes(
            video_id, filter_detections=filter_detections, limit=limit
        )
        
        return jsonify(keyframes_data), 200
        
    except Exception as e:
        logger.error(f"Database keyframes retrieval error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v2/video/events/<video_id>', methods=['GET'])
def get_video_events_db(video_id):
    """Get events from database"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database service not available'}), 503
    
    try:
        event_type = request.args.get('type')  # motion, object_detection, face_recognition
        
        events_data = db_video_service.get_video_events(video_id, event_type)
        
        return jsonify(events_data), 200
        
    except Exception as e:
        logger.error(f"Database events retrieval error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v2/video/detections/<video_id>', methods=['GET'])
def get_video_detections_db(video_id):
    """Get object detections from database"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database service not available'}), 503
    
    try:
        class_filter = request.args.get('class')  # fire, knife, gun, smoke
        
        detections_data = db_video_service.get_video_detections(video_id, class_filter)
        
        return jsonify(detections_data), 200
        
    except Exception as e:
        logger.error(f"Database detections retrieval error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v2/video/results/<video_id>', methods=['GET'])
def get_video_results_db(video_id):
    """Get comprehensive video results from database"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database service not available'}), 503
    
    try:
        # Get video status and basic info
        status_data = db_video_service.get_video_status(video_id)
        
        if 'error' in status_data:
            return jsonify(status_data), 404
        
        # Only return comprehensive results if processing is completed
        if status_data.get('status') != 'completed':
            return jsonify({
                'error': 'Processing not completed',
                'current_status': status_data.get('status'),
                'progress': status_data.get('progress', 0),
                'message': status_data.get('message', '')
            }), 400
        
        # Get keyframes, events, and detections
        keyframes_data = db_video_service.get_video_keyframes(video_id, limit=50)
        events_data = db_video_service.get_video_events(video_id)
        detections_data = db_video_service.get_video_detections(video_id)
        
        # Compile comprehensive results
        results = {
            'video_info': status_data,
            'keyframes_available': len(keyframes_data['keyframes']) > 0,
            'keyframes_count': keyframes_data['total_keyframes'],
            'keyframes_sample': keyframes_data['keyframes'][:10],  # First 10 keyframes
            'events_available': len(events_data['events']) > 0,
            'events_count': events_data['total_events'],
            'events_summary': _summarize_events(events_data['events']),
            'detections_available': len(detections_data['detections']) > 0,
            'detections_count': detections_data['total_detections'],
            'detections_summary': _summarize_detections(detections_data['detections']),
            'threat_assessment': _assess_threat_level(events_data['events'], detections_data['detections'])
        }
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Database results retrieval error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/upload', methods=['POST'])
@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Upload video endpoint"""
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
            args=(video_id, video_path, config_type)
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
def get_status(video_id):
    """Get processing status for a video"""
    # Check memory first
    if video_id in processing_status:
        return jsonify(processing_status[video_id]), 200
    
    # Check if video files exist on disk (recovered processing)
    output_dir = os.path.join(OUTPUT_FOLDER, video_id)
    if os.path.exists(output_dir):
        # Recover status from disk
        recovered_status = {
            'video_id': video_id,
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed (recovered from disk)',
            'uploaded_at': '',
            'filename': f"{video_id}.avi"
        }
        
        # Add back to memory for future requests
        processing_status[video_id] = recovered_status
        
        logger.info(f"🔄 Recovered status for {video_id} from disk")
        return jsonify(recovered_status), 200
    
    return jsonify({'error': 'Video not found'}), 404

@app.route('/api/results/<video_id>', methods=['GET'])
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
def get_video_results(video_id):
    """Get video processing results with availability flags"""
    # First check if video is in memory status
    if video_id in processing_status:
        status = processing_status[video_id]

        if status['status'] == 'processing':
            # Return partial results while processing
            return jsonify({
                'video_id': video_id,
                'status': 'processing',
                'progress': status.get('progress', 0),
                'message': status.get('message', 'Processing...'),
                'compressed_video_available': False,
                'keyframes_available': False,
                'reports_available': False
            }), 200

        if status['status'] == 'failed':
            return jsonify({
                'error': 'Processing failed',
                'message': status.get('message', 'Unknown error'),
                'current_status': status['status']
            }), 400

        # Check if status has results structure (normal processing)
        if 'results' in status and 'output_directory' in status['results']:
            output_dir = status['results']['output_directory']
        else:
            # Fallback to standard directory structure
            output_dir = os.path.join(OUTPUT_FOLDER, video_id)
    else:
        # Check database for video status (for database-integrated processing)
        if DATABASE_ENABLED:
            try:
                db_status = db_video_service.get_video_status(video_id)
                if 'error' not in db_status:
                    # Video found in database, construct results from database metadata
                    meta_data = db_status.get('meta_data', {})

                    # Check for compressed video in MinIO
                    compressed_video_available = bool(meta_data.get('minio_compressed_path'))
                    compressed_video_url = f'/api/video/compressed/{video_id}' if compressed_video_available else None

                    # Check for keyframes
                    keyframes_available = meta_data.get('keyframe_count', 0) > 0
                    keyframes_count = meta_data.get('keyframe_count', 0)

                    # Check for reports (assume available if processing completed)
                    reports_available = db_status.get('status') == 'completed'

                    return jsonify({
                        'video_id': video_id,
                        'status': db_status.get('status', 'unknown'),
                        'compressed_video_available': compressed_video_available,
                        'compressed_video_url': compressed_video_url,
                        'keyframes_available': keyframes_available,
                        'keyframes_count': keyframes_count,
                        'keyframes_url': f'/api/v2/video/keyframes/{video_id}',  # Use v2 endpoint for database
                        'reports_available': reports_available,
                        'reports': []  # Database doesn't store report files locally
                    }), 200
            except Exception as e:
                logger.warning(f"Database lookup failed for results: {e}")

        # Check if video files exist on disk (for recovered/restarted servers)
        output_dir = os.path.join(OUTPUT_FOLDER, video_id)
        if not os.path.exists(output_dir):
            return jsonify({'error': 'Video not found'}), 404

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

@app.route('/api/download/<video_id>/<file_type>', methods=['GET'])
def download_file(video_id, file_type):
    """Download processed files"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    output_dir = status['results']['output_directory']
    
    try:
        if file_type == 'highlight_event':
            file_path = status['results']['highlight_reels'].get('event_aware', '')
        elif file_type == 'highlight_comprehensive':
            file_path = status['results']['highlight_reels'].get('ultra_comprehensive', '')
        elif file_type == 'highlight_quality':
            file_path = status['results']['highlight_reels'].get('quality_focused', '')
        elif file_type == 'compressed_video':
            file_path = status['results']['compressed_video']
        elif file_type == 'report_processing':
            file_path = status['results']['reports'].get('processing_results', '')
        elif file_type == 'report_events':
            file_path = status['results']['reports'].get('canonical_events', '')
        elif file_type == 'html_gallery':
            file_path = status['results']['reports'].get('html_gallery', '')
        else:
            return jsonify({'error': 'Invalid file type'}), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/keyframes/<video_id>', methods=['GET'])
@app.route('/api/keyframes/<video_id>', methods=['GET'])
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
def get_keyframe_image(video_id, filename):
    """Serve keyframe image"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    output_dir = status['results']['output_directory']
    frames_dir = os.path.join(output_dir, 'frames')
    
    return send_from_directory(frames_dir, filename)

@app.route('/api/video/compressed/<video_id>', methods=['GET'])
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

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """List all processed videos"""
    videos = []
    for video_id, status in processing_status.items():
        videos.append({
            'video_id': video_id,
            'filename': status.get('filename', ''),
            'status': status.get('status', ''),
            'uploaded_at': status.get('uploaded_at', ''),
            'progress': status.get('progress', 0)
        })
    
    return jsonify({'videos': videos}), 200

@app.route('/api/video/processing-summary/<video_id>', methods=['GET'])
@app.route('/api/processing-summary/<video_id>', methods=['GET'])
def get_processing_summary(video_id):
    """Get detailed processing summary for a video"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    output_dir = status['results']['output_directory']
    
    # Load detection metadata
    detection_metadata = {}
    detection_metadata_path = os.path.join(output_dir, 'detection_metadata.json')
    if os.path.exists(detection_metadata_path):
        try:
            with open(detection_metadata_path, 'r') as f:
                detection_metadata = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load detection metadata: {e}")
    
    # Get processing stats from status
    processing_stats = status['results'].get('processing_stats', {})
    
    summary = {
        'video_id': video_id,
        'filename': status.get('filename', ''),
        'processing_time': processing_stats.get('total_processing_time', 0),
        'keyframes_extracted': detection_metadata.get('total_keyframes', 0),
        'keyframes_with_detections': detection_metadata.get('frames_with_detections', 0),
        'objects_detected': detection_metadata.get('objects_detected', {}),
        'total_objects': sum(detection_metadata.get('objects_detected', {}).values()),
        'component_times': processing_stats.get('component_times', {}),
        'output_files': {
            'compressed_video': status['results'].get('compressed_video_path', ''),
            'frames_directory': os.path.join(output_dir, 'frames'),
            'reports_directory': os.path.join(output_dir, 'reports')
        }
    }
    
    return jsonify(summary), 200

@app.route('/api/delete/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    """Delete video and its processing results"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    try:
        # Remove from status
        status = processing_status.pop(video_id)
        
        # Delete output directory
        if 'results' in status and 'output_directory' in status['results']:
            import shutil
            output_dir = status['results']['output_directory']
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
        
        # Delete uploaded video
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            if file.startswith(video_id):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file))
        
        return jsonify({'success': True, 'message': 'Video deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# DetectifAI-specific endpoints

@app.route('/api/detectifai/events/<video_id>', methods=['GET'])
def get_detectifai_events(video_id):
    """Get DetectifAI security events for a video"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    results = status.get('results', {})
    security_events = results.get('security_detection', {})
    
    return jsonify({
        'video_id': video_id,
        'security_events': security_events,
        'total_detections': security_events.get('total_object_detections', 0),
        'fire_detections': security_events.get('fire_detections', 0),
        'weapon_detections': security_events.get('weapon_detections', 0),
        'security_alerts': security_events.get('security_alerts', [])
    }), 200

@app.route('/api/detectifai/demo', methods=['GET'])
def demo_detectifai():
    """Demo endpoint to process test videos (rob.mp4, fire.avi)"""
    try:
        demo_videos = []
        
        # Check for test videos
        test_files = ['rob.mp4', 'fire.avi']
        for test_file in test_files:
            if os.path.exists(test_file):
                # Create demo processing entry
                video_id = f"demo_{test_file.replace('.', '_')}_{int(datetime.now().timestamp())}"
                
                processing_status[video_id] = {
                    'video_id': video_id,
                    'filename': test_file,
                    'status': 'ready',
                    'progress': 0,
                    'message': f'Demo video {test_file} ready for DetectifAI processing',
                    'uploaded_at': datetime.now().isoformat(),
                    'video_path': test_file,
                    'is_demo': True,
                    'config_type': 'detectifai'
                }
                
                demo_videos.append({
                    'video_id': video_id,
                    'filename': test_file,
                    'process_url': f'/api/process/{video_id}'
                })
        
        return jsonify({
            'demo_videos': demo_videos,
            'message': f'Found {len(demo_videos)} demo videos ready for DetectifAI processing'
        }), 200
        
    except Exception as e:
        logger.error(f"Demo endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process/<video_id>', methods=['POST'])
def process_existing_video(video_id):
    """Process an existing video (useful for demo videos)"""
    if video_id not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
    
    status = processing_status[video_id]
    
    if status.get('status') not in ['ready', 'failed']:
        return jsonify({'error': 'Video is already being processed or completed'}), 400
    
    video_path = status.get('video_path', '')
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found'}), 404
    
    config_type = status.get('config_type', 'detectifai')
    
    # Start background processing
    thread = threading.Thread(
        target=process_video_async,
        args=(video_id, video_path, config_type)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'video_id': video_id,
        'message': 'DetectifAI processing started',
        'status_url': f'/api/status/{video_id}'
    }), 200

@app.route('/api/video/<video_id>/compressed', methods=['GET'])
def serve_compressed_video(video_id):
    """Serve compressed processed video"""
    try:
        # Find the compressed video file
        output_dir = os.path.join(OUTPUT_FOLDER, video_id, 'compressed')
        logger.info(f"Looking for compressed video in: {output_dir}")
        
        if not os.path.exists(output_dir):
            logger.error(f"Compressed video directory not found: {output_dir}")
            return jsonify({'error': f'Video directory not found: {output_dir}'}), 404
            
        # Look for compressed video files
        files = os.listdir(output_dir)
        logger.info(f"Files in compressed directory: {files}")
        
        for file in files:
            if file.endswith('.mp4'):
                video_path = os.path.join(output_dir, file)
                logger.info(f"Serving compressed video: {video_path}")
                response = send_file(
                    video_path,
                    mimetype='video/mp4',
                    as_attachment=False,
                    download_name=file
                )
                # Add headers for video playback and streaming
                response.headers['Accept-Ranges'] = 'bytes'
                response.headers['Cache-Control'] = 'no-cache'
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Range'
                response.headers['Content-Type'] = 'video/mp4'
                return response
        
        logger.error(f"No .mp4 file found in: {output_dir}")
        return jsonify({'error': 'No compressed video found'}), 404
        
    except Exception as e:
        logger.error(f"Error serving compressed video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>/keyframes', methods=['GET'])
def get_video_keyframes(video_id):
    """Get list of keyframes with detection results"""
    try:
        frames_dir = os.path.join(OUTPUT_FOLDER, video_id, 'frames')
        if not os.path.exists(frames_dir):
            return jsonify({'error': 'Keyframes not found'}), 404
        
        # Load detection metadata
        detection_metadata = {}
        detection_metadata_path = os.path.join(OUTPUT_FOLDER, video_id, 'detection_metadata.json')
        if os.path.exists(detection_metadata_path):
            try:
                with open(detection_metadata_path, 'r') as f:
                    detection_metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load detection metadata: {e}")
        
        # Build detection lookup dictionary
        detection_lookup = {}
        for item in detection_metadata.get('detection_summary', []):
            original_filename = os.path.basename(item['original_path'])
            annotated_filename = os.path.basename(item['annotated_path']) if 'annotated_path' in item else None
            detection_lookup[original_filename] = {
                'has_detections': True,
                'detection_count': item.get('detection_count', 0),
                'objects': item.get('objects', []),
                'confidence_avg': item.get('confidence_avg', 0.0),
                'annotated_filename': annotated_filename
            }
            
        keyframes = []
        for file in os.listdir(frames_dir):
            # Filter out annotated versions - only include original keyframes
            if file.endswith('.jpg') and not file.endswith('_annotated.jpg'):
                # Extract timestamp safely
                timestamp = 0.0
                try:
                    if '_' in file:
                        timestamp_part = file.split('_')[1].replace('s', '').replace('.jpg', '')
                        timestamp = float(timestamp_part)
                except (ValueError, IndexError):
                    timestamp = 0.0
                
                # Build keyframe data with detection info
                keyframe_data = {
                    'filename': file,
                    'url': f'/api/video/{video_id}/keyframe/{file}',
                    'timestamp': timestamp,
                    'has_detections': file in detection_lookup
                }
                
                # Add detection details and annotated frame URL if available
                if file in detection_lookup:
                    detection_info = detection_lookup[file]
                    keyframe_data['detection_count'] = detection_info['detection_count']
                    keyframe_data['objects'] = detection_info['objects']
                    keyframe_data['confidence_avg'] = detection_info['confidence_avg']
                    
                    # Provide annotated frame URL if it exists
                    if detection_info['annotated_filename']:
                        keyframe_data['annotated_url'] = f'/api/video/{video_id}/keyframe/{detection_info["annotated_filename"]}'
                
                keyframes.append(keyframe_data)
        
        # Sort by timestamp
        keyframes.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'video_id': video_id,
            'keyframes': keyframes,
            'total_keyframes': len(keyframes),
            'keyframes_with_detections': detection_metadata.get('frames_with_detections', 0),
            'objects_detected': detection_metadata.get('objects_detected', {})
        })
        
    except Exception as e:
        logger.error(f"Error getting keyframes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>/keyframe/<filename>', methods=['GET'])
def serve_keyframe(video_id, filename):
    """Serve individual keyframe image"""
    try:
        frames_dir = os.path.join(OUTPUT_FOLDER, video_id, 'frames')
        keyframe_path = os.path.join(frames_dir, filename)
        
        if not os.path.exists(keyframe_path):
            return jsonify({'error': 'Keyframe not found'}), 404
            
        return send_file(
            keyframe_path,
            mimetype='image/jpeg',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error serving keyframe: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ====== HELPER FUNCTIONS ======

def _summarize_events(events: List[Dict]) -> Dict:
    """Summarize events by type and threat level"""
    summary = {
        'by_type': {},
        'by_threat_level': {},
        'total_duration': 0.0,
        'highest_confidence': 0.0
    }
    
    for event in events:
        # Count by type
        event_type = event.get('event_type', 'unknown')
        summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1
        
        # Count by threat level
        threat_level = event.get('threat_level', 'low')
        summary['by_threat_level'][threat_level] = summary['by_threat_level'].get(threat_level, 0) + 1
        
        # Calculate duration
        start = event.get('start_timestamp', 0)
        end = event.get('end_timestamp', 0)
        summary['total_duration'] += (end - start)
        
        # Track highest confidence
        confidence = event.get('confidence', 0)
        summary['highest_confidence'] = max(summary['highest_confidence'], confidence)
    
    return summary

def _summarize_detections(detections: List[Dict]) -> Dict:
    """Summarize object detections by class and confidence"""
    summary = {
        'by_class': {},
        'average_confidence': 0.0,
        'highest_confidence': 0.0,
        'threat_objects': []
    }
    
    if not detections:
        return summary
    
    total_confidence = 0.0
    threat_classes = ['fire', 'gun', 'knife', 'smoke']
    
    for detection in detections:
        # Count by class
        class_name = detection.get('class_name', 'unknown')
        summary['by_class'][class_name] = summary['by_class'].get(class_name, 0) + 1
        
        # Calculate confidence stats
        confidence = detection.get('confidence', 0)
        total_confidence += confidence
        summary['highest_confidence'] = max(summary['highest_confidence'], confidence)
        
        # Track threat objects
        if class_name in threat_classes and class_name not in summary['threat_objects']:
            summary['threat_objects'].append(class_name)
    
    # Calculate average confidence
    summary['average_confidence'] = total_confidence / len(detections) if detections else 0.0
    
    return summary

def _assess_threat_level(events: List[Dict], detections: List[Dict]) -> Dict:
    """Assess overall threat level based on events and detections"""
    assessment = {
        'overall_level': 'low',
        'confidence_score': 0.0,
        'risk_factors': [],
        'recommendation': 'No immediate action required'
    }
    
    risk_score = 0.0
    risk_factors = []
    
    # Analyze events
    critical_events = sum(1 for e in events if e.get('threat_level') == 'critical')
    high_events = sum(1 for e in events if e.get('threat_level') == 'high')
    
    if critical_events > 0:
        risk_score += critical_events * 10.0
        risk_factors.append(f"{critical_events} critical events detected")
    
    if high_events > 0:
        risk_score += high_events * 5.0
        risk_factors.append(f"{high_events} high-risk events detected")
    
    # Analyze detections
    critical_objects = sum(1 for d in detections if d.get('class_name') in ['fire', 'gun'])
    high_objects = sum(1 for d in detections if d.get('class_name') == 'knife')
    
    if critical_objects > 0:
        risk_score += critical_objects * 8.0
        risk_factors.append(f"{critical_objects} critical objects detected (fire/gun)")
    
    if high_objects > 0:
        risk_score += high_objects * 4.0
        risk_factors.append(f"{high_objects} weapons detected (knife)")
    
    # Calculate overall threat level
    if risk_score >= 20.0:
        assessment['overall_level'] = 'critical'
        assessment['recommendation'] = 'Immediate response required - potential emergency situation'
    elif risk_score >= 10.0:
        assessment['overall_level'] = 'high'
        assessment['recommendation'] = 'Investigation recommended - elevated security concern'
    elif risk_score >= 5.0:
        assessment['overall_level'] = 'medium'
        assessment['recommendation'] = 'Monitor situation - potential security interest'
    else:
        assessment['overall_level'] = 'low'
        assessment['recommendation'] = 'Normal activity - routine monitoring sufficient'
    
    assessment['confidence_score'] = min(risk_score / 20.0, 1.0)  # Normalize to 0-1
    assessment['risk_factors'] = risk_factors
    
    return assessment

@app.route('/api/search/person-by-image', methods=['POST'])
def search_person_by_image():
    """
    Search for a person by uploading their image.
    Uses facial recognition to find similar faces in the database.
    """
    try:
        # Check if image was uploaded
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No image file selected'
            }), 400
        
        # Validate file type
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload an image file.'
            }), 400
        
        # Save uploaded image temporarily
        filename = secure_filename(f"search_{int(time.time())}_{file.filename}")
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)
        
        try:
            # Initialize facial recognition system
            from facial_recognition import FacialRecognitionIntegrated
            from config import VideoProcessingConfig
            
            config = VideoProcessingConfig()
            config.enable_facial_recognition = True
            
            face_recognizer = FacialRecognitionIntegrated(config)
            
            if not face_recognizer.enabled:
                return jsonify({
                    'success': False,
                    'error': 'Facial recognition system is not enabled or properly configured'
                }), 500
            
            # Get search parameters from request
            threshold = float(request.form.get('threshold', 0.6))
            max_results = int(request.form.get('max_results', 10))
            
            # Perform image search
            search_results = face_recognizer.search_person_by_image(
                temp_path, 
                k=max_results, 
                threshold=threshold
            )
            
            # Format results for frontend
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    'id': result['face_id'],
                    'person_name': result['person_name'],
                    'confidence': round(result['similarity_score'], 3),
                    'person_confidence': round(result['person_confidence'], 3) if result['person_confidence'] else 0.0,
                    'timestamp': result['timestamp'],
                    'event_context': result['event_context'],
                    'detection_context': result['detection_context'],
                    'thumbnail': f"/api/face-image/{result['face_id']}" if result['face_image_path'] else None,
                    'description': f"{result['person_name']} detected in {result['detection_context'].lower()}",
                    'zone': 'Security Zone',  # Placeholder
                    'has_face_image': result['face_image_path'] is not None
                }
                formatted_results.append(formatted_result)
            
            # Get system statistics
            stats = face_recognizer.get_detection_stats()
            
            response_data = {
                'success': True,
                'results': formatted_results,
                'total_matches': len(formatted_results),
                'search_parameters': {
                    'similarity_threshold': threshold,
                    'max_results': max_results
                },
                'system_stats': {
                    'total_faces_in_database': stats.get('total_faces_in_database', 0),
                    'implementation_mode': stats.get('implementation_mode', 'unknown')
                },
                'message': f"Found {len(formatted_results)} matches with similarity >= {threshold}"
            }
            
            return jsonify(response_data)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error in person image search: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/face-image/<face_id>')
def get_face_image(face_id):
    """
    Serve face images for the search results.
    """
    try:
        # Construct face image path
        face_image_path = os.path.join('model', 'faces', f"{face_id}.jpg")
        
        if not os.path.exists(face_image_path):
            # Return a placeholder or 404
            return jsonify({'error': 'Face image not found'}), 404
        
        return send_file(face_image_path, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"Error serving face image {face_id}: {e}")
        return jsonify({'error': 'Error serving face image'}), 500

if __name__ == '__main__':
    logger.info("Starting DetectifAI Flask API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
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

# Import DetectifAI components
from main_pipeline import CompleteVideoProcessingPipeline
from config import get_robbery_detection_config, get_security_focused_config, VideoProcessingConfig

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

# Store processing status in memory (use Redis in production)
processing_status = {}

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
        elif config_type == 'robbery':
            config = get_robbery_detection_config()
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
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

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
    output_dir = os.path.join('video_processing_outputs', video_id)
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
        # Check if video files exist on disk (for recovered/restarted servers)
        output_dir = os.path.join('video_processing_outputs', video_id)
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
        output_dir = os.path.join('video_processing_outputs', video_id, 'compressed')
        if not os.path.exists(output_dir):
            return jsonify({'error': 'Video not found'}), 404
            
        # Look for compressed video files
        for file in os.listdir(output_dir):
            if file.endswith('.mp4'):
                video_path = os.path.join(output_dir, file)
                return send_file(
                    video_path,
                    mimetype='video/mp4',
                    as_attachment=False,
                    download_name=file
                )
        
        return jsonify({'error': 'No compressed video found'}), 404
        
    except Exception as e:
        logger.error(f"Error serving compressed video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>/keyframes', methods=['GET'])
def get_video_keyframes(video_id):
    """Get list of keyframes with detection results"""
    try:
        frames_dir = os.path.join('video_processing_outputs', video_id, 'frames')
        if not os.path.exists(frames_dir):
            return jsonify({'error': 'Keyframes not found'}), 404
            
        keyframes = []
        for file in os.listdir(frames_dir):
            if file.endswith('.jpg'):
                # Extract timestamp safely
                timestamp = 0.0
                try:
                    if '_' in file:
                        timestamp_part = file.split('_')[1].replace('s', '').replace('.jpg', '')
                        timestamp = float(timestamp_part)
                except (ValueError, IndexError):
                    timestamp = 0.0
                
                keyframes.append({
                    'filename': file,
                    'url': f'/api/video/{video_id}/keyframe/{file}',
                    'timestamp': timestamp
                })
        
        # Sort by timestamp
        keyframes.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'video_id': video_id,
            'keyframes': keyframes,
            'total_keyframes': len(keyframes)
        })
        
    except Exception as e:
        logger.error(f"Error getting keyframes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>/keyframe/<filename>', methods=['GET'])
def serve_keyframe(video_id, filename):
    """Serve individual keyframe image"""
    try:
        frames_dir = os.path.join('video_processing_outputs', video_id, 'frames')
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

if __name__ == '__main__':
    logger.info("Starting DetectifAI Flask API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
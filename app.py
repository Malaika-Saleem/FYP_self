"""
Flask Web Application for Video Preprocessing with Webcam Integration

This application provides:
- Real-time webcam processing with motion detection
- Video upload and chunked processing
- Integration with the complete video preprocessing pipeline
- Web interface for monitoring and control
"""

import os
import io
import cv2
import numpy as np
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, Response, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from minio import Minio
from pymongo import MongoClient
import logging

# Import our video processing pipeline
from config import VideoProcessingConfig, get_robbery_detection_config
from webcam_processor import WebcamIntegrationManager, WebcamConfig
from main_pipeline import CompleteVideoProcessingPipeline

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- CONFIG -----------------
# MinIO client setup
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "adminpassword"
MINIO_BUCKET = "detectifai-videos"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)

# MongoDB setup (metadata)
mongo_client = MongoClient("mongodb+srv://detectifai_user:DetectifAI123@cluster0.6f9uj.mongodb.net/detectifai?")
db = mongo_client.detectifai
metadata_collection = db.frames

BASE_DIR = Path(__file__).resolve().parent
STATIC_VIDEOS = BASE_DIR / 'static' / 'videos'
TEMP_UPLOADS = BASE_DIR / 'temp_uploads'
STATIC_VIDEOS.mkdir(parents=True, exist_ok=True)
TEMP_UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)

# ----------------- VIDEO PROCESSING SETUP -----------------
# Initialize video processing pipeline
video_config = get_robbery_detection_config()  # Optimized for event detection
pipeline = CompleteVideoProcessingPipeline(video_config)

# Initialize webcam integration
webcam_config = WebcamConfig(
    camera_index=0,
    frame_width=640,
    frame_height=480,
    fps_target=30,
    enable_streaming=True,
    enable_keyframe_saving=True,
    motion_upload_threshold=25.0,
    blur_threshold=100,
    fps_low=1,
    fps_high=8,
    frame_size=(640, 640)
)
webcam_manager = WebcamIntegrationManager(video_config)

# ----------------- WEBCAM PROCESSING -----------------
@app.route('/start_webcam')
def start_webcam():
    """Start webcam processing"""
    try:
        success = webcam_manager.start_webcam_processing()
        if success:
            return jsonify({'status': 'success', 'message': 'Webcam processing started'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to start webcam'}), 500
    except Exception as e:
        logger.error(f"Error starting webcam: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop_webcam')
def stop_webcam():
    """Stop webcam processing"""
    try:
        webcam_manager.stop_webcam_processing()
        return jsonify({'status': 'success', 'message': 'Webcam processing stopped'})
    except Exception as e:
        logger.error(f"Error stopping webcam: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webcam_status')
def webcam_status():
    """Get webcam status"""
    try:
        status = webcam_manager.get_status()
        return jsonify({'status': 'success', 'data': status})
    except Exception as e:
        logger.error(f"Error getting webcam status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/capture_session')
def capture_session():
    """Capture a session of keyframes from webcam"""
    try:
        duration = int(request.args.get('duration', 30))
        keyframes = webcam_manager.capture_session(duration)

        # Convert keyframes to serializable format
        keyframe_data = []
        for kf in keyframes:
            keyframe_data.append({
                'timestamp': kf.frame_data.timestamp,
                'frame_path': kf.frame_data.frame_path,
                'quality_score': kf.frame_data.quality_score,
                'motion_score': kf.frame_data.motion_score,
                'burst_active': kf.frame_data.burst_active,
                'keyframe_score': kf.keyframe_score,
                'selection_reason': kf.selection_reason
            })

        return jsonify({
            'status': 'success',
            'keyframes_captured': len(keyframes),
            'data': keyframe_data
        })
    except Exception as e:
        logger.error(f"Error capturing session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    """Video feed from webcam with preprocessing"""
    try:
        return Response(
            webcam_manager.get_stream_generator(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.error(f"Error in video feed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ----------------- VIDEO PROCESSING ENDPOINTS -----------------
@app.route('/process_video', methods=['POST'])
def process_video():
    """Process an uploaded video through the complete pipeline"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')

        if not video_path or not os.path.exists(video_path):
            return jsonify({'status': 'error', 'message': 'Video file not found'}), 400

        # Process video through pipeline
        output_name = data.get('output_name', os.path.splitext(os.path.basename(video_path))[0])
        results = pipeline.process_video_complete(video_path, output_name)

        return jsonify({'status': 'success', 'results': results})

    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_pipeline_status')
def get_pipeline_status():
    """Get current pipeline processing status"""
    try:
        summary = pipeline.get_processing_summary()
        return jsonify({'status': 'success', 'summary': summary})
    except Exception as e:
        logger.error(f"Error getting pipeline status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ----------------- CHUNK UPLOAD ENDPOINTS -----------------
@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    """Handle chunked video upload"""
    file = request.files.get('file')
    filename = request.form.get('filename')
    chunk_index = request.form.get('chunk_index')
    total_chunks = request.form.get('total_chunks')

    if not file or not filename or chunk_index is None or total_chunks is None:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400

    safe_dir = TEMP_UPLOADS / filename
    safe_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = safe_dir / f"chunk_{int(chunk_index):06d}"
    file.save(chunk_path)
    return jsonify({'ok': True, 'message': f'chunk {chunk_index} received'})

@app.route('/merge_chunks', methods=['POST'])
def merge_chunks():
    """Merge uploaded chunks into complete video file"""
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'ok': False, 'error': 'filename required'}), 400

    src_dir = TEMP_UPLOADS / filename
    if not src_dir.exists():
        return jsonify({'ok': False, 'error': 'no chunks found'}), 400

    chunk_files = sorted([p for p in src_dir.iterdir() if p.name.startswith('chunk_')])
    if not chunk_files:
        return jsonify({'ok': False, 'error': 'no chunk files'}), 400

    out_path = STATIC_VIDEOS / filename
    with open(out_path, 'wb') as wfd:
        for cf in chunk_files:
            with open(cf, 'rb') as rfd:
                wfd.write(rfd.read())

    minio_client.fput_object(MINIO_BUCKET, filename, str(out_path))

    for cf in chunk_files:
        cf.unlink()
    try:
        src_dir.rmdir()
    except Exception:
        pass

    return jsonify({
        'ok': True,
        'url': f'/static/videos/{filename}',
        'minio_url': f'http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}'
    })

@app.route('/videos')
def list_videos():
    """List all stored videos"""
    files = []
    for obj in minio_client.list_objects(MINIO_BUCKET, recursive=True):
        files.append({
            "name": obj.object_name,
            "url": f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{obj.object_name}",
            "size": obj.size,
            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
        })
    return jsonify({"ok": True, "videos": files})

@app.route('/static/videos/<path:filename>')
def serve_video(filename):
    """Serve video files"""
    return send_from_directory(STATIC_VIDEOS, filename)

# ----------------- WEB INTERFACE -----------------
@app.route('/')
def index():
    """Main web interface"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DetectifAI - Video Preprocessing</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .section { margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 3px; }
            .status.success { background-color: #d4edda; color: #155724; }
            .status.error { background-color: #f8d7da; color: #721c24; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            img { max-width: 640px; max-height: 480px; }
        </style>
    </head>
    <body>
        <h1>🎬 DetectifAI - Video Preprocessing Pipeline</h1>

        <div class="section">
            <h2>📹 Webcam Control</h2>
            <button onclick="startWebcam()">Start Webcam</button>
            <button onclick="stopWebcam()">Stop Webcam</button>
            <button onclick="captureSession()">Capture 30s Session</button>
            <button onclick="getWebcamStatus()">Check Status</button>
            <div id="webcam-status" class="status"></div>
        </div>

        <div class="section">
            <h2>📺 Live Camera Feed</h2>
            <img id="video-feed" src="" alt="camera" style="display:none;" />
            <br>
            <button onclick="startVideoFeed()">Start Feed</button>
            <button onclick="stopVideoFeed()">Stop Feed</button>
        </div>

        <div class="section">
            <h2>📤 Upload Large Video (Chunked)</h2>
            <input type="file" id="video-file" accept="video/*" />
            <br><br>
            <button onclick="uploadVideo()">Upload Video</button>
            <div id="upload-progress">Progress: 0%</div>
        </div>

        <div class="section">
            <h2>🎥 Stored Videos</h2>
            <button onclick="listVideos()">Refresh List</button>
            <div id="video-list"></div>
        </div>

        <div class="section">
            <h2>⚙️ Pipeline Status</h2>
            <button onclick="getPipelineStatus()">Check Pipeline Status</button>
            <pre id="pipeline-status"></pre>
        </div>

        <script>
            let videoFeedActive = false;

            function updateStatus(elementId, message, isSuccess = true) {
                const element = document.getElementById(elementId);
                element.textContent = message;
                element.className = `status ${isSuccess ? 'success' : 'error'}`;
            }

            async function startWebcam() {
                const response = await fetch('/start_webcam');
                const data = await response.json();
                updateStatus('webcam-status', data.message, data.status === 'success');
            }

            async function stopWebcam() {
                const response = await fetch('/stop_webcam');
                const data = await response.json();
                updateStatus('webcam-status', data.message, data.status === 'success');
            }

            async function captureSession() {
                const response = await fetch('/capture_session?duration=30');
                const data = await response.json();
                const message = `Captured ${data.keyframes_captured} keyframes`;
                updateStatus('webcam-status', message, data.status === 'success');
            }

            async function getWebcamStatus() {
                const response = await fetch('/webcam_status');
                const data = await response.json();
                if (data.status === 'success') {
                    const status = data.data;
                    const message = `Webcam: ${status.webcam_info.status}, Captured: ${status.captured_keyframes} keyframes`;
                    updateStatus('webcam-status', message, true);
                } else {
                    updateStatus('webcam-status', data.message, false);
                }
            }

            function startVideoFeed() {
                const img = document.getElementById('video-feed');
                img.src = '/video_feed';
                img.style.display = 'block';
                videoFeedActive = true;
            }

            function stopVideoFeed() {
                const img = document.getElementById('video-feed');
                img.src = '';
                img.style.display = 'none';
                videoFeedActive = false;
            }

            async function uploadVideo() {
                const fileInput = document.getElementById('video-file');
                const file = fileInput.files[0];
                if (!file) {
                    alert('Please select a video file');
                    return;
                }

                const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
                const total = Math.ceil(file.size / CHUNK_SIZE);
                let uploaded = 0;

                for (let i = 0; i < total; i++) {
                    const start = i * CHUNK_SIZE;
                    const end = Math.min(start + CHUNK_SIZE, file.size);
                    const chunk = file.slice(start, end);

                    const form = new FormData();
                    form.append('file', chunk);
                    form.append('filename', file.name);
                    form.append('chunk_index', i);
                    form.append('total_chunks', total);

                    try {
                        const res = await fetch('/upload_chunk', {
                            method: 'POST',
                            body: form,
                        });
                        const json = await res.json();
                        if (!json.ok) {
                            alert('Upload chunk failed');
                            return;
                        }
                        uploaded++;
                        document.getElementById('upload-progress').textContent =
                            `Progress: ${Math.round((uploaded / total) * 100)}%`;
                    } catch (error) {
                        alert('Upload failed: ' + error.message);
                        return;
                    }
                }

                // Merge chunks
                try {
                    const mergeRes = await fetch('/merge_chunks', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: file.name }),
                    });
                    const mergeJson = await mergeRes.json();
                    if (mergeJson.ok) {
                        document.getElementById('upload-progress').textContent = 'Upload complete!';
                        listVideos(); // Refresh video list
                        alert('Upload complete!');
                    } else {
                        alert('Merge failed');
                    }
                } catch (error) {
                    alert('Merge failed: ' + error.message);
                }
            }

            async function listVideos() {
                const response = await fetch('/videos');
                const data = await response.json();
                const videoList = document.getElementById('video-list');

                if (data.ok && data.videos.length > 0) {
                    let html = '<ul>';
                    data.videos.forEach(video => {
                        html += `<li>
                            <strong>${video.name}</strong> (${(video.size / (1024*1024)).toFixed(2)} MB)
                            <br>
                            <video controls width="320" src="${video.url}"></video>
                        </li>`;
                    });
                    html += '</ul>';
                    videoList.innerHTML = html;
                } else {
                    videoList.innerHTML = '<p>No videos yet</p>';
                }
            }

            async function getPipelineStatus() {
                const response = await fetch('/get_pipeline_status');
                const data = await response.json();
                const statusElement = document.getElementById('pipeline-status');

                if (data.status === 'success') {
                    statusElement.textContent = JSON.stringify(data.summary, null, 2);
                } else {
                    statusElement.textContent = 'Error: ' + data.message;
                }
            }

            // Load initial data
            window.onload = function() {
                listVideos();
                getWebcamStatus();
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    try:
        logger.info("Starting DetectifAI Video Preprocessing Server...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
    finally:
        # Cleanup
        webcam_manager.stop_webcam_processing()

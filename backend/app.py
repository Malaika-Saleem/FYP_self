
# backend/app.py
import os
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_VIDEOS = BASE_DIR / 'static' / 'videos'
TEMP_UPLOADS = BASE_DIR / 'temp_uploads'

# create folders
STATIC_VIDEOS.mkdir(parents=True, exist_ok=True)
TEMP_UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)

# --- Live webcam MJPEG streaming ---
cap = None

def get_camera():
    global cap
    if cap is None or not cap.isOpened():
        # 0 uses laptop webcam. Replace with RTSP URL like "rtsp://..." to connect to IP camera
        cap = cv2.VideoCapture("rtsp://rtsp/stream/movie")
    return cap


import requests
import numpy as np

URL = "http://220.254.72.200:80/cgi-bin/camera?resolution=640&quality=1&Language=0&1755169725"

def gen_frames():
    while True:
        try:
            # Fetch latest snapshot from camera
            img_resp = requests.get(URL, stream=True, timeout=5)
            img_arr = np.asarray(bytearray(img_resp.content), dtype=np.uint8)
            frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print("Error fetching frame:", e)



@app.route('/video_feed')
def video_feed():
    # MJPEG stream
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Chunked upload endpoints ---
@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    """
    Expects form fields:
      - file: chunk binary
      - filename: original filename
      - chunk_index: integer
      - total_chunks: integer
    """
    file = request.files.get('file')
    filename = request.form.get('filename')
    chunk_index = request.form.get('chunk_index')
    total_chunks = request.form.get('total_chunks')

    if not file or not filename or chunk_index is None or total_chunks is None:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400

    # safe folder: temp_uploads/<filename>/
    safe_dir = TEMP_UPLOADS / filename
    safe_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = safe_dir / f"chunk_{int(chunk_index):06d}"  # zero-padded
    file.save(chunk_path)
    return jsonify({'ok': True, 'message': f'chunk {chunk_index} received'})


@app.route('/merge_chunks', methods=['POST'])
def merge_chunks():
    """
    Expects JSON: { filename: "original.mp4", total_chunks: N }
    Merges and places final file into static/videos/filename
    """
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

    # optional: cleanup temp chunks
    for cf in chunk_files:
        cf.unlink()
    # remove directory
    try:
        src_dir.rmdir()
    except Exception:
        pass

    return jsonify({'ok': True, 'url': f'/static/videos/{filename}'})


@app.route('/videos')
def list_videos():
    files = []
    for f in STATIC_VIDEOS.iterdir():
        if f.is_file():
            files.append({'name': f.name, 'url': f'/static/videos/{f.name}'})
    return jsonify({'ok': True, 'videos': files})


# Serve video files (Flask's static files also works)
@app.route('/static/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(STATIC_VIDEOS, filename)


if __name__ == '__main__':
    # Note: debug mode restarts may re-open camera. For demo this is fine.
    app.run(host='0.0.0.0', port=5000, debug=True)


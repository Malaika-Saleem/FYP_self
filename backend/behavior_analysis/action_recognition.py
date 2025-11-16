# ============================================================
# FULLY FIXED ACTION RECOGNITION PIPELINE
# Supports:
#   - fight_detection.pt (3D ResNet18, state_dict)
#   - road_accident.pt   (3D ResNet18, state_dict)
#   - wallclimb.pt       (YOLO, Ultralytics)
# ============================================================

from dataclasses import dataclass, asdict
import multiprocessing as mp
import torch
import cv2
import numpy as np
import os
import time
import json
import logging
from typing import List, Optional, Dict, Any
from torchvision.models.video import r3d_18
import torch.nn as nn

# --- YOLO + PyTorch 2.6 compatibility ---
from ultralytics import YOLO
import ultralytics
torch.serialization.add_safe_globals([ultralytics.nn.tasks.DetectionModel])

# --- Logging ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================
# FIXED MODEL PATHS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATHS = {
    "fight_detection":   os.path.join(BASE_DIR, "fight_detection.pt"),
    "road_accident":     os.path.join(BASE_DIR, "accident_detection.pt"),
    "wallclimb":         os.path.join(BASE_DIR, "wallclimb.pt"),
}

# Define which models are 3D-ResNet (run separately) vs YOLO
RESNET_MODELS = {"fight_detection", "road_accident"}
YOLO_MODELS = {"wallclimb"}

# ============================================================
#  Dataclasses
# ============================================================
@dataclass
class ActionPrediction:
    timestamp: float
    frame_index: int
    label: str
    confidence: float


# ============================================================
# MODEL LOADER (YOLO or 3D-ResNet)
# ============================================================
def load_model(model_path: str, device: torch.device):

    name = os.path.basename(model_path).lower()

    # -------- YOLO MODEL (wallclimb) --------
    if "wall" in name or "yolo" in name:
        logger.info(f"Loading YOLO model: {model_path}")
        return YOLO(model_path)

    # -------- TRY TorchScript --------
    try:
        model = torch.jit.load(model_path, map_location=device)
        logger.info(f"Loaded TorchScript model")
        model.eval()
        return model
    except:
        pass

    # -------- 3D-ResNet --------
    try:
        ckpt = torch.load(model_path, map_location=device)

        if isinstance(ckpt, dict):
            logger.info(f"Loading 3D-ResNet model: {model_path}")

            model = r3d_18(weights=None)
            model.fc = nn.Linear(512, 2)

            state = ckpt.get("state_dict", ckpt)
            model.load_state_dict(state)

            model.to(device)
            model.eval()
            return model
    except Exception as e:
        logger.error(f"3D-ResNet load failed: {e}")

    raise RuntimeError(f"Unsupported model format: {model_path}")


# ============================================================
# FRAME PREPROCESSING FOR 3D-ResNet
# ============================================================
def preprocess_clip(frames: List[np.ndarray], device: torch.device, target_size=None):
    """
    frames = list of 16 RGB frames
    output: tensor (1, 3, 16, H, W)
    """
    processed = []

    # default target size used in your training/preprocessing
    if not target_size:
        target_size = (112, 112)

    for f in frames:
        img = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)

        if target_size:
            img = cv2.resize(img, (target_size[1], target_size[0]))

        img = img / 255.0
        img = img.transpose(2, 0, 1)
        processed.append(img)

    clip = np.stack(processed, axis=1)
    tensor = torch.from_numpy(clip).float().unsqueeze(0).to(device)
    return tensor


# ============================================================
# INTERPRET MODEL OUTPUT
# ============================================================
# Map class indices to action labels
ACTION_LABELS = {
    0: "fighting",
    1: "accident",
    2: "climbing"
}
CONFIDENCE_THRESHOLD = 0.5

def interpret_prediction(model, output, model_name):
    """
    Interpret model output and return one of three actions: "fighting", "accident", or "climbing".
    If confidence is below 0.5, suppress the prediction and return ("no_action", 0.0).
    
    Model-specific handling:
    - fight_detection: returns "fighting" if class 1, "no_action" for class 0
    - road_accident: returns "accident" if class 1, "no_action" for class 0
    - wallclimb (YOLO): returns "climbing" for class 2
    """
    # -------- YOLO (wallclimb) --------
    if hasattr(model, "predict") and isinstance(output, list):
        boxes = output[0].boxes
        if boxes is None or len(boxes) == 0:
            return ("no_action", 0.0)

        best = boxes[0]
        cls_idx = int(best.cls)
        conf = float(best.conf)
        
        # Suppress if confidence < threshold
        if conf < CONFIDENCE_THRESHOLD:
            return ("no_action", 0.0)
        
        # YOLO returns climbing detections
        label = "climbing" if cls_idx == 0 else "no_action"
        return (label, conf)

    # -------- 3D-ResNet (fight_detection or road_accident) --------
    if isinstance(output, torch.Tensor):
        probs = torch.softmax(output, dim=1)[0]
        cls_idx = int(torch.argmax(probs).item())
        conf = float(probs[cls_idx])
        
        # Suppress if confidence < threshold
        if conf < CONFIDENCE_THRESHOLD:
            return ("no_action", 0.0)
        
        # Model-specific mapping (class 0 = negative, class 1 = positive)
        if "fight" in model_name.lower():
            label = "fighting" if cls_idx == 1 else "no_action"
        elif "accident" in model_name.lower() or "road" in model_name.lower():
            # match user's naming and capitalization for saved frames
            label = "Accident" if cls_idx == 0 else "no_action"
        else:
            label = "no_action"
        
        return (label, conf)
    

    return ("no_action", 0.0)


# ============================================================
# VIDEO PROCESSING
# ============================================================
def process_video_with_model(
        video_path,
        model_path,
        output_dir,
        model_name=None,
        use_gpu=True,
        frame_skip=1,
        target_size=None,
        annotate=True):

    device = torch.device("cuda" if (use_gpu and torch.cuda.is_available()) else "cpu")

    model_name = model_name or os.path.splitext(os.path.basename(model_path))[0]
    logger.info(f"[{model_name}] Loading model...")

    model = load_model(model_path, device)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"[{model_name}] Could not open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_buffer = []
    idx = 0
    frames_processed = 0
    predictions = []

    # annotation folder
    anno_dir = os.path.join(output_dir, f"{model_name}_annotated")
    if annotate:
        os.makedirs(anno_dir, exist_ok=True)

    start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if idx % frame_skip != 0:
            idx += 1
            continue

        timestamp = idx / fps

        try:
            # -------- YOLO --------
            if hasattr(model, "predict"):
                output = model.predict(frame, verbose=False)
                label, conf = interpret_prediction(model, output, model_name)

            # -------- 3D-ResNet uses CLIPS of 16 frames --------
            else:
                frame_buffer.append(frame)

                if len(frame_buffer) < 16:
                    idx += 1
                    continue

                clip = preprocess_clip(frame_buffer[-16:], device, target_size)

                with torch.no_grad():
                    output = model(clip)

                label, conf = interpret_prediction(model, output, model_name)

            # Only record and annotate positive detections
            if label != "no_action":
                predictions.append(ActionPrediction(timestamp, idx, label, conf))
                frames_processed += 1

                # -------- Annotate output --------
                if annotate:
                    anno = frame.copy()
                    cv2.putText(
                        anno,
                        f"{label} {conf:.2f}",
                        (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),
                        2,
                    )
                    cv2.imwrite(os.path.join(anno_dir, f"{idx:06}.jpg"), anno)

        except Exception as e:
            logger.error(f"[{model_name}] Error on frame {idx}: {e}")

        idx += 1

    cap.release()

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{os.path.basename(video_path)}__{model_name}.json")

    with open(json_path, "w") as f:
        json.dump({
            "video": video_path,
            "model": model_path,
            "frames_processed": frames_processed,
            "processing_time": time.time() - start,
            "predictions": [asdict(p) for p in predictions]
        }, f, indent=2)

    logger.info(f"[{model_name}] Finished. Saved: {json_path}")


# ============================================================
# MULTI-MODEL EXECUTOR (Windows-safe)
# ============================================================
def run_models_on_videos(video_paths, model_paths,
                         output_dir="./action_recognition_outputs",
                         use_gpu=True, frame_skip=5,
                         target_size=None, annotate=True):

    os.makedirs(output_dir, exist_ok=True)
    processes = []

    for model_path in model_paths:
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        for video in video_paths:

            p = mp.Process(target=process_video_with_model,
                           args=(video, model_path, output_dir, model_name,
                                 use_gpu, frame_skip, target_size, annotate))
            p.start()
            processes.append(p)
            logger.info(f"Started PID={p.pid} → {model_name}")

    for p in processes:
        p.join()
        logger.info(f"PID={p.pid} finished with code {p.exitcode}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)   # IMPORTANT FIX ON WINDOWS

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", "-v", nargs="+", required=True)
    parser.add_argument("--models", "-m", nargs="*", default=list(MODEL_PATHS.values()))
    parser.add_argument("--output", "-o", default="./action_recognition_outputs")
    parser.add_argument("--no-gpu", action="store_true")
    parser.add_argument("--frame-skip", type=int, default=5)
    parser.add_argument("--no-annotate", action="store_true")
    args = parser.parse_args()

    run_models_on_videos(
        video_paths=args.videos,
        model_paths=args.models,
        output_dir=args.output,
        use_gpu=not args.no_gpu,
        frame_skip=max(1, args.frame_skip),
        annotate=not args.no_annotate
    )

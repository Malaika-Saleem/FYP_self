import cv2
from transformers import BlipProcessor, BlipForConditionalGeneration

# Load BLIP-2 model
model_name = "Salesforce/blip-image-captioning-large"
processor = BlipProcessor.from_pretrained(model_name)
model = BlipForConditionalGeneration.from_pretrained(model_name)

def frame_to_keywords(frame):
    # Convert OpenCV BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    inputs = processor(images=frame_rgb, return_tensors="pt")

    # Generate caption
    output_ids = model.generate(**inputs, max_length=30)
    caption = processor.decode(output_ids[0], skip_special_tokens=True)

    # Convert caption to keywords (very basic split)
    keywords = [word.strip(",.") for word in caption.split()]
    return keywords

# Read video
video_path = "motion-detection-computer-room-door-1920x1080.mp4"
cap = cv2.VideoCapture(video_path)
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % 30 == 0:  # Process every 30th frame
        keywords = frame_to_keywords(frame)
        print(f"[Frame {frame_count}] Keywords: {keywords}")

cap.release()

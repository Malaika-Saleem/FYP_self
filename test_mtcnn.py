import cv2
import numpy as np
from facenet_pytorch import MTCNN

# Read first frame
cap = cv2.VideoCapture('suspicious_activity.mp4')
ret, frame = cap.read()
cap.release()

if ret:
    print('Frame shape:', frame.shape)

    # Initialize MTCNN
    mtcnn = MTCNN(keep_all=True, min_face_size=20, thresholds=[0.5, 0.6, 0.6])

    # Detect faces
    result = mtcnn(frame, return_prob=True)
    print('MTCNN result type:', type(result))
    print('MTCNN result length:', len(result) if result else 'None')

    if result:
        if len(result) == 3:
            faces, probs, boxes = result
            print('Faces:', faces.shape if faces is not None else 'None')
            print('Probs:', probs.shape if probs is not None else 'None')
            print('Boxes:', boxes.shape if boxes is not None else 'None')

            if probs is not None:
                print('Probabilities:', probs)
        elif len(result) == 2:
            print('Only 2 values returned - no faces detected')
            faces, probs = result
            print('Faces:', faces)
            print('Probs:', probs)
        else:
            print('Unexpected result length')
else:
    print('No frame read')

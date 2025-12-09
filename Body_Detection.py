# -*- coding: utf-8 -*-
import cv2 as cv
from ultralytics import YOLO
import os
import time
import statistics
from collections import deque

# Initialize YOLO
model = YOLO("yolov8n-pose.pt")

# Initialize Camera
capture = cv.VideoCapture(0)

# Smoothing variables
height_buffer = deque(maxlen=10)  # Store last 10 height measurements
measurement_buffer = [] # Store measurements for statistical analysis
final_height = 0
measurement_done = False
REQUIRED_FRAMES = 90 # Approx 3 seconds at 30fps

saved_count = 0
max_saves = 3
save_dir = "captured_frames"

if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# Grid definitions (x1, y1, x2, y2)
HEAD_BOX = (325, 40, 375, 110)
TORSO_BOX = (300, 110, 400, 300)
LEGS_BOX = (310, 300, 390, 450)

def is_point_in_box(point, box):
    x, y = point
    bx1, by1, bx2, by2 = box
    return bx1 < x < bx2 and by1 < y < by2

while True:
    isTrue, img = capture.read()
    if not isTrue:
        break

    # Resize immediately to ensure consistency between processing and display
    img = cv.resize(img, (700, 500))
    
    # YOLO Inference
    results = model(img, verbose=False)
    
    # Default color for grid (Red)
    grid_color = (0, 0, 255)
    aligned = False

    # Check if keypoints are detected
    if results[0].keypoints is not None and results[0].keypoints.xy.shape[0] > 0:
        # Use the plotted image from YOLO for visualization (draws skeleton)
        img = results[0].plot(boxes=False)
        
        # Get keypoints (first person)
        kpts = results[0].keypoints.xy[0].cpu().numpy()
        
        # Ensure we have enough keypoints (YOLO pose has 17 keypoints)
        if len(kpts) >= 17:
            # Key points coordinates
            # YOLO Index 0: Nose
            nose = (int(kpts[0][0]), int(kpts[0][1]))
            
            # YOLO Index 11: Left Hip, 12: Right Hip
            left_hip = kpts[11]
            right_hip = kpts[12]
            mid_hip = (int((left_hip[0] + right_hip[0]) / 2), int((left_hip[1] + right_hip[1]) / 2))
            
            # YOLO Index 15: Left Ankle, 16: Right Ankle
            left_ankle = kpts[15]
            right_ankle = kpts[16]
            mid_ankle = (int((left_ankle[0] + right_ankle[0]) / 2), int((left_ankle[1] + right_ankle[1]) / 2))

            # Check alignment
            head_aligned = is_point_in_box(nose, HEAD_BOX)
            torso_aligned = is_point_in_box(mid_hip, TORSO_BOX)
            legs_aligned = is_point_in_box(mid_ankle, LEGS_BOX)

            if head_aligned and torso_aligned and legs_aligned:
                grid_color = (0, 255, 0) # Green
                aligned = True
            else:
                grid_color = (0, 0, 255) # Red
                aligned = False

            # Height Calculation
            # Original used MediaPipe Index 6 (Right Eye Outer) and 31 (Left Foot Index)
            # YOLO Mapping: Index 2 (Right Eye) and Index 15 (Left Ankle)
            
            cx2, cy2 = int(kpts[2][0]), int(kpts[2][1]) # Right Eye
            cx1, cy1 = int(kpts[15][0]), int(kpts[15][1]) # Left Ankle
            
            # Draw points used for height
            cv.circle(img, (cx2, cy2), 10, (255, 0, 0), cv.FILLED)
            cv.circle(img, (cx1, cy1), 10, (255, 0, 0), cv.FILLED)
            
            # Calculate distance
            d = ((cx2 - cx1)**2 + (cy2 - cy1)**2)**0.5
            
            # Calculate height (using the 0.5 factor from original code, but smoothed)
            raw_height = (d * 0.5)
            height_buffer.append(raw_height)
            
            avg_height = sum(height_buffer) / len(height_buffer)
            di = round(avg_height)
            
            # Display Height
            if not measurement_done:
                cv.putText(img, f"Height: {di} cms", (40, 70), cv.FONT_HERSHEY_DUPLEX, 1, (255, 255, 0), 2)
            else:
                cv.putText(img, f"Final Height: {round(final_height)} cms", (40, 70), cv.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                
            cv.putText(img, "Stand approx 3 meters away", (40, 450), cv.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

    # Handle Capture & Measurement Logic
    if aligned:
        if not measurement_done:
            # Add to statistical buffer
            measurement_buffer.append(raw_height)
            
            # Calculate progress
            progress = min(100, int((len(measurement_buffer) / REQUIRED_FRAMES) * 100))
            cv.putText(img, f"Hold Still: {progress}%", (200, 200), cv.FONT_HERSHEY_DUPLEX, 1, (0, 255, 255), 2)
            
            # Capture frames at intervals (e.g., every 30 frames)
            if len(measurement_buffer) % 30 == 0 and saved_count < max_saves:
                filename = f"{save_dir}/capture_{int(time.time())}_{saved_count}.jpg"
                cv.imwrite(filename, img)
                saved_count += 1
                print(f"Saved {filename}")
            
            # Finalize measurement
            if len(measurement_buffer) >= REQUIRED_FRAMES:
                final_height = statistics.median(measurement_buffer)
                measurement_done = True
                
        else:
             cv.putText(img, "Measurement Complete!", (200, 200), cv.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
             cv.putText(img, f"Final: {round(final_height)} cm", (200, 250), cv.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 0), 3)
    else:
        # Reset if alignment is lost
        if not measurement_done:
            measurement_buffer = []
            saved_count = 0
        else:
            # Optional: Reset after they leave the frame or break alignment for a while
            # For now, we reset immediately to allow re-measurement
            measurement_buffer = []
            measurement_done = False
            saved_count = 0

    # Draw tight fit guide mask with current status color
    # Head Area
    cv.rectangle(img, (HEAD_BOX[0], HEAD_BOX[1]), (HEAD_BOX[2], HEAD_BOX[3]), grid_color, 2)
    cv.putText(img, "Head", (330, 35), cv.FONT_HERSHEY_PLAIN, 1, grid_color, 1)
    
    # Torso Area
    cv.rectangle(img, (TORSO_BOX[0], TORSO_BOX[1]), (TORSO_BOX[2], TORSO_BOX[3]), grid_color, 2)
    
    # Legs Area
    cv.rectangle(img, (LEGS_BOX[0], LEGS_BOX[1]), (LEGS_BOX[2], LEGS_BOX[3]), grid_color, 2)

    # Grid lines on ground level
    cv.line(img, (0, 450), (700, 450), (200, 200, 200), 1)
    cv.line(img, (0, 480), (700, 480), (200, 200, 200), 1)
    # Perspective lines
    cv.line(img, (250, 450), (200, 500), (200, 200, 200), 1)
    cv.line(img, (450, 450), (500, 500), (200, 200, 200), 1)
    cv.line(img, (350, 450), (350, 500), (200, 200, 200), 1)

    cv.imshow("Height Measurement", img)

    if cv.waitKey(20) & 0xFF == ord('q'):
        break

capture.release()
cv.destroyAllWindows()

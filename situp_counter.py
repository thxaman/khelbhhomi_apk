import cv2
import numpy as np
from yolo_onnx import YOLOv8Pose

class SitUpCounter:
    def __init__(self):
        # Initialize the ONNX wrapper
        self.model = YOLOv8Pose("yolov8n-pose.onnx")
        self.counter = 0
        self.stage = None  # "down" or "up"

    def calculate_angle(self, a, b, c):
        """
        Calculates the angle between three points (a, b, c).
        a, b, c are tuples/lists of (x, y).
        """
        a = np.array(a)  # First
        b = np.array(b)  # Mid
        c = np.array(c)  # End

        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)

        if angle > 180.0:
            angle = 360 - angle

        return angle

    def process_frame(self, frame):
        """
        Process a single frame: detect pose, count sit-ups, draw skeleton.
        """
        # Run inference
        results = self.model(frame)

        # If no person detected, just return the frame
        if results.keypoints.data is None:
            return frame

        # We'll take the first person detected
        # keypoints shape is (17, 3) -> (x, y, conf)
        # In our wrapper, results.keypoints.data holds the raw (17, 3) array for the best detection
        person_kpts = results.keypoints.data

        # Extract landmarks for sit-up (Left side: 5, 11, 13; Right side: 6, 12, 14)
        # 5: L-Shoulder, 11: L-Hip, 13: L-Knee
        # 6: R-Shoulder, 12: R-Hip, 14: R-Knee
        
        # We'll use the left side for this example
        l_shoulder = person_kpts[5][:2]
        l_hip = person_kpts[11][:2]
        l_knee = person_kpts[13][:2]

        # Calculate angle at the hip
        angle = self.calculate_angle(l_shoulder, l_hip, l_knee)

        # Sit-up logic
        if angle > 120:
            self.stage = "down"
        if angle < 30 and self.stage == 'down':
            self.stage = "up"
            self.counter += 1
            print(f"Sit-up count: {self.counter}")

        # Draw the skeleton and landmarks
        frame = self.model.draw_skeleton(frame, person_kpts)

        # Draw the angle and count
        cv2.putText(frame, str(int(angle)), 
                    (int(l_hip[0]), int(l_hip[1])), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.putText(frame, f'Sit-ups: {self.counter}', 
                    (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        
        return frame

import cv2
from ultralytics import YOLO
import math

class SitUpCounter:
    def __init__(self):
        # Use yolov8n-pose.pt as it is available in the workspace
        self.model = YOLO("yolov8n-pose.pt")
        self.count = 0
        self.stage = None
        self.first_up_detected = False

    def calculate_angle(self, a, b, c):
        ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) -
                           math.atan2(a[1]-b[1], a[0]-b[0]))
        return abs(ang if ang <= 180 else 360-ang)

    def process_frame(self, frame):
        results = self.model(frame, verbose=False)
        kpts = results[0].keypoints.xy[0].cpu() if results[0].keypoints is not None and len(results[0].keypoints) > 0 else None

        if kpts is not None and len(kpts) >= 14:
            # Body keypoints
            shoulder = kpts[5]   # left shoulder
            hip      = kpts[11]  # left hip
            knee     = kpts[13]  # left knee

            # Ensure confidence is high enough (optional but good practice)
            if shoulder[0] != 0 and hip[0] != 0 and knee[0] != 0:
                angle = self.calculate_angle(shoulder, hip, knee)

                # ------------ SIT-UP LOGIC ------------
                up_thresh   = 140   # adjust if needed
                down_thresh = 80

                # Sitting UP
                if angle > up_thresh:
                    if not self.first_up_detected:
                        self.first_up_detected = True
                    self.stage = "up"

                # Lying DOWN
                elif angle < down_thresh and self.first_up_detected:
                    if self.stage == "up":
                        self.count += 1            # REP!
                        print(f"Rep Count: {self.count}")
                    self.stage = "down"

                # ----------- DRAW KEYPOINTS -----------
                s_pt = (int(shoulder[0]), int(shoulder[1]))
                h_pt = (int(hip[0]), int(hip[1]))
                k_pt = (int(knee[0]), int(knee[1]))
                
                cv2.line(frame, s_pt, h_pt, (255, 255, 0), 3)
                cv2.line(frame, h_pt, k_pt, (255, 255, 0), 3)
                
                cv2.circle(frame, s_pt, 7, (0, 0, 255), -1)
                cv2.circle(frame, h_pt, 7, (0, 0, 255), -1)
                cv2.circle(frame, k_pt, 7, (0, 0, 255), -1)

        # ----------- DISPLAY TEXT -----------
        cv2.putText(frame, f"Sit-Ups: {self.count}", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 3)
        
        return frame

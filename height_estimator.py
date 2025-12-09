import cv2
from yolo_onnx import YOLOv8Pose
import os
import time
import statistics
from collections import deque

class HeightEstimator:
    def __init__(self):
        # Use ONNX model
        self.model = YOLOv8Pose("yolov8n-pose.onnx")
        self.height_buffer = deque(maxlen=10)
        self.measurement_buffer = []
        self.final_height = 0
        self.measurement_done = False
        self.REQUIRED_FRAMES = 90
        self.saved_count = 0
        self.max_saves = 3
        self.save_dir = "captured_frames"
        
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # Grid definitions
        self.HEAD_BOX = (325, 40, 375, 110)
        self.TORSO_BOX = (300, 110, 400, 300)
        self.LEGS_BOX = (310, 300, 390, 450)

    def is_point_in_box(self, point, box):
        x, y = point
        bx1, by1, bx2, by2 = box
        return bx1 < x < bx2 and by1 < y < by2

    def process_frame(self, img):
        # Resize immediately to ensure consistency
        img = cv2.resize(img, (700, 500))
        results = self.model(img, verbose=False)
        
        grid_color = (0, 0, 255)
        aligned = False
        raw_height = 0

        if results.keypoints.data is not None:
            # Draw skeleton manually
            kpts = results.keypoints.xy.numpy()[0] # Get (17, 2) array
            
            # Draw skeleton using our helper
            full_kpts = results.keypoints.data # Access the raw numpy array from Keypoints class
            img = self.model.draw_skeleton(img, full_kpts)
            
            if len(kpts) >= 17:
                nose = (int(kpts[0][0]), int(kpts[0][1]))
                left_hip = kpts[11]
                right_hip = kpts[12]
                mid_hip = (int((left_hip[0] + right_hip[0]) / 2), int((left_hip[1] + right_hip[1]) / 2))
                left_ankle = kpts[15]
                right_ankle = kpts[16]
                mid_ankle = (int((left_ankle[0] + right_ankle[0]) / 2), int((left_ankle[1] + right_ankle[1]) / 2))

                head_aligned = self.is_point_in_box(nose, self.HEAD_BOX)
                torso_aligned = self.is_point_in_box(mid_hip, self.TORSO_BOX)
                legs_aligned = self.is_point_in_box(mid_ankle, self.LEGS_BOX)

                if head_aligned and torso_aligned and legs_aligned:
                    grid_color = (0, 255, 0)
                    aligned = True
                else:
                    grid_color = (0, 0, 255)
                    aligned = False

                cx2, cy2 = int(kpts[2][0]), int(kpts[2][1])
                cx1, cy1 = int(kpts[15][0]), int(kpts[15][1])
                
                cv2.circle(img, (cx2, cy2), 10, (255, 0, 0), cv2.FILLED)
                cv2.circle(img, (cx1, cy1), 10, (255, 0, 0), cv2.FILLED)
                
                d = ((cx2 - cx1)**2 + (cy2 - cy1)**2)**0.5
                raw_height = (d * 0.5)
                self.height_buffer.append(raw_height)
                
                avg_height = sum(self.height_buffer) / len(self.height_buffer)
                di = round(avg_height)
                
                if not self.measurement_done:
                    cv2.putText(img, f"Height: {di} cms", (40, 70), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 0), 2)
                else:
                    cv2.putText(img, f"Final Height: {round(self.final_height)} cms", (40, 70), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                    
                cv2.putText(img, "Stand approx 3 meters away", (40, 450), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

        if aligned:
            if not self.measurement_done:
                self.measurement_buffer.append(raw_height)
                progress = min(100, int((len(self.measurement_buffer) / self.REQUIRED_FRAMES) * 100))
                cv2.putText(img, f"Hold Still: {progress}%", (200, 200), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 255), 2)
                
                if len(self.measurement_buffer) % 30 == 0 and self.saved_count < self.max_saves:
                    filename = f"{self.save_dir}/capture_{int(time.time())}_{self.saved_count}.jpg"
                    cv2.imwrite(filename, img)
                    self.saved_count += 1
                    print(f"Saved {filename}")
                
                if len(self.measurement_buffer) >= self.REQUIRED_FRAMES:
                    self.final_height = statistics.median(self.measurement_buffer)
                    self.measurement_done = True
            else:
                    cv2.putText(img, "Measurement Complete!", (200, 200), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(img, f"Final: {round(self.final_height)} cm", (200, 250), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 0), 3)
        else:
            if not self.measurement_done:
                self.measurement_buffer = []
                self.saved_count = 0
            else:
                self.measurement_buffer = []
                self.measurement_done = False
                self.saved_count = 0

        cv2.rectangle(img, (self.HEAD_BOX[0], self.HEAD_BOX[1]), (self.HEAD_BOX[2], self.HEAD_BOX[3]), grid_color, 2)
        cv2.putText(img, "Head", (330, 35), cv2.FONT_HERSHEY_PLAIN, 1, grid_color, 1)
        cv2.rectangle(img, (self.TORSO_BOX[0], self.TORSO_BOX[1]), (self.TORSO_BOX[2], self.TORSO_BOX[3]), grid_color, 2)
        cv2.rectangle(img, (self.LEGS_BOX[0], self.LEGS_BOX[1]), (self.LEGS_BOX[2], self.LEGS_BOX[3]), grid_color, 2)

        cv2.line(img, (0, 450), (700, 450), (200, 200, 200), 1)
        cv2.line(img, (0, 480), (700, 480), (200, 200, 200), 1)
        cv2.line(img, (250, 450), (200, 500), (200, 200, 200), 1)
        cv2.line(img, (450, 450), (500, 500), (200, 200, 200), 1)
        cv2.line(img, (350, 450), (350, 500), (200, 200, 200), 1)

        return img

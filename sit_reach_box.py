import cv2
import numpy as np
from yolo_onnx import YOLOv8Pose, YOLOv8Detect

class SitReachBoxAnalyzer:
    def __init__(self):
        self.pose_model = YOLOv8Pose("yolov8n-pose.onnx")
        # We assume the user will provide this model. If not, it will fail gracefully or we can try-catch.
        try:
            self.box_model = YOLOv8Detect("sitreach.onnx") # User needs to export this!
        except:
            print("Warning: sitreach.onnx not found. Box detection disabled.")
            self.box_model = None
            
        self.box_history = []
        self.scale_history = []
        self.last_pixels_per_cm = None
        self.BOX_REAL_HEIGHT_CM = 30.0
        self.max_reach_cm = -999

    def process_frame(self, frame):
        # 1. Detect Box
        box_bbox = None
        if self.box_model:
            box_results = self.box_model(frame)
            if box_results.boxes:
                # Take best box
                best_box = max(box_results.boxes, key=lambda b: b.conf.numpy()[0])
                if best_box.conf.numpy()[0] > 0.15:
                    box_bbox = best_box.xyxy[0] # x1, y1, x2, y2

        # 2. Detect Pose
        pose_results = self.pose_model(frame)
        
        # Draw Box
        pixels_per_cm = None
        if box_bbox is not None:
            bx1, by1, bx2, by2 = map(int, box_bbox)
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
            
            box_height_px = by2 - by1
            if box_height_px > 0:
                pixels_per_cm = box_height_px / self.BOX_REAL_HEIGHT_CM
                self.last_pixels_per_cm = pixels_per_cm
        
        if pixels_per_cm is None:
            pixels_per_cm = self.last_pixels_per_cm

        # 3. Logic
        if pose_results.keypoints.data is not None and pixels_per_cm:
            frame = self.pose_model.draw_skeleton(frame, pose_results.keypoints.data)
            kps = pose_results.keypoints.data
            
            l_wrist = kps[9]; r_wrist = kps[10]
            l_ankle = kps[15]; r_ankle = kps[16]
            
            if l_wrist[2] > 0.3 or r_wrist[2] > 0.3:
                wrist_x = []
                if l_wrist[2] > 0.3: wrist_x.append(l_wrist[0])
                if r_wrist[2] > 0.3: wrist_x.append(r_wrist[0])
                avg_wrist_x = np.mean(wrist_x)
                
                ankle_x = []
                if l_ankle[2] > 0.3: ankle_x.append(l_ankle[0])
                if r_ankle[2] > 0.3: ankle_x.append(r_ankle[0])
                
                if ankle_x:
                    avg_ankle_x = np.mean(ankle_x)
                    
                    # Determine direction based on box or ankles
                    # Assuming box is target
                    if box_bbox is not None:
                        box_center_x = (box_bbox[0] + box_bbox[2]) / 2
                        if avg_ankle_x < box_center_x:
                            reach_px = avg_wrist_x - avg_ankle_x
                        else:
                            reach_px = avg_ankle_x - avg_wrist_x
                    else:
                        # Fallback: assume reaching right if wrist > ankle
                        reach_px = avg_wrist_x - avg_ankle_x
                        
                    reach_cm = reach_px / pixels_per_cm
                    if reach_cm > self.max_reach_cm:
                        self.max_reach_cm = reach_cm
                        
                    cv2.putText(frame, f"Reach: {reach_cm:.1f} cm", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                    cv2.putText(frame, f"Max: {self.max_reach_cm:.1f} cm", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 215, 0), 3)

        return frame

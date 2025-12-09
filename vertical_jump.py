import cv2
import numpy as np
from yolo_onnx import YOLOv8Pose

class VerticalJumpAnalyzer:
    def __init__(self, user_height_cm=170):
        self.model = YOLOv8Pose("yolov8n-pose.onnx")
        self.user_height_cm = user_height_cm
        
        self.calib_frames = []
        self.calib_data = None
        self.CALIB_COUNT = 30
        
        self.hip_hist = []
        self.stage = "waiting"
        self.peak_hip = None
        self.baseline_hip = None
        self.pix_per_cm = None
        
        self.final_height_cm = 0.0

    def process_frame(self, frame):
        results = self.model(frame)
        
        if results.keypoints.data is not None:
            frame = self.model.draw_skeleton(frame, results.keypoints.data)
            kps = results.keypoints.data
            
            l_hip, r_hip = kps[11], kps[12]
            l_ankle, r_ankle = kps[15], kps[16]
            nose = kps[0]
            
            if l_hip[2] > 0.5 and r_hip[2] > 0.5:
                hip_center_y = (l_hip[1] + r_hip[1]) / 2.0
                
                # Calibration Phase
                if self.calib_data is None:
                    if len(self.calib_frames) < self.CALIB_COUNT:
                        # Collect height data
                        if l_ankle[2] > 0.5 and r_ankle[2] > 0.5:
                            avg_ankle_y = (l_ankle[1] + r_ankle[1]) / 2.0
                            height_px = abs(avg_ankle_y - nose[1])
                            self.calib_frames.append((height_px, hip_center_y))
                            cv2.putText(frame, f"Calibrating... {len(self.calib_frames)}/{self.CALIB_COUNT}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    else:
                        # Compute calibration
                        heights = [x[0] for x in self.calib_frames]
                        hips = [x[1] for x in self.calib_frames]
                        median_h = np.median(heights)
                        self.pix_per_cm = median_h / self.user_height_cm
                        self.baseline_hip = np.median(hips)
                        self.calib_data = True
                
                # Measurement Phase
                else:
                    # Draw baseline
                    cv2.line(frame, (0, int(self.baseline_hip)), (frame.shape[1], int(self.baseline_hip)), (0, 150, 255), 1)
                    
                    self.hip_hist.append(hip_center_y)
                    if len(self.hip_hist) > 5: self.hip_hist.pop(0)
                    hip_s = np.median(self.hip_hist)
                    
                    if self.stage == "waiting":
                        if (self.baseline_hip - hip_s) > (10 * self.pix_per_cm): # Jump started
                            self.stage = "air"
                            self.peak_hip = hip_s
                    
                    elif self.stage == "air":
                        if hip_s < self.peak_hip: # Higher (smaller y)
                            self.peak_hip = hip_s
                        
                        # Landing
                        if abs(self.baseline_hip - hip_s) < (5 * self.pix_per_cm):
                            self.stage = "done"
                            jump_px = self.baseline_hip - self.peak_hip
                            self.final_height_cm = jump_px / self.pix_per_cm
                    
                    elif self.stage == "done":
                        # Reset if standing still for a while? Or just show result
                        cv2.putText(frame, f"Jump Height: {self.final_height_cm:.1f} cm", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                        
                        # Reset logic (simple)
                        if abs(self.baseline_hip - hip_s) < (5 * self.pix_per_cm):
                             # If we are back at baseline, maybe reset after 3 seconds?
                             pass

        return frame

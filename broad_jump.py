import cv2
import numpy as np
from yolo_onnx import YOLOv8Pose

class BroadJumpAnalyzer:
    def __init__(self, user_height_cm=170):
        self.model = YOLOv8Pose("yolov8n-pose.onnx")
        self.user_height_cm = user_height_cm
        
        # State: 0=Ready, 1=In Air, 2=Landed
        self.state = 0
        
        self.start_x = None
        self.start_y = None
        self.start_x_cm = None
        self.start_z_cm = None
        self.focal_length = None
        
        self.calibrated_torso_px = None
        self.calibrated_height_px = None
        self.calibration_frames = 0
        self.CALIBRATION_LIMIT = 30
        
        self.START_DEPTH_CM = 260.0 
        
        self.ankle_history = []
        self.SMOOTHING_WINDOW = 2
        
        self.max_y_during_jump = 0
        self.jump_distance_cm = 0.0
        self.last_jump_distance_cm = 0.0
        
        # Anthropometric ratio
        if self.user_height_cm >= 180:
            self.TORSO_RATIO = 0.35
        elif self.user_height_cm < 175:
            self.TORSO_RATIO = 0.52
        else:
            self.TORSO_RATIO = 0.55 + (self.user_height_cm - 175) * (-0.04)

    def process_frame(self, frame):
        results = self.model(frame)
        
        # Draw skeleton
        if results.keypoints.data is not None:
            frame = self.model.draw_skeleton(frame, results.keypoints.data)
            
            kps = results.keypoints.data # (17, 3)
            
            # Indices: 0=Nose, 5=L_Shoulder, 6=R_Shoulder, 11=L_Hip, 12=R_Hip, 15=L_Ankle, 16=R_Ankle
            nose = kps[0]
            l_sh = kps[5]; r_sh = kps[6]
            l_hip = kps[11]; r_hip = kps[12]
            l_ankle = kps[15]; r_ankle = kps[16]
            
            if l_ankle[2] > 0.5 and r_ankle[2] > 0.5:
                raw_avg_x = (l_ankle[0] + r_ankle[0]) / 2
                raw_avg_y = (l_ankle[1] + r_ankle[1]) / 2
                
                # Dimensions
                mid_sh_x = (l_sh[0] + r_sh[0]) / 2
                mid_sh_y = (l_sh[1] + r_sh[1]) / 2
                mid_hip_x = (l_hip[0] + r_hip[0]) / 2
                mid_hip_y = (l_hip[1] + r_hip[1]) / 2
                torso_len_px = np.sqrt((mid_sh_x - mid_hip_x)**2 + (mid_sh_y - mid_hip_y)**2)
                
                mid_ankle_x = (l_ankle[0] + r_ankle[0]) / 2
                mid_ankle_y = (l_ankle[1] + r_ankle[1]) / 2
                height_px = np.sqrt((nose[0] - mid_ankle_x)**2 + (nose[1] - mid_ankle_y)**2)
                
                # Smoothing
                self.ankle_history.append((raw_avg_x, raw_avg_y))
                if len(self.ankle_history) > self.SMOOTHING_WINDOW:
                    self.ankle_history.pop(0)
                avg_ankle_x = np.mean([p[0] for p in self.ankle_history])
                avg_ankle_y = np.mean([p[1] for p in self.ankle_history])
                
                # Calibration
                if self.state == 0 and self.calibration_frames < self.CALIBRATION_LIMIT:
                    if height_px > 50:
                        if self.calibrated_torso_px is None:
                            self.calibrated_torso_px = torso_len_px
                            self.calibrated_height_px = height_px
                        else:
                            self.calibrated_torso_px = (self.calibrated_torso_px * self.calibration_frames + torso_len_px) / (self.calibration_frames + 1)
                            self.calibrated_height_px = (self.calibrated_height_px * self.calibration_frames + height_px) / (self.calibration_frames + 1)
                        
                        self.calibration_frames += 1
                        cv2.putText(frame, f"Calibrating... {int(self.calibration_frames/self.CALIBRATION_LIMIT*100)}%", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Logic
                if self.calibration_frames >= self.CALIBRATION_LIMIT:
                    if self.focal_length is None:
                        real_torso_cm = self.user_height_cm * self.TORSO_RATIO
                        self.focal_length = (self.calibrated_torso_px * self.START_DEPTH_CM) / real_torso_cm
                    
                    # Depth estimation
                    current_depth_cm = self.START_DEPTH_CM # Simplified for stability
                    scale_factor = current_depth_cm / self.focal_length
                    current_x_cm = avg_ankle_x * scale_factor
                    
                    if self.start_x_cm is None:
                        self.start_x_cm = current_x_cm
                        self.start_z_cm = self.START_DEPTH_CM
                        self.start_x = avg_ankle_x
                        self.start_y = avg_ankle_y
                    
                    # Jump Logic
                    dx = current_x_cm - self.start_x_cm
                    dz = current_depth_cm - self.start_z_cm
                    current_dist_cm = np.sqrt(dx**2 + dz**2)
                    
                    vertical_rise_px = self.start_y - avg_ankle_y
                    vertical_rise_cm = vertical_rise_px * scale_factor
                    
                    if self.state == 0:
                        if vertical_rise_cm > 10:
                            self.state = 1 # In Air
                            self.max_y_during_jump = avg_ankle_y
                    
                    elif self.state == 1:
                        if avg_ankle_y < self.max_y_during_jump: # Remember Y is down
                            self.max_y_during_jump = avg_ankle_y
                        
                        # Landing detection
                        height_from_ground_cm = (self.start_y - avg_ankle_y) * scale_factor
                        if height_from_ground_cm < 10: # Back on ground
                            self.state = 2
                            self.last_jump_distance_cm = current_dist_cm
                    
                    elif self.state == 2:
                        if current_dist_cm < 20:
                            self.state = 0 # Reset
                            self.start_x_cm = None # Recalibrate start pos
                    
                    # Drawing
                    if self.start_x:
                        cv2.circle(frame, (int(self.start_x), int(self.start_y)), 5, (0, 255, 0), -1)
                        cv2.line(frame, (int(self.start_x), int(self.start_y)), (int(avg_ankle_x), int(avg_ankle_y)), (255, 255, 0), 2)
                    
                    cv2.putText(frame, f"Jump: {current_dist_cm:.1f} cm", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    if self.last_jump_distance_cm > 0:
                        cv2.putText(frame, f"Last: {self.last_jump_distance_cm:.1f} cm", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return frame

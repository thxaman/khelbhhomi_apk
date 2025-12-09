import cv2
from ultralytics import YOLO
import numpy as np
from collections import deque
import statistics

class DebugReachAnalyzer:
    def __init__(self, video_path, real_height_cm):
        self.video_path = video_path
        self.model = YOLO('yolov8n-pose.pt')
        self.REAL_HEIGHT_CM = real_height_cm
        
        # --- PHYSICS ---
        self.REAL_TIBIA_LEN = self.REAL_HEIGHT_CM * 0.246
        self.FOOT_OFFSET_CM = 15.0 
        self.HAND_OFFSET_CM = 18.0 
        
        # --- BUFFERS ---
        self.kps_buffer = deque(maxlen=10) 
        self.ankle_history = deque(maxlen=45)
        
        # --- STATE ---
        self.state = "WAITING_FOR_POSE" 
        self.attempt_state = "IDLE"     
        
        # Locked Data
        self.frozen_scale = 0.0
        self.frozen_toe_x = 0
        self.frozen_direction = 1
        self.locked_side = None # 'left' or 'right'
        
        # --- SCORING ---
        self.global_best_reach = -999.0  # Allow negative bests for debugging  
        self.current_attempt_max = -999.0  
        self.last_locked_score = 0.0    

    def get_avg_point(self, kps_list, idx):
        pts = []
        for k in kps_list:
            if k[idx][2] > 0.5:
                pts.append(k[idx][:2].cpu().numpy())
        if not pts: return None
        return np.mean(pts, axis=0)

    def check_stability(self):
        if len(self.ankle_history) < 45: return False
        xs = [p[0] for p in self.ankle_history]
        return statistics.stdev(xs) < 5.0

    def analyze(self):
        cap = cv2.VideoCapture(self.video_path)
        print("--- DEBUG MODE STARTED ---")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            results = self.model(frame, verbose=False)
            
            if results[0].keypoints is not None and results[0].keypoints.data.shape[0] > 0:
                raw_kps = results[0].keypoints.data[0]
                self.kps_buffer.append(raw_kps)
                
                if len(self.kps_buffer) < 5: continue

                # 1. SIDE SELECTION (LOCK IT ONCE CALIBRATED)
                if self.locked_side is None:
                    conf_l = raw_kps[13][2] + raw_kps[15][2]
                    conf_r = raw_kps[14][2] + raw_kps[16][2]
                    active_side = 'left' if conf_l > conf_r else 'right'
                else:
                    active_side = self.locked_side

                # 2. EXTRACT POINTS BASED ON SIDE
                if active_side == 'left':
                    knee = self.get_avg_point(self.kps_buffer, 13)
                    ankle = self.get_avg_point(self.kps_buffer, 15)
                    hip = self.get_avg_point(self.kps_buffer, 11)
                    wrist = self.get_avg_point(self.kps_buffer, 9)
                    raw_wrist_tensor = raw_kps[9] 
                else:
                    knee = self.get_avg_point(self.kps_buffer, 14)
                    ankle = self.get_avg_point(self.kps_buffer, 16)
                    hip = self.get_avg_point(self.kps_buffer, 12)
                    wrist = self.get_avg_point(self.kps_buffer, 10)
                    raw_wrist_tensor = raw_kps[10]

                if knee is None or ankle is None or hip is None: continue
                self.ankle_history.append(ankle)

                # --- PHASE 1: CALIBRATION ---
                if self.state == "WAITING_FOR_POSE":
                    cv2.putText(frame, "HANDS ON KNEES TO START", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                    cv2.circle(frame, tuple(knee.astype(int)), 40, (0, 165, 255), 2)
                    
                    is_stable = self.check_stability()
                    hands_on_knees = False
                    if wrist is not None:
                        if np.linalg.norm(wrist - knee) < 80: hands_on_knees = True
                    
                    if is_stable and hands_on_knees:
                        tibia_px = np.linalg.norm(knee - ankle)
                        scale = tibia_px / self.REAL_TIBIA_LEN
                        
                        direction = 1
                        if ankle[0] < hip[0]: direction = -1
                        
                        offset_px = self.FOOT_OFFSET_CM * scale
                        self.frozen_toe_x = int(ankle[0] + (direction * offset_px))
                        self.frozen_scale = scale
                        self.frozen_direction = direction
                        self.locked_side = active_side # PERMANENTLY LOCK SIDE
                        
                        self.state = "LOCKED"
                        print(f"LOCKED: Side={self.locked_side}, Scale={scale:.2f}")

                # --- PHASE 2: DEBUG MEASUREMENT ---
                elif self.state == "LOCKED":
                    # Draw Static Red Line
                    cv2.line(frame, (self.frozen_toe_x, 0), (self.frozen_toe_x, frame.shape[0]), (0, 0, 255), 3)
                    
                    # EXTRACT WRIST DATA
                    wrist_conf = float(raw_wrist_tensor[2])
                    wrist_x = float(raw_wrist_tensor[0])
                    wrist_y = float(raw_wrist_tensor[1])
                    
                    raw_cm = -999.0
                    
                    # VISUALIZE HAND DETECTION (Debug Dot)
                    if wrist_conf > 0.5:
                        # Draw Yellow dot = Detected but negative
                        # Draw Green dot = Detected and positive
                        reach_px = (wrist_x - self.frozen_toe_x) * self.frozen_direction
                        raw_cm = (reach_px / self.frozen_scale) + self.HAND_OFFSET_CM
                        
                        dot_color = (0, 255, 255) # Yellow
                        if raw_cm > 0: dot_color = (0, 255, 0) # Green
                            
                        cv2.circle(frame, (int(wrist_x), int(wrist_y)), 10, dot_color, -1)
                        cv2.line(frame, (int(wrist_x), int(wrist_y)), (self.frozen_toe_x, int(wrist_y)), dot_color, 1)
                        
                        # DEBUG TEXT: Show raw value always
                        cv2.putText(frame, f"RAW: {raw_cm:.1f} cm", (int(wrist_x), int(wrist_y)-30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, dot_color, 2)
                    else:
                        cv2.putText(frame, "LOST HAND TRACKING", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    # LOGIC UPDATE (Without strict positive gate)
                    if raw_cm > -900: # If valid detection
                        # Allow attempt start if > -20 (very lenient)
                        if self.attempt_state == "IDLE":
                            if raw_cm > -10.0: 
                                self.attempt_state = "REACHING"
                                self.current_attempt_max = raw_cm

                        elif self.attempt_state == "REACHING":
                            if raw_cm > self.current_attempt_max:
                                self.current_attempt_max = raw_cm
                            
                            # Retraction check
                            if (self.current_attempt_max - raw_cm) > 5.0:
                                self.last_locked_score = self.current_attempt_max
                                if self.current_attempt_max > self.global_best_reach:
                                    self.global_best_reach = self.current_attempt_max
                                self.attempt_state = "IDLE"
                                self.current_attempt_max = -999.0

                    # SCOREBOARD
                    cv2.rectangle(frame, (20, 80), (350, 200), (0, 0, 0), -1)
                    cv2.putText(frame, f"LAST: {self.last_locked_score:.1f} cm", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                    best_color = (0, 215, 255) if self.global_best_reach > 0 else (0, 0, 255)
                    cv2.putText(frame, f"BEST: {self.global_best_reach:.1f} cm", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.2, best_color, 3)

            cv2.imshow("Debug Reach", frame)
            key = cv2.waitKey(1)
            if key == ord('q'): break
            if key == ord('r'): 
                self.state = "WAITING_FOR_POSE"
                self.global_best_reach = -999.0
                self.locked_side = None

        cap.release()
        cv2.destroyAllWindows()
        print(f"FINAL BEST REACH: {self.global_best_reach:.2f} cm")

# Run
analyzer = DebugReachAnalyzer('am3.mp4', 170)
analyzer.analyze()
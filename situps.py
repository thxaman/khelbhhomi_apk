import cv2
from ultralytics import YOLO

# ---------- Load Model ----------
model = YOLO("yolo11n-pose.pt")

cap = cv2.VideoCapture("C:/Users/Nitin/Downloads/situps.mp4")
assert cap.isOpened(), "Error: Video not found!"

# ---------- Output Video ----------
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

writer = cv2.VideoWriter("situp_count.mp4",
                         cv2.VideoWriter_fourcc(*"mp4v"),
                         fps, (w, h))

# ---------- Sit-Up Counter Variables ----------
count = 0
stage = None
first_up_detected = False     # prevents starting pose rep

# ---------- Angle Helper Function ----------
def calculate_angle(a, b, c):
    import math
    ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) -
                       math.atan2(a[1]-b[1], a[0]-b[0]))
    return abs(ang if ang <= 180 else 360-ang)

# ---------- PROCESS VIDEO ----------
while True:
    ret, frame = cap.read()
    if not ret: break

    results = model(frame, pose=True, verbose=False)
    kpts = results[0].keypoints.xy[0].cpu() if len(results[0].keypoints) else None

    if kpts is not None:
        # Body keypoints
        shoulder = kpts[5]   # left shoulder
        hip      = kpts[11]  # left hip
        knee     = kpts[13]  # left knee

        angle = calculate_angle(shoulder, hip, knee)

        # ------------ SIT-UP LOGIC ------------
        up_thresh   = 140   # adjust if needed
        down_thresh = 80

        # Sitting UP
        if angle > up_thresh:
            if not first_up_detected:
                first_up_detected = True
            stage = "up"

        # Lying DOWN
        elif angle < down_thresh and first_up_detected:
            if stage == "up":
                count += 1            # REP!
                print(f"Rep Count: {count}")
            stage = "down"

        # ----------- DRAW KEYPOINTS -----------
        # Draw lines for the angle being measured (Shoulder-Hip-Knee)
        s_pt = (int(shoulder[0]), int(shoulder[1]))
        h_pt = (int(hip[0]), int(hip[1]))
        k_pt = (int(knee[0]), int(knee[1]))
        
        if s_pt[0] > 0 and h_pt[0] > 0 and k_pt[0] > 0:
            # Draw Lines
            cv2.line(frame, s_pt, h_pt, (255, 255, 0), 3)
            cv2.line(frame, h_pt, k_pt, (255, 255, 0), 3)
            
            # Draw Keypoints (Only the ones used)
            cv2.circle(frame, s_pt, 7, (0, 0, 255), -1)
            cv2.circle(frame, h_pt, 7, (0, 0, 255), -1)
            cv2.circle(frame, k_pt, 7, (0, 0, 255), -1)

        # ----------- DISPLAY TEXT -----------
        cv2.putText(frame, f"Sit-Ups: {count}", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 3)
        # cv2.putText(frame, f"Angle: {int(angle)}°", (30, 100),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        # cv2.putText(frame, f"Stage: {stage}", (30, 140),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,200,255), 2)

    # Show Real-time
    cv2.imshow("Sit-Up Counter", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    writer.write(frame)

cap.release()
writer.release()
cv2.destroyAllWindows()
print(f"Total Sit-Ups Counted = {count}")

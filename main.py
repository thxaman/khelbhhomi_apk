from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.utils import platform

import cv2
import numpy as np

# Your analyzers (unchanged)
from height_estimator import HeightEstimator
from reach_test import ReachTestAnalyzer
from situp_counter import SitUpCounter
from broad_jump import BroadJumpAnalyzer
from vertical_jump import VerticalJumpAnalyzer
from sit_reach_box import SitReachBoxAnalyzer

GLOBAL_USER_HEIGHT = 170


# ================================================
#  FIXED ANDROID CAMERA OPEN FUNCTION
# ================================================
def open_android_camera():
    """Open Camera using multiple fallback strategies for Android."""
    import time
    
    # Disable OpenCL and limit threads for stability
    cv2.setNumThreads(1)
    cv2.ocl.setUseOpenCL(False)
    
    print("[INFO] Attempting to open Android camera...")
    
    # Strategy 1: Try CAP_ANDROID backend with different indices
    for idx in [0, 1, -1]:
        try:
            print(f"[INFO] Trying CAP_ANDROID backend with index {idx}")
            cap = cv2.VideoCapture(idx, cv2.CAP_ANDROID)
            time.sleep(0.5)  # Give camera time to initialize
            
            if cap.isOpened():
                # Test if we can actually read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"[SUCCESS] Camera opened with CAP_ANDROID on index {idx}")
                    # Set optimal parameters
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    return cap
                else:
                    print(f"[WARN] Camera opened but cannot read frames on index {idx}")
                    cap.release()
            else:
                cap.release()
        except Exception as e:
            print(f"[ERROR] CAP_ANDROID index {idx} failed: {e}")
    
    # Strategy 2: Try default backend
    for idx in [0, 1]:
        try:
            print(f"[INFO] Trying default backend with index {idx}")
            cap = cv2.VideoCapture(idx)
            time.sleep(0.5)
            
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"[SUCCESS] Camera opened with default backend on index {idx}")
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    return cap
                else:
                    cap.release()
            else:
                cap.release()
        except Exception as e:
            print(f"[ERROR] Default backend index {idx} failed: {e}")
    
    print("[ERROR] All camera initialization strategies failed")
    return None


# ================================================
#  MENU SCREEN
# ================================================
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        title = Label(text="Fitness Vision Tools", font_size=32, size_hint=(1, 0.15))
        layout.add_widget(title)

        buttons = [
            ("Height Measurement", self.go_to_height),
            ("Sit and Reach (Side)", self.go_to_reach),
            ("Sit-Up Counter", self.go_to_situps),
            ("Broad Jump", self.go_to_broad),
            ("Vertical Jump", self.go_to_vertical),
            ("Sit and Reach (Box)", self.go_to_reach_box),
        ]

        for txt, func in buttons:
            b = Button(text=txt, font_size=20, background_color=(0.2, 0.5, 1, 1))
            b.bind(on_press=func)
            layout.add_widget(b)

        self.add_widget(layout)

    def go_to_height(self, inst):
        self.manager.get_screen("camera").start_camera(HeightEstimator())
        self.manager.current = "camera"

    def go_to_reach(self, inst):
        self.manager.get_screen("camera").start_camera(ReachTestAnalyzer())
        self.manager.current = "camera"

    def go_to_situps(self, inst):
        self.manager.get_screen("camera").start_camera(SitUpCounter())
        self.manager.current = "camera"

    def go_to_broad(self, inst):
        self.manager.get_screen("camera").start_camera(BroadJumpAnalyzer(user_height_cm=GLOBAL_USER_HEIGHT))
        self.manager.current = "camera"

    def go_to_vertical(self, inst):
        self.manager.get_screen("camera").start_camera(VerticalJumpAnalyzer(user_height_cm=GLOBAL_USER_HEIGHT))
        self.manager.current = "camera"

    def go_to_reach_box(self, inst):
        self.manager.get_screen("camera").start_camera(SitReachBoxAnalyzer())
        self.manager.current = "camera"


# ================================================
#  CAMERA SCREEN (FULLY FIXED)
# ================================================
class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super(CameraScreen, self).__init__(**kwargs)

        self.layout = BoxLayout(orientation="vertical")
        self.img_widget = Image()

        self.layout.add_widget(self.img_widget)

        back = Button(text="Back to Menu", size_hint=(1, 0.1), background_color=(1, 0, 0, 1))
        back.bind(on_press=self.stop_camera)
        self.layout.add_widget(back)

        self.add_widget(self.layout)

        self.capture = None
        self.processor = None
        self.event = None

    def start_camera(self, processor):
        """Start camera with permission checks and retry logic."""
        print("[INFO] Starting camera…")
        self.processor = processor
        
        # Check permissions on Android
        if platform == "android":
            app = App.get_running_app()
            
            # Wait a bit for permissions to be processed
            from time import sleep
            sleep(0.5)
            
            if not app.permissions_granted:
                print("[ERROR] Camera permissions not granted")
                self.show_error("Camera permission required.\nPlease grant permission and restart the app.")
                return
        
        # Try to open camera
        if platform == "android":
            self.capture = open_android_camera()
        else:
            self.capture = cv2.VideoCapture(0)

        if not self.capture or not self.capture.isOpened():
            print("[ERROR] Camera unavailable.")
            self.show_error("Camera could not be opened.\nTry:\n1. Restart the app\n2. Check camera permissions\n3. Close other camera apps")
            return

        print("[INFO] Camera opened successfully!")
        self.hide_error()
        self.event = Clock.schedule_interval(self.update, 1/30)

    # -------------------------
    def stop_camera(self, *args):
        if self.event:
            self.event.cancel()

        if self.capture:
            self.capture.release()

        self.capture = None
        self.processor = None
        self.manager.current = "menu"

    # -------------------------
    def update(self, dt):
        global GLOBAL_USER_HEIGHT

        if not self.capture:
            return

        ret, frame = self.capture.read()
        if not ret or frame is None:
            print("[WARN] Empty or invalid frame.")
            return
        
        # Validate frame has valid dimensions
        if frame.shape[0] == 0 or frame.shape[1] == 0:
            print("[WARN] Frame has invalid dimensions.")
            return

        # Apply your analyzer
        if self.processor:
            try:
                frame = self.processor.process_frame(frame)
            except Exception as e:
                print(f"[ERROR] Frame processing failed: {e}")
                return

            # update global height from height estimator
            if isinstance(self.processor, HeightEstimator):
                result = self.processor.get_height()
                if result:
                    GLOBAL_USER_HEIGHT = result

        # Kivy uses bottom-left origin → flip vertically
        frame = cv2.flip(frame, 0)

        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="bgr")
        texture.blit_buffer(frame.tobytes(), colorfmt="bgr", bufferfmt="ubyte")
        self.img_widget.texture = texture

    # -------------------------
    def show_error(self, text):
        self.hide_error()
        self.error_lbl = Label(text=text, color=(1, 0, 0, 1), font_size=24)
        self.layout.add_widget(self.error_lbl)

    def hide_error(self):
        if hasattr(self, "error_lbl"):
            self.layout.remove_widget(self.error_lbl)
            del self.error_lbl


# ================================================
#  MAIN APP
# ================================================
class FitnessApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.permissions_granted = False
        
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(CameraScreen(name="camera"))
        return sm

    def on_start(self):
        """Request permissions when app starts."""
        if platform == "android":
            from android.permissions import request_permissions, Permission, check_permission
            
            # Check if we already have camera permission
            has_camera = check_permission(Permission.CAMERA)
            
            if has_camera:
                print("[INFO] Camera permission already granted")
                self.permissions_granted = True
            else:
                print("[INFO] Requesting camera permissions...")
                request_permissions([
                    Permission.CAMERA,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE
                ], self.permission_callback)
        else:
            # On desktop, permissions are not needed
            self.permissions_granted = True
    
    def permission_callback(self, permissions, grant_results):
        """Callback when permissions are granted or denied."""
        if all(grant_results):
            print("[INFO] All permissions granted!")
            self.permissions_granted = True
        else:
            print("[WARN] Some permissions were denied")
            self.permissions_granted = False


if __name__ == "__main__":
    FitnessApp().run()

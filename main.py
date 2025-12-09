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
    """Open Camera using Android Camera2 backend + fail-safe settings."""
    cv2.setNumThreads(1)
    cv2.ocl.setUseOpenCL(False)

    for idx in [0, 1]:
        cap = cv2.VideoCapture(idx, cv2.CAP_ANDROID)

        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            print(f"[INFO] Android camera opened on index {idx}")
            return cap

        cap.release()

    print("[ERROR] Failed to open Android camera")
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
        print("[INFO] Starting camera…")
        self.processor = processor

        if platform == "android":
            self.capture = open_android_camera()
        else:
            self.capture = cv2.VideoCapture(0)

        if not self.capture or not self.capture.isOpened():
            print("[ERROR] Camera unavailable.")
            self.show_error("Camera could not be opened.\nCheck permissions.")
            return

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
        if not ret:
            print("[WARN] Empty frame.")
            return

        # Apply your analyzer
        if self.processor:
            frame = self.processor.process_frame(frame)

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
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(CameraScreen(name="camera"))
        return sm

    def on_start(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission

            request_permissions([
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])


if __name__ == "__main__":
    FitnessApp().run()

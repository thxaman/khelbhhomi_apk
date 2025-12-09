from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window

import cv2
import numpy as np

# Import our refactored modules
from height_estimator import HeightEstimator
from reach_test import ReachTestAnalyzer
from situp_counter import SitUpCounter

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        title = Label(text="Fitness Vision Tools", font_size=32, size_hint=(1, 0.2))
        layout.add_widget(title)
        
        btn_height = Button(text="Height Measurement", font_size=24, background_color=(0, 0.5, 1, 1))
        btn_height.bind(on_press=self.go_to_height)
        layout.add_widget(btn_height)
        
        btn_reach = Button(text="Sit and Reach Test", font_size=24, background_color=(0, 0.8, 0.2, 1))
        btn_reach.bind(on_press=self.go_to_reach)
        layout.add_widget(btn_reach)
        
        btn_situps = Button(text="Sit-Up Counter", font_size=24, background_color=(1, 0.5, 0, 1))
        btn_situps.bind(on_press=self.go_to_situps)
        layout.add_widget(btn_situps)
        
        self.add_widget(layout)

    def go_to_height(self, instance):
        self.manager.get_screen('camera').start_camera(HeightEstimator())
        self.manager.current = 'camera'

    def go_to_reach(self, instance):
        self.manager.get_screen('camera').start_camera(ReachTestAnalyzer())
        self.manager.current = 'camera'

    def go_to_situps(self, instance):
        self.manager.get_screen('camera').start_camera(SitUpCounter())
        self.manager.current = 'camera'

class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super(CameraScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')
        
        # Camera Image Widget
        self.img_widget = Image()
        self.layout.add_widget(self.img_widget)
        
        # Back Button
        btn_back = Button(text="Back to Menu", size_hint=(1, 0.1), background_color=(1, 0, 0, 1))
        btn_back.bind(on_press=self.stop_camera)
        self.layout.add_widget(btn_back)
        
        self.add_widget(self.layout)
        
        self.capture = None
        self.event = None
        self.processor = None

    def start_camera(self, processor):
        self.processor = processor
        # 0 is usually the default camera. On Android, this might need adjustment or permissions.
        self.capture = cv2.VideoCapture(0)
        self.event = Clock.schedule_interval(self.update, 1.0 / 30.0) # 30 FPS

    def stop_camera(self, instance=None):
        if self.event:
            self.event.cancel()
        if self.capture:
            self.capture.release()
        self.capture = None
        self.processor = None
        self.manager.current = 'menu'

    def update(self, dt):
        if self.capture:
            ret, frame = self.capture.read()
            if ret:
                # Process the frame using the selected logic
                if self.processor:
                    frame = self.processor.process_frame(frame)

                # Convert to Kivy Texture
                # Flip vertical because Kivy textures are upside down
                buf1 = cv2.flip(frame, 0)
                buf = buf1.tobytes()
                image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                
                self.img_widget.texture = image_texture

class FitnessApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CameraScreen(name='camera'))
        return sm

if __name__ == '__main__':
    FitnessApp().run()

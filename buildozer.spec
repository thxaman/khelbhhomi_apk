[app]

title = KhelBhoomi
package.name = khelbhoomi
package.domain = org.khelbhoomi

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,pt,onnx

version = 0.1

requirements = python3,kivy,opencv,numpy,pillow

orientation = portrait
fullscreen = 1

# Android permissions - CRITICAL for camera access
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Android features - REQUIRED for camera to work
android.features = android.hardware.camera, android.hardware.camera.autofocus

# API levels
android.api = 33
android.minapi = 21
android.ndk = 25b

# AndroidX support
android.enable_androidx = True

# Gradle dependencies for camera support
android.gradle_dependencies = androidx.camera:camera-core:1.1.0, androidx.camera:camera-camera2:1.1.0, androidx.camera:camera-lifecycle:1.1.0

# Meta-data for legacy camera support
android.meta_data = android.hardware.camera=true, android.hardware.camera.autofocus=true

# Build artifacts
android.release_artifact = aab
android.debug_artifact = apk

# Add wakelock to prevent screen from sleeping during camera use
android.wakelock = True

[buildozer]
log_level = 2
warn_on_root = 1

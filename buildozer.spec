[app]

title = KhelBhoomi
package.name = KhelBhoomi
package.domain = org.fitness

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,pt,onnx

version = 0.1

# WORKING REQUIREMENTS FOR ANDROID
requirements = python3,kivy,opencv,numpy,pillow

orientation = portrait
fullscreen = 1

# ----------------------------------------------
# ANDROID SETTINGS
# ----------------------------------------------
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, RECORD_AUDIO

android.api = 33
android.minapi = 21

# Valid NDK
android.ndk = 23b

# Recommended (to avoid Jetifier errors)
android.enable_androidx = True

# Packaging formats
android.release_artifact = aab
android.debug_artifact = apk


# ----------------------------------------------
# PYTHON-FOR-ANDROID (default usually works)
# ----------------------------------------------
# p4a.bootstrap = sdl2


# ----------------------------------------------
# BUILDOZER SETTINGS
# ----------------------------------------------
[buildozer]
log_level = 2
warn_on_root = 1

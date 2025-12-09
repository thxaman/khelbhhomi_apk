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

android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, RECORD_AUDIO

android.api = 33
android.minapi = 21
android.ndk = 25b

android.enable_androidx = True
android.release_artifact = aab
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1

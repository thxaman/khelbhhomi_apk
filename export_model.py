from ultralytics import YOLO

# Load the YOLOv8 model
model = YOLO("yolov8n-pose.pt")

# Export the model to ONNX format
# opset=12 is widely supported by OpenCV
model.export(format="onnx", opset=12)

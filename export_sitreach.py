from ultralytics import YOLO

# Load the custom trained model
model = YOLO("sitreach.pt")

# Export the model to ONNX format
# opset=12 is widely supported by OpenCV
model.export(format="onnx", opset=12)

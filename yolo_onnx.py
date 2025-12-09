import cv2
import numpy as np

class YOLOv8Pose:
    def __init__(self, path, conf_thres=0.5, iou_thres=0.45):
        self.net = cv2.dnn.readNetFromONNX(path)
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        # Keypoint connections for drawing skeleton (COCO format)
        self.skeleton = [
            (15, 13), (13, 11), (16, 14), (14, 12), (11, 12), 
            (5, 11), (6, 12), (5, 6), (5, 7), (6, 8), 
            (7, 9), (8, 10), (1, 2), (0, 1), (0, 2), 
            (1, 3), (2, 4), (3, 5), (4, 6)
        ]
        self.palette = [
            (255, 128, 0), (255, 153, 51), (255, 178, 102), (230, 230, 0), (255, 153, 255),
            (153, 204, 255), (255, 102, 255), (255, 51, 255), (102, 178, 255), (51, 153, 255),
            (255, 153, 153), (255, 102, 102), (255, 51, 51), (153, 255, 153), (102, 255, 102),
            (51, 255, 51), (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 255)
        ]

    def __call__(self, img, verbose=False):
        # Preprocess
        blob = cv2.dnn.blobFromImage(img, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        
        # Inference
        # Output shape: 1 x 56 x 8400
        # 56 channels: 4 box (cx,cy,w,h) + 1 score + 51 kpts (17 * 3)
        out = self.net.forward()
        
        # Postprocess
        out = out[0] # Remove batch dim -> 56 x 8400
        out = out.transpose() # -> 8400 x 56
        
        # Filter by score
        scores = out[:, 4]
        mask = scores > self.conf_thres
        out = out[mask]
        scores = scores[mask]
        
        if len(out) == 0:
            return Results(None)
            
        # NMS
        boxes = out[:, 0:4]
        # Convert cx,cy,w,h to x1,y1,w,h for NMS
        boxes_nms = boxes.copy()
        boxes_nms[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
        boxes_nms[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
        
        indices = cv2.dnn.NMSBoxes(boxes_nms.tolist(), scores.tolist(), self.conf_thres, self.iou_thres)
        
        if len(indices) == 0:
            return Results(None)
            
        # Get best detection (assuming single person for now or taking best)
        idx = indices[0] # Take best match
        best_det = out[idx]
        
        # Extract keypoints
        # Keypoints start at index 5
        # Shape: 17 keypoints * 3 values (x, y, conf)
        kpts_raw = best_det[5:]
        kpts = []
        
        # Scale keypoints back to original image size
        h, w = img.shape[:2]
        scale_x = w / 640
        scale_y = h / 640
        
        for i in range(0, len(kpts_raw), 3):
            x, y, conf = kpts_raw[i], kpts_raw[i+1], kpts_raw[i+2]
            kpts.append([x * scale_x, y * scale_y, conf])
            
        return Results(np.array(kpts))

    def draw_skeleton(self, img, kpts):
        # Draw points
        for i, (x, y, conf) in enumerate(kpts):
            if conf > 0.5:
                cv2.circle(img, (int(x), int(y)), 5, self.palette[i % len(self.palette)], -1)
        
        # Draw lines
        for i, (idx1, idx2) in enumerate(self.skeleton):
            if idx1 < len(kpts) and idx2 < len(kpts):
                x1, y1, c1 = kpts[idx1]
                x2, y2, c2 = kpts[idx2]
                if c1 > 0.5 and c2 > 0.5:
                    cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), self.palette[i % len(self.palette)], 2)
        return img

class Results:
    def __init__(self, kpts):
        self.keypoints = Keypoints(kpts)
        
    def plot(self, boxes=False):
        # This is a dummy method to satisfy existing code structure
        # The actual drawing should be done by passing the image to draw_skeleton
        return None 

class Keypoints:
    def __init__(self, data):
        self.data = data # numpy array of shape (17, 3)
        
    @property
    def xy(self):
        # Return structure compatible with: results[0].keypoints.xy[0]
        # Original returns tensor of shape (1, 17, 2) or (N, 17, 2)
        # We will return a wrapper that behaves like that
        if self.data is None:
            return Wrapper(np.array([]))
        return Wrapper(np.expand_dims(self.data[:, :2], axis=0))

class Wrapper:
    def __init__(self, data):
        self.data = data
        self.shape = data.shape
        
    def cpu(self):
        return self
        
    def numpy(self):
        return self.data

class YOLOv8Detect:
    def __init__(self, path, conf_thres=0.5, iou_thres=0.45):
        self.net = cv2.dnn.readNetFromONNX(path)
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres

    def __call__(self, img, verbose=False):
        blob = cv2.dnn.blobFromImage(img, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()
        
        out = out[0].transpose()
        
        # Output shape: 8400 x (4 + num_classes)
        if out.shape[1] < 5:
             return DetectResults([])

        scores = np.max(out[:, 4:], axis=1)
        mask = scores > self.conf_thres
        out = out[mask]
        scores = scores[mask]
        
        if len(out) == 0:
            return DetectResults([])
            
        class_ids = np.argmax(out[:, 4:], axis=1)
        boxes = out[:, 0:4]
        
        boxes_nms = boxes.copy()
        boxes_nms[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
        boxes_nms[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
        
        indices = cv2.dnn.NMSBoxes(boxes_nms.tolist(), scores.tolist(), self.conf_thres, self.iou_thres)
        
        final_boxes = []
        h, w = img.shape[:2]
        scale_x = w / 640
        scale_y = h / 640
        
        for i in indices:
            idx = i if isinstance(i, (int, np.integer)) else i[0]
            box = boxes_nms[idx]
            x, y, bw, bh = box
            
            x1 = x * scale_x
            y1 = y * scale_y
            x2 = (x + bw) * scale_x
            y2 = (y + bh) * scale_y
            
            conf = scores[idx]
            cls = class_ids[idx]
            
            final_boxes.append(Box(x1, y1, x2, y2, conf, cls))
            
        return DetectResults(final_boxes)

class Box:
    def __init__(self, x1, y1, x2, y2, conf, cls):
        self.xyxy = [np.array([x1, y1, x2, y2])]
        self.conf = Wrapper(np.array([conf]))
        self.cls = cls

class DetectResults:
    def __init__(self, boxes):
        self.boxes = boxes

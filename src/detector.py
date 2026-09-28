"""
YOLO Detector Module.
Processes video frames, extracts bounding boxes, classes, and confidence.
Dynamically handles class names directly from model.names.
"""
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from ultralytics import YOLO
from src.config import CONFIDENCE_THRESHOLD
from src.model_loader import load_yolo_model, get_device

class YOLODetector:
    def __init__(self, model_path: str = None, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.device = get_device()
        self.model: YOLO = load_yolo_model(model_path, device=self.device)
        self.names: Dict[int, str] = self.model.names
        
        # Identify class mappings from actual model.names
        self.fall_class_ids = [
            cid for cid, cname in self.names.items() 
            if "fall" in str(cname).lower()
        ]
        self.person_class_ids = [
            cid for cid, cname in self.names.items() 
            if "person" in str(cname).lower() or "human" in str(cname).lower()
        ]
        
        print(f"[Detector] Initialized. Total classes: {len(self.names)}")
        print(f"[Detector] Direct fall class IDs: {self.fall_class_ids}")
        print(f"[Detector] Person class IDs: {self.person_class_ids}")

    def detect(self, frame: np.ndarray, frame_number: int = 0) -> List[Dict[str, Any]]:
        """
        Run YOLO detection on a single frame.
        Returns formatted detection objects.
        """
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False
        )

        detections: List[Dict[str, Any]] = []
        
        if not results or len(results) == 0:
            return detections

        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return detections

        boxes = r.boxes
        for box in boxes:
            conf = float(box.conf[0].item()) if hasattr(box.conf[0], "item") else float(box.conf[0])
            if conf < self.confidence_threshold:
                continue

            cls_id = int(box.cls[0].item()) if hasattr(box.cls[0], "item") else int(box.cls[0])
            cls_name = self.names.get(cls_id, f"class_{cls_id}")
            
            # Coordinates [x1, y1, x2, y2]
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = [int(v) for v in xyxy]
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)
            aspect_ratio = width / height  # width / height ratio

            # Determine posture/state
            is_direct_fall_class = cls_id in self.fall_class_ids
            is_person_class = cls_id in self.person_class_ids

            # Posture estimation:
            # If explicit fall class is present:
            # If aspect ratio > 1.0 (width >= height) for person class: horizontal / lying down
            # If aspect ratio < 0.75 for person class: standing / upright
            if is_direct_fall_class:
                posture = "FALL"
                is_fall_candidate = True
            elif is_person_class:
                if aspect_ratio >= 1.0:
                    posture = "LYING_DOWN"
                    is_fall_candidate = True
                elif aspect_ratio <= 0.75:
                    posture = "STANDING"
                    is_fall_candidate = False
                else:
                    posture = "BENDING_OR_SITTING"
                    is_fall_candidate = False
            else:
                posture = "OTHER"
                is_fall_candidate = False

            det = {
                "class_id": cls_id,
                "class_name": cls_name,
                "confidence": round(conf, 4),
                "bbox": [x1, y1, x2, y2],
                "width": width,
                "height": height,
                "aspect_ratio": round(aspect_ratio, 3),
                "posture": posture,
                "is_fall_candidate": is_fall_candidate,
                "frame_number": frame_number
            }
            detections.append(det)

        return detections

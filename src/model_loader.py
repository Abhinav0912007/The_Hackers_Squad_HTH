"""
Model Loader for Ultralytics YOLO.
Supports automatic CUDA detection, CPU fallback, and exposes model properties.
"""
import torch
from pathlib import Path
from ultralytics import YOLO
from src.config import MODEL_PATH

def get_device() -> str:
    """
    Detect whether CUDA GPU is available and properly supports torchvision NMS ops.
    Falls back cleanly to CPU if CUDA NMS is unsupported.
    """
    if torch.cuda.is_available():
        try:
            # Test torchvision NMS on CUDA to prevent runtime NotImplementedError
            import torchvision.ops as tv_ops
            boxes = torch.tensor([[0.0, 0.0, 10.0, 10.0]], device="cuda")
            scores = torch.tensor([0.9], device="cuda")
            _ = tv_ops.nms(boxes, scores, 0.5)
            return "cuda"
        except Exception:
            # Fallback to CPU if CUDA torchvision op is uncompiled
            return "cpu"
    return "cpu"

def load_yolo_model(model_path: str = None, device: str = None) -> YOLO:
    """
    Load YOLO model from the specified path or default config.
    """
    path = model_path or MODEL_PATH
    if not Path(path).exists():
        raise FileNotFoundError(f"YOLO model file not found at: {path}")
    
    target_device = device or get_device()
    print(f"[ModelLoader] Loading YOLO model from '{path}' on device '{target_device}'...")
    model = YOLO(path)
    # Ensure model is on target device
    try:
        model.to(target_device)
    except Exception:
        pass
    return model

def inspect_model_details(model_path: str = None) -> dict:
    """
    Extract task, number of classes, class IDs, and class names from model.
    """
    model = load_yolo_model(model_path)
    names = model.names  # dict of {class_id: class_name}
    task = getattr(model, "task", "detect")
    
    details = {
        "model_path": model_path or MODEL_PATH,
        "task": task,
        "num_classes": len(names),
        "names": names
    }
    return details

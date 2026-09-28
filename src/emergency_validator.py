"""
Fall Detection Validator Module.
Requires consecutive valid detections above the confidence threshold
before marking a fall as CONFIRMED.
"""
from typing import List, Dict, Any, Optional
from src.config import CONFIDENCE_THRESHOLD, REQUIRED_CONSECUTIVE_FRAMES

class FallValidator:
    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        required_consecutive_frames: int = REQUIRED_CONSECUTIVE_FRAMES
    ):
        self.confidence_threshold = confidence_threshold
        self.required_consecutive_frames = required_consecutive_frames
        self.consecutive_counter: int = 0
        self.is_fall_confirmed: bool = False
        self.last_confirmed_detection: Optional[Dict[str, Any]] = None

    def reset(self):
        """Reset validation counter and state."""
        self.consecutive_counter = 0
        self.is_fall_confirmed = False
        self.last_confirmed_detection = None

    def process_detections(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate whether detections contain a confirmed fall.
        """
        # Find best fall candidate in detections
        fall_candidate = None
        max_conf = 0.0

        for d in detections:
            if d.get("is_fall_candidate", False) and d.get("confidence", 0.0) >= self.confidence_threshold:
                if d["confidence"] > max_conf:
                    max_conf = d["confidence"]
                    fall_candidate = d

        if fall_candidate is not None:
            self.consecutive_counter += 1
            if self.consecutive_counter >= self.required_consecutive_frames:
                self.is_fall_confirmed = True
                self.last_confirmed_detection = fall_candidate
                status = "FALL_CONFIRMED"
            else:
                status = "FALL_DETECTING"
        else:
            # If not yet confirmed and fall disappears, reset counter
            if not self.is_fall_confirmed:
                self.consecutive_counter = 0
                status = "NORMAL"
            else:
                # Keep confirmed state once locked in until explicitly reset by recovery monitor
                status = "FALL_CONFIRMED"

        return {
            "status": status,
            "consecutive_counter": self.consecutive_counter,
            "required_frames": self.required_consecutive_frames,
            "is_confirmed": self.is_fall_confirmed,
            "fall_candidate": fall_candidate
        }

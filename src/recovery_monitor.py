"""
10-Second Recovery Monitor Module.
Monitors whether a fallen person gets back up within 10 seconds.
If recovered within 10s: FALL_RECOVERED (Normal fall, no ambulance needed).
If remains down for 10s: SUSPECTED_SERIOUS_MEDICAL_EMERGENCY.
"""
from typing import List, Dict, Any, Optional
import time
from src.config import RECOVERY_TIMEOUT_SECONDS

class RecoveryMonitor:
    def __init__(self, timeout_seconds: float = RECOVERY_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        self.state: str = "IDLE"  # IDLE, RECOVERY_MONITORING, FALL_RECOVERED, SUSPECTED_SERIOUS_MEDICAL_EMERGENCY
        self.start_timestamp: Optional[float] = None
        self.elapsed_seconds: float = 0.0
        self.person_posture_history: List[str] = []
        self.recovery_confirmed_counter: int = 0
        self.required_recovery_frames: int = 5  # consecutive standing frames to confirm recovery

    def reset(self):
        """Reset the recovery monitor."""
        self.state = "IDLE"
        self.start_timestamp = None
        self.elapsed_seconds = 0.0
        self.person_posture_history.clear()
        self.recovery_confirmed_counter = 0

    def start_monitoring(self, current_time: float):
        """Initialize the 10-second recovery timer."""
        self.state = "RECOVERY_MONITORING"
        self.start_timestamp = current_time
        self.elapsed_seconds = 0.0
        self.person_posture_history.clear()
        self.recovery_confirmed_counter = 0
        print(f"[RecoveryMonitor] Fall confirmed! Starting 10-second monitoring window at t={current_time:.2f}s")

    def update(self, current_time: float, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process current frame detections during recovery monitoring.
        current_time can be real time (time.time()) or video timestamp (frame_number / fps).
        """
        if self.state != "RECOVERY_MONITORING":
            return {
                "state": self.state,
                "elapsed_seconds": self.elapsed_seconds,
                "remaining_seconds": max(0.0, self.timeout_seconds - self.elapsed_seconds),
                "person_state": "IDLE",
                "emergency_triggered": self.state == "SUSPECTED_SERIOUS_MEDICAL_EMERGENCY"
            }

        if self.start_timestamp is None:
            self.start_timestamp = current_time

        self.elapsed_seconds = max(0.0, current_time - self.start_timestamp)
        remaining_seconds = max(0.0, self.timeout_seconds - self.elapsed_seconds)

        # Analyze detections for standing vs lying down
        has_standing_person = False
        has_fallen_person = False

        for d in detections:
            posture = d.get("posture", "OTHER")
            if posture == "STANDING":
                has_standing_person = True
            elif posture in ("FALL", "LYING_DOWN") or d.get("is_fall_candidate", False):
                has_fallen_person = True

        # Determine instantaneous person state
        if has_standing_person and not has_fallen_person:
            person_state = "PERSON_RECOVERED"
            self.recovery_confirmed_counter += 1
        elif has_fallen_person:
            person_state = "PERSON_STILL_DOWN"
            self.recovery_confirmed_counter = 0
        else:
            # Occlusion / no clear box detected
            # Do not assume recovery; keep monitoring
            person_state = "UNCERTAIN"

        self.person_posture_history.append(person_state)

        # Check recovery confirmation before timeout
        if self.recovery_confirmed_counter >= self.required_recovery_frames:
            self.state = "FALL_RECOVERED"
            print(f"[RecoveryMonitor] Person recovered at {self.elapsed_seconds:.2f}s! Status: FALL_RECOVERED")
            return {
                "state": self.state,
                "elapsed_seconds": round(self.elapsed_seconds, 2),
                "remaining_seconds": 0.0,
                "person_state": "PERSON_RECOVERED",
                "emergency_triggered": False
            }

        # Check if 10-second timeout has been reached
        if self.elapsed_seconds >= self.timeout_seconds:
            self.state = "SUSPECTED_SERIOUS_MEDICAL_EMERGENCY"
            print(f"[RecoveryMonitor] 10 seconds elapsed without recovery. Triggering SUSPECTED_SERIOUS_MEDICAL_EMERGENCY!")
            return {
                "state": self.state,
                "elapsed_seconds": round(self.elapsed_seconds, 2),
                "remaining_seconds": 0.0,
                "person_state": "PERSON_STILL_DOWN",
                "emergency_triggered": True
            }

        return {
            "state": self.state,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "remaining_seconds": round(remaining_seconds, 2),
            "person_state": person_state,
            "emergency_triggered": False
        }

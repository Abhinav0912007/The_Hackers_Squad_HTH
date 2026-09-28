"""
Emergency Event Processor Module.
Constructs, formats, and stores suspected emergency event payloads in-memory.

IMPORTANT MEDICAL TERMINOLOGY & DISCLAIMER:
- The system is an emergency-response prototype, NOT a medical diagnostic system.
- The YOLO model and video detection do NOT diagnose heart attacks or medical diseases.
- 10-second non-recovery after a fall serves strictly as an operational emergency trigger.
- Terminology used: 'suspected_serious_medical_emergency', 'possible_cardiac_emergency',
  'fall_with_10_second_non_recovery'.
"""
import uuid
import time
from typing import Dict, Any, Optional
from src.state_manager import state_manager

class EventProcessor:
    def __init__(self):
        pass

    def create_emergency_event(
        self,
        confidence: float,
        video_source: str,
        frame_number: int,
        location: Dict[str, Any] = None,
        trigger: str = "fall_with_10_second_non_recovery",
        notes: str = "Suspected serious medical emergency triggered after 10-second non-recovery monitoring."
    ) -> Dict[str, Any]:
        """
        Generate a validated emergency payload and update in-memory state.
        """
        event_id = str(uuid.uuid4())
        timestamp = time.time()
        
        default_location = {
            "node": "A",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "description": "Emergency Incident Point - Sector A"
        }

        event_payload = {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": "suspected_serious_medical_emergency",
            "trigger": trigger,
            "confidence": round(confidence, 4),
            "video_source": video_source,
            "frame_number": frame_number,
            "status": "ACTIVE",
            "possible_cardiac_emergency": True,
            "location": location or default_location,
            "notes": notes,
            "medical_disclaimer": "Emergency-response trigger condition only. Not a medical diagnosis."
        }

        # Save to in-memory state manager
        state_manager.set_emergency(event_payload)
        
        print(f"[EventProcessor] Created Emergency Event: {event_id}")
        print(f"[EventProcessor] Trigger: {trigger} | Confidence: {confidence:.2f}")
        return event_payload

    def get_latest_event(self) -> Optional[Dict[str, Any]]:
        return state_manager.get_latest_emergency()

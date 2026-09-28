"""
In-Memory State Manager for AI + IoT Dynamic Ambulance Corridor System.
STRICT REQUIREMENT: NO DATABASE (No SQLite, MySQL, Postgres, MongoDB, ORM).
Maintains live in-memory operational state.
"""
from typing import Dict, Any, List, Optional
import time
from threading import Lock

class StateManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StateManager, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self):
        self.lock = Lock()
        self.latest_emergency: Optional[Dict[str, Any]] = None
        self.emergency_history: List[Dict[str, Any]] = []
        
        # Fall & Recovery Detection State
        self.fall_status: str = "NORMAL"  # NORMAL, DETECTED, CONFIRMED, MONITORING, RECOVERED, EMERGENCY
        self.fall_consecutive_frames: int = 0
        self.recovery_start_time: Optional[float] = None
        self.recovery_elapsed_seconds: float = 0.0
        self.recovery_state: str = "IDLE"  # IDLE, MONITORING, PERSON_RECOVERED, PERSON_STILL_DOWN, SUSPECTED_SERIOUS_MEDICAL_EMERGENCY
        
        # Ambulance State
        self.ambulance: Dict[str, Any] = {
            "ambulance_id": "AMB_01",
            "status": "IDLE",  # IDLE, DISPATCHED, EN_ROUTE, ARRIVED
            "latitude": 21.1458,
            "longitude": 79.0882,
            "speed": 0.0,
            "direction": 0.0,
            "current_node": "A",
            "next_node": None,
            "destination": "HOSPITAL",
            "last_updated": time.time()
        }

        # Active Route State
        self.current_route: Optional[Dict[str, Any]] = None
        
        # Junctions State
        self.junctions: Dict[str, Dict[str, Any]] = {
            "J01": {
                "junction_id": "J01",
                "name": "Central Crossing - 1",
                "status": "NORMAL",  # NORMAL, PRIORITY
                "priority_direction": None,
                "current_signal": {"NS": "RED", "EW": "GREEN"},
                "latitude": 21.1465,
                "longitude": 79.0890,
                "priority_until": 0.0
            },
            "J02": {
                "junction_id": "J02",
                "name": "Main Highway Junction - 2",
                "status": "NORMAL",
                "priority_direction": None,
                "current_signal": {"NS": "GREEN", "EW": "RED"},
                "latitude": 21.1480,
                "longitude": 79.0915,
                "priority_until": 0.0
            },
            "J03": {
                "junction_id": "J03",
                "name": "Hospital Ring Junction - 3",
                "status": "NORMAL",
                "priority_direction": None,
                "current_signal": {"NS": "RED", "EW": "GREEN"},
                "latitude": 21.1510,
                "longitude": 79.0945,
                "priority_until": 0.0
            },
            "J04": {
                "junction_id": "J04",
                "name": "East Bypass Junction - 4",
                "status": "NORMAL",
                "priority_direction": None,
                "current_signal": {"NS": "GREEN", "EW": "RED"},
                "latitude": 21.1472,
                "longitude": 79.0930,
                "priority_until": 0.0
            }
        }

    def reset_state(self):
        """Reset state back to clean initial state."""
        with self.lock:
            self._init_state()

    # Emergency Event Management
    def set_emergency(self, event_data: Dict[str, Any]):
        with self.lock:
            self.latest_emergency = event_data
            self.emergency_history.append(event_data)

    def get_latest_emergency(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.latest_emergency

    # Fall & Recovery Tracking
    def update_fall_monitoring(self, status: str, consecutive_frames: int, recovery_state: str, elapsed_seconds: float):
        with self.lock:
            self.fall_status = status
            self.fall_consecutive_frames = consecutive_frames
            self.recovery_state = recovery_state
            self.recovery_elapsed_seconds = elapsed_seconds

    def get_fall_monitoring_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "fall_status": self.fall_status,
                "consecutive_frames": self.fall_consecutive_frames,
                "recovery_state": self.recovery_state,
                "recovery_elapsed_seconds": round(self.recovery_elapsed_seconds, 2)
            }

    # Ambulance Location & Status
    def update_ambulance_location(self, ambulance_id: str, latitude: float, longitude: float, speed: float,
                                  current_node: Optional[str] = None, next_node: Optional[str] = None,
                                  direction: float = 0.0, status: Optional[str] = None):
        with self.lock:
            self.ambulance["ambulance_id"] = ambulance_id
            self.ambulance["latitude"] = latitude
            self.ambulance["longitude"] = longitude
            self.ambulance["speed"] = speed
            self.ambulance["direction"] = direction
            if current_node is not None:
                self.ambulance["current_node"] = current_node
            if next_node is not None:
                self.ambulance["next_node"] = next_node
            if status is not None:
                self.ambulance["status"] = status
            self.ambulance["last_updated"] = time.time()
            return dict(self.ambulance)

    def update_ambulance_status(self, ambulance_id: str, status: str) -> Dict[str, Any]:
        with self.lock:
            self.ambulance["ambulance_id"] = ambulance_id
            self.ambulance["status"] = status
            self.ambulance["last_updated"] = time.time()
            return dict(self.ambulance)

    def get_ambulance_state(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.ambulance)

    # Route Management
    def set_active_route(self, route_data: Dict[str, Any]):
        with self.lock:
            self.current_route = route_data

    def get_active_route(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.current_route

    # Junction & Priority Corridor Management
    def get_all_junctions(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.junctions.values())

    def get_junction(self, junction_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.junctions.get(junction_id)

    def set_junction_priority(self, junction_id: str, priority: bool, duration_seconds: int = 20, direction: str = "GREEN_CORRIDOR") -> bool:
        with self.lock:
            if junction_id in self.junctions:
                if priority:
                    self.junctions[junction_id]["status"] = "PRIORITY"
                    self.junctions[junction_id]["priority_direction"] = direction
                    self.junctions[junction_id]["priority_until"] = time.time() + duration_seconds
                    # Direction of corridor gets GREEN, conflicting gets RED
                    self.junctions[junction_id]["current_signal"] = {"CORRIDOR": "GREEN", "CROSS_TRAFFIC": "RED"}
                else:
                    self.junctions[junction_id]["status"] = "NORMAL"
                    self.junctions[junction_id]["priority_direction"] = None
                    self.junctions[junction_id]["priority_until"] = 0.0
                    self.junctions[junction_id]["current_signal"] = {"NS": "GREEN", "EW": "RED"}
                return True
            return False

    def reset_all_junctions_to_normal(self):
        with self.lock:
            for j_id, j_data in self.junctions.items():
                j_data["status"] = "NORMAL"
                j_data["priority_direction"] = None
                j_data["priority_until"] = 0.0
                j_data["current_signal"] = {"NS": "GREEN", "EW": "RED"}

# Singleton instance
state_manager = StateManager()

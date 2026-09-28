"""
Comprehensive Automated Test Suite for AI + IoT Dynamic Ambulance Corridor System.
Covers:
1. YOLO model loading
2. model.names inspection
3. recorded video loading
4. fall detection
5. confidence filtering
6. consecutive-frame validation
7. 10-second timer
8. recovery detection
9. emergency event creation
10. shortest-path calculation (Dijkstra & A*)
11. ambulance movement
12. next-junction calculation
13. dynamic priority
14. MQTT command generation
15. mock hardware
"""
import sys
import os
import time
import pytest
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MODEL_PATH, CONFIDENCE_THRESHOLD, REQUIRED_CONSECUTIVE_FRAMES, RECOVERY_TIMEOUT_SECONDS
from src.model_loader import load_yolo_model, inspect_model_details
from src.detector import YOLODetector
from src.emergency_validator import FallValidator
from src.recovery_monitor import RecoveryMonitor
from src.event_processor import EventProcessor
from src.state_manager import state_manager
from src.route_engine import RoadGraph, route_engine
from src.ambulance_tracker import AmbulanceTracker, ambulance_tracker
from src.hardware_controller import MockHardwareController, MQTTHardwareController, CompositeHardwareController
from src.mqtt_client import AmbulanceMQTTClient
from tests.generate_test_video import generate_emergency_test_video

# 1. Test YOLO Model Loading
def test_01_yolo_model_loading():
    model = load_yolo_model(MODEL_PATH)
    assert model is not None, "Model failed to load"
    assert hasattr(model, "names"), "Loaded model does not contain names attribute"

# 2. Test model.names inspection
def test_02_model_names_inspection():
    details = inspect_model_details(MODEL_PATH)
    assert "names" in details
    assert isinstance(details["names"], dict)
    assert details["num_classes"] > 0
    # COCO / person check
    assert any("person" in name.lower() or "fall" in name.lower() for name in details["names"].values())

# 3. Test Recorded Video Loading (strictly no webcam)
def test_03_recorded_video_loading():
    test_video_path = generate_emergency_test_video("videos/test_emergency.mp4", duration_sec=3, fps=30)
    import cv2
    cap = cv2.VideoCapture(test_video_path)
    assert cap.isOpened(), "Could not open recorded video file"
    ret, frame = cap.read()
    assert ret is True
    assert frame is not None
    assert frame.shape[0] == 480 and frame.shape[1] == 640
    cap.release()

# 4. Test Fall / Posture Detection Logic
def test_04_fall_detection_posture():
    detector = YOLODetector(MODEL_PATH, confidence_threshold=0.25)
    # Synthetic frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = detector.detect(frame, frame_number=1)
    assert isinstance(detections, list)

# 5. Test Confidence Filtering
def test_05_confidence_filtering():
    validator = FallValidator(confidence_threshold=0.60, required_consecutive_frames=5)
    # Low confidence detection
    low_conf_det = [{
        "class_id": 0, "class_name": "person", "confidence": 0.40,
        "is_fall_candidate": True, "bbox": [100, 100, 200, 200]
    }]
    res = validator.process_detections(low_conf_det)
    assert res["status"] == "NORMAL"
    assert res["consecutive_counter"] == 0

# 6. Test Consecutive Frame Validation
def test_06_consecutive_frame_validation():
    validator = FallValidator(confidence_threshold=0.50, required_consecutive_frames=3)
    validator.reset()
    valid_det = [{
        "class_id": 0, "class_name": "person", "confidence": 0.85,
        "is_fall_candidate": True, "bbox": [100, 100, 300, 200]
    }]
    
    # Frame 1
    r1 = validator.process_detections(valid_det)
    assert r1["status"] == "FALL_DETECTING" and r1["consecutive_counter"] == 1
    
    # Frame 2
    r2 = validator.process_detections(valid_det)
    assert r2["status"] == "FALL_DETECTING" and r2["consecutive_counter"] == 2
    
    # Frame 3 (Threshold reached)
    r3 = validator.process_detections(valid_det)
    assert r3["status"] == "FALL_CONFIRMED" and r3["is_confirmed"] is True

# 7. Test 10-Second Recovery Timer Timeout
def test_07_recovery_10_second_timeout():
    monitor = RecoveryMonitor(timeout_seconds=10.0)
    monitor.reset()
    monitor.start_monitoring(current_time=0.0)
    
    # Simulate staying down at t=2, 4, 6, 8s
    down_det = [{"posture": "LYING_DOWN", "is_fall_candidate": True}]
    for t in [2.0, 4.0, 6.0, 8.0]:
        res = monitor.update(current_time=t, detections=down_det)
        assert res["state"] == "RECOVERY_MONITORING"
        assert res["emergency_triggered"] is False

    # Simulate reaching 10.0s
    final_res = monitor.update(current_time=10.0, detections=down_det)
    assert final_res["state"] == "SUSPECTED_SERIOUS_MEDICAL_EMERGENCY"
    assert final_res["emergency_triggered"] is True

# 8. Test Person Recovery Detection (< 10 seconds)
def test_08_recovery_person_stands_up():
    monitor = RecoveryMonitor(timeout_seconds=10.0)
    monitor.reset()
    monitor.start_monitoring(current_time=0.0)
    
    # Person still down for 3 seconds
    monitor.update(current_time=3.0, detections=[{"posture": "LYING_DOWN", "is_fall_candidate": True}])
    
    # Person gets up at t=4s (multiple consecutive standing detections)
    stand_det = [{"posture": "STANDING", "is_fall_candidate": False}]
    for i in range(5):
        res = monitor.update(current_time=4.0 + (i * 0.1), detections=stand_det)

    assert res["state"] == "FALL_RECOVERED"
    assert res["emergency_triggered"] is False

# 9. Test Emergency Event Creation (with proper non-diagnostic terminology)
def test_09_emergency_event_creation():
    processor = EventProcessor()
    event = processor.create_emergency_event(
        confidence=0.92,
        video_source="emergency.mp4",
        frame_number=300,
        trigger="fall_with_10_second_non_recovery"
    )
    assert "event_id" in event
    assert event["event_type"] == "suspected_serious_medical_emergency"
    assert event["possible_cardiac_emergency"] is True
    # Ensure no confirmed heart attack claim
    assert "heart_attack_confirmed" not in event
    assert "medical_disclaimer" in event

# 10. Test Shortest Path Calculation (Dijkstra vs A*)
def test_10_shortest_path_dijkstra_and_astar():
    graph = RoadGraph()
    astar_res = graph.find_shortest_path_astar("A", "HOSPITAL")
    dijkstra_res = graph.find_shortest_path_dijkstra("A", "HOSPITAL")
    
    assert astar_res["route"][0] == "A"
    assert astar_res["route"][-1] == "HOSPITAL"
    assert dijkstra_res["route"] == astar_res["route"]
    assert astar_res["distance"] > 0
    assert astar_res["estimated_time"] > 0

# 11. Test Ambulance Movement Simulation
def test_11_ambulance_movement_simulation():
    tracker = AmbulanceTracker("AMB_TEST")
    route = tracker.dispatch("A", "HOSPITAL")
    assert tracker.status == "DISPATCHED"
    assert tracker.current_step_index == 0
    
    # Step forward
    state = tracker.step()
    assert tracker.status == "EN_ROUTE"
    assert tracker.current_step_index == 1

# 12. Test Upcoming Junction Identification
def test_12_upcoming_junction_calculation():
    tracker = AmbulanceTracker("AMB_TEST")
    tracker.dispatch("A", "HOSPITAL")
    next_junc = tracker.get_upcoming_junction()
    assert next_junc in ["J01", "J02", "J03", "J04"]

# 13. Test Dynamic Corridor Priority Hand-off
def test_13_dynamic_corridor_priority():
    tracker = AmbulanceTracker("AMB_TEST")
    tracker.dispatch("A", "HOSPITAL")
    initial_priority = tracker.active_priority_junction
    assert initial_priority is not None
    
    # Verify state manager has priority for that junction
    junc_data = state_manager.get_junction(initial_priority)
    assert junc_data["status"] == "PRIORITY"

    # Simulate until arrival
    tracker.simulate_full_run(delay_seconds=0.01)
    assert tracker.status == "ARRIVED"
    
    # All signals must be restored to NORMAL upon arrival
    for j in state_manager.get_all_junctions():
        assert j["status"] == "NORMAL"

# 14. Test MQTT Message Formatting & Publishing
def test_14_mqtt_formatting():
    client = AmbulanceMQTTClient()
    assert client.broker is not None
    assert client.port == 1883
    # Verify publishing does not crash even when offline
    client.publish_ambulance_location("AMB_01", 21.1458, 79.0882, 45.0, "J01")
    client.publish_junction_command("J01", "PRIORITY", "AMB_01", 20)
    client.publish_junction_command("J01", "NORMAL")

# 15. Test Mock Hardware Controller
def test_15_mock_hardware_controller():
    mock_hw = MockHardwareController()
    mock_hw.set_priority("J01", "AMB_01", 20)
    assert state_manager.get_junction("J01")["status"] == "PRIORITY"
    
    mock_hw.set_normal("J01")
    assert state_manager.get_junction("J01")["status"] == "NORMAL"
    
    mock_hw.reset_all()
    for j in state_manager.get_all_junctions():
        assert j["status"] == "NORMAL"

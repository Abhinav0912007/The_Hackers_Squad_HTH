"""
Test FastAPI API Endpoints.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from api.main import app
from src.state_manager import state_manager

client = TestClient(app)

def setup_function():
    state_manager.reset_state()

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"

def test_api_emergency_create_and_latest():
    payload = {
        "video_source": "videos/emergency.mp4",
        "confidence": 0.94,
        "frame_number": 250,
        "trigger": "fall_with_10_second_non_recovery",
        "location_node": "A"
    }
    response = client.post("/api/emergency", json=payload)
    assert response.status_code == 200
    event = response.json()
    assert event["event_type"] == "suspected_serious_medical_emergency"
    assert event["confidence"] == 0.94
    assert event["status"] == "ACTIVE"

    # Fetch latest
    latest_resp = client.get("/api/emergency/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.json()["event_id"] == event["event_id"]

def test_api_ambulance_status_and_location():
    status_resp = client.get("/api/ambulance/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["ambulance_id"] == "AMB_01"

    loc_payload = {
        "ambulance_id": "AMB_01",
        "latitude": 21.1465,
        "longitude": 79.0910,
        "speed": 52.0,
        "current_node": "B",
        "next_node": "E",
        "status": "EN_ROUTE"
    }
    update_resp = client.post("/api/ambulance/location", json=loc_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["current_node"] == "B"
    assert update_resp.json()["speed"] == 52.0

def test_api_route_calculation():
    resp = client.get("/api/route?start=A&destination=HOSPITAL&algorithm=astar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["start"] == "A"
    assert data["destination"] == "HOSPITAL"
    assert len(data["route"]) >= 3
    assert data["distance"] > 0

def test_api_junctions_and_priority():
    juncs_resp = client.get("/api/junctions")
    assert juncs_resp.status_code == 200
    assert len(juncs_resp.json()) >= 4

    priority_resp = client.post("/api/junction/J01/priority", json={"priority": True, "duration_seconds": 25})
    assert priority_resp.status_code == 200
    assert priority_resp.json()["junction"]["status"] == "PRIORITY"

    reset_resp = client.post("/api/junctions/reset")
    assert reset_resp.status_code == 200

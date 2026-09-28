"""
Pydantic Schemas for FastAPI Endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class EmergencyCreateRequest(BaseModel):
    video_source: str = Field(default="videos/emergency.mp4", description="Source video file path")
    confidence: float = Field(default=0.91, ge=0.0, le=1.0, description="Detection confidence")
    frame_number: int = Field(default=150, ge=0, description="Video frame number of detection")
    trigger: str = Field(default="fall_with_10_second_non_recovery", description="Trigger mechanism")
    location_node: Optional[str] = Field(default="A", description="Starting node/incident point")

class EmergencyResponse(BaseModel):
    event_id: str
    timestamp: float
    event_type: str
    trigger: str
    confidence: float
    video_source: str
    frame_number: int
    status: str
    possible_cardiac_emergency: bool
    location: Dict[str, Any]
    notes: Optional[str] = None
    medical_disclaimer: str

class AmbulanceLocationUpdateRequest(BaseModel):
    ambulance_id: str = "AMB_01"
    latitude: float
    longitude: float
    speed: float = 45.0
    direction: float = 0.0
    current_node: Optional[str] = None
    next_node: Optional[str] = None
    status: Optional[str] = None

class AmbulanceStatusResponse(BaseModel):
    ambulance_id: str
    status: str
    latitude: float
    longitude: float
    speed: float
    direction: float
    current_node: Optional[str]
    next_node: Optional[str]
    destination: str
    last_updated: float

class RouteCalculationRequest(BaseModel):
    start_node: str = "A"
    destination_node: str = "HOSPITAL"
    algorithm: str = "astar"  # astar or dijkstra

class RouteResponse(BaseModel):
    ambulance_id: str
    start: str
    destination: str
    route: List[str]
    waypoints: List[Dict[str, Any]]
    distance: float
    estimated_time: int

class JunctionPriorityRequest(BaseModel):
    priority: bool = True
    ambulance_id: str = "AMB_01"
    duration_seconds: int = 20

class JunctionResponse(BaseModel):
    junction_id: str
    name: str
    status: str
    priority_direction: Optional[str]
    current_signal: Dict[str, str]
    latitude: float
    longitude: float
    priority_until: float

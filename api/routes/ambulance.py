"""
Ambulance & Route API Routes.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from api.schemas import AmbulanceLocationUpdateRequest, AmbulanceStatusResponse, RouteResponse
from src.state_manager import state_manager
from src.route_engine import route_engine
from src.ambulance_tracker import ambulance_tracker

router = APIRouter(prefix="/api", tags=["Ambulance & Route"])

@router.post("/ambulance/location", response_model=AmbulanceStatusResponse)
def update_ambulance_location(req: AmbulanceLocationUpdateRequest):
    """
    Update the ambulance GPS location and status in memory.
    """
    state = state_manager.update_ambulance_location(
        ambulance_id=req.ambulance_id,
        latitude=req.latitude,
        longitude=req.longitude,
        speed=req.speed,
        direction=req.direction,
        current_node=req.current_node,
        next_node=req.next_node,
        status=req.status
    )
    return state

@router.get("/ambulance/status", response_model=AmbulanceStatusResponse)
def get_ambulance_status():
    """
    Get live status, current position, speed, and upcoming node of the ambulance.
    """
    return state_manager.get_ambulance_state()

@router.post("/ambulance/dispatch")
def dispatch_ambulance(start_node: str = "A", destination_node: str = "HOSPITAL"):
    """
    Trigger ambulance dispatch and calculate the dynamic green corridor.
    """
    route_result = ambulance_tracker.dispatch(start_node=start_node, destination_node=destination_node)
    return {
        "status": "DISPATCHED",
        "route_details": route_result
    }

@router.post("/ambulance/step")
def step_ambulance_simulation():
    """
    Advance simulated ambulance one step forward along the route.
    """
    state = ambulance_tracker.step()
    return {
        "message": "Ambulance advanced",
        "state": state
    }

@router.get("/route", response_model=RouteResponse)
def get_calculated_route(
    start: str = Query("A", description="Starting intersection node"),
    destination: str = Query("HOSPITAL", description="Destination hospital node"),
    algorithm: str = Query("astar", description="Algorithm: 'astar' or 'dijkstra'")
):
    """
    Calculate and return the shortest route using Dijkstra or A* graph algorithm.
    """
    try:
        if algorithm.lower() == "dijkstra":
            route_res = route_engine.find_shortest_path_dijkstra(start, destination)
        else:
            route_res = route_engine.find_shortest_path_astar(start, destination)
        return route_res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

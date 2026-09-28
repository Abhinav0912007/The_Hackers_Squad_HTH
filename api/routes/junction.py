"""
Junction and Traffic Signal Corridor Routes.
"""
from fastapi import APIRouter, HTTPException, Path
from typing import List, Dict, Any
from api.schemas import JunctionResponse, JunctionPriorityRequest
from src.state_manager import state_manager
from src.hardware_controller import hardware_controller

router = APIRouter(prefix="/api", tags=["Junctions & Traffic Priority"])

@router.get("/junctions", response_model=List[JunctionResponse])
def get_all_junctions():
    """
    Get live status and signal states for all traffic junctions.
    """
    return state_manager.get_all_junctions()

@router.get("/junction/{junction_id}", response_model=JunctionResponse)
def get_single_junction(junction_id: str = Path(..., description="Junction Identifier e.g. J01, J02")):
    """
    Get current signal status for a specific junction.
    """
    junction = state_manager.get_junction(junction_id)
    if not junction:
        raise HTTPException(status_code=404, detail=f"Junction '{junction_id}' not found.")
    return junction

@router.post("/junction/{junction_id}/priority")
def set_junction_priority(
    junction_id: str = Path(..., description="Junction Identifier e.g. J01, J02"),
    req: JunctionPriorityRequest = None
):
    """
    Manually or automatically set green priority for an upcoming junction.
    """
    priority = req.priority if req else True
    duration = req.duration_seconds if req else 20
    ambulance_id = req.ambulance_id if req else "AMB_01"

    if priority:
        hardware_controller.set_priority(junction_id, ambulance_id=ambulance_id, duration=duration)
    else:
        hardware_controller.set_normal(junction_id)

    updated = state_manager.get_junction(junction_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Junction '{junction_id}' not found.")

    return {
        "message": f"Junction {junction_id} priority set to {priority}",
        "junction": updated
    }

@router.post("/junctions/reset")
def reset_all_junctions():
    """
    Reset all junctions back to standard NORMAL operation.
    """
    hardware_controller.reset_all()
    return {
        "message": "All junctions reset to NORMAL signal cycle.",
        "junctions": state_manager.get_all_junctions()
    }

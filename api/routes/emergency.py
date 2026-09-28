"""
Emergency & Video Processing API Routes.
"""
import shutil
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any, Optional

from api.schemas import EmergencyCreateRequest, EmergencyResponse
from src.event_processor import EventProcessor
from src.state_manager import state_manager
from src.ambulance_tracker import ambulance_tracker
from src.video_inference import process_video
from src.config import VIDEO_DIR, OUTPUT_DIR

router = APIRouter(prefix="/api", tags=["Emergency & Video Processing"])
event_processor = EventProcessor()

@router.post("/emergency", response_model=EmergencyResponse)
def create_emergency_event(req: EmergencyCreateRequest):
    """
    Trigger a suspected medical emergency from video detection event.
    Automatically assigns and dispatches the ambulance on the shortest route.
    """
    event = event_processor.create_emergency_event(
        confidence=req.confidence,
        video_source=req.video_source,
        frame_number=req.frame_number,
        trigger=req.trigger,
        location={"node": req.location_node, "latitude": 21.1458, "longitude": 79.0882}
    )
    
    # Trigger ambulance dispatch automatically on confirmed emergency
    ambulance_tracker.dispatch(start_node=req.location_node, destination_node="HOSPITAL")
    
    return event

@router.get("/emergency/latest")
def get_latest_emergency():
    """
    Fetch the latest registered emergency event.
    """
    latest = state_manager.get_latest_emergency()
    if latest is None:
        return {
            "status": "NO_ACTIVE_EMERGENCY",
            "message": "No emergency event has been triggered yet."
        }
    return latest

@router.get("/emergency/fall-status")
def get_fall_monitoring_status():
    """
    Fetch current live fall detection & 10s recovery monitoring status.
    """
    return state_manager.get_fall_monitoring_status()

@router.post("/video/upload")
async def upload_and_process_video(file: UploadFile = File(...)):
    """
    Upload a recorded video file (.mp4, .avi, .mov), run YOLO fall detection & 10s recovery monitoring,
    and trigger the dynamic ambulance corridor if an emergency is detected.
    STRICTLY PROCESSES RECORDED VIDEO (NO WEBCAM).
    """
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Invalid video format. Supported formats: .mp4, .avi, .mov, .mkv")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Sanitize and save video
    safe_filename = file.filename.replace(" ", "_")
    input_path = VIDEO_DIR / safe_filename
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    output_filename = f"annotated_{safe_filename}"
    output_path = str(OUTPUT_DIR / output_filename)

    try:
        # Run inference pipeline
        result = process_video(
            video_source=str(input_path),
            output_path=output_path,
            show_window=False
        )

        return {
            "status": "SUCCESS",
            "message": "Video processed successfully.",
            "input_filename": safe_filename,
            "output_video_url": f"/outputs/{output_filename}",
            "total_frames_processed": result["total_frames_processed"],
            "processing_time_seconds": result["processing_time_seconds"],
            "fall_confirmed": result["fall_confirmed"],
            "recovery_state": result["recovery_state"],
            "emergency_triggered": result["emergency_triggered"],
            "emergency_event": result["emergency_event"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

"""
FastAPI Server Entrypoint for AI + IoT Dynamic Ambulance Corridor System.
Provides REST APIs for Emergency Events, Ambulance GPS Tracking, Shortest Route Calculation,
Traffic Signal Green Corridor Control, and serves the Web Frontend Dashboard.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes.emergency import router as emergency_router
from api.routes.ambulance import router as ambulance_router
from api.routes.junction import router as junction_router
from src.mqtt_client import mqtt_client
from src.config import BASE_DIR, API_HOST, API_PORT

app = FastAPI(
    title="AI + IoT Dynamic Ambulance Corridor System",
    description="Emergency Response & Dynamic Traffic Green Corridor Control System",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(emergency_router)
app.include_router(ambulance_router)
app.include_router(junction_router)

# Mount Frontend Static Assets
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Mount Outputs Directory for Video Playback
outputs_dir = BASE_DIR / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

@app.on_event("startup")
def startup_event():
    # Attempt MQTT non-blocking background connection
    mqtt_client.connect_async()
    print("[FastAPI] Server started. In-memory state ready. MQTT client initialized.")

@app.get("/")
def serve_dashboard():
    index_file = BASE_DIR / "frontend" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "system": "AI + IoT Dynamic Ambulance Corridor System",
        "status": "OPERATIONAL",
        "message": "Frontend dashboard loaded."
    }

@app.get("/api/info")
def system_info():
    return {
        "system": "AI + IoT Dynamic Ambulance Corridor System",
        "status": "OPERATIONAL",
        "endpoints": {
            "emergency_create": "POST /api/emergency",
            "emergency_latest": "GET /api/emergency/latest",
            "ambulance_location": "POST /api/ambulance/location",
            "ambulance_status": "GET /api/ambulance/status",
            "route_calculation": "GET /api/route",
            "junctions_list": "GET /api/junctions",
            "junction_priority": "POST /api/junction/{junction_id}/priority"
        },
        "disclaimer": "Emergency-response trigger prototype only. Not a medical diagnostic tool."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)

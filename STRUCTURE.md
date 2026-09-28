# AI + IoT Dynamic Ambulance Corridor System — Architecture & Structure

This document provides a detailed breakdown of the file structure, module responsibilities, data flow, API architecture, and hardware-software integration specifications for the project.

---

## 1. Directory Tree

```
Ambulance_IOT/
│
├── .env                              # Active environment configuration (MQTT, ports, thresholds)
├── .env.example                      # Template environment variables
├── requirements.txt                  # Python dependencies (No DB/ORM packages)
├── README.md                         # Main project documentation & execution guide
├── STRUCTURE.md                      # Detailed architecture and project breakdown
│
├── models/
│   └── yolo8vs.pt                    # Ultralytics YOLOv8 weights (COCO format, class 0: person)
│
├── videos/
│   ├── test_emergency.mp4            # Generated synthetic test video
│   └── emergency.mp4                 # User-provided recorded video file (NO LIVE CAMERA)
│
├── outputs/
│   └── annotated_test_emergency.mp4  # Output video with bounding boxes & HUD overlay
│
├── src/                              # Core AI, Routing, IoT, and State Logic
│   ├── __init__.py
│   ├── config.py                     # Centralized settings & environment loader
│   ├── model_loader.py               # Safe model loader (automatic CUDA/CPU fallback)
│   ├── inspect_model.py              # CLI tool to inspect model.names without assumptions
│   ├── detector.py                   # YOLO inference & posture aspect ratio analyzer
│   ├── emergency_validator.py        # 5-consecutive frame fall validator (threshold >= 0.50)
│   ├── recovery_monitor.py           # 10-second non-recovery timer & state tracker
│   ├── event_processor.py            # Generates structured emergency payloads
│   ├── state_manager.py              # In-memory operational state store (STRICTLY NO DB)
│   ├── route_engine.py               # Road network graph, Dijkstra & A* routing algorithms
│   ├── ambulance_tracker.py          # GPS telemetry simulation & priority corridor shifter
│   ├── mqtt_client.py                # Non-blocking Paho MQTT client (pub/sub)
│   ├── hardware_controller.py        # Console Mock & MQTT hardware abstractions
│   └── main.py                       # Unified CLI runner (simulate, video, api, inspect)
│
├── api/                              # FastAPI REST Backend & Web Services
│   ├── __init__.py
│   ├── main.py                       # FastAPI entrypoint & frontend static mount
│   ├── schemas.py                    # Pydantic data validation schemas
│   └── routes/
│       ├── __init__.py
│       ├── emergency.py              # POST/GET emergency event routes
│       ├── ambulance.py              # GPS location, status, and route calculation routes
│       └── junction.py               # Traffic signal status & green corridor priority routes
│
├── frontend/                         # Modern Dark-Themed Web Dashboard
│   ├── index.html                    # Dashboard layout & canvas containers
│   ├── styles.css                    # Glassmorphic dark styling & neon corridor animations
│   └── app.js                        # Interactive graph visualizer, 10s gauge, & REST polling
│
├── hardware/
│   └── esp32/
│       └── esp32_corridor_controller.ino # ESP32 Arduino C++ firmware with WiFi & MQTT
│
└── tests/                            # Automated Testing Suite
    ├── generate_test_video.py        # Script to generate synthetic test videos
    ├── test_all_modules.py           # 15 unit tests covering AI, Validator, Router, and MQTT
    └── test_api_endpoints.py         # 5 integration tests for FastAPI endpoints
```

---

## 2. Module Responsibilities & Component Descriptions

| Module | Location | Primary Purpose |
|---|---|---|
| **`config.py`** | [src/config.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/config.py) | Central repository for paths, thresholds (`CONFIDENCE_THRESHOLD=0.50`, `REQUIRED_CONSECUTIVE_FRAMES=5`, `RECOVERY_TIMEOUT_SECONDS=10.0`), and MQTT/API network parameters. |
| **`model_loader.py`** | [src/model_loader.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/model_loader.py) | Loads YOLO weights with automatic hardware verification (detects CUDA vs CPU and tests torchvision NMS ops to avoid Windows DLL issues). |
| **`inspect_model.py`** | [src/inspect_model.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/inspect_model.py) | Reads and prints `model.names` directly from the `.pt` file as the single source of truth. |
| **`detector.py`** | [src/detector.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/detector.py) | Runs YOLO on video frames. Computes bounding box aspect ratios ($W/H$) to detect horizontal/fallen vs upright postures. |
| **`emergency_validator.py`** | [src/emergency_validator.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/emergency_validator.py) | Requires $\ge 5$ consecutive frames of fall detection before transitioning state to `FALL_CONFIRMED`. |
| **`recovery_monitor.py`** | [src/recovery_monitor.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/recovery_monitor.py) | Manages the 10.0-second timer. If the person recovers before 10s $\rightarrow$ `FALL_RECOVERED`. If they stay down for 10s $\rightarrow$ `SUSPECTED_SERIOUS_MEDICAL_EMERGENCY`. |
| **`event_processor.py`** | [src/event_processor.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/event_processor.py) | Builds unique UUID emergency events with medical disclaimers and coordinates. |
| **`state_manager.py`** | [src/state_manager.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/state_manager.py) | Thread-safe in-memory singleton storing active emergencies, vehicle telemetry, active routes, and junction signal states. **No database used.** |
| **`route_engine.py`** | [src/route_engine.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/route_engine.py) | Graph-based road network representing intersections and roads. Computes optimal shortest routes via **A\*** (Haversine heuristic) and **Dijkstra**. |
| **`ambulance_tracker.py`** | [src/ambulance_tracker.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/ambulance_tracker.py) | Simulates GPS waypoint movement, identifies upcoming junctions, shifts green corridor priority, and restores passed junctions to NORMAL. |
| **`hardware_controller.py`**| [src/hardware_controller.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/hardware_controller.py) | Hardware abstraction layer exposing `MockHardwareController` (console logs) and `MQTTHardwareController` (ESP32 commands). |
| **`mqtt_client.py`** | [src/mqtt_client.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/mqtt_client.py) | Asynchronous MQTT publisher for telemetry (`ambulance/AMB_01/location`) and traffic commands (`junction/{id}/command`). |
| **`video_inference.py`** | [src/video_inference.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/video_inference.py) | Processes recorded `.mp4` video files using OpenCV. Draws bounding boxes, telemetry HUD, and countdown bars. Strictly rejects live webcams. |
| **`esp32_corridor_controller.ino`** | [hardware/esp32/esp32_corridor_controller.ino](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/hardware/esp32/esp32_corridor_controller.ino) | Arduino C++ firmware for ESP32 with WiFi & MQTT to control physical 6-LED traffic light modules. |

---

## 3. End-to-End Data & Execution Flow

```
1. RECORDED VIDEO INPUT (videos/emergency.mp4)
         │
         ▼
2. YOLOv8 INFERENCE (src/detector.py)
         │ Extract class_name, confidence, bbox, aspect ratio
         ▼
3. FALL VALIDATION (src/emergency_validator.py)
         │ Consecutive frame counter reaches 5 frames
         ▼
4. 10-SECOND RECOVERY WINDOW (src/recovery_monitor.py)
         ├─────────────────────────────────────────┐
         │ (Person stands up < 10s)                │ (Person remains down >= 10s)
         ▼                                         ▼
   FALL_RECOVERED                          SUSPECTED_SERIOUS_MEDICAL_EMERGENCY
   (Normal fall, no dispatch)                      │
                                                   ▼
5. EMERGENCY EVENT GENERATION (src/event_processor.py)
         │ Store in In-Memory StateManager (src/state_manager.py)
         ▼
6. SHORTEST PATH ROUTING (src/route_engine.py)
         │ A* Graph Search: A -> B (J01) -> E (J04) -> G (J03) -> HOSPITAL
         ▼
7. AMBULANCE DISPATCH & GPS SIMULATION (src/ambulance_tracker.py)
         │
         ├── At Node A ────────► Upcoming J01: PRIORITY (Green Corridor)
         ├── Reaches Node B ───► J01: NORMAL, Upcoming J04: PRIORITY
         ├── Reaches Node E ───► J04: NORMAL, Upcoming J03: PRIORITY
         └── Reaches HOSPITAL ─► All signals reset to NORMAL, Status = ARRIVED
         │
         ▼
8. IoT HARDWARE ACTUATION (src/mqtt_client.py & ESP32)
         │ MQTT Topics: junction/J01/command, ambulance/AMB_01/location
         ▼
9. PHYSICAL LED SWITCHING (hardware/esp32/esp32_corridor_controller.ino)
         │ Corridor LEDs: GREEN, Cross Traffic LEDs: RED
```

---

## 4. API Endpoints Reference

| Method | Route | Schema / Parameters | Description |
|---|---|---|---|
| `GET` | `/` | HTML | Serves the interactive web frontend dashboard. |
| `POST` | `/api/emergency` | `EmergencyCreateRequest` | Triggers emergency event and auto-dispatches ambulance. |
| `GET` | `/api/emergency/latest` | — | Returns latest active emergency event. |
| `GET` | `/api/emergency/fall-status` | — | Returns current fall detection and 10s timer state. |
| `POST` | `/api/ambulance/location` | `AmbulanceLocationUpdateRequest` | Updates GPS location and telemetry. |
| `GET` | `/api/ambulance/status` | — | Returns ambulance position, status, and upcoming node. |
| `POST` | `/api/ambulance/dispatch` | `start_node`, `destination_node` | Dispatches ambulance on shortest path. |
| `POST` | `/api/ambulance/step` | — | Advances ambulance simulation one waypoint forward. |
| `GET` | `/api/route` | `start`, `destination`, `algorithm` | Computes shortest path via A* or Dijkstra. |
| `GET` | `/api/junctions` | — | Returns live status and signal states for all junctions. |
| `POST` | `/api/junction/{id}/priority`| `JunctionPriorityRequest` | Sets dynamic green corridor priority for a junction. |
| `POST` | `/api/junctions/reset` | — | Resets all traffic signals to NORMAL cycle. |

---

## 5. MQTT Topic & Message Schema

### 1. Ambulance GPS Telemetry Topic: `ambulance/AMB_01/location`
```json
{
  "ambulance_id": "AMB_01",
  "latitude": 21.1465,
  "longitude": 79.0910,
  "speed": 52.0,
  "next_junction": "J01",
  "timestamp": 1774782000.0
}
```

### 2. Junction Priority Command Topic: `junction/J01/command`
```json
{
  "command": "PRIORITY",
  "ambulance_id": "AMB_01",
  "duration": 20,
  "timestamp": 1774782000.0
}
```

### 3. Junction Normal Restore Topic: `junction/J01/command`
```json
{
  "command": "NORMAL",
  "timestamp": 1774782020.0
}
```

---

## 6. ESP32 Hardware Pin Mapping

```
ESP32 DevKit V1
┌───────────────────────────────┐
│ GPIO 23 ───► Corridor RED LED │
│ GPIO 22 ───► Corridor YEL LED │
│ GPIO 21 ───► Corridor GRN LED │
│                               │
│ GPIO 19 ───► Cross RED LED    │
│ GPIO 18 ───► Cross YEL LED    │
│ GPIO 5  ───► Cross GRN LED    │
│ GND     ───► Common Ground    │
└───────────────────────────────┘
```

# AI + IoT Based Dynamic Ambulance Corridor System

An intelligent emergency response and dynamic traffic corridor automation system. The system processes **recorded video footage**, detects human falls, monitors the person for a **10-second non-recovery window**, and triggers an automated ambulance dispatch with **graph-based shortest path calculation** (A* / Dijkstra) and **dynamic green wave traffic signal control** via MQTT and ESP32 IoT nodes.

> [!IMPORTANT]
> **MEDICAL DISCLAIMER & TERMINOLOGY NOTICE:**
> The system is an automated emergency-response prototype, **NOT a medical diagnostic system**.
> A fall followed by 10 seconds of remaining on the ground is solely an **operational emergency trigger condition**.
> The system does **NOT** diagnose heart attacks or medical conditions.
> Approved terminology used:
> - *"Fall detected"*
> - *"Person remained down for 10 seconds"*
> - *"Suspected serious medical emergency"*
> - *"Suspected cardiac emergency / Possible cardiac emergency"*
> - *"Emergency response triggered"*

---

## 1. System Architecture

```
RECORDED VIDEO (.mp4)
       │
       ▼
YOLO OBJECT DETECTION (models/yolo8vs.pt)
       │
       ▼
FALL VALIDATION (>= 5 Consecutive Frames @ Conf >= 0.50)
       │
       ▼
10-SECOND RECOVERY MONITOR
       │
   ┌───┴────────────────────────┐
   │ (Person stands up < 10s)   │ (Person still down @ 10s)
   ▼                            ▼
FALL_RECOVERED            SUSPECTED SERIOUS MEDICAL EMERGENCY
(No dispatch needed)            │
                                ▼
                       FASTAPI BACKEND SERVER (In-Memory State)
                                │
                       AMBULANCE DISPATCH (AMB_01)
                                │
                       SHORTEST PATH (A* / Dijkstra Graph Algorithm)
                                │
                       GPS & TELEMETRY SIMULATION
                                │
                       UPCOMING JUNCTION DETECTION
                                │
                       MQTT BROKER (Topics: junction/{id}/command)
                                │
                       ESP32 IoT TRAFFIC CONTROLLERS
                                │
                       DYNAMIC GREEN CORRIDOR (Corridor: GREEN, Cross: RED)
                                │
                       HOSPITAL ARRIVAL -> ALL SIGNALS NORMAL
```

---

## 2. Key Highlights & Constraints Adherence

- **Strictly Recorded Video Only**: Strictly operates on recorded `.mp4` video files via `cv2.VideoCapture(video_path)`. **NO webcam, NO live camera, and NO `cv2.VideoCapture(0)`**.
- **No Database**: Pure in-memory operational state via [state_manager.py](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/src/state_manager.py). No SQLite, MySQL, Postgres, MongoDB, or ORMs.
- **Model Truth Inspection**: Inspects `model.names` directly from `models/yolo8vs.pt` to detect available classes (`person` at ID 0 / custom `fall`).
- **Dynamic Shortest Path**: Graph-based road network computing optimal routes using **A\*** (with Haversine heuristic) and **Dijkstra** algorithms. Never hard-codes routes.
- **Dynamic Green Wave**: Only the immediate upcoming junction ahead of the ambulance is granted `PRIORITY` (Green Corridor). Passed junctions immediately return to `NORMAL`. Upon hospital arrival, all signals reset.
- **Hardware Abstraction & ESP32 Firmware**: Dual support for console simulation (`MockHardwareController`) and live IoT communication (`MQTTHardwareController` & ESP32 Arduino firmware).

---

## 3. Project Structure

```
ambulance-ai/
│
├── models/
│   └── yolo8vs.pt                  # YOLOv8 weights
│
├── videos/
│   ├── test_emergency.mp4          # Synthetic test video
│   └── emergency.mp4               # User recorded input video
│
├── outputs/
│   └── annotated_output.mp4        # Rendered output video with HUD
│
├── src/
│   ├── config.py                   # Centralized configuration & environment loader
│   ├── model_loader.py             # CUDA/CPU-safe YOLO model loader
│   ├── inspect_model.py            # Model.names inspector
│   ├── detector.py                 # Frame inference & posture analyzer
│   ├── emergency_validator.py      # Consecutive frame fall validator
│   ├── recovery_monitor.py         # 10-second non-recovery timer & state tracker
│   ├── event_processor.py          # Emergency payload builder
│   ├── state_manager.py            # In-memory state store (NO DATABASE)
│   ├── route_engine.py             # Graph network, A* & Dijkstra routing
│   ├── ambulance_tracker.py        # GPS telemetry & green corridor shifter
│   ├── mqtt_client.py              # MQTT publisher & subscriber
│   ├── hardware_controller.py      # Mock & MQTT hardware abstraction
│   └── main.py                     # CLI entrypoint for simulation & video
│
├── api/
│   ├── main.py                     # FastAPI application entrypoint
│   ├── schemas.py                  # Pydantic request/response schemas
│   └── routes/
│       ├── emergency.py            # Emergency trigger & status endpoints
│       ├── ambulance.py            # Ambulance dispatch & location endpoints
│       └── junction.py             # Traffic junction priority & signal endpoints
│
├── hardware/
│   └── esp32/
│       └── esp32_corridor_controller.ino  # ESP32 C++ Arduino firmware
│
├── tests/
│   ├── generate_test_video.py      # Synthetic test video generator
│   ├── test_all_modules.py         # 15 unit tests covering all core modules
│   └── test_api_endpoints.py       # Integration tests for FastAPI routes
│
├── .env                            # Active environment variables
├── .env.example                    # Example configuration template
├── requirements.txt                # Python dependencies
└── README.md                       # Documentation
```

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Windows / Linux / macOS compatible
- (Optional) Local MQTT broker such as Mosquitto

### Step 1: Clone or Navigate to Directory
```bash
cd c:\Users\Dell\OneDrive\Desktop\Ambulance_IOT
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 5. Execution Commands

### 1. Inspect YOLO Model Classes
Inspects `model.names` as the single source of truth without assumptions:
```bash
python src/inspect_model.py
```

### 2. Run Video Fall Detection & Corridor Trigger
Processes a recorded video file, renders bounding boxes and real-time HUD dashboard, and saves the annotated video to `outputs/`:
```bash
python src/video_inference.py --source videos/test_emergency.mp4
```
*(You can pass any user-provided recorded video: `--source videos/emergency.mp4`)*

### 3. Run End-to-End Simulation in CLI
Runs graph route computation, ambulance GPS tracking, and dynamic junction priority hand-off:
```bash
python src/main.py --mode simulate
```

### 4. Start the FastAPI Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger API documentation is available at:
`http://localhost:8000/docs`

### 5. Run Complete Automated Test Suite
Runs all 20 unit and API integration tests:
```bash
pytest tests/ -v
```

---

## 6. REST API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/emergency` | Trigger suspected emergency event and auto-dispatch ambulance |
| `GET` | `/api/emergency/latest` | Fetch latest active emergency event |
| `GET` | `/api/emergency/fall-status` | Get real-time fall detection and 10s timer status |
| `POST` | `/api/ambulance/location` | Update ambulance GPS telemetry |
| `GET` | `/api/ambulance/status` | Get current ambulance position, status, and upcoming node |
| `POST` | `/api/ambulance/dispatch` | Manually dispatch ambulance (`start_node` -> `destination_node`) |
| `POST` | `/api/ambulance/step` | Advance ambulance simulation by one waypoint |
| `GET` | `/api/route` | Compute shortest route via A* or Dijkstra (`?start=A&destination=HOSPITAL`) |
| `GET` | `/api/junctions` | List all traffic junctions and signal states |
| `GET` | `/api/junction/{junction_id}` | Get status of a specific junction |
| `POST` | `/api/junction/{junction_id}/priority` | Set dynamic green corridor priority for a junction |
| `POST` | `/api/junctions/reset` | Reset all traffic signals to NORMAL cycle |

---

## 7. Shortest Path & Dynamic Corridor Logic

### Road Network Graph
```
A ---- B ---- C
|      |      |
D ---- E ---- F
       |
       G
       |
    HOSPITAL
```

- **Nodes**: Intersections ($A, B, C, D, E, F, G$) and $HOSPITAL$.
- **Algorithm**: **A\*** (with Haversine distance heuristic) & **Dijkstra**.
- **Dynamic Green Wave Hand-off**:
  1. Ambulance at $A \rightarrow$ Next junction $J01 (B)$ gets **PRIORITY** (Green).
  2. Ambulance passes $J01 \rightarrow J01$ returns to **NORMAL**, $J04 (E)$ gets **PRIORITY**.
  3. Ambulance passes $J04 \rightarrow J04$ returns to **NORMAL**, $J03 (G)$ gets **PRIORITY**.
  4. Ambulance reaches $HOSPITAL \rightarrow$ All junctions return to **NORMAL**.

---

## 8. MQTT & ESP32 IoT Integration

### MQTT Topics
- **Ambulance Telemetry**: `ambulance/AMB_01/location`
  ```json
  {
    "ambulance_id": "AMB_01",
    "latitude": 21.1458,
    "longitude": 79.0882,
    "speed": 45.0,
    "next_junction": "J01",
    "timestamp": 1774780000.0
  }
  ```
- **Junction Priority Command**: `junction/J01/command`
  ```json
  {
    "command": "PRIORITY",
    "ambulance_id": "AMB_01",
    "duration": 20
  }
  ```
- **Junction Normal Command**: `junction/J01/command`
  ```json
  {
    "command": "NORMAL"
  }
  ```

### ESP32 Pin Mapping
- **North-South (Corridor Direction)**: Red: GPIO 23, Yellow: GPIO 22, Green: GPIO 21
- **East-West (Cross Direction)**: Red: GPIO 19, Yellow: GPIO 18, Green: GPIO 5

---

## 9. Troubleshooting

1. **PyTorch / Torchvision NMS Warning on Windows**:
   - `model_loader.py` automatically tests torchvision CUDA NMS and cleanly falls back to CPU if selective CUDA operators are missing, preventing crashes.
2. **Missing Video File**:
   - Run `python tests/generate_test_video.py` to generate `videos/emergency_demo.mp4` or provide your own `.mp4` video in the `videos/` folder.
3. **MQTT Connection Warning**:
   - If an MQTT broker is not running locally, the system automatically runs with console mock hardware fallback without interrupting video processing or API requests.

---

## 10. Hardware Requirements for Next Stage

For physical deployment with traffic lights and emergency vehicles:
- 1x ESP32 DevKit V1 per traffic junction
- 2x 3-channel Traffic Light LED Modules (Red, Yellow, Green 5V/12V with relay driver)
- 1x GPS Module (NEO-6M / NEO-8M) for ambulance GPS tracking
- 1x 4G/LTE / Wi-Fi IoT Gateway on ambulance
- MQTT Broker (Eclipse Mosquitto / EMQX deployed on cloud or edge server)

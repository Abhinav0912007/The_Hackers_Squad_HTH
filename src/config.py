# Central configuration file for AI + IoT Dynamic Ambulance Corridor System
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Model Configuration
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "yolo8vs.pt"))
# Fallback if models/yolo8vs.pt is not found
if not os.path.exists(MODEL_PATH):
    alt_model = BASE_DIR / "model" / "yolov8s (1).pt"
    if alt_model.exists():
        MODEL_PATH = str(alt_model)

# Detection & Validation Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))
REQUIRED_CONSECUTIVE_FRAMES = int(os.getenv("REQUIRED_CONSECUTIVE_FRAMES", "5"))

# Recovery & Emergency Timing (in seconds)
RECOVERY_TIMEOUT_SECONDS = float(os.getenv("RECOVERY_TIMEOUT_SECONDS", "10.0"))

# Paths
VIDEO_DIR = Path(os.getenv("VIDEO_DIR", str(BASE_DIR / "videos")))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs")))

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# Ambulance and Routing Defaults
DEFAULT_AMBULANCE_ID = os.getenv("AMBULANCE_ID", "AMB_01")
DEFAULT_AMBULANCE_START = os.getenv("AMBULANCE_START", "A")
DEFAULT_DESTINATION = os.getenv("DESTINATION", "HOSPITAL")

# MQTT Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))

# FastAPI Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

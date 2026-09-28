"""
MQTT Client Module for AI + IoT Dynamic Ambulance Corridor.
Publishes ambulance telemetry and traffic junction priority commands.
"""
import json
import time
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
from src.config import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_KEEPALIVE

class AmbulanceMQTTClient:
    def __init__(
        self,
        broker: str = MQTT_BROKER,
        port: int = MQTT_PORT,
        username: str = MQTT_USERNAME,
        password: str = MQTT_PASSWORD
    ):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[mqtt.Client] = None
        self.is_connected: bool = False
        self._init_client()

    def _init_client(self):
        try:
            # Paho MQTT 2.x compatibility with callback_api_version
            if hasattr(mqtt, "CallbackAPIVersion"):
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="AmbulanceCentralSystem")
            else:
                self.client = mqtt.Client(client_id="AmbulanceCentralSystem")

            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
        except Exception as e:
            print(f"[MQTT] Init error: {e}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            print(f"[MQTT] Connected successfully to broker {self.broker}:{self.port}")
        else:
            print(f"[MQTT] Connection failed with code: {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.is_connected = False
        print(f"[MQTT] Disconnected from broker.")

    def connect_async(self):
        """Attempt non-blocking connection to MQTT broker."""
        try:
            if self.client:
                self.client.connect_async(self.broker, self.port, MQTT_KEEPALIVE)
                self.client.loop_start()
        except Exception as e:
            print(f"[MQTT] Warning: Could not connect to MQTT broker ({self.broker}:{self.port}): {e}")
            print("        Operating in local/offline fallback mode.")

    def publish_ambulance_location(self, ambulance_id: str, latitude: float, longitude: float, speed: float, next_junction: Optional[str] = None):
        topic = f"ambulance/{ambulance_id}/location"
        payload = {
            "ambulance_id": ambulance_id,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "speed": round(speed, 1),
            "next_junction": next_junction or "NONE",
            "timestamp": time.time()
        }
        self._publish(topic, payload)

    def publish_junction_command(self, junction_id: str, command: str, ambulance_id: str = "AMB_01", duration: int = 20):
        topic = f"junction/{junction_id}/command"
        if command == "PRIORITY":
            payload = {
                "command": "PRIORITY",
                "ambulance_id": ambulance_id,
                "duration": duration,
                "timestamp": time.time()
            }
        else:
            payload = {
                "command": "NORMAL",
                "timestamp": time.time()
            }
        self._publish(topic, payload)

    def _publish(self, topic: str, payload: Dict[str, Any]):
        json_str = json.dumps(payload)
        if self.client and self.is_connected:
            self.client.publish(topic, json_str, qos=1)
        # Log published message
        # print(f"[MQTT PUBLISH] Topic: {topic} | Payload: {json_str}")

# Global MQTT Client instance
mqtt_client = AmbulanceMQTTClient()

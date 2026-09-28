"""
Hardware Abstraction Layer for Traffic Light Controllers.
Provides interface for both Mock Hardware (Console simulation) and MQTT Hardware (ESP32).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from src.state_manager import state_manager
from src.mqtt_client import mqtt_client

class HardwareController(ABC):
    @abstractmethod
    def set_priority(self, junction_id: str, ambulance_id: str = "AMB_01", duration: int = 20):
        pass

    @abstractmethod
    def set_normal(self, junction_id: str):
        pass

    @abstractmethod
    def reset_all(self):
        pass

class MockHardwareController(HardwareController):
    """
    Console simulated hardware controller.
    Logs signal state transitions without requiring physical microcontrollers.
    """
    def set_priority(self, junction_id: str, ambulance_id: str = "AMB_01", duration: int = 20):
        state_manager.set_junction_priority(junction_id, priority=True, duration_seconds=duration)
        print(f"[{junction_id}] PRIORITY -> Green Corridor Active for {ambulance_id} ({duration}s)")

    def set_normal(self, junction_id: str):
        state_manager.set_junction_priority(junction_id, priority=False)
        print(f"[{junction_id}] NORMAL -> Traffic Signals Resumed Standard Cycle")

    def reset_all(self):
        state_manager.reset_all_junctions_to_normal()
        junctions = state_manager.get_all_junctions()
        for j in junctions:
            print(f"[{j['junction_id']}] NORMAL")

class MQTTHardwareController(HardwareController):
    """
    Hardware controller transmitting commands over MQTT to ESP32 / IoT nodes.
    """
    def set_priority(self, junction_id: str, ambulance_id: str = "AMB_01", duration: int = 20):
        state_manager.set_junction_priority(junction_id, priority=True, duration_seconds=duration)
        mqtt_client.publish_junction_command(junction_id, command="PRIORITY", ambulance_id=ambulance_id, duration=duration)
        print(f"[ESP32 MQTT -> {junction_id}] PRIORITY signal sent")

    def set_normal(self, junction_id: str):
        state_manager.set_junction_priority(junction_id, priority=False)
        mqtt_client.publish_junction_command(junction_id, command="NORMAL")
        print(f"[ESP32 MQTT -> {junction_id}] NORMAL signal sent")

    def reset_all(self):
        state_manager.reset_all_junctions_to_normal()
        junctions = state_manager.get_all_junctions()
        for j in junctions:
            j_id = j["junction_id"]
            mqtt_client.publish_junction_command(j_id, command="NORMAL")
            print(f"[ESP32 MQTT -> {j_id}] NORMAL signal sent")

# Dual composite controller: updates both internal mock state & publishes to MQTT
class CompositeHardwareController(HardwareController):
    def __init__(self):
        self.mock = MockHardwareController()
        self.mqtt = MQTTHardwareController()

    def set_priority(self, junction_id: str, ambulance_id: str = "AMB_01", duration: int = 20):
        self.mock.set_priority(junction_id, ambulance_id, duration)
        self.mqtt.set_priority(junction_id, ambulance_id, duration)

    def set_normal(self, junction_id: str):
        self.mock.set_normal(junction_id)
        self.mqtt.set_normal(junction_id)

    def reset_all(self):
        self.mock.reset_all()
        self.mqtt.reset_all()

# Default controller instance
hardware_controller = CompositeHardwareController()

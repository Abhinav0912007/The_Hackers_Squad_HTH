"""
Ambulance GPS Tracker and Dynamic Corridor Controller.
Simulates ambulance movement along the shortest path and shifts traffic priority dynamically.
"""
import time
import math
from typing import Dict, Any, List, Optional
from src.state_manager import state_manager
from src.route_engine import route_engine
from src.hardware_controller import hardware_controller
from src.mqtt_client import mqtt_client

class AmbulanceTracker:
    def __init__(self, ambulance_id: str = "AMB_01"):
        self.ambulance_id = ambulance_id
        self.route: List[str] = []
        self.current_step_index: int = 0
        self.status: str = "IDLE"  # IDLE, DISPATCHED, EN_ROUTE, ARRIVED
        self.active_priority_junction: Optional[str] = None
        self.speed: float = 45.0  # km/h

    def dispatch(self, start_node: str = "A", destination_node: str = "HOSPITAL") -> Dict[str, Any]:
        """
        Calculate shortest path and dispatch the ambulance.
        """
        route_result = route_engine.find_shortest_path_astar(start_node, destination_node)
        self.route = route_result["route"]
        self.current_step_index = 0
        self.status = "DISPATCHED"
        
        # Save route in state manager
        state_manager.set_active_route(route_result)
        
        # Initial node setup
        first_node = self.route[0]
        first_pos = route_engine.nodes[first_node]
        
        next_node = self.route[1] if len(self.route) > 1 else None
        
        # Update ambulance state
        state_manager.update_ambulance_location(
            ambulance_id=self.ambulance_id,
            latitude=first_pos["lat"],
            longitude=first_pos["lon"],
            speed=0.0,
            current_node=first_node,
            next_node=next_node,
            status="DISPATCHED"
        )
        
        # Reset all signals first
        hardware_controller.reset_all()

        # Identify upcoming junction and activate priority
        upcoming_junction = self.get_upcoming_junction()
        if upcoming_junction:
            self._activate_junction_priority(upcoming_junction)

        print(f"\n[AmbulanceTracker] Ambulance {self.ambulance_id} DISPATCHED from {start_node} to {destination_node}.")
        print(f"[AmbulanceTracker] Route: {' -> '.join(self.route)}")
        print(f"[AmbulanceTracker] Total Distance: {route_result['distance']} km | ETA: {route_result['estimated_time']}s")
        print(route_engine.render_ascii_route(self.route, first_node))
        
        return route_result

    def get_upcoming_junction(self) -> Optional[str]:
        """
        Identify the next junction ahead of the ambulance along the active route.
        Maps node names (e.g. B -> J01, C -> J02, G -> J03, E -> J04).
        """
        # Node to Junction mapping helper
        node_to_junction = {
            "B": "J01",
            "C": "J02",
            "G": "J03",
            "E": "J04",
            "J01": "J01",
            "J02": "J02",
            "J03": "J03",
            "J04": "J04"
        }

        for i in range(self.current_step_index, len(self.route)):
            node = self.route[i]
            if node in node_to_junction:
                return node_to_junction[node]
        return None

    def _activate_junction_priority(self, junction_id: str):
        if self.active_priority_junction and self.active_priority_junction != junction_id:
            # Revert previously prioritized junction to NORMAL
            print(f"[Corridor] Reverting {self.active_priority_junction} to NORMAL")
            hardware_controller.set_normal(self.active_priority_junction)
        
        self.active_priority_junction = junction_id
        print(f"[Corridor] Granting DYNAMIC PRIORITY (GREEN CORRIDOR) to upcoming junction {junction_id}")
        hardware_controller.set_priority(junction_id, self.ambulance_id, duration=30)

    def step(self) -> Dict[str, Any]:
        """
        Advance ambulance one step along the route.
        """
        if not self.route or self.status == "ARRIVED":
            return state_manager.get_ambulance_state()

        if self.status == "DISPATCHED":
            self.status = "EN_ROUTE"

        self.current_step_index += 1

        if self.current_step_index >= len(self.route) - 1:
            # Ambulance has reached the destination (Hospital)
            dest_node = self.route[-1]
            dest_pos = route_engine.nodes[dest_node]
            self.status = "ARRIVED"
            
            # Revert any active priority junction to normal
            if self.active_priority_junction:
                hardware_controller.set_normal(self.active_priority_junction)
                self.active_priority_junction = None
            hardware_controller.reset_all()

            state = state_manager.update_ambulance_location(
                ambulance_id=self.ambulance_id,
                latitude=dest_pos["lat"],
                longitude=dest_pos["lon"],
                speed=0.0,
                current_node=dest_node,
                next_node=None,
                status="ARRIVED"
            )
            mqtt_client.publish_ambulance_location(self.ambulance_id, dest_pos["lat"], dest_pos["lon"], 0.0, None)
            print(f"\n[AmbulanceTracker] Ambulance {self.ambulance_id} ARRIVED at {dest_node} (Hospital)!")
            print("[Corridor] All traffic signals returned to NORMAL.")
            return state

        # Currently at intermediate node
        curr_node = self.route[self.current_step_index]
        next_node = self.route[self.current_step_index + 1] if self.current_step_index + 1 < len(self.route) else None
        curr_pos = route_engine.nodes[curr_node]
        
        # Determine upcoming junction and update corridor priority
        upcoming_junction = self.get_upcoming_junction()
        if upcoming_junction and upcoming_junction != self.active_priority_junction:
            self._activate_junction_priority(upcoming_junction)

        state = state_manager.update_ambulance_location(
            ambulance_id=self.ambulance_id,
            latitude=curr_pos["lat"],
            longitude=curr_pos["lon"],
            speed=self.speed,
            current_node=curr_node,
            next_node=next_node,
            status=self.status
        )

        mqtt_client.publish_ambulance_location(self.ambulance_id, curr_pos["lat"], curr_pos["lon"], self.speed, upcoming_junction)
        print(f"[AmbulanceTracker] AMB_01 reached node '{curr_node}' -> Moving towards '{next_node}' | Next Junction: {upcoming_junction}")
        print(route_engine.render_ascii_route(self.route, curr_node))

        return state

    def simulate_full_run(self, delay_seconds: float = 1.0) -> List[Dict[str, Any]]:
        """
        Run the complete simulation until arrival.
        """
        history = [state_manager.get_ambulance_state()]
        while self.status != "ARRIVED":
            time.sleep(delay_seconds)
            state = self.step()
            history.append(state)
        return history

# Global tracker instance
ambulance_tracker = AmbulanceTracker()

"""
Shortest Path Engine using Dijkstra and A* Algorithms.
Computes optimal ambulance routing over a graph-based road network.
STRICT REQUIREMENT: NO HARD-CODED ROUTES.
"""
import math
import heapq
from typing import Dict, List, Tuple, Optional, Any

class RoadGraph:
    def __init__(self):
        # Nodes: {node_id: {"name": str, "lat": float, "lon": float, "type": str}}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # Adjacency list: {node_id: {neighbor_id: {"distance_km": float, "speed_limit_kmh": float, "delay_factor": float}}}
        self.edges: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._build_default_city_network()

    def add_node(self, node_id: str, name: str, lat: float, lon: float, node_type: str = "JUNCTION"):
        self.nodes[node_id] = {
            "id": node_id,
            "name": name,
            "lat": lat,
            "lon": lon,
            "type": node_type  # "START", "JUNCTION", "EMERGENCY_SCENE", "HOSPITAL"
        }
        if node_id not in self.edges:
            self.edges[node_id] = {}

    def add_edge(self, u: str, v: str, distance_km: float, speed_limit_kmh: float = 40.0, bidirectional: bool = True):
        if u not in self.nodes or v not in self.nodes:
            raise ValueError(f"Nodes {u} and {v} must exist before adding an edge.")
        
        self.edges[u][v] = {
            "distance_km": float(distance_km),
            "speed_limit_kmh": float(speed_limit_kmh),
            "delay_factor": 1.0  # multiplier for traffic congestion
        }
        if bidirectional:
            self.edges[v][u] = {
                "distance_km": float(distance_km),
                "speed_limit_kmh": float(speed_limit_kmh),
                "delay_factor": 1.0
            }

    def _build_default_city_network(self):
        """
        Build realistic city road network graph:
        A ---- B ---- C
        |      |      |
        D ---- E ---- F
               |
               G
               |
            HOSPITAL
        """
        # Add Nodes with coordinates
        self.add_node("A", "Ambulance Station A / Incident Point", 21.1458, 79.0882, "START")
        self.add_node("B", "Junction J01 (North Central)", 21.1465, 79.0910, "JUNCTION")
        self.add_node("C", "Junction J02 (North East)", 21.1470, 79.0945, "JUNCTION")
        self.add_node("D", "South West Corridor", 21.1420, 79.0880, "JUNCTION")
        self.add_node("E", "Junction J04 (Central Hub)", 21.1425, 79.0912, "JUNCTION")
        self.add_node("F", "East Perimeter Crossing", 21.1430, 79.0950, "JUNCTION")
        self.add_node("G", "Junction J03 (Hospital Approach)", 21.1390, 79.0915, "JUNCTION")
        self.add_node("HOSPITAL", "Metropolitan Apex Hospital", 21.1350, 79.0920, "HOSPITAL")

        # Add Edges (distances in kilometers, speeds in km/h)
        self.add_edge("A", "B", distance_km=1.2, speed_limit_kmh=50.0)
        self.add_edge("B", "C", distance_km=1.5, speed_limit_kmh=50.0)
        self.add_edge("A", "D", distance_km=1.1, speed_limit_kmh=40.0)
        self.add_edge("D", "E", distance_km=1.3, speed_limit_kmh=45.0)
        self.add_edge("B", "E", distance_km=1.0, speed_limit_kmh=40.0)
        self.add_edge("C", "F", distance_km=1.2, speed_limit_kmh=45.0)
        self.add_edge("E", "F", distance_km=1.4, speed_limit_kmh=45.0)
        self.add_edge("E", "G", distance_km=1.0, speed_limit_kmh=50.0)
        self.add_edge("G", "HOSPITAL", distance_km=1.1, speed_limit_kmh=60.0)

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great circle distance in kilometers between two GPS points."""
        R = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _heuristic(self, node_a: str, node_b: str) -> float:
        """A* heuristic function: Haversine distance between nodes."""
        pos_a = self.nodes[node_a]
        pos_b = self.nodes[node_b]
        return self.haversine_distance(pos_a["lat"], pos_a["lon"], pos_b["lat"], pos_b["lon"])

    def find_shortest_path_astar(self, start: str, destination: str) -> Dict[str, Any]:
        """
        A* Shortest Path Algorithm.
        """
        if start not in self.nodes:
            raise KeyError(f"Start node '{start}' not found in road network graph.")
        if destination not in self.nodes:
            raise KeyError(f"Destination node '{destination}' not found in road network graph.")

        open_set = []
        heapq.heappush(open_set, (0.0, start))
        
        came_from: Dict[str, str] = {}
        g_score: Dict[str, float] = {node: float("inf") for node in self.nodes}
        g_score[start] = 0.0

        f_score: Dict[str, float] = {node: float("inf") for node in self.nodes}
        f_score[start] = self._heuristic(start, destination)

        while open_set:
            current_f, current = heapq.heappop(open_set)

            if current == destination:
                return self._reconstruct_route(came_from, current, start, destination)

            for neighbor, edge_data in self.edges.get(current, {}).items():
                cost = edge_data["distance_km"] * edge_data.get("delay_factor", 1.0)
                tentative_g = g_score[current] + cost

                if tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, destination)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        raise ValueError(f"No reachable path found between '{start}' and '{destination}'.")

    def find_shortest_path_dijkstra(self, start: str, destination: str) -> Dict[str, Any]:
        """
        Dijkstra's Shortest Path Algorithm.
        """
        if start not in self.nodes or destination not in self.nodes:
            raise KeyError("Start or destination node not in graph.")

        distances: Dict[str, float] = {node: float("inf") for node in self.nodes}
        distances[start] = 0.0
        previous_nodes: Dict[str, str] = {}
        pq = [(0.0, start)]

        while pq:
            current_dist, current_node = heapq.heappop(pq)

            if current_node == destination:
                break

            if current_dist > distances[current_node]:
                continue

            for neighbor, edge_data in self.edges.get(current_node, {}).items():
                weight = edge_data["distance_km"] * edge_data.get("delay_factor", 1.0)
                new_dist = current_dist + weight

                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(pq, (new_dist, neighbor))

        return self._reconstruct_route(previous_nodes, destination, start, destination)

    def _reconstruct_route(self, came_from: Dict[str, str], current: str, start: str, destination: str) -> Dict[str, Any]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()

        total_distance = 0.0
        total_time_seconds = 0.0
        waypoints = []

        for i in range(len(path)):
            node_id = path[i]
            node_info = self.nodes[node_id]
            waypoints.append({
                "node_id": node_id,
                "name": node_info["name"],
                "lat": node_info["lat"],
                "lon": node_info["lon"],
                "type": node_info["type"]
            })

            if i < len(path) - 1:
                next_id = path[i + 1]
                edge_data = self.edges[node_id][next_id]
                dist = edge_data["distance_km"]
                speed = edge_data["speed_limit_kmh"]
                total_distance += dist
                # Time in seconds = (distance / speed) * 3600
                total_time_seconds += (dist / speed) * 3600

        return {
            "ambulance_id": "AMB_01",
            "start": start,
            "destination": destination,
            "route": path,
            "waypoints": waypoints,
            "distance": round(total_distance, 2),
            "estimated_time": int(total_time_seconds)
        }

    def render_ascii_route(self, route_nodes: List[str], current_node: Optional[str] = None) -> str:
        """Render a readable text visualization of the route."""
        lines = []
        lines.append("=" * 50)
        lines.append("         AMBULANCE ROUTE CORRIDOR         ")
        lines.append("=" * 50)
        for i, node in enumerate(route_nodes):
            marker = " [CURRENT POSITION]" if node == current_node else ""
            node_name = self.nodes[node]["name"]
            if i == 0:
                lines.append(f" START       -> ({node}) {node_name}{marker}")
            elif i == len(route_nodes) - 1:
                lines.append(f" DESTINATION -> ({node}) {node_name}{marker}")
            else:
                lines.append(f" JUNCTION {i}  -> ({node}) {node_name}{marker}")
            if i < len(route_nodes) - 1:
                lines.append("     |")
                lines.append("     v")
        lines.append("=" * 50)
        return "\n".join(lines)

# Global route engine instance
route_engine = RoadGraph()

"""
Main CLI Application Runner for AI + IoT Dynamic Ambulance Corridor System.
"""
import sys
import argparse
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MODEL_PATH, VIDEO_DIR, API_HOST, API_PORT
from src.model_loader import inspect_model_details
from src.route_engine import route_engine
from src.ambulance_tracker import ambulance_tracker
from src.hardware_controller import hardware_controller
from src.video_inference import process_video

def run_simulation():
    print("\n" + "=" * 60)
    print("      AI + IoT DYNAMIC AMBULANCE CORRIDOR SYSTEM")
    print("              END-TO-END DEMONSTRATION")
    print("=" * 60)

    print("\n[STEP 1] Road Network & Shortest Path Computation")
    start_node = "A"
    dest_node = "HOSPITAL"
    route_result = route_engine.find_shortest_path_astar(start_node, dest_node)
    
    print(f"Calculated Optimal Route: {' -> '.join(route_result['route'])}")
    print(f"Total Corridor Distance: {route_result['distance']} km")
    print(f"Estimated Response Time: {route_result['estimated_time']} seconds")
    print(route_engine.render_ascii_route(route_result['route'], start_node))

    print("\n[STEP 2] Dispatching Ambulance AMB_01 & Activating Dynamic Priority")
    ambulance_tracker.dispatch(start_node, dest_node)

    print("\n[STEP 3] Simulating Live Ambulance GPS Telemetry & Junction Priority Hand-off")
    history = ambulance_tracker.simulate_full_run(delay_seconds=0.8)
    
    print("\n[STEP 4] Arrival and Signal Normalization")
    print("Simulation completed successfully! All signals returned to NORMAL.")
    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="AI + IoT Dynamic Ambulance Corridor System Entrypoint")
    parser.add_argument("--mode", choices=["simulate", "video", "api", "inspect"], default="simulate", help="Execution mode")
    parser.add_argument("--source", type=str, default=None, help="Video source path (for --mode video)")
    parser.add_argument("--host", type=str, default=API_HOST, help="API host")
    parser.add_argument("--port", type=int, default=API_PORT, help="API port")
    args = parser.parse_args()

    if args.mode == "inspect":
        details = inspect_model_details(MODEL_PATH)
        print("Model Classes:", details["names"])
    elif args.mode == "simulate":
        run_simulation()
    elif args.mode == "video":
        if not args.source:
            print("Error: --source <video_file> is required for video mode.")
            sys.exit(1)
        process_video(video_source=args.source)
    elif args.mode == "api":
        import uvicorn
        uvicorn.run("api.main:app", host=args.host, port=args.port, reload=True)

if __name__ == "__main__":
    main()

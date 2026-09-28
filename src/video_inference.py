"""
Video Inference Pipeline for AI + IoT Dynamic Ambulance Corridor.
Processes ONLY recorded video files.
STRICT REQUIREMENT: NO WEBCAM, NO LIVE CAMERA (NO cv2.VideoCapture(0)).
"""
import sys
import os
import time
import argparse
from pathlib import Path
import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CONFIDENCE_THRESHOLD, REQUIRED_CONSECUTIVE_FRAMES, RECOVERY_TIMEOUT_SECONDS, OUTPUT_DIR
from src.detector import YOLODetector
from src.emergency_validator import FallValidator
from src.recovery_monitor import RecoveryMonitor
from src.event_processor import EventProcessor
from src.ambulance_tracker import ambulance_tracker
from src.state_manager import state_manager

def draw_hud_overlay(
    frame: np.ndarray,
    fps: float,
    frame_num: int,
    total_frames: int,
    fall_status: str,
    fall_conf: float,
    recovery_data: dict,
    ambulance_status: str,
    active_junction: str,
    is_emergency: bool
) -> np.ndarray:
    """
    Draw emergency status HUD overlay on video frame.
    """
    h, w = frame.shape[:2]
    
    # Top Information Bar
    header_color = (0, 0, 180) if is_emergency else (30, 30, 30)
    cv2.rectangle(frame, (0, 0), (w, 75), header_color, -1)
    
    title_text = "AI + IoT DYNAMIC AMBULANCE CORRIDOR SYSTEM"
    cv2.putText(frame, title_text, (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    
    status_tag = "SUSPECTED SERIOUS MEDICAL EMERGENCY" if is_emergency else "STATUS: MONITORING"
    tag_color = (0, 255, 255) if is_emergency else (0, 255, 0)
    cv2.putText(frame, status_tag, (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.65, tag_color, 2)
    
    fps_text = f"FPS: {fps:.1f} | Frame: {frame_num}/{total_frames}"
    cv2.putText(frame, fps_text, (w - 280, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    # Bottom Dashboard Panel
    panel_h = 100
    cv2.rectangle(frame, (0, h - panel_h), (w, h), (20, 20, 20), -1)
    
    # Column 1: Fall & Detection
    cv2.putText(frame, f"Fall Status: {fall_status}", (20, h - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(frame, f"Fall Confidence: {fall_conf:.2f}", (20, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    cv2.putText(frame, f"Consecutive: {recovery_data.get('consecutive', 0)}/{REQUIRED_CONSECUTIVE_FRAMES}", (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    # Column 2: 10s Recovery Monitor
    rec_state = recovery_data.get("state", "IDLE")
    elapsed = recovery_data.get("elapsed", 0.0)
    rem = recovery_data.get("remaining", RECOVERY_TIMEOUT_SECONDS)
    
    timer_color = (0, 0, 255) if is_emergency else ((0, 165, 255) if rec_state == "RECOVERY_MONITORING" else (0, 255, 0))
    cv2.putText(frame, f"Recovery Monitor: {rec_state}", (w // 3, h - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, timer_color, 2)
    cv2.putText(frame, f"Timer: {elapsed:.1f}s / {RECOVERY_TIMEOUT_SECONDS:.0f}s (Remaining: {rem:.1f}s)", (w // 3, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(frame, f"Posture: {recovery_data.get('person_state', 'N/A')}", (w // 3, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Column 3: Ambulance & Traffic Corridor
    cv2.putText(frame, f"Ambulance: {ambulance_status}", (2 * w // 3, h - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    corridor_text = f"Priority Junction: {active_junction or 'NONE (NORMAL)'}"
    junc_color = (0, 255, 0) if active_junction else (180, 180, 180)
    cv2.putText(frame, corridor_text, (2 * w // 3, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, junc_color, 2)
    cv2.putText(frame, "Corridor Mode: DYNAMIC GREEN WAVE", (2 * w // 3, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    return frame

def process_video(
    video_source: str,
    model_path: str = None,
    output_path: str = None,
    show_window: bool = False
) -> dict:
    """
    Main Video Processing Loop.
    Enforces recorded video input only (no webcam/live streams).
    """
    # Strict validation: prevent any webcam indices
    if str(video_source).strip() in ["0", "1", "2", "webcam", "camera"]:
        raise ValueError("Webcam / live camera input is strictly forbidden. Please provide a recorded video file path.")

    video_file = Path(video_source)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found at: {video_source}")

    print(f"\n============================================================")
    print(f"[VideoInference] Loading recorded video: {video_source}")
    print(f"============================================================")

    cap = cv2.VideoCapture(str(video_file))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file: {video_source}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"[VideoInference] Properties: {width}x{height} | {fps:.2f} FPS | Total Frames: {total_frames}")

    # Initialize Modules
    detector = YOLODetector(model_path=model_path, confidence_threshold=CONFIDENCE_THRESHOLD)
    validator = FallValidator(confidence_threshold=CONFIDENCE_THRESHOLD, required_consecutive_frames=REQUIRED_CONSECUTIVE_FRAMES)
    recovery_monitor = RecoveryMonitor(timeout_seconds=RECOVERY_TIMEOUT_SECONDS)
    event_processor = EventProcessor()

    # Video Writer Output Setup
    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / f"annotated_{video_file.name}")
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_num = 0
    start_proc_time = time.time()
    emergency_event_created = False
    emergency_payload = None

    last_time = time.time()
    computed_fps = fps

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1
        video_timestamp_sec = frame_num / fps

        # Compute loop FPS
        curr_time = time.time()
        time_diff = curr_time - last_time
        if time_diff > 0:
            computed_fps = 0.9 * computed_fps + 0.1 * (1.0 / time_diff)
        last_time = curr_time

        # 1. Run YOLO Object Detection
        t0 = time.time()
        detections = detector.detect(frame, frame_number=frame_num)
        infer_time_ms = (time.time() - t0) * 1000

        # 2. Validate Fall across consecutive frames
        val_res = validator.process_detections(detections)
        fall_status = val_res["status"]
        fall_cand = val_res["fall_candidate"]
        fall_conf = fall_cand["confidence"] if fall_cand else 0.0

        # 3. Handle 10-Second Recovery Monitoring
        if val_res["is_confirmed"] and recovery_monitor.state == "IDLE":
            recovery_monitor.start_monitoring(current_time=video_timestamp_sec)

        rec_res = recovery_monitor.update(current_time=video_timestamp_sec, detections=detections)
        
        # Update in-memory state manager
        state_manager.update_fall_monitoring(
            status=fall_status,
            consecutive_frames=val_res["consecutive_counter"],
            recovery_state=rec_res["state"],
            elapsed_seconds=rec_res["elapsed_seconds"]
        )

        # 4. Emergency Trigger at 10 seconds of non-recovery
        is_emergency = rec_res["state"] == "SUSPECTED_SERIOUS_MEDICAL_EMERGENCY"
        if is_emergency and not emergency_event_created:
            emergency_event_created = True
            emergency_payload = event_processor.create_emergency_event(
                confidence=fall_conf if fall_conf > 0 else 0.90,
                video_source=str(video_file.name),
                frame_number=frame_num,
                trigger="fall_with_10_second_non_recovery"
            )
            # Dispatch ambulance automatically
            ambulance_tracker.dispatch(start_node="A", destination_node="HOSPITAL")

        # 5. Advance ambulance simulation if emergency is active
        if is_emergency:
            # Advance simulation step every 2 seconds of video time
            if frame_num % max(1, int(fps * 2.0)) == 0 and ambulance_tracker.status != "ARRIVED":
                ambulance_tracker.step()

        # 6. Draw Bounding Boxes and Annotations
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cls_name = det["class_name"]
            conf = det["confidence"]
            posture = det["posture"]

            # Box color: Red if fall candidate, Green if standing, Cyan for others
            if det["is_fall_candidate"]:
                box_color = (0, 0, 255)
            elif posture == "STANDING":
                box_color = (0, 255, 0)
            else:
                box_color = (255, 200, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            label = f"{cls_name} ({conf:.2f}) [{posture}]"
            cv2.putText(frame, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 2)

        # 7. Draw HUD Dashboard
        amb_state = state_manager.get_ambulance_state()
        active_junc = ambulance_tracker.active_priority_junction

        recovery_info = {
            "state": rec_res["state"],
            "elapsed": rec_res["elapsed_seconds"],
            "remaining": rec_res["remaining_seconds"],
            "person_state": rec_res.get("person_state", "N/A"),
            "consecutive": val_res["consecutive_counter"]
        }

        annotated_frame = draw_hud_overlay(
            frame=frame,
            fps=computed_fps,
            frame_num=frame_num,
            total_frames=total_frames,
            fall_status=fall_status,
            fall_conf=fall_conf,
            recovery_data=recovery_info,
            ambulance_status=amb_state["status"],
            active_junction=active_junc,
            is_emergency=is_emergency
        )

        out_writer.write(annotated_frame)

        if show_window:
            cv2.imshow("AI + IoT Ambulance Corridor - Video Inference", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    out_writer.release()
    if show_window:
        cv2.destroyAllWindows()

    total_proc_time = time.time() - start_proc_time
    print(f"\n============================================================")
    print(f"[VideoInference] Completed processing {frame_num} frames in {total_proc_time:.2f}s")
    print(f"[VideoInference] Annotated video saved to: {output_path}")
    print(f"[VideoInference] Final Fall Status: {fall_status} | Recovery State: {recovery_monitor.state}")
    print(f"============================================================\n")

    return {
        "total_frames_processed": frame_num,
        "processing_time_seconds": round(total_proc_time, 2),
        "output_video": output_path,
        "fall_confirmed": val_res["is_confirmed"],
        "recovery_state": recovery_monitor.state,
        "emergency_triggered": emergency_event_created,
        "emergency_event": emergency_payload
    }

def main():
    parser = argparse.ArgumentParser(description="Process recorded video for fall detection and ambulance corridor dispatch.")
    parser.add_argument("--source", type=str, required=True, help="Path to recorded video file (e.g. videos/emergency.mp4)")
    parser.add_argument("--model", type=str, default=None, help="Optional custom path to YOLO .pt model")
    parser.add_argument("--output", type=str, default=None, help="Optional output video file path")
    parser.add_argument("--show", action="store_true", help="Display visual playback window")
    args = parser.parse_args()

    process_video(
        video_source=args.source,
        model_path=args.model,
        output_path=args.output,
        show_window=args.show
    )

if __name__ == "__main__":
    main()

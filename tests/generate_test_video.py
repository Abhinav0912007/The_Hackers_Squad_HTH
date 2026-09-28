"""
Synthetic Test Video Generator for Fall and Recovery Simulation.
Creates a video with simulated human posture changes to test end-to-end video inference.
"""
import cv2
import numpy as np
from pathlib import Path

def generate_emergency_test_video(output_path: str = "videos/emergency_demo.mp4", duration_sec: int = 15, fps: int = 30):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    width, height = 640, 480
    total_frames = duration_sec * fps
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Phase 1: 0 - 2s (Frames 0-60) Standing person
    # Phase 2: 2s - 15s (Frames 61-450) Fallen person (horizontal box) on ground
    for frame_idx in range(total_frames):
        img = np.full((height, width, 3), 40, dtype=np.uint8) # Dark room background
        
        # Draw floor line
        cv2.line(img, (0, 380), (width, 380), (80, 80, 80), 2)
        
        t_sec = frame_idx / fps

        if t_sec < 2.0:
            # Standing posture (vertical bounding box)
            cv2.rectangle(img, (280, 180), (360, 380), (200, 200, 200), -1)
            cv2.circle(img, (320, 150), 25, (220, 220, 220), -1)
            cv2.putText(img, "Person: Standing", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            # Fallen posture on floor (horizontal bounding box)
            cv2.rectangle(img, (200, 320), (440, 380), (200, 200, 200), -1)
            cv2.circle(img, (180, 350), 22, (220, 220, 220), -1)
            cv2.putText(img, f"Person: Fallen on ground (t={t_sec:.1f}s)", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        out.write(img)

    out.release()
    print(f"[TestVideoGen] Successfully created test video: {output_path} ({duration_sec}s, {total_frames} frames)")
    return output_path

if __name__ == "__main__":
    generate_emergency_test_video()

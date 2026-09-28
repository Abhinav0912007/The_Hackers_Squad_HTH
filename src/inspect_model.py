"""
Script to inspect YOLO model properties and verify classes directly from model.names.
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.model_loader import inspect_model_details
from src.config import MODEL_PATH

def main():
    parser = argparse.ArgumentParser(description="Inspect YOLO Model details and class names.")
    parser.add_argument("--model", type=str, default=MODEL_PATH, help="Path to YOLO model (.pt)")
    args = parser.parse_args()

    print("=" * 60)
    print("           YOLO MODEL INSPECTION           ")
    print("=" * 60)
    
    try:
        details = inspect_model_details(args.model)
        print(f"Model Path:         {details['model_path']}")
        print(f"Model Task:         {details['task']}")
        print(f"Number of Classes:  {details['num_classes']}")
        print("\nClass IDs and Class Names (model.names):")
        print("-" * 60)
        for class_id, class_name in details['names'].items():
            print(f"  Class ID {class_id:3d} : '{class_name}'")
        print("-" * 60)

        # Check for fall-related and person-related classes
        names_dict = details['names']
        fall_classes = [name for name in names_dict.values() if "fall" in str(name).lower()]
        person_classes = [name for name in names_dict.values() if "person" in str(name).lower() or "human" in str(name).lower() or "stand" in str(name).lower()]

        print("\nClass Analysis:")
        if fall_classes:
            print(f"  [+] Fall-related classes found: {fall_classes}")
        else:
            print("  [!] Notice: No explicit class with substring 'fall' found.")
            print("      Model might be standard COCO (person class) or custom format.")
        
        if person_classes:
            print(f"  [+] Person/Human-related classes found: {person_classes}")

        print("=" * 60)
        return details
    except Exception as e:
        print(f"Error inspecting model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

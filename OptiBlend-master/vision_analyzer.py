import cv2
import numpy as np
from ultralytics import YOLO
import sys

# Constants
MODEL_PATH = 'yolov8n.pt'
# Mapping standard COCO classes to our Industrial Waste types
CLASS_MAPPING = {
    2: "Tires", 7: "Tires",
    39: "Plastic_HDPE", 41: "Plastic_HDPE",
    56: "Wood", 57: "Wood",
    58: "Biomass",
}

def calculate_surface_percentage(results, frame_area):
    """Calculates coverage percentage per class."""
    surface_map = {}
    if results[0].boxes:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            label = CLASS_MAPPING.get(cls_id, results[0].names[cls_id])
            _, _, w, h = box.xywh[0]
            box_area = float(w * h)
            
            if label not in surface_map: surface_map[label] = 0.0
            surface_map[label] += box_area

    percentages = {}
    for label, area in surface_map.items():
        pct = (area / frame_area) * 100.0
        percentages[label] = round(pct, 2)
        
    for key in ["Tires", "Plastic_HDPE", "Wood", "Biomass"]:
        if key not in percentages: percentages[key] = 0.0
            
    return percentages

def run_live_analysis():
    print(f"Loading YOLO model ({MODEL_PATH})...")
    model = YOLO(MODEL_PATH) 
    
    print("Opening Camera Feed...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open video device.")
        return

    print("Vision System Active. Press 'q' to exit.")

    while True:
        success, frame = cap.read()
        if not success: break

        results = model(frame, verbose=False)
        height, width, _ = frame.shape
        frame_area = width * height
        
        surfaces = calculate_surface_percentage(results, frame_area)
        
        # Print to Console for CLI_Monitor
        sys.stdout.write(f"\rVISION_OUTPUT: {surfaces}")
        sys.stdout.flush()

        # Visualization
        annotated_frame = results[0].plot()
        y_offset = 30
        for label, pct in surfaces.items():
            text = f"{label}: {pct}%"
            cv2.putText(annotated_frame, text, (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += 30

        cv2.imshow("Holcim AI-Recipe | Vision Analyzer", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\nVision System Stopped.")

if __name__ == "__main__":
    run_live_analysis()

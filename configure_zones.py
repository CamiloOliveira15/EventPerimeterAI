import cv2
import json
import numpy as np
import os

# Global variables
points = []
zones = {}
current_zone_name = "recording_zone" 
zone_names = ["recording_zone", "violation_zone"]
zone_colors = {"recording_zone": (255, 0, 0), "violation_zone": (0, 0, 255)} # Blue, Red

def mouse_callback(event, x, y, flags, param):
    global points

    if event == cv2.EVENT_LBUTTONDOWN:
        # Scale coordinates back to actual resolution
        real_x = int(x * scale_x)
        real_y = int(y * scale_y)
        points.append((real_x, real_y))
        print(f"Point added to {current_zone_name}: {real_x}, {real_y}")

import argparse

def main():
    global points, current_zone_name, zones, scale_x, scale_y
    
    parser = argparse.ArgumentParser(description='Define perimeter zones.')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (default: 0)')
    args = parser.parse_args()

    print(f"Opening camera {args.camera}...")
    source = args.camera
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        source = 1
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return

    # Set Camera to 4K (same as monitoring script)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
    cap.set(cv2.CAP_PROP_FPS, 30)

    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Camera resolution: {int(actual_w)}x{int(actual_h)}")

    # Display resolution (HD)
    display_w = 1280
    display_h = 720
    
    scale_x = actual_w / display_w
    scale_y = actual_h / display_h

    cv2.namedWindow('Perimeter Definition')
    cv2.setMouseCallback('Perimeter Definition', mouse_callback)

    print(f"--- DEFINING {current_zone_name.upper()} ---")
    print("Controls:")
    print("  Click: Add point")
    print("  n: Confirm current zone & Next")
    print("  s: Save ALL and Quit (must define both zones)")
    print("  c: Clear current points")
    print("  q: Quit (without saving)")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Resize for display
        display_frame = cv2.resize(frame, (display_w, display_h))

        # Draw previously defined zones
        for name, zone_points in zones.items():
            if len(zone_points) > 1:
                # Scale points for display
                display_points = [(int(pt[0]/scale_x), int(pt[1]/scale_y)) for pt in zone_points]
                cv2.polylines(display_frame, [np.array(display_points)], isClosed=True, color=zone_colors[name], thickness=2)
                # Label
                cv2.putText(display_frame, name, display_points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone_colors[name], 2)

        # Draw current points
        if len(points) > 0:
            # Scale current points for display
            display_points = [(int(pt[0]/scale_x), int(pt[1]/scale_y)) for pt in points]
            for pt in display_points:
                cv2.circle(display_frame, pt, 5, zone_colors[current_zone_name], -1)
            
            if len(display_points) > 1:
                cv2.polylines(display_frame, [np.array(display_points)], isClosed=True, color=zone_colors[current_zone_name], thickness=2)

        # UI Text
        cv2.putText(display_frame, f"Defining: {current_zone_name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, zone_colors[current_zone_name], 2)
        
        status_text = "Press 'n' to confirm zone"
        if len(zones) == len(zone_names):
             status_text = "All zones defined! Press 's' to save."
        
        cv2.putText(display_frame, status_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow('Perimeter Definition', display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            points = []
            print("Current points cleared.")
        elif key == ord('n'):
            if len(points) < 3:
                print("Error: A zone must have at least 3 points.")
                continue
            
            zones[current_zone_name] = points
            points = []
            print(f"Confirmed {current_zone_name}.")
            
            # Move to next zone if available
            current_idx = zone_names.index(current_zone_name)
            if current_idx < len(zone_names) - 1:
                current_zone_name = zone_names[current_idx + 1]
                print(f"--- DEFINING {current_zone_name.upper()} ---")
            else:
                print("All zones defined. Press 's' to save and quit.")

        elif key == ord('s'):
            # Check if all zones are present
            if all(name in zones for name in zone_names):
                filename = 'perimeters.json'
                
                # Load existing data
                all_perimeters = {}
                if os.path.exists(filename):
                    try:
                        with open(filename, 'r') as f:
                            all_perimeters = json.load(f)
                    except json.JSONDecodeError:
                        print("Warning: Could not decode existing JSON. Starting fresh.")
                
                # Update for current camera
                camera_id = str(args.camera)
                all_perimeters[camera_id] = zones
                
                with open(filename, 'w') as f:
                    json.dump(all_perimeters, f, indent=4)
                print(f"SUCCESS: Saved zones for Camera {camera_id} to {os.path.abspath(filename)}")
                break
            else:
                print(f"Error: You must define all zones: {zone_names}")
                missing = [name for name in zone_names if name not in zones]
                print(f"Missing: {missing}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

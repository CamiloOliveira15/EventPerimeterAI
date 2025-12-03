import cv2
import numpy as np
import json
import os
from ultralytics import YOLO
from paddleocr import PaddleOCR
from datetime import datetime
import logging

# Suppress Paddle logs
logging.getLogger("ppocr").setLevel(logging.ERROR)

class AIProcessor:
    def __init__(self, perimeters_file='perimeters.json'):
        print("Loading AI Models...")
        self.model = YOLO('yolov8n.pt')
        self.ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        self.perimeters = self.load_perimeters(perimeters_file)
        self.violation_states = {} # {camera_id: {track_id: start_time}}
        
    def load_perimeters(self, filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            # Convert lists to numpy arrays for all cameras
            processed_data = {}
            for key, val in data.items():
                if isinstance(val, dict): # Camera ID keys
                    processed_data[key] = {}
                    for zone_name, points in val.items():
                        processed_data[key][zone_name] = np.array(points, dtype=np.int32)
            return processed_data
        except Exception as e:
            print(f"Error loading perimeters: {e}")
            return {}
            
    def update_perimeter(self, camera_id, zone_type, points_normalized):
        """
        Updates the perimeter for a specific camera and zone type.
        points_normalized: List of [x, y] where x, y are between 0 and 1.
        """
        camera_key = str(camera_id)
        if camera_key not in self.perimeters:
            self.perimeters[camera_key] = {}
            
        # Scale to 4K (3840x2160)
        width, height = 3840, 2160
        scaled_points = []
        for p in points_normalized:
            scaled_points.append([int(p[0] * width), int(p[1] * height)])
            
        np_points = np.array(scaled_points, dtype=np.int32)
        self.perimeters[camera_key][zone_type] = np_points
        
        self.save_perimeters()
        print(f"Updated {zone_type} for Camera {camera_id}. Points: {scaled_points}")

    def save_perimeters(self, filepath='perimeters.json'):
        # Convert numpy arrays back to lists for JSON serialization
        data_to_save = {}
        for cam_id, zones in self.perimeters.items():
            data_to_save[cam_id] = {}
            for zone_name, points in zones.items():
                data_to_save[cam_id][zone_name] = points.tolist()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            print(f"Error saving perimeters: {e}")

    def is_inside(self, point, polygon):
        return cv2.pointPolygonTest(polygon, point, False) >= 0

    def process_frame(self, frame, camera_id, check_recording=True, check_violation=True, violation_threshold=2.0):
        camera_key = str(camera_id)
        zones = self.perimeters.get(camera_key, {})
        
        recording_zone = zones.get("recording_zone") if check_recording else None
        violation_zone = zones.get("violation_zone") if check_violation else None
        
        # YOLO Tracking
        results = self.model.track(frame, persist=True, verbose=False)
        
        detections = []
        violation_alert = False
        recording_trigger = False
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xywh.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            classes = results[0].boxes.cls.int().cpu().tolist()
            xyxy_boxes = results[0].boxes.xyxy.cpu()

            for box, xyxy, track_id, cls in zip(boxes, xyxy_boxes, track_ids, classes):
                # Filter vehicles/people
                if cls not in [0, 1, 2, 3, 5, 7]:
                    continue

                x, y, w, h = box
                # Scale center point from AI resolution (640x640) to Original resolution (3840x2160)
                # This is necessary because zones are stored in 3840x2160 coordinates
                scale_x = 3840 / 640
                scale_y = 2160 / 640
                center_point = (int(x * scale_x), int(y * scale_y))
                
                # Check Recording Zone
                if recording_zone is not None and self.is_inside(center_point, recording_zone):
                    recording_trigger = True
                    # print(f"Object {track_id} inside Recording Zone")
                
                # Check Violation Zone
                is_violation = False
                duration = 0
                if violation_zone is not None and self.is_inside(center_point, violation_zone):
                    # print(f"Object {track_id} inside Violation Zone")
                    # Track violation duration
                    if camera_key not in self.violation_states:
                        self.violation_states[camera_key] = {}
                    
                    if track_id not in self.violation_states[camera_key]:
                        self.violation_states[camera_key][track_id] = datetime.now()
                    
                    duration = (datetime.now() - self.violation_states[camera_key][track_id]).total_seconds()
                    
                    if duration > violation_threshold:
                        is_violation = True
                        violation_alert = True
                else:
                    # Reset if leaves zone
                    if camera_key in self.violation_states and track_id in self.violation_states[camera_key]:
                        del self.violation_states[camera_key][track_id]

                detections.append({
                    "box": [int(c) for c in xyxy],
                    "id": track_id,
                    "class": cls,
                    "violation": is_violation,
                    "duration": duration
                })

        return detections, recording_trigger, violation_alert

    def perform_lpr(self, frame, box):
        x1, y1, x2, y2 = map(int, box)
        h, w, _ = frame.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
            
        result = self.ocr.ocr(crop, cls=False)
        if not result or not result[0]:
            return None
            
        # Extract best text
        try:
            text = result[0][0][1][0]
            conf = result[0][0][1][1]
            if conf > 0.8:
                return "".join(e for e in text if e.isalnum())
        except:
            pass
        return None

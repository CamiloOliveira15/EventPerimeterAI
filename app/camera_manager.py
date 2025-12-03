import cv2
import threading
import time
import numpy as np
from datetime import datetime
from .ai_processor import AIProcessor

class CameraStream:
    def __init__(self, camera_id, ai_processor):
        self.camera_id = camera_id
        self.ai = ai_processor
        self.stopped = False
        self.frame = None
        self.display_frame_base = None # Pre-resized frame for display
        self.latest_detections = []
        self.latest_zones = {}
        self.lock = threading.Lock()
        self.recording_lock = threading.Lock()
        
        # Initialize Camera
        self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        # Request 4K
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {camera_id}")
            self.stopped = True
            
        # Recording State
        self.recording = False
        self.out = None
        self.last_recording_time = 0
        self.recording_cooldown = 3
        
        # Control Flags
        self.is_active = True
        self.monitoring_enabled = True
        self.recording_enabled = True
        self.snapshots_enabled = True
        self.check_recording_zone = True
        self.check_violation_zone = True
        self.violation_threshold = 0.0 # Immediate alert by default as requested
        
        # Start threads
        self.t_capture = threading.Thread(target=self.capture_loop, daemon=True)
        self.t_process = threading.Thread(target=self.process_loop, daemon=True)
        self.t_capture.start()
        self.t_process.start()

    def capture_loop(self):
        while not self.stopped:
            if not self.is_active:
                time.sleep(0.1)
                continue

            ret, frame = self.cap.read()
            if not ret:
                print(f"Camera {self.camera_id} disconnected.")
                self.stopped = True
                break
            
            # Resize immediately for display (HD) to avoid cost in streaming loop
            # 4K -> 720p
            display_small = cv2.resize(frame, (1280, 720))

            with self.lock:
                self.frame = frame
                self.display_frame_base = display_small
            
            # Handle Recording (Write raw 4K frame)
            # Handle Recording (Write raw 4K frame)
            with self.recording_lock:
                if self.recording and self.out:
                    try:
                        self.out.write(frame)
                    except Exception as e:
                        print(f"Error writing frame: {e}")
                
            time.sleep(0.001)

    def process_loop(self):
        while not self.stopped:
            with self.lock:
                if self.frame is None:
                    continue
                # Copy frame for processing to avoid locking capture
                process_frame = self.frame.copy()
            
            # Resize for AI (Speed up)
            ai_frame = cv2.resize(process_frame, (640, 640))
            
            # Run AI only if monitoring is enabled
            detections = []
            rec_trigger = False
            violation = False
            
            if self.monitoring_enabled:
                detections, rec_trigger, violation = self.ai.process_frame(
                    ai_frame, 
                    self.camera_id,
                    check_recording=self.check_recording_zone,
                    check_violation=self.check_violation_zone,
                    violation_threshold=self.violation_threshold
                )
            
            # Store results for display thread
            with self.lock:
                self.latest_detections = detections
                # Zones don't change often, but good to keep synced
                self.latest_zones = self.ai.perimeters.get(str(self.camera_id), {})
            
            # Update Recording State
            # Record if Recording Zone triggered OR Violation triggered
            should_record = (rec_trigger and self.recording_enabled) or (violation and self.recording_enabled)

            if should_record:
                self.last_recording_time = time.time()
                if not self.recording:
                    self.start_recording(process_frame.shape)
            elif self.recording and (time.time() - self.last_recording_time > self.recording_cooldown):
                self.stop_recording()
            
            # Need original dimensions for scaling calculations?
            # We know original is 4K (3840x2160) and display is 1280x720.
            # Ratios are constant.

            # Handle Snapshots (if violation and enabled)
            if violation and self.snapshots_enabled:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snap_name = f"violation_cam{self.camera_id}_{timestamp}.jpg"
                cv2.imwrite(snap_name, ai_frame)
                print(f"Cam {self.camera_id}: Saved snapshot {snap_name}")

            # Throttle AI loop slightly
            time.sleep(0.01)

    def start_recording(self, shape):
        with self.recording_lock:
            self.recording = True
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_cam{self.camera_id}_{timestamp}.avi"
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            # We record at 30 FPS (assuming capture is keeping up)
            self.out = cv2.VideoWriter(filename, fourcc, 30.0, (shape[1], shape[0]))
            print(f"Cam {self.camera_id}: Started recording {filename}")

    def stop_recording(self):
        with self.recording_lock:
            self.recording = False
            if self.out:
                self.out.release()
                self.out = None
            print(f"Cam {self.camera_id}: Stopped recording")
            
    def get_jpeg(self):
        # Get latest pre-resized frame
        with self.lock:
            if self.display_frame_base is None:
                return None
            # Copy the small frame (fast)
            display_frame = self.display_frame_base.copy()
            detections = self.latest_detections
            zones = self.latest_zones
            
        # Draw Overlays
        # Zones: 4K -> HD
        # 1280 / 3840 = 0.333
        # 720 / 2160 = 0.333
        disp_scale_x = 1280 / 3840
        disp_scale_y = 720 / 2160
        
        for name, points in zones.items():
            # Skip drawing if zone is disabled
            if "recording" in name and not self.check_recording_zone:
                continue
            if "violation" in name and not self.check_violation_zone:
                continue

            disp_points = (points * [disp_scale_x, disp_scale_y]).astype(np.int32)
            color = (255, 0, 0) if "recording" in name else (0, 0, 255)
            cv2.polylines(display_frame, [disp_points], True, color, 2)

        # Detections: 640 -> HD
        # 1280 / 640 = 2.0
        # 720 / 640 = 1.125
        det_scale_x = 1280 / 640
        det_scale_y = 720 / 640

        for det in detections:
            x1, y1, x2, y2 = det['box']
            dx1 = int(x1 * det_scale_x)
            dy1 = int(y1 * det_scale_y)
            dx2 = int(x2 * det_scale_x)
            dy2 = int(y2 * det_scale_y)
            
            color = (0, 0, 255) if det['violation'] else (0, 255, 0)
            cv2.rectangle(display_frame, (dx1, dy1), (dx2, dy2), color, 2)
            
            if det['violation']:
                cv2.putText(display_frame, "VIOLATION", (dx1, dy1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)

        # Encode
        # Use slightly lower quality for speed if needed, 80 is good balance
        ret, jpeg = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return jpeg.tobytes()

    def stop(self):
        self.stopped = True
        self.t_capture.join()
        self.t_process.join()
        self.cap.release()

    def toggle_monitoring(self, state: bool):
        self.monitoring_enabled = state
        print(f"Cam {self.camera_id}: Monitoring set to {state}")

    def toggle_recording(self, state: bool):
        self.recording_enabled = state
        if not state and self.recording:
            self.stop_recording()
        print(f"Cam {self.camera_id}: Recording set to {state}")

    def toggle_snapshots(self, state: bool):
        self.snapshots_enabled = state
        print(f"Cam {self.camera_id}: Snapshots set to {state}")

    def toggle_active(self, state: bool):
        self.is_active = state
        print(f"Cam {self.camera_id}: Active set to {state}")

    def reset_defaults(self):
        self.is_active = True
        self.monitoring_enabled = True
        self.recording_enabled = True
        self.snapshots_enabled = True
        self.check_recording_zone = True
        self.check_violation_zone = True
        self.violation_threshold = 0.0
        print(f"Cam {self.camera_id}: Reset to defaults")

    def toggle_zone_recording(self, state: bool):
        self.check_recording_zone = state
        print(f"Cam {self.camera_id}: Recording Zone set to {state}")

    def toggle_zone_violation(self, state: bool):
        self.check_violation_zone = state
        print(f"Cam {self.camera_id}: Violation Zone set to {state}")


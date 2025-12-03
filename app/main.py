from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import os
import signal
import threading
import time
from contextlib import asynccontextmanager
from .camera_manager import CameraStream
from .ai_processor import AIProcessor
from pydantic import BaseModel
from typing import List

# Global State
cameras = {}
ai_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global ai_processor
    ai_processor = AIProcessor()
    
    # Load configured cameras from perimeters.json
    try:
        with open('perimeters.json', 'r') as f:
            data = json.load(f)
            for key in data.keys():
                if key.isdigit():
                    cam_id = int(key)
                    print(f"Initializing Camera {cam_id}...")
                    cameras[cam_id] = CameraStream(cam_id, ai_processor)
    except Exception as e:
        print(f"Error loading config: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down cameras...")
    for cam in cameras.values():
        cam.stop()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "cameras": cameras.keys()})

def generate_frames(camera_id):
    cam = cameras.get(camera_id)
    if not cam:
        return
    while True:
        frame = cam.get_jpeg()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            pass # Wait for frame

@app.get("/video_feed/{camera_id}")
async def video_feed(camera_id: int):
    return StreamingResponse(generate_frames(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/shutdown")
async def shutdown():
    print("Shutdown requested via UI...")
    # Schedule shutdown in a separate thread to allow response to return
    def kill_server():
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)
    
    threading.Thread(target=kill_server).start()
    return {"status": "Shutting down..."}

@app.post("/camera/{camera_id}/{action}/{state}")
async def control_camera(camera_id: int, action: str, state: str):
    cam = cameras.get(camera_id)
    if not cam:
        return {"error": "Camera not found"}
    
    is_enabled = (state.lower() == "true")
    
    if action == "monitoring":
        cam.toggle_monitoring(is_enabled)
    elif action == "recording":
        cam.toggle_recording(is_enabled)
    elif action == "snapshots":
        cam.toggle_snapshots(is_enabled)
    elif action == "active":
        cam.toggle_active(is_enabled)
    elif action == "zone_recording":
        cam.toggle_zone_recording(is_enabled)
    elif action == "zone_violation":
        cam.toggle_zone_violation(is_enabled)
    elif action == "reset":
        cam.reset_defaults()
    else:
        return {"error": "Invalid action"}
    
    return {"status": "ok", "action": action, "state": is_enabled}

class ZoneUpdate(BaseModel):
    type: str # "recording_zone" or "violation_zone"
    points: List[List[float]] # Normalized coordinates [[0.1, 0.1], ...]

@app.post("/camera/{camera_id}/update_zone")
async def update_zone(camera_id: int, zone_data: ZoneUpdate):
    try:
        ai_processor.update_perimeter(camera_id, zone_data.type, zone_data.points)
        # Update the camera's local cache of zones immediately
        if camera_id in cameras:
            cameras[camera_id].latest_zones = ai_processor.perimeters.get(str(camera_id), {})
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

# EventPerimeterAI

**EventPerimeterAI** is an advanced intelligent monitoring system designed for real-time surveillance, digital perimeter security, and License Plate Recognition (LPR). It features a modern Web Dashboard for continuous monitoring of multiple cameras with minimal latency.

## 🚀 Features

*   **Web Dashboard**: A responsive, dark-themed web interface to monitor multiple cameras simultaneously.
*   **Minimal Freezing**: Decoupled architecture ensures smooth video playback even during heavy AI processing.
*   **Digital Perimeters**: Define "Recording Zones" (Blue) and "Violation Zones" (Red) for each camera.
*   **Violation Detection**: Automatically detects objects (people, vehicles) staying in a violation zone for too long.
*   **License Plate Recognition (LPR)**: Captures and reads license plates of vehicles involved in violations using PaddleOCR.
*   **Automatic Recording**:
    *   **Video**: Records in 4K (if available) when activity is detected.
    *   **Audio**: Captures audio alongside video.
    *   **Smart Merging**: Automatically merges video and audio into a single `.mp4` file with corrected playback speed.
*   **Multi-Camera Support**: Scalable design supporting multiple camera feeds.

## 🛠️ Tech Stack

*   **Backend**: Python 3.10+, FastAPI
*   **AI**: YOLOv8 (Object Tracking), PaddleOCR (LPR)
*   **Video Processing**: OpenCV, MoviePy
*   **Frontend**: HTML5, JavaScript, CSS (Jinja2 Templates)

## 📦 Installation

### Prerequisites
*   Python 3.10+
*   A webcam (or multiple)

### Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/CamilloOliveira15/EventPerimeterAI.git
    cd EventPerimeterAI
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Ensure you have `fastapi`, `uvicorn`, `ultralytics`, `paddlepaddle`, `paddleocr`, `opencv-python`, `moviepy`, and `sounddevice` installed.*

## 🚦 Usage

### 1. Define Perimeters
Before running the dashboard, you must define the zones for each camera.

**For Camera 0:**
```bash
python configure_zones.py --camera 0
```
*   **Left Click**: Add points.
*   **'n'**: Confirm current zone (Recording -> Violation).
*   **'s'**: Save configuration.

**For Camera 1 (if available):**
```bash
python configure_zones.py --camera 1
```

### 2. Run the Dashboard
Start the central monitoring server:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Access the Monitor
Open your web browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

You will see the live feed from all configured cameras. The system will automatically record and log violations in the background.

## 📂 Project Structure

```text
EventPerimeterAI/
├── app/
│   ├── main.py            # FastAPI Server Entry Point
│   ├── camera_manager.py  # Threaded Camera Handling
│   ├── ai_processor.py    # AI Logic (YOLO + OCR)
│   ├── templates/
│   │   └── index.html     # Web Dashboard UI
│   └── static/            # CSS/JS Assets
├── configure_zones.py     # Tool to define zones
├── perimeters.json        # Zone Configurations
└── requirements.txt       # Project Dependencies
```

import asyncio
import json
import base64
import cv2
import numpy as np
import re
import logging
from ultralytics import YOLO
from paddleocr import PaddleOCR
from src.infrastructure.redis_client import get_redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LPRWorker:
    def __init__(self):
        self.redis = None
        self.running = False
        
        # Initialize Models
        # Note: In production, use a model fine-tuned for license plates
        logger.info("Loading YOLOv8 model...")
        self.detector = YOLO("yolov8n.pt") 
        
        logger.info("Loading PaddleOCR...")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        
        # Regex for Brazilian Plates
        # Mercosul: ABC1D23
        # Old: ABC1234
        self.plate_pattern = re.compile(r'^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$')

    async def start(self):
        self.redis = await get_redis_client()
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("video_frames")
        self.running = True
        
        logger.info("LPR Worker started. Waiting for frames...")

        try:
            async for message in pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'message':
                    await self.process_frame(message['data'])
        except Exception as e:
            logger.error(f"Error in LPR Worker: {e}")

    async def process_frame(self, message_data):
        try:
            data = json.loads(message_data)
            camera_id = data['camera_id']
            timestamp = data['timestamp']
            jpg_as_text = data['frame']

            # Decode image
            jpg_original = base64.b64decode(jpg_as_text)
            jpg_as_np = np.frombuffer(jpg_original, dtype=np.uint8)
            frame = cv2.imdecode(jpg_as_np, flags=1)

            # 1. Detect Objects (Looking for cars/plates)
            # For this demo using yolov8n, we might detect 'car' (class 2)
            # In a real scenario, we'd detect 'license_plate' directly
            results = self.detector(frame, verbose=False)
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Check if it's a car (class 2 in COCO) or plate if custom model
                    # For now, let's assume we crop anything that looks like a vehicle 
                    # and try to find text, or ideally we have a plate detector.
                    # Simplified: Just run OCR on the whole frame or large crops? 
                    # No, that's slow. 
                    # Let's assume we are detecting 'car' and then running OCR on the car crop 
                    # (not ideal) or we assume the model detects plates.
                    
                    # Placeholder logic: If confidence > 0.5
                    if box.conf[0] > 0.5:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Crop
                        roi = frame[y1:y2, x1:x2]
                        if roi.size == 0:
                            continue

                        # 2. OCR
                        ocr_result = self.ocr.ocr(roi, cls=True)
                        
                        if ocr_result and ocr_result[0]:
                            for line in ocr_result[0]:
                                text = line[1][0].upper().replace("-", "").replace(" ", "")
                                confidence = line[1][1]
                                
                                # 3. Validate
                                if self.validate_plate(text):
                                    logger.info(f"MATCH FOUND: {text} on {camera_id} (Conf: {confidence:.2f})")
                                    # TODO: Publish event to DB/API
                                    
        except Exception as e:
            logger.error(f"Frame processing error: {e}")

    def validate_plate(self, text):
        # Basic cleanup
        clean_text = ''.join(e for e in text if e.isalnum())
        return bool(self.plate_pattern.match(clean_text))

    def stop(self):
        self.running = False

if __name__ == "__main__":
    worker = LPRWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        worker.stop()

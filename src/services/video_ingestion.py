import cv2
import asyncio
import base64
import json
import time
import logging
from src.infrastructure.redis_client import get_redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoIngestionService:
    def __init__(self, camera_id: str, source: str | int, fps_limit: int = 5):
        self.camera_id = camera_id
        self.source = source
        self.fps_limit = fps_limit
        self.redis = None
        self.running = False

    async def start(self):
        self.redis = await get_redis_client()
        self.running = True
        
        logger.info(f"Starting ingestion for camera {self.camera_id} from source {self.source}")
        
        # Open video source
        cap = cv2.VideoCapture(self.source)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video source: {self.source}")
            return

        frame_interval = 1.0 / self.fps_limit
        last_frame_time = 0

        try:
            while self.running:
                current_time = time.time()
                ret, frame = cap.read()

                if not ret:
                    logger.warning(f"Failed to read frame from {self.source}. Retrying...")
                    await asyncio.sleep(1)
                    # Reconnect logic could go here
                    cap.release()
                    cap = cv2.VideoCapture(self.source)
                    continue

                # Rate limiting
                if current_time - last_frame_time < frame_interval:
                    await asyncio.sleep(0.01)
                    continue

                last_frame_time = current_time

                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')

                # Create message payload
                payload = {
                    "camera_id": self.camera_id,
                    "timestamp": current_time,
                    "frame": jpg_as_text
                }

                # Publish to Redis channel 'video_frames'
                await self.redis.publish("video_frames", json.dumps(payload))
                
                # logger.debug(f"Published frame from {self.camera_id}")

        except Exception as e:
            logger.error(f"Error in video ingestion: {e}")
        finally:
            cap.release()
            logger.info(f"Stopped ingestion for camera {self.camera_id}")

    def stop(self):
        self.running = False

# Example usage (can be run directly for testing)
if __name__ == "__main__":
    async def main():
        # Use 0 for webcam or RTSP URL
        service = VideoIngestionService(camera_id="cam_01", source=0)
        try:
            await service.start()
        except KeyboardInterrupt:
            service.stop()

    asyncio.run(main())

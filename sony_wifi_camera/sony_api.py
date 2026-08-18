"""
Sony Camera Remote API Implementation
HTTP 기반 Sony 카메라 원격 제어 API (A6700, A7IV 등 최신 카메라 지원)

Sony Camera Remote API는 HTTP/JSON 기반으로 동작합니다.
"""

import requests
import json
import time
import threading
import logging
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraState(Enum):
    """Camera connection state"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class CameraInfo:
    """Camera information"""
    model: str = ""
    firmware: str = ""
    api_version: str = ""
    available_apis: List[str] = None

    def __post_init__(self):
        if self.available_apis is None:
            self.available_apis = []


class SonyCameraAPI:
    """
    Sony Camera Remote API Client

    HTTP/JSON 기반 API로 최신 Sony 카메라 (A6700, A7IV 등) 지원
    """

    DEFAULT_PORT = 8080

    def __init__(self, ip_address: str, port: int = 8080):
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}/sony"
        self.session = requests.Session()
        self.session.timeout = 10

        self.connected = False
        self.camera_info = CameraInfo()
        self.state = CameraState.DISCONNECTED

        self._liveview_url: Optional[str] = None
        self._liveview_thread: Optional[threading.Thread] = None
        self._liveview_running = False
        self._liveview_callback: Optional[Callable] = None
        self._event_callback: Optional[Callable] = None

        # API endpoints
        self.endpoints = {
            'camera': f"{self.base_url}/camera",
            'avContent': f"{self.base_url}/avContent",
            'system': f"{self.base_url}/system",
        }

    def _call_api(self, endpoint: str, method: str, params: list = None,
                  version: str = "1.0", id_num: int = 1) -> Optional[Dict]:
        """
        Call Sony Camera API

        Args:
            endpoint: API endpoint (camera, avContent, system)
            method: API method name
            params: Method parameters
            version: API version
            id_num: Request ID

        Returns:
            API response dict or None on error
        """
        if params is None:
            params = []

        url = self.endpoints.get(endpoint, f"{self.base_url}/{endpoint}")

        payload = {
            "method": method,
            "params": params,
            "id": id_num,
            "version": version
        }

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error = result["error"]
                logger.error(f"API error: {error}")
                return None

            return result.get("result", [])

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return None
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to camera

        Returns:
            True if connection successful
        """
        self.state = CameraState.CONNECTING
        logger.info(f"Connecting to camera at {self.ip_address}:{self.port}")

        try:
            # Get available API list
            result = self._call_api("camera", "getAvailableApiList")

            if result is None:
                # Try system endpoint
                result = self._call_api("system", "getVersions")
                if result is None:
                    self.state = CameraState.ERROR
                    logger.error("Failed to connect - no API response")
                    return False

            # Get camera info
            self._get_camera_info()

            # Start rec mode if needed
            self._start_rec_mode()

            self.connected = True
            self.state = CameraState.CONNECTED
            logger.info(f"Connected to {self.camera_info.model}")
            return True

        except Exception as e:
            self.state = CameraState.ERROR
            logger.error(f"Connection failed: {e}")
            return False

    def _get_camera_info(self):
        """Get camera information"""
        # Get available APIs
        result = self._call_api("camera", "getAvailableApiList")
        if result and len(result) > 0:
            self.camera_info.available_apis = result[0]

        # Get application info
        result = self._call_api("system", "getApplicationInfo")
        if result and len(result) > 0:
            info = result[0] if isinstance(result[0], dict) else {}
            self.camera_info.model = info.get("name", "Sony Camera")
            self.camera_info.firmware = info.get("version", "")

        # Get versions
        result = self._call_api("camera", "getVersions")
        if result and len(result) > 0:
            self.camera_info.api_version = str(result[0])

    def _start_rec_mode(self):
        """Start recording mode (required for some operations)"""
        if "startRecMode" in self.camera_info.available_apis:
            result = self._call_api("camera", "startRecMode")
            if result is not None:
                logger.info("Rec mode started")
                time.sleep(1)  # Wait for camera to be ready

    def disconnect(self):
        """Disconnect from camera"""
        self.stop_liveview()

        if self.connected:
            # Stop rec mode
            if "stopRecMode" in self.camera_info.available_apis:
                self._call_api("camera", "stopRecMode")

        self.connected = False
        self.state = CameraState.DISCONNECTED
        logger.info("Disconnected from camera")

    def capture(self) -> Optional[str]:
        """
        Take a photo

        Returns:
            URL of captured image or None on error
        """
        if not self.connected:
            logger.error("Not connected")
            return None

        logger.info("Taking photo...")

        # actTakePicture
        result = self._call_api("camera", "actTakePicture")

        if result and len(result) > 0:
            # Result contains list of image URLs
            urls = result[0]
            if urls and len(urls) > 0:
                image_url = urls[0]
                logger.info(f"Photo captured: {image_url}")
                return image_url

        logger.error("Capture failed")
        return None

    def capture_and_download(self, save_path: str) -> bool:
        """
        Take a photo and download it

        Args:
            save_path: Path to save the image

        Returns:
            True if successful
        """
        image_url = self.capture()

        if image_url:
            try:
                response = self.session.get(image_url, timeout=30)
                response.raise_for_status()

                with open(save_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Image saved to {save_path}")
                return True

            except Exception as e:
                logger.error(f"Download failed: {e}")
                return False

        return False

    def start_liveview(self, callback: Callable[[bytes], None] = None) -> bool:
        """
        Start LiveView streaming

        Args:
            callback: Function to receive JPEG frames

        Returns:
            True if started successfully
        """
        if not self.connected:
            return False

        if self._liveview_running:
            return True

        # Get LiveView URL
        result = self._call_api("camera", "startLiveview")

        if result and len(result) > 0:
            self._liveview_url = result[0]
            logger.info(f"LiveView URL: {self._liveview_url}")

            self._liveview_callback = callback
            self._liveview_running = True

            self._liveview_thread = threading.Thread(
                target=self._liveview_loop,
                daemon=True
            )
            self._liveview_thread.start()

            return True

        logger.error("Failed to start LiveView")
        return False

    def _liveview_loop(self):
        """LiveView streaming loop"""
        try:
            response = self.session.get(self._liveview_url, stream=True, timeout=30)

            buffer = b''

            for chunk in response.iter_content(chunk_size=1024):
                if not self._liveview_running:
                    break

                buffer += chunk

                # Find JPEG start (FFD8) and end (FFD9)
                while True:
                    start = buffer.find(b'\xff\xd8')
                    if start == -1:
                        buffer = b''
                        break

                    end = buffer.find(b'\xff\xd9', start)
                    if end == -1:
                        # Keep searching, need more data
                        if start > 0:
                            buffer = buffer[start:]
                        break

                    # Extract JPEG frame
                    frame = buffer[start:end+2]
                    buffer = buffer[end+2:]

                    if self._liveview_callback:
                        try:
                            self._liveview_callback(frame)
                        except Exception as e:
                            logger.debug(f"Callback error: {e}")

        except Exception as e:
            logger.error(f"LiveView error: {e}")
        finally:
            self._liveview_running = False

    def stop_liveview(self):
        """Stop LiveView streaming"""
        self._liveview_running = False

        if self._liveview_thread:
            self._liveview_thread.join(timeout=2)
            self._liveview_thread = None

        if self.connected and "stopLiveview" in self.camera_info.available_apis:
            self._call_api("camera", "stopLiveview")

        self._liveview_url = None
        logger.info("LiveView stopped")

    def get_battery_level(self) -> Optional[int]:
        """Get battery level percentage"""
        result = self._call_api("system", "getEvent", [False])

        if result:
            for item in result:
                if isinstance(item, dict) and "batteryInfo" in item:
                    battery_info = item["batteryInfo"]
                    if battery_info and len(battery_info) > 0:
                        level = battery_info[0].get("levelNumer", -1)
                        denom = battery_info[0].get("levelDenom", 1)
                        if level >= 0 and denom > 0:
                            return int((level / denom) * 100)

        return None

    def get_available_settings(self) -> Dict:
        """Get available camera settings"""
        settings = {}

        # Get shoot mode
        result = self._call_api("camera", "getAvailableShootMode")
        if result and len(result) >= 2:
            settings["shootMode"] = {
                "current": result[0],
                "available": result[1]
            }

        # Get exposure mode
        result = self._call_api("camera", "getAvailableExposureMode")
        if result and len(result) >= 2:
            settings["exposureMode"] = {
                "current": result[0],
                "available": result[1]
            }

        # Get F number
        result = self._call_api("camera", "getAvailableFNumber")
        if result and len(result) >= 2:
            settings["fNumber"] = {
                "current": result[0],
                "available": result[1]
            }

        # Get shutter speed
        result = self._call_api("camera", "getAvailableShutterSpeed")
        if result and len(result) >= 2:
            settings["shutterSpeed"] = {
                "current": result[0],
                "available": result[1]
            }

        # Get ISO
        result = self._call_api("camera", "getAvailableIsoSpeedRate")
        if result and len(result) >= 2:
            settings["iso"] = {
                "current": result[0],
                "available": result[1]
            }

        return settings

    def set_shoot_mode(self, mode: str) -> bool:
        """Set shoot mode (still, movie, etc.)"""
        result = self._call_api("camera", "setShootMode", [mode])
        return result is not None

    def set_exposure_mode(self, mode: str) -> bool:
        """Set exposure mode (Program Auto, Aperture, Shutter, Manual)"""
        result = self._call_api("camera", "setExposureMode", [mode])
        return result is not None

    def set_f_number(self, f_number: str) -> bool:
        """Set F number (aperture)"""
        result = self._call_api("camera", "setFNumber", [f_number])
        return result is not None

    def set_shutter_speed(self, speed: str) -> bool:
        """Set shutter speed"""
        result = self._call_api("camera", "setShutterSpeed", [speed])
        return result is not None

    def set_iso(self, iso: str) -> bool:
        """Set ISO"""
        result = self._call_api("camera", "setIsoSpeedRate", [iso])
        return result is not None

    def half_press_shutter(self) -> bool:
        """Half press shutter (AF)"""
        result = self._call_api("camera", "actHalfPressShutter")
        return result is not None

    def cancel_half_press_shutter(self) -> bool:
        """Cancel half press shutter"""
        result = self._call_api("camera", "cancelHalfPressShutter")
        return result is not None

    def set_event_callback(self, callback: Callable):
        """Set callback for camera events"""
        self._event_callback = callback

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Test
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python sony_api.py <camera_ip>")
        sys.exit(1)

    camera_ip = sys.argv[1]

    camera = SonyCameraAPI(camera_ip)

    if camera.connect():
        print(f"Connected to {camera.camera_info.model}")
        print(f"Available APIs: {camera.camera_info.available_apis}")

        # Get battery
        battery = camera.get_battery_level()
        if battery:
            print(f"Battery: {battery}%")

        # Get settings
        settings = camera.get_available_settings()
        print(f"Settings: {json.dumps(settings, indent=2)}")

        input("Press Enter to take a photo...")

        url = camera.capture()
        if url:
            print(f"Photo URL: {url}")

        camera.disconnect()
    else:
        print("Connection failed")

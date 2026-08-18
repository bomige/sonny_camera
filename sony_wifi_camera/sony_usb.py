"""
Sony Camera USB Connection Module
pysonycam 라이브러리를 활용한 USB 카메라 연결

Windows에서 사용하려면 Zadig로 WinUSB 드라이버 설치 필요
"""

import sys
import logging
from typing import Optional, Callable, Generator
from dataclasses import dataclass
from enum import Enum

# Add pysonycam to path
sys.path.insert(0, r'D:\code_ex\sonny\pysonycam')

try:
    from pysonycam import SonyCamera
    from pysonycam.constants import (
        DeviceProperty, ExposureMode, WhiteBalance,
        FocusMode, SaveMedia, ISO_TABLE, F_NUMBER_TABLE,
        SHUTTER_SPEED_TABLE
    )
    PYSONYCAM_AVAILABLE = True
except ImportError as e:
    PYSONYCAM_AVAILABLE = False
    print(f"Warning: pysonycam not available: {e}")

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
    serial: str = ""
    firmware: str = ""
    battery: Optional[int] = None


class SonyUSBCamera:
    """
    Sony Camera USB Connection Handler

    Uses pysonycam library for USB PTP communication
    """

    def __init__(self):
        self._camera: Optional[SonyCamera] = None
        self.connected = False
        self.state = CameraState.DISCONNECTED
        self.camera_info = CameraInfo()
        self._liveview_callback: Optional[Callable] = None
        self._liveview_running = False

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to camera via USB

        Returns:
            True if connection successful
        """
        if not PYSONYCAM_AVAILABLE:
            logger.error("pysonycam library not available")
            return False

        self.state = CameraState.CONNECTING
        logger.info("Connecting to Sony camera via USB...")

        try:
            self._camera = SonyCamera()
            self._camera.connect()
            self._camera.authenticate()

            # Get camera info
            self._get_camera_info()

            self.connected = True
            self.state = CameraState.CONNECTED
            logger.info(f"Connected to {self.camera_info.model}")
            return True

        except Exception as e:
            self.state = CameraState.ERROR
            logger.error(f"Connection failed: {e}")
            self._camera = None
            return False

    def _get_camera_info(self):
        """Get camera information"""
        if not self._camera:
            return

        try:
            # Get all properties
            props = self._camera.get_all_properties()

            # Model name
            if 0x5001 in props:  # ManufacturerInfo
                self.camera_info.model = "Sony Camera"

            # Battery level
            battery = self._camera.battery_level
            if battery:
                self.camera_info.battery = battery.current_value

        except Exception as e:
            logger.debug(f"Failed to get camera info: {e}")

    def disconnect(self):
        """Disconnect from camera"""
        self._liveview_running = False

        if self._camera:
            try:
                self._camera.disconnect()
            except:
                pass
            self._camera = None

        self.connected = False
        self.state = CameraState.DISCONNECTED
        logger.info("Disconnected from camera")

    def capture(self, save_path: str = None) -> Optional[bytes]:
        """
        Capture a photo

        Args:
            save_path: Optional path to save the image

        Returns:
            Image data as bytes, or None on error
        """
        if not self.connected or not self._camera:
            logger.error("Not connected")
            return None

        try:
            logger.info("Capturing photo...")

            # Set to still mode
            self._camera.set_mode("still")

            # Capture
            if save_path:
                data = self._camera.capture(save_path)
                logger.info(f"Photo saved to {save_path}")
            else:
                data = self._camera.capture()
                logger.info("Photo captured")

            return data

        except Exception as e:
            logger.error(f"Capture failed: {e}")
            return None

    def get_liveview_frame(self) -> Optional[bytes]:
        """
        Get a single LiveView frame

        Returns:
            JPEG image data or None
        """
        if not self.connected or not self._camera:
            return None

        try:
            return self._camera.get_liveview_frame()
        except Exception as e:
            logger.debug(f"LiveView frame error: {e}")
            return None

    def start_liveview(self, callback: Callable[[bytes], None] = None) -> bool:
        """
        Start LiveView streaming

        Args:
            callback: Function to receive JPEG frames

        Returns:
            True if started successfully
        """
        if not self.connected or not self._camera:
            return False

        self._liveview_callback = callback
        self._liveview_running = True

        # For USB, we don't need to start anything special
        # Just return True, the thread will poll get_liveview_frame()
        return True

    def stop_liveview(self):
        """Stop LiveView streaming"""
        self._liveview_running = False
        self._liveview_callback = None

    def liveview_stream(self, count: int = None) -> Generator[bytes, None, None]:
        """
        Generator for LiveView frames

        Args:
            count: Number of frames to yield (None for infinite)

        Yields:
            JPEG frame data
        """
        if not self.connected or not self._camera:
            return

        try:
            for frame in self._camera.liveview_stream(count=count):
                yield frame
        except Exception as e:
            logger.error(f"LiveView stream error: {e}")

    def get_battery_level(self) -> Optional[int]:
        """Get battery level percentage"""
        if not self.connected or not self._camera:
            return None

        try:
            battery = self._camera.battery_level
            if battery:
                return battery.current_value
        except:
            pass
        return None

    def get_device_info(self) -> dict:
        """Get device information"""
        return {
            'model': self.camera_info.model,
            'serial': self.camera_info.serial,
            'firmware': self.camera_info.firmware
        }

    def set_exposure_mode(self, mode: str) -> bool:
        """Set exposure mode (P, A, S, M, Auto)"""
        if not self.connected or not self._camera:
            return False

        mode_map = {
            'P': ExposureMode.PROGRAM_AUTO,
            'A': ExposureMode.APERTURE_PRIORITY,
            'S': ExposureMode.SHUTTER_PRIORITY,
            'M': ExposureMode.MANUAL,
            'Auto': ExposureMode.INTELLIGENT_AUTO,
        }

        if mode in mode_map:
            try:
                self._camera.set_exposure_mode(mode_map[mode])
                return True
            except:
                pass
        return False

    def set_iso(self, iso: int) -> bool:
        """Set ISO value"""
        if not self.connected or not self._camera:
            return False

        try:
            self._camera.set_iso(iso)
            return True
        except:
            return False

    def get_available_settings(self) -> dict:
        """Get available camera settings"""
        if not self.connected or not self._camera:
            return {}

        settings = {}
        try:
            props = self._camera.get_all_properties()

            # ISO
            if DeviceProperty.ISO in props:
                iso_prop = props[DeviceProperty.ISO]
                settings['iso'] = {
                    'current': ISO_TABLE.get(iso_prop.current_value, str(iso_prop.current_value)),
                    'available': [ISO_TABLE.get(v, str(v)) for v in iso_prop.supported_values]
                }

            # F-number
            if DeviceProperty.F_NUMBER in props:
                f_prop = props[DeviceProperty.F_NUMBER]
                settings['fNumber'] = {
                    'current': F_NUMBER_TABLE.get(f_prop.current_value, str(f_prop.current_value)),
                    'available': [F_NUMBER_TABLE.get(v, str(v)) for v in f_prop.supported_values]
                }

            # Shutter speed
            if DeviceProperty.SHUTTER_SPEED in props:
                ss_prop = props[DeviceProperty.SHUTTER_SPEED]
                settings['shutterSpeed'] = {
                    'current': SHUTTER_SPEED_TABLE.get(ss_prop.current_value, str(ss_prop.current_value)),
                    'available': [SHUTTER_SPEED_TABLE.get(v, str(v)) for v in ss_prop.supported_values]
                }

        except Exception as e:
            logger.error(f"Failed to get settings: {e}")

        return settings

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Test
if __name__ == "__main__":
    if not PYSONYCAM_AVAILABLE:
        print("pysonycam not available. Please install it first.")
        print("cd D:\\code_ex\\sonny\\pysonycam && pip install -e .")
        sys.exit(1)

    camera = SonyUSBCamera()

    if camera.connect():
        print(f"Connected to {camera.camera_info.model}")

        # Get battery
        battery = camera.get_battery_level()
        if battery:
            print(f"Battery: {battery}%")

        # Get settings
        settings = camera.get_available_settings()
        print(f"Settings: {settings}")

        input("Press Enter to capture...")
        camera.capture("test_photo.jpg")

        camera.disconnect()
    else:
        print("Connection failed")
        print("\nTroubleshooting:")
        print("1. Connect camera via USB")
        print("2. Set camera to PC Remote mode")
        print("3. Install WinUSB driver using Zadig (Windows)")

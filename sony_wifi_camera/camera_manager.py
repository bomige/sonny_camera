"""
Camera Manager
여러 대의 카메라를 관리하는 매니저
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from ptp_ip import SonyPtpIpCamera

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
    id: str
    ip: str
    port: int
    name: str = ""
    model: str = ""
    state: CameraState = CameraState.DISCONNECTED
    battery: Optional[int] = None
    camera: Optional[SonyPtpIpCamera] = field(default=None, repr=False)
    error_message: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.ip}:{self.port}"
        if not self.name:
            self.name = f"Camera ({self.ip})"


class CameraManager:
    """
    Multi-camera manager

    여러 대의 Sony 카메라를 동시에 관리하고 제어합니다.
    """

    def __init__(self):
        self._cameras: Dict[str, CameraInfo] = {}
        self._lock = threading.Lock()
        self._state_callback: Optional[Callable] = None

    @property
    def cameras(self) -> List[CameraInfo]:
        """Get all cameras"""
        with self._lock:
            return list(self._cameras.values())

    @property
    def connected_cameras(self) -> List[CameraInfo]:
        """Get connected cameras only"""
        with self._lock:
            return [c for c in self._cameras.values() if c.state == CameraState.CONNECTED]

    def set_state_callback(self, callback: Callable[[str, CameraState], None]):
        """Set callback for state changes"""
        self._state_callback = callback

    def add_camera(self, ip: str, port: int = 15740, name: str = "") -> CameraInfo:
        """
        Add a camera to manage

        Args:
            ip: Camera IP address
            port: PTP-IP port (default 15740)
            name: Optional camera name

        Returns:
            CameraInfo object
        """
        camera_id = f"{ip}:{port}"

        with self._lock:
            if camera_id in self._cameras:
                return self._cameras[camera_id]

            info = CameraInfo(
                id=camera_id,
                ip=ip,
                port=port,
                name=name or f"Camera ({ip})"
            )
            self._cameras[camera_id] = info
            logger.info(f"Added camera: {info.name}")
            return info

    def remove_camera(self, camera_id: str) -> bool:
        """
        Remove a camera

        Args:
            camera_id: Camera ID

        Returns:
            True if removed
        """
        with self._lock:
            if camera_id not in self._cameras:
                return False

            info = self._cameras[camera_id]

            # Disconnect if connected
            if info.camera and info.camera.connected:
                info.camera.disconnect()

            del self._cameras[camera_id]
            logger.info(f"Removed camera: {info.name}")
            return True

    def connect(self, camera_id: str, timeout: float = 10.0) -> bool:
        """
        Connect to a camera

        Args:
            camera_id: Camera ID
            timeout: Connection timeout

        Returns:
            True if connected
        """
        with self._lock:
            if camera_id not in self._cameras:
                return False
            info = self._cameras[camera_id]

        self._update_state(camera_id, CameraState.CONNECTING)

        try:
            camera = SonyPtpIpCamera(info.ip, info.port)
            success = camera.connect(timeout=timeout)

            if success:
                with self._lock:
                    info.camera = camera
                    info.model = "Sony Camera"  # TODO: Get from device info

                self._update_state(camera_id, CameraState.CONNECTED)
                logger.info(f"Connected to {info.name}")
                return True
            else:
                self._update_state(camera_id, CameraState.ERROR, "Connection failed")
                return False

        except Exception as e:
            self._update_state(camera_id, CameraState.ERROR, str(e))
            return False

    def disconnect(self, camera_id: str) -> bool:
        """
        Disconnect from a camera

        Args:
            camera_id: Camera ID

        Returns:
            True if disconnected
        """
        with self._lock:
            if camera_id not in self._cameras:
                return False
            info = self._cameras[camera_id]

        if info.camera:
            info.camera.disconnect()
            with self._lock:
                info.camera = None

        self._update_state(camera_id, CameraState.DISCONNECTED)
        logger.info(f"Disconnected from {info.name}")
        return True

    def connect_all(self, timeout: float = 10.0) -> Dict[str, bool]:
        """
        Connect to all cameras

        Args:
            timeout: Connection timeout per camera

        Returns:
            Dict of camera_id -> success
        """
        results = {}
        threads = []

        for camera_id in list(self._cameras.keys()):
            t = threading.Thread(
                target=lambda cid: results.update({cid: self.connect(cid, timeout)}),
                args=(camera_id,)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return results

    def disconnect_all(self):
        """Disconnect from all cameras"""
        for camera_id in list(self._cameras.keys()):
            self.disconnect(camera_id)

    def capture(self, camera_id: str) -> bool:
        """
        Capture photo on a camera

        Args:
            camera_id: Camera ID

        Returns:
            True if capture successful
        """
        with self._lock:
            if camera_id not in self._cameras:
                return False
            info = self._cameras[camera_id]

        if not info.camera or not info.camera.connected:
            return False

        return info.camera.capture()

    def capture_all(self) -> Dict[str, bool]:
        """
        Capture on all connected cameras simultaneously

        Returns:
            Dict of camera_id -> success
        """
        results = {}
        threads = []

        for info in self.connected_cameras:
            t = threading.Thread(
                target=lambda cid: results.update({cid: self.capture(cid)}),
                args=(info.id,)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return results

    def capture_sync(self, delay_ms: int = 0) -> Dict[str, bool]:
        """
        Synchronized capture on all connected cameras

        Args:
            delay_ms: Delay between captures in milliseconds

        Returns:
            Dict of camera_id -> success
        """
        results = {}
        cameras = self.connected_cameras

        if not cameras:
            return results

        # Prepare all cameras (half-press shutter for AF)
        for info in cameras:
            if info.camera:
                # Half press for AF lock
                pass

        time.sleep(0.5)  # Wait for AF

        # Capture all
        threads = []
        for info in cameras:
            t = threading.Thread(
                target=lambda cid: results.update({cid: self.capture(cid)}),
                args=(info.id,)
            )
            threads.append(t)
            t.start()

            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

        for t in threads:
            t.join()

        return results

    def get_camera(self, camera_id: str) -> Optional[CameraInfo]:
        """Get camera info by ID"""
        with self._lock:
            return self._cameras.get(camera_id)

    def get_battery_levels(self) -> Dict[str, Optional[int]]:
        """Get battery levels for all connected cameras"""
        levels = {}
        for info in self.connected_cameras:
            if info.camera:
                levels[info.id] = info.camera.get_battery_level()
        return levels

    def refresh_status(self, camera_id: str):
        """Refresh camera status"""
        with self._lock:
            if camera_id not in self._cameras:
                return
            info = self._cameras[camera_id]

        if info.camera and info.camera.connected:
            info.battery = info.camera.get_battery_level()
            device_info = info.camera.get_device_info()
            if device_info:
                info.model = device_info.get('model', info.model)

    def _update_state(self, camera_id: str, state: CameraState, error: str = ""):
        """Update camera state"""
        with self._lock:
            if camera_id in self._cameras:
                self._cameras[camera_id].state = state
                self._cameras[camera_id].error_message = error

        if self._state_callback:
            self._state_callback(camera_id, state)

    def __len__(self) -> int:
        return len(self._cameras)

    def __iter__(self):
        return iter(self.cameras)


# Global instance
_manager: Optional[CameraManager] = None


def get_camera_manager() -> CameraManager:
    """Get global camera manager instance"""
    global _manager
    if _manager is None:
        _manager = CameraManager()
    return _manager


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = CameraManager()

    # Add multiple cameras
    manager.add_camera("192.168.1.20", name="Camera A")
    manager.add_camera("192.168.1.21", name="Camera B")
    manager.add_camera("192.168.1.22", name="Camera C")

    print(f"Added {len(manager)} cameras")

    # Connect all
    print("Connecting to all cameras...")
    results = manager.connect_all()
    for cam_id, success in results.items():
        print(f"  {cam_id}: {'OK' if success else 'Failed'}")

    # Capture on all
    if manager.connected_cameras:
        print("\nCapturing on all cameras...")
        results = manager.capture_all()
        for cam_id, success in results.items():
            print(f"  {cam_id}: {'OK' if success else 'Failed'}")

    # Disconnect
    manager.disconnect_all()

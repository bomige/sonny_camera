"""
Connection Thread
카메라 연결을 위한 백그라운드 스레드
"""

from PyQt5.QtCore import QThread, pyqtSignal


class ConnectionThread(QThread):
    """Thread for camera connection"""

    # Signals
    connected = pyqtSignal(bool, str)  # success, message

    def __init__(self, camera, timeout: float = 10.0):
        super().__init__()
        self.camera = camera
        self.timeout = timeout

    def run(self):
        """Run connection process"""
        try:
            success = self.camera.connect(timeout=self.timeout)
            if success:
                model = getattr(self.camera, 'camera_info', None)
                if model and hasattr(model, 'model') and model.model:
                    self.connected.emit(True, f"Connected to {model.model}")
                else:
                    self.connected.emit(True, "Connected successfully")
            else:
                self.connected.emit(False, "Connection failed - check USB and camera settings")
        except Exception as e:
            error_msg = str(e)
            if "Access denied" in error_msg or "WinUSB" in error_msg:
                self.connected.emit(False, "Driver error - install WinUSB driver using Zadig")
            elif "No device" in error_msg or "not found" in error_msg.lower():
                self.connected.emit(False, "Camera not found - connect USB and enable PC Remote mode")
            else:
                self.connected.emit(False, f"Connection error: {error_msg}")

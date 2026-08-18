"""
Connection Thread
카메라 연결을 위한 백그라운드 스레드
"""

from PyQt5.QtCore import QThread, pyqtSignal

from ptp_ip import SonyPtpIpCamera


class ConnectionThread(QThread):
    """Thread for camera connection"""

    # Signals
    connected = pyqtSignal(bool, str)  # success, message

    def __init__(self, camera: SonyPtpIpCamera, timeout: float = 10.0):
        super().__init__()
        self.camera = camera
        self.timeout = timeout

    def run(self):
        """Run connection process"""
        try:
            success = self.camera.connect(timeout=self.timeout)
            if success:
                self.connected.emit(True, "Connected successfully")
            else:
                self.connected.emit(False, "Connection failed - check camera settings")
        except ConnectionRefusedError:
            self.connected.emit(False, "Connection refused - camera may not be in PC Remote mode")
        except TimeoutError:
            self.connected.emit(False, "Connection timeout - check IP address and network")
        except Exception as e:
            self.connected.emit(False, f"Connection error: {str(e)}")

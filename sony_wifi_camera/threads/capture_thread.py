"""
Capture Thread
사진 촬영을 위한 백그라운드 스레드
"""

from PyQt5.QtCore import QThread, pyqtSignal


class CaptureThread(QThread):
    """Thread for photo capture"""

    # Signals
    capture_started = pyqtSignal()
    capture_complete = pyqtSignal(bool, str)  # success, result/error message
    image_data_received = pyqtSignal(bytes)  # raw image data

    def __init__(self, camera, save_path: str = None):
        super().__init__()
        self.camera = camera
        self.save_path = save_path

    def run(self):
        """Run capture process"""
        self.capture_started.emit()

        try:
            # Check if camera has capture_and_download method (HTTP API)
            if hasattr(self.camera, 'capture_and_download') and self.save_path:
                success = self.camera.capture_and_download(self.save_path)
                if success:
                    self.capture_complete.emit(True, f"Photo saved: {self.save_path}")
                else:
                    self.capture_complete.emit(False, "Capture failed")
            # Check if camera has capture method that returns URL (HTTP API)
            elif hasattr(self.camera, 'capture'):
                result = self.camera.capture()
                if result:
                    # HTTP API returns URL string
                    if isinstance(result, str):
                        if self.save_path:
                            # Download the image
                            import requests
                            response = requests.get(result, timeout=30)
                            if response.status_code == 200:
                                with open(self.save_path, 'wb') as f:
                                    f.write(response.content)
                                self.capture_complete.emit(True, f"Photo saved: {self.save_path}")
                            else:
                                self.capture_complete.emit(False, "Failed to download image")
                        else:
                            self.capture_complete.emit(True, f"Photo URL: {result}")
                    # PTP-IP returns bool
                    elif isinstance(result, bool) and result:
                        self.capture_complete.emit(True, "Capture successful")
                    else:
                        self.capture_complete.emit(False, "Capture failed")
                else:
                    self.capture_complete.emit(False, "Capture failed - check camera state")
            else:
                self.capture_complete.emit(False, "Camera does not support capture")

        except Exception as e:
            self.capture_complete.emit(False, f"Capture error: {str(e)}")

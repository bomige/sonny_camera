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
            result = self.camera.capture(self.save_path)

            if result:
                if self.save_path:
                    self.capture_complete.emit(True, f"Photo saved: {self.save_path}")
                else:
                    self.capture_complete.emit(True, "Capture successful")
                    if isinstance(result, bytes):
                        self.image_data_received.emit(result)
            else:
                self.capture_complete.emit(False, "Capture failed - check camera state")

        except Exception as e:
            self.capture_complete.emit(False, f"Capture error: {str(e)}")

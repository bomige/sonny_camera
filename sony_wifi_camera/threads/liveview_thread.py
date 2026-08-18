"""
LiveView Thread
라이브뷰 스트리밍을 위한 백그라운드 스레드
"""

from PyQt5.QtCore import QThread, pyqtSignal


class LiveViewThread(QThread):
    """Thread for live view streaming"""

    # Signals
    frame_ready = pyqtSignal(bytes)  # JPEG frame data
    error = pyqtSignal(str)  # error message
    started_signal = pyqtSignal()
    stopped_signal = pyqtSignal()

    def __init__(self, camera, fps: int = 30):
        super().__init__()
        self.camera = camera
        self.fps = fps
        self._running = False
        self._frame_interval = 1000 // fps  # milliseconds

    def run(self):
        """Run liveview streaming"""
        self._running = True
        self.started_signal.emit()

        # Check if camera uses HTTP API (start_liveview with callback)
        if hasattr(self.camera, 'start_liveview'):
            # HTTP API - use callback-based streaming
            def frame_callback(frame_data: bytes):
                if self._running:
                    self.frame_ready.emit(frame_data)

            success = self.camera.start_liveview(callback=frame_callback)

            if not success:
                self.error.emit("Failed to start LiveView")
                self.stopped_signal.emit()
                return

            # Wait while running
            while self._running:
                self.msleep(100)

            # Stop liveview
            self.camera.stop_liveview()

        else:
            # PTP-IP style - polling based
            error_count = 0
            max_errors = 10

            while self._running:
                try:
                    frame = self.camera.get_liveview_frame()
                    if frame:
                        self.frame_ready.emit(frame)
                        error_count = 0
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    if error_count >= max_errors:
                        self.error.emit(f"LiveView error: {str(e)}")
                        break

                self.msleep(self._frame_interval)

        self.stopped_signal.emit()

    def stop(self):
        """Stop liveview streaming"""
        self._running = False

    def is_running(self) -> bool:
        """Check if liveview is running"""
        return self._running

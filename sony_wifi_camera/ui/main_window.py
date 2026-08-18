"""
Main Window
메인 애플리케이션 윈도우
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QProgressBar, QMessageBox, QLabel
)
from PyQt5.QtGui import QFont

from .styles import AppStyles
from .preview_widget import PreviewWidget
from .connection_panel import ConnectionPanel
from .status_panel import StatusPanel
from .capture_panel import CapturePanel

from ptp_ip import SonyPtpIpCamera
from threads import ConnectionThread, CaptureThread, LiveViewThread


class SonyCameraApp(QMainWindow):
    """Main Application Window"""

    def __init__(self):
        super().__init__()

        # Camera and threads
        self.camera: SonyPtpIpCamera = None
        self.connection_thread: ConnectionThread = None
        self.capture_thread: CaptureThread = None
        self.liveview_thread: LiveViewThread = None

        self.init_ui()
        self.connect_signals()
        self.apply_styles()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Sony Camera Wi-Fi Remote")
        self.setMinimumSize(900, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left panel - Preview and Capture
        left_panel = QVBoxLayout()

        # Preview widget
        self.preview_widget = PreviewWidget()
        left_panel.addWidget(self.preview_widget)

        # Capture panel
        self.capture_panel = CapturePanel()
        left_panel.addWidget(self.capture_panel)

        main_layout.addLayout(left_panel, stretch=2)

        # Right panel - Controls
        right_panel = QVBoxLayout()

        # Connection panel
        self.connection_panel = ConnectionPanel()
        right_panel.addWidget(self.connection_panel)

        # Status panel
        self.status_panel = StatusPanel()
        right_panel.addWidget(self.status_panel)

        # Spacer
        right_panel.addStretch()

        # Info label
        info_label = QLabel("Based on Sony Camera Remote SDK\nPTP-IP Protocol")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        right_panel.addWidget(info_label)

        main_layout.addLayout(right_panel, stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Enter camera IP and click Connect")

        # Progress bar in status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def connect_signals(self):
        """Connect UI signals to handlers"""
        # Connection panel signals
        self.connection_panel.connect_requested.connect(self.connect_camera)
        self.connection_panel.disconnect_requested.connect(self.disconnect_camera)

        # Status panel signals
        self.status_panel.refresh_requested.connect(self.refresh_camera_status)

        # Capture panel signals
        self.capture_panel.capture_requested.connect(self.capture_photo)
        self.capture_panel.liveview_toggle_requested.connect(self.toggle_liveview)

    def apply_styles(self):
        """Apply application-wide styles"""
        self.setStyleSheet(AppStyles.get_main_stylesheet())

    def connect_camera(self, ip: str, port: int):
        """Connect to camera"""
        self.status_bar.showMessage(f"Connecting to {ip}:{port}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.connection_panel.set_connecting(True)
        self.status_panel.set_status("Connecting...", connecting=True)

        self.camera = SonyPtpIpCamera(ip, port)

        self.connection_thread = ConnectionThread(self.camera)
        self.connection_thread.connected.connect(self._on_connection_result)
        self.connection_thread.start()

    def _on_connection_result(self, success: bool, message: str):
        """Handle connection result"""
        self.progress_bar.setVisible(False)
        self.connection_panel.set_connecting(False)

        if success:
            self.connection_panel.set_connected(True)
            self.status_panel.set_status("Connected", connected=True)
            self.status_panel.set_enabled(True)
            self.capture_panel.set_enabled(True)
            self.status_bar.showMessage("Connected to camera")

            # Refresh camera status
            self.refresh_camera_status()
        else:
            self.connection_panel.set_connected(False)
            self.status_panel.set_status("Disconnected")
            self.status_bar.showMessage(f"Connection failed: {message}")
            QMessageBox.warning(self, "Connection Failed", message)

    def disconnect_camera(self):
        """Disconnect from camera"""
        # Stop liveview if running
        if self.liveview_thread and self.liveview_thread.is_running():
            self.stop_liveview()

        # Disconnect camera
        if self.camera:
            self.camera.disconnect()
            self.camera = None

        # Update UI
        self.connection_panel.set_connected(False)
        self.status_panel.reset()
        self.capture_panel.set_enabled(False)
        self.preview_widget.clear_preview()
        self.status_bar.showMessage("Disconnected")

    def refresh_camera_status(self):
        """Refresh camera status information"""
        if not self.camera or not self.camera.connected:
            return

        # Get battery level
        battery = self.camera.get_battery_level()
        self.status_panel.set_battery_level(battery)

        # Get device info
        info = self.camera.get_device_info()
        if info:
            self.status_panel.set_model(info.get('model'))

        self.status_bar.showMessage("Status refreshed")

    def toggle_liveview(self):
        """Toggle live view"""
        if self.capture_panel.is_liveview_active():
            self.stop_liveview()
        else:
            self.start_liveview()

    def start_liveview(self):
        """Start live view"""
        if not self.camera or not self.camera.connected:
            return

        self.liveview_thread = LiveViewThread(self.camera)
        self.liveview_thread.frame_ready.connect(self.preview_widget.update_frame)
        self.liveview_thread.error.connect(self._on_liveview_error)
        self.liveview_thread.started_signal.connect(
            lambda: self.capture_panel.set_liveview_active(True)
        )
        self.liveview_thread.stopped_signal.connect(
            lambda: self.capture_panel.set_liveview_active(False)
        )
        self.liveview_thread.start()

        self.status_bar.showMessage("LiveView started")

    def stop_liveview(self):
        """Stop live view"""
        if self.liveview_thread:
            self.liveview_thread.stop()
            self.liveview_thread.wait()
            self.liveview_thread = None

        self.capture_panel.set_liveview_active(False)
        self.status_bar.showMessage("LiveView stopped")

    def _on_liveview_error(self, error: str):
        """Handle live view error"""
        self.status_bar.showMessage(f"LiveView error: {error}")

    def capture_photo(self, save_path: str):
        """Capture a photo"""
        if not self.camera or not self.camera.connected:
            QMessageBox.warning(self, "Error", "Camera not connected")
            return

        self.status_bar.showMessage("Capturing...")
        self.capture_panel.set_capturing(True)

        self.capture_thread = CaptureThread(self.camera, save_path)
        self.capture_thread.capture_complete.connect(self._on_capture_complete)
        self.capture_thread.start()

    def _on_capture_complete(self, success: bool, result: str):
        """Handle capture completion"""
        self.capture_panel.set_capturing(False)

        if success:
            self.status_bar.showMessage(result)
        else:
            self.status_bar.showMessage(f"Capture failed: {result}")
            QMessageBox.warning(self, "Capture Failed", result)

    def closeEvent(self, event):
        """Handle window close"""
        if self.camera and self.camera.connected:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Camera is connected. Disconnect and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.disconnect_camera()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

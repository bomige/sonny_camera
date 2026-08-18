"""
Status Panel
카메라 상태 표시 패널
"""

from PyQt5.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QPushButton
)
from PyQt5.QtCore import pyqtSignal

from .styles import AppStyles


class StatusPanel(QGroupBox):
    """Camera status display panel"""

    # Signals
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Camera Status", parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QGridLayout(self)

        # Connection status
        layout.addWidget(QLabel("Status:"), 0, 0)
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet(AppStyles.get_status_disconnected_style())
        layout.addWidget(self.status_label, 0, 1)

        # Battery level
        layout.addWidget(QLabel("Battery:"), 1, 0)
        self.battery_label = QLabel("--")
        layout.addWidget(self.battery_label, 1, 1)

        # Camera model
        layout.addWidget(QLabel("Model:"), 2, 0)
        self.model_label = QLabel("--")
        layout.addWidget(self.model_label, 2, 1)

        # Exposure mode
        layout.addWidget(QLabel("Mode:"), 3, 0)
        self.mode_label = QLabel("--")
        layout.addWidget(self.mode_label, 3, 1)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_btn, 4, 0, 1, 2)

    def set_status(self, status: str, connected: bool = False, connecting: bool = False):
        """
        Set connection status

        Args:
            status: Status text
            connected: Whether connected
            connecting: Whether connecting
        """
        self.status_label.setText(status)
        if connecting:
            self.status_label.setStyleSheet(AppStyles.get_status_connecting_style())
        elif connected:
            self.status_label.setStyleSheet(AppStyles.get_status_connected_style())
        else:
            self.status_label.setStyleSheet(AppStyles.get_status_disconnected_style())

    def set_battery_level(self, level: int = None):
        """Set battery level"""
        if level is not None:
            self.battery_label.setText(f"{level}%")

            # Color based on level
            if level > 50:
                self.battery_label.setStyleSheet("color: #4caf50;")
            elif level > 20:
                self.battery_label.setStyleSheet("color: #ff9800;")
            else:
                self.battery_label.setStyleSheet("color: #f44336;")
        else:
            self.battery_label.setText("--")
            self.battery_label.setStyleSheet("")

    def set_model(self, model: str = None):
        """Set camera model"""
        self.model_label.setText(model if model else "--")

    def set_mode(self, mode: str = None):
        """Set exposure mode"""
        self.mode_label.setText(mode if mode else "--")

    def set_enabled(self, enabled: bool):
        """Enable/disable refresh button"""
        self.refresh_btn.setEnabled(enabled)

    def reset(self):
        """Reset all status to default"""
        self.set_status("Disconnected", connected=False)
        self.set_battery_level(None)
        self.set_model(None)
        self.set_mode(None)
        self.set_enabled(False)

"""
Connection Panel
USB 카메라 연결 패널
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt5.QtCore import pyqtSignal


class ConnectionPanel(QGroupBox):
    """USB Camera connection panel"""

    # Signals
    connect_requested = pyqtSignal()  # No IP/port needed for USB
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("USB Connection", parent)
        self._connected = False
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel("Connect Sony camera via USB cable")
        info_label.setStyleSheet("color: #888;")
        layout.addWidget(info_label)

        # Instructions
        instructions = QLabel(
            "1. Connect camera with USB\n"
            "2. Set camera to PC Remote mode\n"
            "3. Click Connect button"
        )
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instructions)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

    def _on_connect_clicked(self):
        """Handle connect button click"""
        if self._connected:
            self.disconnect_requested.emit()
        else:
            self.connect_requested.emit()

    def set_connected(self, connected: bool):
        """Update connection state"""
        self._connected = connected
        if connected:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #c62828;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
        else:
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("")

    def set_connecting(self, connecting: bool):
        """Set connecting state"""
        self.connect_btn.setEnabled(not connecting)
        if connecting:
            self.connect_btn.setText("Connecting...")

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected

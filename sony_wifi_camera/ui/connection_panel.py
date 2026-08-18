"""
Connection Panel
카메라 연결 설정 패널
"""

from PyQt5.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox
)
from PyQt5.QtCore import pyqtSignal


class ConnectionPanel(QGroupBox):
    """Camera connection settings panel"""

    # Signals
    connect_requested = pyqtSignal(str, int)  # ip, port
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Connection", parent)
        self._connected = False
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QGridLayout(self)

        # IP Address
        layout.addWidget(QLabel("Camera IP:"), 0, 0)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.1")
        self.ip_input.setText("192.168.122.1")
        layout.addWidget(self.ip_input, 0, 1)

        # Port
        layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(15740)
        layout.addWidget(self.port_input, 1, 1)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn, 2, 0, 1, 2)

    def _on_connect_clicked(self):
        """Handle connect button click"""
        if self._connected:
            self.disconnect_requested.emit()
        else:
            ip = self.ip_input.text().strip()
            port = self.port_input.value()
            if ip:
                self.connect_requested.emit(ip, port)

    def set_connected(self, connected: bool):
        """Update connection state"""
        self._connected = connected
        if connected:
            self.connect_btn.setText("Disconnect")
            self.ip_input.setEnabled(False)
            self.port_input.setEnabled(False)
        else:
            self.connect_btn.setText("Connect")
            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)

    def set_connecting(self, connecting: bool):
        """Set connecting state"""
        self.connect_btn.setEnabled(not connecting)
        if connecting:
            self.connect_btn.setText("Connecting...")

    def get_ip(self) -> str:
        """Get IP address"""
        return self.ip_input.text().strip()

    def set_ip(self, ip: str):
        """Set IP address"""
        self.ip_input.setText(ip)

    def get_port(self) -> int:
        """Get port number"""
        return self.port_input.value()

    def set_port(self, port: int):
        """Set port number"""
        self.port_input.setValue(port)

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected

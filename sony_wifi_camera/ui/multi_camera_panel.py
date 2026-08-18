"""
Multi Camera Panel
여러 대의 카메라를 관리하는 UI 패널
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QSpinBox, QGridLayout, QMessageBox,
    QProgressDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor

from camera_manager import CameraManager, CameraInfo, CameraState


class ConnectAllThread(QThread):
    """Thread for connecting all cameras"""
    progress = pyqtSignal(str, bool)  # camera_id, success
    finished_signal = pyqtSignal(dict)  # results

    def __init__(self, manager: CameraManager, timeout: float = 10.0):
        super().__init__()
        self.manager = manager
        self.timeout = timeout

    def run(self):
        results = {}
        for info in self.manager.cameras:
            if info.state != CameraState.CONNECTED:
                success = self.manager.connect(info.id, self.timeout)
                results[info.id] = success
                self.progress.emit(info.id, success)
        self.finished_signal.emit(results)


class CaptureAllThread(QThread):
    """Thread for capturing on all cameras"""
    progress = pyqtSignal(str, bool)  # camera_id, success
    finished_signal = pyqtSignal(dict)  # results

    def __init__(self, manager: CameraManager):
        super().__init__()
        self.manager = manager

    def run(self):
        results = self.manager.capture_all()
        for cam_id, success in results.items():
            self.progress.emit(cam_id, success)
        self.finished_signal.emit(results)


class MultiCameraPanel(QWidget):
    """Multi-camera management panel"""

    camera_selected = pyqtSignal(str)  # camera_id
    capture_all_requested = pyqtSignal()

    def __init__(self, manager: CameraManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._connect_thread: ConnectAllThread = None
        self._capture_thread: CaptureAllThread = None
        self.init_ui()

        # Set state callback
        self.manager.set_state_callback(self._on_state_changed)

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Add camera section
        add_group = QGroupBox("Add Camera")
        add_layout = QGridLayout(add_group)

        add_layout.addWidget(QLabel("IP:"), 0, 0)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.20")
        add_layout.addWidget(self.ip_input, 0, 1)

        add_layout.addWidget(QLabel("Port:"), 0, 2)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(15740)
        self.port_input.setMaximumWidth(80)
        add_layout.addWidget(self.port_input, 0, 3)

        add_layout.addWidget(QLabel("Name:"), 1, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Camera A")
        add_layout.addWidget(self.name_input, 1, 1, 1, 2)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_camera)
        add_layout.addWidget(self.add_btn, 1, 3)

        layout.addWidget(add_group)

        # Camera list
        list_group = QGroupBox("Cameras")
        list_layout = QVBoxLayout(list_group)

        self.camera_list = QListWidget()
        self.camera_list.itemClicked.connect(self._on_camera_clicked)
        list_layout.addWidget(self.camera_list)

        # List buttons
        btn_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect_selected)
        btn_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect_selected)
        btn_layout.addWidget(self.disconnect_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        list_layout.addLayout(btn_layout)
        layout.addWidget(list_group)

        # Bulk actions
        bulk_group = QGroupBox("Bulk Actions")
        bulk_layout = QHBoxLayout(bulk_group)

        self.connect_all_btn = QPushButton("Connect All")
        self.connect_all_btn.clicked.connect(self._connect_all)
        bulk_layout.addWidget(self.connect_all_btn)

        self.disconnect_all_btn = QPushButton("Disconnect All")
        self.disconnect_all_btn.clicked.connect(self._disconnect_all)
        bulk_layout.addWidget(self.disconnect_all_btn)

        layout.addWidget(bulk_group)

        # Capture all button (big)
        self.capture_all_btn = QPushButton("CAPTURE ALL")
        self.capture_all_btn.setMinimumHeight(50)
        self.capture_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.capture_all_btn.clicked.connect(self._capture_all)
        layout.addWidget(self.capture_all_btn)

        # Status
        self.status_label = QLabel("No cameras added")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

    def _add_camera(self):
        """Add a camera"""
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter IP address")
            return

        port = self.port_input.value()
        name = self.name_input.text().strip()

        info = self.manager.add_camera(ip, port, name)
        self._refresh_list()

        # Clear inputs
        self.ip_input.clear()
        self.name_input.clear()

    def _remove_selected(self):
        """Remove selected camera"""
        item = self.camera_list.currentItem()
        if item:
            camera_id = item.data(Qt.UserRole)
            if camera_id:
                self.manager.remove_camera(camera_id)
                self._refresh_list()

    def _connect_selected(self):
        """Connect to selected camera"""
        item = self.camera_list.currentItem()
        if item:
            camera_id = item.data(Qt.UserRole)
            if camera_id:
                self.manager.connect(camera_id)
                self._refresh_list()

    def _disconnect_selected(self):
        """Disconnect selected camera"""
        item = self.camera_list.currentItem()
        if item:
            camera_id = item.data(Qt.UserRole)
            if camera_id:
                self.manager.disconnect(camera_id)
                self._refresh_list()

    def _connect_all(self):
        """Connect to all cameras"""
        if not self.manager.cameras:
            return

        self.connect_all_btn.setEnabled(False)
        self.connect_all_btn.setText("Connecting...")

        self._connect_thread = ConnectAllThread(self.manager)
        self._connect_thread.progress.connect(self._on_connect_progress)
        self._connect_thread.finished_signal.connect(self._on_connect_all_finished)
        self._connect_thread.start()

    def _on_connect_progress(self, camera_id: str, success: bool):
        """Handle connection progress"""
        self._refresh_list()

    def _on_connect_all_finished(self, results: dict):
        """Handle connect all finished"""
        self.connect_all_btn.setEnabled(True)
        self.connect_all_btn.setText("Connect All")
        self._refresh_list()
        self._update_status()

    def _disconnect_all(self):
        """Disconnect from all cameras"""
        self.manager.disconnect_all()
        self._refresh_list()

    def _capture_all(self):
        """Capture on all cameras"""
        connected = self.manager.connected_cameras
        if not connected:
            QMessageBox.warning(self, "Error", "No cameras connected")
            return

        self.capture_all_btn.setEnabled(False)
        self.capture_all_btn.setText("Capturing...")

        self._capture_thread = CaptureAllThread(self.manager)
        self._capture_thread.finished_signal.connect(self._on_capture_all_finished)
        self._capture_thread.start()

    def _on_capture_all_finished(self, results: dict):
        """Handle capture all finished"""
        self.capture_all_btn.setEnabled(True)
        self.capture_all_btn.setText("CAPTURE ALL")

        success_count = sum(1 for s in results.values() if s)
        total = len(results)
        self.status_label.setText(f"Captured: {success_count}/{total} cameras")

    def _on_camera_clicked(self, item: QListWidgetItem):
        """Handle camera click"""
        camera_id = item.data(Qt.UserRole)
        if camera_id:
            self.camera_selected.emit(camera_id)

    def _on_state_changed(self, camera_id: str, state: CameraState):
        """Handle camera state change"""
        self._refresh_list()
        self._update_status()

    def _refresh_list(self):
        """Refresh camera list"""
        self.camera_list.clear()

        for info in self.manager.cameras:
            # State indicator
            if info.state == CameraState.CONNECTED:
                status = "●"
                color = QColor("#4caf50")
            elif info.state == CameraState.CONNECTING:
                status = "◐"
                color = QColor("#ff9800")
            elif info.state == CameraState.ERROR:
                status = "✗"
                color = QColor("#f44336")
            else:
                status = "○"
                color = QColor("#888")

            text = f"{status} {info.name} ({info.ip})"
            if info.battery is not None:
                text += f" [{info.battery}%]"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, info.id)
            item.setForeground(color)
            self.camera_list.addItem(item)

    def _update_status(self):
        """Update status label"""
        total = len(self.manager.cameras)
        connected = len(self.manager.connected_cameras)
        self.status_label.setText(f"Cameras: {connected}/{total} connected")

    def refresh(self):
        """Public refresh method"""
        self._refresh_list()
        self._update_status()

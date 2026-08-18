"""
Discovery Panel
카메라 자동 검색 패널
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal

from discovery import CameraDiscovery, NetworkScanner, DiscoveredCamera


class DiscoveryThread(QThread):
    """Camera discovery thread"""

    camera_found = pyqtSignal(object)  # DiscoveredCamera
    scan_progress = pyqtSignal(int, int, int)  # current, total, found
    finished_signal = pyqtSignal(list)  # List[DiscoveredCamera]

    def __init__(self, timeout: float = 5.0):
        super().__init__()
        self.timeout = timeout

    def run(self):
        """Run discovery"""
        cameras = []

        # SSDP discovery
        discovery = CameraDiscovery()
        ssdp_cameras = discovery.discover(
            timeout=self.timeout,
            callback=lambda cam: self.camera_found.emit(cam)
        )
        cameras.extend(ssdp_cameras)

        # Port scan if nothing found
        if not cameras:
            scanner = NetworkScanner()
            ips = scanner.scan_subnet(
                timeout=0.3,
                callback=lambda cur, total, found: self.scan_progress.emit(cur, total, found)
            )

            for ip in ips:
                cam = DiscoveredCamera(
                    ip=ip,
                    port=8080,
                    name="Sony Camera",
                    model="Unknown",
                    uuid=""
                )
                cameras.append(cam)
                self.camera_found.emit(cam)

        self.finished_signal.emit(cameras)


class DiscoveryPanel(QGroupBox):
    """Camera discovery panel"""

    camera_selected = pyqtSignal(str, int)  # ip, port

    def __init__(self, parent=None):
        super().__init__("Auto Discovery", parent)
        self._discovery_thread: DiscoveryThread = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Scan button
        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Network")
        self.scan_btn.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_btn)
        layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Camera list
        self.camera_list = QListWidget()
        self.camera_list.itemDoubleClicked.connect(self._on_camera_selected)
        layout.addWidget(self.camera_list)

        # Select button
        self.select_btn = QPushButton("Select Camera")
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self._select_current)
        layout.addWidget(self.select_btn)

    def start_scan(self):
        """Start camera discovery"""
        self.camera_list.clear()
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self._discovery_thread = DiscoveryThread(timeout=5.0)
        self._discovery_thread.camera_found.connect(self._on_camera_found)
        self._discovery_thread.scan_progress.connect(self._on_scan_progress)
        self._discovery_thread.finished_signal.connect(self._on_scan_finished)
        self._discovery_thread.start()

    def _on_camera_found(self, camera: DiscoveredCamera):
        """Handle discovered camera"""
        item = QListWidgetItem(str(camera))
        item.setData(256, camera)  # Store camera object
        self.camera_list.addItem(item)
        self.select_btn.setEnabled(True)

    def _on_scan_progress(self, current: int, total: int, found: int):
        """Handle scan progress"""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def _on_scan_finished(self, cameras: list):
        """Handle scan completion"""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Network")
        self.progress_bar.setVisible(False)

        if not cameras:
            self.camera_list.addItem("No cameras found")

    def _on_camera_selected(self, item: QListWidgetItem):
        """Handle camera double-click"""
        camera = item.data(256)
        if camera:
            self.camera_selected.emit(camera.ip, camera.port)

    def _select_current(self):
        """Select current camera"""
        item = self.camera_list.currentItem()
        if item:
            camera = item.data(256)
            if camera:
                self.camera_selected.emit(camera.ip, camera.port)

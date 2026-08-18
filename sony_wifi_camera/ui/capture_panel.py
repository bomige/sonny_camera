"""
Capture Panel
촬영 및 저장 설정 패널
"""

import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QFileDialog,
    QDateTimeEdit, QSpinBox, QProgressBar
)
from PyQt5.QtCore import pyqtSignal, QDateTime

from .styles import AppStyles


class CapturePanel(QWidget):
    """Capture button and save settings panel"""

    # Signals
    capture_requested = pyqtSignal(str)  # save_path
    liveview_toggle_requested = pyqtSignal()
    download_requested = pyqtSignal(object, object, int)  # start_time, end_time, count

    def __init__(self, parent=None):
        super().__init__(parent)
        self.save_directory = os.path.expanduser("~/Pictures/SonyCapture")
        self._liveview_active = False
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Capture button (large)
        self.capture_btn = QPushButton("CAPTURE")
        self.capture_btn.setMinimumHeight(60)
        self.capture_btn.setEnabled(False)
        self.capture_btn.clicked.connect(self._on_capture_clicked)
        self.capture_btn.setStyleSheet(AppStyles.get_capture_button_style())
        layout.addWidget(self.capture_btn)

        # LiveView button
        self.liveview_btn = QPushButton("Start LiveView")
        self.liveview_btn.setEnabled(False)
        self.liveview_btn.clicked.connect(self._on_liveview_clicked)
        layout.addWidget(self.liveview_btn)

        # Save settings group
        save_group = QGroupBox("Save Settings")
        save_layout = QVBoxLayout(save_group)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.save_dir_input = QLineEdit()
        self.save_dir_input.setText(self.save_directory)
        self.save_dir_input.setReadOnly(True)
        dir_layout.addWidget(self.save_dir_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(browse_btn)

        save_layout.addLayout(dir_layout)

        # File naming prefix
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setText("IMG_")
        self.prefix_input.setMaximumWidth(100)
        name_layout.addWidget(self.prefix_input)
        name_layout.addStretch()
        save_layout.addLayout(name_layout)

        layout.addWidget(save_group)

        # Download from camera group
        download_group = QGroupBox("Download from Camera")
        download_layout = QVBoxLayout(download_group)

        # Time range selection
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("From:"))
        self.start_time = QDateTimeEdit()
        self.start_time.setDateTime(QDateTime.currentDateTime().addSecs(-3600))  # 1 hour ago
        self.start_time.setCalendarPopup(True)
        time_layout.addWidget(self.start_time)

        time_layout.addWidget(QLabel("To:"))
        self.end_time = QDateTimeEdit()
        self.end_time.setDateTime(QDateTime.currentDateTime())
        self.end_time.setCalendarPopup(True)
        time_layout.addWidget(self.end_time)
        download_layout.addLayout(time_layout)

        # Max count
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Max files:"))
        self.max_count = QSpinBox()
        self.max_count.setRange(1, 1000)
        self.max_count.setValue(100)
        self.max_count.setMaximumWidth(80)
        count_layout.addWidget(self.max_count)
        count_layout.addStretch()
        download_layout.addLayout(count_layout)

        # Download button
        self.download_btn = QPushButton("Download Photos")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download_clicked)
        download_layout.addWidget(self.download_btn)

        # Progress bar
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        download_layout.addWidget(self.download_progress)

        layout.addWidget(download_group)

    def _on_capture_clicked(self):
        """Handle capture button click"""
        # Ensure directory exists
        os.makedirs(self.save_directory, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.prefix_input.text()
        filename = f"{prefix}{timestamp}.jpg"
        save_path = os.path.join(self.save_directory, filename)

        self.capture_requested.emit(save_path)

    def _on_liveview_clicked(self):
        """Handle liveview button click"""
        self.liveview_toggle_requested.emit()

    def _browse_directory(self):
        """Browse for save directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            self.save_directory
        )
        if directory:
            self.save_directory = directory
            self.save_dir_input.setText(directory)

    def _on_download_clicked(self):
        """Handle download button click"""
        start = self.start_time.dateTime().toPyDateTime()
        end = self.end_time.dateTime().toPyDateTime()
        count = self.max_count.value()
        self.download_requested.emit(start, end, count)

    def set_enabled(self, enabled: bool):
        """Enable/disable capture controls"""
        self.capture_btn.setEnabled(enabled)
        self.liveview_btn.setEnabled(enabled)
        self.download_btn.setEnabled(enabled)

    def set_capturing(self, capturing: bool):
        """Set capturing state"""
        self.capture_btn.setEnabled(not capturing)
        if capturing:
            self.capture_btn.setText("Capturing...")
        else:
            self.capture_btn.setText("CAPTURE")

    def set_liveview_active(self, active: bool):
        """Set liveview state"""
        self._liveview_active = active
        if active:
            self.liveview_btn.setText("Stop LiveView")
        else:
            self.liveview_btn.setText("Start LiveView")

    def is_liveview_active(self) -> bool:
        """Check if liveview is active"""
        return self._liveview_active

    def get_save_directory(self) -> str:
        """Get save directory"""
        return self.save_directory

    def get_prefix(self) -> str:
        """Get filename prefix"""
        return self.prefix_input.text()

    def set_download_progress(self, current: int, total: int):
        """Set download progress"""
        self.download_progress.setVisible(True)
        self.download_progress.setRange(0, total)
        self.download_progress.setValue(current)
        if current >= total:
            self.download_progress.setVisible(False)

    def set_downloading(self, downloading: bool):
        """Set downloading state"""
        self.download_btn.setEnabled(not downloading)
        if downloading:
            self.download_btn.setText("Downloading...")
            self.download_progress.setVisible(True)
            self.download_progress.setRange(0, 0)
        else:
            self.download_btn.setText("Download Photos")
            self.download_progress.setVisible(False)

"""
Preview Widget
라이브 프리뷰 표시 위젯
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage

from .styles import AppStyles


class PreviewWidget(QGroupBox):
    """Live preview display widget"""

    def __init__(self, parent=None):
        super().__init__("Live Preview", parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setStyleSheet(AppStyles.get_preview_style())
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("No Preview")

        layout.addWidget(self.preview_label)

    def update_frame(self, frame_data: bytes):
        """
        Update preview with new frame data

        Args:
            frame_data: JPEG image data
        """
        try:
            image = QImage.fromData(frame_data)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                scaled = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
        except Exception as e:
            pass

    def clear_preview(self):
        """Clear the preview"""
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("No Preview")

    def set_message(self, message: str):
        """Display a message in the preview area"""
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(message)

    def get_size(self):
        """Get preview label size"""
        return self.preview_label.size()

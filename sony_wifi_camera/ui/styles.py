"""
Application Styles
애플리케이션 전체 스타일 정의
"""


class AppStyles:
    """Application-wide style definitions"""

    # Colors
    PRIMARY_COLOR = "#0078d4"
    PRIMARY_HOVER = "#1084d8"
    PRIMARY_PRESSED = "#006cbd"

    DANGER_COLOR = "#d32f2f"
    DANGER_HOVER = "#f44336"
    DANGER_PRESSED = "#b71c1c"

    SUCCESS_COLOR = "#4caf50"
    WARNING_COLOR = "#ff9800"
    ERROR_COLOR = "#f44336"

    BG_DARK = "#2b2b2b"
    BG_PANEL = "#333"
    BG_INPUT = "#444"
    BORDER_COLOR = "#555"
    TEXT_COLOR = "#ddd"
    TEXT_MUTED = "#888"

    @staticmethod
    def get_main_stylesheet() -> str:
        """Get main application stylesheet"""
        return """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #333;
                color: #fff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #ddd;
            }
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #fff;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QLineEdit:read-only {
                background-color: #3a3a3a;
            }
            QSpinBox {
                background-color: #444;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #fff;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QStatusBar {
                background-color: #252525;
                color: #aaa;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
            }
            QComboBox {
                background-color: #444;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #fff;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #444;
                color: #fff;
                selection-background-color: #0078d4;
            }
        """

    @staticmethod
    def get_capture_button_style() -> str:
        """Get capture button style"""
        return """
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 30px;
                border: none;
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
        """

    @staticmethod
    def get_preview_style() -> str:
        """Get preview label style"""
        return """
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #444;
                border-radius: 8px;
            }
        """

    @staticmethod
    def get_status_connected_style() -> str:
        """Get connected status style"""
        return "color: #4caf50; font-weight: bold;"

    @staticmethod
    def get_status_disconnected_style() -> str:
        """Get disconnected status style"""
        return "color: #f44336; font-weight: bold;"

    @staticmethod
    def get_status_connecting_style() -> str:
        """Get connecting status style"""
        return "color: #ff9800; font-weight: bold;"

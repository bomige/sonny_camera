"""
Sony Camera Wi-Fi Remote Control - PyQt Application

A PyQt-based GUI application for controlling Sony cameras over Wi-Fi.

Features:
- Wi-Fi connection to Sony cameras (PTP-IP protocol)
- Live preview
- Single photo capture
- Camera status display

Usage:
    python main.py
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from ui import SonyCameraApp


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Sony Camera Wi-Fi Remote")

    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create and show main window
    window = SonyCameraApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

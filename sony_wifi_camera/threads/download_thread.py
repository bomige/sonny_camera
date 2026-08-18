"""
Download Thread
카메라에서 사진 다운로드를 위한 백그라운드 스레드
"""

import os
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal


class DownloadThread(QThread):
    """Thread for downloading photos from camera"""

    # Signals
    progress = pyqtSignal(int, int)  # current, total
    file_downloaded = pyqtSignal(str)  # file path
    finished_signal = pyqtSignal(int, int)  # success_count, total_count
    error = pyqtSignal(str)

    def __init__(self, camera, save_dir: str, start_time: datetime,
                 end_time: datetime, max_count: int = 100):
        super().__init__()
        self.camera = camera
        self.save_dir = save_dir
        self.start_time = start_time
        self.end_time = end_time
        self.max_count = max_count

    def run(self):
        """Run download process"""
        try:
            # Get file list from camera
            files = self._get_files_in_range()

            if not files:
                self.error.emit("No files found in the specified time range")
                self.finished_signal.emit(0, 0)
                return

            total = min(len(files), self.max_count)
            success_count = 0

            os.makedirs(self.save_dir, exist_ok=True)

            for i, file_info in enumerate(files[:self.max_count]):
                self.progress.emit(i + 1, total)

                try:
                    # Download file
                    save_path = self._download_file(file_info)
                    if save_path:
                        self.file_downloaded.emit(save_path)
                        success_count += 1
                except Exception as e:
                    pass  # Continue with next file

            self.finished_signal.emit(success_count, total)

        except Exception as e:
            self.error.emit(f"Download error: {str(e)}")
            self.finished_signal.emit(0, 0)

    def _get_files_in_range(self) -> list:
        """Get list of files within time range"""
        files = []

        try:
            # pysonycam uses browse_content or similar
            if hasattr(self.camera, '_camera') and self.camera._camera:
                cam = self.camera._camera

                # Get object handles
                if hasattr(cam, 'get_object_handles'):
                    handles = cam.get_object_handles()

                    for handle in handles:
                        try:
                            info = cam.get_object_info(handle)
                            if info:
                                # Check if it's an image
                                if hasattr(info, 'format_code') and info.format_code in [0x3801, 0x3800]:  # JPEG, EXIF_JPEG
                                    # Check time range
                                    if hasattr(info, 'capture_date'):
                                        capture_time = info.capture_date
                                        if self.start_time <= capture_time <= self.end_time:
                                            files.append({
                                                'handle': handle,
                                                'info': info,
                                                'name': getattr(info, 'filename', f'IMG_{handle}.jpg')
                                            })
                        except:
                            pass

        except Exception as e:
            # Fallback: try to get recent files
            pass

        return files

    def _download_file(self, file_info: dict) -> str:
        """Download a single file"""
        try:
            handle = file_info['handle']
            filename = file_info['name']
            save_path = os.path.join(self.save_dir, filename)

            # Avoid overwriting
            if os.path.exists(save_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(save_path):
                    save_path = os.path.join(self.save_dir, f"{base}_{counter}{ext}")
                    counter += 1

            if hasattr(self.camera, '_camera') and self.camera._camera:
                cam = self.camera._camera
                if hasattr(cam, 'get_object'):
                    data = cam.get_object(handle)
                    if data:
                        with open(save_path, 'wb') as f:
                            f.write(data)
                        return save_path

        except Exception as e:
            pass

        return None

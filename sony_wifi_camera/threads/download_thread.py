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
            # Get internal camera object
            if not hasattr(self.camera, '_camera') or not self.camera._camera:
                self.error.emit("Camera not properly connected")
                self.finished_signal.emit(0, 0)
                return

            cam = self.camera._camera

            # Get content list using pysonycam API
            if not hasattr(cam, 'get_content_info_list'):
                self.error.emit("Camera does not support content browsing")
                self.finished_signal.emit(0, 0)
                return

            # Get file list
            items = cam.get_content_info_list(start_index=0, max_count=500)

            if not items:
                self.error.emit("No files found on camera")
                self.finished_signal.emit(0, 0)
                return

            # Filter by time range and file type (JPEG/ARW)
            image_formats = [0x3801, 0x3800, 0xB905]  # EXIF/JPEG, Undefined Image, ARW
            filtered = []

            for item in items:
                # Check format
                fmt = item.get('format_code', 0)
                if fmt not in image_formats:
                    continue

                # Check time range
                dt_str = item.get('date_time', '')
                if dt_str:
                    try:
                        # Parse datetime string (format: YYYYMMDDTHHMMSS)
                        item_time = datetime.strptime(dt_str, '%Y%m%dT%H%M%S')
                        if self.start_time <= item_time <= self.end_time:
                            filtered.append(item)
                    except:
                        # If can't parse, include anyway
                        filtered.append(item)
                else:
                    filtered.append(item)

            if not filtered:
                self.error.emit(f"No images found in time range")
                self.finished_signal.emit(0, 0)
                return

            # Limit count
            to_download = filtered[:self.max_count]
            total = len(to_download)
            success_count = 0

            os.makedirs(self.save_dir, exist_ok=True)

            for i, item in enumerate(to_download):
                self.progress.emit(i + 1, total)

                try:
                    save_path = self._download_item(cam, item)
                    if save_path:
                        self.file_downloaded.emit(save_path)
                        success_count += 1
                except Exception as e:
                    pass  # Continue with next file

            self.finished_signal.emit(success_count, total)

        except Exception as e:
            self.error.emit(f"Download error: {str(e)}")
            self.finished_signal.emit(0, 0)

    def _download_item(self, cam, item: dict) -> str:
        """Download a single item"""
        content_id = item.get('content_id')
        if content_id is None:
            return None

        file_name = item.get('file_name', f'IMG_{content_id}.jpg')

        # Make safe filename
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file_name)
        save_path = os.path.join(self.save_dir, safe_name)

        # Avoid overwriting
        if os.path.exists(save_path):
            base, ext = os.path.splitext(safe_name)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(self.save_dir, f"{base}_{counter}{ext}")
                counter += 1

        # Download
        data = cam.get_content_data(content_id)
        if data:
            with open(save_path, 'wb') as f:
                f.write(data)
            return save_path

        return None

"""
Download Thread
카메라에서 사진 다운로드를 위한 백그라운드 스레드
"""

import os
import logging
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


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
            logger.info(f"Starting download: {self.start_time} ~ {self.end_time}, max={self.max_count}")

            # Get internal pysonycam camera object
            if not hasattr(self.camera, '_camera') or self.camera._camera is None:
                self.error.emit("Camera not properly connected")
                self.finished_signal.emit(0, 0)
                return

            cam = self.camera._camera
            logger.info(f"Camera object: {type(cam)}")

            # Check if method exists
            if not hasattr(cam, 'get_content_info_list'):
                self.error.emit("Camera does not support content browsing")
                self.finished_signal.emit(0, 0)
                return

            # Set to transfer mode for content access
            try:
                cam.set_mode("transfer")
                logger.info("Set to transfer mode")
            except Exception as e:
                logger.warning(f"Could not set transfer mode: {e}")

            # Get file list
            logger.info("Getting content list...")
            items = cam.get_content_info_list(start_index=0, max_count=500)
            logger.info(f"Found {len(items) if items else 0} items")

            if not items:
                self.error.emit("No files found on camera")
                self.finished_signal.emit(0, 0)
                return

            # Filter by time range and file type
            image_formats = [0x3801, 0x3800, 0xB905]  # EXIF/JPEG, Undefined Image, ARW
            filtered = []

            for item in items:
                logger.debug(f"Item: {item}")

                # Check format
                fmt = item.get('format_code', 0)
                if fmt not in image_formats:
                    continue

                # Check time range
                dt_str = item.get('date_time', '')
                if dt_str:
                    try:
                        # Parse datetime (format: YYYYMMDDTHHMMSS or similar)
                        if 'T' in dt_str:
                            item_time = datetime.strptime(dt_str, '%Y%m%dT%H%M%S')
                        else:
                            item_time = datetime.strptime(dt_str, '%Y%m%d%H%M%S')

                        if self.start_time <= item_time <= self.end_time:
                            filtered.append(item)
                            logger.info(f"Matched: {item.get('file_name')} @ {item_time}")
                    except Exception as e:
                        # If can't parse time, include anyway
                        logger.debug(f"Time parse error for {dt_str}: {e}")
                        filtered.append(item)
                else:
                    # No time info, include anyway
                    filtered.append(item)

            logger.info(f"Filtered to {len(filtered)} items in time range")

            if not filtered:
                self.error.emit(f"No images found between {self.start_time} and {self.end_time}")
                self.finished_signal.emit(0, 0)
                return

            # Limit count
            to_download = filtered[:self.max_count]
            total = len(to_download)
            success_count = 0

            os.makedirs(self.save_dir, exist_ok=True)

            for i, item in enumerate(to_download):
                self.progress.emit(i + 1, total)
                logger.info(f"Downloading {i+1}/{total}: {item.get('file_name')}")

                try:
                    save_path = self._download_item(cam, item)
                    if save_path:
                        self.file_downloaded.emit(save_path)
                        success_count += 1
                        logger.info(f"Saved: {save_path}")
                except Exception as e:
                    logger.error(f"Download failed: {e}")

            # Back to still mode
            try:
                cam.set_mode("still")
            except:
                pass

            self.finished_signal.emit(success_count, total)

        except Exception as e:
            logger.exception(f"Download error: {e}")
            self.error.emit(f"Download error: {str(e)}")
            self.finished_signal.emit(0, 0)

    def _download_item(self, cam, item: dict) -> str:
        """Download a single item"""
        content_id = item.get('content_id')
        if content_id is None:
            logger.error("No content_id in item")
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

        # Download using pysonycam API
        logger.info(f"Getting content data for ID: {content_id}")
        data = cam.get_content_data(content_id)

        if data:
            with open(save_path, 'wb') as f:
                f.write(data)
            return save_path

        return None

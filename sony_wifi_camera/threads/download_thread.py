"""
Download Thread
카메라에서 사진 다운로드를 위한 백그라운드 스레드

인증된 세션에서 SetContentsTransferMode를 활성화한 후
표준 PTP 명령(GetObjectHandles, GetObjectInfo, GetObject)을 사용합니다.
"""

import os
import struct
import time
import logging
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

# PTP object format codes
FORMAT_FOLDER = 0x3001
FORMAT_JPEG = 0x3801
FORMAT_ARW = 0xB905


class DownloadThread(QThread):
    """Thread for downloading photos from camera using PTP commands"""

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
        """Run download process - try multiple strategies"""
        try:
            logger.info(f"Starting download: {self.start_time} ~ {self.end_time}, max={self.max_count}")

            # Get internal pysonycam camera object
            if not hasattr(self.camera, '_camera') or self.camera._camera is None:
                self.error.emit("Camera not properly connected")
                self.finished_signal.emit(0, 0)
                return

            cam = self.camera._camera
            transport = cam._transport
            logger.info(f"Camera object: {type(cam)}")

            # Import necessary constants
            try:
                from pysonycam.constants import SDIOOpCode, ResponseCode, PTPOpCode
            except ImportError:
                self.error.emit("pysonycam constants not available")
                self.finished_signal.emit(0, 0)
                return

            # Strategy: Use SetContentsTransferMode in authenticated session
            logger.info("Enabling Content Transfer Mode via SetContentsTransferMode...")

            try:
                # SetContentsTransferMode with params from v3-Windows SDK:
                # Param1: 0x02 (SELECT_ON_REMOTE_DEVICE)
                # Param2: 0x01 (MODE_ON)
                # Param3: 0x00 (ADD_INFO_NONE)
                resp = transport.send(
                    SDIOOpCode.SET_CONTENTS_TRANSFER_MODE,
                    [0x02, 0x01, 0x00]
                )
                logger.info(f"SetContentsTransferMode response: 0x{resp.code:04X}")
                time.sleep(2.0)  # Wait for camera to switch mode
            except Exception as e:
                logger.warning(f"SetContentsTransferMode failed: {e}")
                # Try to clear any stall
                try:
                    transport.clear_halt()
                except:
                    pass

            # Now try to get storage and files
            try:
                logger.info("Getting storage IDs...")
                storage_ids = self._get_storage_ids(transport, PTPOpCode, ResponseCode)
                logger.info(f"Storage IDs: {[hex(s) for s in storage_ids]}")

                if not storage_ids:
                    storage_ids = [0x00010001]  # Default SD card

                # Get all image files
                all_images = []
                for sid in storage_ids:
                    images = self._enumerate_images(transport, sid, PTPOpCode, ResponseCode)
                    all_images.extend(images)
                    logger.info(f"Storage {hex(sid)}: {len(images)} images found")

                logger.info(f"Total images found: {len(all_images)}")

            except Exception as e:
                logger.error(f"Failed to enumerate files: {e}")
                self._disable_transfer_mode(transport, SDIOOpCode)
                self.error.emit(f"Failed to list files: {e}")
                self.finished_signal.emit(0, 0)
                return

            if not all_images:
                self._disable_transfer_mode(transport, SDIOOpCode)
                self.error.emit("No image files found on camera")
                self.finished_signal.emit(0, 0)
                return

            # Filter by time range
            filtered = []
            for img in all_images:
                capture_date = img.get('capture_date', '')
                if capture_date:
                    try:
                        # Parse date (format: YYYYMMDDTHHMMSS)
                        img_time = datetime.strptime(capture_date, '%Y%m%dT%H%M%S')
                        if self.start_time <= img_time <= self.end_time:
                            filtered.append(img)
                            logger.info(f"Matched: {img.get('filename')} @ {img_time}")
                    except Exception as e:
                        logger.debug(f"Date parse error: {e}")
                        filtered.append(img)
                else:
                    filtered.append(img)

            logger.info(f"Filtered to {len(filtered)} images in time range")

            if not filtered:
                self._disable_transfer_mode(transport, SDIOOpCode)
                self.error.emit(f"No images found between {self.start_time} and {self.end_time}")
                self.finished_signal.emit(0, 0)
                return

            # Limit count and download
            to_download = filtered[:self.max_count]
            total = len(to_download)
            success_count = 0

            os.makedirs(self.save_dir, exist_ok=True)

            for i, img in enumerate(to_download):
                self.progress.emit(i + 1, total)
                logger.info(f"Downloading {i+1}/{total}: {img.get('filename')}")

                try:
                    save_path = self._download_file(transport, img, PTPOpCode, ResponseCode)
                    if save_path:
                        self.file_downloaded.emit(save_path)
                        success_count += 1
                        logger.info(f"Saved: {save_path}")
                except Exception as e:
                    logger.error(f"Download failed: {e}")

            # Disable transfer mode
            self._disable_transfer_mode(transport, SDIOOpCode)

            self.finished_signal.emit(success_count, total)

        except Exception as e:
            logger.exception(f"Download error: {e}")
            self.error.emit(f"Download error: {str(e)}")
            self.finished_signal.emit(0, 0)

    def _disable_transfer_mode(self, transport, SDIOOpCode):
        """Disable content transfer mode"""
        try:
            logger.info("Disabling Content Transfer Mode...")
            transport.send(
                SDIOOpCode.SET_CONTENTS_TRANSFER_MODE,
                [0x02, 0x00, 0x00]  # MODE_OFF
            )
        except Exception as e:
            logger.debug(f"Disable transfer mode: {e}")

    def _get_storage_ids(self, transport, PTPOpCode, ResponseCode) -> list:
        """Get storage IDs using PTP command"""
        resp, data = transport.receive(PTPOpCode.GET_STORAGE_ID)
        if resp.code != ResponseCode.OK or len(data) < 4:
            return []
        count = struct.unpack_from("<I", data, 0)[0]
        if count == 0:
            return []
        return list(struct.unpack_from(f"<{count}I", data, 4))

    def _get_object_handles(self, transport, storage_id, format_code, parent, PTPOpCode, ResponseCode) -> list:
        """Get object handles using PTP command"""
        resp, data = transport.receive(
            PTPOpCode.GET_OBJECT_HANDLES,
            [storage_id, format_code, parent]
        )
        if resp.code != ResponseCode.OK or len(data) < 4:
            return []
        count = struct.unpack_from("<I", data, 0)[0]
        if count == 0:
            return []
        return list(struct.unpack_from(f"<{count}I", data, 4))

    def _get_object_info(self, transport, handle, PTPOpCode, ResponseCode) -> dict:
        """Get object info and parse it"""
        resp, data = transport.receive(PTPOpCode.GET_OBJECT_INFO, [handle])
        if resp.code != ResponseCode.OK or len(data) < 53:
            return {}

        storage_id, obj_format, protect, obj_size = struct.unpack_from("<IHHI", data, 0)

        # Parse filename at offset 52
        offset = 52
        filename = ""
        if offset < len(data):
            name_len = data[offset]
            offset += 1
            if name_len > 0 and offset + name_len * 2 <= len(data):
                filename = data[offset:offset + (name_len - 1) * 2].decode(
                    "utf-16-le", errors="replace"
                )
                offset += name_len * 2

        # Parse capture date
        capture_date = ""
        if offset < len(data):
            date_len = data[offset]
            offset += 1
            if date_len > 0 and offset + date_len * 2 <= len(data):
                capture_date = data[offset:offset + (date_len - 1) * 2].decode(
                    "utf-16-le", errors="replace"
                )

        return {
            "handle": handle,
            "storage_id": storage_id,
            "format": obj_format,
            "size": obj_size,
            "filename": filename,
            "capture_date": capture_date,
        }

    def _enumerate_images(self, transport, storage_id, PTPOpCode, ResponseCode) -> list:
        """Enumerate all image files on storage"""
        all_images = []
        image_formats = [FORMAT_JPEG, FORMAT_ARW, 0x3800]  # JPEG, ARW, Undefined Image

        # Try hierarchical: get folders first, then images in each folder
        folders = self._get_object_handles(transport, storage_id, FORMAT_FOLDER, 0xFFFFFFFF, PTPOpCode, ResponseCode)
        logger.info(f"  Found {len(folders)} folders")

        for folder_handle in folders:
            for fmt in image_formats:
                handles = self._get_object_handles(transport, storage_id, fmt, folder_handle, PTPOpCode, ResponseCode)
                for h in handles:
                    try:
                        info = self._get_object_info(transport, h, PTPOpCode, ResponseCode)
                        if info:
                            all_images.append(info)
                    except Exception as e:
                        logger.debug(f"Failed to get info for handle {hex(h)}: {e}")

            # Also check subfolders
            subfolders = self._get_object_handles(transport, storage_id, FORMAT_FOLDER, folder_handle, PTPOpCode, ResponseCode)
            for sf in subfolders:
                for fmt in image_formats:
                    handles = self._get_object_handles(transport, storage_id, fmt, sf, PTPOpCode, ResponseCode)
                    for h in handles:
                        try:
                            info = self._get_object_info(transport, h, PTPOpCode, ResponseCode)
                            if info:
                                all_images.append(info)
                        except Exception as e:
                            logger.debug(f"Failed to get info for handle {hex(h)}: {e}")

        # If no images found via hierarchy, try flat query
        if not all_images:
            logger.info("  Trying flat query...")
            for fmt in image_formats:
                handles = self._get_object_handles(transport, storage_id, fmt, 0x00000000, PTPOpCode, ResponseCode)
                for h in handles:
                    try:
                        info = self._get_object_info(transport, h, PTPOpCode, ResponseCode)
                        if info:
                            all_images.append(info)
                    except Exception as e:
                        logger.debug(f"Failed to get info for handle {hex(h)}: {e}")

        # If still nothing, try all objects
        if not all_images:
            logger.info("  Trying all objects query...")
            handles = self._get_object_handles(transport, storage_id, 0, 0xFFFFFFFF, PTPOpCode, ResponseCode)
            logger.info(f"  Total object handles: {len(handles)}")
            for h in handles:
                try:
                    info = self._get_object_info(transport, h, PTPOpCode, ResponseCode)
                    if info and info.get('format') in image_formats:
                        all_images.append(info)
                    elif info:
                        fn = info.get('filename', '').lower()
                        if fn.endswith('.jpg') or fn.endswith('.jpeg') or fn.endswith('.arw'):
                            all_images.append(info)
                except Exception as e:
                    logger.debug(f"Failed to get info for handle {hex(h)}: {e}")

        # Sort by capture date (newest first)
        all_images.sort(key=lambda x: x.get('capture_date', ''), reverse=True)
        return all_images

    def _download_file(self, transport, img: dict, PTPOpCode, ResponseCode) -> str:
        """Download a single file"""
        handle = img.get('handle')
        if handle is None:
            return None

        filename = img.get('filename', f'IMG_{handle:08X}.jpg')

        # Make safe filename
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        save_path = os.path.join(self.save_dir, safe_name)

        # Avoid overwriting
        if os.path.exists(save_path):
            base, ext = os.path.splitext(safe_name)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(self.save_dir, f"{base}_{counter}{ext}")
                counter += 1

        # Download using PTP GetObject
        logger.info(f"Getting object data for handle: {hex(handle)}")
        resp, data = transport.receive(PTPOpCode.GET_OBJECT, [handle])

        if resp.code != ResponseCode.OK:
            logger.error(f"GetObject failed: {hex(resp.code)}")
            return None

        if data:
            with open(save_path, 'wb') as f:
                f.write(data)
            return save_path

        return None

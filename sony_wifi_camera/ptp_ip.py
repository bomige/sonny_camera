"""
Sony Camera PTP-IP Protocol Implementation
Based on Sony Camera Remote SDK (CrSDK) protocol analysis

PTP-IP (Picture Transfer Protocol over IP) implementation for Sony cameras.
"""

import socket
import struct
import threading
import time
import logging
from enum import IntEnum
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PtpIpPacketType(IntEnum):
    """PTP-IP Packet Types"""
    INIT_COMMAND_REQUEST = 0x0001
    INIT_COMMAND_ACK = 0x0002
    INIT_EVENT_REQUEST = 0x0003
    INIT_EVENT_ACK = 0x0004
    INIT_FAIL = 0x0005
    CMD_REQUEST = 0x0006
    CMD_RESPONSE = 0x0007
    EVENT = 0x0008
    START_DATA_PACKET = 0x0009
    DATA_PACKET = 0x000A
    CANCEL_TRANSACTION = 0x000B
    END_DATA_PACKET = 0x000C
    PROBE_REQUEST = 0x000D
    PROBE_RESPONSE = 0x000E


class PtpOpCode(IntEnum):
    """PTP Operation Codes"""
    GET_DEVICE_INFO = 0x1001
    OPEN_SESSION = 0x1002
    CLOSE_SESSION = 0x1003
    GET_STORAGE_IDS = 0x1004
    GET_STORAGE_INFO = 0x1005
    GET_NUM_OBJECTS = 0x1006
    GET_OBJECT_HANDLES = 0x1007
    GET_OBJECT_INFO = 0x1008
    GET_OBJECT = 0x1009
    GET_THUMB = 0x100A
    DELETE_OBJECT = 0x100B
    INITIATE_CAPTURE = 0x100E
    GET_DEVICE_PROP_DESC = 0x1014
    GET_DEVICE_PROP_VALUE = 0x1015
    SET_DEVICE_PROP_VALUE = 0x1016

    # Sony specific
    SONY_SDIO_CONNECT = 0x9201
    SONY_SDIO_GET_EXT_DEVICE_INFO = 0x9202
    SONY_GET_ALL_DEVICE_PROP_DATA = 0x9209
    SONY_SET_CONTROL_DEVICE_A = 0x920A
    SONY_GET_CONTROL_DEVICE_DESC = 0x920B
    SONY_SET_CONTROL_DEVICE_B = 0x920C
    SONY_GET_ALL_DEVICE_PROP_DATA_V2 = 0x9212


class PtpResponseCode(IntEnum):
    """PTP Response Codes"""
    OK = 0x2001
    GENERAL_ERROR = 0x2002
    SESSION_NOT_OPEN = 0x2003
    INVALID_TRANSACTION_ID = 0x2004
    OPERATION_NOT_SUPPORTED = 0x2005
    PARAMETER_NOT_SUPPORTED = 0x2006
    INCOMPLETE_TRANSFER = 0x2007
    INVALID_STORAGE_ID = 0x2008
    INVALID_OBJECT_HANDLE = 0x2009
    DEVICE_PROP_NOT_SUPPORTED = 0x200A
    INVALID_OBJECT_FORMAT_CODE = 0x200B
    STORE_FULL = 0x200C
    OBJECT_WRITE_PROTECTED = 0x200D
    STORE_READ_ONLY = 0x200E
    ACCESS_DENIED = 0x200F
    NO_THUMBNAIL_PRESENT = 0x2010
    SELF_TEST_FAILED = 0x2011
    PARTIAL_DELETION = 0x2012
    STORE_NOT_AVAILABLE = 0x2013
    SPECIFICATION_BY_FORMAT_NOT_SUPPORTED = 0x2014
    NO_VALID_OBJECT_INFO = 0x2015
    INVALID_CODE_FORMAT = 0x2016
    UNKNOWN_VENDOR_CODE = 0x2017
    CAPTURE_ALREADY_TERMINATED = 0x2018
    DEVICE_BUSY = 0x2019
    INVALID_PARENT_OBJECT = 0x201A
    INVALID_DEVICE_PROP_FORMAT = 0x201B
    INVALID_DEVICE_PROP_VALUE = 0x201C
    INVALID_PARAMETER = 0x201D
    SESSION_ALREADY_OPEN = 0x201E
    TRANSACTION_CANCELLED = 0x201F
    SPECIFICATION_OF_DESTINATION_UNSUPPORTED = 0x2020


class SonyDeviceProperty(IntEnum):
    """Sony Device Properties"""
    EXPOSURE_MODE = 0xD210
    F_NUMBER = 0xD211
    EXPOSURE_TIME = 0xD212  # Shutter Speed
    ISO = 0xD213
    EXPOSURE_COMPENSATION = 0xD214
    STILL_CAPTURE_MODE = 0xD215
    FOCUS_MODE = 0xD218
    WHITE_BALANCE = 0xD219
    FLASH_MODE = 0xD21A
    FOCUS_AREA = 0xD21B
    BATTERY_LEVEL = 0xD22D
    RECORDING_STATE = 0xD22F
    LIVE_VIEW_STATUS = 0xD231


class SonyCommand(IntEnum):
    """Sony Control Commands"""
    SHUTTER_RELEASE = 0x0001
    SHUTTER_HALF_PRESS = 0x0002
    SHUTTER_HALF_RELEASE = 0x0003
    AF_ON = 0x0004
    AF_OFF = 0x0005
    ZOOM_TELE = 0x0006
    ZOOM_WIDE = 0x0007
    ZOOM_STOP = 0x0008
    MOVIE_REC_START = 0x0009
    MOVIE_REC_STOP = 0x000A


@dataclass
class PtpIpPacket:
    """PTP-IP Packet Structure"""
    length: int
    packet_type: int
    payload: bytes

    def to_bytes(self) -> bytes:
        return struct.pack('<II', self.length, self.packet_type) + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PtpIpPacket':
        if len(data) < 8:
            raise ValueError("Packet too short")
        length, packet_type = struct.unpack('<II', data[:8])
        payload = data[8:length] if len(data) >= length else data[8:]
        return cls(length, packet_type, payload)


class SonyPtpIpCamera:
    """
    Sony Camera PTP-IP Connection Handler

    Implements PTP-IP protocol for Wi-Fi connection to Sony cameras.
    Based on Sony Camera Remote SDK (CrSDK).
    """

    PTP_IP_PORT = 15740  # Standard PTP-IP port
    SONY_PTP_PORT = 15740  # Sony uses standard port

    def __init__(self, ip_address: str, port: int = 15740):
        self.ip_address = ip_address
        self.port = port
        self.cmd_socket: Optional[socket.socket] = None
        self.event_socket: Optional[socket.socket] = None
        self.session_id: int = 0
        self.transaction_id: int = 0
        self.connection_number: int = 0
        self.connected: bool = False
        self._event_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._event_callback: Optional[Callable] = None
        self._guid = self._generate_guid()

    def _generate_guid(self) -> bytes:
        """Generate a GUID for the initiator"""
        import uuid
        return uuid.uuid4().bytes

    def _next_transaction_id(self) -> int:
        """Get next transaction ID"""
        self.transaction_id += 1
        if self.transaction_id > 0xFFFFFFFF:
            self.transaction_id = 1
        return self.transaction_id

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to the camera via PTP-IP

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to camera at {self.ip_address}:{self.port}")

            # Create command socket
            self.cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_socket.settimeout(timeout)
            self.cmd_socket.connect((self.ip_address, self.port))

            # Init Command Connection
            if not self._init_command_connection():
                return False

            # Create event socket
            self.event_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.event_socket.settimeout(timeout)
            self.event_socket.connect((self.ip_address, self.port))

            # Init Event Connection
            if not self._init_event_connection():
                return False

            # Open PTP Session
            if not self._open_session():
                return False

            # Sony SDIO Connect
            if not self._sony_sdio_connect():
                return False

            self.connected = True
            self._running = True

            # Start event listener thread
            self._event_thread = threading.Thread(target=self._event_listener, daemon=True)
            self._event_thread.start()

            logger.info("Connected to camera successfully")
            return True

        except socket.timeout:
            logger.error("Connection timeout")
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused - camera may not be in PC Remote mode")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def _init_command_connection(self) -> bool:
        """Initialize command connection with InitCommandRequest"""
        # Build InitCommandRequest packet
        # GUID (16 bytes) + Friendly Name (variable, null-terminated UTF-16LE) + Protocol Version (4 bytes)
        friendly_name = "PythonPtpIp\x00".encode('utf-16-le')
        protocol_version = struct.pack('<I', 0x00010000)  # Version 1.0

        payload = self._guid + friendly_name + protocol_version
        packet_length = 8 + len(payload)

        packet = struct.pack('<II', packet_length, PtpIpPacketType.INIT_COMMAND_REQUEST) + payload

        self.cmd_socket.send(packet)

        # Receive InitCommandAck
        response = self._recv_packet(self.cmd_socket)
        if response is None:
            logger.error("No response to InitCommandRequest")
            return False

        if response.packet_type == PtpIpPacketType.INIT_FAIL:
            logger.error("Init command failed")
            return False

        if response.packet_type != PtpIpPacketType.INIT_COMMAND_ACK:
            logger.error(f"Unexpected packet type: {response.packet_type}")
            return False

        # Parse connection number from response
        if len(response.payload) >= 4:
            self.connection_number = struct.unpack('<I', response.payload[:4])[0]
            logger.info(f"Connection number: {self.connection_number}")

        return True

    def _init_event_connection(self) -> bool:
        """Initialize event connection with InitEventRequest"""
        # Connection Number (4 bytes)
        payload = struct.pack('<I', self.connection_number)
        packet_length = 8 + len(payload)

        packet = struct.pack('<II', packet_length, PtpIpPacketType.INIT_EVENT_REQUEST) + payload

        self.event_socket.send(packet)

        # Receive InitEventAck
        response = self._recv_packet(self.event_socket)
        if response is None:
            logger.error("No response to InitEventRequest")
            return False

        if response.packet_type == PtpIpPacketType.INIT_FAIL:
            logger.error("Init event failed")
            return False

        if response.packet_type != PtpIpPacketType.INIT_EVENT_ACK:
            logger.error(f"Unexpected packet type: {response.packet_type}")
            return False

        return True

    def _open_session(self) -> bool:
        """Open PTP session"""
        self.session_id = 1

        response = self._send_command(PtpOpCode.OPEN_SESSION, [self.session_id])
        if response is None:
            return False

        if response[0] != PtpResponseCode.OK:
            # Session might already be open
            if response[0] == PtpResponseCode.SESSION_ALREADY_OPEN:
                logger.info("Session already open")
                return True
            logger.error(f"Open session failed: {hex(response[0])}")
            return False

        logger.info(f"Session opened: {self.session_id}")
        return True

    def _sony_sdio_connect(self) -> bool:
        """Sony SDIO Connect - establish Sony specific connection"""
        # Sony uses 0x9201 for SDIO connect
        # Parameters: Phase=1, Version
        phase = 1
        version = 0x012C  # v3.0 (300)

        response = self._send_command(PtpOpCode.SONY_SDIO_CONNECT, [phase, version])
        if response is None:
            return False

        if response[0] != PtpResponseCode.OK:
            logger.warning(f"Sony SDIO connect phase 1 response: {hex(response[0])}")

        # Phase 2
        phase = 2
        response = self._send_command(PtpOpCode.SONY_SDIO_CONNECT, [phase, version])
        if response is None:
            return False

        logger.info("Sony SDIO connection established")
        return True

    def _send_command(self, opcode: int, params: list = None, data: bytes = None) -> Optional[Tuple]:
        """
        Send PTP command and receive response

        Args:
            opcode: PTP operation code
            params: List of 32-bit parameters (max 5)
            data: Optional data phase payload

        Returns:
            Tuple of (response_code, params...) or None on error
        """
        if self.cmd_socket is None:
            return None

        params = params or []
        transaction_id = self._next_transaction_id()

        # Build command request packet
        # Data Phase Info (4 bytes) + Operation Code (2 bytes) + Transaction ID (4 bytes) + Params
        data_phase_info = 0x00000001 if data else 0x00000002  # 1=has data, 2=no data

        payload = struct.pack('<IHI', data_phase_info, opcode, transaction_id)
        for param in params[:5]:  # Max 5 params
            payload += struct.pack('<I', param)

        packet_length = 8 + len(payload)
        packet = struct.pack('<II', packet_length, PtpIpPacketType.CMD_REQUEST) + payload

        try:
            self.cmd_socket.send(packet)

            # If we have data to send
            if data:
                self._send_data(transaction_id, data)

            # Receive response (may include data phase)
            return self._recv_response(transaction_id)

        except Exception as e:
            logger.error(f"Send command failed: {e}")
            return None

    def _send_data(self, transaction_id: int, data: bytes):
        """Send data phase"""
        # Start Data Packet
        payload = struct.pack('<IQ', transaction_id, len(data))
        packet_length = 8 + len(payload)
        packet = struct.pack('<II', packet_length, PtpIpPacketType.START_DATA_PACKET) + payload
        self.cmd_socket.send(packet)

        # End Data Packet with actual data
        payload = struct.pack('<I', transaction_id) + data
        packet_length = 8 + len(payload)
        packet = struct.pack('<II', packet_length, PtpIpPacketType.END_DATA_PACKET) + payload
        self.cmd_socket.send(packet)

    def _recv_response(self, expected_transaction_id: int) -> Optional[Tuple]:
        """Receive command response, handling data phase if present"""
        received_data = b''

        while True:
            pkt = self._recv_packet(self.cmd_socket)
            if pkt is None:
                return None

            if pkt.packet_type == PtpIpPacketType.START_DATA_PACKET:
                # Data phase starting
                if len(pkt.payload) >= 12:
                    trans_id, total_length = struct.unpack('<IQ', pkt.payload[:12])
                continue

            elif pkt.packet_type == PtpIpPacketType.DATA_PACKET:
                # Data packet
                if len(pkt.payload) >= 4:
                    trans_id = struct.unpack('<I', pkt.payload[:4])[0]
                    received_data += pkt.payload[4:]
                continue

            elif pkt.packet_type == PtpIpPacketType.END_DATA_PACKET:
                # End of data
                if len(pkt.payload) >= 4:
                    trans_id = struct.unpack('<I', pkt.payload[:4])[0]
                    received_data += pkt.payload[4:]
                continue

            elif pkt.packet_type == PtpIpPacketType.CMD_RESPONSE:
                # Command response
                if len(pkt.payload) >= 6:
                    response_code, trans_id = struct.unpack('<HI', pkt.payload[:6])
                    params = []
                    offset = 6
                    while offset + 4 <= len(pkt.payload):
                        param = struct.unpack('<I', pkt.payload[offset:offset+4])[0]
                        params.append(param)
                        offset += 4
                    return (response_code, *params, received_data) if received_data else (response_code, *params)

            else:
                logger.debug(f"Unexpected packet type in response: {pkt.packet_type}")

        return None

    def _recv_packet(self, sock: socket.socket) -> Optional[PtpIpPacket]:
        """Receive a PTP-IP packet"""
        try:
            # First read the header (8 bytes: length + type)
            header = b''
            while len(header) < 8:
                chunk = sock.recv(8 - len(header))
                if not chunk:
                    return None
                header += chunk

            length, packet_type = struct.unpack('<II', header)

            # Read payload
            payload = b''
            remaining = length - 8
            while len(payload) < remaining:
                chunk = sock.recv(min(remaining - len(payload), 65536))
                if not chunk:
                    break
                payload += chunk

            return PtpIpPacket(length, packet_type, payload)

        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Receive packet failed: {e}")
            return None

    def _event_listener(self):
        """Background thread to listen for events"""
        self.event_socket.settimeout(1.0)

        while self._running:
            try:
                pkt = self._recv_packet(self.event_socket)
                if pkt and pkt.packet_type == PtpIpPacketType.EVENT:
                    self._handle_event(pkt)
            except:
                pass

    def _handle_event(self, packet: PtpIpPacket):
        """Handle incoming event"""
        if len(packet.payload) >= 6:
            event_code, trans_id = struct.unpack('<HI', packet.payload[:6])
            params = []
            offset = 6
            while offset + 4 <= len(packet.payload):
                param = struct.unpack('<I', packet.payload[offset:offset+4])[0]
                params.append(param)
                offset += 4

            logger.debug(f"Event: code={hex(event_code)}, params={params}")

            if self._event_callback:
                self._event_callback(event_code, params)

    def disconnect(self):
        """Disconnect from camera"""
        self._running = False

        if self.connected and self.session_id:
            try:
                self._send_command(PtpOpCode.CLOSE_SESSION)
            except:
                pass

        if self.cmd_socket:
            try:
                self.cmd_socket.close()
            except:
                pass
            self.cmd_socket = None

        if self.event_socket:
            try:
                self.event_socket.close()
            except:
                pass
            self.event_socket = None

        self.connected = False
        self.session_id = 0
        logger.info("Disconnected from camera")

    def capture(self) -> bool:
        """
        Capture a photo

        Returns:
            True if capture initiated successfully
        """
        if not self.connected:
            logger.error("Not connected")
            return False

        # Half-press shutter (AF)
        response = self._send_command(
            PtpOpCode.SONY_SET_CONTROL_DEVICE_B,
            [SonyCommand.SHUTTER_HALF_PRESS]
        )

        time.sleep(0.5)  # Wait for AF

        # Full press shutter
        response = self._send_command(
            PtpOpCode.SONY_SET_CONTROL_DEVICE_B,
            [SonyCommand.SHUTTER_RELEASE]
        )

        if response and response[0] == PtpResponseCode.OK:
            logger.info("Capture initiated")
            return True

        # Alternative method using INITIATE_CAPTURE
        response = self._send_command(PtpOpCode.INITIATE_CAPTURE, [0, 0])

        if response and response[0] == PtpResponseCode.OK:
            logger.info("Capture initiated (PTP)")
            return True

        logger.error("Capture failed")
        return False

    def get_device_info(self) -> Optional[dict]:
        """Get device information"""
        if not self.connected:
            return None

        response = self._send_command(PtpOpCode.GET_DEVICE_INFO)
        if response is None or response[0] != PtpResponseCode.OK:
            return None

        # Parse device info from data
        if len(response) > 1 and isinstance(response[-1], bytes):
            return self._parse_device_info(response[-1])

        return {}

    def _parse_device_info(self, data: bytes) -> dict:
        """Parse device info data"""
        info = {}
        try:
            offset = 0
            # Standard Version
            info['standard_version'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            # Vendor Extension ID
            info['vendor_extension_id'] = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            # Vendor Extension Version
            info['vendor_extension_version'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            # Skip rest for now (strings are complex to parse)
        except:
            pass
        return info

    def get_property(self, prop_code: int) -> Optional[int]:
        """Get device property value"""
        if not self.connected:
            return None

        response = self._send_command(PtpOpCode.GET_DEVICE_PROP_VALUE, [prop_code])
        if response is None or response[0] != PtpResponseCode.OK:
            return None

        # Value is in the data
        if len(response) > 1 and isinstance(response[-1], bytes):
            data = response[-1]
            if len(data) >= 4:
                return struct.unpack('<I', data[:4])[0]
            elif len(data) >= 2:
                return struct.unpack('<H', data[:2])[0]

        return None

    def get_battery_level(self) -> Optional[int]:
        """Get battery level percentage"""
        return self.get_property(SonyDeviceProperty.BATTERY_LEVEL)

    def get_liveview_frame(self) -> Optional[bytes]:
        """
        Get a single LiveView frame

        Returns:
            JPEG image data or None
        """
        if not self.connected:
            return None

        # Sony uses a specific command for LiveView
        # This is a simplified implementation
        response = self._send_command(0x9205)  # GetLiveViewImage

        if response and len(response) > 1 and isinstance(response[-1], bytes):
            return response[-1]

        return None

    def set_event_callback(self, callback: Callable):
        """Set callback function for camera events"""
        self._event_callback = callback

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Simple connection test
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ptp_ip.py <camera_ip>")
        sys.exit(1)

    camera_ip = sys.argv[1]

    camera = SonyPtpIpCamera(camera_ip)
    if camera.connect():
        print("Connected!")

        # Get device info
        info = camera.get_device_info()
        print(f"Device Info: {info}")

        # Get battery level
        battery = camera.get_battery_level()
        if battery:
            print(f"Battery: {battery}%")

        input("Press Enter to take a photo...")
        camera.capture()

        camera.disconnect()
    else:
        print("Connection failed")

"""
Camera Discovery
네트워크에서 Sony 카메라 자동 검색 (SSDP/mDNS)
"""

import socket
import struct
import threading
import time
import logging
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredCamera:
    """Discovered camera information"""
    ip: str
    port: int
    name: str
    model: str
    uuid: str

    def __str__(self):
        return f"{self.model} ({self.ip}:{self.port})"


class CameraDiscovery:
    """
    Sony Camera Discovery using SSDP (Simple Service Discovery Protocol)

    Sony 카메라는 SSDP를 통해 네트워크에서 검색 가능합니다.
    """

    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900

    # Sony camera search targets
    SEARCH_TARGETS = [
        "urn:schemas-sony-com:service:ScalarWebAPI:1",
        "urn:schemas-upnp-org:device:MediaServer:1",
        "ssdp:all"
    ]

    def __init__(self):
        self.discovered_cameras: List[DiscoveredCamera] = []
        self._discovery_callback: Optional[Callable] = None
        self._running = False

    def discover(self, timeout: float = 5.0, callback: Callable = None) -> List[DiscoveredCamera]:
        """
        Discover Sony cameras on the network

        Args:
            timeout: Discovery timeout in seconds
            callback: Optional callback for each discovered camera

        Returns:
            List of discovered cameras
        """
        self.discovered_cameras = []
        self._discovery_callback = callback

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        try:
            # Bind to any address
            sock.bind(('', 0))

            # Send M-SEARCH for each target
            for target in self.SEARCH_TARGETS:
                self._send_msearch(sock, target)

            # Receive responses
            end_time = time.time() + timeout
            while time.time() < end_time:
                try:
                    data, addr = sock.recvfrom(4096)
                    self._parse_response(data.decode('utf-8', errors='ignore'), addr[0])
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"Error receiving SSDP response: {e}")

        finally:
            sock.close()

        return self.discovered_cameras

    def _send_msearch(self, sock: socket.socket, search_target: str):
        """Send SSDP M-SEARCH request"""
        message = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 3\r\n"
            f"ST: {search_target}\r\n"
            "\r\n"
        )

        try:
            sock.sendto(message.encode('utf-8'), (self.SSDP_ADDR, self.SSDP_PORT))
            logger.debug(f"Sent M-SEARCH for {search_target}")
        except Exception as e:
            logger.error(f"Failed to send M-SEARCH: {e}")

    def _parse_response(self, response: str, ip: str):
        """Parse SSDP response"""
        # Check if it's a Sony device
        if 'sony' not in response.lower():
            return

        # Parse headers
        headers = {}
        for line in response.split('\r\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.upper().strip()] = value.strip()

        # Check for HTTP API port
        port = 8080  # Default Sony Camera Remote API port

        # Extract model from response
        model = "Sony Camera"
        server = headers.get('SERVER', '')
        if 'Sony' in server:
            model = server

        # Extract UUID
        uuid = headers.get('USN', '')

        # Check if already discovered
        for cam in self.discovered_cameras:
            if cam.ip == ip:
                return

        camera = DiscoveredCamera(
            ip=ip,
            port=port,
            name=model,
            model=model,
            uuid=uuid
        )

        self.discovered_cameras.append(camera)
        logger.info(f"Discovered camera: {camera}")

        if self._discovery_callback:
            self._discovery_callback(camera)


class NetworkScanner:
    """
    Simple network scanner to find devices with open HTTP API port

    SSDP가 작동하지 않을 때 포트 스캔으로 카메라 찾기
    """

    HTTP_API_PORT = 8080

    def __init__(self):
        self.found_devices: List[str] = []

    def scan_subnet(self, base_ip: str = None, timeout: float = 0.5,
                    callback: Callable = None) -> List[str]:
        """
        Scan local subnet for devices with HTTP API port open

        Args:
            base_ip: Base IP (e.g., "192.168.1"). Auto-detect if None.
            timeout: Connection timeout per host
            callback: Optional callback for progress

        Returns:
            List of IPs with HTTP API port open
        """
        self.found_devices = []

        if base_ip is None:
            base_ip = self._get_local_subnet()

        if not base_ip:
            logger.error("Could not determine local subnet")
            return []

        logger.info(f"Scanning subnet {base_ip}.0/24 for Sony cameras...")

        threads = []
        for i in range(1, 255):
            ip = f"{base_ip}.{i}"
            t = threading.Thread(target=self._check_port, args=(ip, timeout))
            t.daemon = True
            threads.append(t)
            t.start()

            # Limit concurrent threads
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []

                if callback:
                    callback(i, 254, len(self.found_devices))

        # Wait for remaining threads
        for t in threads:
            t.join()

        return self.found_devices

    def _check_port(self, ip: str, timeout: float):
        """Check if HTTP API port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, self.HTTP_API_PORT))
            sock.close()

            if result == 0:
                logger.info(f"Found device at {ip}:{self.HTTP_API_PORT}")
                self.found_devices.append(ip)

        except Exception:
            pass

    def _get_local_subnet(self) -> Optional[str]:
        """Get local subnet base IP"""
        try:
            # Connect to external address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Extract subnet (first 3 octets)
            parts = local_ip.split('.')
            if len(parts) == 4:
                return '.'.join(parts[:3])

        except Exception as e:
            logger.error(f"Failed to get local subnet: {e}")

        return None


def discover_cameras(timeout: float = 5.0) -> List[DiscoveredCamera]:
    """
    Convenience function to discover cameras

    Args:
        timeout: Discovery timeout

    Returns:
        List of discovered cameras
    """
    discovery = CameraDiscovery()
    cameras = discovery.discover(timeout=timeout)

    # If SSDP didn't find anything, try port scanning
    if not cameras:
        logger.info("SSDP discovery found no cameras, trying port scan...")
        scanner = NetworkScanner()
        ips = scanner.scan_subnet(timeout=0.3)

        for ip in ips:
            cameras.append(DiscoveredCamera(
                ip=ip,
                port=8080,
                name="Sony Camera",
                model="Unknown",
                uuid=""
            ))

    return cameras


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Discovering Sony cameras on network...")
    cameras = discover_cameras(timeout=5.0)

    if cameras:
        print(f"\nFound {len(cameras)} camera(s):")
        for i, cam in enumerate(cameras, 1):
            print(f"  [{i}] {cam}")
    else:
        print("No cameras found")

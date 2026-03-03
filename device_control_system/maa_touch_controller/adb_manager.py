"""
MAA Touch Controller - ADB Manager

Pure Python implementation of ADB device management
"""

import subprocess
import logging
import time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class AdbManager:
    """ADB device manager for touch control system"""

    def __init__(self, adb_path: str = "adb"):
        """
        Initialize ADB manager

        Args:
            adb_path (str): Path to ADB executable (default: "adb")
        """
        self.adb_path = adb_path
        self.connected_devices = set()

    def _run_adb_command(self, args: List[str], timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Run ADB command and return result

        Args:
            args (List[str]): ADB command arguments
            timeout (int): Command timeout in seconds

        Returns:
            Tuple[bool, str, str]: (success, stdout, stderr)
        """
        try:
            cmd = [self.adb_path] + args
            logger.debug(f"Running ADB command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if not success:
                logger.warning(f"ADB command failed: {stderr}")

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out after {timeout} seconds")
            return False, "", "Command timed out"
        except FileNotFoundError:
            logger.error(f"ADB executable not found: {self.adb_path}")
            return False, "", f"ADB not found: {self.adb_path}"
        except Exception as e:
            logger.error(f"ADB command failed with exception: {e}")
            return False, "", str(e)

    def get_connected_devices(self) -> List[Dict[str, str]]:
        """
        Get list of connected ADB devices

        Returns:
            List[Dict[str, str]]: List of devices with 'id' and 'status' keys
        """
        success, stdout, stderr = self._run_adb_command(["devices"])
        if not success:
            return []

        devices = []
        lines = stdout.split('\n')

        # Skip header line
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith('*') and 'offline' not in line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    devices.append({
                        'id': parts[0],
                        'status': parts[1]
                    })

        return devices

    def connect_device(self, device_id: str) -> bool:
        """
        Connect to ADB device

        Args:
            device_id (str): Device ID or IP address

        Returns:
            bool: True if connection successful
        """
        # If it's an IP address, try to connect first
        if ':' in device_id:
            success, _, _ = self._run_adb_command(["connect", device_id])
            if not success:
                return False

        # Verify device is accessible
        success, _, _ = self._run_adb_command(["-s", device_id, "shell", "echo", "connected"])
        if success:
            self.connected_devices.add(device_id)
            return True

        return False

    def disconnect_device(self, device_id: str) -> None:
        """
        Disconnect from ADB device

        Args:
            device_id (str): Device ID to disconnect
        """
        self.connected_devices.discard(device_id)

    def is_device_connected(self, device_id: str) -> bool:
        """
        Check if device is connected

        Args:
            device_id (str): Device ID to check

        Returns:
            bool: True if device is connected
        """
        return device_id in self.connected_devices

    def get_device_abi(self, device_id: str) -> List[str]:
        """
        Get device CPU architecture information

        Args:
            device_id (str): Device ID

        Returns:
            List[str]: List of supported ABIs
        """
        # Try abilist first
        success, stdout, _ = self._run_adb_command([
            "-s", device_id, "shell", "getprop", "ro.product.cpu.abilist"
        ])

        if success and stdout.strip():
            return [abi.strip() for abi in stdout.split(',') if abi.strip()]

        # Fallback to single ABI
        success, stdout, _ = self._run_adb_command([
            "-s", device_id, "shell", "getprop", "ro.product.cpu.abi"
        ])

        if success and stdout.strip():
            return [stdout.strip()]

        return []

    def get_screen_resolution(self, device_id: str) -> Tuple[int, int]:
        """
        Get device screen resolution

        Args:
            device_id (str): Device ID

        Returns:
            Tuple[int, int]: (width, height) in pixels
        """
        # Try wm size command
        success, stdout, _ = self._run_adb_command([
            "-s", device_id, "shell", "wm", "size"
        ])

        if success:
            import re
            match = re.search(r'Physical size: (\d+)x(\d+)', stdout)
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                return width, height

        # Default fallback
        return 1080, 1920

    def get_device_orientation(self, device_id: str) -> int:
        """
        Get device orientation

        Args:
            device_id (str): Device ID

        Returns:
            int: Orientation (0, 1, 2, 3)
        """
        success, stdout, _ = self._run_adb_command([
            "-s", device_id, "shell", "dumpsys", "input"
        ])

        if success:
            import re
            match = re.search(r'SurfaceOrientation:\s*(\d+)', stdout)
            if match:
                return int(match.group(1)) % 4

        return 0

    def push_file(self, device_id: str, local_path: str, remote_path: str) -> bool:
        """
        Push file to device

        Args:
            device_id (str): Device ID
            local_path (str): Local file path
            remote_path (str): Remote file path on device

        Returns:
            bool: True if successful
        """
        success, _, _ = self._run_adb_command([
            "-s", device_id, "push", local_path, remote_path
        ])
        return success

    def execute_shell_command(self, device_id: str, command: str) -> str:
        """
        Execute shell command on device

        Args:
            device_id (str): Device ID
            command (str): Shell command to execute

        Returns:
            str: Command output
        """
        success, stdout, _ = self._run_adb_command([
            "-s", device_id, "shell", command
        ])
        return stdout if success else ""
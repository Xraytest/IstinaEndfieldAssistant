"""
MAA Touch Controller - Minitouch Implementation

Pure Python implementation of Minitouch touch control system using interactive shell session
"""

import os
import time
import logging
import subprocess
import threading
from typing import Tuple, Optional
from .adb_manager import AdbManager

logger = logging.getLogger(__name__)


class MinitouchController:
    """Minitouch-based touch controller for Android devices"""

    def __init__(self, adb_manager: AdbManager):
        """
        Initialize Minitouch controller

        Args:
            adb_manager (AdbManager): ADB manager instance
        """
        self.adb_manager = adb_manager
        self.device_id = ""
        self.is_connected = False

        # Minitouch properties
        self.max_contacts = 0
        self.max_x = 0
        self.max_y = 0
        self.max_pressure = 32767
        self.x_scaling = 1.0
        self.y_scaling = 1.0
        self.orientation = 0
        self.screen_width = 0
        self.screen_height = 0

        # Minitouch process (interactive shell)
        self.minitouch_process = None
        self.minitouch_thread = None
        self.minitouch_running = False
        self.minitouch_lock = threading.Lock()
        self.minitouch_available = False

    def connect(self, device_id: str) -> bool:
        """
        Connect to device and initialize Minitouch

        Args:
            device_id (str): Device ID

        Returns:
            bool: True if connection successful
        """
        try:
            self.device_id = device_id

            # Get device information
            self.screen_width, self.screen_height = self.adb_manager.get_screen_resolution(device_id)
            self.orientation = self.adb_manager.get_device_orientation(device_id)

            # Initialize Minitouch
            success = self._init_minitouch()
            if success:
                self.is_connected = True
                return True

            logger.warning("Minitouch initialization failed, falling back to basic ADB mode")
            self.is_connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to connect Minitouch controller: {e}")
            self.is_connected = False
            return False

    def _init_minitouch(self) -> bool:
        """
        Initialize Minitouch service on device using interactive shell session

        Returns:
            bool: True if successful
        """
        try:
            # Get device CPU architecture
            abis = self.adb_manager.get_device_abi(self.device_id)
            supported_archs = ['x86_64', 'x86', 'arm64-v8a', 'armeabi-v7a', 'armeabi']
            selected_arch = 'armeabi-v7a'  # Default

            for arch in supported_archs:
                if arch in abis:
                    selected_arch = arch
                    break

            logger.info(f"Selected minitouch architecture: {selected_arch}")

            # Get local minitouch path
            local_minitouch_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'minitouch_resources',
                selected_arch,
                'minitouch'
            )

            if not os.path.exists(local_minitouch_path):
                logger.error(f"Minitouch binary not found: {local_minitouch_path}")
                return False

            # Push minitouch to device
            remote_minitouch_path = '/data/local/tmp/minitouch'
            if not self.adb_manager.push_file(self.device_id, local_minitouch_path, remote_minitouch_path):
                logger.error("Failed to push minitouch binary to device")
                return False

            # Set execute permissions
            self.adb_manager.execute_shell_command(self.device_id, f"chmod 700 {remote_minitouch_path}")

            # Start interactive shell session with minitouch
            return self._start_interactive_minitouch(remote_minitouch_path)

        except Exception as e:
            logger.error(f"Minitouch initialization failed: {e}")
            return False

    def _start_interactive_minitouch(self, remote_minitouch_path: str) -> bool:
        """
        Start Minitouch in interactive shell session (same as MAA approach)

        Args:
            remote_minitouch_path (str): Remote minitouch path on device

        Returns:
            bool: True if successful
        """
        try:
            # Build ADB command for interactive shell
            adb_path = self.adb_manager.adb_path
            cmd = [adb_path, "-s", self.device_id, "shell", remote_minitouch_path]

            logger.info(f"Starting interactive minitouch: {' '.join(cmd)}")

            # Start process with stdin/stdout pipes
            self.minitouch_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )

            # Start thread to read output
            self.minitouch_running = True
            self.minitouch_thread = threading.Thread(target=self._read_minitouch_output)
            self.minitouch_thread.daemon = True
            self.minitouch_thread.start()

            # Wait for connection marker ($) with timeout
            timeout = 5.0
            start_time = time.time()
            while time.time() - start_time < timeout:
                with self.minitouch_lock:
                    if self.minitouch_available:
                        break
                time.sleep(0.1)

            with self.minitouch_lock:
                if not self.minitouch_available:
                    logger.warning("Minitouch did not become available within timeout")
                    self._stop_minitouch()
                    return False

            logger.info("Minitouch interactive session started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start interactive minitouch: {e}")
            self._stop_minitouch()
            return False

    def _read_minitouch_output(self):
        """Thread function to read minitouch output continuously"""
        pipe_str = ""
        found_dollar = False
        found_caret = False

        try:
            while self.minitouch_running and self.minitouch_process:
                try:
                    # Read output with timeout
                    char = self.minitouch_process.stdout.read(1)
                    if not char:
                        break

                    pipe_str += char

                    # Check for connection marker $
                    if '$' in pipe_str and not found_dollar:
                        found_dollar = True
                        logger.debug("Found $ marker (minitouch connected)")

                    # Check for properties marker ^
                    if '^' in pipe_str and not found_caret:
                        found_caret = True
                        self._parse_minitouch_properties(pipe_str)

                    with self.minitouch_lock:
                        self.minitouch_available = found_dollar and found_caret

                except Exception as e:
                    logger.debug(f"Error reading minitouch output: {e}")
                    break

        except Exception as e:
            logger.error(f"Minitouch output reader thread error: {e}")
        finally:
            with self.minitouch_lock:
                self.minitouch_available = False

    def _parse_minitouch_properties(self, pipe_str: str):
        """
        Parse minitouch properties from output

        Args:
            pipe_str (str): Output string from minitouch
        """
        try:
            # Find ^ marker and parse properties
            s_pos = pipe_str.find('^')
            if s_pos == -1:
                return

            e_pos = pipe_str.find('\n', s_pos)
            if e_pos == -1:
                e_pos = len(pipe_str)

            key_info = pipe_str[s_pos + 1:e_pos].strip()
            logger.info(f"Minitouch properties: {key_info}")

            parts = key_info.split()
            if len(parts) >= 4:
                try:
                    self.max_contacts = int(parts[0])
                    size1 = int(parts[1])
                    size2 = int(parts[2])
                    self.max_pressure = int(parts[3])

                    # Some emulators swap x and y, take larger as max_x
                    self.max_x = max(size1, size2)
                    self.max_y = min(size1, size2)

                    # Calculate scaling factors
                    if self.screen_width > 0 and self.screen_height > 0:
                        self.x_scaling = self.max_x / self.screen_width
                        self.y_scaling = self.max_y / self.screen_height
                    else:
                        self.x_scaling = 1.0
                        self.y_scaling = 1.0

                    logger.info(f"Minitouch initialized: maxX={self.max_x}, maxY={self.max_y}, maxPressure={self.max_pressure}")
                    logger.info(f"Scaling: x={self.x_scaling:.4f}, y={self.y_scaling:.4f}, orientation={self.orientation}")

                except (ValueError, IndexError) as e:
                    logger.error(f"Failed to parse minitouch properties: {e}")

        except Exception as e:
            logger.error(f"Error parsing minitouch properties: {e}")

    def _send_minitouch_command(self, command: str) -> bool:
        """
        Send command to minitouch via interactive shell

        Args:
            command (str): Command to send

        Returns:
            bool: True if successful
        """
        try:
            with self.minitouch_lock:
                if not self.minitouch_process or not self.minitouch_available:
                    return False

                try:
                    self.minitouch_process.stdin.write(command + '\n')
                    self.minitouch_process.stdin.flush()
                    return True
                except Exception as e:
                    logger.error(f"Failed to write to minitouch: {e}")
                    self.minitouch_available = False
                    return False

        except Exception as e:
            logger.error(f"Error sending minitouch command: {e}")
            return False

    def _stop_minitouch(self):
        """Stop minitouch process"""
        self.minitouch_running = False

        if self.minitouch_process:
            try:
                self.minitouch_process.stdin.close()
                self.minitouch_process.terminate()
                self.minitouch_process.wait(timeout=2)
            except:
                try:
                    self.minitouch_process.kill()
                except:
                    pass
            finally:
                self.minitouch_process = None

        if self.minitouch_thread:
            self.minitouch_thread.join(timeout=1)
            self.minitouch_thread = None

        with self.minitouch_lock:
            self.minitouch_available = False

    def _scale_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """
        Scale coordinates based on device properties and orientation

        Args:
            x (int): Original X coordinate
            y (int): Original Y coordinate

        Returns:
            Tuple[int, int]: Scaled coordinates
        """
        scaled_x = int(x * self.x_scaling)
        scaled_y = int(y * self.y_scaling)

        # Handle device orientation
        if self.orientation == 0:
            return scaled_x, scaled_y
        elif self.orientation == 1:
            return self.max_y - scaled_y, scaled_x
        elif self.orientation == 2:
            return self.max_x - scaled_x, self.max_y - scaled_y
        elif self.orientation == 3:
            return scaled_y, self.max_x - scaled_x
        else:
            return scaled_x, scaled_y

    def click(self, x: int, y: int) -> bool:
        """
        Perform click operation

        Args:
            x (int): X coordinate
            y (int): Y coordinate

        Returns:
            bool: True if successful
        """
        if not self.is_connected:
            raise RuntimeError("Device not connected")

        try:
            # Validate coordinates
            x = max(0, min(x, self.screen_width - 1))
            y = max(0, min(y, self.screen_height - 1))

            with self.minitouch_lock:
                if self.minitouch_available:
                    # Use Minitouch mode
                    scaled_x, scaled_y = self._scale_coordinates(x, y)

                    # Build minitouch command sequence
                    commands = [
                        f"d 0 {scaled_x} {scaled_y} {self.max_pressure}",
                        "c",
                        "w 50",
                        "u 0",
                        "c"
                    ]

                    for cmd in commands:
                        if not self._send_minitouch_command(cmd):
                            break

                    time.sleep(0.1)
                    return True
                else:
                    # Fallback to basic ADB mode
                    self.adb_manager.execute_shell_command(
                        self.device_id,
                        f"input tap {x} {y}"
                    )
                    time.sleep(0.1)
                    return True

        except Exception as e:
            logger.error(f"Click operation failed: {e}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 200) -> bool:
        """
        Perform swipe operation

        Args:
            x1 (int): Starting X coordinate
            y1 (int): Starting Y coordinate
            x2 (int): Ending X coordinate
            y2 (int): Ending Y coordinate
            duration (int): Duration in milliseconds (default: 200)

        Returns:
            bool: True if successful
        """
        if not self.is_connected:
            raise RuntimeError("Device not connected")

        try:
            # Validate starting coordinates
            x1 = max(0, min(x1, self.screen_width - 1))
            y1 = max(0, min(y1, self.screen_height - 1))
            x2 = max(0, min(x2, self.screen_width - 1))
            y2 = max(0, min(y2, self.screen_height - 1))

            with self.minitouch_lock:
                if self.minitouch_available:
                    # Use Minitouch mode
                    start_x, start_y = self._scale_coordinates(x1, y1)
                    end_x, end_y = self._scale_coordinates(x2, y2)

                    # Calculate steps
                    steps = max(1, duration // 50)
                    commands = []

                    # Touch down
                    commands.append(f"d 0 {start_x} {start_y} {self.max_pressure}")
                    commands.append("c")

                    # Intermediate move points
                    for i in range(1, steps + 1):
                        progress = i / steps
                        current_x = int(start_x + (end_x - start_x) * progress)
                        current_y = int(start_y + (end_y - start_y) * progress)
                        commands.append(f"m 0 {current_x} {current_y} {self.max_pressure}")
                        commands.append("c")

                        if i < steps:
                            commands.append("w 50")

                    # Touch up
                    commands.append("w 50")
                    commands.append("u 0")
                    commands.append("c")

                    # Send commands
                    for cmd in commands:
                        if not self._send_minitouch_command(cmd):
                            break

                    # Wait for completion
                    time.sleep(duration / 1000 + 0.1)
                    return True
                else:
                    # Fallback to basic ADB mode
                    self.adb_manager.execute_shell_command(
                        self.device_id,
                        f"input swipe {x1} {y1} {x2} {y2} {duration}"
                    )
                    time.sleep(duration / 1000 + 0.1)
                    return True

        except Exception as e:
            logger.error(f"Swipe operation failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect and cleanup resources"""
        if not self.is_connected:
            return

        self._stop_minitouch()

        # Cleanup minitouch binary on device
        try:
            self.adb_manager.execute_shell_command(
                self.device_id,
                "rm -f /data/local/tmp/minitouch"
            )
        except Exception as e:
            logger.warning(f"Failed to cleanup minitouch binary: {e}")

        self.is_connected = False
        self.device_id = ""

    def get_device_info(self) -> dict:
        """
        Get device information

        Returns:
            dict: Device information including screen dimensions and touch mode
        """
        if not self.is_connected:
            raise RuntimeError("Device not connected")

        with self.minitouch_lock:
            touch_mode = 'minitouch' if self.minitouch_available else 'adb'

        return {
            'device_id': self.device_id,
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'orientation': self.orientation,
            'touch_mode': touch_mode
        }
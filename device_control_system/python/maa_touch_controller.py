#!/usr/bin/env python3
"""
MAA Touch Controller - Python Interface

This module provides a Python interface to the MAA Touch Controller.
It uses subprocess to call the Node.js implementation.
"""

import subprocess
import json
import os
import sys
from typing import Optional, Dict, Any

class MaaTouchController:
    """
    Python interface for MAA Touch Controller

    This class provides a Python wrapper around the Node.js implementation
    of the MAA Touch Controller.
    """

    def __init__(self, adb_path: str, device_id: str):
        """
        Initialize the touch controller

        Args:
            adb_path (str): Path to ADB executable
            device_id (str): Device ID or IP address (e.g., "127.0.0.1:5555")
        """
        self.adb_path = adb_path
        self.device_id = device_id
        self._connected = False
        self._script_path = os.path.join(os.path.dirname(__file__), 'touch_controller.js')

        # Verify that the Node.js script exists
        if not os.path.exists(self._script_path):
            raise FileNotFoundError(f"Node.js script not found: {self._script_path}")

    def _run_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Run a Node.js command and return the result

        Args:
            command (str): Command to run
            **kwargs: Additional arguments to pass to the command

        Returns:
            Dict[str, Any]: Result from the Node.js script
        """
        try:
            # Prepare the command arguments
            args = [sys.executable.replace('python', 'node'), self._script_path, command]

            # Add the main arguments
            args.extend([self.adb_path, self.device_id])

            # Add additional keyword arguments
            for key, value in kwargs.items():
                args.extend([f"--{key}", str(value)])

            # Run the command
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"Command failed: {result.stderr}")

            # Parse the JSON output
            if result.stdout.strip():
                return json.loads(result.stdout)
            else:
                return {"success": True}

        except subprocess.TimeoutExpired:
            raise TimeoutError("Command timed out")
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid JSON response: {result.stdout}")
        except Exception as e:
            raise RuntimeError(f"Failed to run command: {e}")

    def connect(self) -> bool:
        """
        Connect to the device

        Returns:
            bool: True if connection was successful
        """
        result = self._run_command("connect")
        self._connected = result.get("success", False)
        return self._connected

    def disconnect(self) -> None:
        """
        Disconnect from the device
        """
        if self._connected:
            self._run_command("disconnect")
            self._connected = False

    def click(self, x: int, y: int) -> bool:
        """
        Perform a click operation

        Args:
            x (int): X coordinate
            y (int): Y coordinate

        Returns:
            bool: True if operation was successful
        """
        if not self._connected:
            raise RuntimeError("Device not connected")

        result = self._run_command("click", x=x, y=y)
        return result.get("success", False)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 200) -> bool:
        """
        Perform a swipe operation

        Args:
            x1 (int): Starting X coordinate
            y1 (int): Starting Y coordinate
            x2 (int): Ending X coordinate
            y2 (int): Ending Y coordinate
            duration (int): Duration in milliseconds (default: 200)

        Returns:
            bool: True if operation was successful
        """
        if not self._connected:
            raise RuntimeError("Device not connected")

        result = self._run_command("swipe", x1=x1, y1=y1, x2=x2, y2=y2, duration=duration)
        return result.get("success", False)

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information

        Returns:
            Dict[str, Any]: Device information including screen dimensions and orientation
        """
        if not self._connected:
            raise RuntimeError("Device not connected")

        return self._run_command("getDeviceInfo")

    def is_connected(self) -> bool:
        """
        Check if device is connected

        Returns:
            bool: True if device is connected
        """
        return self._connected

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience function to create a controller
def create_touch_controller(adb_path: str, device_id: str) -> MaaTouchController:
    """
    Create a touch controller instance

    Args:
        adb_path (str): Path to ADB executable
        device_id (str): Device ID or IP address

    Returns:
        MaaTouchController: Touch controller instance
    """
    return MaaTouchController(adb_path, device_id)
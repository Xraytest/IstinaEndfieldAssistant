"""
MAA Touch Controller - Main Interface

Pure Python touch control system extracted from MAA
"""

from .adb_manager import AdbManager
from .minitouch_controller import MinitouchController

class MaaTouchController:
    """
    Main interface for MAA Touch Controller

    This class provides a simple API to control Android device touch operations
    through ADB and Minitouch.
    """

    def __init__(self, adb_path: str = "adb", device_id: str = ""):
        """
        Initialize touch controller

        Args:
            adb_path (str): Path to ADB executable (default: "adb")
            device_id (str): Device ID or IP address (optional, can be set later)
        """
        self.adb_manager = AdbManager(adb_path)
        self.minitouch_controller = None
        self.device_id = device_id
        self.is_connected = False

    def connect(self, device_id: str = None) -> bool:
        """
        Connect to device and initialize touch control system

        Args:
            device_id (str): Device ID or IP address (if not provided in constructor)

        Returns:
            bool: True if connection successful
        """
        if device_id:
            self.device_id = device_id

        if not self.device_id:
            raise ValueError("Device ID must be provided")

        # Connect to device via ADB
        if not self.adb_manager.connect_device(self.device_id):
            return False

        # Initialize minitouch controller
        self.minitouch_controller = MinitouchController(self.adb_manager)
        if self.minitouch_controller.connect(self.device_id):
            self.is_connected = True
            return True

        return False

    def disconnect(self) -> None:
        """Disconnect from device and cleanup resources"""
        if self.minitouch_controller:
            self.minitouch_controller.disconnect()
            self.minitouch_controller = None

        if self.device_id:
            self.adb_manager.disconnect_device(self.device_id)

        self.is_connected = False

    def click(self, x: int, y: int) -> bool:
        """
        Perform click operation at specified coordinates

        Args:
            x (int): X coordinate (screen pixels)
            y (int): Y coordinate (screen pixels)

        Returns:
            bool: True if operation successful
        """
        if not self.is_connected or not self.minitouch_controller:
            raise RuntimeError("Device not connected")

        return self.minitouch_controller.click(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 200) -> bool:
        """
        Perform swipe operation from start to end coordinates

        Args:
            x1 (int): Starting X coordinate
            y1 (int): Starting Y coordinate
            x2 (int): Ending X coordinate
            y2 (int): Ending Y coordinate
            duration (int): Duration in milliseconds (default: 200)

        Returns:
            bool: True if operation successful
        """
        if not self.is_connected or not self.minitouch_controller:
            raise RuntimeError("Device not connected")

        return self.minitouch_controller.swipe(x1, y1, x2, y2, duration)

    def get_device_info(self) -> dict:
        """
        Get device information

        Returns:
            dict: Device information including screen dimensions and touch mode
        """
        if not self.is_connected or not self.minitouch_controller:
            raise RuntimeError("Device not connected")

        return self.minitouch_controller.get_device_info()

    def is_connected_to_device(self) -> bool:
        """
        Check if device is connected

        Returns:
            bool: True if device is connected
        """
        return self.is_connected

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def create_touch_controller(adb_path: str = "adb", device_id: str = "") -> MaaTouchController:
    """
    Create a touch controller instance

    Args:
        adb_path (str): Path to ADB executable
        device_id (str): Device ID or IP address

    Returns:
        MaaTouchController: Touch controller instance
    """
    return MaaTouchController(adb_path, device_id)
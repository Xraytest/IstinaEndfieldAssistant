#!/usr/bin/env python3
"""
MAA Touch Controller - Python Usage Example

This example demonstrates how to use the pure Python MAA Touch Controller.
"""

import sys
import os

# Add current directory to path for development
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from maa_touch_controller import MaaTouchController, create_touch_controller

def main():
    """Main example function"""
    # Method 1: Using the class directly
    controller = MaaTouchController(
        adb_path='adb',  # or full path like 'C:\\platform-tools\\adb.exe'
        device_id='127.0.0.1:5555'  # Replace with your device ID
    )

    try:
        print("Connecting to device...")
        if controller.connect():
            print("Connected successfully!")

            # Get device info
            device_info = controller.get_device_info()
            print(f"Device info: {device_info}")

            # Perform click operation
            print("Performing click at (500, 500)...")
            if controller.click(500, 500):
                print("Click successful!")
            else:
                print("Click failed!")

            # Perform swipe operation
            print("Performing swipe from (200, 500) to (800, 500)...")
            if controller.swipe(200, 500, 800, 500, 300):
                print("Swipe successful!")
            else:
                print("Swipe failed!")

        else:
            print("Failed to connect to device")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        controller.disconnect()
        print("Disconnected from device")


def main_with_context_manager():
    """Using context manager for automatic cleanup"""
    try:
        with create_touch_controller(
            adb_path='adb',
            device_id='127.0.0.1:5555'  # Replace with your device ID
        ) as controller:
            print("Connected successfully!")

            # Perform operations
            controller.click(500, 500)
            controller.swipe(200, 500, 800, 500, 300)

            print("Operations completed!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    # Choose which example to run
    main()
    # main_with_context_manager()
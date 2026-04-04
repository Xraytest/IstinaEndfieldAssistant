#!/usr/bin/env python3
"""
MAA Touch Controller - Python Usage Example
"""

from maa_touch_controller import MaaTouchController, create_touch_controller

def main():
    # Method 1: Using the class directly
    controller = MaaTouchController(
        adb_path='C:\\platform-tools\\adb.exe',
        device_id='127.0.0.1:5555'
    )

    try:
        # Connect to device
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

            # Perform swipe operation
            print("Performing swipe from (200, 500) to (800, 500)...")
            if controller.swipe(200, 500, 800, 500, 300):
                print("Swipe successful!")

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
            adb_path='C:\\platform-tools\\adb.exe',
            device_id='127.0.0.1:5555'
        ) as controller:
            print("Connected successfully!")

            # Perform operations
            controller.click(500, 500)
            controller.swipe(200, 500, 800, 500, 300)

            print("Operations completed!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
    # main_with_context_manager()
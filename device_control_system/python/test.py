#!/usr/bin/env python3
"""
MAA Touch Controller - Python Test Suite
"""

import unittest
import os
from maa_touch_controller import MaaTouchController, create_touch_controller

class TestMaaTouchController(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.adb_path = os.environ.get('ADB_PATH', 'C:\\platform-tools\\adb.exe')
        self.device_id = os.environ.get('DEVICE_ID', '127.0.0.1:5555')
        self.controller = None

    def tearDown(self):
        """Clean up test fixtures"""
        if self.controller and self.controller.is_connected():
            try:
                self.controller.disconnect()
            except:
                pass
        self.controller = None

    def test_create_instance(self):
        """Test creating an instance"""
        self.controller = MaaTouchController(self.adb_path, self.device_id)
        self.assertIsNotNone(self.controller)

    def test_connect_disconnect(self):
        """Test connect and disconnect functionality"""
        self.controller = MaaTouchController(self.adb_path, self.device_id)

        # Test connection
        try:
            connected = self.controller.connect()
            self.assertTrue(connected)
            self.assertTrue(self.controller.is_connected())

            # Test device info
            device_info = self.controller.get_device_info()
            self.assertIn('deviceId', device_info)
            self.assertIn('screenWidth', device_info)
            self.assertIn('screenHeight', device_info)

            # Test disconnection
            self.controller.disconnect()
            self.assertFalse(self.controller.is_connected())

        except Exception as e:
            # If ADB is not available, skip the test
            if 'spawn' in str(e) or 'ENOENT' in str(e):
                self.skipTest("ADB not found")
            else:
                raise e

    def test_click_operation(self):
        """Test click operation"""
        self.controller = MaaTouchController(self.adb_path, self.device_id)

        try:
            self.controller.connect()

            # Test click
            result = self.controller.click(500, 500)
            self.assertTrue(result)

            # Test invalid coordinates (should be handled gracefully)
            result = self.controller.click(-100, -100)
            self.assertTrue(result)

        except Exception as e:
            if 'spawn' in str(e) or 'ENOENT' in str(e):
                self.skipTest("ADB not found")
            else:
                raise e

    def test_swipe_operation(self):
        """Test swipe operation"""
        self.controller = MaaTouchController(self.adb_path, self.device_id)

        try:
            self.controller.connect()

            # Test swipe with duration
            result = self.controller.swipe(200, 500, 800, 500, 300)
            self.assertTrue(result)

            # Test swipe with default duration
            result = self.controller.swipe(200, 500, 800, 500)
            self.assertTrue(result)

        except Exception as e:
            if 'spawn' in str(e) or 'ENOENT' in str(e):
                self.skipTest("ADB not found")
            else:
                raise e

    def test_context_manager(self):
        """Test context manager functionality"""
        try:
            with create_touch_controller(self.adb_path, self.device_id) as controller:
                self.assertTrue(controller.is_connected())
                controller.click(500, 500)

            # Controller should be automatically disconnected
            # Note: We can't test this directly since the controller is out of scope

        except Exception as e:
            if 'spawn' in str(e) or 'ENOENT' in str(e):
                self.skipTest("ADB not found")
            else:
                raise e

    def test_error_handling(self):
        """Test error handling for unconnected device"""
        self.controller = MaaTouchController(self.adb_path, self.device_id)

        # Should raise error when not connected
        with self.assertRaises(RuntimeError):
            self.controller.click(500, 500)

        with self.assertRaises(RuntimeError):
            self.controller.swipe(200, 500, 800, 500)

        with self.assertRaises(RuntimeError):
            self.controller.get_device_info()

if __name__ == '__main__':
    unittest.main()
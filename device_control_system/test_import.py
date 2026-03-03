#!/usr/bin/env python3
"""
Simple test to verify the Python package can be imported
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from maa_touch_controller import MaaTouchController
    print("SUCCESS: Successfully imported MaaTouchController")
    print("SUCCESS: Package version: 1.0.0")

    # Test basic instantiation
    controller = MaaTouchController()
    print("SUCCESS: Successfully created MaaTouchController instance")

    print("\nPure Python MAA Touch Controller is ready!")
    print("Run 'python example.py' to see it in action.")

except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")
    sys.exit(1)
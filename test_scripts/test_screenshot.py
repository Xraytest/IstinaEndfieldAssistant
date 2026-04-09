import sys
import os
sys.path.insert(0, '.')
from core.adb_manager import ADBDeviceManager
from core.screen_capture import ScreenCapture
import base64
adb = ADBDeviceManager()
sc = ScreenCapture(adb)
data = sc.capture_screen('127.0.0.1:16512')
if data:
    image_data = base64.b64decode(data)
    with open('test_screenshot.png', 'wb') as f:
        f.write(image_data)
    print('Screenshot saved to test_screenshot.png')
    from PIL import Image
    try:
        img = Image.open('test_screenshot.png')
        print(f'Image verified: size={img.size}, mode={img.mode}')
    except Exception as e:
        print(f'Image verification failed: {e}')
else:
    print('Failed to capture screenshot')
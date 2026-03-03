# MAA Touch Controller

A pure Python touch control system extracted from MAA (MaaAssistantArknights) for controlling Android devices through ADB and Minitouch.

## 📦 Installation

### From Source

```bash
git clone <repository-url>
cd maa-touch-controller
pip install .
```

### Development Installation

```bash
git clone <repository-url>
cd maa-touch-controller
pip install -e .
```

## 🚀 Quick Start

### Basic Usage

```python
from maa_touch_controller import MaaTouchController

# Create touch controller instance
controller = MaaTouchController(
    adb_path='adb',              # ADB executable path (default: 'adb')
    device_id='127.0.0.1:5555'  # Device ID or IP address
)

try:
    # Connect to device
    controller.connect()

    # Perform click operation
    controller.click(500, 500)

    # Perform swipe operation
    controller.swipe(200, 500, 800, 500, 300)

finally:
    # Disconnect from device
    controller.disconnect()
```

### Using Context Manager (Recommended)

```python
from maa_touch_controller import create_touch_controller

with create_touch_controller('adb', '127.0.0.1:5555') as controller:
    controller.click(500, 500)
    controller.swipe(200, 500, 800, 500, 300)
# Automatically disconnects when exiting the context
```

## 📚 API Documentation

### `MaaTouchController(adb_path="adb", device_id="")`

Create a touch controller instance.

- **Parameters**:
  - `adb_path` (str): Path to ADB executable (default: "adb")
  - `device_id` (str): Device ID or IP address (optional, can be set later)

### `controller.connect(device_id=None)`

Connect to device and initialize touch control system.

- **Parameters**:
  - `device_id` (str, optional): Device ID or IP address (if not provided in constructor)
- **Returns**: `bool` - True if connection successful
- **Raises**: `ValueError` - If device ID is not provided

### `controller.disconnect()`

Disconnect from device and cleanup resources.

- **Returns**: `None`

### `controller.click(x, y)`

Perform click operation at specified coordinates.

- **Parameters**:
  - `x` (int): X coordinate (screen pixels)
  - `y` (int): Y coordinate (screen pixels)
- **Returns**: `bool` - True if operation successful
- **Raises**: `RuntimeError` - If device not connected

### `controller.swipe(x1, y1, x2, y2, duration=200)`

Perform swipe operation from start to end coordinates.

- **Parameters**:
  - `x1` (int): Starting X coordinate
  - `y1` (int): Starting Y coordinate
  - `x2` (int): Ending X coordinate
  - `y2` (int): Ending Y coordinate
  - `duration` (int, optional): Duration in milliseconds (default: 200)
- **Returns**: `bool` - True if operation successful
- **Raises**: `RuntimeError` - If device not connected

### `controller.get_device_info()`

Get device information.

- **Returns**: `dict`
  - `device_id` (str): Device ID
  - `screen_width` (int): Screen width in pixels
  - `screen_height` (int): Screen height in pixels
  - `orientation` (int): Device orientation (0, 1, 2, 3)
  - `touch_mode` (str): Touch mode ('minitouch' | 'adb')

### `controller.is_connected_to_device()`

Check if device is connected.

- **Returns**: `bool` - True if device is connected

### `create_touch_controller(adb_path="adb", device_id="")`

Create a touch controller instance (convenience function).

- **Parameters**:
  - `adb_path` (str): Path to ADB executable
  - `device_id` (str): Device ID or IP address
- **Returns**: `MaaTouchController` - Touch controller instance

## ⚙️ Features

### Smart Mode Switching
- **Minitouch Mode**: High precision, multi-touch, pressure sensitivity
- **ADB Fallback Mode**: Basic click and swipe, better compatibility
- Automatically detects device architecture and selects appropriate minitouch binary

### Coordinate Handling
- Automatic coordinate scaling based on screen resolution
- Supports all device orientations (0°, 90°, 180°, 270°)
- Handles coordinate validation and clamping

### Error Handling
- Comprehensive error handling and status feedback
- Graceful handling of network disconnections or device disconnects

### Resource Management
- Automatic cleanup of temporary files and processes
- Memory-safe resource management

## 🧪 Testing

### Run Example

```bash
python example.py
```

### Run Tests

```bash
python -m pytest tests/
# or
python tests/test_maa_touch_controller.py
```

### Test Environment Requirements

- **ADB Tool**: Android SDK Platform-Tools
- **Python**: 3.7+
- **Android Device**: With developer options and USB debugging enabled
- **Network Device**: On same network with wireless debugging enabled

## 🔧 Compatibility

### Device Compatibility
- ✅ Physical Android phones (Android 7.0+)
- ✅ Android tablets
- ✅ BlueStacks emulator
- ✅ MuMu emulator
- ✅ LDPlayer emulator
- ✅ Nox emulator
- ✅ Windows Subsystem for Android (WSA)

### Platform Compatibility
- ✅ Windows 10/11
- ✅ macOS 12+
- ✅ Ubuntu 20.04+
- ✅ Other Linux distributions

## 🛡️ Security Considerations

1. **Minimal Permissions**: Only requests necessary ADB permissions
2. **Data Security**: Does not store sensitive device information
3. **Network Isolation**: Should only be used on local networks
4. **User Authorization**: All operations require explicit user initiation

## 📁 Project Structure

```
maa-touch-controller/
├── maa_touch_controller/      # Main package
│   ├── __init__.py           # Main interface
│   ├── adb_manager.py        # ADB device manager
│   └── minitouch_controller.py  # Minitouch implementation
├── minitouch_resources/      # Minitouch binary files
│   ├── arm64-v8a/
│   ├── armeabi/
│   ├── armeabi-v7a/
│   ├── maatouch/
│   ├── x86/
│   └── x86_64/
├── tests/                    # Test suite
│   └── test_maa_touch_controller.py
├── example.py                # Usage example
├── setup.py                  # Package configuration
├── requirements.txt          # Dependencies
└── README.md                 # Documentation
```

## 🤝 Contributing

Contributions are welcome! Please ensure:

1. Follow existing code style
2. Add corresponding test cases
3. Update relevant documentation

## 📜 License

MIT License

## 🙏 Acknowledgments

Thanks to the MAA (MaaAssistantArknights) project for providing the excellent touch control system implementation.
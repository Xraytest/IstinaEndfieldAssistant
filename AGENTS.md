# IstinaEndfieldAssistant - Agent Instructions

## Project Overview
Arknights Endfield automation client with Agent mode. Python project using PyQt6 GUI.

## Directory Structure
- `src/` - All source code
  - `src/core/` - Core business logic
  - `src/device/` - Device control (ADB, touch)
  - `src/screenshot/` - Screen capture
  - `src/gui/` - GUI entrypoints (PyQt6 only)
- `tests/` - Pytest test suite
- `config/` - Configuration files
- `3rd-party/` - External tools (ADB, Git)
- `assets/` - Static assets
- `models/` - ML models

## Entrypoints
- **PyQt6 GUI**: `src/gui/pyqt6/main.py`

## Path Setup (Critical)
All scripts must add `src/` directory to `sys.path`:
```python
import sys, os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
```

## Configuration
- **Main config**: `config/client_config.json`
- **Server**: `127.0.0.1:9999`
- **API Password**: `default_password`
- **ADB**: `3rd-party/adb/adb.exe`

## Testing
```bash
# Run all tests
pytest tests/

# Run single test file
pytest tests/test_auth.py

# Run with verbose output
pytest tests/ -v
```

## Core Modules
- `src/core/cloud/managers/` - Auth, device, agent execution management
- `src/core/communication/` - ClientCommunicator for server API
- `src/device/` - ADB device manager, touch control (MAA framework)
- `src/screenshot/` - Screen capture
- `src/core/local_inference/` - Local LLM inference (llama-cpp, GGUF models)

## Key Classes
- `AuthManager` - User authentication via ArkPass
- `DeviceManager` - ADB device scanning/selection
- `AgentExecutor` - Agent mode execution with VLM feedback loop
- `InferenceManager` - Local/Cloud inference mode management
- `ClientCommunicator` - HTTP client for cloud API

## Common Tasks
1. **Modify agent execution**: Edit `src/core/cloud/agent_executor.py`
2. **Add GUI page**: Create in `src/gui/pyqt6/pages/`
3. **Change touch behavior**: Edit `src/device/touch/maafw_touch_adapter.py`
4. **Configure local inference**: Edit `src/core/local_inference/`

## Dependencies
- PyQt6 (for GUI)
- Pillow (PIL for image handling)
- pytest (testing)
- llama-cpp-python (local inference, optional)

# IstinaEndfieldAssistant - Agent Instructions

## Project Overview
Arknights Endfield automation client with VLM-powered Agent mode. Python 3.10+, PyQt6 GUI, TCP server at `127.0.0.1:9999`.

## Entrypoints
- **GUI app**: `python src/gui/pyqt6/main.py` → `gui.pyqt6.app_main.run_application()`
- **No CLI entrypoint** — scripts in `scripts/` are standalone exploration utilities, not CLI entrypoints
- **Server** is external (IstinaPlatform project), started via `start_server.bat`

## Path Setup (Critical)
All files under `src/` must add `src/` to `sys.path`. The dirname depth varies by location:
- `src/gui/pyqt6/*.py`: 4× `dirname()` to reach project root
- `scripts/*.py` (project root): 2× `dirname()` 
- `src/core/cloud/managers/*.py`: 5× `dirname()` (arkpass cache path)
- `src/device/*.py`: 2× `dirname()` (inline in adb_manager.py)

Pattern for scripts:
```python
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
```

## Architecture

| Directory | Responsibility |
|-----------|----------------|
| `src/core/cloud/managers/` | AuthManager, DeviceManager, ExceptionDetector, LogManager |
| `src/core/cloud/` | AgentExecutor (VLM feedback loop), ExplorationEngine, PageTree (UI page graph), RealtimeCombatController |
| `src/core/cloud/communication/` | Cloud-side communication submodule |
| `src/core/communication/` | ClientCommunicator — TCP client, custom binary protocol (magic `ARKS` + version + big-endian length), Fernet encryption |
| `src/core/local_inference/` | InferenceManager, LocalInferenceEngine, RealTimeInferenceEngine, GPUChecker, ModelManager |
| `src/core/device_state_manager.py` | ADB device lifecycle/state tracking with template matching |
| `src/core/logger.py` | LogCategory enum (MAIN, ADB, COMMUNICATION, EXECUTION, AUTHENTICATION, GUI, EXCEPTION, PERFORMANCE), requires `init_logger()` before use |
| `src/device/adb_manager.py` | ADBDeviceManager (start-server, connect, shell, screencap) |
| `src/device/touch/` | TouchManager, MaafwTouchAdapter, MaafwWin32Adapter |
| `src/screenshot/` | ScreenCapture — MAA first, ADB fallback |
| `src/gui/pyqt6/pages/` | auth_page, agent_page, cloud_page, settings_page, standard_reasoning_page, prts_full_intelligence_page, model_manager_page |

### Key Flow
1. `AuthManager.login_with_arkpass()` → server `register`/`login` → session_id → `*.arkpass` cached in `cache/`
2. `DeviceManager` → ADB scan + selection
3. `AgentExecutor` → captures screenshot → sends `agent_chat` request (with instruction + image + history) → server returns actions (tap/swipe/wait) → executes via TouchManager
4. `InferenceManager` routes between `local` (llama-cpp-python, GGUF) and `cloud` modes

## Configuration
- **File**: `config/client_config.json`
- Key sections: `server` (host/port), `communication.password`, `touch.maa_style` (press_jitter_px, swipe_delay), `inference.mode` (auto/local/cloud), `inference.local`

## Testing
```bash
pytest tests/              # All tests (root + unit/ subdir)
pytest tests/unit/         # Unit tests only (27 files)
pytest tests/test_auth.py  # Single test
pytest tests/ -v           # Verbose
```
- `tests/e2e/` and `tests/integration/` exist but are **empty** — only `tests/` root and `tests/unit/` have tests
- Test files may produce `.json`/`.txt` output alongside `.py` (e.g., `test_robustness_results.json`)
- `pyproject.toml`: `testpaths = ["tests"]`, `pythonpath = ["."]`

## Scripts & Exploration
- Scripts in `scripts/` target device `emulator-5562` and server port `9999`
- `scripts/explore_game.py` — full autonomous UI exploration via ExplorationEngine
- `scripts/find_tasks.py` — task-focused exploration loop
- `scripts/navigate_to_game.py` — login → world sequence (auto-tap through dialogs)
- `scripts/check_env.py` — verify ADB connectivity and MaaFramework paths
- Auth flow in scripts: hardcoded api_key `aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763` for user `explorer`, `agent_chat` endpoint not `agent_chat` (see explore_game.py)
- `model_tag: "exploration_deep"` routes to cherryin/qwen3.5-35b-a3b
- `system_prompt` is sent in request data (server extracts it)

## Gotchas
- **Windows-only**: ADB at `3rd-party/adb/adb.exe`, git at `3rd-party/git/bin/git.exe`
- **Logging**: Must call `init_logger()` before any log call (uses `LogCategory` enum)
- **TouchManager MAA connection**: `connect_android("emulator-5562")` fails (hostname resolution); use ADB-based touch fallback instead
- **Auto-logout**: Server session expires after ~1h idle; game restart required
- **Protocol**: TCP with Fernet encryption (password-derived key via PBKDF2), not plain HTTP
- **Tests reference old dirs**: Some test files import from old Chinese-named directories — ignore those, use `src/` imports
- **Server must be running** (`start_server.bat` or IstinaPlatform independently) before client auth
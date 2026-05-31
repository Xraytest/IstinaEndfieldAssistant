# IstinaEndfieldAssistant - Agent Instructions

## Project Overview
Arknights Endfield automation client with VLM-powered Agent mode. Python 3.10+, PyQt6 GUI, TCP server at `127.0.0.1:9999`.

## Entrypoints
- **GUI app**: `python src/gui/pyqt6/main.py` → `gui.pyqt6.app_main.run_application()`
- **CLI analysis**: `python scripts/analyze_tasks.py` — daily/weekly task analysis using IstinaPlatform large model
- **No CLI entrypoint** — scripts in `scripts/` are standalone exploration utilities, not CLI entrypoints
- **Server** is external (IstinaPlatform project), started via `start_server.bat`

## Path Setup (Critical)
All files under `src/` must add `src/` to `sys.path`. The dirname depth varies by location:
- `src/gui/pyqt6/*.py`: 4× `dirname()` to reach project root
- `scripts/*.py` (project root): 2× `dirname()` 
- `src/core/cloud/managers/*.py`: 5× `dirname()` (arkpass cache path)
- `src/core/element_analysis/*.py`: 4× `dirname()` (project root)
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
| `src/core/element_analysis/` | ElementAnalyzer (VLM코고정도 분석), TaskAnalyzer(每日/每周任务), ElementRepository(持久化存储), models(数据模型) |
| `src/core/cloud/managers/` | AuthManager, DeviceManager, ExceptionDetector, LogManager |
| `src/core/cloud/` | AgentExecutor (VLM feedback loop), ExplorationEngine, PageTree (UI page graph), RealtimeCombatController |
| `src/core/cloud/communication/` | Cloud-side communication submodule |
| `src/core/communication/` | ClientCommunicator — TCP client, custom binary protocol (magic `ARKS` + version + big-endian length), Fernet encryption |
| `src/core/local_inference/` | InferenceManager, LocalInferenceEngine, RealTimeInferenceEngine, GPUChecker, ModelManager |
| `src/core/device_state_manager.py` | ADB device lifecycle/state tracking with template matching |
| `src/core/combat/` | **Empty** — no combat logic yet |
| `src/core/logger.py` | LogCategory enum (MAIN, ADB, COMMUNICATION, EXECUTION, AUTHENTICATION, GUI, EXCEPTION, PERFORMANCE), requires `init_logger()` before use |
| `src/device/adb_manager.py` | ADBDeviceManager (start-server, connect, shell, screencap) |
| `src/device/touch/` | TouchManager, MaafwTouchAdapter, MaafwWin32Adapter |
| `src/screenshot/` | ScreenCapture — MAA first, ADB fallback |
| `src/gui/pyqt6/pages/` | auth_page, agent_page, cloud_page, iea_page, settings_page, standard_reasoning_page, prts_full_intelligence_page, model_manager_page |

| **Data Storage** | |
| `data/elements/` | 持久化页面元素知识 (PageKnowledge JSON) — 从cache分离 |
| `data/tasks/` | 任务定义与实例快照 (TaskDefinition / TaskInstance) |
| `data/events/` | 活动信息 (EventActivity) |
| `data/analysis/` | 分析历史记录 (AnalysisResult 按时间戳) |

### Key Flow
1. `AuthManager.login_with_arkpass()` → server `register`/`login` → session_id → `*.arkpass` cached in `cache/`
2. `DeviceManager` → ADB scan + selection
3. `AgentExecutor` → captures screenshot → sends `agent_chat` request (with instruction + image + history) → server returns actions (tap/swipe/wait) → executes via TouchManager
4. `InferenceManager` routes between `local` (llama-cpp-python, GGUF) and `cloud` modes

### Element Analysis Flow
1. `ElementAnalyzer.analyze_full_page()` → screenshot → send to IstinaPlatform VLM (large model, model_tag=`exploration_deep`) → parse JSON → `ElementKnowledge` objects
2. `TaskAnalyzer.analyze_current_tasks()` → VLM task-focused analysis → extract `TaskDefinition` objects with status/progress/claim-button
3. `ElementRepository` → persist to `data/elements/`, `data/tasks/`, `data/events/`, `data/analysis/` (separate from `cache/`)
4. `scripts/analyze_tasks.py` — main entry: supports `--quick`, `--claim`, `--session`, `--device`, `--model`

### Important Entrypoints
- `gui.pyqt6.app_main.run_application(auth_manager, device_manager, agent_executor, communicator, screen_capture, touch_executor, config)` — all core dependencies passed as arguments.
- `scripts/analyze_tasks.py` — task analysis CLI for device `localhost:16512`

## Server Protocol
- See `command_help.md` for supported commands: `register`, `login`, `get_default_tasks`, `process_image`, `get_user_info`
- Error types: `session_expired`, `invalid_api_key`, `quota_exceeded`, `provider_rate_limit_exceeded`

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
- `scripts/analyze_tasks.py` — daily/weekly task analysis with IstinaPlatform large model (device localhost:16512)
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
- **element_analysis path**: `src/core/element_analysis/*.py` uses 4× `dirname()` for project root (same as gui/pyqt6)

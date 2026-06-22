import sys, os, signal, time, json

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

project_root = os.path.dirname(os.path.dirname(__file__))

from core.cloud.exploration_engine import ExplorationEngine, ExplorationConfig, ExplorationState
from core.cloud.agent_executor import AgentExecutor
from core.communication import ClientCommunicator
from screenshot import ScreenCapture
from device.touch import TouchManager
from device.adb_manager import ADBDeviceManager
from core.logger import init_logger, LogCategory, get_logger
import uuid

init_logger()

def main():
    adb_path = os.path.join(project_root, "3rd-party", "adb", "adb.exe")
    device_serial = "emulator-5562"
    touch_address = "127.0.0.1:5563"

    logger = get_logger()
    logger.info(LogCategory.MAIN, "初始化探索引擎组件...")

    adb_manager = ADBDeviceManager(adb_path=adb_path)
    adb_manager.connect_device(device_serial)

    screen_capture = ScreenCapture(adb_manager)

    touch_manager = TouchManager()
    touch_manager.connect_android(adb_path=adb_path, address=touch_address)
    screen_capture.set_touch_manager(touch_manager)

    # 从配置读取密码和密钥
    config_data = {}
    try:
        with open(os.path.join(project_root, "config", "client_config.json")) as f:
            config_data = json.load(f)
    except Exception:
        pass
    server_config = config_data.get("server", {})
    server_password = server_config.get("password", "default_password")
    api_key = config_data.get("api_key", "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763")

    communicator = ClientCommunicator(
        host="127.0.0.1",
        port=9999,
        password=server_password,
        timeout=300,
    )

    arkpass_data = {"user_id": "explorer", "api_key": api_key, "server_host": "127.0.0.1", "server_port": 9999}
    arkpass_path = os.path.join(project_root, "cache", "explorer.arkpass")
    os.makedirs(os.path.dirname(arkpass_path), exist_ok=True)
    with open(arkpass_path, "w", encoding="utf-8") as f:
        json.dump(arkpass_data, f, indent=2)
    print(f"  已保存arkpass: {arkpass_path}")

    print("登录获取会话ID...")
    login_result = communicator.send_request("login", {
        "user_id": "explorer",
        "key": api_key,
    })
    print(f"  登录结果: {json.dumps(login_result, ensure_ascii=False)}")
    session_id = login_result.get("session_id", "") if login_result else ""
    print(f"  session_id: {session_id[:16] if session_id else 'N/A'}...")

    if session_id:
        raw = screen_capture.capture_screen(device_serial)
        if raw:
            b64 = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            payload = {
                "instruction": "识别当前游戏画面中的所有可交互UI元素，包括按钮、图标、文字标签等。输出JSON格式。",
                "screenshot": b64,
                "history": [],
                "session_id": session_id,
                "user_id": "explorer",
                "model_tag": "exploration_deep",
                "system_prompt": "你是一个《明日方舟：终末地》游戏UI分析器。返回JSON：{page_name, page_type, elements: [{id, type, label, bbox, confidence, action}], description}。bbox为[x1,y1,x2,y2]像素坐标。",
            }
            diag_response = communicator.send_request("agent_chat", payload)
            print(f"  诊断响应: {json.dumps(diag_response, ensure_ascii=False, indent=2)[:3000]}")
            if diag_response:
                reply = diag_response.get("reply", "")
                print(f"  回复长度: {len(reply)}")
                if reply:
                    print(f"  回复(前1000): {reply[:1000]}")
        else:
            print("  截图失败!")

    communicator.set_logged_in(True)

    def signal_handler(signum, frame):
        print("\n收到退出信号，正在保存结果...")
        try:
            engine._save_results()
            print("结果已保存")
        except Exception as e:
            print(f"保存失败: {e}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)

    config = ExplorationConfig(
        device_serial=device_serial,
        model_tag="exploration_deep",
        verification_passes=3,
        tap_wait_time=3.0,
        max_depth=30,
        max_pages=200,
        session_id=session_id,
        user_id="explorer",
        save_interval=1,
        output_file=os.path.join(project_root, "cache", "game_map.md"),
        output_json=os.path.join(project_root, "cache", "page_tree.json"),
    )

    engine = ExplorationEngine(
        communicator=communicator,
        screen_capture=screen_capture,
        touch_executor=touch_manager,
        agent_executor=None,
        config=config,
    )

    def on_page_discovered(page):
        logger.info(LogCategory.MAIN, f"发现新页面: {page.name} ({page.page_id})")
        print(f"  [页面] {page.name} | ID={page.page_id} | 元素={len(page.elements)}")

    def on_state_changed(state):
        print(f"  [状态] {state.value}")

    def on_error(**kwargs):
        print(f"  [错误] {kwargs.get('message', '未知错误')}")

    def on_save(**kwargs):
        print(f"  [保存] MD={kwargs.get('md_file')} JSON={kwargs.get('json_file')}")

    engine.on("page_discovered", on_page_discovered)
    engine.on("state_changed", on_state_changed)
    engine.on("error", on_error)
    engine.on("save", on_save)

    print()
    print("开始自动化探索...")
    print(f"  设备: {device_serial}")
    print(f"  模型标签: exploration_deep")
    print(f"  最大深度: 30")
    print()

    try:
        engine.start()
    except KeyboardInterrupt:
        print("\n用户中断探索")
        engine.stop()
    except Exception as e:
        print(f"\n探索出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stats = engine.stats
        print(f"\n探索统计:")
        print(f"  页面: {stats['pages_found']}")
        print(f"  元素: {stats['elements_found']}")
        print(f"  VLM调用: {stats['vlm_calls']}")
        print(f"  点击: {stats['taps']}")
        print(f"  错误: {stats['errors']}")

        summary_path = os.path.join(project_root, "cache", "exploration_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": stats,
                "timestamp": time.time(),
                "device": device_serial,
                "model_tag": "exploration_deep",
            }, f, ensure_ascii=False, indent=2)
        print(f"\n摘要已保存: {summary_path}")
        print(f"页面地图: {config.output_file}")
        print(f"页面树: {config.output_json}")

if __name__ == "__main__":
    main()
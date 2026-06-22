#!/usr/bin/env python3
"""
IstinaEndfieldAssistant — 统一 CLI 入口 v4

薄路由层，将各子命令委托给领域专用的 CLI 模块 (src/cli/) 或核心模块。

用法:
  python -m src.cli.istina <command> [args]

子命令:
  module list                    # 列出所有模块
  module test <name>             # 测试单个模块可用性
  module test all                # 测试所有模块
  module info <name>             # 查看模块详情
  gpu status|monitor|recommend   # GPU 检测
  system doctor|env|disk|perf    # 系统诊断
  device status|screenshot|info  # 设备管理
  scene capture|nav|analyze|ocr  # 场景采集
  daily|harvest|analyze|explore  # 业务命令
  config|auth|model|nav          # 配置/认证/模型/导航
"""

import sys
import os
import json
import argparse
import subprocess
import time
import importlib
from pathlib import Path
from typing import Optional, Dict, Any, List

# ── 路径设置 ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ── 模块清单（自动发现） ──────────────────────────────────────

def _discover_modules() -> Dict[str, Dict]:
    """扫描 core/*/ 下的子包，返回 {模块名: {layer, path, exports}}"""
    modules = {}
    core_dir = SRC_DIR / "core"
    for layer_dir in ["foundation", "capability", "service"]:
        layer_path = core_dir / layer_dir
        if not layer_path.exists():
            continue
        for sub_dir in sorted(layer_path.iterdir()):
            if not sub_dir.is_dir() or sub_dir.name.startswith("_"):
                continue
            init_file = sub_dir / "__init__.py"
            if not init_file.exists():
                continue
            # 读取导出清单
            exports = []
            try:
                with open(init_file, "r", encoding="utf-8") as f:
                    content = f.read()
                # 从 __all__ 提取导出符号
                if "__all__" in content:
                    import ast
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == "__all__":
                                    if isinstance(node.value, ast.List):
                                        exports = [
                                            elt.value for elt in node.value.elts
                                            if isinstance(elt, ast.Constant)
                                        ]
            except Exception:
                pass
            modules[sub_dir.name] = {
                "layer": layer_dir,
                "path": str(sub_dir),
                "exports": exports,
            }
    return modules


def _check_module_available(module_name: str) -> Dict:
    """检查模块可用性，返回结构化结果"""
    result = {
        "module": module_name,
        "layer": "unknown",
        "available": False,
        "runtime_ready": False,
        "checks": {"import": False, "dependencies": False, "config": False, "runtime": False},
        "details": {"import_error": None, "missing_deps": [], "config_path": None, "runtime_info": None},
    }

    # 查找模块
    modules = _discover_modules()
    if module_name not in modules:
        result["details"]["import_error"] = f"模块 '{module_name}' 未找到"
        return result

    mod_info = modules[module_name]
    result["layer"] = mod_info["layer"]

    # 尝试导入
    try:
        import_path = f"core.{mod_info['layer']}.{module_name}"
        mod = importlib.import_module(import_path)
        result["checks"]["import"] = True
    except Exception as e:
        result["details"]["import_error"] = str(e)
        return result

    # 检查依赖（从模块自描述）
    deps = getattr(mod, "__dependencies__", [])
    if deps:
        missing = []
        for dep in deps:
            try:
                importlib.import_module(f"core.{mod_info['layer']}.{dep}")
            except Exception:
                missing.append(dep)
        result["checks"]["dependencies"] = len(missing) == 0
        result["details"]["missing_deps"] = missing
    else:
        result["checks"]["dependencies"] = True

    # 检查配置
    config_files = getattr(mod, "__config_files__", [])
    if config_files:
        all_found = True
        for cfg in config_files:
            cfg_path = PROJECT_ROOT / "config" / cfg
            if not cfg_path.exists():
                all_found = False
                result["details"]["config_path"] = str(cfg_path)
                break
        result["checks"]["config"] = all_found
    else:
        result["checks"]["config"] = True

    # 检查运行时条件
    runtime_check = getattr(mod, "__runtime_check__", None)
    if runtime_check:
        try:
            runtime_result = runtime_check()
            result["checks"]["runtime"] = bool(runtime_result)
            result["details"]["runtime_info"] = str(runtime_result) if runtime_result else None
        except Exception as e:
            result["checks"]["runtime"] = False
            result["details"]["runtime_info"] = str(e)
    else:
        # 无运行时检查，标记为不可用但不算失败
        result["checks"]["runtime"] = False

    # 综合判定
    if mod_info["layer"] == "foundation":
        result["available"] = result["checks"]["import"]
    elif mod_info["layer"] == "capability":
        result["available"] = result["checks"]["import"] and result["checks"]["dependencies"]
        result["runtime_ready"] = result["checks"]["runtime"]
    elif mod_info["layer"] == "service":
        result["available"] = result["checks"]["import"] and result["checks"]["dependencies"] and result["checks"]["config"]
        result["runtime_ready"] = result["checks"]["runtime"]

    return result


# ── 模块子命令 ────────────────────────────────────────────────

def cmd_module_list(args):
    """列出所有模块"""
    modules = _discover_modules()
    if args.json:
        print(json.dumps(modules, ensure_ascii=False, indent=2))
        return 0

    print(f"\n{'模块名':<20} {'层级':<15} {'导出符号数':<10}")
    print("-" * 50)
    for name, info in sorted(modules.items()):
        print(f"{name:<20} {info['layer']:<15} {len(info['exports']):<10}")
    print(f"\n共 {len(modules)} 个模块")
    return 0


def cmd_module_test(args):
    """测试模块可用性"""
    if args.name == "all":
        modules = _discover_modules()
        all_ok = True
        for name in sorted(modules.keys()):
            result = _check_module_available(name)
            _print_module_result(result)
            if not result["available"]:
                all_ok = False
        print(f"\n{'='*40}")
        print(f"总体: {'全部通过' if all_ok else '存在不可用模块'}")
        return 0 if all_ok else 1
    else:
        result = _check_module_available(args.name)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_module_result(result)
        return 0 if result["available"] else 1


def _print_module_result(result: Dict):
    """打印模块测试结果"""
    status = "✓" if result["available"] else "✗"
    runtime = " ⚠" if result["runtime_ready"] else ""
    print(f"{status} {result['module']:<20} [{result['layer']:<12}]{runtime}")
    if not result["available"]:
        for check, ok in result["checks"].items():
            if not ok:
                detail = result["details"].get(f"{check}_error") or result["details"].get(f"missing_{check}")
                print(f"    └─ {check}: FAIL ({detail or 'unknown'})")


def cmd_module_info(args):
    """查看模块详情"""
    modules = _discover_modules()
    if args.name not in modules:
        print(f"模块 '{args.name}' 未找到")
        return 1
    info = modules[args.name]
    print(f"\n模块: {args.name}")
    print(f"层级: {info['layer']}")
    print(f"路径: {info['path']}")
    print(f"导出符号 ({len(info['exports'])}):")
    for exp in info["exports"]:
        print(f"  - {exp}")
    return 0


# ── 原有子命令（从 scripts/istina.py 迁移） ──────────────────

def run_script(script_name: str, args_list: List[str] = None,
               capture: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """运行 scripts/ 下的子脚本"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        msg = f"[istina] 脚本未找到: {script_path}"
        print(msg, file=sys.stderr)
        return subprocess.CompletedProcess([], 1, b"", msg.encode())
    cmd = [sys.executable, str(script_path)]
    if args_list:
        cmd.extend(args_list)
    if capture:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    return subprocess.run(cmd, timeout=timeout)


def print_json(data: Any):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _delegate_to_cli_module(module_name: str, args_list: List[str]) -> int:
    """委托给 src/cli/ 下的领域模块执行"""
    module_path = SRC_DIR / "cli" / f"{module_name}.py"
    cmd = [sys.executable, str(module_path)] + args_list
    try:
        result = subprocess.run(cmd, timeout=300)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"[istina] 模块 {module_name} 超时")
        return 1


def _import_cli(module_name: str):
    """动态导入 CLI 模块"""
    try:
        return importlib.import_module(f"cli.{module_name}")
    except ImportError:
        return None


def ensure_session() -> tuple:
    """创建服务器连接"""
    from core.foundation.logger import init_logger
    init_logger()
    from core.service.communication import ClientCommunicator

    config = {}
    try:
        with open(os.path.join(PROJECT_ROOT, "config", "client_config.json")) as f:
            config = json.load(f)
    except Exception:
        pass
    server_cfg = config.get("server", {})

    password = server_cfg.get("password", "default_password")
    api_key = server_cfg.get("api_key", "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763")
    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 9999)
    user_id = server_cfg.get("user_id", "cli_user")

    comm = ClientCommunicator(host=host, port=port, password=password, timeout=120)
    r = comm.send_request("login", {"user_id": user_id, "key": api_key})
    sid = r.get("session_id", "") if r else ""
    comm.set_logged_in(True)
    return comm, sid


# ── 业务子命令 ────────────────────────────────────────────────

def cmd_daily(args):
    """每日签到+任务分析"""
    params = []
    if args.model:
        params.extend(["--model", args.model])
    if args.dry_run:
        params.append("--dry-run")
    if args.delay:
        params.extend(["--delay", str(args.delay)])
    if args.timeout:
        params.extend(["--timeout", str(args.timeout)])
    print(f"[istina] 运行每日流水线 (model={args.model or 'exploration_deep'})")
    result = run_script("daily_pipeline.py", params, timeout=args.timeout or 300)
    out = result.stdout.decode("utf-8", errors="replace")
    if out:
        print(out)
    if result.stderr:
        print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    if result.returncode != 0:
        print(f"[istina] 每日流程异常退出 (code={result.returncode})")
    return result.returncode


def cmd_harvest(args):
    """实体图像采集"""
    params = []
    if args.count:
        params.extend(["--count", str(args.count)])
    if args.model:
        params.extend(["--model", args.model])
    if args.interval:
        params.extend(["--interval", str(args.interval)])
    print(f"[istina] 启动实体采集管线 (target={args.count or 200} 张)")
    result = run_script("entity_harvest_pipeline.py", params, capture=False,
                        timeout=args.timeout or 7200)
    return result.returncode if hasattr(result, 'returncode') else 0


def cmd_analyze(args):
    """分析当前画面"""
    from core.capability.adb_utils import ADB
    from core.capability.vlm import vlm_analyze, VLMOptions

    adb = ADB()
    img = adb.screencap(dedup=False)
    if img is None:
        print('{"error":"截图失败"}')
        return 1

    instruction = args.instruction or "识别当前游戏画面中的所有UI元素。JSON输出"
    opts = VLMOptions(
        model_tag=args.model or "exploration_deep",
        timeout=args.timeout or 120,
        system_prompt=args.system_prompt or "你是终末地UI分析器。逐一列出每个按钮。",
    )
    resp = vlm_analyze(img, instruction=instruction, opts=opts)
    if resp:
        reply = resp.get("reply", "")
        print(reply)
    else:
        print('{"error":"VLM 无响应"}')
        return 1
    return 0


def cmd_explore(args):
    """UI 探索"""
    params = []
    if args.depth:
        params.extend(["--depth", str(args.depth)])
    if args.model:
        params.extend(["--model", args.model])
    print(f"[istina] 启动 UI 探索 (depth={args.depth or 3})")
    result = run_script("explore_game.py", params, capture=False,
                        timeout=args.timeout or 1800)
    return 0


def cmd_config(args):
    """配置查看/修改"""
    config_path = PROJECT_ROOT / "config" / "client_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if args.key:
        keys = args.key.split(".")
        val = config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k, "<not found>")
            else:
                val = "<not found>"
                break
        if args.value is not None:
            parent = config
            for k in keys[:-1]:
                parent = parent.get(k, {})
            parent[keys[-1]] = args.value
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"已设置 {args.key} = {args.value}")
        else:
            print(f"{args.key} = {val}")
    else:
        print_json(config)
    return 0


def cmd_auth(args):
    """认证管理"""
    from core.service.cloud.managers import AuthManager
    auth = AuthManager()
    if args.action == "status":
        info = auth.get_auth_info()
        print_json(info)
    elif args.action == "login":
        if args.token:
            result = auth.login_with_token(args.token)
        else:
            result = auth.login()
        print_json(result if result else {"error": "登录失败"})
    elif args.action == "logout":
        auth.logout()
        print('{"status":"logged_out"}')
    return 0


def cmd_model(args):
    """模型管理"""
    from core.capability.local_inference import ModelManager
    manager = ModelManager(models_dir=str(PROJECT_ROOT / "models"))
    if args.action == "list":
        models = manager.get_all_models()
        data = []
        for m in models:
            data.append({
                "name": m.name,
                "description": m.description,
                "size_gb": m.size_gb,
                "downloaded": m.is_downloaded,
                "parameters": m.parameters,
                "quantization": m.quantization,
            })
        print_json(data)
    elif args.action == "info":
        if not args.model_name:
            print('{"error":"需要模型名称"}')
            return 1
        info = manager.get_model_info(args.model_name)
        if info:
            print_json({
                "name": info.name,
                "description": info.description,
                "size_gb": info.size_gb,
                "parameters": info.parameters,
                "quantization": info.quantization,
                "downloaded": info.is_downloaded,
                "local_path": str(info.local_path) if info.local_path else None,
                "recommended_gpu_memory_gb": info.recommended_gpu_memory_gb,
            })
        else:
            print(f'{{"error":"未找到模型: {args.model_name}"}}')
            return 1
    elif args.action == "download":
        if not args.model_name:
            print('{"error":"需要模型名称"}')
            return 1
        print(f"[istina] 下载模型: {args.model_name}")
        path = manager.download_model(args.model_name)
        if path:
            print(f"  完成: {path}")
        else:
            print(f"  失败")
            return 1
    elif args.action == "disk":
        usage = manager.get_disk_usage()
        print_json(usage)
    return 0


def cmd_nav(args):
    """导航到页面"""
    from core.capability.adb_utils import ADB
    from core.foundation.game_data import Coords, NAVIGATION_MAP, PAGE_TYPE_KEYWORDS

    adb = ADB()
    target = args.target
    nav_info = NAVIGATION_MAP.get(target)
    if nav_info:
        action = nav_info.get("action")
        if action == "click":
            coords = nav_info.get("coords", Coords.title_click)
            print(f"[istina] 导航: {nav_info['desc']} → 点击 {coords}")
            adb.tap(*coords)
        elif action == "wait":
            dur = nav_info.get("duration", 5)
            print(f"[istina] 导航: {nav_info['desc']} → 等待 {dur}s")
            adb.wait(dur)
        elif action == "claim":
            for cx, cy in nav_info.get("claim_coords", []):
                print(f"  尝试点击 ({cx}, {cy})")
                adb.tap(cx, cy)
                adb.wait(1)
        return 0
    matched = False
    for page_type, keywords in PAGE_TYPE_KEYWORDS.items():
        if any(kw in target for kw in keywords):
            print(f"[istina] 页面类型 '{target}' → 匹配 '{page_type}'")
            matched = True
            break
    if not matched:
        print(f"[istina] 未知导航目标: {target}")
        print(f"  可用目标: {list(NAVIGATION_MAP.keys())}")
    print(f"[istina] 回退到探索引擎导航")
    result = run_script("navigate_to_game.py", capture=False, timeout=60)
    return 0


def cmd_doctor(args):
    """全面诊断"""
    from core.capability.adb_utils import ADB, list_devices, check_device
    from core.capability.local_inference import ModelManager
    from core.foundation.game_data import Coords

    print("=" * 50)
    print("IstinaEndfieldAssistant - 系统诊断")
    print("=" * 50)

    ADB_PATH = str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe")
    print(f"\n[ADB] Path: {ADB_PATH}")
    print(f"  Exists: {os.path.exists(ADB_PATH)}")
    ok = check_device()
    print(f"  Device connected: {ok}")
    if ok:
        devices = list_devices()
        print(f"  Devices: {devices}")

    print(f"\n[Server] 127.0.0.1:9999")
    try:
        from core.foundation.logger import init_logger
        init_logger()
        from core.service.communication import ClientCommunicator
        comm = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=10)
        r = comm.send_request("ping", {})
        print(f"  Status: {'OK' if r else 'No response'}")
    except Exception as e:
        print(f"  Error: {e}")

    config_path = PROJECT_ROOT / "config" / "client_config.json"
    print(f"\n[Config] {config_path}")
    print(f"  Exists: {config_path.exists()}")
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        print(f"  Server: {cfg.get('server')}")
        print(f"  Inference mode: {cfg.get('inference', {}).get('mode')}")

    manager = ModelManager(models_dir=str(PROJECT_ROOT / "models"))
    usage = manager.get_disk_usage()
    print(f"\n[Models]")
    print(f"  Disk usage: {usage.get('total_size_gb', 0):.1f}GB")
    for name, size in usage.get("models", {}).items():
        print(f"    {name}: {size:.1f}GB")

    try:
        from core.foundation.game_data import Coords
        print(f"\n[Coords] 模块已加载")
    except Exception as e:
        print(f"\n[Coords] 加载失败: {e}")

    print(f"\n[Python] {sys.version}")
    return 0


# ── 领域模块委托 ─────────────────────────────────────────────

def _delegate_with_extra(module_name: str, extra_args: List[str]) -> int:
    """委托给领域模块，透传额外参数"""
    if not extra_args:
        print(f"[istina] {module_name}: 需要子命令 (如 status)")
        return 1
    mod = _import_cli(module_name)
    if mod and hasattr(mod, "main"):
        importlib.reload(mod)
        sys.argv = ["", *extra_args]
        try:
            return mod.main()
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 0
    return _delegate_to_cli_module(module_name, extra_args)


def cmd_gpu(args, extra):
    return _delegate_with_extra("gpu_cli", extra)

def cmd_system(args, extra):
    return _delegate_with_extra("system_cli", extra)

def cmd_device(args, extra):
    return _delegate_with_extra("device_cli", extra)

def cmd_scene(args, extra):
    return _delegate_with_extra("scenario_cli", extra)


# ── CLI 解析 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="IstinaEndfieldAssistant — 统一 CLI v4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # ── module 子命令 ──
    p_mod = sub.add_parser("module", help="模块管理 (list/test/info)")
    p_mod_sub = p_mod.add_subparsers(dest="module_action", help="模块操作")

    p_mod_list = p_mod_sub.add_parser("list", help="列出所有模块")
    p_mod_list.add_argument("--json", action="store_true", help="JSON 输出")

    p_mod_test = p_mod_sub.add_parser("test", help="测试模块可用性")
    p_mod_test.add_argument("name", help="模块名 (或 'all')")
    p_mod_test.add_argument("--json", action="store_true", help="JSON 输出")

    p_mod_info = p_mod_sub.add_parser("info", help="查看模块详情")
    p_mod_info.add_argument("name", help="模块名")

    # ── 业务命令 ──
    p_daily = sub.add_parser("daily", help="每日签到+任务分析")
    p_daily.add_argument("--model", help="模型标签")
    p_daily.add_argument("--dry-run", action="store_true", help="仅分析不点击")
    p_daily.add_argument("--delay", type=float, help="点击后等待秒数")
    p_daily.add_argument("--timeout", type=int, default=300, help="超时秒数")

    p_harvest = sub.add_parser("harvest", help="实体图像采集")
    p_harvest.add_argument("--count", type=int, default=200)
    p_harvest.add_argument("--model")
    p_harvest.add_argument("--interval", type=float)
    p_harvest.add_argument("--timeout", type=int, default=7200)

    p_ana = sub.add_parser("analyze", help="VLM 分析当前画面")
    p_ana.add_argument("--model")
    p_ana.add_argument("--instruction", "-i", default="")
    p_ana.add_argument("--system-prompt")
    p_ana.add_argument("--timeout", type=int, default=120)

    p_exp = sub.add_parser("explore", help="UI 探索")
    p_exp.add_argument("--depth", type=int, default=3)
    p_exp.add_argument("--model")
    p_exp.add_argument("--timeout", type=int, default=1800)

    p_cfg = sub.add_parser("config", help="配置查看/修改")
    p_cfg.add_argument("key", nargs="?")
    p_cfg.add_argument("value", nargs="?")

    p_auth = sub.add_parser("auth", help="认证管理")
    p_auth.add_argument("action", choices=["status", "login", "logout"])
    p_auth.add_argument("--token")

    p_mdl = sub.add_parser("model", help="模型管理")
    p_mdl.add_argument("action", choices=["list", "info", "download", "disk"])
    p_mdl.add_argument("model_name", nargs="?")

    p_nav = sub.add_parser("nav", help="导航到页面")
    p_nav.add_argument("target")

    # ── 领域模块命令 ──
    sub.add_parser("gpu", help="GPU 检测")
    sub.add_parser("system", help="系统诊断")
    sub.add_parser("device", help="设备管理")
    sub.add_parser("scene", help="场景采集")

    args, extra = parser.parse_known_args()

    if not args.command:
        parser.print_help()
        return 1

    # ── 命令路由 ──
    if args.command == "module":
        if not args.module_action:
            print("需要子命令: list, test, info")
            return 1
        route = {
            "list": cmd_module_list,
            "test": cmd_module_test,
            "info": cmd_module_info,
        }
        return route[args.module_action](args)

    direct_commands = {
        "daily": cmd_daily,
        "harvest": cmd_harvest,
        "analyze": cmd_analyze,
        "explore": cmd_explore,
        "config": cmd_config,
        "auth": cmd_auth,
        "model": cmd_model,
        "nav": cmd_nav,
        "doctor": cmd_doctor,
    }
    delegated_commands = {
        "gpu": cmd_gpu,
        "system": cmd_system,
        "device": cmd_device,
        "scene": cmd_scene,
    }

    if args.command in direct_commands:
        return direct_commands[args.command](args)
    elif args.command in delegated_commands:
        return delegated_commands[args.command](args, extra)
    else:
        print(f"[istina] 未知命令: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

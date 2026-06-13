"""
IEA ADB 工具层 — 统一设备操作接口

整合所有 ADB 相关操作（screencap），提供：
- 截图哈希去重
- 重试与超时机制
- 统一的 VLM 分析接口（通过 IstinaPlatform TCP）

注意：触控操作（tap/swipe/keyevent）已完全迁移至 MaaFw TouchManager，
不再通过 adb shell input 执行。

用法:
  from core.adb_utils import ADB
  adb = ADB()
  img = adb.screencap()      # 截图
  result = adb.vlm_analyze(img, "分析画面")
"""

import io, os, sys, time, json, base64, hashlib, subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field


# ── 项目路径 ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ADB_PATH = str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe")
DEVICE_SERIAL = "localhost:16512"

# 服务器连接参数
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999
SERVER_PASSWORD = "default_password"
API_KEY = "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"


# ── 异常 ──────────────────────────────────────────────────────────
class ADBError(Exception):
    """ADB 操作异常"""
    pass

class ScreenshotError(ADBError):
    """截图异常"""
    pass

class TimeoutError(ADBError):
    """操作超时"""
    pass


# ── ADB 设备管理 ──────────────────────────────────────────────────
def _adb_cmd(args: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
    """执行 ADB 命令"""
    cmd = [ADB_PATH, "-s", DEVICE_SERIAL] + args
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"ADB 命令超时: {' '.join(args[:3])}")
    except FileNotFoundError:
        raise ADBError(f"ADB 未找到: {ADB_PATH}")


def check_device() -> bool:
    """检查 ADB 设备是否在线"""
    try:
        r = _adb_cmd(["get-state"], timeout=5)
        return r.returncode == 0 and r.stdout.decode().strip() == "device"
    except ADBError:
        return False


def list_devices() -> List[str]:
    """列出 ADB 设备"""
    r = _adb_cmd(["devices"], timeout=5)
    lines = r.stdout.decode().strip().split("\n")[1:]
    return [l.split("\t")[0] for l in lines if l.strip() and "device" in l]


# ── ADB 截图 ──────────────────────────────────────────────────────

def adb_screencap(timeout: int = 15) -> Optional[bytes]:
    """ADB 截图，返回 PNG 字节"""
    try:
        r = _adb_cmd(["exec-out", "screencap", "-p"], timeout=timeout)
        if r.returncode == 0 and len(r.stdout) > 1000:
            return r.stdout
        return None
    except ADBError:
        return None


def adb_screencap_unique(timeout: int = 15,
                          last_hash: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
    """截图并去重，返回 (image_bytes, md5_hash)

    如果画面与 last_hash 相同则返回 (None, same_hash)
    """
    img = adb_screencap(timeout=timeout)
    if img is None:
        return (None, None)

    h = hashlib.md5(img).hexdigest()
    if last_hash is not None and h == last_hash:
        return (None, h)

    return (img, h)


# ── 重试工具 ──────────────────────────────────────────────────────
def retry(max_attempts: int = 3, delay: float = 1.0,
          backoff: float = 2.0) -> Callable:
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (backoff ** attempt))
            raise last_exc  # type: ignore
        return wrapper
    return decorator


# ── VLM 分析接口 ──────────────────────────────────────────────────
@dataclass
class VLMOptions:
    """VLM 调用参数"""
    model_tag: str = "exploration_deep"
    timeout: int = 120
    temperature: float = 0.01
    max_tokens: int = 2048
    system_prompt: str = ""


DEFAULT_VLM_OPTS = VLMOptions()


def vlm_analyze(image_bytes: bytes,
                instruction: str = "识别当前画面",
                opts: Optional[VLMOptions] = None,
                communicator=None) -> Optional[Dict[str, Any]]:
    """通过 IstinaPlatform TCP 调用 VLM 分析画面

    Args:
        image_bytes: PNG 截图字节
        instruction: 分析指令
        opts: VLM 参数
        communicator: 可复用的 communicator 实例（避免重复登录）

    Returns:
        VLM 回复文本或 None
    """
    if opts is None:
        opts = DEFAULT_VLM_OPTS

    if communicator is None:
        from core.communication.communicator import ClientCommunicator
        from core.logger import init_logger
        init_logger()
        comm = ClientCommunicator(
            host=SERVER_HOST, port=SERVER_PORT,
            password=SERVER_PASSWORD, timeout=opts.timeout
        )
        r = comm.send_request("login", {
            "user_id": "explorer",
            "key": API_KEY
        })
        sid = r.get("session_id", "") if r else ""
        comm.set_logged_in(True)
    else:
        comm = communicator
        sid = ""

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    resp = comm.send_request("agent_chat", {
        "instruction": instruction,
        "screenshot": b64,
        "history": [],
        "session_id": sid,
        "user_id": "explorer",
        "model_tag": opts.model_tag,
        "system_prompt": opts.system_prompt or "你是终末地界面分析器。输出JSON格式。",
        "temperature": opts.temperature,
        "max_tokens": opts.max_tokens,
    })

    if resp and resp.get("status") == "success":
        return resp
    return None


# ── 统一 ADB 接口类 ──────────────────────────────────────────────
class ADB:
    """统一 ADB 操作接口（便捷封装）
    
    注意：tap/swipe/keyevent 已迁移至 TouchManager/MaaFwTouchExecutor，
    此类仅保留截图和连接管理功能。
    """

    def __init__(self, serial: str = DEVICE_SERIAL):
        self.serial = serial
        self._last_screenshot_hash: Optional[str] = None

    def screencap(self, dedup: bool = True) -> Optional[bytes]:
        """截图（可选去重）

        去重启用时，如果画面与上次相同返回 None
        """
        if dedup:
            img, h = adb_screencap_unique(last_hash=self._last_screenshot_hash)
            if img is not None:
                self._last_screenshot_hash = h
            return img
        else:
            return adb_screencap()

    def wait(self, seconds: float):
        """等待"""
        time.sleep(seconds)

    def screenshot_path(self, session_dir: str, tag: str = "img") -> Optional[str]:
        """截图并保存到文件"""
        img = self.screencap(dedup=False)
        if img is None:
            return None
        os.makedirs(session_dir, exist_ok=True)
        h = hashlib.md5(img).hexdigest()[:8]
        path = os.path.join(session_dir, f"{tag}_{int(time.time())}_{h}.png")
        with open(path, "wb") as f:
            f.write(img)
        return path

    def check_connection(self) -> bool:
        """检查设备连接"""
        return check_device()

#utils/android_control.py
"""
完整版 Android 设备控制函数模块
提供设备发现、连接、触摸控制、文本输入、按键、屏幕截图和时间获取功能
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import base64
import cv2
import subprocess
import os
from dataclasses import dataclass
from enum import Enum


# 定义ADB路径常量
ADB_PATH = "3rd-part/ADB/adb.exe"

# 定义按键代码常量
class KeyCode:
    BACK = 4
    HOME = 3
    MENU = 82
    ENTER = 66
    DEL = 67
    VOLUME_UP = 24
    VOLUME_DOWN = 25
    POWER = 26


# 存储已连接的控制器
_connected_controllers = {}


def find_adb_device_list() -> List[str]:
    """
    扫描并枚举当前系统中所有可用的 ADB 设备，包括网络设备。
    返回设备名称列表
    """
    try:
        # 先确保ADB服务器启动
        try:
            subprocess.run([ADB_PATH, "start-server"], capture_output=True, text=True, timeout=5)
        except:
            pass

        time.sleep(1)  # 等待ADB初始化

        # 获取所有USB连接的设备
        result = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True, timeout=10)

        devices = []
        lines = result.stdout.strip().split('\n')

        # 跳过标题行
        start_index = 1 if lines and "List of devices attached" in lines[0] else 0

        for line in lines[start_index:]:
            line = line.strip()
            if line and '\t' in line:
                device_id, status = line.split('\t')
                if status == 'device':
                    devices.append(device_id)

        # 尝试获取已连接的网络设备（如果有保存的IP列表）
        try:
            # 检查已有的网络连接
            connected_result = subprocess.run([ADB_PATH, "devices", "-l"],
                                            capture_output=True, text=True, timeout=10)
            for line in connected_result.stdout.split('\n'):
                if 'product:' in line and 'model:' in line:
                    # 提取IP地址（如果有）
                    parts = line.split()
                    for part in parts:
                        if ':' in part and '.' in part and 'product:' not in part and 'model:' not in part:
                            if part not in devices:
                                devices.append(part)
        except:
            pass

        return devices
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # 如果 adb 命令不存在或超时，返回空列表
        return []


def connect_adb_device(device_name: str) -> Optional[str]:
    """
    建立与指定 ADB 设备的连接，支持网络设备。
    参数:
    - device_name: 目标设备名称 (格式: IP:PORT 或 192.168.1.100:5555)
    返回:
    - 成功：返回控制器 ID
    - 失败：返回 None
    """
    try:
        # 检查是否为网络设备格式 (IP:PORT)
        is_network_device = ':' in device_name and '.' in device_name.split(':')[0]

        if is_network_device:
            # 网络设备，先尝试连接
            ip_port = device_name
            print(f"尝试连接网络设备: {ip_port}")

            # 执行adb connect命令
            connect_cmd = [ADB_PATH, "connect", ip_port]
            result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=10)

            # 检查连接结果
            if result.returncode == 0:
                if "connected" in result.stdout.lower() or "already" in result.stdout.lower():
                    print(f"设备连接成功: {result.stdout.strip()}")
                    # 等待连接稳定
                    time.sleep(2)
                else:
                    print(f"连接可能失败: {result.stdout}")
                    return None
            else:
                print(f"连接命令执行失败: {result.stderr}")
                return None

        # 检查设备是否在可用设备列表中
        print("扫描可用设备...")
        devices = find_adb_device_list()
        print(f"当前可用设备: {devices}")

        # 对于网络设备，可能需要检查连接状态
        if is_network_device and device_name not in devices:
            # 尝试再次连接
            print(f"设备 {device_name} 不在列表中，重新连接...")
            connect_cmd = [ADB_PATH, "connect", device_name]
            retry_result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=10)
            print(f"重连结果: {retry_result.stdout}")

            # 再次检查设备列表
            time.sleep(2)
            devices = find_adb_device_list()
            print(f"重连后可用设备: {devices}")

        # 检查设备是否可用
        if device_name not in devices:
            print(f"警告: 设备 {device_name} 不在可用设备列表中")

            # 如果是网络设备，尝试强制连接
            if is_network_device:
                print("尝试强制连接...")
                force_cmd = [ADB_PATH, "connect", f"{device_name}"]
                subprocess.run(force_cmd, capture_output=True, text=True, timeout=10)
                time.sleep(2)

                # 再次检查
                devices = find_adb_device_list()
                if device_name not in devices:
                    print(f"设备 {device_name} 无法连接")
                    return None
            else:
                # USB设备，直接返回失败
                return None

        # 创建控制器ID
        controller_id = f"adb_controller_{device_name}_{int(datetime.now().timestamp())}"
        _connected_controllers[controller_id] = device_name

        print(f"连接成功，控制器ID: {controller_id}")
        return controller_id

    except Exception as e:
        print(f"连接设备时发生错误: {e}")
        return None


def click(
    controller_id: str, x: int, y: int, button: int = 0, duration: int = 50
) -> bool:
    """
    在设备屏幕上执行单点点击操作，支持长按。
    参数:
    - controller_id: 控制器 ID
    - x: 目标点的 X 坐标（像素，整数）
    - y: 目标点的 Y 坐标（像素，整数）
    - button: 按键编号，默认为 0
    - duration: 按下持续时间（毫秒），默认为 50
    返回:
    - 成功：返回 True
    - 失败：返回 False
    """
    if controller_id not in _connected_controllers:
        return False

    device_name = _connected_controllers[controller_id]

    try:
        # 执行点击操作
        cmd = [ADB_PATH, "-s", device_name, "shell", "input", "tap", str(x), str(y)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if duration > 50:
            # 如果需要长按，短暂等待
            time.sleep(duration / 1000.0)

        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def double_click(
    controller_id: str,
    x: int,
    y: int,
    button: int = 0,
    duration: int = 50,
    interval: int = 100,
) -> bool:
    """
    在设备屏幕上执行双击操作。
    参数:
    - controller_id: 控制器 ID
    - x: 目标点的 X 坐标（像素，整数）
    - y: 目标点的 Y 坐标（像素，整数）
    - button: 按键编号，默认为 0
    - duration: 每次按下的持续时间（毫秒），默认为 50
    - interval: 两次点击之间的间隔时间（毫秒），默认为 100
    返回:
    - 成功：返回 True
    - 失败：返回 False
    """
    if controller_id not in _connected_controllers:
        return False

    device_name = _connected_controllers[controller_id]

    try:
        # 第一次点击
        cmd1 = [ADB_PATH, "-s", device_name, "shell", "input", "tap", str(x), str(y)]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)

        if result1.returncode != 0:
            return False

        # 间隔等待
        time.sleep(interval / 1000.0)

        # 第二次点击
        cmd2 = [ADB_PATH, "-s", device_name, "shell", "input", "tap", str(x), str(y)]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)

        return result2.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def swipe(
    controller_id: str,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: int,
) -> bool:
    """
    在设备屏幕上执行手势滑动操作，模拟手指从起始点滑动到终点。
    参数:
    - controller_id: 控制器 ID
    - start_x: 起始点的 X 坐标（像素，整数）
    - start_y: 起始点的 Y 坐标（像素，整数）
    - end_x: 终点的 X 坐标（像素，整数）
    - end_y: 终点的 Y 坐标（像素，整数）
    - duration: 滑动持续时间（毫秒，整数）
    返回:
    - 成功：返回 True
    - 失败：返回 False
    """
    if controller_id not in _connected_controllers:
        return False

    device_name = _connected_controllers[controller_id]

    try:
        # 执行滑动操作
        cmd = [
            ADB_PATH, "-s", device_name, "shell", "input", "swipe",
            str(start_x), str(start_y), str(end_x), str(end_y), str(duration)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def input_text(controller_id: str, text: str) -> bool:
    """
    在设备屏幕上执行输入文本操作。
    参数:
    - controller_id: 控制器 ID
    - text: 要输入的文本（字符串）
    返回:
    - 成功：返回 True
    - 失败：返回 False
    """
    if controller_id not in _connected_controllers:
        return False

    device_name = _connected_controllers[controller_id]

    try:
        # 执行文本输入操作
        # 需要对特殊字符进行转义
        escaped_text = text.replace("'", "\\'").replace('"', '\\"')
        cmd = [ADB_PATH, "-s", device_name, "shell", "input", "text", escaped_text]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def click_key(controller_id: str, key: int, duration: int = 50) -> bool:
    """
    在设备屏幕上执行按键点击操作，支持长按。
    参数:
    - controller_id: 控制器 ID
    - key: 要点击的按键（虚拟按键码）
    - duration: 按键持续时间（毫秒），默认为 50
    返回:
    - 成功：返回 True
    - 失败：返回 False

    常用按键值：
    - 返回键: 4
    - Home键: 3
    - 菜单键: 82
    - 回车/确认: 66
    - 删除/退格: 67
    - 音量+: 24
    - 音量-: 25
    - 电源键: 26
    """
    if controller_id not in _connected_controllers:
        return False

    device_name = _connected_controllers[controller_id]

    try:
        # 执行按键操作
        cmd = [ADB_PATH, "-s", device_name, "shell", "input", "keyevent", str(key)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if duration > 50:
            # 如果需要长按，短暂等待
            time.sleep(duration / 1000.0)

        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def screencap(controller_id: str) -> Optional[object]:
    """
    对当前设备屏幕进行截图，并返回图像数据。
    参数:
    - controller_id: 控制器 ID
    返回:
    - 成功：返回截图的base64编码数据
    - 失败：返回 None
    """
    if controller_id not in _connected_controllers:
        return None

    device_name = _connected_controllers[controller_id]

    try:
        # 创建临时文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_png = f"/sdcard/screenshot_{timestamp}.png"
        local_png = f"screenshot_{timestamp}.png"

        # 在设备上截图
        cmd1 = [ADB_PATH, "-s", device_name, "shell", "screencap", "-p", temp_png]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=15)

        if result1.returncode != 0:
            return None

        # 将截图拉取到本地
        cmd2 = [ADB_PATH, "-s", device_name, "pull", temp_png, local_png]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)

        if result2.returncode != 0:
            # 清理设备上的临时文件
            subprocess.run([ADB_PATH, "-s", device_name, "shell", "rm", temp_png],
                          capture_output=True, timeout=5)
            return None

        # 删除设备上的临时文件
        subprocess.run([ADB_PATH, "-s", device_name, "shell", "rm", temp_png],
                      capture_output=True, timeout=5)

        # 读取图像文件
        if not os.path.exists(local_png):
            return None

        # 读取图像
        image = cv2.imread(local_png)
        if image is None:
            # 删除本地临时文件
            if os.path.exists(local_png):
                os.remove(local_png)
            return None

        # 将图像压缩为JPEG格式
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]  # 85%质量
        success, encoded_image = cv2.imencode('.jpg', image, encode_param)

        if not success:
            # 如果JPEG编码失败，回退到PNG格式
            success, encoded_image = cv2.imencode('.png', image)
            if not success:
                # 删除本地临时文件
                if os.path.exists(local_png):
                    os.remove(local_png)
                return None
            mime_type = "image/png"
            format_extension = ".png"
        else:
            mime_type = "image/jpeg"
            format_extension = ".jpg"

        # 将压缩后的图像数据转换为base64字符串
        image_data = encoded_image.tobytes()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"

        # 保存截图到本地
        try:
            screenshots_dir = Path("./screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            filepath = screenshots_dir / f"screenshot_{timestamp}{format_extension}"

            # 将图像数据写入文件
            with open(filepath, 'wb') as f:
                f.write(image_data)

            # 删除临时PNG文件
            if os.path.exists(local_png):
                os.remove(local_png)
        except:
            # 如果无法保存文件，继续执行
            # 删除临时PNG文件
            if os.path.exists(local_png):
                os.remove(local_png)
            pass

        # 创建一个简单的 Image 类来包装数据
        class Image:
            def __init__(self, data):
                self.data = data

        # 返回包含base64数据URL的Image对象
        return Image(data_url)

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        # 清理可能存在的临时文件
        if 'temp_png' in locals():
            try:
                subprocess.run([ADB_PATH, "-s", device_name, "shell", "rm", temp_png],
                              capture_output=True, timeout=5)
            except:
                pass
        if 'local_png' in locals() and os.path.exists(local_png):
            try:
                os.remove(local_png)
            except:
                pass
        return None


def get_current_datetime() -> str:
    """
    获取当前时间字符串（年月日时分秒）。
    返回当前时间字符串，例如：2025-12-14 10:23:45
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def add_network_device(ip: str, port: str = "5555") -> bool:
    """
    添加网络ADB设备。
    参数:
    - ip: 设备IP地址
    - port: ADB端口，默认5555
    返回:
    - 成功返回True，失败返回False
    """
    try:
        device_address = f"{ip}:{port}"
        print(f"添加网络设备: {device_address}")

        # 连接设备
        connect_cmd = [ADB_PATH, "connect", device_address]
        result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            if "connected" in result.stdout.lower() or "already" in result.stdout.lower():
                print(f"设备添加成功: {device_address}")
                return True
            else:
                print(f"设备添加失败: {result.stdout}")
                return False
        else:
            print(f"连接命令失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"添加网络设备时发生错误: {e}")
        return False


def disconnect_device(controller_id: str) -> bool:
    """
    断开ADB设备连接（对于网络设备）。
    参数:
    - controller_id: 控制器ID
    返回:
    - 成功返回True，失败返回False
    """
    try:
        if controller_id not in _connected_controllers:
            return False

        device_name = _connected_controllers[controller_id]

        # 检查是否为网络设备
        is_network_device = ':' in device_name and '.' in device_name.split(':')[0]

        if is_network_device:
            # 断开网络连接
            disconnect_cmd = [ADB_PATH, "disconnect", device_name]
            result = subprocess.run(disconnect_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print(f"网络设备已断开: {device_name}")

        # 从控制器列表中移除
        del _connected_controllers[controller_id]
        return True

    except Exception as e:
        print(f"断开设备时发生错误: {e}")
        return False


def check_network_device_status(ip: str, port: str = "5555") -> str:
    """
    检查网络设备状态。
    返回:
    - "connected": 已连接
    - "disconnected": 未连接
    - "error": 检查出错
    """
    try:
        device_address = f"{ip}:{port}"

        # 检查设备是否在列表中
        devices = find_adb_device_list()

        if device_address in devices:
            # 进一步检查设备是否响应
            try:
                test_cmd = [ADB_PATH, "-s", device_address, "shell", "echo", "test"]
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return "connected"
                else:
                    return "disconnected"
            except:
                return "disconnected"
        else:
            return "disconnected"

    except Exception as e:
        print(f"检查设备状态时发生错误: {e}")
        return "error"


def list_network_devices() -> List[str]:
    """
    获取所有网络连接的ADB设备。
    返回网络设备地址列表
    """
    try:
        devices = find_adb_device_list()
        network_devices = []

        for device in devices:
            if ':' in device and '.' in device.split(':')[0]:
                network_devices.append(device)

        return network_devices
    except Exception as e:
        print(f"获取网络设备列表时发生错误: {e}")
        return []


# 导出函数
__all__ = [
    "find_adb_device_list",
    "connect_adb_device",
    "click",
    "double_click",
    "swipe",
    "input_text",
    "click_key",
    "screencap",
    "get_current_datetime",
    # 新增的网络设备管理函数
    "add_network_device",
    "disconnect_device",
    "check_network_device_status",
    "list_network_devices"
]
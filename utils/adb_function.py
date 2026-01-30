import subprocess
import socket
import time
import os
import re
import logging
import tempfile
import shutil
import requests
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """设备信息数据类"""
    id: str
    status: str
    model: str = ""
    api_level: int = 0
    abi: str = ""  # CPU 架构


class MiniTouchController:
    """基于 MiniTouch 的高精度安卓触控控制器（无仿人延迟）"""
    
    # MiniTouch 二进制源
    MINITOUCH_SOURCES = [
        "https://github.com/openatx/stf-binaries/raw/master/prebuilt/{arch}/bin/minitouch",
        "https://unpkg.com/@devicefarmer/minitouch-prebuilt@1.3.0/prebuilt/{arch}/bin/minitouch"
    ]
    
    # STFService APK 下载地址
    STFSERVICE_APK_URL = "https://github.com/openstf/stf/releases/download/v2.3/STFService.apk"
    
    # 本地缓存目录
    CACHE_DIR = os.path.join(tempfile.gettempdir(), "minitouch_cache")
    
    def __init__(self, adb_path: str = None):
        """
        初始化 MiniTouch 控制器
        
        参数:
            adb_path (str): ADB 可执行文件路径，默认使用项目内的 "3rd-part/ADB/adb.exe"
        
        异常:
            RuntimeError: ADB 不可用或验证失败
        """
        if adb_path is None:
            # 默认使用项目内的 ADB 路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.adb_path = os.path.join(base_dir, "3rd-part", "ADB", "adb.exe")
            
            # 如果默认路径不存在，尝试其他可能的路径
            if not os.path.exists(self.adb_path):
                # 尝试当前目录下的相对路径
                self.adb_path = os.path.join("3rd-part", "ADB", "adb.exe")
                
                if not os.path.exists(self.adb_path):
                    # 尝试系统 PATH 中的 adb
                    self.adb_path = "adb"
                    logger.warning("使用默认ADB路径失败，尝试系统PATH中的adb")
        else:
            self.adb_path = adb_path
            
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self._validate_adb()
        self._device_sockets: Dict[str, socket.socket] = {}
        self._device_ports: Dict[str, int] = {}
        self._device_screen_info: Dict[str, Dict] = {}
        self._minitouch_pids: Dict[str, str] = {}
    
    def _run_adb(self, args: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        """执行 ADB 命令"""
        cmd = [self.adb_path] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            if result.returncode != 0 and 'error' in result.stderr.lower():
                logger.warning(f"ADB 命令警告: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ADB 命令超时 ({timeout}s): {' '.join(cmd)}")
        except Exception as e:
            raise RuntimeError(f"ADB 命令执行失败: {e}")
    
    def _validate_adb(self):
        """验证 ADB 可用性"""
        try:
            result = self._run_adb(['version'])
            if result.returncode != 0:
                raise RuntimeError(f"ADB 不可用: {result.stderr}")
            logger.info(f"✓ ADB 版本: {result.stdout.splitlines()[0]}")
            
            # 检查设备连接
            result = self._run_adb(['devices'])
            if result.returncode != 0:
                raise RuntimeError(f"ADB 设备检测失败: {result.stderr}")
                
        except FileNotFoundError:
            raise RuntimeError(f"找不到 ADB 可执行文件: {self.adb_path}")
        except Exception as e:
            raise RuntimeError(f"ADB 验证失败: {e}")
    
    def list_devices(self) -> List[DeviceInfo]:
        """
        列出所有连接的设备
        
        :return: 设备信息列表
        """
        result = self._run_adb(['devices', '-l'])
        devices = []
        
        for line in result.stdout.strip().splitlines()[1:]:
            if not line.strip() or 'List of devices' in line:
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
                
            dev_id = parts[0]
            status = parts[1]
            
            # 提取 model
            model = ""
            for part in parts[2:]:
                if part.startswith('model:'):
                    model = part.split(':', 1)[1]
                    break
            
            # 获取 API level 和 ABI
            api_level = 0
            abi = ""
            try:
                api_result = self._run_adb(['-s', dev_id, 'shell', 'getprop', 'ro.build.version.sdk'])
                if api_result.returncode == 0:
                    api_level = int(api_result.stdout.strip())
                
                abi_result = self._run_adb(['-s', dev_id, 'shell', 'getprop', 'ro.product.cpu.abi'])
                if abi_result.returncode == 0:
                    abi = abi_result.stdout.strip()
            except:
                pass
            
            devices.append(DeviceInfo(
                id=dev_id,
                status=status,
                model=model,
                api_level=api_level,
                abi=abi
            ))
        
        if not devices:
            logger.warning("⚠ 未检测到任何设备，请检查 USB 连接或执行 'adb devices'")
        else:
            logger.info(f"✓ 检测到 {len(devices)} 个设备:")
            for i, dev in enumerate(devices, 1):
                logger.info(f"  {i}. [{dev.status}] {dev.id} | Model: {dev.model or 'N/A'} | API: {dev.api_level} | ABI: {dev.abi}")
        
        return devices
    
    def connect(self, device_id: str, reinstall: bool = False) -> bool:
        """
        连接设备并初始化 MiniTouch 服务
        
        :param device_id: 设备序列号
        :param reinstall: 强制重新安装 MiniTouch
        :return: 连接是否成功
        """
        # 检查设备是否存在
        devices = self.list_devices()
        device = next((d for d in devices if d.id == device_id), None)
        if not device:
            raise ValueError(f"设备 {device_id} 未连接或状态异常")
        
        # 检查 Android 10+ 限制并安装 STFService
        if device.api_level >= 29:  # Android 10+
            self._check_and_install_stfservice(device_id, device.api_level)
        
        # 获取屏幕信息
        screen_info = self._get_screen_info(device_id)
        self._device_screen_info[device_id] = screen_info
        logger.info(f"✓ 屏幕分辨率: {screen_info['width']}x{screen_info['height']}")
        
        # 检查/部署 MiniTouch
        if reinstall or not self._check_minitouch_installed(device_id):
            self._deploy_minitouch(device_id, device.abi)
        else:
            logger.info(f"✓ MiniTouch 已安装在 {device_id}")
        
        # 杀死可能存在的旧进程
        self._kill_minitouch(device_id)
        
        # 启动 MiniTouch 服务
        pid = self._start_minitouch_service(device_id)
        self._minitouch_pids[device_id] = pid
        logger.info(f"✓ MiniTouch 服务启动 (PID: {pid})")
        
        # 端口转发
        local_port = self._setup_port_forwarding(device_id)
        self._device_ports[device_id] = local_port
        
        # 建立 Socket 连接
        sock = self._connect_socket(local_port)
        self._device_sockets[device_id] = sock
        
        # 读取 MiniTouch 元数据 (max_x, max_y)
        meta = self._read_minitouch_metadata(sock)
        self._device_screen_info[device_id].update(meta)
        logger.info(f"✓ MiniTouch 坐标范围: X[0-{meta['max_x']}] Y[0-{meta['max_y']}]")
        
        logger.info(f"✓ 设备 {device_id} 连接成功")
        return True
    
    def disconnect(self, device_id: str):
        """断开设备连接并清理资源"""
        # 关闭 socket
        if device_id in self._device_sockets:
            try:
                self._device_sockets[device_id].close()
            except:
                pass
            del self._device_sockets[device_id]
        
        # 移除端口转发
        if device_id in self._device_ports:
            try:
                self._run_adb(['-s', device_id, 'forward', '--remove', f'tcp:{self._device_ports[device_id]}'])
            except:
                pass
            del self._device_ports[device_id]
        
        # 杀死 MiniTouch 进程
        if device_id in self._minitouch_pids:
            self._kill_minitouch(device_id)
            del self._minitouch_pids[device_id]
        
        # 清理屏幕信息
        self._device_screen_info.pop(device_id, None)
        
        logger.info(f"✓ 设备 {device_id} 已断开")
    
    def _get_screen_info(self, device_id: str) -> Dict:
        """获取设备屏幕信息"""
        # 方法1: wm size
        result = self._run_adb(['-s', device_id, 'shell', 'wm', 'size'])
        if result.returncode == 0:
            match = re.search(r'(\d+)x(\d+)', result.stdout)
            if match:
                return {
                    'width': int(match.group(1)),
                    'height': int(match.group(2))
                }
        
        # 方法2: dumpsys display
        result = self._run_adb(['-s', device_id, 'shell', 'dumpsys', 'display'])
        if result.returncode == 0:
            match = re.search(r'displayWidth=(\d+).*?displayHeight=(\d+)', result.stdout, re.DOTALL)
            if match:
                return {
                    'width': int(match.group(1)),
                    'height': int(match.group(2))
                }
        
        raise RuntimeError(f"无法获取设备 {device_id} 的屏幕分辨率")
    
    def _check_minitouch_installed(self, device_id: str) -> bool:
        """检查 MiniTouch 是否已安装"""
        result = self._run_adb(['-s', device_id, 'shell', 'test', '-x', '/data/local/tmp/minitouch', '&&', 'echo', 'OK'])
        return 'OK' in result.stdout
    
    def _download_minitouch_binary(self, abi: str) -> str:
        """下载对应架构的 MiniTouch 二进制到本地缓存"""
        # 架构映射
        ABI_MAP = {
            'arm64-v8a': 'arm64-v8a',
            'armeabi-v7a': 'armeabi-v7a',
            'x86_64': 'x86_64',
            'x86': 'x86'
        }
        
        arch = None
        if 'arm64' in abi or 'armv8' in abi:
            arch = 'arm64-v8a'
        elif 'armeabi' in abi:
            arch = 'armeabi-v7a'
        elif 'x86_64' in abi:
            arch = 'x86_64'
        elif 'x86' in abi:
            arch = 'x86'
        
        if not arch:
            raise ValueError(f"不支持的 CPU 架构: {abi}")
        
        # 检查缓存
        cache_path = os.path.join(self.CACHE_DIR, f"minitouch-{arch}")
        if os.path.exists(cache_path):
            logger.info(f"✓ 使用缓存的 MiniTouch 二进制: {cache_path}")
            return cache_path
        
        # 下载二进制
        for url_template in self.MINITOUCH_SOURCES:
            url = url_template.format(arch=arch)
            try:
                logger.info(f"→ 下载 MiniTouch ({arch}) 从 {url}")
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                
                # 保存为可执行文件
                with open(cache_path, 'wb') as f:
                    f.write(resp.content)
                os.chmod(cache_path, 0o755)
                logger.info(f"✓ 二进制已缓存至: {cache_path}")
                return cache_path
                
            except Exception as e:
                logger.warning(f"下载失败 ({url}): {e}")
                continue
        
        raise RuntimeError(f"无法下载 {arch} 架构的 MiniTouch 二进制")
    
    def _deploy_minitouch(self, device_id: str, abi: str):
        """部署 MiniTouch 二进制到设备"""
        # 下载二进制
        bin_path = self._download_minitouch_binary(abi)
        
        # 推送到设备
        logger.info(f"→ 部署 MiniTouch 到设备 {device_id}...")
        push_result = self._run_adb(['-s', device_id, 'push', bin_path, '/data/local/tmp/minitouch'])
        if push_result.returncode != 0:
            # 尝试使用 STFService 的路径（Android 10+）
            push_result = self._run_adb(['-s', device_id, 'push', bin_path, '/data/local/tmp/minitouch'])
            if push_result.returncode != 0:
                raise RuntimeError(f"推送 MiniTouch 失败: {push_result.stderr}")
        
        # 赋予执行权限
        chmod_result = self._run_adb(['-s', device_id, 'shell', 'chmod', '755', '/data/local/tmp/minitouch'])
        if chmod_result.returncode != 0:
            raise RuntimeError(f"设置权限失败: {chmod_result.stderr}")
        
        logger.info("✓ MiniTouch 部署成功")
    
    def _check_and_install_stfservice(self, device_id: str, api_level: int):
        """
        检查 Android 10+ 设备并自动安装 STFService
        
        Android 10+ 限制:
          - /data/local/tmp 不可执行 (SELinux 限制)
          - 需要 STFService.apk 提供执行环境
        """
        if api_level < 29:
            return
        
        # 检查 STFService 是否已安装
        result = self._run_adb(['-s', device_id, 'shell', 'pm', 'list', 'packages', '|', 'grep', 'jp.co.cyberagent.stf'])
        if 'jp.co.cyberagent.stf' in result.stdout:
            logger.info(f"✓ STFService 已安装 (Android {api_level})")
            return
        
        # 下载 APK
        apk_path = os.path.join(self.CACHE_DIR, "STFService.apk")
        if not os.path.exists(apk_path):
            logger.info(f"→ 下载 STFService.apk 从 {self.STFSERVICE_APK_URL}")
            try:
                resp = requests.get(self.STFSERVICE_APK_URL, timeout=60)
                resp.raise_for_status()
                with open(apk_path, 'wb') as f:
                    f.write(resp.content)
                logger.info(f"✓ APK 已缓存至: {apk_path}")
            except Exception as e:
                raise RuntimeError(f"下载 STFService.apk 失败: {e}")
        
        # 安装 APK
        logger.info(f"→ 安装 STFService (Android {api_level} 需要此服务)...")
        install_result = self._run_adb(['-s', device_id, 'install', '-r', '-g', apk_path])
        if install_result.returncode != 0:
            raise RuntimeError(f"安装 STFService 失败: {install_result.stderr}")
        
        # 启动服务
        start_result = self._run_adb([
            '-s', device_id, 'shell', 'am', 'startservice',
            '-n', 'jp.co.cyberagent.stf/.Service',
            '-a', 'jp.co.cyberagent.stf.ACTION_START'
        ])
        if start_result.returncode != 0:
            logger.warning(f"启动 STFService 服务警告: {start_result.stderr}")
        
        logger.info("✓ STFService 安装并启动成功")
    
    def _kill_minitouch(self, device_id: str):
        """杀死设备上运行的 MiniTouch 进程"""
        # 方法1: pidof
        result = self._run_adb(['-s', device_id, 'shell', 'pidof', 'minitouch'])
        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip()
            self._run_adb(['-s', device_id, 'shell', 'kill', '-9', pid])
            time.sleep(0.2)
            return
        
        # 方法2: pgrep
        result = self._run_adb(['-s', device_id, 'shell', 'pgrep', 'minitouch'])
        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip()
            self._run_adb(['-s', device_id, 'shell', 'kill', '-9', pid])
            time.sleep(0.2)
    
    def _start_minitouch_service(self, device_id: str) -> str:
        """启动 MiniTouch 服务并返回 PID"""
        # Android 10+ 使用 STFService 路径
        minitouch_path = "/data/local/tmp/minitouch"
        
        # 启动命令 (后台运行)
        cmd = f"sh -c '{minitouch_path} 2>&1 >/dev/null &' && echo $!"
        
        result = self._run_adb(['-s', device_id, 'shell', cmd])
        if result.returncode != 0:
            raise RuntimeError(f"启动 MiniTouch 失败: {result.stderr}")
        
        pid = result.stdout.strip()
        if not pid.isdigit():
            raise RuntimeError(f"无法获取 MiniTouch PID: {pid}")
        
        # 等待服务启动
        time.sleep(0.3)
        return pid
    
    def _setup_port_forwarding(self, device_id: str) -> int:
        """设置 ADB 端口转发"""
        # 分配唯一本地端口
        local_port = 20000
        while local_port in self._device_ports.values():
            local_port += 1
        
        # 设置转发
        result = self._run_adb([
            '-s', device_id, 
            'forward', 
            f'tcp:{local_port}', 
            'localabstract:minitouch'
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"端口转发失败: {result.stderr}")
        
        logger.debug(f"→ 端口转发: 设备 minitouch → 本地 {local_port}")
        return local_port
    
    def _connect_socket(self, local_port: int, retries: int = 5) -> socket.socket:
        """连接到 MiniTouch Socket"""
        for i in range(retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(('127.0.0.1', local_port))
                sock.settimeout(None)
                return sock
            except (ConnectionRefusedError, socket.timeout) as e:
                if i == retries - 1:
                    raise RuntimeError(f"无法连接 MiniTouch Socket (端口 {local_port}): {e}")
                time.sleep(0.3)
    
    def _read_minitouch_metadata(self, sock: socket.socket) -> Dict:
        """读取 MiniTouch 元数据 (版本和坐标范围)"""
        metadata = {}
        sock.settimeout(2.0)
        
        # 读取最多10行
        for _ in range(10):
            try:
                line = sock.recv(256).decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # 版本行: v <version>
                if line.startswith('v '):
                    metadata['version'] = line.split()[1]
                
                # 坐标范围行: ^ <max_contacts> <max_x> <max_y> <max_pressure>
                if line.startswith('^ '):
                    parts = line.split()
                    if len(parts) >= 4:
                        metadata['max_contacts'] = int(parts[1])
                        metadata['max_x'] = int(parts[2])
                        metadata['max_y'] = int(parts[3])
                        metadata['max_pressure'] = int(parts[4]) if len(parts) > 4 else 255
                        break
            except socket.timeout:
                break
        
        if 'max_x' not in metadata or 'max_y' not in metadata:
            raise RuntimeError("无法获取 MiniTouch 坐标范围")
        
        return metadata
    
    def _scale_coordinate(self, device_id: str, x: int, y: int) -> Tuple[int, int]:
        """将屏幕坐标转换为 MiniTouch 坐标"""
        info = self._device_screen_info[device_id]
        screen_w = info['width']
        screen_h = info['height']
        mt_max_x = info['max_x']
        mt_max_y = info['max_y']
        
        # 线性缩放
        scaled_x = int(x * mt_max_x / screen_w)
        scaled_y = int(y * mt_max_y / screen_h)
        
        # 边界保护
        scaled_x = max(0, min(scaled_x, mt_max_x))
        scaled_y = max(0, min(scaled_y, mt_max_y))
        
        return scaled_x, scaled_y
    
    def _send_minitouch_commands(self, device_id: str, commands: List[str]):
        """发送 MiniTouch 命令序列"""
        if device_id not in self._device_sockets:
            raise RuntimeError(f"设备 {device_id} 未连接，请先调用 connect()")
        
        sock = self._device_sockets[device_id]
        payload = ''.join(commands) + 'c\n'  # c=commit
        
        try:
            sock.sendall(payload.encode('utf-8'))
        except Exception as e:
            # 尝试重建连接
            logger.warning(f"Socket 发送失败，尝试重建: {e}")
            local_port = self._device_ports[device_id]
            sock.close()
            new_sock = self._connect_socket(local_port)
            self._device_sockets[device_id] = new_sock
            new_sock.sendall(payload.encode('utf-8'))
    
    # ========== 核心操作 API (无仿人延迟) ==========
    
    def tap(self, device_id: str, x: int, y: int, duration_ms: int = 50, pressure: int = 100):
        """
        精确点击操作（无随机延迟）
        
        :param device_id: 设备ID
        :param x: 屏幕X坐标 (像素)
        :param y: 屏幕Y坐标 (像素)
        :param duration_ms: 按压持续时间 (ms)，默认50ms
        :param pressure: 压力值 (0-255)
        """
        mt_x, mt_y = self._scale_coordinate(device_id, x, y)
        pressure = max(0, min(pressure, 255))
        
        commands = [
            f"d 0 {mt_x} {mt_y} {pressure}\n",  # 按下
            f"c\n",                             # 提交
            f"w {duration_ms}\n",               # 等待
            f"u 0\n"                            # 抬起 (自动提交)
        ]
        
        self._send_minitouch_commands(device_id, commands)
        logger.info(f"✓ 点击: ({x}, {y}) 持续 {duration_ms}ms [设备: {device_id}]")
    
    def swipe(self, device_id: str, start_x: int, start_y: int, end_x: int, end_y: int, 
              duration_ms: int = 200, steps: int = 10, pressure: int = 100):
        """
        精确滑动操作（无随机延迟，固定步进）
        
        :param device_id: 设备ID
        :param start_x: 起始X坐标
        :param start_y: 起始Y坐标
        :param end_x: 结束X坐标
        :param end_y: 结束Y坐标
        :param duration_ms: 滑动总时长 (ms)
        :param steps: 插值步数 (默认10步)
        :param pressure: 压力值
        """
        start_mt = self._scale_coordinate(device_id, start_x, start_y)
        end_mt = self._scale_coordinate(device_id, end_x, end_y)
        pressure = max(0, min(pressure, 255))
        
        commands = [
            f"d 0 {start_mt[0]} {start_mt[1]} {pressure}\n",
            "c\n"
        ]
        
        # 生成精确轨迹
        for i in range(1, steps + 1):
            ratio = i / steps
            cur_x = int(start_mt[0] + (end_mt[0] - start_mt[0]) * ratio)
            cur_y = int(start_mt[1] + (end_mt[1] - start_mt[1]) * ratio)
            commands.append(f"m 0 {cur_x} {cur_y} {pressure}\n")
            commands.append("c\n")
        
        commands.extend([
            f"u 0\n",
            "c\n"
        ])
        
        self._send_minitouch_commands(device_id, commands)
        logger.info(f"✓ 滑动: ({start_x},{start_y}) → ({end_x},{end_y}) [设备: {device_id}]")
    
    def multi_touch(self, device_id: str, points: List[Tuple[int, int, int]], 
                   duration_ms: int = 100, pressure: int = 100):
        """
        多点触控 (最多10点)
        
        :param device_id: 设备ID
        :param points: [(x, y, contact_id), ...] contact_id 范围 0-9
        :param duration_ms: 持续时间 (ms)
        :param pressure: 压力值
        """
        if len(points) > 10:
            raise ValueError("MiniTouch 最多支持 10 个触点")
        
        pressure = max(0, min(pressure, 255))
        commands = []
        
        # 按下所有点
        for x, y, contact_id in points:
            if not (0 <= contact_id <= 9):
                raise ValueError(f"contact_id 必须在 0-9 范围内: {contact_id}")
            mt_x, mt_y = self._scale_coordinate(device_id, x, y)
            commands.append(f"d {contact_id} {mt_x} {mt_y} {pressure}\n")
        
        commands.append("c\n")
        commands.append(f"w {duration_ms}\n")
        
        # 抬起所有点
        for _, _, contact_id in points:
            commands.append(f"u {contact_id}\n")
        commands.append("c\n")
        
        self._send_minitouch_commands(device_id, commands)
        logger.info(f"✓ 多点触控: {len(points)} 个触点 [设备: {device_id}]")
    
    def long_press(self, device_id: str, x: int, y: int, duration_ms: int = 1000, pressure: int = 100):
        """长按操作"""
        self.tap(device_id, x, y, duration_ms, pressure)
    
    def get_screen_size(self, device_id: str) -> Tuple[int, int]:
        """获取设备屏幕分辨率"""
        if device_id not in self._device_screen_info:
            raise RuntimeError(f"设备 {device_id} 未连接")
        info = self._device_screen_info[device_id]
        return info['width'], info['height']


# ==================== 使用示例 ====================
def example_usage():
    """使用示例"""
    controller = MiniTouchController()
    
    # 1. 列出设备
    devices = controller.list_devices()
    if not devices:
        logger.error("❌ 无可用设备")
        return
    
    # 2. 连接第一个设备 (自动处理 Android 10+ 限制)
    device_id = devices[0].id
    try:
        controller.connect(device_id)
        
        # 3. 获取屏幕尺寸
        width, height = controller.get_screen_size(device_id)
        logger.info(f"📱 屏幕: {width}x{height}")
        
        # 4. 执行精确操作 (无随机延迟)
        # 点击屏幕中央 (50ms 精确按压)
        controller.tap(device_id, width // 2, height // 2, duration_ms=50)
        
        # 向上滑动 (200ms 精确滑动，10步插值)
        controller.swipe(
            device_id,
            start_x=width // 2,
            start_y=int(height * 0.8),
            end_x=width // 2,
            end_y=int(height * 0.2),
            duration_ms=200,
            steps=10
        )
        
        # 双指缩放 (100ms 精确多点)
        controller.multi_touch(
            device_id,
            points=[
                (width // 3, height // 2, 0),   # 左指
                (width * 2 // 3, height // 2, 1)  # 右指
            ],
            duration_ms=100
        )
        
        logger.info("✅ 所有操作执行完毕")
        
    except Exception as e:
        logger.error(f"❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 5. 断开连接
        controller.disconnect(device_id)


if __name__ == "__main__":
    example_usage()
#!/usr/bin/env python3
"""
使用 9b 模型执行每日任务标准流
设备：192.168.1.12:16512
记录过程画面影像
"""
import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 设置路径
from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

PROJECT_ROOT = PROJECT_ROOT
SRC_DIR = SRC_DIR
MODELS_DIR = PROJECT_ROOT / "models"

# 9b 模型路径
MODEL_9B_PATH = PROJECT_ROOT / "models" / "unsloth" / "Qwen3___5-9B-GGUF" / "Qwen3.5-9B-Q8_0.gguf"
if not MODEL_9B_PATH.exists():
    # 尝试父目录
    MODEL_9B_PATH = PROJECT_ROOT.parent / "models" / "unsloth" / "Qwen3___5-9B-GGUF" / "Qwen3.5-9B-Q8_0.gguf"

DEVICE_SERIAL = "192.168.1.12:16512"
FLOW_NAME = "daily_quest"
LLAMA_SERVER_PORT = 8080

def find_llama_server():
    """查找 llama-server 可执行文件"""
    candidates = [
        PROJECT_ROOT / "3rd-party" / "llama-cpp" / "llama-server.exe",
        PROJECT_ROOT / "3rd-party" / "llama-server" / "llama-server.exe",
        Path("C:/Users/xray/Desktop/workflow/llamacpp/llamacpp-cuda124/llama-server.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "llama-server"

def check_server_running(port):
    """检查服务器是否已运行"""
    import urllib.request
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3)
        return req.status == 200
    except:
        return False

def start_llama_server(model_path, port):
    """启动 llama-server"""
    server_exe = find_llama_server()
    
    # 计算 GPU 层数
    try:
        r = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.free,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10
        )
        parts = r.stdout.strip().split(',')
        free_mib = int(parts[0].strip())
        free_gb = free_mib / 1024
        # 9b 模型需要更多层，预留 3GB 给游戏
        available = max(0, free_gb - 3.0)
        if available >= 8:
            gpu_layers = 99
        elif available >= 6:
            gpu_layers = 80
        else:
            gpu_layers = 50
        print(f"[GPU] 可用显存：{free_gb:.1f}GB，设置 n-gpu-layers={gpu_layers}")
    except:
        gpu_layers = 99
        print(f"[GPU] 无法获取显存信息，使用默认 n-gpu-layers={gpu_layers}")
    
    cmd = [
        server_exe,
        "--model", str(model_path),
        "--port", str(port),
        "--host", "127.0.0.1",
        "--ctx-size", "8192",
        "--n-gpu-layers", str(gpu_layers),
        "--parallel", "1",
        "--no-webui",
    ]
    
    # 检查 mmproj
    mmproj = model_path.parent / "mmproj-F16.gguf"
    if mmproj.exists():
        cmd += ["--mmproj", str(mmproj)]
        print(f"[MMProj] 找到视觉编码器：{mmproj}")
    
    print(f"[Server] 启动命令：{' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    
    # 等待服务器就绪
    for i in range(60):
        time.sleep(1)
        if check_server_running(port):
            print(f"[Server] llama-server 已就绪 (port {port})")
            return process
        if process.poll() is not None:
            _, stderr = process.communicate()
            print(f"[Server] 启动失败：{stderr.decode('utf-8', errors='replace')[:500]}")
            return None
        if (i + 1) % 10 == 0:
            print(f"[Server] 等待服务器启动... ({i+1}/60)")
    
    print("[Server] 启动超时")
    return None

def kill_existing_server(port):
    """杀死已运行的服务器"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # 通过命令行参数查找
                if 'llama-server' in proc.info.get('name', ''):
                    # 尝试连接检查
                    pass
            except:
                pass
    except:
        pass
    # 简单方法：尝试通过 curl 检查，然后 kill
    # 这里简化处理，让用户手动关闭

def main():
    print("=" * 70)
    print(" " * 20 + "9B 模型标准流执行")
    print("=" * 70)
    print(f"流程：{FLOW_NAME}")
    print(f"设备：{DEVICE_SERIAL}")
    print(f"模型：{MODEL_9B_PATH}")
    print(f"记录：是")
    print("=" * 70)
    
    # 检查模型文件
    if not MODEL_9B_PATH.exists():
        print(f"[ERROR] 模型文件不存在：{MODEL_9B_PATH}")
        return 1
    
    print(f"[模型] 找到 9B 模型：{MODEL_9B_PATH}")
    print(f"[大小] {MODEL_9B_PATH.stat().st_size / 1024**3:.2f} GB")
    
    # 检查服务器状态
    if check_server_running(LLAMA_SERVER_PORT):
        print(f"[Server] 检测到已有服务器运行在端口 {LLAMA_SERVER_PORT}")
        resp = input("是否继续使用该服务器？(y/N): ")
        if resp.lower() != 'y':
            print("[提示] 请手动关闭现有服务器后重试")
            return 1
    else:
        # 启动服务器
        print("[Server] 启动 llama-server...")
        server_process = start_llama_server(MODEL_9B_PATH, LLAMA_SERVER_PORT)
        if not server_process:
            print("[ERROR] 服务器启动失败")
            return 1
    
    # 执行标准流
    print("\n" + "=" * 70)
    print("开始执行标准流...")
    print("=" * 70)
    
    # 调用标准流引擎
    from standard_flow_engine import FlowConfig, FlowRecorder, FlowExecutor, Local2BEngine
    
    # 配置
    config = FlowConfig()
    exec_config = config.execution_config
    
    # 记录器
    session_name = f"{FLOW_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    recorder = FlowRecorder(
        session_name=session_name,
        record_video=True,
        device_serial=DEVICE_SERIAL
    )
    print(f"[记录] 会话目录：{recorder.session_dir}")
    
    # 引擎 - 使用已运行的服务器
    engine = Local2BEngine()
    # 强制使用本地模式
    engine._server_process = True
    engine._loaded = True
    engine._using_api = False
    engine._model_name = "qwen3.5-9b-q8_0"
    engine._model_path = str(MODEL_9B_PATH)
    print(f"[引擎] 使用 9B 本地模型")
    
    # 执行器
    executor = FlowExecutor(config, engine, recorder, device_serial=DEVICE_SERIAL)
    
    # 执行流程
    success = executor.execute_flow(FLOW_NAME)
    
    # 导出报告
    report = recorder.export_report()
    report_path = recorder.session_dir / "execution_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[报告] 已保存：{report_path}")
    
    print("\n" + "=" * 70)
    if success:
        print("标准流执行完成 - 成功")
    else:
        print("标准流执行完成 - 有失败步骤")
    print("=" * 70)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

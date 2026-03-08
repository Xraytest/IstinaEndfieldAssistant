"""
测试客户端命令帮助 - 快速测试脚本
此脚本用于快速测试各种客户端命令的功能
"""
import os
import sys
import json
import base64
import time

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from communicator import ClientCommunicator
from logger import init_logger, get_logger, LogCategory

# 初始化日志
log_config_path = os.path.join(os.path.dirname(__file__), "config", "logging_config.json")
init_logger(log_config_path)
logger = get_logger()

# 默认配置
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999
PASSWORD = "default_password"


def print_divider():
    """打印分隔线"""
    print("\n" + "=" * 80 + "\n")


def test_register(user_id):
    """测试注册功能"""
    print_divider()
    print("🧪 测试注册功能")
    print(f"  用户ID: {user_id}")

    communicator = ClientCommunicator(SERVER_HOST, SERVER_PORT, PASSWORD, timeout=10)

    request_data = {"user_id": user_id}
    response = communicator.send_request("register", request_data)

    if response and response.get("status") == "success":
        print(f"  ✅ 注册成功！")
        print(f"  API密钥: {response.get('key')}")
        return response.get("key")
    else:
        print(f"  ❌ 注册失败: {response.get('message', '未知错误')}")
        return None


def test_login(user_id, api_key):
    """测试登录功能"""
    print_divider()
    print("🧪 测试登录功能")
    print(f"  用户ID: {user_id}")

    communicator = ClientCommunicator(SERVER_HOST, SERVER_PORT, PASSWORD, timeout=10)

    request_data = {"user_id": user_id, "key": api_key}
    response = communicator.send_request("login", request_data)

    if response and response.get("status") == "success":
        session_id = response.get("session_id")
        print(f"  ✅ 登录成功！")
        print(f"  Session ID: {session_id[:20]}...")
        communicator.set_logged_in(True)
        return communicator, session_id
    else:
        print(f"  ❌ 登录失败: {response.get('message', '未知错误')}")
        return None, None


def test_get_tasks(communicator):
    """测试获取任务列表"""
    print_divider()
    print("🧪 测试获取任务列表")

    response = communicator.send_request("get_default_tasks", {})

    if response and response.get("status") == "success":
        tasks = response.get("tasks", [])
        print(f"  ✅ 获取成功！共 {len(tasks)} 个任务")
        for task in tasks[:5]:  # 只显示前5个
            print(f"    - {task.get('id')}: {task.get('name')}")
        if len(tasks) > 5:
            print(f"    ... 还有 {len(tasks) - 5} 个任务")
        return tasks
    else:
        print(f"  ❌ 获取失败: {response.get('message', '未知错误')}")
        return []


def test_get_task_definition(communicator, task_id):
    """测试获取单个任务定义"""
    print_divider()
    print(f"🧪 测试获取任务定义: {task_id}")

    request_data = {"task_id": task_id}
    response = communicator.send_request("get_task_definition", request_data)

    if response and response.get("status") == "success":
        task = response.get("task", {})
        print(f"  ✅ 获取成功！")
        print(f"  任务名称: {task.get('name')}")
        print(f"  变量数量: {len(task.get('variables', []))}")
        for var in task.get("variables", [])[:3]:
            print(f"    - {var.get('name')}: {var.get('type')} (默认值: {var.get('default')})")
        return task
    else:
        print(f"  ❌ 获取失败: {response.get('message', '未知错误')}")
        return None


def test_get_user_info(communicator, user_id, session_id):
    """测试获取用户信息"""
    print_divider()
    print("🧪 测试获取用户信息")

    request_data = {"user_id": user_id, "session_id": session_id}
    response = communicator.send_request("get_user_info", request_data)

    if response and response.get("status") == "success":
        user_info = response.get("user_info", {})
        print(f"  ✅ 获取成功！")
        print(f"  用户层级: {user_info.get('tier', 'unknown')}")
        print(f"  配额使用: {user_info.get('quota', {}).get('daily_used', 0)}/{user_info.get('quota', {}).get('daily_limit', 0)}")
        print(f"  Token使用量: {user_info.get('token_usage', 0)}")
        return user_info
    else:
        print(f"  ❌ 获取失败: {response.get('message', '未知错误')}")
        return None


def test_check_version():
    """测试检查版本"""
    print_divider()
    print("🧪 测试检查版本")

    communicator = ClientCommunicator(SERVER_HOST, SERVER_PORT, PASSWORD, timeout=10)

    response = communicator.send_request("check_version", {})

    if response and response.get("status") == "success":
        version = response.get("data", {}).get("version", "unknown")
        print(f"  ✅ 检查成功！")
        print(f"  最新版本: {version}")
        return version
    else:
        print(f"  ❌ 检查失败: {response.get('message', '未知错误')}")
        return None


def main():
    """主测试函数"""
    print("=" * 80)
    print("🧪 测试客户端命令帮助 - 快速测试脚本")
    print("=" * 80)
    print(f"\n🔧 服务器配置:")
    print(f"   地址: {SERVER_HOST}:{SERVER_PORT}")
    print(f"   密码: {PASSWORD}")

    # 测试1: 注册
    test_user_id = f"test_user_{int(time.time())}"
    api_key = test_register(test_user_id)

    if not api_key:
        print("\n⚠️  注册失败，停止测试")
        return

    # 等待1秒
    time.sleep(1)

    # 测试2: 登录
    communicator, session_id = test_login(test_user_id, api_key)

    if not communicator:
        print("\n⚠️  登录失败，停止测试")
        return

    # 等待1秒
    time.sleep(1)

    # 测试3: 获取任务列表
    tasks = test_get_tasks(communicator)

    # 测试4: 获取任务定义（如果存在任务）
    if tasks:
        test_get_task_definition(communicator, tasks[0].get("id"))

    # 等待1秒
    time.sleep(1)

    # 测试5: 获取用户信息
    test_get_user_info(communicator, test_user_id, session_id)

    # 测试6: 检查版本
    test_check_version()

    print_divider()
    print("✅ 测试完成！")
    print("=" * 80)
    print("\n📝 提示:")
    print("  - 更多详细信息请查看 command_help.md")
    print("  - 要测试 process_image 命令，请使用客户端主程序")
    print("  - 检查日志文件以获取更多调试信息")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试发生异常: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
"""
诊断供应商响应问题
"""

import sys
import os
import json
import time
import requests

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_provider_directly():
    """直接测试BigModel API"""
    print("=== 直接测试BigModel API ===")

    # 从数据库获取BigModel配置
    try:
        from cloud.admin_gui import DBManager
        db = DBManager("cloud/system_data.db")

        cur = db.conn.cursor()
        cur.execute("""
            SELECT endpoint, api_key, model_name, api_format
            FROM providers
            WHERE name='BigModel' AND is_active=1
        """)
        result = cur.fetchone()
        db.conn.close()

        if not result:
            print("[X] 未找到BigModel供应商配置")
            return False

        endpoint, api_key, model_name, api_format = result
        print(f"配置信息:")
        print(f"  - 端点: {endpoint}")
        print(f"  - 模型: {model_name}")
        print(f"  - 格式: {api_format}")
        print(f"  - 密钥: {'已配置' if api_key else '未配置'}")

        if not api_key:
            print("[X] API密钥未配置，无法测试")
            print("\n解决方案:")
            print("1. 在管理GUI中编辑BigModel供应商")
            print("2. 填入有效的智谱AI API密钥")
            print("3. 保存后重新测试")
            return False

        # 构建测试请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ArkStudio-Test/1.0"
        }

        # Z-AI格式请求
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "你好，请说一句话"}
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }

        print(f"\n发送测试请求...")
        print(f"请求URL: {endpoint}")
        print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30,
            verify=False
        )

        print(f"\n📥 响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 请求成功")
            print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")

            # 检查响应格式
            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if content:
                    print(f"\n[SUCCESS] 获得有效回复: {content}")
                    return True
                else:
                    print("\n[WARNING] 响应中content字段为空")
                    print("可能原因:")
                    print("1. API配额已用完")
                    print("2. 模型配置问题")
                    print("3. 请求参数不正确")
                    return False
            else:
                print("\n[WARNING] 响应中没有choices字段")
                return False
        else:
            print(f"[ERROR] 请求失败: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cloud_with_debug():
    """通过云服务测试并查看详细日志"""
    print("\n\n=== 通过云服务测试（调试模式）===")

    try:
        from utils.tcp_client import CloudClient

        client = CloudClient()

        # 使用测试用户登录
        if os.path.exists("test_user.arkpass"):
            success, result = client.login_with_file("test_user.arkpass")
            if success:
                print(f"[OK] 登录成功: {result}")

                # 发送测试消息
                payload = {
                    "model": "glm-5",  # 使用Z-AI格式默认模型
                    "messages": [{"role": "user", "content": "测试"}],
                    "max_tokens": 20
                }

                print(f"\n通过云服务发送测试请求...")
                response = client.chat_completion(payload)

                print(f"云服务响应: {json.dumps(response, ensure_ascii=False, indent=2)}")

                if response.get("status") == "success":
                    result = response.get("result", "")
                    if result:
                        print(f"[SUCCESS] 获得有效回复: {result}")
                    else:
                        print("\n[WARNING] 云服务返回空结果")
                        print("调试信息:")
                        print(f"- 供应商: {response.get('provider')}")
                        print(f"- Token使用: {response.get('usage')}")
                        print(f"- 完成原因: {response.get('finish_reason')}")
                else:
                    print(f"[ERROR] 云服务返回错误: {response.get('msg')}")
            else:
                print(f"[ERROR] 登录失败: {result}")
        else:
            print("[ERROR] 未找到测试用户文件，请先运行 test_cloud_api.py 进行注册")

    except Exception as e:
        print(f"[ERROR] 云服务测试异常: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("开始诊断供应商响应问题...")
    print("="*60)

    # 1. 直接测试供应商API
    direct_success = test_provider_directly()

    # 2. 通过云服务测试
    test_cloud_with_debug()

    # 3. 提供解决方案
    print("\n\n" + "="*60)
    print("\n解决方案建议:")

    if not direct_success:
        print("\n1. 配置问题（最常见）:")
        print("   - 启动管理GUI: python cloud/admin_gui.py")
        print("   - 转到'供应商管理'标签")
        print("   - 双击'BigModel'供应商")
        print("   - 填入有效的智谱AI API密钥")
        print("   - 确认API格式设置为'z-ai'")
        print("   - 保存更改")

    print("\n2. API密钥获取:")
    print("   - 访问: https://open.bigmodel.cn/")
    print("   - 注册/登录智谱AI平台")
    print("   - 获取API Key")
    print("   - 充值或使用免费额度")

    print("\n3. 检查使用情况:")
    print("   - 登录智谱AI控制台")
    print("   - 查看API余额和使用量")
    print("   - 确认未超出限制")

    print("\n4. 测试步骤:")
    print("   - 配置好API密钥后，重新运行: python test_cloud_api.py")
    print("   - 或使用本脚本: python test_provider_debug.py")

    if direct_success:
        print("\n[INFO] 直接API测试成功，问题可能在云服务配置")
        print("建议检查云服务的请求转发逻辑")
    else:
        print("\n[WARNING] 直接API测试失败，请先解决API配置问题")

if __name__ == "__main__":
    main()
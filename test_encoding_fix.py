#!/usr/bin/env python3
"""
修复API请求编码问题的测试脚本
"""

import sys
import os
import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_provider_fixed():
    """使用修复后的编码测试"""
    print("=== 测试修复后的API请求 ===")

    try:
        from cloud.admin_gui import DBManager
        db = DBManager("cloud/system_data.db")

        # 获取配置
        cur = db.conn.cursor()
        cur.execute("""
            SELECT endpoint, api_key, model_name, api_format
            FROM providers
            WHERE name='BigModel' AND is_active=1
        """)
        result = cur.fetchone()
        db.conn.close()

        if not result:
            print("[ERROR] BigModel配置未找到")
            return False

        endpoint, api_key, model_name, api_format = result

        # 修复方案1：使用ASCII内容
        print("\n1. 使用英文内容测试...")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Charset": "UTF-8"
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hello, please say something"}
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }

        # 手动编码JSON，确保UTF-8
        json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        response = requests.post(
            endpoint,
            headers=headers,
            data=json_data,
            timeout=30,
            verify=False
        )

        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            choices = result.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    print(f"[SUCCESS] 英文测试成功: {content}")

                    # 修复方案2：正确处理中文
                    print("\n2. 测试中文内容（修复编码）...")

                    payload_utf8 = {
                        "model": model_name,
                        "messages": [
                            {"role": "user", "content": "你好请说话"}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 50
                    }

                    # 确保JSON正确编码
                    json_data_utf8 = json.dumps(payload_utf8, ensure_ascii=False).encode('utf-8')

                    response2 = requests.post(
                        endpoint,
                        headers=headers,
                        data=json_data_utf8,
                        timeout=30,
                        verify=False
                    )

                    print(f"状态码: {response2.status_code}")
                    if response2.status_code == 200:
                        result2 = response2.json()
                        choices2 = result2.get("choices", [])
                        if choices2:
                            content2 = choices2[0].get("message", {}).get("content", "")
                            if content2:
                                print(f"[SUCCESS] 中文测试成功: {content2}")
                                return True

                    print(f"中文测试失败: {response2.text}")
                else:
                    print("[WARNING] 英文测试返回空内容")
            else:
                print("[WARNING] 英文测试响应格式异常")

        print(f"英文测试失败: {response.text}")

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()

    return False

def show_fix_guide():
    """显示修复指南"""
    print("\n" + "="*60)
    print("修复指南")
    print("="*60)

    print("\n🔧 核心问题：")
    print("API请求中的中文UTF-8编码错误")

    print("\n✅ 解决方案1（推荐）：")
    print("修改 admin_gui.py 中的 APIClient._call_z_ai_provider 方法")
    print("将 requests.post 的 json 参数改为 data 参数，手动编码")

    print("\n修复代码示例：")
    print("""
    # 原代码（有问题）：
    response = requests.post(endpoint, headers=headers, json=payload, ...)

    # 修复后：
    json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    response = requests.post(endpoint, headers=headers, data=json_data, ...)
    """)

    print("\n✅ 解决方案2（临时）：")
    print("1. 使用英文内容进行测试")
    print("2. 或者使用 URL 编码处理中文")

    print("\n📝 下一步操作：")
    print("1. 备份 cloud/admin_gui.py")
    print("2.修复编码问题")
    print("3. 重新测试")

def main():
    print("编码问题修复测试")
    print("="*60)

    # 测试修复后的请求
    success = test_provider_fixed()

    if not success:
        show_fix_guide()
    else:
        print("\n[SUCCESS] 修复测试成功")
        print("请按照修复指南更新 admin_gui.py")

if __name__ == "__main__":
    main()
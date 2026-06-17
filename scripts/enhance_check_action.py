#!/usr/bin/env python3
"""
增强 check 动作，集成 OCR 管理器
"""

file_path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到并替换 check 动作的实现
old_check = '''            # === check: 高精度页面分析（使用新分析器）===
            elif step_action == "check":
                img_bytes = adb_screencap()
                if img_bytes:
                    import numpy as np
                    import cv2
                    np_img = np.frombuffer(img_bytes, dtype=np.uint8)
                    cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                    if cv_img is not None:
                        result = self.page_analyzer.analyze(cv_img)
                        page_type = result["page_type"]
                        confidence = result["confidence"]
                        features = result["features"]
                        print(f"  [CHECK] 页面={page_type} 置信度={confidence:.2f} "
                              f"left_bar={features.get('left_bar_brightness', 0):.0f} "
                              f"green={features.get('green_pixels_top_right', 0):.0f}")

                        # 检查 expect 字段
                        expected = step_cfg.get("expect")
                        if expected:
                            if page_type == expected or (expected == "world" and page_type in ("world", "world_transition")):
                                print(f"  [OK] 页面匹配预期：{expected}")
                                success = True
                            else:
                                print(f"  [WARN] 页面不匹配预期：期望={expected} 实际={page_type}")
                                success = False
                        else:
                            success = True
                    else:
                        success = False
                else:
                    success = False'''

new_check = '''            # === check: 高精度页面分析（使用新分析器 + OCR）===
            elif step_action == "check":
                success = False
                page_type = "unknown"
                
                # 优先使用 OCR 管理器（如果已启用）
                if self.ocr_manager:
                    try:
                        print(f"  [CHECK] 使用 OCR 管理器检测页面...")
                        state = self.ocr_manager.capture_and_recognize(self.device_serial)
                        page_type = state.page_type
                        print(f"  [CHECK] 页面={page_type} 描述={state.description}")
                        
                        # 检查 expect 字段
                        expected = step_cfg.get("expect")
                        if expected:
                            if page_type == expected or (expected == "world" and page_type in ("world", "world_transition", "world_map")):
                                print(f"  [OK] 页面匹配预期：{expected}")
                                success = True
                            else:
                                print(f"  [WARN] 页面不匹配预期：期望={expected} 实际={page_type}")
                                success = False
                        else:
                            # 无 expect，只要成功获取页面类型就成功
                            if page_type not in ("error", "unknown"):
                                success = True
                    except Exception as e:
                        print(f"  [WARN] OCR 检测失败：{e}，降级到页面分析器")
                
                # 降级：使用页面分析器
                if not success:
                    img_bytes = adb_screencap()
                    if img_bytes:
                        import numpy as np
                        import cv2
                        np_img = np.frombuffer(img_bytes, dtype=np.uint8)
                        cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                        if cv_img is not None:
                            result = self.page_analyzer.analyze(cv_img)
                            page_type = result["page_type"]
                            confidence = result["confidence"]
                            features = result["features"]
                            print(f"  [CHECK] 页面={page_type} 置信度={confidence:.2f} "
                                  f"left_bar={features.get('left_bar_brightness', 0):.0f} "
                                  f"green={features.get('green_pixels_top_right', 0):.0f}")

                            # 检查 expect 字段
                            expected = step_cfg.get("expect")
                            if expected:
                                if page_type == expected or (expected == "world" and page_type in ("world", "world_transition")):
                                    print(f"  [OK] 页面匹配预期：{expected}")
                                    success = True
                                else:
                                    print(f"  [WARN] 页面不匹配预期：期望={expected} 实际={page_type}")
                                    success = False
                            else:
                                success = True
                        else:
                            print(f"  [FAIL] 截图解码失败")
                    else:
                        print(f"  [FAIL] 截图失败")
                else:
                    print(f"  [OK] check 完成")'''

if old_check in content:
    content = content.replace(old_check, new_check)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] check 动作增强完成!")
else:
    print("[FAIL] 未找到 check 动作代码块")
    print("尝试查找类似内容...")
    if "elif step_action == \"check\":" in content:
        print("找到 check 动作，但内容不匹配")

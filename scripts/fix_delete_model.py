#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复 settings_page.py 中的_delete_model 方法，移除硬编码"""

import os

file_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'src', 'gui', 'pyqt6', 'pages', 'settings_page.py'
)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 新的_delete_model 方法
new_delete_model = '''    def _delete_model(self):
        """删除本地模型文件（配置驱动，动态匹配）"""
        from PyQt6.QtWidgets import QMessageBox

        model_id = self._model_select_combo.currentData()
        if not model_id:
            return
        
        # 从配置文件查找模型定义
        models_config = self._load_models_config()
        model_cfg = None
        for cfg in models_config:
            if cfg.get("repo_id") == model_id:
                model_cfg = cfg
                break
        
        if not model_cfg:
            QMessageBox.warning(self, "配置错误", f"未找到模型配置：{model_id}")
            return
        
        models_dir = self._get_models_dir()
        
        # 使用正则模式匹配本地已下载的文件
        matched_gguf, matched_mmproj = self._match_local_files(models_dir, model_cfg)
        
        # 构建要删除的文件列表
        files_to_delete = []
        if matched_gguf:
            files_to_delete.append((matched_gguf, os.path.join(models_dir, matched_gguf)))
        if matched_mmproj:
            files_to_delete.append((matched_mmproj, os.path.join(models_dir, matched_mmproj)))
        
        if not files_to_delete:
            QMessageBox.warning(self, "无本地文件", "该模型未下载，无法删除。")
            return
        
        # 显示确认对话框
        files_list = "\\n".join([f"  {name}" for name, _ in files_to_delete])
        reply = QMessageBox.question(
            self, "确认删除",
            f"删除以下 {len(files_to_delete)} 个文件？\\n\\n{files_list}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行删除
        errors = []
        for name, path in files_to_delete:
            try:
                os.remove(path)
            except Exception as e:
                errors.append(f"{name}: {e}")
        
        if errors:
            QMessageBox.critical(self, "删除失败", "\\n".join(errors))
        else:
            self._download_status_label.setText(f"Deleted {len(files_to_delete)} file(s)")
        
        self._scan_local_models()
'''

# 使用正则表达式找到并替换_delete_model 方法
import re

# 匹配从 def _delete_model 到下一个 def 方法
pattern = r'    def _delete_model\(self\):.*?(?=\n    def \w+)'

def replace_method(match):
    return new_delete_model + '\n'

content = re.sub(pattern, replace_method, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: _delete_model method updated")

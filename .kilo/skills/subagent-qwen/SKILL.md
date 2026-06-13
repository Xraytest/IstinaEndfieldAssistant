---
name: subagent-qwen
description: 将复杂任务分析委托给远程 Qwen 大模型的 subagent 机制。遵循 kilo code 子智能体模式：提供丰富上下文 → 请求模型分析 → 模型可请求更多信息 → 返回结构化分析结果。
trigger: 当需要深度分析、多步推理、图像理解或专业知识判断时，优先调用此技能。
---

# SubAgent Qwen — 远程大模型分析委托技能

## 概述

将复杂分析任务委托给 Qwen 大模型端点，遵循 **kilo code 子智能体模式**：

1. **信息注入** — 提供完整上下文（代码、截图、日志、配置）
2. **模型推理** — Qwen 模型逐步分析、给出诊断和方案
3. **信息请求** — 模型可主动请求更多信息
4. **行动输出** — 返回结构化分析结果

## 端点

| 端点 | URL | 认证 | 状态 |
|------|-----|------|------|
| **Cherryin.ai** | `https://open.cherryin.cc/v1` | `Bearer sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst` | **唯一端点** |

## 模型

| 模型名称 | 端点 | 用途 |
|----------|------|------|
| `qwen/qwen3.5-27b(free)` | Cherryin.ai | **唯一模型**，文本+视觉通用 |

## 触发条件

此技能在以下场景应优先被调用（代替自己硬解）：

- **游戏自动化调试**：分析 VLM 返回值、截图、执行日志，诊断为什么操作失败
- **长代码审查**：500+ 行的关键脚本需要全面分析（如 `explore_and_dailies.py`）
- **多因素问题诊断**：涉及 ADB、TCP 通信、VLM 分析、UI 布局等的复合问题
- **图像/UI 分析**：需要理解游戏截图中的 UI 布局和可交互元素
- **策略规划**：需要制定多步执行计划、重写复杂逻辑

## SubAgent 协议

### 调用格式

```json
{
  "model": "qwen/qwen3.5-27b(free)",
  "messages": [
    {
      "role": "system",
      "content": "<系统提示词>"
    },
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "<分析任务描述 + 上下文>"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,<base64>"}}
      ]
    }
  ],
  "temperature": 0.3,
  "max_tokens": 8192
}
```

### 系统提示词模板

```
你是 SubAgent Qwen — 一个深度分析子智能体。你的任务是对提供的上下文进行彻底分析。

## 分析流程
1. 首先理解任务目标
2. 分析提供的所有上下文信息（代码、截图、日志、配置）
3. 逐步推理问题根因
4. 给出具体的解决方案或下一步行动建议
5. 如果信息不足，明确说明还需要什么信息

## 输出格式
请以结构化方式输出：
### 问题理解
[你对该问题的理解]

### 上下文分析
[对提供的代码/截图/日志的分析]

### 根因诊断
[问题根因]

### 解决方案
[具体的解决步骤]

### 信息需求
[如果需要更多信息才能确定，列出还需要什么]
```

### 上下文注入模板

```
## 任务
{任务描述}

## 相关代码
```python
{关键代码段}
```

## 执行日志（最近）
```
{最近日志行}
```

## 截图
[以 base64 图像形式附上]

## 已知信息
- 设备: {设备信息}
- 分辨率: {分辨率}
- 服务器: {服务器信息}
- 已尝试方案: {已尝试过的方案}
- 当前状态: {当前程序状态}
```

## 工作流程

1. 我判断任务需要 Qwen 分析 → 调用此技能
2. 技能收集当前上下文（代码、截图、日志、执行状态）
3. 技能构建 HTTP 请求发送到 `https://open.cherryin.cc/v1/chat/completions`
4. 技能使用 Cherryin.ai API Key 进行 Bearer 认证
5. `qwen/qwen3.5-27b(free)` 模型返回结构化分析
6. 技能解析并呈现分析结果
7. Qwen 如需更多信息 → 我获取后再发送一轮

## HTTP 请求细节

- **端点**: `POST https://open.cherryin.cc/v1/chat/completions`
- **认证**: `Authorization: Bearer sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst`
- **超时**: 180 秒
- **模型**: `qwen/qwen3.5-27b(free)`

```python
import base64, requests

API_URL = "https://open.cherryin.cc/v1/chat/completions"
API_KEY = "sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst"

resp = requests.post(API_URL, headers={
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}, json={
    "model": "qwen/qwen3.5-27b(free)",
    "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        {"type": "text", "text": "描述画面内容"},
    ]}],
    "max_tokens": 4096,
}, timeout=180)
```

## Python 客户端用法

```python
from subagent_client import SubAgentQwen

agent = SubAgentQwen()
result = agent.analyze(task="分析这个游戏截图中的UI元素")
# result: {"success": bool, "model": str, "analysis": str, "error": str | None, ...}
```

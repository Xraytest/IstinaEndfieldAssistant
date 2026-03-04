# 测试客户端命令用法说明

## 概述
本测试客户端用于与服务端进行通信调试。所有命令都通过TCP协议与服务端交互，使用加密传输。

## 连接配置

### 默认配置
- 服务端地址: `127.0.0.1`
- 服务端端口: `9999`
- 通信密码: `default_password`
- 超时时间: `300秒` (5分钟，支持长时间的LLM处理)

### 自定义配置
编辑 `config/client_config.json` 文件修改连接配置：

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 9999
  },
  "communication": {
    "password": "your_password"
  }
}
```

## 命令列表

### 1. 用户认证类命令

#### 注册用户 (register)
**用途**: 创建新用户账户并获取API密钥

**请求数据**:
```json
{
  "user_id": "your_username"
}
```

**响应数据**:
```json
{
  "status": "success",
  "key": "generated_api_key"
}
```

**使用场景**:
- 首次使用系统时
- 需要创建新用户时

---

#### 登录 (login)
**用途**: 验证用户身份并获取会话令牌

**请求数据**:
```json
{
  "user_id": "your_username",
  "key": "your_api_key"
}
```

**响应数据**:
```json
{
  "status": "success",
  "session_id": "session_token"
}
```

**使用场景**:
- 启动客户端时自动执行
- 会话过期后重新登录

---

### 2. 任务管理类命令

#### 获取任务列表 (get_default_tasks)
**用途**: 获取所有可用的任务模板

**请求数据**: 空对象 `{}`

**响应数据**:
```json
{
  "status": "success",
  "tasks": [
    {
      "id": "task_id_1",
      "name": "任务名称",
      "description": "任务描述",
      "variables": [
        {
          "name": "变量名",
          "type": "string|number|boolean",
          "default": "默认值",
          "required": true|false
        }
      ]
    }
  ]
}
```

**使用场景**:
- 客户端启动时加载任务列表
- 查看可用任务模板

---

#### 获取单个任务定义 (get_task_definition)
**用途**: 获取指定任务的详细定义和变量配置

**请求数据**:
```json
{
  "task_id": "task_id_1"
}
```

**响应数据**:
```json
{
  "status": "success",
  "task": {
    "id": "task_id_1",
    "name": "任务名称",
    "variables": [...],
    "updated_at": "timestamp"
  }
}
```

**使用场景**:
- 同步任务的最新变量定义
- 获取任务的默认值配置

---

#### 批量同步任务定义 (sync_all_tasks_definitions)
**用途**: 批量获取多个任务的最新定义

**请求数据**:
```json
{
  "task_ids": ["task_id_1", "task_id_2", "task_id_3"]
}
```

**响应数据**:
```json
{
  "status": "success",
  "tasks": {
    "task_id_1": {
      "id": "task_id_1",
      "name": "任务名称",
      "variables": [...],
      "updated_at": "timestamp"
    },
    ...
  }
}
```

**使用场景**:
- 批量更新任务队列中的任务定义
- 验证多个任务的最新配置

---

### 3. 图像处理类命令

#### 处理图像 (process_image)
**用途**: 核心命令，用于发送屏幕截图和任务信息，接收触控指令

**请求数据**:
```json
{
  "user_id": "your_username",
  "session_id": "session_token",
  "device_image": "base64_encoded_image_data",
  "current_task": "task_id",
  "task_variables": {
    "custom_var_1": "value1",
    "custom_var_2": "value2"
  },
  "device_info": {
    "resolution": [1080, 1920],
    "model": "Pixel 6",
    "image_size": [540, 960]
  },
  "auxiliary_info": [
    {
      "name": "template_name",
      "confidence": 0.95,
      "bounding_box": [x1, y1, x2, y2]
    }
  ]
}
```

**响应数据**:
```json
{
  "status": "success",
  "data": {
    "touch_actions": [
      {
        "action": "click|swipe|long_press|drag",
        "parameters": {
          "coordinates": [x, y],
          "end_coordinates": [x, y],
          "duration": 1000
        }
      }
    ],
    "task_completed": true|false,
    "token_usage": 1234
  }
}
```

**使用场景**:
- 自动化执行任务时的主循环
- 每次捕获屏幕后发送请求

**注意**:
- `device_image` 必须是Base64编码的图像数据
- `task_variables` 必须符合任务定义中的变量要求
- 如果遇到供应商限流（429错误），会返回 `provider_rate_limited` 状态

---

#### 处理排队请求 (process_queued_request)
**用途**: 处理之前因供应商限流而排队的请求

**请求数据**:
```json
{
  "user_id": "your_username"
}
```

**响应数据**: 同 `process_image` 命令

**使用场景**:
- 收到 `queued` 状态后，稍后重试获取结果
- 定期检查是否有排队的请求

---

### 4. 用户信息类命令

#### 获取用户信息 (get_user_info)
**用途**: 获取当前用户的详细信息和配额状态

**请求数据**:
```json
{
  "user_id": "your_username",
  "session_id": "session_token"
}
```

**响应数据**:
```json
{
  "status": "success",
  "user_info": {
    "user_id": "your_username",
    "tier": "free|premium",
    "quota": {
      "daily_limit": 100,
      "daily_used": 15,
      "remaining": 85,
      "reset_at": "timestamp"
    },
    "token_usage": 12345,
    "is_banned": false,
    "created_at": "timestamp",
    "last_login": "timestamp"
  }
}
```

**使用场景**:
- 查看当前配额使用情况
- 验证用户状态

---

### 5. 版本检查类命令

#### 检查客户端版本 (check_version)
**用途**: 获取最新的客户端版本信息

**请求数据**: 空对象 `{}`

**响应数据**:
```json
{
  "status": "success",
  "data": {
    "version": "v1.0.0"
  }
}
```

**使用场景**:
- 客户端启动时自动检查更新
- 显示当前最新版本

---

### 6. 运行中操作管理类命令

#### 获取运行中操作 (get_running_operations)
**用途**: 获取当前正在执行的操作列表

**请求数据**:
```json
{
  "user_id": "your_username",
  "session_id": "session_token"
}
```

**响应数据**:
```json
{
  "status": "success",
  "data": {
    "running_operations": [
      {
        "id": 1,
        "action_type": "click|swipe",
        "params": {...},
        "start_time": "timestamp",
        "status": "running|completed|cancelled"
      }
    ]
  }
}
```

**使用场景**:
- 监控当前执行状态
- 查看有哪些操作正在进行

---

#### 取消操作 (cancel_operation)
**用途**: 取消指定的操作

**请求数据**:
```json
{
  "user_id": "your_username",
  "session_id": "session_token",
  "operation_id": 1
}
```

**响应数据**:
```json
{
  "status": "success",
  "message": "操作 1 已取消"
}
```

**使用场景**:
- 取消某个正在执行的操作
- 停止不必要的操作

---

#### 更新操作参数 (update_operation_params)
**用途**: 更新正在运行的操作参数

**请求数据**:
```json
{
  "user_id": "your_username",
  "session_id": "session_token",
  "operation_id": 1,
  "new_params": {
    "coordinates": [x, y],
    "duration": 2000
  }
}
```

**响应数据**:
```json
{
  "status": "success",
  "message": "操作 1 参数已更新"
}
```

**使用场景**:
- 动态调整操作参数
- 修改未完成操作的目标位置

---

## 错误响应格式

所有命令可能返回的错误格式：

```json
{
  "status": "error",
  "message": "错误描述",
  "error_type": "错误类型（可选）"
}
```

### 常见错误类型

| 错误类型 | 说明 | 处理建议 |
|---------|------|---------|
| `session_expired` | 会话已过期 | 重新登录获取新的 session_id |
| `invalid_api_key` | API密钥错误 | 检查API密钥是否正确 |
| `user_not_found` | 用户不存在 | 确认用户是否存在或重新注册 |
| `user_banned` | 账户被封禁 | 联系管理员解封 |
| `invalid_request` | 请求参数无效 | 检查请求参数格式 |
| `provider_rate_limit_exceeded` | 供应商限流 | 稍后重试或联系管理员 |
| `quota_exceeded` | 配额不足 | 升级账户或等待配额重置 |

---

## 调试建议

### 1. 使用重连机制
- 登录成功后，通信器会自动启用重连机制
- 网络中断时最多重试3次，每次间隔4秒
- 登录/注册请求不使用重连机制

### 2. 检查网络连接
```python
# 检查连接状态
if communicator.is_authenticated():
    print("已认证，可以执行任务")
```

### 3. 日志调试
所有通信操作都会记录到日志中：
- 使用 `logger.log()` 记录调试信息
- 查看 `logs/` 目录下的日志文件
- 使用 `LogCategory.COMMUNICATION` 过滤通信相关日志

### 4. 超时设置
- 默认超时为300秒（5分钟）
- 可在初始化时自定义：
```python
communicator = ClientCommunicator(
    host="127.0.0.1",
    port=9999,
    timeout=600  # 10分钟
)
```

### 5. 加密说明
- 所有通信数据都会被加密
- 使用 PBKDF2-HMAC-SHA256 导出密钥
- 加密算法为 AES（通过 Fernet 库实现）
- 确保客户端和服务端密码一致

---

## 示例代码

### 基础使用示例

```python
from communicator import ClientCommunicator

# 初始化通信器
communicator = ClientCommunicator(
    host="127.0.0.1",
    port=9999,
    password="default_password"
)

# 注册用户
register_data = {"user_id": "test_user"}
register_response = communicator.send_request("register", register_data)
api_key = register_response["key"]

# 登录
login_data = {
    "user_id": "test_user",
    "key": api_key
}
login_response = communicator.send_request("login", login_data)
session_id = login_response["session_id"]

# 设置登录状态
communicator.set_logged_in(True)

# 获取任务列表
tasks_response = communicator.send_request("get_default_tasks", {})
tasks = tasks_response["tasks"]

# 处理图像（示例）
process_data = {
    "user_id": "test_user",
    "session_id": session_id,
    "device_image": "base64_image_data",
    "current_task": "task_id_1",
    "task_variables": {},
    "device_info": {
        "resolution": [1080, 1920],
        "model": "Test Device",
        "image_size": [540, 960]
    }
}
result = communicator.send_request("process_image", process_data)

# 检查结果
if result["status"] == "success":
    actions = result["data"]["touch_actions"]
    print(f"收到 {len(actions)} 个触控动作")
```

### 错误处理示例

```python
result = communicator.send_request("process_image", data)

if result["status"] == "success":
    # 成功处理
    print("处理成功")

elif result["status"] == "error":
    error_type = result.get("error_type")

    if error_type == "session_expired":
        # 重新登录
        print("会话过期，重新登录...")
        # ...重新登录逻辑

    elif error_type == "provider_rate_limited":
        # 供应商限流，等待后重试
        print("供应商限流，等待10秒后重试")
        import time
        time.sleep(10)
        # ...重试逻辑

    else:
        # 其他错误
        print(f"错误: {result['message']}")
```

---

## 注意事项

1. **认证顺序**: 必须先注册/登录，获取 session_id 后才能执行其他操作
2. **配额限制**: 每天有使用次数限制，请合理分配使用
3. **图像大小**: 发送的图像会经过压缩，建议控制在 1024 像素以内
4. **会话有效期**: session_id 有一定有效期，过期需要重新登录
5. **并发限制**: 同一用户不建议同时发起多个 process_image 请求
6. **错误重试**: 网络错误会自动重试，但业务逻辑错误需要手动处理

---

## 版本历史

- **v1.0.0** (2026-03-04)
  - 初版命令帮助文档
  - 支持基本的认证、任务和图像处理命令
  - 支持重连机制和自动会话恢复

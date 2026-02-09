## 完整 Android 设备控制模块使用说明

## 概述

`complete_android_control_no_maa.py` 模块提供了一个完整的 Android 设备控制接口，基于标准的 ADB 命令实现所有功能。

## 功能特性

1. **设备发现**：扫描并列出所有可用的 ADB 设备
2. **设备连接**：建立与指定设备的连接
3. **触摸控制**：点击、双击、滑动操作
4. **文本输入**：向设备输入文本
5. **按键控制**：模拟物理按键操作
6. **屏幕截图**：获取设备屏幕截图并返回 base64 编码数据
7. **时间获取**：获取当前系统时间
8. **跨平台兼容**：支持 Windows、macOS 和 Linux
9. **自动文件管理**：自动保存截图并管理临时文件

## 安装和依赖

该模块依赖于以下库：
- `opencv-python` - 图像处理库
- `ADB (Android Debug Bridge)` - Android 调试桥工具

需要确保以下条件：
1. 系统已安装 ADB 工具并添加到 PATH 环境变量中
2. Android 设备已开启开发者选项和 USB 调试
3. 通过 USB 连接设备并授权调试权限

## 使用方法

### 1. 基本导入

```python
from maa_mcp.complete_android_control_no_maa import (
    find_adb_device_list,
    connect_adb_device,
    click,
    double_click,
    swipe,
    input_text,
    click_key,
    screencap,
    get_current_datetime
)
```

### 2. 设备发现和连接

```python
# 查找所有可用的 ADB 设备
devices = find_adb_device_list()
print(f"找到 {len(devices)} 个设备: {devices}")

# 连接指定设备（这里假设选择了第一个设备）
if devices:
    selected_device = devices[0]
    controller_id = connect_adb_device(selected_device)

    if controller_id:
        print(f"成功连接设备，控制器ID: {controller_id}")
    else:
        print("连接设备失败")
else:
    print("未找到可用设备")
```

### 3. 触摸控制

```python
# 点击屏幕中心点（假设屏幕分辨率为1080x1920）
if controller_id:
    # 单击
    success = click(controller_id, 540, 960)
    print(f"点击操作: {'成功' if success else '失败'}")

    # 长按1秒
    success = click(controller_id, 540, 960, duration=1000)
    print(f"长按操作: {'成功' if success else '失败'}")

    # 双击
    success = double_click(controller_id, 540, 960)
    print(f"双击操作: {'成功' if success else '失败'}")

    # 滑动（从屏幕底部向上滑动）
    success = swipe(controller_id, 540, 1800, 540, 200, 500)
    print(f"滑动操作: {'成功' if success else '失败'}")
```

### 4. 文本输入和按键

```python
# 输入文本
if controller_id:
    success = input_text(controller_id, "Hello, World!")
    print(f"文本输入: {'成功' if success else '失败'}")

    # 模拟回车键
    success = click_key(controller_id, 66)  # 66是Android回车键的 keycode
    print(f"回车键: {'成功' if success else '失败'}")

    # 模拟返回键
    success = click_key(controller_id, 4)   # 4是Android返回键的 keycode
    print(f"返回键: {'成功' if success else '失败'}")

    # 长按电源键
    success = click_key(controller_id, 26, duration=2000)  # 26是Android电源键的 keycode
    print(f"长按电源键: {'成功' if success else '失败'}")
```

### 5. 屏幕截图

```python
# 截图
if controller_id:
    image = screencap(controller_id)

    if image:
        print(f"截图成功，数据长度: {len(image.data)}")
        # image.data 包含 base64 编码的图像数据
        # 可以直接用于前端显示或保存到文件
    else:
        print("截图失败")
```

### 6. 获取当前时间

```python
# 获取当前时间
current_time = get_current_datetime()
print(f"当前时间: {current_time}")
```

### 7. 完整示例

```python
from maa_mcp.complete_android_control_no_maa import (
    find_adb_device_list,
    connect_adb_device,
    click,
    swipe,
    input_text,
    click_key,
    screencap,
    get_current_datetime
)
import time

def main():
    # 获取当前时间
    print(f"开始执行: {get_current_datetime()}")

    # 查找设备
    devices = find_adb_device_list()
    print(f"找到 {len(devices)} 个设备")

    if not devices:
        print("未找到可用设备")
        return

    # 连接设备
    selected_device = devices[0]
    controller_id = connect_adb_device(selected_device)
    if not controller_id:
        print("连接设备失败")
        return

    print(f"设备连接成功: {controller_id}")

    # 等待设备稳定
    time.sleep(2)

    # 截图
    print("执行截图...")
    image = screencap(controller_id)
    if image:
        print(f"截图成功，数据长度: {len(image.data[:50])}...")
    else:
        print("截图失败")

    # 点击屏幕中心
    print("执行点击...")
    success = click(controller_id, 540, 960)
    print(f"点击操作: {'成功' if success else '失败'}")

    # 等待
    time.sleep(1)

    # 输入文本
    print("执行文本输入...")
    success = input_text(controller_id, "测试文本")
    print(f"文本输入: {'成功' if success else '失败'}")

    # 等待
    time.sleep(1)

    # 模拟回车
    print("执行回车...")
    success = click_key(controller_id, 66)
    print(f"回车操作: {'成功' if success else '失败'}")

    # 再次截图
    print("执行第二次截图...")
    image = screencap(controller_id)
    if image:
        print(f"截图成功，数据长度: {len(image.data[:50])}...")
    else:
        print("截图失败")

    print(f"执行完成: {get_current_datetime()}")

if __name__ == "__main__":
    main()
```

## API 详细说明

### find_adb_device_list() -> List[str]

**功能**：扫描并枚举当前系统中所有可用的 ADB 设备

**返回值**：
- 设备名称列表

**注意事项**：
- 当返回多个设备时，应该暂停执行并让用户选择设备
- 不应该自动选择设备

### connect_adb_device(device_name: str) -> Optional[str]

**功能**：建立与指定 ADB 设备的连接

**参数**：
- `device_name`: 目标设备名称，需通过 `find_adb_device_list()` 获取

**返回值**：
- 成功：返回控制器 ID（字符串）
- 失败：返回 None

### click(controller_id: str, x: int, y: int, button: int = 0, duration: int = 50) -> bool

**功能**：在设备屏幕上执行单点点击操作，支持长按

**参数**：
- `controller_id`: 控制器 ID
- `x`: 目标点的 X 坐标（像素，整数）
- `y`: 目标点的 Y 坐标（像素，整数）
- `button`: 按键编号，默认为 0
- `duration`: 按下持续时间（毫秒），默认为 50

**返回值**：
- 成功：返回 True
- 失败：返回 False

### double_click(controller_id: str, x: int, y: int, button: int = 0, duration: int = 50, interval: int = 100) -> bool

**功能**：在设备屏幕上执行双击操作

**参数**：
- `controller_id`: 控制器 ID
- `x`: 目标点的 X 坐标（像素，整数）
- `y`: 目标点的 Y 坐标（像素，整数）
- `button`: 按键编号，默认为 0
- `duration`: 每次按下的持续时间（毫秒），默认为 50
- `interval`: 两次点击之间的间隔时间（毫秒），默认为 100

**返回值**：
- 成功：返回 True
- 失败：返回 False

### swipe(controller_id: str, start_x: int, start_y: int, end_x: int, end_y: int, duration: int) -> bool

**功能**：在设备屏幕上执行手势滑动操作

**参数**：
- `controller_id`: 控制器 ID
- `start_x`: 起始点的 X 坐标（像素，整数）
- `start_y`: 起始点的 Y 坐标（像素，整数）
- `end_x`: 终点的 X 坐标（像素，整数）
- `end_y`: 终点的 Y 坐标（像素，整数）
- `duration`: 滑动持续时间（毫秒，整数）

**返回值**：
- 成功：返回 True
- 失败：返回 False

### input_text(controller_id: str, text: str) -> bool

**功能**：在设备屏幕上执行输入文本操作

**参数**：
- `controller_id`: 控制器 ID
- `text`: 要输入的文本（字符串）

**返回值**：
- 成功：返回 True
- 失败：返回 False

### click_key(controller_id: str, key: int, duration: int = 50) -> bool

**功能**：在设备屏幕上执行按键点击操作，支持长按

**参数**：
- `controller_id`: 控制器 ID
- `key`: 要点击的按键（虚拟按键码）
- `duration`: 按键持续时间（毫秒），默认为 50

**返回值**：
- 成功：返回 True
- 失败：返回 False

**常用按键值**：
- 返回键: 4
- Home键: 3
- 菜单键: 82
- 回车/确认: 66
- 删除/退格: 67
- 音量+: 24
- 音量-: 25
- 电源键: 26

### screencap(controller_id: str) -> Optional[object]

**功能**：对当前设备屏幕进行截图，并返回图像数据

**参数**：
- `controller_id`: 控制器 ID

**返回值**：
- 成功：返回包含 base64 编码数据的 Image 对象
- 失败：返回 None

### get_current_datetime() -> str

**功能**：获取当前时间字符串（年月日时分秒）

**返回值**：
- 当前时间字符串，例如："2025-12-14 10:23:45"

## 注意事项

1. **ADB 环境**：确保系统已正确安装 ADB 并添加到 PATH
2. **设备连接**：确保 Android 设备已开启 USB 调试并正确连接
3. **权限问题**：首次连接设备时需要在设备上授权调试权限
4. **错误处理**：所有函数都可能返回 None 或 False，应该适当处理
5. **资源管理**：模块会自动管理截图文件的保存和清理
6. **坐标系统**：所有坐标都以屏幕左上角为原点 (0, 0)，X 轴向右，Y 轴向下
7. **超时处理**：所有 ADB 命令都有超时限制，避免长时间阻塞

## 故障排除

1. **找不到设备**：
   - 确保设备已开启开发者选项和 USB 调试
   - 检查 USB 连接是否正常
   - 确保已安装正确的 ADB 驱动
   - 在命令行中运行 `adb devices` 确认设备可见

2. **连接失败**：
   - 检查设备是否被其他程序占用
   - 确保 ADB 服务正常运行
   - 尝试重新插拔 USB 线
   - 在命令行中运行 `adb kill-server` 和 `adb start-server` 重启 ADB 服务

3. **控制操作失败**：
   - 检查设备屏幕是否锁定
   - 确认应用有相应权限
   - 检查坐标是否在屏幕范围内
   - 确保设备没有处于特殊模式（如 recovery 模式）

4. **截图失败**：
   - 检查设备屏幕是否锁定
   - 确认设备存储空间充足
   - 检查是否有足够的本地存储空间
   - 确认 ADB 有截图权限

5. **文本输入问题**：
   - 某些特殊字符可能需要额外转义
   - 确保输入框已获得焦点
   - 检查输入法是否正常工作
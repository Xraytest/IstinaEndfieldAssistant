# IstinaEndfieldAssistant 自动化测试落实方案

## 一、项目现状分析

### 1.1 当前测试状态

| 项目 | 状态 |
|---|---|
| 测试目录 | `tests/` (9 个 git-tracked 文件，全部使用废弃中文目录导入) |
| 单元测试 | `tests/unit/` (24 个文件，未 git 跟踪) |
| 集成测试 | `tests/e2e/` (空目录) |
| 端到端测试 | `tests/integration/` (空目录) |
| **实际覆盖率** | **0%** (所有测试因导入错误无法运行) |

### 1.2 核心问题

1. **导入路径错误**：测试文件引用已废弃的中文目录 (`安卓相关/`, `入口/`, `控制/`, `图像传递/`)
2. **无 pytest 基础设施**：缺少 `conftest.py`、fixtures、mock 工具
3. **无测试分层**：所有测试都是全链路手动脚本，需要设备 + 服务器
4. **代码可测性**：部分模块依赖硬件 (GPU/ADB) 或外部服务 (TCP 服务器)

---

## 二、测试架构设计

### 2.1 测试目录结构

```
tests/
  conftest.py                    # 全局 fixtures + path setup
  unit/                          # 单元测试 (CI 运行)
    core/
      test_models.py             # 数据模型层 (纯数据，无需 mock)
      test_page_tree.py          # 页面树结构 (纯逻辑)
      test_logger.py             # 日志系统 (部分需 mock 文件系统)
      test_communicator.py       # 通信协议 (编解码逻辑)
      test_exploration_engine.py # 探索引擎 (解析逻辑)
      test_exception_detector.py # 异常检测 (文本匹配)
      test_model_manager.py      # 模型管理 (注册表逻辑)
      test_gpu_checker.py        # GPU 检测 (部分需 mock 硬件)
    device/
      test_adb_manager.py        # ADB 管理器 (需 mock subprocess)
      test_touch_manager.py      # 触控管理 (需 mock MaaFramework)
    cli/
      test_cli_router.py         # CLI 路由 (argparse 逻辑)
  integration/                   # 集成测试 (需服务器/设备)
    test_communication_flow.py   # 通信流程
    test_auth_flow.py            # 认证流程
    test_device_adb.py           # ADB 设备操作
  e2e/                          # 端到端测试 (手动触发)
    test_agent_loop.py          # Agent VLM 循环
    test_exploration_loop.py    # 探索循环
```

### 2.2 测试分层策略

| 层级 | 目标 | 运行条件 | 预期用例数 | 优先级 |
|---|---|---|---|---|
| **Unit** | 纯逻辑、数据模型、协议编解码、文本解析 | 无外部依赖 | 200+ | P0 |
| **Integration** | 模块间协作（通信 + 认证、ADB+ 截图） | 需 server 或设备 | 30+ | P1 |
| **E2E** | 完整自动化循环（VLM→截图→操作→验证） | 需 server+ 设备 + 游戏 | 10+ | P2 |

### 2.3 可测性分级

#### Tier 1 - 完全可测（无需 mock）
- `src/core/element_analysis/models.py` - 枚举/数据类/序列化
- `src/core/cloud/page_tree.py` - PageTree CRUD/hash/序列化
- `src/core/logger.py` - LogLevel/LogRecord/PerformanceMonitor

#### Tier 2 - 需简单 mock
- `src/core/communication/communicator.py` - 协议编解码
- `src/core/cloud/exploration_engine.py` - JSON 解析/元素转换
- `src/core/cloud/managers/exception_detector.py` - 文本检测/UI 状态判断
- `src/core/local_inference/model_manager.py` - 注册表查找/recommend_model
- `src/core/local_inference/gpu_checker.py` - 推荐模型/阈值判断

#### Tier 3 - 需深度 mock
- `src/core/cloud/managers/auth_manager.py` - mock communicator + filesystem
- `src/device/adb_manager.py` - mock subprocess
- `src/device/touch/touch_manager.py` - mock MaaFwTouchExecutor
- `src/screenshot/screen_capture.py` - mock adb_manager + touch_manager

#### Tier 4 - 仅集成测试
- `src/gui/pyqt6/app_main.py` - 需 Qt 运行时
- `scripts/istina.py` - 需 server + device + config
- 完整 VLM 反馈循环

---

## 三、实施计划

### 阶段 1：基础设施建立（Week 1）

#### 任务 1.1：创建 conftest.py
- [ ] 添加 src 目录到 sys.path
- [ ] 创建通用 fixtures：
  - `tmp_cache_dir` - 隔离缓存目录
  - `tmp_log_dir` - 隔离日志目录
  - `tmp_model_dir` - 隔离模型目录
  - `mock_communicator` - Mock TCP 通信器
  - `mock_screen_capture` - Mock 截图
  - `mock_touch_executor` - Mock 触控执行
  - `mock_subprocess` - Mock ADB 命令
  - `mock_pynvml` / `mock_psutil` - Mock 硬件检测

#### 任务 1.2：删除废弃测试
- [ ] 移除 `tests/test_auth.py` 等 9 个 git-tracked 文件（或标记为 deprecated）
- [ ] 清理 `tests/unit/` 中引用旧目录的文件

#### 任务 1.3：配置 pytest
- [ ] 确认 `pyproject.toml` 中 `testpaths` 和 `pythonpath` 配置
- [ ] 添加 pytest markers：
  ```python
  pytest.mark.requires_server  # 需要 127.0.0.1:9999
  pytest.mark.requires_device  # 需要 ADB 设备
  pytest.mark.requires_gpu     # 需要 NVIDIA GPU
  ```

### 阶段 2：单元测试实施（Week 2-3）

#### 任务 2.1：数据模型测试（Tier 1）
- [ ] `test_models.py` - 25 用例
  - ElementType/VerificationStatus/TaskStatus/TaskCycle 枚举值
  - ElementKnowledge.to_dict()/from_dict() 往返
  - PageKnowledge.get_element_by_semantic()
  - make_semantic_id() 确定性
- [ ] `test_page_tree.py` - 20 用例
  - hash_screenshot()/hash_element() 确定性
  - PageTree.add_node()/add_edge()/get_node()
  - PageNode.unexplored_elements 过滤逻辑
  - save()/load() 往返（tmpdir）
- [ ] `test_logger.py` - 15 用例
  - LogLevel/LogCategory 枚举
  - LogRecord.to_dict()
  - PerformanceMonitor.record/get_statistics

#### 任务 2.2：协议与解析测试（Tier 2）
- [ ] `test_communicator.py` - 15 用例
  - `_pack_message()` / `_unpack_message()` 二进制协议
  - `_create_cipher()` 密钥派生一致性
  - protocol_magic/protocol_version 常量
- [ ] `test_exploration_engine.py` - 12 用例
  - `_parse_json_from_text()` 多格式提取
  - `_dict_to_element()` 转换
  - `_enqueue_elements()` 元素入队逻辑
- [ ] `test_exception_detector.py` - 20 用例
  - `_detect_text_exceptions()` 中文游戏错误文本匹配
  - `_detect_ui_state()` 模式识别
  - `_is_state_stuck()` 历史序列判断
  - TaskExecutionMonitor.track/get/reset

#### 任务 2.3：硬件与管理测试（Tier 2-3）
- [ ] `test_model_manager.py` - 10 用例
  - MODEL_REGISTRY 验证
  - get_model_info() 注册表查找
  - recommend_model() GPU 内存匹配
- [ ] `test_gpu_checker.py` - 8 用例
  - _get_recommended_model() 查找
  - _check_meets_requirements() 阈值判断（mock psutil）
- [ ] `test_adb_manager.py` - 8 用例（mock subprocess）
- [ ] `test_touch_manager.py` - 7 用例（mock MaaFwTouchExecutor）

### 阶段 3：集成测试实施（Week 4）

#### 任务 3.1：通信集成
- [ ] `test_communication_flow.py`
  - 需本地 server 在 127.0.0.1:9999
  - 测试 register/login/get_user_info 完整流程
  - 测试 session 过期处理

#### 任务 3.2：设备集成
- [ ] `test_device_adb.py`
  - 需 ADB 设备连接
  - 测试 scan_devices/connect_device/shell_command

#### 任务 3.3：认证集成
- [ ] `test_auth_flow.py`
  - 需 server + arkpass 文件
  - 测试 login_with_arkpass/auto_login_with_arkpass

### 阶段 4：E2E 测试实施（Week 5+）

#### 任务 4.1：Agent 循环
- [ ] `test_agent_loop.py`
  - 需 server + 设备 + 游戏
  - 测试 screenshot → agent_chat → tap/swipe 完整循环
  - 手动触发标记

#### 任务 4.2：探索循环
- [ ] `test_exploration_loop.py`
  - 需 server + 设备 + 游戏
  - 测试 analyze → verify → navigate → backtrack 循环

---

## 四、运行策略

### 4.1 CI 配置（GitHub Actions / Azure DevOps）

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run unit tests
        run: pytest tests/unit/ -v --tb=short
```

### 4.2 本地开发

```bash
# 运行所有单元测试（无外部依赖）
pytest tests/unit/ -v

# 运行特定模块
pytest tests/unit/core/test_models.py -v

# 运行集成测试（需 server）
pytest tests/integration/ -v -m "requires_server"

# 运行 E2E 测试（需设备，手动触发）
pytest tests/e2e/ -v -m "requires_device"

# 生成覆盖率报告
pytest tests/unit/ --cov=src/core --cov-report=html
```

### 4.3 pytest markers 使用

```python
# 在测试函数上使用标记
@pytest.mark.requires_server
def test_auth_flow():
    ...

@pytest.mark.requires_device
def test_adb_screenshot():
    ...

# 运行特定标记的测试
pytest -m "not requires_device"  # 排除需要设备的测试
pytest -m "requires_server"       # 仅运行需要 server 的测试
```

---

## 五、验收标准

### 5.1 覆盖率目标

| 模块 | 目标覆盖率 | 优先级 |
|---|---|---|
| models.py | ≥95% | P0 |
| page_tree.py | ≥95% | P0 |
| logger.py | ≥90% | P0 |
| communicator.py | ≥85% | P1 |
| exploration_engine.py | ≥80% | P1 |
| exception_detector.py | ≥85% | P1 |
| model_manager.py | ≥80% | P2 |
| gpu_checker.py | ≥75% | P2 |

### 5.2 质量标准

- [ ] 所有单元测试在 CI 中通过（无外部依赖）
- [ ] 无测试间相互依赖
- [ ] 测试执行时间 < 30 秒（单元测试）
- [ ] 关键路径有集成测试覆盖
- [ ] 测试代码遵循 AAA 模式 (Arrange-Act-Assert)

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 硬件依赖测试无法在 CI 运行 | GPU/ADB 测试跳过 | 使用 mock，标记为 requires_gpu/device |
| Server 协议变更 | 集成测试失败 | 优先测试协议编解码层，上层逻辑 mock |
| PyQt6 测试需 GUI 环境 | GUI 测试无法自动化 | 分离业务逻辑，GUI 层仅手动测试 |
| 测试维护成本高 | 测试随代码过时 | 将测试纳入 Definition of Done，PR 必须包含相关测试 |

---

## 七、后续工作

1. **测试数据管理**：建立 `tests/fixtures/` 目录存放测试数据（JSON 样本、截图等）
2. **Mock 服务器**：创建轻量 mock server 用于集成测试，避免依赖真实服务
3. **视觉回归测试**：对 GUI 页面进行截图对比测试（需额外工具如 pytest-snapshot）
4. **性能测试**：对关键路径（VLM 调用、截图处理）进行基准测试

---

## 八、时间估算

| 阶段 | 工作内容 | 预计时间 |
|---|---|---|
| 阶段 1 | 基础设施 + 清理 | 3-5 天 |
| 阶段 2 | 单元测试实施 | 10-15 天 |
| 阶段 3 | 集成测试实施 | 5-7 天 |
| 阶段 4 | E2E 测试实施 | 5-10 天 |
| **总计** | | **23-37 天** |

---

## 九、推荐优先级

**立即执行（P0）**
1. 建立 conftest.py + fixtures
2. 实现 Tier 1 测试（models/page_tree/logger）
3. 配置 CI 自动运行单元测试

**短期执行（P1）**
1. 实现 Tier 2 测试（communicator/exploration/exception_detector）
2. 建立集成测试框架
3. 添加覆盖率报告

**中期执行（P2）**
1. 实现 Tier 3 测试（auth/device/touch）
2. 完善 E2E 手动测试脚本
3. 达到 80%+ 覆盖率目标

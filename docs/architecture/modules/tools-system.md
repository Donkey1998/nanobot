# 工具系统模块

> **文件位置**: [nanobot/agent/tools/](../../../nanobot/agent/tools/)
> **主要文件**: registry.py (75 行), base.py (103 行), filesystem.py (212 行)
> **最后更新**: 2026-02-10

---

## 1. 概述

工具系统模块是 nanobot 框架的可扩展能力层，为 Agent 提供执行实际操作的能力（如文件操作、Shell 命令、Web 搜索等）。

### 核心职责

- **工具注册**: 动态注册和管理可用工具
- **工具执行**: 异步执行工具调用并返回结果
- **参数验证**: 基于 JSON Schema 验证工具参数
- **错误处理**: 优雅处理工具执行失败

### 内置工具清单

| 工具 | 文件 | 功能 |
|------|------|------|
| **read_file** | [filesystem.py](../../../nanobot/agent/tools/filesystem.py) | 读取文件内容 |
| **write_file** | [filesystem.py](../../../nanobot/agent/tools/filesystem.py) | 写入文件 |
| **edit_file** | [filesystem.py](../../../nanobot/agent/tools/filesystem.py) | 编辑文件（替换文本） |
| **list_dir** | [filesystem.py](../../../nanobot/agent/tools/filesystem.py) | 列出目录内容 |
| **exec** | [shell.py](../../../nanobot/agent/tools/shell.py) | 执行 Shell 命令 |
| **web_search** | [web.py](../../../nanobot/agent/tools/web.py) | Web 搜索（Brave API） |
| **web_fetch** | [web.py](../../../nanobot/agent/tools/web.py) | 抓取网页内容 |
| **message** | [message.py](../../../nanobot/agent/tools/message.py) | 主动发送消息 |
| **spawn** | [spawn.py](../../../nanobot/agent/tools/spawn.py) | 创建子 Agent |
| **cron** | [cron.py](../../../nanobot/agent/tools/cron.py) | 管理定时任务 |
| **browser** | [browser.py](../../../nanobot/agent/tools/browser.py) | 浏览器自动化 |

### 相关模块

- [Agent 循环](agent-loop.md) - 工具的主要使用者
- [浏览器自动化](browser-automation.md) - browser 工具的实现
- [子 Agent 管理](subagent-manager.md) - spawn 工具的实现

---

## 2. 设计理念

### 2.1 策略模式

所有工具继承自统一的 `Tool` 抽象基类，确保一致的接口。

**代码位置**: [base.py:7-53](../../../nanobot/agent/tools/base.py#L7-L53)

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str: ...
```

### 2.2 注册表模式

`ToolRegistry` 集中管理所有工具，支持动态注册和查找。

**好处**:
- **解耦**: Agent 不需要知道具体工具类
- **可扩展**: 轻松添加新工具
- **测试友好**: 可以模拟工具进行测试

### 2.3 OpenAI Function Calling 格式

工具定义使用 OpenAI Function Calling 格式，确保与主流 LLM 兼容。

**参数 Schema**: JSON Schema 格式

---

## 3. 核心机制

### 3.1 工具执行流程

```
LLM 返回工具调用
    ↓
ToolRegistry.execute(name, params)
    ├─ 1. 查找工具实例
    ├─ 2. 参数验证 (JSON Schema)
    ├─ 3. 调用 Tool.execute(**params)
    └─ 4. 返回结果字符串
    ↓
结果添加到消息历史
    ↓
LLM 基于结果继续决策
```

### 3.2 参数验证

工具在执行前自动验证参数，确保类型和必填字段正确。

**代码位置**: [base.py:55-91](../../../nanobot/agent/tools/base.py#L55-L91)

**支持的验证**:
- 类型验证（string, integer, number, boolean, array, object）
- 必填字段（required）
- 枚举值（enum）
- 数值范围（minimum, maximum）
- 字符串长度（minLength, maxLength）
- 嵌套对象验证

### 3.3 路径解析和安全

文件系统工具使用 `_resolve_path()` 函数解析路径并可选地限制访问范围。

**代码位置**: [filesystem.py:9-14](../../../nanobot/agent/tools/filesystem.py#L9-L14)

```python
def _resolve_path(path: str, allowed_dir: Path | None = None) -> Path:
    resolved = Path(path).expanduser().resolve()
    if allowed_dir and not str(resolved).startswith(str(allowed_dir.resolve())):
        raise PermissionError(f"Path {path} is outside allowed directory {allowed_dir}")
    return resolved
```

---

## 4. 关键接口

### 4.1 Tool 基类

#### 属性

```python
@property
@abstractmethod
def name(self) -> str:  # 工具名称（用于函数调用）
    pass

@property
@abstractmethod
def description(self) -> str:  # 工具描述（告诉 LLM 用途）
    pass

@property
@abstractmethod
def parameters(self) -> dict[str, Any]:  # JSON Schema 格式的参数定义
    pass
```

#### 方法

```python
@abstractmethod
async def execute(self, **kwargs: Any) -> str:
    """执行工具，返回字符串结果"""
    pass

def validate_params(self, params: dict[str, Any]) -> list[str]:
    """验证参数，返回错误列表（空列表表示验证通过）"""
    pass

def to_schema(self) -> dict[str, Any]:
    """转换为 OpenAI Function Calling 格式"""
    pass
```

### 4.2 ToolRegistry

#### 构造函数

```python
def __init__(self):
    self._tools: dict[str, Tool] = {}
```

#### 方法

```python
def register(self, tool: Tool) -> None:
    """注册工具"""

def unregister(self, name: str) -> None:
    """注销工具"""

def get(self, name: str) -> Tool | None:
    """获取工具实例"""

def has(self, name: str) -> bool:
    """检查工具是否存在"""

def get_definitions(self) -> list[dict[str, Any]]:
    """获取所有工具的 OpenAI 格式定义"""

async def execute(self, name: str, params: dict[str, Any]) -> str:
    """执行工具"""

@property
def tool_names(self) -> list[str]:
    """获取已注册工具名称列表"""
```

---

## 5. 使用示例

### 5.1 创建自定义工具

```python
from nanobot.agent.tools.base import Tool
from typing import Any

class WeatherTool(Tool):
    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "获取指定城市的当前天气"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位"
                }
            },
            "required": ["city"]
        }

    async def execute(self, city: str, unit: str = "celsius", **kwargs) -> str:
        # 实现天气查询逻辑
        return f"{city} 的天气是 25°{unit[0]}"
```

### 5.2 注册和使用工具

```python
from nanobot.agent.tools.registry import ToolRegistry

# 创建注册表
registry = ToolRegistry()

# 注册工具
registry.register(WeatherTool())

# 获取工具定义（传给 LLM）
definitions = registry.get_definitions()

# 执行工具
result = await registry.execute("get_weather", {
    "city": "北京",
    "unit": "celsius"
})
print(result)  # 北京 的天气是 25°C
```

### 5.3 带权限控制的工具

```python
class SecureDeleteTool(Tool):
    def __init__(self, allowed_paths: list[str]):
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]

    @property
    def name(self) -> str:
        return "secure_delete"

    async def execute(self, path: str, **kwargs) -> str:
        file_path = Path(path).resolve()

        # 验证路径
        if not any(str(file_path).startswith(str(p)) for p in self.allowed_paths):
            return f"错误：路径 {path} 不在允许列表中"

        # 执行删除
        if file_path.exists():
            file_path.unlink()
            return f"已删除 {path}"
        return f"文件不存在：{path}"
```

### 5.4 上下文感知工具

某些工具需要知道当前会话信息（如 `message` 工具需要知道发送目标）。

```python
class ContextAwareTool(Tool):
    def __init__(self):
        self._channel = None
        self._chat_id = None

    def set_context(self, channel: str, chat_id: str):
        """设置当前会话上下文"""
        self._channel = channel
        self._chat_id = chat_id

    async def execute(self, content: str, **kwargs) -> str:
        if not self._channel or not self._chat_id:
            return "错误：未设置会话上下文"

        # 使用上下文执行操作
        await send_message(self._channel, self._chat_id, content)
        return f"已发送消息到 {self._channel}:{self._chat_id}"
```

---

## 6. 扩展指南

### 6.1 添加新工具

1. **创建工具类**：继承 `Tool`
2. **实现属性和方法**：`name`, `description`, `parameters`, `execute`
3. **注册工具**：在 `AgentLoop._register_default_tools()` 中注册

**示例**:

```python
# 在 nanobot/agent/tools/ 创建 mytool.py
from nanobot.agent.tools.base import Tool

class MyCustomTool(Tool):
    # ... 实现 ...

# 在 agent/loop.py 中注册
from nanobot.agent.tools.mytool import MyCustomTool

def _register_default_tools(self) -> None:
    # ... 现有工具 ...
    self.tools.register(MyCustomTool())
```

### 6.2 工具依赖管理

如果工具需要外部依赖，可以在执行时检查并给出友好提示：

```python
class DatabaseTool(Tool):
    async def execute(self, query: str, **kwargs) -> str:
        try:
            import psycopg2  # 检查依赖
        except ImportError:
            return "错误：此工具需要安装 psycopg2: pip install psycopg2-binary"

        # 执行数据库操作
        pass
```

### 6.3 工具异步操作

工具是异步的，可以执行耗时操作而不阻塞 Agent：

```python
class LongRunningTool(Tool):
    async def execute(self, **kwargs) -> str:
        # 异步下载大文件
        async with httpx.AsyncClient() as client:
            response = await client.get("https://example.com/large.zip")
            # ... 处理响应
        return "下载完成"
```

### 6.4 工具组合

一个工具可以调用其他工具：

```python
class DeployTool(Tool):
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, app: str, **kwargs) -> str:
        # 组合调用其他工具
        test_result = await self.registry.execute("run_tests", {"app": app})
        if "failed" in test_result:
            return f"部署失败：测试未通过\n{test_result}"

        build_result = await self.registry.execute("build", {"app": app})
        return f"部署成功：\n{build_result}"
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/agent/tools/base.py](../../../nanobot/agent/tools/base.py) - Tool 基类（103 行）
- [nanobot/agent/tools/registry.py](../../../nanobot/agent/tools/registry.py) - 工具注册表（75 行）
- [nanobot/agent/tools/filesystem.py](../../../nanobot/agent/tools/filesystem.py) - 文件系统工具（212 行）
- [nanobot/agent/tools/shell.py](../../../nanobot/agent/tools/shell.py) - Shell 执行工具
- [nanobot/agent/tools/web.py](../../../nanobot/agent/tools/web.py) - Web 工具
- [nanobot/agent/tools/message.py](../../../nanobot/agent/tools/message.py) - 消息工具
- [nanobot/agent/tools/spawn.py](../../../nanobot/agent/tools/spawn.py) - 子 Agent 生成工具
- [nanobot/agent/tools/cron.py](../../../nanobot/agent/tools/cron.py) - 定时任务工具
- [nanobot/agent/tools/browser.py](../../../nanobot/agent/tools/browser.py) - 浏览器工具

### 依赖模块

- [nanobot/agent/loop.py](../../../nanobot/agent/loop.py) - 工具注册和使用

### 相关文档

- [Agent 循环模块文档](agent-loop.md)
- [浏览器自动化模块文档](browser-automation.md)
- [子 Agent 管理模块文档](subagent-manager.md)

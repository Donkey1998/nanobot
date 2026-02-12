# Agent 循环模块

> **文件位置**: [nanobot/agent/loop.py](nanobot/agent/loop.py)
> **行数**: 约 427 行
> **最后更新**: 2026-02-10

---

## 1. 概述

Agent 循环模块（`AgentLoop`）是 nanobot 框架的核心处理引擎，实现了 ReAct（推理-行动）模式的智能体决策循环。它负责从消息总线接收用户消息、构建完整的 LLM 上下文、执行工具调用、并返回响应。

### 核心职责

- **消息循环处理**: 从消息总线持续接收并处理入站消息
- **上下文构建**: 整合历史记录、记忆和技能构建完整上下文
- **LLM 交互**: 调用大语言模型并处理响应
- **工具执行**: 执行 LLM 返回的工具调用请求
- **会话管理**: 维护对话历史和状态
- **子 Agent 协调**: 处理系统消息和子 Agent 通信

### 相关模块

- [消息总线](message-bus.md) - 提供异步消息传递机制
- [上下文构建器](context-builder.md) - 负责组装 LLM 上下文
- [工具系统](tools-system.md) - 提供可执行的工具
- [会话管理](session-manager.md) - 持久化对话历史
- [子 Agent 管理](subagent-manager.md) - 并行任务处理

---

## 2. 设计理念

### 2.1 ReAct 模式

Agent 循环实现了 ReAct（Reasoning + Acting）模式，这是一种让 AI Agent 能够通过**推理**和**行动**的交替循环来完成复杂任务的方法。

**核心思想**:
1. LLM 先**思考**当前应该做什么
2. 决定是否需要调用工具（**行动**）
3. 观察工具执行结果
4. 基于结果继续思考或给出最终答案

**代码体现** ([loop.py:231-274](../../../nanobot/agent/loop.py#L231-L274)):
```python
while iteration < self.max_iterations:
    # 1. LLM 思考
    response = await self.provider.chat(messages, tools)

    if response.has_tool_calls:
        # 2. 执行工具调用
        for tool_call in response.tool_calls:
            result = await self.tools.execute(tool_call.name, tool_call.arguments)
            messages = self.context.add_tool_result(messages, tool_call.id, tool_call.name, result)
        # 3. 继续下一轮迭代
        iteration += 1
    else:
        # 4. 生成最终回复
        final_content = response.content
        break
```

### 2.2 单一职责原则

`AgentLoop` 专注于**决策和协调**，将具体功能委托给专门的模块：

| 职责 | 委托给 |
|------|--------|
| 工具执行 | `ToolRegistry` |
| 上下文组装 | `ContextBuilder` |
| 会话持久化 | `SessionManager` |
| 子 Agent 管理 | `SubagentManager` |

### 2.3 防御性设计

- **迭代次数限制**: 默认最多 20 轮工具调用，防止无限循环
- **异常隔离**: 单条消息错误不会中断整个循环
- **超时保护**: 消息消费使用 1 秒超时，允许优雅停止

---

## 3. 核心机制

### 3.1 主循环流程

```
┌─────────────────────────────────────────────────────────┐
│                    AgentLoop.run()                       │
│              (持续运行直到 stop() 被调用)                 │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│         从 MessageBus.consume_inbound() 获取消息         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│              _process_message(msg)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. 获取/创建会话 (sessions.get_or_create)        │    │
│  │ 2. 更新工具上下文 (message, spawn, cron)         │    │
│  │ 3. 构建 LLM 上下文 (context.build_messages)      │    │
│  │ 4. ReAct 循环 (最多 max_iterations 轮)           │    │
│  │ 5. 保存会话历史 (sessions.save)                  │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│     向 MessageBus.publish_outbound() 发送响应            │
└─────────────────────────────────────────────────────────┘
```

### 3.2 工具上下文更新

某些工具需要知道当前消息的来源（例如 `message` 工具需要知道发送到哪个频道）。

**代码位置**: [loop.py:204-214](../../../nanobot/agent/loop.py#L204-L214)

```python
# 更新 message 工具的上下文
message_tool = self.tools.get("message")
if isinstance(message_tool, MessageTool):
    message_tool.set_context(msg.channel, msg.chat_id)

# 更新 spawn 工具的上下文
spawn_tool = self.tools.get("spawn")
if isinstance(spawn_tool, SpawnTool):
    spawn_tool.set_context(msg.channel, msg.chat_id)

# 更新 cron 工具的上下文
cron_tool = self.tools.get("cron")
if isinstance(cron_tool, CronTool):
    cron_tool.set_context(msg.channel, msg.chat_id)
```

### 3.3 系统消息处理

子 Agent 通过系统频道向主 Agent 公布结果。主 Agent 需要解析原始来源信息并将响应路由回正确的目标。

**代码位置**: [loop.py:293-393](../../../nanobot/agent/loop.py#L293-L393)

**chat_id 格式**: `"original_channel:original_chat_id"`

例如，如果原始消息来自 `telegram:12345`，子 Agent 的系统消息 `chat_id` 将是 `"telegram:12345"`，主 Agent 解析后将响应发送回正确的渠道。

---

## 4. 关键接口

### 4.1 构造函数

```python
def __init__(
    self,
    bus: MessageBus,                          # 消息总线
    provider: LLMProvider,                    # LLM 提供商
    workspace: Path,                          # 工作区路径
    model: str | None = None,                 # 模型名称
    max_iterations: int = 20,                 # 最大工具迭代次数
    brave_api_key: str | None = None,         # Brave 搜索 API 密钥
    exec_config: ExecToolConfig | None = None, # Shell 执行配置
    cron_service: CronService | None = None,  # 定时任务服务
    restrict_to_workspace: bool = False,      # 限制工具访问工作区
    config: Config | None = None,             # 完整配置
)
```

**参数说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `bus` | `MessageBus` | 必填 | 用于接收/发送消息的消息总线 |
| `provider` | `LLMProvider` | 必填 | LLM 提供商实例 |
| `workspace` | `Path` | 必填 | 工作区路径，用于文件操作和会话存储 |
| `model` | `str \| None` | `None` | 模型名称，`None` 时使用提供商默认模型 |
| `max_iterations` | `int` | `20` | 单个消息处理的最大工具调用迭代次数 |
| `restrict_to_workspace` | `bool` | `False` | 是否限制文件操作在工作区内 |

### 4.2 核心方法

#### `async def run() -> None`

启动 Agent 循环，持续处理来自消息总线的消息。

**代码位置**: [loop.py:144-174](../../../nanobot/agent/loop.py#L144-L174)

**行为**:
- 持续从 `MessageBus.inbound` 队列获取消息
- 调用 `_process_message()` 处理每条消息
- 将响应发布到 `MessageBus.outbound` 队列
- 捕获异常并返回错误响应给用户

#### `def stop() -> None`

停止 Agent 循环。

**代码位置**: [loop.py:176-179](../../../nanobot/agent/loop.py#L176-L179)

#### `async def process_direct(...) -> str`

直接处理消息（绕过消息总线），用于 CLI 模式。

**代码位置**: [loop.py:395-426](../../../nanobot/agent/loop.py#L395-L426)

**参数**:
- `content`: 用户输入的消息内容
- `session_key`: 会话标识符，默认 `"cli:direct"`
- `channel`: 来源渠道，默认 `"cli"`
- `chat_id`: 来源聊天 ID，默认 `"direct"`

**返回**: Agent 的响应文本内容

---

## 5. 使用示例

### 5.1 创建和启动 Agent 循环

```python
import asyncio
from pathlib import Path
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.agent.loop import AgentLoop

async def main():
    # 创建核心组件
    bus = MessageBus()
    provider = LiteLLMProvider(api_key="sk-...")
    workspace = Path("~/.nanobot/workspace").expanduser()

    # 创建 Agent 循环
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
        model="anthropic/claude-sonnet-4-5",
        max_iterations=20,
    )

    # 启动循环（在后台任务中）
    task = asyncio.create_task(agent.run())

    # 模拟发送消息
    from nanobot.bus.events import InboundMessage
    await bus.publish_inbound(InboundMessage(
        channel="cli",
        sender_id="user",
        chat_id="direct",
        content="你好，请帮我列出当前目录的文件"
    ))

    # 等待响应
    response = await bus.consume_outbound()
    print(response.content)

    # 停止
    agent.stop()
    await task

asyncio.run(main())
```

### 5.2 直接处理模式（CLI）

```python
# 绕过消息总线，直接处理用户输入
response = await agent.process_direct(
    content="帮我创建一个新的 Python 文件",
    session_key="cli:interactive",
    channel="cli",
    chat_id="user"
)
print(response)
```

### 5.3 自定义工具迭代限制

```python
# 创建限制更严格的 Agent（适合简单任务）
strict_agent = AgentLoop(
    bus=bus,
    provider=provider,
    workspace=workspace,
    max_iterations=5,  # 最多 5 轮工具调用
)

# 创建宽松的 Agent（适合复杂任务）
flexible_agent = AgentLoop(
    bus=bus,
    provider=provider,
    workspace=workspace,
    max_iterations=50,  # 最多 50 轮工具调用
)
```

---

## 6. 扩展指南

### 6.1 添加自定义工具

在 `_register_default_tools()` 方法中注册新工具：

**代码位置**: [loop.py:95-142](../../../nanobot/agent/loop.py#L95-L142)

```python
def _register_default_tools(self) -> None:
    # ... 现有工具 ...

    # 添加自定义工具
    from my_tools import CustomTool
    self.tools.register(CustomTool())
```

### 6.2 修改系统提示

系统提示由 `ContextBuilder` 生成。要自定义提示，可以：

1. 修改工作区中的引导文件（`AGENTS.md`、`SOUL.md` 等）
2. 或者创建自定义的 `ContextBuilder` 子类

### 6.3 处理新的消息类型

要处理特殊类型的消息（例如图片、文件），可以：

1. 扩展 `InboundMessage` 数据模型
2. 在 `_process_message()` 中添加特殊处理逻辑
3. 将媒体内容传递给 `context.build_messages()`

### 6.4 集成新的 LLM 提供商

创建新的 `LLMProvider` 实现并传递给 `AgentLoop`：

```python
from nanobot.providers.base import LLMProvider

class MyCustomProvider(LLMProvider):
    async def chat(self, messages, tools, model):
        # 实现自定义 LLM 调用逻辑
        pass

# 使用自定义提供商
agent = AgentLoop(
    bus=bus,
    provider=MyCustomProvider(api_key="..."),
    workspace=workspace,
)
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/agent/loop.py](nanobot/agent/loop.py) - Agent 循环主文件（427 行）

### 依赖模块

- [nanobot/bus/queue.py](nanobot/bus/queue.py) - 消息总线
- [nanobot/agent/context.py](nanobot/agent/context.py) - 上下文构建器
- [nanobot/agent/tools/registry.py](nanobot/agent/tools/registry.py) - 工具注册表
- [nanobot/session/manager.py](nanobot/session/manager.py) - 会话管理器
- [nanobot/agent/subagent.py](nanobot/agent/subagent.py) - 子 Agent 管理器

### 相关文档

- [消息总线模块文档](message-bus.md)
- [上下文构建器模块文档](context-builder.md)
- [工具系统模块文档](tools-system.md)
- [会话管理模块文档](session-manager.md)

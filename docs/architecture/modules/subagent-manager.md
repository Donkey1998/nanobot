# 子 Agent 管理模块

> **文件位置**: [nanobot/agent/subagent.py](../../../nanobot/agent/subagent.py)
> **行数**: 约 245 行
> **最后更新**: 2026-02-10

---

## 1. 概述

子 Agent 管理模块负责创建和管理后台任务，通过并行处理提高 Agent 的效率。子 Agent 是独立运行的轻量级 Agent 实例，专注于完成特定任务。

### 核心职责

- **子 Agent 创建**: 为后台任务创建独立的 Agent 实例
- **任务管理**: 管理运行中的子 Agent 生命周期
- **结果汇报**: 将子 Agent 的结果通过系统频道汇报给主 Agent
- **工具限制**: 子 Agent 使用受限的工具集（无 message、spawn 工具）

### 特点

- **并行处理**: 后台任务不阻塞主 Agent
- **独立上下文**: 子 Agent 无历史记录访问
- **专注提示**: 单任务导向的系统提示
- **自动汇报**: 完成后结果自动发送给主 Agent

### 相关模块

- [Agent 循环](agent-loop.md) - 主 Agent 和系统消息处理
- [工具系统](tools-system.md) - spawn 工具的实现

---

## 2. 设计理念

### 2.1 任务并行化

主 Agent 可以生成多个子 Agent 同时处理不同任务，提高效率。

**使用场景**:
- 长时间运行的任务（如数据处理）
- 独立的研究任务（如收集信息）
- 并行数据处理

### 2.2 隔离上下文

子 Agent 拥有独立的上下文，不访问主 Agent 的对话历史。

**好处**:
- **专注**: 子 Agent 专注于单任务
- **安全**: 防止子 Agent 访问敏感历史
- **简洁**: 更小的上下文降低 Token 成本

### 2.3 工具限制

子 Agent 的工具集受限，防止递归生成和不必要的消息发送。

**限制**:
- 无 `message` 工具（不能直接发消息）
- 无 `spawn` 工具（不能递归生成）
- 保留文件操作、Shell、Web 等基础工具

### 2.4 结果汇总

子 Agent 完成后通过系统频道向主 Agent 汇报结果，主 Agent 自然地总结给用户。

---

## 3. 核心机制

### 3.1 子 Agent 生成流程

```
主 Agent 调用 spawn 工具
    ↓
SubagentManager.spawn(task, origin_channel, origin_chat_id)
    ├─ 生成唯一的 task_id
    ├─ 创建后台 asyncio 任务
    └─ 返回确认消息
    ↓
_run_subagent(task_id, task, origin)
    ├─ 构建独立上下文（无历史）
    ├─ 限制工具集
    ├─ 添加专注的系统提示
    └─ 运行 ReAct 循环（最多 15 轮）
    ↓
_announce_result(result, origin)
    ├─ 构建系统消息
    └─ 发布到 MessageBus.inbound
    ↓
主 Agent 接收系统消息
    └─ 自然地总结结果给用户
```

### 3.2 系统消息格式

子 Agent 通过系统频道汇报结果，`chat_id` 编码了原始来源信息。

**格式**: `"original_channel:original_chat_id"`

**代码位置**: [subagent.py:179-209](../../../nanobot/agent/subagent.py#L179-L209)

```python
async def _announce_result(self, task_id, label, task, result, origin, status):
    announce_content = f"""[子 Agent '{label}' {status_text}]

任务：{task}

结果：
{result}

请为用户自然地总结一下。保持简短（1-2 句话）。不要提及"子 Agent"或任务 ID 等技术细节。"""

    msg = InboundMessage(
        channel="system",
        sender_id="subagent",
        chat_id=f"{origin['channel']}:{origin['chat_id']}",
        content=announce_content,
    )
    await self.bus.publish_inbound(msg)
```

### 3.3 专注的系统提示

子 Agent 使用专门的系统提示，强调专注和简洁。

**代码位置**: [subagent.py:211-240](../../../nanobot/agent/subagent.py#L211-L240)

```python
def _build_subagent_prompt(self, task: str) -> str:
    return f"""# 子 Agent

你是主 Agent 生成的子 Agent，用于完成特定任务。

## 你的任务
{task}

## 规则
1. 保持专注 - 只完成指定的任务，不做其他事情
2. 你的最终响应将报告给主 Agent
3. 不要发起对话或承担副任务
4. 在发现中保持简洁但信息丰富

## 你可以做什么
- 读取和写入工作区中的文件
- 执行 Shell 命令
- 搜索网络和获取网页
- 彻底完成任务

## 你不能做什么
- 直接向用户发送消息（没有消息工具）
- 生成其他子 Agent
- 访问主 Agent 的对话历史

## 工作区
你的工作区位于：{self.workspace}

完成任务后，请清晰总结你的发现或操作。"""
```

---

## 4. 关键接口

### 4.1 SubagentManager

#### 构造函数

```python
def __init__(
    self,
    provider: LLMProvider,
    workspace: Path,
    bus: MessageBus,
    model: str | None = None,
    brave_api_key: str | None = None,
    exec_config: ExecToolConfig | None = None,
    restrict_to_workspace: bool = False,
):
    self.provider = provider
    self.workspace = workspace
    self.bus = bus
    self.model = model or provider.get_default_model()
    self._running_tasks: dict[str, asyncio.Task[None]] = {}
```

#### 方法

```python
async def spawn(
    self,
    task: str,
    label: str | None = None,
    origin_channel: str = "cli",
    origin_chat_id: str = "direct",
) -> str:
    """生成子 Agent 在后台执行任务"""

async def _run_subagent(
    self,
    task_id: str,
    task: str,
    label: str,
    origin: dict[str, str],
) -> None:
    """执行子 Agent 任务并公布结果"""

async def _announce_result(
    self,
    task_id: str,
    label: str,
    task: str,
    result: str,
    origin: dict[str, str],
    status: str,
) -> None:
    """通过消息总线向主 Agent 公布子 Agent 的结果"""

def _build_subagent_prompt(self, task: str) -> str:
    """为子 Agent 构建专注的系统提示"""

def get_running_count(self) -> int:
    """返回当前运行的子 Agent 数量"""
```

---

## 5. 使用示例

### 5.1 通过 spawn 工具使用

用户与主 Agent 对话时，LLM 可能决定调用 spawn 工具：

```
用户: "帮我分析这个项目的代码结构，同时搜索相关的最佳实践"

主 Agent: (决定生成两个子 Agent)
  - 子 Agent 1: 分析项目代码结构
  - 子 Agent 2: 搜索最佳实践

主 Agent: "我已经启动两个后台任务来处理这个请求，完成后我会给你总结。"

... (子 Agent 并行工作) ...

子 Agent 1: (系统消息) "代码结构分析完成..."
子 Agent 2: (系统消息) "最佳实践搜索完成..."

主 Agent: "基于分析结果，这个项目采用模块化架构..."
```

### 5.2 直接使用 SubagentManager

```python
import asyncio
from pathlib import Path
from nanobot.agent.subagent import SubagentManager
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.bus.queue import MessageBus

async def main():
    # 创建组件
    bus = MessageBus()
    provider = LiteLLMProvider(api_key="sk-...")
    workspace = Path("~/.nanobot/workspace").expanduser()

    # 创建子 Agent 管理器
    manager = SubagentManager(
        provider=provider,
        workspace=workspace,
        bus=bus
    )

    # 生成子 Agent
    result = await manager.spawn(
        task="分析 /path/to/project 的代码结构",
        label="代码分析",
        origin_channel="cli",
        origin_chat_id="user123"
    )

    print(result)
    # 输出: 子 Agent [代码分析] 已启动（id: a1b2c3d4）。完成后我会通知你。

    # 等待子 Agent 完成...
    await asyncio.sleep(30)

asyncio.run(main())
```

### 5.3 监控运行中的子 Agent

```python
# 获取运行中的子 Agent 数量
count = manager.get_running_count()
print(f"当前有 {count} 个子 Agent 在运行")
```

---

## 6. 扩展指南

### 6.1 添加子 Agent 优先级

```python
class PrioritizedSubagentManager(SubagentManager):
    async def spawn(self, task, priority="normal", **kwargs):
        """支持优先级的子 Agent 生成"""
        if priority == "high":
            # 使用不同的模型或更高的超时
            task_id = await self._spawn_with_priority(task, "high", **kwargs)
        else:
            task_id = await super().spawn(task, **kwargs)
        return task_id
```

### 6.2 添加子 Agent 通信

允许子 Agent 之间通信：

```python
class CollaborativeSubagentManager(SubagentManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shared_context = {}

    async def spawn(self, task, share_context=False, **kwargs):
        """支持上下文共享的子 Agent"""
        if share_context:
            # 子 Agent 可以访问共享上下文
            pass
        return await super().spawn(task, **kwargs)
```

### 6.3 添加子 Agent 超时控制

```python
class TimeoutSubagentManager(SubagentManager):
    async def _run_subagent(self, task_id, task, label, origin, timeout=300):
        """带超时的子 Agent 执行"""
        try:
            await asyncio.wait_for(
                super()._run_subagent(task_id, task, label, origin),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            error_msg = f"子 Agent [{label}] 超时（{timeout}秒）"
            await self._announce_result(task_id, label, task, error_msg, origin, "error")
```

### 6.4 添加子 Agent 结果缓存

```python
class CachingSubagentManager(SubagentManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._result_cache = {}

    async def spawn(self, task, use_cache=True, **kwargs):
        """支持结果缓存的子 Agent"""
        cache_key = hash(task)

        if use_cache and cache_key in self._result_cache:
            # 返回缓存结果
            await self._announce_result(
                None, "Cached", task,
                self._result_cache[cache_key],
                kwargs.get("origin", {}),
                "ok"
            )
            return "使用缓存结果"

        # 正常执行并缓存结果
        result = await super().spawn(task, **kwargs)
        # ... 缓存结果 ...
        return result
```

### 6.5 添加子 Agent 进度报告

```python
class ProgressReportingSubagentManager(SubagentManager):
    async def _run_subagent(self, task_id, task, label, origin):
        """支持进度报告的子 Agent"""
        # 在关键步骤报告进度
        await self._report_progress(task_id, label, "开始执行", origin)

        # 执行任务...
        await self._report_progress(task_id, label, "正在分析...", origin)

        # 完成
        await super()._run_subagent(task_id, task, label, origin)

    async def _report_progress(self, task_id, label, progress, origin):
        """报告进度"""
        content = f"[子 Agent '{label}] 进度更新]\n{progress}"
        msg = InboundMessage(
            channel="system",
            sender_id="subagent",
            chat_id=f"{origin['channel']}:{origin['chat_id']}",
            content=content,
        )
        await self.bus.publish_inbound(msg)
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/agent/subagent.py](../../../nanobot/agent/subagent.py) - 子 Agent 管理器（245 行）

### 依赖模块

- [nanobot/agent/loop.py](../../../nanobot/agent/loop.py) - 主 Agent 和系统消息处理
- [nanobot/agent/tools/spawn.py](../../../nanobot/agent/tools/spawn.py) - Spawn 工具
- [nanobot/bus/queue.py](../../../nanobot/bus/queue.py) - 消息总线

### 相关文档

- [Agent 循环模块文档](agent-loop.md)
- [工具系统模块文档](tools-system.md)
- [消息总线模块文档](message-bus.md)

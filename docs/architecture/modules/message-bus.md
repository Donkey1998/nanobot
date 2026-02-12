# 消息总线模块

> **文件位置**: [nanobot/bus/queue.py](../../../nanobot/bus/queue.py)
> **行数**: 约 82 行
> **最后更新**: 2026-02-10

---

## 1. 概述

消息总线模块（`MessageBus`）是 nanobot 框架的核心通信基础设施，实现了异步消息队列机制，用于解耦聊天平台适配器和 Agent 核心处理逻辑。

### 核心职责

- **消息入站**: 从聊天渠道接收用户消息
- **消息出站**: 将 Agent 响应发送回聊天渠道
- **异步解耦**: 允许渠道和 Agent 并发运行
- **消息分发**: 支持订阅模式路由出站消息

### 设计模式

**生产者-消费者模式**: 聊天渠道作为生产者发布消息，Agent 循环作为消费者处理消息。

### 相关模块

- [Agent 循环](agent-loop.md) - 消息的主要消费者
- [渠道管理器](channel-manager.md) - 消息的生产者和分发者
- [渠道适配器](channel-manager.md#渠道适配器) - 具体的聊天平台实现

---

## 2. 设计理念

### 2.1 解耦架构

消息总线将聊天平台和 Agent 核心完全解耦：

```
┌──────────────┐         ┌───────────────────┐         ┌──────────────┐
│  Telegram    │         │                   │         │              │
│  Discord     │ ──────> │   MessageBus      │ <────── │  AgentLoop   │
│  WhatsApp    │         │                   │         │              │
│  Feishu      │         └───────────────────┘         └──────────────┘
└──────────────┘                   ▲
                                     │
                              ┌──────┴──────┐
                              │  Inbound    │
                              │  Queue      │
                              │             │
                              │  Outbound   │
                              │  Queue      │
                              └─────────────┘
```

**好处**:
- **独立演进**: 聊天平台和 Agent 可以独立修改
- **并发处理**: 多个渠道可以同时处理消息
- **易于测试**: 可以模拟消息队列进行单元测试
- **灵活扩展**: 添加新渠道无需修改 Agent 逻辑

### 2.2 异步优先

全面使用 `asyncio.Queue` 实现非阻塞通信：

```python
self.inbound: asyncio.Queue[InboundMessage]   # 入站队列
self.outbound: asyncio.Queue[OutboundMessage]  # 出站队列
```

### 2.3 订阅者模式

出站消息使用订阅者模式，允许多个消费者接收特定渠道的消息：

**代码位置**: [queue.py:41-49](../../../nanobot/bus/queue.py#L41-L49)

```python
def subscribe_outbound(
    self,
    channel: str,
    callback: Callable[[OutboundMessage], Awaitable[None]]
) -> None:
    """订阅特定渠道的出站消息。"""
    if channel not in self._outbound_subscribers:
        self._outbound_subscribers[channel] = []
    self._outbound_subscribers[channel].append(callback)
```

---

## 3. 核心机制

### 3.1 双向队列架构

```
                    ┌──────────────────────────────────┐
                    │         MessageBus               │
                    │                                  │
┌───────────────┐   │  ┌──────────────────────────┐   │  ┌───────────────┐
│  Telegram     │   │  │   inbound: Queue         │   │  │               │
│  Channel      │───┼──>   (InboundMessage)       │───┼──>│  AgentLoop    │
│               │   │  │                          │   │  │               │
└───────────────┘   │  └──────────────────────────┘   │  └───────────────┘
                    │                                  │
                    │  ┌──────────────────────────┐   │
                    │  │   outbound: Queue        │   │
                    │  │   (OutboundMessage)      │<──┼─────────────────┐
                    │  │                          │   │                 │
                    │  └──────────────────────────┘   │                 │
                    │                                  │                 │
                    │  dispatch_outbound() ────────────┼─────────────────┤
                    │                                  │                 │
                    └──────────────────────────────────┘                 │
                                                                   │
┌───────────────┐                                           ┌───────┴─────────┐
│  Telegram     │<──────────────────────────────────────────│  Subscribers   │
│  Channel      │                                           │  Callback      │
└───────────────┘                                           └────────────────┘
```

### 3.2 消息类型

#### InboundMessage（入站消息）

从聊天平台发送到 Agent 的消息。

```python
@dataclass
class InboundMessage:
    channel: str          # 渠道标识符（telegram, discord, feishu, whatsapp）
    sender_id: str        # 发送者 ID
    chat_id: str          # 聊天 ID
    content: str          # 消息内容
    media: list[str] | None = None  # 媒体文件路径（图片等）
    session_key: str = field(default_factory=lambda: f"{channel}:{chat_id}")
```

#### OutboundMessage（出站消息）

从 Agent 发送到聊天平台的消息。

```python
@dataclass
class OutboundMessage:
    channel: str          # 目标渠道
    chat_id: str          # 目标聊天 ID
    content: str          # 响应内容
    media: list[str] | None = None  # 可选的媒体文件
```

### 3.3 出站分发器

`dispatch_outbound()` 方法作为后台任务运行，将出站消息路由到订阅的渠道回调。

**代码位置**: [queue.py:51-67](../../../nanobot/bus/queue.py#L51-L67)

```python
async def dispatch_outbound(self) -> None:
    """将出站消息分发到订阅的渠道。"""
    self._running = True
    while self._running:
        try:
            msg = await asyncio.wait_for(self.outbound.get(), timeout=1.0)
            subscribers = self._outbound_subscribers.get(msg.channel, [])
            for callback in subscribers:
                try:
                    await callback(msg)
                except Exception as e:
                    logger.error(f"分发到 {msg.channel} 时出错：{e}")
        except asyncio.TimeoutError:
            continue
```

---

## 4. 关键接口

### 4.1 构造函数

```python
def __init__(self):
    self.inbound: asyncio.Queue[InboundMessage]      # 入站消息队列
    self.outbound: asyncio.Queue[OutboundMessage]    # 出站消息队列
    self._outbound_subscribers: dict[str, list[Callable]]  # 订阅者回调
    self._running: bool = False
```

### 4.2 入站消息方法

#### `async def publish_inbound(self, msg: InboundMessage) -> None`

发布入站消息到队列。

**代码位置**: [queue.py:25-27](../../../nanobot/bus/queue.py#L25-L27)

**用法**:
```python
await bus.publish_inbound(InboundMessage(
    channel="telegram",
    sender_id="123456",
    chat_id="123456",
    content="Hello, bot!"
))
```

#### `async def consume_inbound(self) -> InboundMessage`

从入站队列获取消息（阻塞直到可用）。

**代码位置**: [queue.py:29-31](../../../nanobot/bus/queue.py#L29-L31)

### 4.3 出站消息方法

#### `async def publish_outbound(self, msg: OutboundMessage) -> None`

发布出站消息到队列。

**代码位置**: [queue.py:33-35](../../../nanobot/bus/queue.py#L33-L35)

#### `async def consume_outbound(self) -> OutboundMessage`

从出站队列获取消息（阻塞直到可用）。

**代码位置**: [queue.py:37-39](../../../nanobot/bus/queue.py#L37-L39)

### 4.4 订阅者方法

#### `def subscribe_outbound(self, channel: str, callback: Callable) -> None`

订阅特定渠道的出站消息。

**代码位置**: [queue.py:41-49](../../../nanobot/bus/queue.py#L41-L49)

**参数**:
- `channel`: 渠道名称（如 `"telegram"`）
- `callback`: 异步回调函数，接收 `OutboundMessage`

**用法**:
```python
async def handle_telegram(msg: OutboundMessage):
    await bot.send_message(chat_id=msg.chat_id, text=msg.content)

bus.subscribe_outbound("telegram", handle_telegram)
```

### 4.5 分发器方法

#### `async def dispatch_outbound(self) -> None`

启动出站消息分发循环。

**代码位置**: [queue.py:51-67](../../../nanobot/bus/queue.py#L51-L67)

**注意**: 此方法应在后台任务中运行。

#### `def stop(self) -> None`

停止分发器循环。

**代码位置**: [queue.py:69-71](../../../nanobot/bus/queue.py#L69-L71)

### 4.6 属性

#### `property def inbound_size(self) -> int`

获取待处理的入站消息数量。

**代码位置**: [queue.py:73-76](../../../nanobot/bus/queue.py#L73-L76)

#### `property def outbound_size(self) -> int`

获取待处理的出站消息数量。

**代码位置**: [queue.py:78-81](../../../nanobot/bus/queue.py#L78-L81)

---

## 5. 使用示例

### 5.1 基础使用

```python
import asyncio
from nanobot.bus.queue import MessageBus
from nanobot.bus.events import InboundMessage, OutboundMessage

async def producer(bus: MessageBus):
    """模拟聊天渠道发送消息"""
    for i in range(3):
        await bus.publish_inbound(InboundMessage(
            channel="test",
            sender_id="user",
            chat_id="room1",
            content=f"Message {i}"
        ))
        await asyncio.sleep(0.1)

async def consumer(bus: MessageBus):
    """模拟 Agent 处理消息"""
    while True:
        msg = await bus.consume_inbound()
        print(f"Received: {msg.content}")
        # 发送响应
        await bus.publish_outbound(OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=f"Echo: {msg.content}"
        ))

async def main():
    bus = MessageBus()

    # 并发运行生产者和消费者
    await asyncio.gather(
        producer(bus),
        consumer(bus)
    )

asyncio.run(main())
```

### 5.2 使用订阅者模式

```python
import asyncio
from nanobot.bus.queue import MessageBus
from nanobot.bus.events import OutboundMessage

async def telegram_handler(msg: OutboundMessage):
    print(f"[Telegram] Sending to {msg.chat_id}: {msg.content}")

async def discord_handler(msg: OutboundMessage):
    print(f"[Discord] Sending to {msg.chat_id}: {msg.content}")

async def main():
    bus = MessageBus()

    # 订阅不同渠道的出站消息
    bus.subscribe_outbound("telegram", telegram_handler)
    bus.subscribe_outbound("discord", discord_handler)

    # 启动分发器
    dispatch_task = asyncio.create_task(bus.dispatch_outbound())

    # 发布消息
    await bus.publish_outbound(OutboundMessage(
        channel="telegram",
        chat_id="12345",
        content="Hello Telegram!"
    ))

    await bus.publish_outbound(OutboundMessage(
        channel="discord",
        chat_id="67890",
        content="Hello Discord!"
    ))

    await asyncio.sleep(0.1)
    bus.stop()
    await dispatch_task

asyncio.run(main())
```

### 5.3 监控队列大小

```python
async def monitor_queues(bus: MessageBus):
    """定期打印队列状态"""
    while True:
        print(f"Inbound: {bus.inbound_size}, Outbound: {bus.outbound_size}")
        await asyncio.sleep(1)

# 在后台运行监控
asyncio.create_task(monitor_queues(bus))
```

---

## 6. 扩展指南

### 6.1 添加新的消息类型

如果需要支持新的消息元数据（如语音、视频），可以扩展 `InboundMessage` 和 `OutboundMessage`：

```python
@dataclass
class InboundMessage:
    # ... 现有字段 ...
    voice_note: str | None = None     # 语音文件路径
    video: str | None = None          # 视频文件路径
    reply_to: str | None = None       # 回复的消息 ID
```

### 6.2 实现消息优先级

如果需要支持消息优先级，可以使用 `asyncio.PriorityQueue`：

```python
import heapq
from dataclasses import dataclass, order

@order
@dataclass
class PrioritizedMessage:
    priority: int
    message: InboundMessage

class MessageBus:
    def __init__(self):
        self.inbound: asyncio.PriorityQueue[PrioritizedMessage] = ...

    async def publish_inbound(self, msg: InboundMessage, priority: int = 0):
        await self.inbound.put(PrioritizedMessage(priority, msg))
```

### 6.3 添加消息过滤

可以在发布消息时添加过滤逻辑：

```python
class MessageBus:
    def __init__(self):
        # ... 现有代码 ...
        self._filters: list[Callable[[InboundMessage], bool]] = []

    def add_filter(self, filter_fn: Callable[[InboundMessage], bool]):
        """添加消息过滤器，返回 False 的消息将被丢弃"""
        self._filters.append(filter_fn)

    async def publish_inbound(self, msg: InboundMessage) -> None:
        # 应用所有过滤器
        for filter_fn in self._filters:
            if not filter_fn(msg):
                return
        await self.inbound.put(msg)

# 使用示例
bus.add_filter(lambda msg: msg.sender_id in ALLOWED_USERS)
```

### 6.4 实现消息持久化

为了防止消息丢失，可以添加持久化支持：

```python
class MessageBus:
    def __init__(self, persistence_path: str):
        # ... 现有代码 ...
        self.persistence_path = persistence_path

    async def publish_inbound(self, msg: InboundMessage) -> None:
        # 持久化消息
        self._persist_message(msg)
        await self.inbound.put(msg)

    def _persist_message(self, msg: InboundMessage):
        with open(self.persistence_path, "a") as f:
            f.write(json.dumps(asdict(msg)) + "\n")
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/bus/queue.py](../../../nanobot/bus/queue.py) - 消息总线主文件（82 行）
- [nanobot/bus/events.py](../../../nanobot/bus/events.py) - 消息事件定义

### 依赖模块

- [nanobot/agent/loop.py](../../../nanobot/agent/loop.py) - 消息的主要消费者
- [nanobot/channels/manager.py](../../../nanobot/channels/manager.py) - 消息的生产者和分发者

### 相关文档

- [Agent 循环模块文档](agent-loop.md)
- [渠道管理器模块文档](channel-manager.md)

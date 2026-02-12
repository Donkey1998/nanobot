# 渠道管理器模块

> **文件位置**: [nanobot/channels/](../../../nanobot/channels/)
> **主要文件**: manager.py (162 行), base.py (128 行)
> **最后更新**: 2026-02-10

---

## 1. 概述

渠道管理器模块负责协调多个聊天平台适配器（Telegram、Discord、Feishu、WhatsApp），提供统一的接口将消息路由到正确的平台。

### 核心职责

- **渠道初始化**: 根据配置创建和初始化聊天平台适配器
- **消息路由**: 将出站消息分发到对应的渠道
- **生命周期管理**: 启动和停止所有渠道
- **权限控制**: 管理哪些用户可以与 Agent 交互

### 支持的平台

| 平台 | 文件 | 协议 | 说明 |
|------|------|------|------|
| **Telegram** | [telegram.py](../../../nanobot/channels/telegram.py) | Bot API | 最流行的聊天机器人平台 |
| **Discord** | [discord.py](../../../nanobot/channels/discord.py) | Gateway WebSocket | 游戏/社区聊天平台 |
| **Feishu** | [feishu.py](../../../nanobot/channels/feishu.py) | 长连接 WebSocket | 企业协作平台 |
| **WhatsApp** | [whatsapp.py](../../../nanobot/channels/whatsapp.py) | Node.js 桥接 | 即时通讯应用 |

### 相关模块

- [消息总线](message-bus.md) - 消息传递基础设施
- [Agent 循环](agent-loop.md) - 消息的处理者

---

## 2. 设计理念

### 2.1 适配器模式

每个聊天平台实现统一的 `BaseChannel` 接口，隐藏平台差异。

**代码位置**: [base.py:12-127](../../../nanobot/channels/base.py#L12-L127)

```python
class BaseChannel(ABC):
    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None: ...
```

### 2.2 统一消息模型

使用统一的 `InboundMessage` 和 `OutboundMessage` 数据模型，使渠道和 Agent 完全解耦。

### 2.3 权限白名单

通过 `allowFrom` 配置控制哪些用户可以与 Agent 交互，增强安全性。

**代码位置**: [base.py:61-84](../../../nanobot/channels/base.py#L61-L84)

```python
def is_allowed(self, sender_id: str) -> bool:
    allow_list = getattr(self.config, "allow_from", [])
    if not allow_list:
        return True  # 无白名单时允许所有人
    return str(sender_id) in allow_list
```

---

## 3. 核心机制

### 3.1 渠道初始化

`_init_channels()` 方法根据配置创建启用的渠道。

**代码位置**: [manager.py:32-79](../../../nanobot/channels/manager.py#L32-L79)

**流程**:
1. 检查每个渠道的 `enabled` 配置
2. 尝试导入渠道适配器
3. 创建渠道实例并传递配置
4. 添加到 `channels` 字典

### 3.2 消息路由

出站消息通过 `_dispatch_outbound()` 方法路由到对应的渠道。

**代码位置**: [manager.py:119-140](../../../nanobot/channels/manager.py#L119-L140)

**流程**:
1. 从消息总线消费出站消息
2. 根据 `msg.channel` 查找对应渠道
3. 调用渠道的 `send()` 方法
4. 捕获并记录错误

### 3.3 渠道生命周期

```
┌─────────────────────────────────────────────────────────┐
│                  ChannelManager                        │
├─────────────────────────────────────────────────────────┤
│  start_all()                                           │
│  ├─ 启动出站分发器 (asyncio.create_task)                │
│  └─ 启动所有渠道 (asyncio.gather)                       │
│       ├─ telegram.start() ────> 接收消息               │
│       ├─ discord.start()  ────> 接收消息               │
│       └─ feishu.start()   ────> 接收消息               │
│                                                          │
│  (所有渠道并发运行)                                      │
│                                                          │
│  stop_all()                                             │
│  ├─ 停止分发器                                          │
│  └─ 停止所有渠道                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 关键接口

### 4.1 BaseChannel 抽象类

#### 属性

```python
name: str = "base"  # 渠道标识符
```

#### 方法

```python
@abstractmethod
async def start(self) -> None:
    """启动渠道并开始监听消息"""

@abstractmethod
async def stop(self) -> None:
    """停止渠道并清理资源"""

@abstractmethod
async def send(self, msg: OutboundMessage) -> None:
    """发送消息到聊天平台"""

def is_allowed(self, sender_id: str) -> bool:
    """检查发送者是否有权限使用 bot"""

async def _handle_message(
    self,
    sender_id: str,
    chat_id: str,
    content: str,
    media: list[str] | None = None,
    metadata: dict[str, Any] | None = None
) -> None:
    """处理传入消息并转发到总线"""
```

### 4.2 ChannelManager

#### 构造函数

```python
def __init__(self, config: Config, bus: MessageBus):
    self.config = config
    self.bus = bus
    self.channels: dict[str, BaseChannel] = {}
    self._dispatch_task: asyncio.Task | None = None
    self._init_channels()
```

#### 方法

```python
async def start_all(self) -> None:
    """启动所有渠道和出站分发器"""

async def stop_all(self) -> None:
    """停止所有渠道和分发器"""

async def _dispatch_outbound(self) -> None:
    """将出站消息分发到相应的渠道（后台任务）"""

def get_channel(self, name: str) -> BaseChannel | None:
    """按名称获取渠道"""

def get_status(self) -> dict[str, Any]:
    """获取所有渠道的状态"""

@property
def enabled_channels(self) -> list[str]:
    """获取已启用的渠道名称列表"""
```

---

## 5. 使用示例

### 5.1 创建和使用渠道管理器

```python
import asyncio
from pathlib import Path
from nanobot.config.loader import load_config
from nanobot.bus.queue import MessageBus
from nanobot.channels.manager import ChannelManager

async def main():
    # 加载配置
    config = load_config()

    # 创建消息总线
    bus = MessageBus()

    # 创建渠道管理器
    channels = ChannelManager(config, bus)

    # 启动所有渠道（这会阻塞）
    await channels.start_all()

asyncio.run(main())
```

### 5.2 实现自定义渠道

```python
from nanobot.channels.base import BaseChannel
from nanobot.bus.events import InboundMessage, OutboundMessage

class CustomChannel(BaseChannel):
    name = "custom"

    async def start(self) -> None:
        """连接到自定义聊天平台"""
        self._running = True
        # 监听消息并调用 _handle_message()
        # await self._handle_message(sender_id, chat_id, content)

    async def stop(self) -> None:
        """断开连接"""
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        """发送消息到平台"""
        # 实现发送逻辑
        pass

# 注册到 manager.py 的 _init_channels()
if self.config.channels.custom.enabled:
    from nanobot.channels.custom import CustomChannel
    self.channels["custom"] = CustomChannel(
        self.config.channels.custom,
        self.bus
    )
```

### 5.3 渠道权限控制

```python
# 配置文件 config.json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "...",
      "allowFrom": ["123456", "789012"]  # 只允许这些用户
    }
  }
}
```

### 5.4 监控渠道状态

```python
# 获取渠道状态
status = channels.get_status()
print(status)
# 输出:
# {
#   "telegram": {"enabled": true, "running": true},
#   "discord": {"enabled": true, "running": true},
#   "whatsapp": {"enabled": false, "running": false}
# }
```

---

## 6. 扩展指南

### 6.1 添加新的聊天平台

1. **创建渠道类**：继承 `BaseChannel`
2. **实现抽象方法**：`start()`, `stop()`, `send()`
3. **添加配置模型**：在 `config/schema.py` 中添加配置类
4. **注册渠道**：在 `manager.py` 的 `_init_channels()` 中添加初始化代码

**示例模板**:

```python
# nanobot/channels/myservice.py
from typing import Any
from nanobot.channels.base import BaseChannel
from nanobot.bus.events import OutboundMessage

class MyServiceChannel(BaseChannel):
    name = "myservice"

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__(config, bus)
        self.api_key = config.api_key
        self._client = None

    async def start(self) -> None:
        """连接到 MyService"""
        self._client = await MyServiceClient.connect(self.api_key)

        @self._client.on_message
        async def handle_message(msg):
            await self._handle_message(
                sender_id=msg.sender_id,
                chat_id=msg.chat_id,
                content=msg.text,
                media=msg.attachments
            )

        self._running = True

    async def stop(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.disconnect()
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        """发送消息"""
        await self._client.send_message(
            chat_id=msg.chat_id,
            text=msg.content,
            attachments=msg.media
        )
```

### 6.2 添加消息格式转换

不同平台可能有不同的消息格式，可以在渠道中转换：

```python
class MarkdownChannel(BaseChannel):
    async def send(self, msg: OutboundMessage) -> None:
        # 转换 Markdown 到平台特定格式
        formatted = self._convert_markdown(msg.content)
        await self._client.send(msg.chat_id, formatted)

    def _convert_markdown(self, text: str) -> str:
        # 实现特定平台的 Markdown 转换
        pass
```

### 6.3 支持多模态消息

```python
async def send(self, msg: OutboundMessage) -> None:
    if msg.media:
        # 发送带媒体的消息
        for media_path in msg.media:
            await self._client.send_photo(
                chat_id=msg.chat_id,
                photo=media_path,
                caption=msg.content
            )
    else:
        # 发送纯文本消息
        await self._client.send_message(
            chat_id=msg.chat_id,
            text=msg.content
        )
```

### 6.4 添加命令处理

```python
class CommandChannel(BaseChannel):
    async def _handle_message(self, sender_id, chat_id, content, **kwargs):
        # 处理特殊命令
        if content.startswith("/"):
            await self._handle_command(sender_id, chat_id, content)
        else:
            # 转发到 Agent
            await super()._handle_message(sender_id, chat_id, content, **kwargs)

    async def _handle_command(self, sender_id, chat_id, command):
        if command == "/status":
            status = "Bot is running!"
            await self.bus.publish_outbound(OutboundMessage(
                channel=self.name,
                chat_id=chat_id,
                content=status
            ))
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/channels/manager.py](../../../nanobot/channels/manager.py) - 渠道管理器（162 行）
- [nanobot/channels/base.py](../../../nanobot/channels/base.py) - 渠道基类（128 行）
- [nanobot/channels/telegram.py](../../../nanobot/channels/telegram.py) - Telegram 适配器
- [nanobot/channels/discord.py](../../../nanobot/channels/discord.py) - Discord 适配器
- [nanobot/channels/feishu.py](../../../nanobot/channels/feishu.py) - 飞书适配器
- [nanobot/channels/whatsapp.py](../../../nanobot/channels/whatsapp.py) - WhatsApp 适配器

### 依赖模块

- [nanobot/bus/queue.py](../../../nanobot/bus/queue.py) - 消息总线
- [nanobot/config/schema.py](../../../nanobot/config/schema.py) - 配置模型

### 相关文档

- [消息总线模块文档](message-bus.md)
- [Agent 循环模块文档](agent-loop.md)
- [配置系统模块文档](config-system.md)

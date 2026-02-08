"""聊天平台的基础渠道接口。"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


class BaseChannel(ABC):
    """
    聊天渠道实现的抽象基类。

    每个渠道（Telegram、Discord 等）都应实现此接口
    以与 nanobot 消息总线集成。
    """
    
    name: str = "base"
    
    def __init__(self, config: Any, bus: MessageBus):
        """
        初始化渠道。

        Args:
            config: 特定于渠道的配置。
            bus: 用于通信的消息总线。
        """
        self.config = config
        self.bus = bus
        self._running = False
    
    @abstractmethod
    async def start(self) -> None:
        """
        启动渠道并开始监听消息。

        这应该是一个长期运行的异步任务：
        1. 连接到聊天平台
        2. 监听传入消息
        3. 通过 _handle_message() 将消息转发到总线
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止渠道并清理资源。"""
        pass

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """
        通过此渠道发送消息。

        Args:
            msg: 要发送的消息。
        """
        pass
    
    def is_allowed(self, sender_id: str) -> bool:
        """
        检查发送者是否被允许使用此 bot。

        Args:
            sender_id: 发送者的标识符。

        Returns:
            如果允许则为 True，否则为 False。
        """
        allow_list = getattr(self.config, "allow_from", [])

        # 如果没有允许列表，允许所有人
        if not allow_list:
            return True
        
        sender_str = str(sender_id)
        if sender_str in allow_list:
            return True
        if "|" in sender_str:
            for part in sender_str.split("|"):
                if part and part in allow_list:
                    return True
        return False
    
    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        处理来自聊天平台的传入消息。

        此方法检查权限并转发到总线。

        Args:
            sender_id: 发送者的标识符。
            chat_id: 聊天/渠道标识符。
            content: 消息文本内容。
            media: 可选的媒体 URL 列表。
            metadata: 可选的特定于渠道的元数据。
        """
        if not self.is_allowed(sender_id):
            logger.warning(
                f"Access denied for sender {sender_id} on channel {self.name}. "
                f"Add them to allowFrom list in config to grant access."
            )
            return
        
        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {}
        )
        
        await self.bus.publish_inbound(msg)
    
    @property
    def is_running(self) -> bool:
        """检查渠道是否正在运行。"""
        return self._running

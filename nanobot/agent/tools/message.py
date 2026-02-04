"""用于向用户发送消息的工具。"""

from typing import Any, Callable, Awaitable

from nanobot.agent.tools.base import Tool
from nanobot.bus.events import OutboundMessage


class MessageTool(Tool):
    """向聊天渠道的用户发送消息的工具。"""
    
    def __init__(
        self, 
        send_callback: Callable[[OutboundMessage], Awaitable[None]] | None = None,
        default_channel: str = "",
        default_chat_id: str = ""
    ):
        self._send_callback = send_callback
        self._default_channel = default_channel
        self._default_chat_id = default_chat_id
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """设置当前消息上下文。"""
        self._default_channel = channel
        self._default_chat_id = chat_id
    
    def set_send_callback(self, callback: Callable[[OutboundMessage], Awaitable[None]]) -> None:
        """设置发送消息的回调函数。"""
        self._send_callback = callback
    
    @property
    def name(self) -> str:
        return "message"
    
    @property
    def description(self) -> str:
        return "向用户发送消息。当你想要传达某些信息时使用此工具。"
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "要发送的消息内容"
                },
                "channel": {
                    "type": "string",
                    "description": "可选：目标渠道（telegram、discord 等）"
                },
                "chat_id": {
                    "type": "string",
                    "description": "可选：目标聊天/用户 ID"
                }
            },
            "required": ["content"]
        }
    
    async def execute(
        self, 
        content: str, 
        channel: str | None = None, 
        chat_id: str | None = None,
        **kwargs: Any
    ) -> str:
        channel = channel or self._default_channel
        chat_id = chat_id or self._default_chat_id
        
        if not channel or not chat_id:
            return "错误：未指定目标渠道/聊天"
        
        if not self._send_callback:
            return "错误：消息发送未配置"
        
        msg = OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=content
        )
        
        try:
            await self._send_callback(msg)
            return f"消息已发送到 {channel}:{chat_id}"
        except Exception as e:
            return f"发送消息错误：{str(e)}"

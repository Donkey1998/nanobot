"""使用 lark-oapi SDK 和 WebSocket 长连接实现的飞书/Lark 通道。"""

import asyncio
import json
import threading
from collections import OrderedDict
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import FeishuConfig

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest,
        CreateMessageRequestBody,
        CreateMessageReactionRequest,
        CreateMessageReactionRequestBody,
        Emoji,
        P2ImMessageReceiveV1,
    )
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False
    lark = None
    Emoji = None

# 消息类型显示映射
MSG_TYPE_MAP = {
    "image": "[image]",
    "audio": "[audio]",
    "file": "[file]",
    "sticker": "[sticker]",
}


class FeishuChannel(BaseChannel):
    """
    使用 WebSocket 长连接的飞书/Lark 通道。

    使用 WebSocket 接收事件 - 无需公网 IP 或 Webhook。

    需要以下配置：
    - 飞书开放平台的 App ID 和 App Secret
    - 已启用机器人能力
    - 已启用事件订阅 (im.message.receive_v1)
    """
    
    name = "feishu"
    
    def __init__(self, config: FeishuConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: FeishuConfig = config
        self._client: Any = None
        self._ws_client: Any = None
        self._ws_thread: threading.Thread | None = None
        self._processed_message_ids: OrderedDict[str, None] = OrderedDict()  # 有序去重缓存
        self._loop: asyncio.AbstractEventLoop | None = None
    
    async def start(self) -> None:
        """使用 WebSocket 长连接启动飞书机器人。"""
        if not FEISHU_AVAILABLE:
            logger.error("未安装飞书 SDK。请运行: pip install lark-oapi")
            return
        
        if not self.config.app_id or not self.config.app_secret:
            logger.error("未配置飞书的 app_id 和 app_secret")
            return
        
        self._running = True
        self._loop = asyncio.get_running_loop()
        
        # 创建 Lark 客户端用于发送消息
        self._client = lark.Client.builder() \
            .app_id(self.config.app_id) \
            .app_secret(self.config.app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # 创建事件处理器（仅注册消息接收，忽略其他事件）
        event_handler = lark.EventDispatcherHandler.builder(
            self.config.encrypt_key or "",
            self.config.verification_token or "",
        ).register_p2_im_message_receive_v1(
            self._on_message_sync
        ).build()
        
        # 创建 WebSocket 客户端用于长连接
        self._ws_client = lark.ws.Client(
            self.config.app_id,
            self.config.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO
        )
        
        # 在单独的线程中启动 WebSocket 客户端
        def run_ws():
            try:
                self._ws_client.start()
            except Exception as e:
                logger.error(f"飞书 WebSocket 错误: {e}")
        
        self._ws_thread = threading.Thread(target=run_ws, daemon=True)
        self._ws_thread.start()
        
        logger.info("飞书机器人已使用 WebSocket 长连接启动")
        logger.info("无需公网 IP - 使用 WebSocket 接收事件")
        
        # 保持运行直到停止
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """停止飞书机器人。"""
        self._running = False
        if self._ws_client:
            try:
                self._ws_client.stop()
            except Exception as e:
                logger.warning(f"停止 WebSocket 客户端时出错: {e}")
        logger.info("飞书机器人已停止")
    
    def _add_reaction_sync(self, message_id: str, emoji_type: str) -> None:
        """添加表情回应的同步辅助函数（在线程池中运行）。"""
        try:
            request = CreateMessageReactionRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    CreateMessageReactionRequestBody.builder()
                    .reaction_type(Emoji.builder().emoji_type(emoji_type).build())
                    .build()
                ).build()
            
            response = self._client.im.v1.message_reaction.create(request)
            
            if not response.success():
                logger.warning(f"添加表情失败: code={response.code}, msg={response.msg}")
            else:
                logger.debug(f"已为消息 {message_id} 添加 {emoji_type} 表情")
        except Exception as e:
            logger.warning(f"添加表情时出错: {e}")

    async def _add_reaction(self, message_id: str, emoji_type: str = "THUMBSUP") -> None:
        """
        为消息添加表情回应（非阻塞）。

        常用表情类型: THUMBSUP, OK, EYES, DONE, OnIt, HEART
        """
        if not self._client or not Emoji:
            return
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._add_reaction_sync, message_id, emoji_type)
    
    async def send(self, msg: OutboundMessage) -> None:
        """通过飞书发送消息。"""
        if not self._client:
            logger.warning("飞书客户端未初始化")
            return
        
        try:
            # 根据 chat_id 格式确定 receive_id_type
            # open_id 以 "ou_" 开头，chat_id 以 "oc_" 开头
            if msg.chat_id.startswith("oc_"):
                receive_id_type = "chat_id"
            else:
                receive_id_type = "open_id"
            
            # 构建文本消息内容
            content = json.dumps({"text": msg.content})
            
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(msg.chat_id)
                    .msg_type("text")
                    .content(content)
                    .build()
                ).build()
            
            response = self._client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(
                    f"发送飞书消息失败: code={response.code}, "
                    f"msg={response.msg}, log_id={response.get_log_id()}"
                )
            else:
                logger.debug(f"飞书消息已发送到 {msg.chat_id}")
                
        except Exception as e:
            logger.error(f"发送飞书消息时出错: {e}")
    
    def _on_message_sync(self, data: "P2ImMessageReceiveV1") -> None:
        """
        接收消息的同步处理器（从 WebSocket 线程调用）。
        在主事件循环中调度异步处理。
        """
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._on_message(data), self._loop)
    
    async def _on_message(self, data: "P2ImMessageReceiveV1") -> None:
        """处理来自飞书的接收消息。"""
        try:
            event = data.event
            message = event.message
            sender = event.sender
            
            # 去重检查
            message_id = message.message_id
            if message_id in self._processed_message_ids:
                return
            self._processed_message_ids[message_id] = None
            
            # 清理缓存：超过 1000 时保留最近 500 条
            while len(self._processed_message_ids) > 1000:
                self._processed_message_ids.popitem(last=False)
            
            # 跳过机器人消息
            sender_type = sender.sender_type
            if sender_type == "bot":
                return
            
            sender_id = sender.sender_id.open_id if sender.sender_id else "unknown"
            chat_id = message.chat_id
            chat_type = message.chat_type  # "p2p" or "group"
            msg_type = message.message_type
            
            # 添加表情表示"已读"
            await self._add_reaction(message_id, "THUMBSUP")
            
            # 解析消息内容
            if msg_type == "text":
                try:
                    content = json.loads(message.content).get("text", "")
                except json.JSONDecodeError:
                    content = message.content or ""
            else:
                content = MSG_TYPE_MAP.get(msg_type, f"[{msg_type}]")
            
            if not content:
                return
            
            # 转发到消息总线
            reply_to = chat_id if chat_type == "group" else sender_id
            await self._handle_message(
                sender_id=sender_id,
                chat_id=reply_to,
                content=content,
                metadata={
                    "message_id": message_id,
                    "chat_type": chat_type,
                    "msg_type": msg_type,
                }
            )
            
        except Exception as e:
            logger.error(f"处理飞书消息时出错: {e}")

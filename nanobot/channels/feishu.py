"""使用 lark-oapi SDK 和 WebSocket 长连接实现的飞书/Lark 通道。"""

import asyncio
import json
import re
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


def _extract_post_text(content_json: dict) -> str:
    """Extract plain text from Feishu post (rich text) message content.
    
    Supports two formats:
    1. Direct format: {"title": "...", "content": [...]}
    2. Localized format: {"zh_cn": {"title": "...", "content": [...]}}
    """
    def extract_from_lang(lang_content: dict) -> str | None:
        if not isinstance(lang_content, dict):
            return None
        title = lang_content.get("title", "")
        content_blocks = lang_content.get("content", [])
        if not isinstance(content_blocks, list):
            return None
        text_parts = []
        if title:
            text_parts.append(title)
        for block in content_blocks:
            if not isinstance(block, list):
                continue
            for element in block:
                if isinstance(element, dict):
                    tag = element.get("tag")
                    if tag == "text":
                        text_parts.append(element.get("text", ""))
                    elif tag == "a":
                        text_parts.append(element.get("text", ""))
                    elif tag == "at":
                        text_parts.append(f"@{element.get('user_name', 'user')}")
        return " ".join(text_parts).strip() if text_parts else None
    
    # Try direct format first
    if "content" in content_json:
        result = extract_from_lang(content_json)
        if result:
            return result
    
    # Try localized format
    for lang_key in ("zh_cn", "en_us", "ja_jp"):
        lang_content = content_json.get(lang_key)
        result = extract_from_lang(lang_content)
        if result:
            return result
    
    return ""


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
    
    # Regex to match markdown tables (header + separator + data rows)
    _TABLE_RE = re.compile(
        r"((?:^[ \t]*\|.+\|[ \t]*\n)(?:^[ \t]*\|[-:\s|]+\|[ \t]*\n)(?:^[ \t]*\|.+\|[ \t]*\n?)+)",
        re.MULTILINE,
    )

    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    _CODE_BLOCK_RE = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)

    @staticmethod
    def _parse_md_table(table_text: str) -> dict | None:
        """Parse a markdown table into a Feishu table element."""
        lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            return None
        split = lambda l: [c.strip() for c in l.strip("|").split("|")]
        headers = split(lines[0])
        rows = [split(l) for l in lines[2:]]
        columns = [{"tag": "column", "name": f"c{i}", "display_name": h, "width": "auto"}
                   for i, h in enumerate(headers)]
        return {
            "tag": "table",
            "page_size": len(rows) + 1,
            "columns": columns,
            "rows": [{f"c{i}": r[i] if i < len(r) else "" for i in range(len(headers))} for r in rows],
        }

    def _build_card_elements(self, content: str) -> list[dict]:
        """Split content into div/markdown + table elements for Feishu card."""
        elements, last_end = [], 0
        for m in self._TABLE_RE.finditer(content):
            before = content[last_end:m.start()]
            if before.strip():
                elements.extend(self._split_headings(before))
            elements.append(self._parse_md_table(m.group(1)) or {"tag": "markdown", "content": m.group(1)})
            last_end = m.end()
        remaining = content[last_end:]
        if remaining.strip():
            elements.extend(self._split_headings(remaining))
        return elements or [{"tag": "markdown", "content": content}]

    def _split_headings(self, content: str) -> list[dict]:
        """Split content by headings, converting headings to div elements."""
        protected = content
        code_blocks = []
        for m in self._CODE_BLOCK_RE.finditer(content):
            code_blocks.append(m.group(1))
            protected = protected.replace(m.group(1), f"\x00CODE{len(code_blocks)-1}\x00", 1)

        elements = []
        last_end = 0
        for m in self._HEADING_RE.finditer(protected):
            before = protected[last_end:m.start()].strip()
            if before:
                elements.append({"tag": "markdown", "content": before})
            level = len(m.group(1))
            text = m.group(2).strip()
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{text}**",
                },
            })
            last_end = m.end()
        remaining = protected[last_end:].strip()
        if remaining:
            elements.append({"tag": "markdown", "content": remaining})

        for i, cb in enumerate(code_blocks):
            for el in elements:
                if el.get("tag") == "markdown":
                    el["content"] = el["content"].replace(f"\x00CODE{i}\x00", cb)

        return elements or [{"tag": "markdown", "content": content}]

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
                    .msg_type("interactive")
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
            elif msg_type == "post":
                try:
                    content_json = json.loads(message.content)
                    content = _extract_post_text(content_json)
                except (json.JSONDecodeError, TypeError):
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

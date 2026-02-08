"""用于协调聊天渠道的渠道管理器。"""

import asyncio
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import Config


class ChannelManager:
    """
    管理聊天渠道并协调消息路由。

    职责：
    - 初始化启用的渠道（Telegram、WhatsApp 等）
    - 启动/停止渠道
    - 路由出站消息
    """
    
    def __init__(self, config: Config, bus: MessageBus):
        self.config = config
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None
        
        self._init_channels()
    
    def _init_channels(self) -> None:
        """根据配置初始化渠道。"""
        
        # Telegram channel
        if self.config.channels.telegram.enabled:
            try:
                from nanobot.channels.telegram import TelegramChannel
                self.channels["telegram"] = TelegramChannel(
                    self.config.channels.telegram,
                    self.bus,
                    groq_api_key=self.config.providers.groq.api_key,
                )
                logger.info("Telegram 渠道已启用")
            except ImportError as e:
                logger.warning(f"Telegram 渠道不可用：{e}")

        # WhatsApp channel
        if self.config.channels.whatsapp.enabled:
            try:
                from nanobot.channels.whatsapp import WhatsAppChannel
                self.channels["whatsapp"] = WhatsAppChannel(
                    self.config.channels.whatsapp, self.bus
                )
                logger.info("WhatsApp 渠道已启用")
            except ImportError as e:
                logger.warning(f"WhatsApp 渠道不可用：{e}")

        # Discord channel
        if self.config.channels.discord.enabled:
            try:
                from nanobot.channels.discord import DiscordChannel
                self.channels["discord"] = DiscordChannel(
                    self.config.channels.discord, self.bus
                )
                logger.info("Discord 渠道已启用")
            except ImportError as e:
                logger.warning(f"Discord 渠道不可用：{e}")

        # Feishu channel
        if self.config.channels.feishu.enabled:
            try:
                from nanobot.channels.feishu import FeishuChannel
                self.channels["feishu"] = FeishuChannel(
                    self.config.channels.feishu, self.bus
                )
                logger.info("Feishu 渠道已启用")
            except ImportError as e:
                logger.warning(f"Feishu 渠道不可用：{e}")
    
    async def start_all(self) -> None:
        """启动 WhatsApp 渠道和出站分发器。"""
        if not self.channels:
            logger.warning("没有启用的渠道")
            return
        
        # Start outbound dispatcher
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())
        
        # Start WhatsApp channel
        tasks = []
        for name, channel in self.channels.items():
            logger.info(f"Starting {name} channel...")
            tasks.append(asyncio.create_task(channel.start()))
        
        # Wait for all to complete (they should run forever)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all(self) -> None:
        """停止所有渠道和分发器。"""
        logger.info("正在停止所有渠道...")
        
        # Stop dispatcher
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        
        # Stop all channels
        for name, channel in self.channels.items():
            try:
                await channel.stop()
                logger.info(f"Stopped {name} channel")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
    
    async def _dispatch_outbound(self) -> None:
        """将出站消息分发到相应的渠道。"""
        logger.info("出站分发器已启动")
        
        while True:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_outbound(),
                    timeout=1.0
                )
                
                channel = self.channels.get(msg.channel)
                if channel:
                    try:
                        await channel.send(msg)
                    except Exception as e:
                        logger.error(f"发送到 {msg.channel} 时出错：{e}")
                else:
                    logger.warning(f"未知渠道：{msg.channel}")
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    
    def get_channel(self, name: str) -> BaseChannel | None:
        """按名称获取渠道。"""
        return self.channels.get(name)
    
    def get_status(self) -> dict[str, Any]:
        """获取所有渠道的状态。"""
        return {
            name: {
                "enabled": True,
                "running": channel.is_running
            }
            for name, channel in self.channels.items()
        }
    
    @property
    def enabled_channels(self) -> list[str]:
        """获取已启用的渠道名称列表。"""
        return list(self.channels.keys())

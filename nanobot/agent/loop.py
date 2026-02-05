"""Agent 循环：核心处理引擎。"""

import asyncio
import json
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.context import ContextBuilder
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.subagent import SubagentManager
from nanobot.session.manager import SessionManager
"""
AgentLoop 是 nanobot 的核心处理引擎，负责：

消息循环处理 - 从消息总线持续接收并处理消息
上下文构建 - 整合历史记录、记忆和技能
LLM 交互 - 调用大语言模型并处理响应
工具执行 - 执行 LLM 返回的工具调用
会话管理 - 维护对话历史和状态
子 Agent 协调 - 处理系统消息和子 agent 通信
"""

class AgentLoop:
    """
    Agent 循环是核心处理引擎。

    它：
    1. 从总线接收消息
    2. 使用历史、记忆、技能构建上下文
    3. 调用 LLM
    4. 执行工具调用
    5. 发回响应
    """
    
    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        brave_api_key: str | None = None
    ):
        # 核心依赖：消息总线（用于接收/发送消息）、LLM 提供者、工作空间路径
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        # 模型配置：未指定时使用提供者的默认模型
        self.model = model or provider.get_default_model()
        # 防止无限循环：单个消息处理的最大工具调用迭代次数
        self.max_iterations = max_iterations
        self.brave_api_key = brave_api_key

        # 上下文构建器：负责组装发送给 LLM 的消息（包含系统提示、历史、当前消息等）
        self.context = ContextBuilder(workspace)
        # 会话管理器：持久化存储每个会话的历史记录，实现跨请求的对话记忆
        self.sessions = SessionManager(workspace)
        # 工具注册表：管理所有可用工具（文件操作、Shell、Web 搜索等）
        self.tools = ToolRegistry()
        # 子 Agent 管理器：处理 spawn 工具创建的独立子 agent 实例
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            brave_api_key=brave_api_key,
        )

        self._running = False
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """
        注册默认工具集。

        这些工具构成了 agent 的基础能力：
        - 文件操作：读取、写入、编辑、列出目录
        - Shell 执行：运行命令行工具
        - Web 访问：搜索和抓取网页
        - 消息发送：主动发送消息到对话频道
        - 子 agent：创建独立的 agent 实例处理并行任务
        """
        # 文件系统工具：让 agent 能操作代码库
        self.tools.register(ReadFileTool())
        self.tools.register(WriteFileTool())
        self.tools.register(EditFileTool())
        self.tools.register(ListDirTool())

        # Shell 工具：执行命令（注意安全限制，限制在工作空间内）
        self.tools.register(ExecTool(working_dir=str(self.workspace)))

        # Web 工具：搜索和抓取（需要 Brave API key）
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())

        # 消息工具：让 agent 能主动发送消息（例如状态更新）
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)

        # 生成工具：创建子 agent 处理独立任务（例如后台运行、并行任务）
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)
    
    async def run(self) -> None:
        """运行 Agent 循环，处理来自总线的消息。"""
        self._running = True
        logger.info("Agent 循环已启动")

        # 主事件循环：持续监听消息总线
        while self._running:
            try:
                # 阻塞等待下一条入站消息，超时 1 秒以允许检查 _running 标志
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )

                # 处理消息并捕获异常，防止单条消息错误中断整个循环
                try:
                    response = await self._process_message(msg)
                    if response:
                        # 将处理结果发布到出站队列，由适配器层负责实际发送
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"处理消息时出错：{e}")
                    # 发送错误响应：即使出错也要给用户反馈
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"抱歉，我遇到了错误：{str(e)}"
                    ))
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环以检查 _running 标志
                continue
    
    def stop(self) -> None:
        """停止 Agent 循环。"""
        self._running = False
        logger.info("Agent 循环正在停止")
    
    async def _process_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        处理单条入站消息。

        Args:
            msg: 要处理的入站消息。

        Returns:
            响应消息，如果不需要响应则为 None。
        """
        # 处理系统消息（子 Agent 公布）
        # chat_id 包含原始的 "channel:chat_id" 用于路由返回
        if msg.channel == "system":
            return await self._process_system_message(msg)

        logger.info(f"正在处理来自 {msg.channel}:{msg.sender_id} 的消息")

        # ========== 会话管理 ==========
        # 获取或创建会话：每个 channel:chat_id 组合有独立的会话历史
        session = self.sessions.get_or_create(msg.session_key)

        # ========== 工具上下文更新 ==========
        # 某些工具需要知道当前消息的来源（例如 message 工具需要知道发送到哪个频道）
        message_tool = self.tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(msg.channel, msg.chat_id)

        spawn_tool = self.tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(msg.channel, msg.chat_id)

        # ========== 构建 LLM 上下文 ==========
        # 组装完整的消息列表：系统提示 + 历史记录 + 当前消息（包含媒体）
        messages = self.context.build_messages(
            history=session.get_history(),  # 从会话获取 LLM 格式的历史消息
            current_message=msg.content,
            media=msg.media if msg.media else None,  # 支持图片等多媒体内容
        )
        
        # ========== Agent 循环：LLM 与工具的迭代交互 ==========
        # 这个循环实现了 ReAct 模式：LLM 可以连续调用多个工具来完成复杂任务
        iteration = 0
        final_content = None

        while iteration < self.max_iterations:
            iteration += 1

            # 调用 LLM：传入当前消息上下文和可用工具定义
            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),  # 工具的 OpenAI Function Calling 格式定义
                model=self.model
            )

            # ========== 处理工具调用 ==========
            if response.has_tool_calls:
                # LLM 决定调用工具：将 assistant 消息（包含工具调用）添加到历史
                # 注意：OpenAI 格式要求 arguments 必须是 JSON 字符串
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)  # 必须是 JSON 字符串
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )

                # 执行所有工具调用
                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments)
                    logger.debug(f"Executing tool: {tool_call.name} with arguments: {args_str}")
                    # 异步执行工具并获取结果
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    # 将工具执行结果作为新的消息添加，LLM 可以基于结果继续决策
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
                # 循环继续：LLM 将看到工具结果，可以调用更多工具或给出最终答案
            else:
                # LLM 完成思考：不再调用工具，返回最终响应
                final_content = response.content
                break
        
        # 达到最大迭代次数时的兜底处理
        if final_content is None:
            final_content = "我已完成处理，但没有可提供的响应。"

        # ========== 持久化会话 ==========
        # 将对话添加到历史并保存，确保下次请求能获得完整的上下文
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content)
        self.sessions.save(session)

        # 返回出站消息，由消息总线路由到对应的适配器
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content
        )
    
    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        处理系统消息（例如，子 Agent 公布）。

        子 agent 通过系统频道返回结果，chat_id 字段编码了原始来源信息，
        格式为 "original_channel:original_chat_id"，以便将响应路由回正确的目标。

        设计理由：子 agent 独立运行，无法直接访问原始消息总线，因此通过
        系统频道中转，由主 agent 负责将结果路由回用户。
        """
        logger.info(f"正在处理来自 {msg.sender_id} 的系统消息")

        # ========== 解码原始消息来源 ==========
        # chat_id 格式："channel:chat_id"，需要解析以路由回正确的目标
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            # 兼容旧格式或错误格式，回退到 CLI
            origin_channel = "cli"
            origin_chat_id = msg.chat_id

        # 使用原始会话作为上下文，确保子 agent 的结果能访问完整对话历史
        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self.sessions.get_or_create(session_key)
        
        # Update tool contexts
        message_tool = self.tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(origin_channel, origin_chat_id)
        
        spawn_tool = self.tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(origin_channel, origin_chat_id)
        
        # Build messages with the announce content
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content
        )
        
        # Agent loop (limited for announce handling)
        iteration = 0
        final_content = None
        
        while iteration < self.max_iterations:
            iteration += 1
            
            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model
            )
            
            if response.has_tool_calls:
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )
                
                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments)
                    logger.debug(f"Executing tool: {tool_call.name} with arguments: {args_str}")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                final_content = response.content
                break
        
        if final_content is None:
            final_content = "后台任务已完成。"

        # 保存到会话（在历史中标记为系统消息）
        session.add_message("user", f"[系统：{msg.sender_id}] {msg.content}")
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content
        )
    
    async def process_direct(self, content: str, session_key: str = "cli:direct") -> str:
        """
        直接处理消息（用于 CLI 模式）。

        这个方法为命令行接口提供了简化的访问方式，绕过消息总线直接处理用户输入。
        相比消息总线模式，直接模式的延迟更低，适合交互式 CLI 使用场景。

        Args:
            content: 用户输入的消息内容。
            session_key: 会话标识符，默认为 "cli:direct"。

        Returns:
            Agent 的响应文本内容。
        """
        # 构造入站消息对象，模拟从消息总线接收的消息
        msg = InboundMessage(
            channel="cli",
            sender_id="user",
            chat_id="direct",
            content=content
        )

        # 复用核心消息处理逻辑
        response = await self._process_message(msg)
        return response.content if response else ""

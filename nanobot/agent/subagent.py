"""用于后台任务执行的子 Agent 管理器。"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool


class SubagentManager:
    """
    管理后台子 Agent 的执行。

    子 Agent 是在后台运行的轻量级 Agent 实例，
    用于处理特定任务。它们共享相同的 LLM 提供商，
    但拥有隔离的上下文和专注的系统提示。
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        bus: MessageBus,
        model: str | None = None,
        brave_api_key: str | None = None,
    ):
        self.provider = provider
        self.workspace = workspace
        self.bus = bus
        self.model = model or provider.get_default_model()
        self.brave_api_key = brave_api_key
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
    
    async def spawn(
        self,
        task: str,
        label: str | None = None,
        origin_channel: str = "cli",
        origin_chat_id: str = "direct",
    ) -> str:
        """
        生成子 Agent 在后台执行任务。

        Args:
            task: 子 Agent 的任务描述。
            label: 任务的可读标签。
            origin_channel: 用于公布结果的渠道。
            origin_chat_id: 用于公布结果的聊天 ID。

        Returns:
            表示子 Agent 已启动的状态消息。
        """
        task_id = str(uuid.uuid4())[:8]
        display_label = label or task[:30] + ("..." if len(task) > 30 else "")
        
        origin = {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        }
        
        # Create background task
        bg_task = asyncio.create_task(
            self._run_subagent(task_id, task, display_label, origin)
        )
        self._running_tasks[task_id] = bg_task
        
        # Cleanup when done
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))
        
        logger.info(f"已生成子 Agent [{task_id}]: {display_label}")
        return f"子 Agent [{display_label}] 已启动（id: {task_id}）。完成后我会通知你。"
    
    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
    ) -> None:
        """执行子 Agent 任务并公布结果。"""
        logger.info(f"子 Agent [{task_id}] 正在启动任务：{label}")
        
        try:
            # Build subagent tools (no message tool, no spawn tool)
            tools = ToolRegistry()
            tools.register(ReadFileTool())
            tools.register(WriteFileTool())
            tools.register(ListDirTool())
            tools.register(ExecTool(working_dir=str(self.workspace)))
            tools.register(WebSearchTool(api_key=self.brave_api_key))
            tools.register(WebFetchTool())
            
            # Build messages with subagent-specific prompt
            system_prompt = self._build_subagent_prompt(task)
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]
            
            # Run agent loop (limited iterations)
            max_iterations = 15
            iteration = 0
            final_result: str | None = None
            
            while iteration < max_iterations:
                iteration += 1
                
                response = await self.provider.chat(
                    messages=messages,
                    tools=tools.get_definitions(),
                    model=self.model,
                )
                
                if response.has_tool_calls:
                    # Add assistant message with tool calls
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": tool_call_dicts,
                    })
                    
                    # Execute tools
                    for tool_call in response.tool_calls:
                        logger.debug(f"Subagent [{task_id}] executing: {tool_call.name}")
                        result = await tools.execute(tool_call.name, tool_call.arguments)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.name,
                            "content": result,
                        })
                else:
                    final_result = response.content
                    break
            
            if final_result is None:
                final_result = "任务已完成，但未生成最终响应。"

            logger.info(f"子 Agent [{task_id}] 已成功完成")
            await self._announce_result(task_id, label, task, final_result, origin, "ok")
            
        except Exception as e:
            error_msg = f"错误：{str(e)}"
            logger.error(f"子 Agent [{task_id}] 失败：{e}")
            await self._announce_result(task_id, label, task, error_msg, origin, "error")
    
    async def _announce_result(
        self,
        task_id: str,
        label: str,
        task: str,
        result: str,
        origin: dict[str, str],
        status: str,
    ) -> None:
        """通过消息总线向主 Agent 公布子 Agent 的结果。"""
        status_text = "成功完成" if status == "ok" else "失败"
        
        announce_content = f"""[子 Agent '{label}' {status_text}]

任务：{task}

结果：
{result}

请为用户自然地总结一下。保持简短（1-2 句话）。不要提及"子 Agent"或任务 ID 等技术细节。"""
        
        # Inject as system message to trigger main agent
        msg = InboundMessage(
            channel="system",
            sender_id="subagent",
            chat_id=f"{origin['channel']}:{origin['chat_id']}",
            content=announce_content,
        )

        await self.bus.publish_inbound(msg)
        logger.debug(f"子 Agent [{task_id}] 已向 {origin['channel']}:{origin['chat_id']} 公布结果")

    def _build_subagent_prompt(self, task: str) -> str:
        """为子 Agent 构建专注的系统提示。"""
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
    
    def get_running_count(self) -> int:
        """返回当前运行的子 Agent 数量。"""
        return len(self._running_tasks)

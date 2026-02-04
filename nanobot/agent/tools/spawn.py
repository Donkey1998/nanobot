"""用于创建后台子 Agent 的生成工具。"""

from typing import Any, TYPE_CHECKING

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager


class SpawnTool(Tool):
    """
    生成子 Agent 以执行后台任务的工具。

    子 Agent 异步运行，并在完成时将其结果
    通知回主 Agent。
    """
    
    def __init__(self, manager: "SubagentManager"):
        self._manager = manager
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """设置子 Agent 通知的原始上下文。"""
        self._origin_channel = channel
        self._origin_chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "spawn"
    
    @property
    def description(self) -> str:
        return (
            "生成一个子 Agent 在后台处理任务。"
            "用于可以独立运行的复杂或耗时任务。"
            "子 Agent 将完成任务并在完成时报告。"
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "子 Agent 要完成的任务",
                },
                "label": {
                    "type": "string",
                    "description": "任务的可选简短标签（用于显示）",
                },
            },
            "required": ["task"],
        }
    
    async def execute(self, task: str, label: str | None = None, **kwargs: Any) -> str:
        """生成一个子 Agent 来执行给定任务。"""
        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )

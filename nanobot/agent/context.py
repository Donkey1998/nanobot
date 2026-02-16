-"""用于组装 Agent 提示的上下文构建器。"""

import base64
import mimetypes
import platform
from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.skills import SkillsLoader


class ContextBuilder:
    """
    为 Agent 构建上下文（系统提示 + 消息）。

    将引导文件、记忆、技能和对话历史
    组装成给 LLM 的连贯提示。
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
    
    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """
        从引导文件、记忆和技能构建系统提示。

        Args:
            skill_names: 要包含的可选技能列表。

        Returns:
            完整的系统提示。
        """
        parts = []
        
        # Core identity
        parts.append(self._get_identity())
        
        # Bootstrap files  ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
        
        # Memory context
        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")
        
        # Skills - progressive loading
        # 1. Always-loaded skills: include full content
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")
        
        # 2. Available skills: only show summary (agent uses read_file to load)
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

以下技能扩展了你的能力。要使用技能，请使用 read_file 工具读取其 SKILL.md 文件。
available="false" 的技能需要先安装依赖项 - 你可以尝试使用 apt/brew 安装它们。

{skills_summary}""")
            
        print (parts)
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """获取核心身份部分。"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# nanobot 🐈

你是 nanobot，一个有用的 AI 助手。你可以使用以下工具：
- 读取、写入和编辑文件
- 执行 Shell 命令
- 搜索网络和获取网页
- 向聊天渠道的用户发送消息
- 为复杂的后台任务生成子 Agent

## 当前时间
{now}

## 运行环境
{runtime}

## 工作区
你的工作区位于：{workspace_path}
- 记忆文件：{workspace_path}/memory/MEMORY.md
- 每日笔记：{workspace_path}/memory/YYYY-MM-DD.md
- 自定义技能：{workspace_path}/skills/{{skill-name}}/SKILL.md

重要提示：当响应直接问题或对话时，直接用你的文本响应。
仅当需要向特定聊天渠道（如 WhatsApp）发送消息时，才使用 'message' 工具。
对于正常对话，只需用文本响应 - 不要调用 message 工具。

始终保持有用、准确和简洁。使用工具时，解释你在做什么。
记住某些内容时，请写入 {workspace_path}/memory/MEMORY.md"""
    
    def _load_bootstrap_files(self) -> str:
        """从工作区加载所有引导文件。"""
        parts = []
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        为 LLM 调用构建完整的消息列表。

        Args:
            history: 之前的对话消息。
            current_message: 新的用户消息。
            skill_names: 要包含的可选技能。
            media: 图像/媒体的本地文件路径的可选列表。
            channel: 当前渠道（telegram、feishu 等）。
            chat_id: 当前聊天/用户 ID。

        Returns:
            包括系统提示的消息列表。
        """
        messages = []

        # System prompt
        system_prompt = self.build_system_prompt(skill_names)
        if channel and chat_id:
            system_prompt += f"\n\n## Current Session\nChannel: {channel}\nChat ID: {chat_id}"
        messages.append({"role": "system", "content": system_prompt})

        # History
        messages.extend(history)

        # Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """构建用户消息内容，可包含 base64 编码的图像。"""
        if not media:
            return text
        
        images = []
        for path in media:
            p = Path(path)
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        
        if not images:
            return text
        return images + [{"type": "text", "text": text}]
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """
        将工具结果添加到消息列表。

        Args:
            messages: 当前消息列表。
            tool_call_id: 工具调用的 ID。
            tool_name: 工具名称。
            result: 工具执行结果。

        Returns:
            更新后的消息列表。
        """
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        将助手消息添加到消息列表。

        Args:
            messages: 当前消息列表。
            content: 消息内容。
            tool_calls: 可选的工具调用。

        Returns:
            更新后的消息列表。
        """
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
        
        messages.append(msg)
        return messages

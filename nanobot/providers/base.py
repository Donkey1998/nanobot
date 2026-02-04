"""基础 LLM 提供商接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRequest:
    """来自 LLM 的工具调用请求。"""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 提供商的响应。"""
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    
    @property
    def has_tool_calls(self) -> bool:
        """检查响应是否包含工具调用。"""
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    LLM 提供商的抽象基类。

    实现应处理每个提供商 API 的细节，
    同时保持一致的接口。
    """
    
    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        self.api_base = api_base
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        发送聊天完成请求。

        Args:
            messages: 包含 'role' 和 'content' 的消息字典列表。
            tools: 可选的工具定义列表。
            model: 模型标识符（特定于提供商）。
            max_tokens: 响应中的最大令牌数。
            temperature: 采样温度。

        Returns:
            包含内容和/或工具调用的 LLMResponse。
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """获取此提供商的默认模型。"""
        pass

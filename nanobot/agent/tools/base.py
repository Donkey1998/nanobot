"""Agent 工具的基类。"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    Agent 工具的抽象基类。

    工具是 Agent 可以用来与环境交互的能力，
    例如读取文件、执行命令等。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """函数调用中使用的工具名称。"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具功能的描述。"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """工具参数的 JSON Schema。"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """
        使用给定参数执行工具。

        Args:
            **kwargs: 工具特定的参数。

        Returns:
            工具执行的字符串结果。
        """
        pass
    
    def to_schema(self) -> dict[str, Any]:
        """将工具转换为 OpenAI 函数 Schema 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

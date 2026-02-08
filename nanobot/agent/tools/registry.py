"""用于动态工具管理的工具注册表。"""

from typing import Any

from nanobot.agent.tools.base import Tool


class ToolRegistry:
    """
    代理工具注册表。

    允许动态注册和执行工具。
    """
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """注册一个工具。"""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """按名称注销工具。"""
        self._tools.pop(name, None)
    
    def get(self, name: str) -> Tool | None:
        """按名称获取工具。"""
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """检查工具是否已注册。"""
        return name in self._tools
    
    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI 格式定义。"""
        return [tool.to_schema() for tool in self._tools.values()]
    
    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """
        使用给定参数按名称执行工具。

        Args:
            name: 工具名称。
            params: 工具参数。

        Returns:
            工具执行结果字符串。

        Raises:
            KeyError: 如果找不到工具。
        """
        tool = self._tools.get(name)
        if not tool:
            return f"错误：未找到工具 '{name}'"


        try:
            errors = tool.validate_params(params)
            if errors:
                return f"错误：工具 '{name}' 的参数无效：" + "; ".join(errors)
            return await tool.execute(**params)
        except Exception as e:
            return f"执行 {name} 时出错: {str(e)}"
    
    @property
    def tool_names(self) -> list[str]:
        """获取已注册工具名称列表。"""
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools

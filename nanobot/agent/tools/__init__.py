"""Agent tools module."""

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.registry import ToolRegistry

# Optional browser tool (requires playwright)
try:
    from nanobot.agent.tools.browser import BrowserTool
    _browser_available = True
except ImportError:
    _browser_available = False

__all__ = ["Tool", "ToolRegistry"]

if _browser_available:
    __all__.append("BrowserTool")

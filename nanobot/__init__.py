"""
nanobot - A lightweight AI agent framework
"""

__version__ = "0.1.0"
__logo__ = "🐈"
__all__ = []

# Browser automation module (optional, requires playwright)
try:
    from nanobot import browser
    __all__.append("browser")
except ImportError:
    pass

"""Nanobot 浏览器自动化模块。"""

from nanobot.browser.session import BrowserSession
from nanobot.browser.snapshot import PageSnapshot
from nanobot.browser.actions import BrowserActions
from nanobot.browser.permissions import PermissionDenied, check_domain_allowed

__all__ = [
    "BrowserSession",
    "PageSnapshot",
    "BrowserActions",
    "PermissionDenied",
    "check_domain_allowed",
]

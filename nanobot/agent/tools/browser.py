"""Nanobot 浏览器自动化工具。"""

import json
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.browser.actions import BrowserActions, ElementNotFoundError, BrowserTimeoutError
from nanobot.browser.adapters import perform_login, LoginResult
from nanobot.browser.permissions import PermissionDenied, normalize_domain
from nanobot.browser.session import BrowserSession
from nanobot.browser.snapshot import PageSnapshot
from nanobot.config.schema import Config


class BrowserTool(Tool):
    """浏览器自动化工具,用于网页交互。

    提供以下功能:
    - 启动/停止浏览器会话
    - 导航到 URL
    - 截取页面快照
    - 点击元素和输入文本
    - 执行登录

    需要在配置中设置 `browser.enabled=true`。
    """

    name = "browser"
    description = (
        "自动化浏览器控制。导航网站、截取快照、"
        "点击元素、输入文本和执行登录。"
        "URL 需要在配置的白名单中。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "stop", "navigate", "snapshot", "click", "type", "login"],
                "description": "要执行的操作",
            },
            "url": {"type": "string", "description": "导航或登录操作的 URL"},
            "locator": {"type": "string", "description": "点击/输入操作的元素定位器"},
            "text": {"type": "string", "description": "要输入的文本"},
            "strategy": {
                "type": "string",
                "enum": ["auto", "aria", "id", "testid", "css", "text"],
                "default": "auto",
                "description": "元素定位策略",
            },
            "loginStrategy": {
                "type": "string",
                "enum": ["auto", "adapter", "generic", "manual"],
                "default": "auto",
                "description": "登录策略",
            },
            "username": {"type": "string", "description": "登录用户名"},
            "password": {"type": "string", "description": "登录密码"},
        },
        "required": ["action"],
    }

    def __init__(self, config: Config):
        """初始化浏览器工具。

        Args:
            config: Nanobot 配置
        """
        self.config = config
        self._session: BrowserSession | None = None

    async def execute(self, action: str, **kwargs: Any) -> str:
        """执行浏览器操作。

        Args:
            action: 要执行的操作
            **kwargs: 操作特定的参数

        Returns:
            JSON 格式的结果字符串
        """
        try:
            if action == "start":
                return await self._start_browser()
            elif action == "stop":
                return await self._stop_browser()
            elif action == "navigate":
                return await self._navigate(**kwargs)
            elif action == "snapshot":
                return await self._snapshot(**kwargs)
            elif action == "click":
                return await self._click(**kwargs)
            elif action == "type":
                return await self._type(**kwargs)
            elif action == "login":
                return await self._login(**kwargs)
            else:
                return json.dumps({"error": f"未知的操作: {action}"})
        except PermissionDenied as e:
            return json.dumps({"error": str(e), "errorType": "PermissionDenied"})
        except ElementNotFoundError as e:
            return json.dumps({"error": str(e), "errorType": "ElementNotFound"})
        except BrowserTimeoutError as e:
            return json.dumps({"error": str(e), "errorType": "Timeout"})
        except Exception as e:
            return json.dumps({"error": str(e), "errorType": "Unknown"})

    async def _start_browser(self) -> str:
        """启动浏览器会话。"""
        if self._session and self._session.is_started:
            return json.dumps({"status": "already_started", "message": "浏览器已在运行"})

        # 获取域名的配置文件目录
        profile_dir = self.config.browser.profile_dir

        self._session = BrowserSession(
            allowed_domains=self.config.browser.allowed_domains,
            headless=self.config.browser.headless,
            timeout=self.config.browser.timeout,
            profile_dir=profile_dir,
        )

        await self._session.start()

        return json.dumps({
            "status": "started",
            "message": "浏览器启动成功",
            "headless": self.config.browser.headless,
        })

    async def _stop_browser(self) -> str:
        """停止浏览器会话。"""
        if not self._session or not self._session.is_started:
            return json.dumps({"status": "not_started", "message": "浏览器未运行"})

        await self._session.stop()
        self._session = None

        return json.dumps({"status": "stopped", "message": "浏览器已成功停止"})

    async def _navigate(self, url: str, **kwargs: Any) -> str:
        """导航到 URL。"""
        self._ensure_session()

        await self._session.navigate(url)

        return json.dumps({
            "status": "success",
            "message": f"已导航到 {url}",
            "url": self._session.page.url,
        })

    async def _snapshot(self, **kwargs: Any) -> str:
        """截取页面快照。"""
        self._ensure_session()

        snapshot = PageSnapshot(self._session.page, timeout=self.config.browser.timeout)
        tree = await snapshot.get_tree()
        text = tree.to_text()

        # 获取可交互元素
        elements = await snapshot.get_interactive_elements()

        return json.dumps({
            "status": "success",
            "url": self._session.page.url,
            "tree": text,
            "interactiveElements": elements,
            "elementCount": len(elements),
        }, ensure_ascii=False)

    async def _click(self, locator: str, strategy: str = "auto", **kwargs: Any) -> str:
        """点击元素。"""
        self._ensure_session()

        actions = BrowserActions(self._session.page, timeout=self.config.browser.timeout)
        await actions.click(locator, strategy=strategy)

        return json.dumps({
            "status": "success",
            "message": f"已点击 {locator}",
            "url": self._session.page.url,
        })

    async def _type(self, locator: str, text: str, strategy: str = "auto", **kwargs: Any) -> str:
        """在元素中输入文本。"""
        self._ensure_session()

        actions = BrowserActions(self._session.page, timeout=self.config.browser.timeout)
        await actions.type_text(locator, text, strategy=strategy)

        return json.dumps({
            "status": "success",
            "message": f"已在 {locator} 中输入文本",
        })

    async def _login(
        self,
        url: str,
        strategy: str = "auto",
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> str:
        """执行登录。"""
        self._ensure_session()

        # 检查是否有存储的凭据
        if username is None or password is None:
            from nanobot.browser.credentials import CredentialManager
            mgr = CredentialManager(self.config.browser.credentials_path)

            domain = normalize_domain(url)
            creds = mgr.list_credentials(domain)

            if creds and len(creds) == 1:
                # 使用存储的凭据
                cred = creds[0]
                stored_password = mgr.get(cred.domain, cred.username)
                if stored_password:
                    username = cred.username
                    password = stored_password

        # 执行登录
        result: LoginResult = await perform_login(
            self._session,
            url,
            username,
            password,
            strategy,
        )

        return json.dumps({
            "status": result.status.value,
            "message": result.message,
            "requiredFields": result.required_fields,
            "suggestedStrategy": result.suggested_strategy,
        })

    def _ensure_session(self) -> None:
        """确保浏览器会话处于活动状态。"""
        if not self._session or not self._session.is_started:
            raise RuntimeError("浏览器未启动。请先调用 browser action=start。")

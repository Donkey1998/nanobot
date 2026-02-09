"""浏览器会话管理。"""

import asyncio
from pathlib import Path
from typing import Literal

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from nanobot.browser.permissions import require_domain_allowed


class BrowserTimeoutError(Exception):
    """当浏览器操作超时时抛出。"""

    pass


class BrowserSession:
    """管理具有持久配置文件的浏览器会话。

    每个会话维护自己的浏览器上下文,具有单独的 cookies、
    localStorage 等。会话基于域持久化到磁盘。

    示例:
        >>> async with BrowserSession(config) as session:
        ...     await session.navigate("https://mail.qq.com")
        ...     snapshot = await session.snapshot()
    """

    def __init__(
        self,
        allowed_domains: list[str],
        headless: bool = True,
        timeout: int = 30000,
        profile_dir: str | Path | None = None,
        user_data_dir: str | Path | None = None,
    ) -> None:
        """初始化浏览器会话。

        Args:
            allowed_domains: 允许的域模式白名单
            headless: 在无头模式下运行浏览器(无 GUI)
            timeout: 操作的默认超时时间(毫秒)
            profile_dir: 浏览器配置文件的基本目录(默认: ~/.nanobot/browser-profiles/)
            user_data_dir: 此会话的特定用户数据目录(可选)
        """
        self.allowed_domains = allowed_domains
        self.headless = headless
        self.timeout = timeout
        self._profile_dir = Path(profile_dir) if profile_dir else Path.home() / ".nanobot" / "browser-profiles"
        self._user_data_dir = Path(user_data_dir) if user_data_dir else None

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._started = False

    @property
    def is_started(self) -> bool:
        """检查浏览器会话是否已启动。"""
        return self._started

    async def start(self) -> None:
        """启动浏览器会话。

        Raises:
            BrowserTimeoutError: 如果浏览器在超时内未能启动
        """
        if self._started:
            return

        try:
            self._playwright = await asyncio.wait_for(
                async_playwright().start(),
                timeout=self.timeout / 1000,
            )
            self._browser = await asyncio.wait_for(
                self._playwright.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox"] if self.headless else [],
                ),
                timeout=self.timeout / 1000,
            )

            # 创建具有持久存储的上下文(如果指定)
            context_args: dict = {}
            if self._user_data_dir:
                self._user_data_dir.mkdir(parents=True, exist_ok=True)
                context_args["user_data_dir"] = str(self._user_data_dir)

            self._context = await self._browser.new_context(**context_args)
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.timeout / 1000)
            self._started = True

        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError("Failed to start browser within timeout") from exc

    async def stop(self) -> None:
        """停止浏览器会话并保存状态。

        关闭浏览器并持久化 cookies、localStorage 等。
        """
        if not self._started:
            return

        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._started = False

    async def __aenter__(self) -> "BrowserSession":
        """异步上下文管理器入口。"""
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        """异步上下文管理器出口。"""
        await self.stop()

    async def navigate(
        self,
        url: str,
        wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load",
    ) -> None:
        """导航到 URL。

        Args:
            url: 要导航到的 URL
            wait_until: 何时认为导航成功

        Raises:
            PermissionDenied: 如果 URL 域不在白名单中
            BrowserTimeoutError: 如果导航超时
        """
        if not self._started:
            raise RuntimeError("Browser session not started. Call start() first.")

        # 检查权限
        require_domain_allowed(url, self.allowed_domains)

        try:
            # 使用显式超时导航(Playwright 使用毫秒)
            await self._page.goto(url, wait_until=wait_until, timeout=self.timeout)
        except Exception as exc:
            # Playwright 的 TimeoutError 具有不同的消息格式
            if "Timeout" in str(exc):
                raise BrowserTimeoutError(f"Navigation to {url} timed out") from exc
            raise

    async def wait_for_load_state(self, state: Literal["load", "domcontentloaded", "networkidle"] = "networkidle") -> None:
        """等待特定的加载状态。

        Args:
            state: 要等待的加载状态
        """
        if not self._page:
            raise RuntimeError("Browser session not started")

        await self._page.wait_for_load_state(state)

    @property
    def page(self) -> Page:
        """获取活动页面对象。

        Returns:
            Playwright Page 对象

        Raises:
            RuntimeError: 如果会话未启动
        """
        if not self._page:
            raise RuntimeError("Browser session not started")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """获取浏览器上下文。

        Returns:
            Playwright BrowserContext 对象

        Raises:
            RuntimeError: 如果会话未启动
        """
        if not self._context:
            raise RuntimeError("Browser session not started")
        return self._context

    @classmethod
    def get_profile_path(cls, domain: str, base_dir: str | Path | None = None) -> Path:
        """获取特定域的配置文件路径。

        Args:
            domain: 域名(例如 "mail.qq.com")
            base_dir: 配置文件的基本目录(默认: ~/.nanobot/browser-profiles/)

        Returns:
            配置文件目录的路径
        """
        base = Path(base_dir) if base_dir else Path.home() / ".nanobot" / "browser-profiles"
        return base / domain

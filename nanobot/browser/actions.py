"""用于与页面交互的浏览器操作。"""

from typing import Any

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from nanobot.browser.session import BrowserTimeoutError


class ElementNotFoundError(Exception):
    """当页面上找不到元素时抛出。"""

    def __init__(self, locator: str, reason: str = "Element not found") -> None:
        self.locator = locator
        self.reason = reason
        super().__init__(f"Element not found: {locator} - {reason}")


class ElementNotInteractableError(Exception):
    """当元素找到但无法交互时抛出。"""

    def __init__(self, locator: str, reason: str = "Element not interactable") -> None:
        self.locator = locator
        self.reason = reason
        super().__init__(f"Element not interactable: {locator} - {reason}")


class BrowserActions:
    """执行浏览器操作,如点击、输入、等待等。

    支持多种元素定位策略:
    - ARIA 标签(对于动态应用最稳定)
    - id 属性
    - data-testid 属性
    - CSS 选择器
    - 文本内容

    示例:
        >>> actions = BrowserActions(page, timeout=30000)
        >>> await actions.click("Login button")
        >>> await actions.type("Email input", "user@example.com")
        >>> await actions.wait_for_element("Welcome message")
    """

    def __init__(self, page: Page, timeout: int = 30000) -> None:
        """初始化浏览器操作。

        Args:
            page: Playwright Page 对象
            timeout: 操作的默认超时时间(毫秒)
        """
        self.page = page
        self.timeout = timeout

    async def click(
        self,
        locator: str,
        strategy: str = "auto",
        wait_for_navigation: bool = True,
    ) -> None:
        """点击页面上的元素。

        Args:
            locator: 元素标识符(取决于策略)
            strategy: 定位策略: "auto", "aria", "id", "testid", "css", "text"
            wait_for_navigation: 点击后是否等待导航

        Raises:
            ElementNotFoundError: 如果找不到元素
            ElementNotInteractableError: 如果元素无法交互
            BrowserTimeoutError: 如果操作超时
        """
        element = await self._find_element(locator, strategy)

        try:
            if wait_for_navigation:
                async with self.page.expect_navigation(timeout=self.timeout / 1000):
                    await element.click(timeout=self.timeout / 1000)
            else:
                await element.click(timeout=self.timeout / 1000)
        except PlaywrightTimeoutError as exc:
            raise BrowserTimeoutError(f"Click on '{locator}' timed out") from exc

    async def type_text(
        self,
        locator: str,
        text: str,
        strategy: str = "auto",
        clear_first: bool = True,
    ) -> None:
        """在输入字段中输入文本。

        Args:
            locator: 元素标识符
            text: 要输入的文本
            strategy: 定位策略
            clear_first: 输入前是否清除现有文本

        Raises:
            ElementNotFoundError: 如果找不到元素
            BrowserTimeoutError: 如果操作超时
        """
        element = await self._find_element(locator, strategy)

        try:
            if clear_first:
                await element.clear(timeout=self.timeout / 1000)

            # 使用正确的事件输入,确保框架捕获输入
            await element.fill(text, timeout=self.timeout / 1000)
            await element.dispatch_event("input")
            await element.dispatch_event("change")

        except PlaywrightTimeoutError as exc:
            raise BrowserTimeoutError(f"Type into '{locator}' timed out") from exc

    async def wait_for_element(
        self,
        locator: str,
        strategy: str = "auto",
        state: str = "visible",
    ) -> None:
        """等待元素出现在页面上。

        Args:
            locator: 元素标识符
            strategy: 定位策略
            state: 元素状态: "visible", "attached", "hidden", "detached"

        Raises:
            BrowserTimeoutError: 如果元素在超时时间内未出现
        """
        selector = self._build_selector(locator, strategy)

        try:
            await self.page.wait_for_selector(
                selector,
                state=state,
                timeout=self.timeout / 1000,
            )
        except PlaywrightTimeoutError as exc:
            raise BrowserTimeoutError(f"Element '{locator}' did not reach state '{state}'") from exc

    async def get_text(
        self,
        locator: str,
        strategy: str = "auto",
    ) -> str:
        """从元素中提取文本内容。

        Args:
            locator: 元素标识符
            strategy: 定位策略

        Returns:
            文本内容(去除空白)

        Raises:
            ElementNotFoundError: 如果找不到元素
            BrowserTimeoutError: 如果操作超时
        """
        element = await self._find_element(locator, strategy)

        try:
            text = await element.inner_text(timeout=self.timeout / 1000)
            return " ".join(text.split())  # 去除空白
        except PlaywrightTimeoutError as exc:
            raise BrowserTimeoutError(f"Get text from '{locator}' timed out") from exc

    async def _find_element(self, locator: str, strategy: str):
        """使用指定策略查找元素。

        Args:
            locator: 元素标识符
            strategy: 定位策略

        Returns:
            Playwright ElementHandle

        Raises:
            ElementNotFoundError: 如果找不到元素
            BrowserTimeoutError: 如果搜索超时
        """
        selector = self._build_selector(locator, strategy)

        try:
            element = await self.page.wait_for_selector(
                selector,
                state="attached",
                timeout=self.timeout / 1000,
            )
        except PlaywrightTimeoutError as exc:
            # 提供有用的错误消息
            raise ElementNotFoundError(
                locator,
                f"Could not find element using {strategy} strategy",
            ) from exc

        if element is None:
            raise ElementNotFoundError(locator, f"Element not found using {strategy} strategy")

        return element

    def _build_selector(self, locator: str, strategy: str) -> str:
        """从定位符和策略构建 CSS 选择器。

        Args:
            locator: 元素标识符
            strategy: 定位策略

        Returns:
            CSS 选择器字符串
        """
        if strategy == "aria":
            # ARIA 标签: [aria-label="Login"]
            return f'[aria-label="{locator}"]'
        elif strategy == "id":
            # ID: #login-button
            return f"#{locator}"
        elif strategy == "testid":
            # data-testid: [data-testid="login-button"]
            return f'[data-testid="{locator}"]'
        elif strategy == "text":
            # 文本内容: :text("Login")
            return f':text("{locator}")'
        elif strategy == "css":
            # 直接 CSS 选择器
            return locator
        elif strategy == "auto":
            # 按顺序尝试多种策略
            return self._auto_selector(locator)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _auto_selector(self, locator: str) -> str:
        """自动检测最佳选择器策略。

        Args:
            locator: 元素标识符

        Returns:
            CSS 选择器
        """
        # 如果看起来像 CSS (包含 ., #, [, >, +, ~, :)
        if any(c in locator for c in [".", "#", "[", ">", "+", "~", ":"]):
            return locator

        # 首先尝试 aria-label(对于动态应用最稳定)
        return f'[aria-label="{locator}"], [data-testid="{locator}"], #{locator}, :text("{locator}")'

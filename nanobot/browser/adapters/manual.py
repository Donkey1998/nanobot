"""手动登录支持 - 用户在浏览器中完成登录。"""

import asyncio

from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult
from nanobot.browser.session import BrowserSession


class ManualLoginAdapter(WebsiteAdapter):
    """手动登录适配器 - 打开浏览器供用户完成登录。

    用作自动登录失败时的最终后备。
    打开浏览器窗口(非无头模式)并等待用户
    手动完成登录。
    """

    NAME = "manual"
    DOMAINS = []  # 后备适配器
    DISPLAY_NAME = "Manual Login"

    async def login(
        self,
        session: BrowserSession,
        username: str | None = None,
        password: str | None = None,
        login_url: str | None = None,
    ) -> LoginResult:
        """打开浏览器进行手动登录。

        Args:
            session: 浏览器会话(如果需要将变为非无头模式)
            username: 不用于手动登录
            password: 不用于手动登录
            login_url: 打开登录的 URL(默认为当前页面)

        Returns:
            用户确认登录完成后的 LoginResult
        """
        # 确保浏览器可见
        if session.headless:
            return LoginResult.failed(
                "Cannot use manual login in headless mode. Please disable headless mode in config.",
            )

        # 如果提供,导航到登录 URL
        if login_url:
            await session.navigate(login_url)

        # 等待用户完成登录
        # 在实际实现中,这会在 UI 中显示提示
        # 目前,我们将等待登录验证
        return await self._wait_for_manual_login(session)

    async def _wait_for_manual_login(self, session: BrowserSession) -> LoginResult:
        """等待用户完成手动登录。

        通过以下方式检测登录完成:
        - URL 从登录页更改
        - 登录元素的出现
        - 用户确认

        Returns:
            LoginResult
        """
        # 轮询登录完成(最多 5 分钟)
        max_attempts = 300  # 5 分钟
        check_interval = 1  # 1 秒

        for i in range(max_attempts):
            await asyncio.sleep(check_interval)

            # 检查登录是否成功
            if await self.verify_login(session):
                return LoginResult.success("Manual login completed")

        return LoginResult.failed("Manual login timeout - please try again")

    async def verify_login(self, session: BrowserSession) -> bool:
        """验证手动登录完成。

        检查:
        - URL 不包含登录指示符
        - 没有可见的错误消息
        """
        url = session.page.url.lower()
        login_indicators = ["/login", "/signin", "/auth", "/sign_in"]

        # 仍在登录页上
        if any(indicator in url for indicator in login_indicators):
            return False

        # 检查错误消息
        try:
            error_elements = await session.page.query_selector_all('.error, .alert-error, [role="alert"]')
            for elem in error_elements:
                text = await elem.inner_text()
                if text and "error" in text.lower():
                    return False
        except Exception:
            pass

        # 如果不在登录页且没有错误,则假定成功
        return True

    @classmethod
    def get_priority(cls) -> int:
        """手动登录具有最低优先级。"""
        return -1

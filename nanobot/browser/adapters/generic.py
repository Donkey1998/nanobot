"""使用启发式规则的通用登录适配器。"""

import asyncio

from nanobot.browser.actions import BrowserActions, ElementNotFoundError
from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult


class GenericLoginAdapter(WebsiteAdapter):
    """适用于标准登录表单的通用登录适配器。

    使用启发式规则查找和填写登录表单。适用于大约
    60-70% 的标准用户名/密码登录表单。

    启发式:
    - 查找具有密码字段的表单
    - 在密码之前查找用户名/电子邮件字段
    - 查找具有 "login"/"sign in" 文本的提交按钮
    """

    NAME = "generic"
    DOMAINS = []  # 没有特定域 - 用作后备
    DISPLAY_NAME = "Generic Login"

    # 用于识别登录元素的模式
    USERNAME_SELECTORS = [
        'input[type="text"]',
        'input[type="email"]',
        'input[name*="user" i]',
        'input[name*="email" i]',
        'input[id*="user" i]',
        'input[id*="email" i]',
        'input[placeholder*="user" i]',
        'input[placeholder*="email" i]',
    ]

    PASSWORD_SELECTORS = [
        'input[type="password"]',
    ]

    SUBMIT_SELECTORS = [
        'button[type="submit"]',
        'button:has-text("登录")',
        'button:has-text("Login")',
        'button:has-text("Sign in")',
        'button:has-text("登录")',
        'button:has-text("signin")',
        'input[type="submit"]',
        'input[value*="登录"]',
        'input[value*="Login"]',
    ]

    async def login(
        self,
        session: "nanobot.browser.session.BrowserSession",
        username: str | None = None,
        password: str | None = None,
    ) -> LoginResult:
        """使用通用启发式尝试登录。

        Args:
            session: 浏览器会话
            username: 用户名(如果为 None 则请求)
            password: 密码(如果为 None 则请求)

        Returns:
            LoginResult
        """
        if username is None or password is None:
            return LoginResult.requires_credentials(["username", "password"])

        actions = BrowserActions(session.page, timeout=session.timeout)

        try:
            # 步骤 1: 查找密码字段(锚定元素)
            password_field = await self._find_password_field(actions)
            if password_field is None:
                return LoginResult.failed(
                    "Could not find password field",
                    suggested_strategy="manual",
                )

            # 步骤 2: 查找用户名字段
            username_field = await self._find_username_field(actions)
            if username_field is None:
                return LoginResult.failed(
                    "Could not find username/email field",
                    suggested_strategy="manual",
                )

            # 步骤 3: 填写凭据
            await actions.type_text("username_field", username, strategy="css")
            await asyncio.sleep(0.1)  # 小延迟
            await actions.type_text("password_field", password, strategy="css")
            await asyncio.sleep(0.1)

            # 步骤 4: 检查"记住我"复选框
            await self._check_remember_me(actions)

            # 步骤 5: 查找并点击提交按钮
            submit_clicked = await self._click_submit(actions)

            if not submit_clicked:
                return LoginResult.failed(
                    "Could not find or click submit button",
                    suggested_strategy="manual",
                )

            # 步骤 6: 等待导航
            await asyncio.sleep(2)

            # 步骤 7: 验证登录
            if await self.verify_login(session):
                return LoginResult.success()
            else:
                # 检查错误消息
                error = await self._check_error_messages(actions)
                if error:
                    return LoginResult.failed(f"Login failed: {error}")
                return LoginResult.failed(
                    "Login verification failed",
                    suggested_strategy="manual",
                )

        except Exception as e:
            return LoginResult.failed(f"Generic login error: {e}")

    async def _find_password_field(self, actions: BrowserActions):
        """查找密码输入字段。"""
        for selector in self.PASSWORD_SELECTORS:
            try:
                await actions.wait_for_element(selector, state="attached", strategy="css")
                return selector
            except Exception:
                continue
        return None

    async def _find_username_field(self, actions: BrowserActions):
        """查找用户名/电子邮件输入字段。"""
        for selector in self.USERNAME_SELECTORS:
            try:
                await actions.wait_for_element(selector, state="attached", strategy="css")
                return selector
            except Exception:
                continue
        return None

    async def _check_remember_me(self, actions: BrowserActions):
        """检查并点击"记住我"复选框(如果存在)。"""
        remember_selectors = [
            'input[type="checkbox"][name*="remember" i]',
            'input[type="checkbox"][id*="remember" i]',
            'label:has-text("记住")',
            'label:has-text("Remember")',
        ]

        for selector in remember_selectors:
            try:
                await actions.wait_for_element(selector, state="attached", strategy="css")
                # 检查是否尚未选中
                checked = await actions.page.query_selector(selector + ":not(:checked)")
                if checked:
                    await actions.click(selector, strategy="css")
                return
            except Exception:
                continue

    async def _click_submit(self, actions: BrowserActions) -> bool:
        """查找并点击提交按钮。"""
        for selector in self.SUBMIT_SELECTORS:
            try:
                await actions.wait_for_element(selector, state="visible", strategy="css")
                await actions.click(selector, strategy="css", wait_for_navigation=False)
                return True
            except Exception:
                continue
        return False

    async def _check_error_messages(self, actions: BrowserActions) -> str | None:
        """检查页面上的登录错误消息。"""
        error_selectors = [
            ".error",
            ".alert-error",
            "[role=\"alert\"]",
            ".message.error",
            ".login-error",
        ]

        for selector in error_selectors:
            try:
                text = await actions.get_text(selector, strategy="css")
                if text and text.strip():
                    return text.strip()
            except Exception:
                continue

        return None

    @classmethod
    def get_priority(cls) -> int:
        """通用适配器具有最低优先级。"""
        return 0

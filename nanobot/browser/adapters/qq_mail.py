"""QQ Mail adapter - automated login for mail.qq.com."""

import asyncio

from nanobot.browser.actions import BrowserActions, ElementNotFoundError
from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult


class QQMailAdapter(WebsiteAdapter):
    """Adapter for QQ Mail (mail.qq.com) login.

    Supports both password login and QR code login.

    For password login, handles:
    - Switching to password login mode
    - Filling QQ number and password
    - Handling CAPTCHA (prompts user)
    - Verifying login success

    For QR code login:
    - Switches to QR code mode
    - Waits for user to scan with mobile QQ
    - Detects login completion
    """

    NAME = "qq-mail"
    DOMAINS = ["mail.qq.com", "*.mail.qq.com", "qq.com"]
    DISPLAY_NAME = "QQ Mail"

    QQ_MAIL_URL = "https://mail.qq.com"

    # Selectors specific to QQ Mail
    SWITCH_TO_PASSWORD_BTN = 'a:has-text("账号密码登录")'
    USERNAME_FIELD = 'input[name="u"]'
    PASSWORD_FIELD = 'input[name="p"]'
    LOGIN_BTN = 'input[type="button"][value="登 录"]'
    SWITCH_TO_QRCODE_BTN = 'a:has-text("扫码登录")'

    async def login(
        self,
        session: "nanobot.browser.session.BrowserSession",
        username: str | None = None,
        password: str | None = None,
        use_qrcode: bool = False,
    ) -> LoginResult:
        """Login to QQ Mail.

        Args:
            session: Browser session
            username: QQ number (for password login)
            password: Password (for password login)
            use_qrcode: Use QR code login instead of password

        Returns:
            LoginResult
        """
        # Navigate to QQ Mail
        await session.navigate(self.QQ_MAIL_URL)
        await asyncio.sleep(2)

        if use_qrcode:
            return await self._login_qrcode(session)

        # Password login
        if username is None or password is None:
            return LoginResult.requires_credentials(["QQ number", "password"])

        return await self._login_password(session, username, password)

    async def _login_password(
        self,
        session: "nanobot.browser.session.BrowserSession",
        username: str,
        password: str,
    ) -> LoginResult:
        """Login using QQ number and password."""
        actions = BrowserActions(session.page, timeout=session.timeout)

        try:
            # Switch to password login mode
            try:
                await actions.wait_for_element(self.SWITCH_TO_PASSWORD_BTN, strategy="css", state="visible")
                await actions.click(self.SWITCH_TO_PASSWORD_BTN, strategy="css", wait_for_navigation=False)
                await asyncio.sleep(1)
            except ElementNotFoundError:
                # Already in password mode or page changed
                pass

            # Fill QQ number
            await actions.wait_for_element(self.USERNAME_FIELD, strategy="css", state="visible")
            await actions.type_text(self.USERNAME_FIELD, username, strategy="css")
            await asyncio.sleep(0.3)

            # Fill password
            await actions.type_text(self.PASSWORD_FIELD, password, strategy="css")
            await asyncio.sleep(0.3)

            # Check for CAPTCHA
            has_captcha = await self._check_for_captcha(actions)
            if has_captcha:
                return LoginResult.requires_user_input("CAPTCHA detected. Please solve CAPTCHA manually and click login.")

            # Click login button
            await actions.click(self.LOGIN_BTN, strategy="css", wait_for_navigation=False)

            # Wait for navigation
            await asyncio.sleep(3)

            # Verify login
            if await self.verify_login(session):
                return LoginResult.success("QQ Mail login successful")
            else:
                # Check for error messages
                error = await self._check_qq_error(actions)
                if error:
                    return LoginResult.failed(f"QQ Mail login failed: {error}")
                return LoginResult.failed("QQ Mail login verification failed", suggested_strategy="manual")

        except Exception as e:
            return LoginResult.failed(f"QQ Mail password login error: {e}")

    async def _login_qrcode(self, session: "nanobot.browser.session.BrowserSession") -> LoginResult:
        """Login using QR code scan."""
        actions = BrowserActions(session.page, timeout=session.timeout)

        try:
            # Switch to QR code mode
            try:
                await actions.wait_for_element(self.SWITCH_TO_QRCODE_BTN, strategy="css", state="visible")
                await actions.click(self.SWITCH_TO_QRCODE_BTN, strategy="css", wait_for_navigation=False)
                await asyncio.sleep(1)
            except ElementNotFoundError:
                pass

            # Wait for user to scan QR code (poll for login)
            # QR code is shown, wait for URL change indicating success
            for _ in range(60):  # Wait up to 60 seconds
                await asyncio.sleep(1)
                if await self.verify_login(session):
                    return LoginResult.success("QQ Mail QR code login successful")

            return LoginResult.failed("QR code login timeout - no scan detected", suggested_strategy="manual")

        except Exception as e:
            return LoginResult.failed(f"QQ Mail QR code login error: {e}")

    async def _check_for_captcha(self, actions: BrowserActions) -> bool:
        """Check if CAPTCHA is present on the page."""
        captcha_selectors = [
            'img[alt*="验证码" i]',
            'img[alt*="captcha" i]',
            '.verifyimg',
            '#verifycode',
        ]

        for selector in captcha_selectors:
            try:
                await actions.wait_for_element(selector, strategy="css", state="visible")
                return True
            except ElementNotFoundError:
                continue

        return False

    async def _check_qq_error(self, actions: BrowserActions) -> str | None:
        """Check for QQ Mail specific error messages."""
        error_selectors = [
            ".err_m",
            ".login_error",
            "[id*=\"err\"]",
        ]

        for selector in error_selectors:
            try:
                text = await actions.get_text(selector, strategy="css")
                if text and text.strip():
                    return text.strip()
            except ElementNotFoundError:
                continue

        return None

    async def verify_login(self, session: "nanobot.browser.session.BrowserSession") -> bool:
        """Verify QQ Mail login success.

        Checks for:
        - URL changed to main mail interface
        - Presence of inbox elements
        """
        url = session.page.url

        # Check if we're on the main mail interface
        if "mail.qq.com" in url and "/cgi-bin" in url:
            return True

        # Check for inbox elements
        try:
            await asyncio.wait_for(
                session.page.wait_for_selector('.inbox, [class*="inbox" i]', timeout=3000),
                timeout=3.0,
            )
            return True
        except Exception:
            pass

        return False

    @classmethod
    def get_priority(cls) -> int:
        """QQ Mail adapter has high priority."""
        return 100

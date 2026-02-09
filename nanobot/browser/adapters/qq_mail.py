"""QQ Mail 适配器 - mail.qq.com 的自动登录。"""

import asyncio

from nanobot.browser.actions import BrowserActions, ElementNotFoundError
from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult


class QQMailAdapter(WebsiteAdapter):
    """QQ Mail (mail.qq.com) 登录的适配器。

    支持密码登录和二维码登录。

    对于密码登录,处理:
    - 切换到密码登录模式
    - 填写 QQ 号和密码
    - 处理验证码(提示用户)
    - 验证登录成功

    对于二维码登录:
    - 切换到二维码模式
    - 等待用户使用手机 QQ 扫描
    - 检测登录完成
    """

    NAME = "qq-mail"
    DOMAINS = ["mail.qq.com", "*.mail.qq.com", "qq.com"]
    DISPLAY_NAME = "QQ Mail"

    QQ_MAIL_URL = "https://mail.qq.com"

    # QQ Mail 特定的选择器
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
        """登录 QQ Mail。

        Args:
            session: 浏览器会话
            username: QQ 号(用于密码登录)
            password: 密码(用于密码登录)
            use_qrcode: 使用二维码登录代替密码

        Returns:
            LoginResult
        """
        # 导航到 QQ Mail
        await session.navigate(self.QQ_MAIL_URL)
        await asyncio.sleep(2)

        if use_qrcode:
            return await self._login_qrcode(session)

        # 密码登录
        if username is None or password is None:
            return LoginResult.requires_credentials(["QQ number", "password"])

        return await self._login_password(session, username, password)

    async def _login_password(
        self,
        session: "nanobot.browser.session.BrowserSession",
        username: str,
        password: str,
    ) -> LoginResult:
        """使用 QQ 号和密码登录。"""
        actions = BrowserActions(session.page, timeout=session.timeout)

        try:
            # 切换到密码登录模式
            try:
                await actions.wait_for_element(self.SWITCH_TO_PASSWORD_BTN, strategy="css", state="visible")
                await actions.click(self.SWITCH_TO_PASSWORD_BTN, strategy="css", wait_for_navigation=False)
                await asyncio.sleep(1)
            except ElementNotFoundError:
                # 已处于密码模式或页面已更改
                pass

            # 填写 QQ 号
            await actions.wait_for_element(self.USERNAME_FIELD, strategy="css", state="visible")
            await actions.type_text(self.USERNAME_FIELD, username, strategy="css")
            await asyncio.sleep(0.3)

            # 填写密码
            await actions.type_text(self.PASSWORD_FIELD, password, strategy="css")
            await asyncio.sleep(0.3)

            # 检查验证码
            has_captcha = await self._check_for_captcha(actions)
            if has_captcha:
                return LoginResult.requires_user_input("CAPTCHA detected. Please solve CAPTCHA manually and click login.")

            # 点击登录按钮
            await actions.click(self.LOGIN_BTN, strategy="css", wait_for_navigation=False)

            # 等待导航
            await asyncio.sleep(3)

            # 验证登录
            if await self.verify_login(session):
                return LoginResult.success("QQ Mail login successful")
            else:
                # 检查错误消息
                error = await self._check_qq_error(actions)
                if error:
                    return LoginResult.failed(f"QQ Mail login failed: {error}")
                return LoginResult.failed("QQ Mail login verification failed", suggested_strategy="manual")

        except Exception as e:
            return LoginResult.failed(f"QQ Mail password login error: {e}")

    async def _login_qrcode(self, session: "nanobot.browser.session.BrowserSession") -> LoginResult:
        """使用二维码扫描登录。"""
        actions = BrowserActions(session.page, timeout=session.timeout)

        try:
            # 切换到二维码模式
            try:
                await actions.wait_for_element(self.SWITCH_TO_QRCODE_BTN, strategy="css", state="visible")
                await actions.click(self.SWITCH_TO_QRCODE_BTN, strategy="css", wait_for_navigation=False)
                await asyncio.sleep(1)
            except ElementNotFoundError:
                pass

            # 等待用户扫描二维码(轮询登录)
            # 显示二维码,等待 URL 更改指示成功
            for _ in range(60):  # 等待最多 60 秒
                await asyncio.sleep(1)
                if await self.verify_login(session):
                    return LoginResult.success("QQ Mail QR code login successful")

            return LoginResult.failed("QR code login timeout - no scan detected", suggested_strategy="manual")

        except Exception as e:
            return LoginResult.failed(f"QQ Mail QR code login error: {e}")

    async def _check_for_captcha(self, actions: BrowserActions) -> bool:
        """检查页面上是否存在验证码。"""
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
        """检查 QQ Mail 特定的错误消息。"""
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
        """验证 QQ Mail 登录成功。

        检查:
        - URL 更改为主邮件界面
        - 收件箱元素的存在
        """
        url = session.page.url

        # 检查我们是否在主邮件界面上
        if "mail.qq.com" in url and "/cgi-bin" in url:
            return True

        # 检查收件箱元素
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
        """QQ Mail 适配器具有高优先级。"""
        return 100

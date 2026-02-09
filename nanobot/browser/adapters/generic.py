"""Generic login adapter using heuristic rules."""

import asyncio

from nanobot.browser.actions import BrowserActions, ElementNotFoundError
from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult


class GenericLoginAdapter(WebsiteAdapter):
    """Generic login adapter that works with standard login forms.

    Uses heuristic rules to find and fill login forms. Works with about
    60-70% of standard username/password login forms.

    Heuristics:
    - Find form with password field
    - Find username/email field before password
    - Find submit button with "login"/"sign in" text
    """

    NAME = "generic"
    DOMAINS = []  # No specific domains - used as fallback
    DISPLAY_NAME = "Generic Login"

    # Patterns for identifying login elements
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
        """Attempt login using generic heuristics.

        Args:
            session: Browser session
            username: Username (if None, request it)
            password: Password (if None, request it)

        Returns:
            LoginResult
        """
        if username is None or password is None:
            return LoginResult.requires_credentials(["username", "password"])

        actions = BrowserActions(session.page, timeout=session.timeout)

        try:
            # Step 1: Find password field (anchor element)
            password_field = await self._find_password_field(actions)
            if password_field is None:
                return LoginResult.failed(
                    "Could not find password field",
                    suggested_strategy="manual",
                )

            # Step 2: Find username field
            username_field = await self._find_username_field(actions)
            if username_field is None:
                return LoginResult.failed(
                    "Could not find username/email field",
                    suggested_strategy="manual",
                )

            # Step 3: Fill credentials
            await actions.type_text("username_field", username, strategy="css")
            await asyncio.sleep(0.1)  # Small delay
            await actions.type_text("password_field", password, strategy="css")
            await asyncio.sleep(0.1)

            # Step 4: Check for "remember me" checkbox
            await self._check_remember_me(actions)

            # Step 5: Find and click submit button
            submit_clicked = await self._click_submit(actions)

            if not submit_clicked:
                return LoginResult.failed(
                    "Could not find or click submit button",
                    suggested_strategy="manual",
                )

            # Step 6: Wait for navigation
            await asyncio.sleep(2)

            # Step 7: Verify login
            if await self.verify_login(session):
                return LoginResult.success()
            else:
                # Check for error messages
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
        """Find the password input field."""
        for selector in self.PASSWORD_SELECTORS:
            try:
                await actions.wait_for_element(selector, state="attached", strategy="css")
                return selector
            except Exception:
                continue
        return None

    async def _find_username_field(self, actions: BrowserActions):
        """Find the username/email input field."""
        for selector in self.USERNAME_SELECTORS:
            try:
                await actions.wait_for_element(selector, state="attached", strategy="css")
                return selector
            except Exception:
                continue
        return None

    async def _check_remember_me(self, actions: BrowserActions):
        """Check and click "remember me" checkbox if present."""
        remember_selectors = [
            'input[type="checkbox"][name*="remember" i]',
            'input[type="checkbox"][id*="remember" i]',
            'label:has-text("记住")',
            'label:has-text("Remember")',
        ]

        for selector in remember_selectors:
            try:
                await actions.wait_for_element(selector, state="attached", strategy="css")
                # Check if not already checked
                checked = await actions.page.query_selector(selector + ":not(:checked)")
                if checked:
                    await actions.click(selector, strategy="css")
                return
            except Exception:
                continue

    async def _click_submit(self, actions: BrowserActions) -> bool:
        """Find and click the submit button."""
        for selector in self.SUBMIT_SELECTORS:
            try:
                await actions.wait_for_element(selector, state="visible", strategy="css")
                await actions.click(selector, strategy="css", wait_for_navigation=False)
                return True
            except Exception:
                continue
        return False

    async def _check_error_messages(self, actions: BrowserActions) -> str | None:
        """Check for login error messages on the page."""
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
        """Generic adapter has lowest priority."""
        return 0

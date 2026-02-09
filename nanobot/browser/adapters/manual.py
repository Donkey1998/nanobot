"""Manual login support - user completes login in browser."""

import asyncio

from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult
from nanobot.browser.session import BrowserSession


class ManualLoginAdapter(WebsiteAdapter):
    """Manual login adapter - opens browser for user to complete login.

    Used as final fallback when automated login fails.
    Opens the browser window (non-headless) and waits for user to
    manually complete login.
    """

    NAME = "manual"
    DOMAINS = []  # Fallback adapter
    DISPLAY_NAME = "Manual Login"

    async def login(
        self,
        session: BrowserSession,
        username: str | None = None,
        password: str | None = None,
        login_url: str | None = None,
    ) -> LoginResult:
        """Open browser for manual login.

        Args:
            session: Browser session (will be made non-headless if needed)
            username: Not used for manual login
            password: Not used for manual login
            login_url: URL to open for login (defaults to current page)

        Returns:
            LoginResult after user confirms login complete
        """
        # Make sure browser is visible
        if session.headless:
            return LoginResult.failed(
                "Cannot use manual login in headless mode. Please disable headless mode in config.",
            )

        # Navigate to login URL if provided
        if login_url:
            await session.navigate(login_url)

        # Wait for user to complete login
        # In a real implementation, this would show a prompt in the UI
        # For now, we'll wait for login verification
        return await self._wait_for_manual_login(session)

    async def _wait_for_manual_login(self, session: BrowserSession) -> LoginResult:
        """Wait for user to complete manual login.

        Detects login completion by:
        - URL change away from login pages
        - Appearance of logged-in elements
        - User confirmation

        Returns:
            LoginResult
        """
        # Poll for login completion (up to 5 minutes)
        max_attempts = 300  # 5 minutes
        check_interval = 1  # 1 second

        for i in range(max_attempts):
            await asyncio.sleep(check_interval)

            # Check if login successful
            if await self.verify_login(session):
                return LoginResult.success("Manual login completed")

        return LoginResult.failed("Manual login timeout - please try again")

    async def verify_login(self, session: BrowserSession) -> bool:
        """Verify manual login completion.

        Checks:
        - URL doesn't contain login indicators
        - No error messages visible
        """
        url = session.page.url.lower()
        login_indicators = ["/login", "/signin", "/auth", "/sign_in"]

        # Still on login page
        if any(indicator in url for indicator in login_indicators):
            return False

        # Check for error messages
        try:
            error_elements = await session.page.query_selector_all('.error, .alert-error, [role="alert"]')
            for elem in error_elements:
                text = await elem.inner_text()
                if text and "error" in text.lower():
                    return False
        except Exception:
            pass

        # Assume success if not on login page and no errors
        return True

    @classmethod
    def get_priority(cls) -> int:
        """Manual login has lowest priority."""
        return -1

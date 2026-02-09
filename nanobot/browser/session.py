"""Browser session management."""

import asyncio
from pathlib import Path
from typing import Literal

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from nanobot.browser.permissions import require_domain_allowed


class BrowserTimeoutError(Exception):
    """Raised when browser operation times out."""

    pass


class BrowserSession:
    """Manage a browser session with persistent profile.

    Each session maintains its own browser context with separate cookies,
    localStorage, etc. Sessions are persisted to disk based on domain.

    Example:
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
        """Initialize browser session.

        Args:
            allowed_domains: Whitelist of allowed domain patterns
            headless: Run browser in headless mode (no GUI)
            timeout: Default timeout for operations (milliseconds)
            profile_dir: Base directory for browser profiles (default: ~/.nanobot/browser-profiles/)
            user_data_dir: Specific user data directory for this session (optional)
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
        """Check if browser session is started."""
        return self._started

    async def start(self) -> None:
        """Start browser session.

        Raises:
            BrowserTimeoutError: If browser fails to start within timeout
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

            # Create context with persistent storage if specified
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
        """Stop browser session and save state.

        Closes browser and persists cookies, localStorage, etc.
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
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.stop()

    async def navigate(
        self,
        url: str,
        wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load",
    ) -> None:
        """Navigate to URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation succeeded

        Raises:
            PermissionDenied: If URL domain is not in whitelist
            BrowserTimeoutError: If navigation times out
        """
        if not self._started:
            raise RuntimeError("Browser session not started. Call start() first.")

        # Check permissions
        require_domain_allowed(url, self.allowed_domains)

        try:
            # Navigate with explicit timeout (Playwright uses milliseconds)
            await self._page.goto(url, wait_until=wait_until, timeout=self.timeout)
        except Exception as exc:
            # Playwright's TimeoutError has different message format
            if "Timeout" in str(exc):
                raise BrowserTimeoutError(f"Navigation to {url} timed out") from exc
            raise

    async def wait_for_load_state(self, state: Literal["load", "domcontentloaded", "networkidle"] = "networkidle") -> None:
        """Wait for specific load state.

        Args:
            state: Load state to wait for
        """
        if not self._page:
            raise RuntimeError("Browser session not started")

        await self._page.wait_for_load_state(state)

    @property
    def page(self) -> Page:
        """Get the active page object.

        Returns:
            Playwright Page object

        Raises:
            RuntimeError: If session not started
        """
        if not self._page:
            raise RuntimeError("Browser session not started")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """Get the browser context.

        Returns:
            Playwright BrowserContext object

        Raises:
            RuntimeError: If session not started
        """
        if not self._context:
            raise RuntimeError("Browser session not started")
        return self._context

    @classmethod
    def get_profile_path(cls, domain: str, base_dir: str | Path | None = None) -> Path:
        """Get the profile path for a specific domain.

        Args:
            domain: Domain name (e.g., "mail.qq.com")
            base_dir: Base directory for profiles (default: ~/.nanobot/browser-profiles/)

        Returns:
            Path to profile directory
        """
        base = Path(base_dir) if base_dir else Path.home() / ".nanobot" / "browser-profiles"
        return base / domain

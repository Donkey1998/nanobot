"""Browser actions for interacting with pages."""

from typing import Any

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from nanobot.browser.session import BrowserTimeoutError


class ElementNotFoundError(Exception):
    """Raised when an element cannot be found on the page."""

    def __init__(self, locator: str, reason: str = "Element not found") -> None:
        self.locator = locator
        self.reason = reason
        super().__init__(f"Element not found: {locator} - {reason}")


class ElementNotInteractableError(Exception):
    """Raised when an element is found but not interactable."""

    def __init__(self, locator: str, reason: str = "Element not interactable") -> None:
        self.locator = locator
        self.reason = reason
        super().__init__(f"Element not interactable: {locator} - {reason}")


class BrowserActions:
    """Execute browser actions like click, type, wait, etc.

    Supports multiple element location strategies:
    - ARIA labels (most stable for dynamic apps)
    - id attribute
    - data-testid attribute
    - CSS selectors
    - Text content

    Example:
        >>> actions = BrowserActions(page, timeout=30000)
        >>> await actions.click("Login button")
        >>> await actions.type("Email input", "user@example.com")
        >>> await actions.wait_for_element("Welcome message")
    """

    def __init__(self, page: Page, timeout: int = 30000) -> None:
        """Initialize browser actions.

        Args:
            page: Playwright Page object
            timeout: Default timeout for operations (milliseconds)
        """
        self.page = page
        self.timeout = timeout

    async def click(
        self,
        locator: str,
        strategy: str = "auto",
        wait_for_navigation: bool = True,
    ) -> None:
        """Click an element on the page.

        Args:
            locator: Element identifier (depends on strategy)
            strategy: Location strategy: "auto", "aria", "id", "testid", "css", "text"
            wait_for_navigation: Wait for navigation after click

        Raises:
            ElementNotFoundError: If element not found
            ElementNotInteractableError: If element not interactable
            BrowserTimeoutError: If operation times out
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
        """Type text into an input field.

        Args:
            locator: Element identifier
            text: Text to type
            strategy: Location strategy
            clear_first: Clear existing text before typing

        Raises:
            ElementNotFoundError: If element not found
            BrowserTimeoutError: If operation times out
        """
        element = await self._find_element(locator, strategy)

        try:
            if clear_first:
                await element.clear(timeout=self.timeout / 1000)

            # Type with proper events to ensure frameworks capture input
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
        """Wait for an element to appear on the page.

        Args:
            locator: Element identifier
            strategy: Location strategy
            state: Element state: "visible", "attached", "hidden", "detached"

        Raises:
            BrowserTimeoutError: If element doesn't appear within timeout
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
        """Extract text content from an element.

        Args:
            locator: Element identifier
            strategy: Location strategy

        Returns:
            Text content (whitespace trimmed)

        Raises:
            ElementNotFoundError: If element not found
            BrowserTimeoutError: If operation times out
        """
        element = await self._find_element(locator, strategy)

        try:
            text = await element.inner_text(timeout=self.timeout / 1000)
            return " ".join(text.split())  # Trim whitespace
        except PlaywrightTimeoutError as exc:
            raise BrowserTimeoutError(f"Get text from '{locator}' timed out") from exc

    async def _find_element(self, locator: str, strategy: str):
        """Find an element using the specified strategy.

        Args:
            locator: Element identifier
            strategy: Location strategy

        Returns:
            Playwright ElementHandle

        Raises:
            ElementNotFoundError: If element not found
            BrowserTimeoutError: If search times out
        """
        selector = self._build_selector(locator, strategy)

        try:
            element = await self.page.wait_for_selector(
                selector,
                state="attached",
                timeout=self.timeout / 1000,
            )
        except PlaywrightTimeoutError as exc:
            # Provide helpful error message
            raise ElementNotFoundError(
                locator,
                f"Could not find element using {strategy} strategy",
            ) from exc

        if element is None:
            raise ElementNotFoundError(locator, f"Element not found using {strategy} strategy")

        return element

    def _build_selector(self, locator: str, strategy: str) -> str:
        """Build a CSS selector from locator and strategy.

        Args:
            locator: Element identifier
            strategy: Location strategy

        Returns:
            CSS selector string
        """
        if strategy == "aria":
            # ARIA label: [aria-label="Login"]
            return f'[aria-label="{locator}"]'
        elif strategy == "id":
            # ID: #login-button
            return f"#{locator}"
        elif strategy == "testid":
            # data-testid: [data-testid="login-button"]
            return f'[data-testid="{locator}"]'
        elif strategy == "text":
            # Text content: :text("Login")
            return f':text("{locator}")'
        elif strategy == "css":
            # Direct CSS selector
            return locator
        elif strategy == "auto":
            # Try multiple strategies in order
            return self._auto_selector(locator)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _auto_selector(self, locator: str) -> str:
        """Auto-detect the best selector strategy.

        Args:
            locator: Element identifier

        Returns:
            CSS selector
        """
        # If it looks like CSS (contains ., #, [), >, +, ~)
        if any(c in locator for c in [".", "#", "[", ">", "+", "~", ":"]):
            return locator

        # Try aria-label first (most stable for dynamic apps)
        return f'[aria-label="{locator}"], [data-testid="{locator}"], #{locator}, :text("{locator}")'

"""Browser automation tool for nanobot."""

import json
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.browser.actions import BrowserActions, ElementNotFoundError, BrowserTimeoutError
from nanobot.browser.adapters import perform_login, LoginResult
from nanobot.browser.permissions import PermissionDenied, normalize_domain
from nanobot.browser.session import BrowserSession
from nanobot.browser.snapshot import PageSnapshot
from nanobot.config.schema import Config


class BrowserTool(Tool):
    """Browser automation tool for web interaction.

    Provides capabilities for:
    - Starting/stopping browser sessions
    - Navigating to URLs
    - Taking page snapshots
    - Clicking elements and typing text
    - Performing login

    Requires `browser.enabled=true` in config.
    """

    name = "browser"
    description = (
        "Automated browser control. Navigate websites, take snapshots, "
        "click elements, type text, and perform login. "
        "Requires URLs to be in the configured whitelist."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "stop", "navigate", "snapshot", "click", "type", "login"],
                "description": "Action to perform",
            },
            "url": {"type": "string", "description": "URL for navigate or login actions"},
            "locator": {"type": "string", "description": "Element locator for click/type actions"},
            "text": {"type": "string", "description": "Text to type"},
            "strategy": {
                "type": "string",
                "enum": ["auto", "aria", "id", "testid", "css", "text"],
                "default": "auto",
                "description": "Element location strategy",
            },
            "loginStrategy": {
                "type": "string",
                "enum": ["auto", "adapter", "generic", "manual"],
                "default": "auto",
                "description": "Login strategy",
            },
            "username": {"type": "string", "description": "Username for login"},
            "password": {"type": "string", "description": "Password for login"},
        },
        "required": ["action"],
    }

    def __init__(self, config: Config):
        """Initialize browser tool.

        Args:
            config: Nanobot configuration
        """
        self.config = config
        self._session: BrowserSession | None = None

    async def execute(self, action: str, **kwargs: Any) -> str:
        """Execute browser action.

        Args:
            action: Action to perform
            **kwargs: Action-specific parameters

        Returns:
            Result as JSON string
        """
        try:
            if action == "start":
                return await self._start_browser()
            elif action == "stop":
                return await self._stop_browser()
            elif action == "navigate":
                return await self._navigate(**kwargs)
            elif action == "snapshot":
                return await self._snapshot(**kwargs)
            elif action == "click":
                return await self._click(**kwargs)
            elif action == "type":
                return await self._type(**kwargs)
            elif action == "login":
                return await self._login(**kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except PermissionDenied as e:
            return json.dumps({"error": str(e), "errorType": "PermissionDenied"})
        except ElementNotFoundError as e:
            return json.dumps({"error": str(e), "errorType": "ElementNotFound"})
        except BrowserTimeoutError as e:
            return json.dumps({"error": str(e), "errorType": "Timeout"})
        except Exception as e:
            return json.dumps({"error": str(e), "errorType": "Unknown"})

    async def _start_browser(self) -> str:
        """Start browser session."""
        if self._session and self._session.is_started:
            return json.dumps({"status": "already_started", "message": "Browser already running"})

        # Get profile directory for domain
        profile_dir = self.config.browser.profile_dir

        self._session = BrowserSession(
            allowed_domains=self.config.browser.allowed_domains,
            headless=self.config.browser.headless,
            timeout=self.config.browser.timeout,
            profile_dir=profile_dir,
        )

        await self._session.start()

        return json.dumps({
            "status": "started",
            "message": "Browser started successfully",
            "headless": self.config.browser.headless,
        })

    async def _stop_browser(self) -> str:
        """Stop browser session."""
        if not self._session or not self._session.is_started:
            return json.dumps({"status": "not_started", "message": "Browser not running"})

        await self._session.stop()
        self._session = None

        return json.dumps({"status": "stopped", "message": "Browser stopped successfully"})

    async def _navigate(self, url: str, **kwargs: Any) -> str:
        """Navigate to URL."""
        self._ensure_session()

        await self._session.navigate(url)

        return json.dumps({
            "status": "success",
            "message": f"Navigated to {url}",
            "url": self._session.page.url,
        })

    async def _snapshot(self, **kwargs: Any) -> str:
        """Take page snapshot."""
        self._ensure_session()

        snapshot = PageSnapshot(self._session.page, timeout=self.config.browser.timeout)
        tree = await snapshot.get_tree()
        text = tree.to_text()

        # Get interactive elements
        elements = await snapshot.get_interactive_elements()

        return json.dumps({
            "status": "success",
            "url": self._session.page.url,
            "tree": text,
            "interactiveElements": elements,
            "elementCount": len(elements),
        }, ensure_ascii=False)

    async def _click(self, locator: str, strategy: str = "auto", **kwargs: Any) -> str:
        """Click element."""
        self._ensure_session()

        actions = BrowserActions(self._session.page, timeout=self.config.browser.timeout)
        await actions.click(locator, strategy=strategy)

        return json.dumps({
            "status": "success",
            "message": f"Clicked {locator}",
            "url": self._session.page.url,
        })

    async def _type(self, locator: str, text: str, strategy: str = "auto", **kwargs: Any) -> str:
        """Type text into element."""
        self._ensure_session()

        actions = BrowserActions(self._session.page, timeout=self.config.browser.timeout)
        await actions.type_text(locator, text, strategy=strategy)

        return json.dumps({
            "status": "success",
            "message": f"Typed text into {locator}",
        })

    async def _login(
        self,
        url: str,
        strategy: str = "auto",
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Perform login."""
        self._ensure_session()

        # Check if we have stored credentials
        if username is None or password is None:
            from nanobot.browser.credentials import CredentialManager
            mgr = CredentialManager(self.config.browser.credentials_path)

            domain = normalize_domain(url)
            creds = mgr.list_credentials(domain)

            if creds and len(creds) == 1:
                # Use stored credential
                cred = creds[0]
                stored_password = mgr.get(cred.domain, cred.username)
                if stored_password:
                    username = cred.username
                    password = stored_password

        # Perform login
        result: LoginResult = await perform_login(
            self._session,
            url,
            username,
            password,
            strategy,
        )

        return json.dumps({
            "status": result.status.value,
            "message": result.message,
            "requiredFields": result.required_fields,
            "suggestedStrategy": result.suggested_strategy,
        })

    def _ensure_session(self) -> None:
        """Ensure browser session is active."""
        if not self._session or not self._session.is_started:
            raise RuntimeError("Browser not started. Call browser action=start first.")

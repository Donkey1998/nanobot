"""Base adapter interface for website login automation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class LoginStatus(Enum):
    """Status of a login attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    REQUIRES_CREDENTIALS = "requires_credentials"
    REQUIRES_USER_INPUT = "requires_user_input"
    REQUIRES_CAPTCHA = "requires_captcha"


@dataclass
class LoginResult:
    """Result of a login attempt."""

    status: LoginStatus
    message: str
    # If REQUIRES_CREDENTIALS, prompt for these
    required_fields: list[str] | None = None
    # If failed, might suggest retry with different strategy
    suggested_strategy: str | None = None

    @classmethod
    def success(cls, message: str = "Login successful") -> "LoginResult":
        """Create a successful result."""
        return cls(status=LoginStatus.SUCCESS, message=message)

    @classmethod
    def failed(cls, message: str, suggested_strategy: str | None = None) -> "LoginResult":
        """Create a failed result."""
        return cls(status=LoginStatus.FAILED, message=message, suggested_strategy=suggested_strategy)

    @classmethod
    def requires_credentials(cls, fields: list[str]) -> "LoginResult":
        """Create a result indicating credentials are needed."""
        return cls(status=LoginStatus.REQUIRES_CREDENTIALS, message="Credentials required", required_fields=fields)

    @classmethod
    def requires_user_input(cls, message: str = "Manual login required") -> "LoginResult":
        """Create a result indicating manual user input is needed."""
        return cls(status=LoginStatus.REQUIRES_USER_INPUT, message=message)


class WebsiteAdapter(ABC):
    """Abstract base class for website login adapters.

    Each adapter handles the login flow for a specific website or service.
    Adapters should be robust to page structure changes and provide
    clear error messages.

    Example:
        >>> class MyMailAdapter(WebsiteAdapter):
        ...     NAME = "mymail"
        ...     DOMAINS = ["*.mymail.com", "mymail.com"]
        ...
        ...     async def login(self, session, username, password):
        ...         # Implementation
        ...         return LoginResult.success()
    """

    # Adapter metadata (override in subclasses)
    NAME: str = "base"  # Unique identifier
    DOMAINS: list[str] = []  # Domain patterns this adapter handles
    DISPLAY_NAME: str = "Base Adapter"  # Human-readable name

    def __init__(self) -> None:
        """Initialize adapter."""
        pass

    @abstractmethod
    async def login(
        self,
        session: "nanobot.browser.session.BrowserSession",
        username: str | None = None,
        password: str | None = None,
    ) -> LoginResult:
        """Perform login for this website.

        Args:
            session: Active browser session
            username: Username (may be None if not yet provided)
            password: Password (may be None if not yet provided)

        Returns:
            LoginResult indicating the outcome

        Raises:
            BrowserTimeoutError: If operations time out
            ElementNotFoundError: If required elements not found
        """
        raise NotImplementedError

    async def verify_login(self, session: "nanobot.browser.session.BrowserSession") -> bool:
        """Verify that the user is logged in.

        Called after login to confirm success. Override to provide
        site-specific verification.

        Args:
            session: Active browser session

        Returns:
            True if logged in, False otherwise
        """
        # Default verification: check if URL changed from login page
        current_url = session.page.url
        login_indicators = ["/login", "/signin", "/auth", "/login.html"]
        return not any(indicator in current_url.lower() for indicator in login_indicators)

    def matches_domain(self, domain: str) -> bool:
        """Check if this adapter handles the given domain.

        Args:
            domain: Domain to check (e.g., "mail.qq.com")

        Returns:
            True if this adapter handles the domain
        """
        from nanobot.browser.permissions import check_domain_allowed
        return check_domain_allowed(domain, tuple(self.DOMAINS))

    @classmethod
    def get_priority(cls) -> int:
        """Get adapter priority for domain matching.

        Higher priority adapters are tried first.
        Base priority is 0. Specific adapters should override.

        Returns:
            Priority value (higher = more specific)
        """
        return 0

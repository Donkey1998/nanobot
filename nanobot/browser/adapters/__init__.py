"""Website login adapters and login orchestration."""

from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult, LoginStatus
from nanobot.browser.adapters.manual import ManualLoginAdapter
from nanobot.browser.adapters.registry import AdapterRegistry, get_adapter_registry, register_custom_adapter

__all__ = [
    "WebsiteAdapter",
    "LoginResult",
    "LoginStatus",
    "ManualLoginAdapter",
    "AdapterRegistry",
    "get_adapter_registry",
    "register_custom_adapter",
    "perform_login",
]


async def perform_login(
    session: "nanobot.browser.session.BrowserSession",
    url: str,
    username: str | None = None,
    password: str | None = None,
    strategy: str = "auto",
) -> LoginResult:
    """Perform login using three-tier strategy.

    Tries in order:
    1. Specialized adapter (if available for domain)
    2. Generic login (heuristic-based)
    3. Manual login (fallback)

    Args:
        session: Browser session
        url: URL to login to
        username: Username (may be None for manual login)
        password: Password (may be None for manual login)
        strategy: Login strategy: "auto", "adapter", "generic", "manual"

    Returns:
        LoginResult indicating outcome
    """
    from nanobot.browser.permissions import normalize_domain

    domain = normalize_domain(url)
    registry = get_adapter_registry()

    # Strategy: adapter only
    if strategy == "adapter":
        adapter = registry.find_adapter(domain)
        if adapter:
            instance = adapter()
            return await instance.login(session, username, password)
        return LoginResult.failed(f"No adapter found for {domain}", suggested_strategy="generic")

    # Strategy: generic only
    if strategy == "generic":
        from nanobot.browser.adapters.generic import GenericLoginAdapter
        adapter = GenericLoginAdapter()
        return await adapter.login(session, username, password)

    # Strategy: manual only
    if strategy == "manual":
        adapter = ManualLoginAdapter()
        return await adapter.login(session, login_url=url)

    # Strategy: auto (three-tier)
    # Tier 1: Try specialized adapter
    adapter_class = registry.find_adapter(domain)
    if adapter_class:
        adapter = adapter_class()
        result = await adapter.login(session, username, password)

        if result.status == LoginStatus.SUCCESS:
            return result

        # If adapter failed, fall through to generic
        if result.status == LoginStatus.FAILED:
            # Try generic login as fallback
            pass

    # Tier 2: Try generic login
    from nanobot.browser.adapters.generic import GenericLoginAdapter
    generic = GenericLoginAdapter()
    result = await generic.login(session, username, password)

    if result.status == LoginStatus.SUCCESS:
        return result

    # Tier 3: Manual login fallback
    manual = ManualLoginAdapter()
    return await manual.login(session, login_url=url)

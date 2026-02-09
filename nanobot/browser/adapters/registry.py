"""Adapter registry for managing website login adapters."""

from typing import TYPE_CHECKING, Type

from nanobot.browser.adapters.base import WebsiteAdapter

if TYPE_CHECKING:
    from nanobot.browser.adapters.generic import GenericLoginAdapter
    from nanobot.browser.adapters.qq_mail import QQMailAdapter


# Global registry instance
_registry: list[Type[WebsiteAdapter]] = []


class AdapterRegistry:
    """Registry for website login adapters.

    Manages available adapters and finds the best match for a domain.

    Example:
        >>> registry = get_adapter_registry()
        >>> adapter = registry.find_adapter("mail.qq.com")
        >>> if adapter:
        ...     result = await adapter.login(session, username, password)
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._adapters: list[Type[WebsiteAdapter]] = []

    def register(self, adapter_class: Type[WebsiteAdapter]) -> None:
        """Register an adapter class.

        Args:
            adapter_class: Adapter class to register
        """
        if adapter_class not in self._adapters:
            self._adapters.append(adapter_class)
            # Sort by priority (highest first)
            self._adapters.sort(key=lambda a: a.get_priority(), reverse=True)

    def find_adapter(self, domain: str) -> Type[WebsiteAdapter] | None:
        """Find the best adapter for a domain.

        Args:
            domain: Domain to find adapter for

        Returns:
            Adapter class or None if no match found
        """
        for adapter_class in self._adapters:
            # Check if domain matches any pattern
            from nanobot.browser.permissions import normalize_domain
            normalized_domain = normalize_domain(domain)

            for pattern in adapter_class.DOMAINS:
                pattern_normalized = normalize_domain(pattern)

                # Handle wildcard
                if pattern_normalized.startswith("*."):
                    import fnmatch
                    if fnmatch.fnmatch(normalized_domain, pattern_normalized):
                        return adapter_class
                else:
                    # Exact match
                    if normalized_domain == pattern_normalized:
                        return adapter_class

        return None

    def list_adapters(self) -> list[Type[WebsiteAdapter]]:
        """List all registered adapters.

        Returns:
            List of adapter classes
        """
        return list(self._adapters)

    def create_adapter(self, domain: str) -> WebsiteAdapter | None:
        """Create an adapter instance for a domain.

        Args:
            domain: Domain to create adapter for

        Returns:
            Adapter instance or None if no match
        """
        adapter_class = self.find_adapter(domain)
        if adapter_class:
            return adapter_class()
        return None


# Global registry instance
_global_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry.

    Returns:
        Global registry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
        _register_builtin_adapters(_global_registry)
    return _global_registry


def _register_builtin_adapters(registry: AdapterRegistry) -> None:
    """Register built-in adapters.

    Args:
        registry: Registry to populate
    """
    # Import here to avoid circular imports
    from nanobot.browser.adapters.generic import GenericLoginAdapter
    from nanobot.browser.adapters.qq_mail import QQMailAdapter

    registry.register(QQMailAdapter)  # Higher priority
    registry.register(GenericLoginAdapter)  # Fallback


def register_custom_adapter(adapter_class: Type[WebsiteAdapter]) -> None:
    """Register a custom adapter with the global registry.

    Args:
        adapter_class: Custom adapter class

    Example:
        >>> class MyMailAdapter(WebsiteAdapter):
        ...     NAME = "mymail"
        ...     DOMAINS = ["*.mymail.com"]
        ...
        >>> register_custom_adapter(MyMailAdapter)
    """
    registry = get_adapter_registry()
    registry.register(adapter_class)

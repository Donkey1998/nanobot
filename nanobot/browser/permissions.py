"""Permission control for browser automation."""

import fnmatch
from functools import lru_cache


class PermissionDenied(Exception):
    """Raised when access to a domain is denied by whitelist policy."""

    def __init__(self, domain: str, reason: str = "Domain not in whitelist") -> None:
        self.domain = domain
        self.reason = reason
        super().__init__(f"Access denied to {domain}: {reason}")


def normalize_domain(url: str) -> str:
    """Extract and normalize domain from URL.

    Args:
        url: URL string (with or without protocol)

    Returns:
        Normalized domain (e.g., "mail.qq.com")

    Examples:
        >>> normalize_domain("https://mail.qq.com/")
        "mail.qq.com"
        >>> normalize_domain("http://mail.qq.com/path")
        "mail.qq.com"
        >>> normalize_domain("mail.qq.com")
        "mail.qq.com"
    """
    # Remove protocol
    if "://" in url:
        url = url.split("://", 1)[1]
    # Remove path and port
    domain = url.split("/")[0].split(":")[0]
    return domain.lower()


def check_domain_allowed(domain: str, allowed_domains: list[str] | tuple[str, ...]) -> bool:
    """Check if a domain is allowed by the whitelist.

    Supports wildcard patterns like "*.example.com".

    Args:
        domain: Domain to check (e.g., "mail.example.com")
        allowed_domains: List of allowed domain patterns (e.g., ["*.example.com", "api.example.com"])

    Returns:
        True if domain is allowed, False otherwise

    Examples:
        >>> check_domain_allowed("mail.example.com", ["*.example.com"])
        True
        >>> check_domain_allowed("mail.example.com", ["example.com"])
        False  # Requires exact match or wildcard
        >>> check_domain_allowed("evil.com", ["*.example.com"])
        False
    """
    if not allowed_domains:
        return False

    normalized = normalize_domain(domain)

    for pattern in allowed_domains:
        # Normalize pattern
        pattern_normalized = normalize_domain(pattern)

        # Handle wildcard
        if pattern_normalized.startswith("*."):
            # Convert wildcard to fnmatch pattern
            # *.example.com -> *.example.com
            wildcard = pattern_normalized
            if fnmatch.fnmatch(normalized, wildcard):
                return True
        else:
            # Exact match
            if normalized == pattern_normalized:
                return True

    return False


def require_domain_allowed(domain: str, allowed_domains: list[str] | tuple[str, ...]) -> None:
    """Raise PermissionDenied if domain is not in whitelist.

    Args:
        domain: Domain to check
        allowed_domains: List of allowed domain patterns

    Raises:
        PermissionDenied: If domain is not allowed
    """
    if not check_domain_allowed(domain, allowed_domains):
        raise PermissionDenied(domain)

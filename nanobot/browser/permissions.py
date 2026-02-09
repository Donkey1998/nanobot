"""浏览器自动化的权限控制。"""

import fnmatch
from functools import lru_cache


class PermissionDenied(Exception):
    """当白名单策略拒绝访问域时抛出。"""

    def __init__(self, domain: str, reason: str = "Domain not in whitelist") -> None:
        self.domain = domain
        self.reason = reason
        super().__init__(f"Access denied to {domain}: {reason}")


def normalize_domain(url: str) -> str:
    """从 URL 提取并标准化域。

    Args:
        url: URL 字符串(带或不带协议)

    Returns:
        标准化的域(例如 "mail.qq.com")

    示例:
        >>> normalize_domain("https://mail.qq.com/")
        "mail.qq.com"
        >>> normalize_domain("http://mail.qq.com/path")
        "mail.qq.com"
        >>> normalize_domain("mail.qq.com")
        "mail.qq.com"
    """
    # 移除协议
    if "://" in url:
        url = url.split("://", 1)[1]
    # 移除路径和端口
    domain = url.split("/")[0].split(":")[0]
    return domain.lower()


def check_domain_allowed(domain: str, allowed_domains: list[str] | tuple[str, ...]) -> bool:
    """检查域是否被白名单允许。

    支持通配符模式,如 "*.example.com"。

    Args:
        domain: 要检查的域(例如 "mail.example.com")
        allowed_domains: 允许的域模式列表(例如 ["*.example.com", "api.example.com"])

    Returns:
        如果允许域则返回 True,否则返回 False

    示例:
        >>> check_domain_allowed("mail.example.com", ["*.example.com"])
        True
        >>> check_domain_allowed("mail.example.com", ["example.com"])
        False  # 需要精确匹配或通配符
        >>> check_domain_allowed("evil.com", ["*.example.com"])
        False
    """
    if not allowed_domains:
        return False

    normalized = normalize_domain(domain)

    for pattern in allowed_domains:
        # 标准化模式
        pattern_normalized = normalize_domain(pattern)

        # 处理通配符
        if pattern_normalized.startswith("*."):
            # 将通配符转换为 fnmatch 模式
            # *.example.com -> *.example.com
            wildcard = pattern_normalized
            if fnmatch.fnmatch(normalized, wildcard):
                return True
        else:
            # 精确匹配
            if normalized == pattern_normalized:
                return True

    return False


def require_domain_allowed(domain: str, allowed_domains: list[str] | tuple[str, ...]) -> None:
    """如果域不在白名单中,则引发 PermissionDenied。

    Args:
        domain: 要检查的域
        allowed_domains: 允许的域模式列表

    Raises:
        PermissionDenied: 如果不允许域
    """
    if not check_domain_allowed(domain, allowed_domains):
        raise PermissionDenied(domain)

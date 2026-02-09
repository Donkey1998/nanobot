"""用于管理网站登录适配器的适配器注册表。"""

from typing import TYPE_CHECKING, Type

from nanobot.browser.adapters.base import WebsiteAdapter

if TYPE_CHECKING:
    from nanobot.browser.adapters.generic import GenericLoginAdapter
    from nanobot.browser.adapters.qq_mail import QQMailAdapter


# 全局注册表实例
_registry: list[Type[WebsiteAdapter]] = []


class AdapterRegistry:
    """网站登录适配器的注册表。

    管理可用适配器并为域查找最佳匹配。

    示例:
        >>> registry = get_adapter_registry()
        >>> adapter = registry.find_adapter("mail.qq.com")
        >>> if adapter:
        ...     result = await adapter.login(session, username, password)
    """

    def __init__(self) -> None:
        """初始化注册表。"""
        self._adapters: list[Type[WebsiteAdapter]] = []

    def register(self, adapter_class: Type[WebsiteAdapter]) -> None:
        """注册适配器类。

        Args:
            adapter_class: 要注册的适配器类
        """
        if adapter_class not in self._adapters:
            self._adapters.append(adapter_class)
            # 按优先级排序(最高优先)
            self._adapters.sort(key=lambda a: a.get_priority(), reverse=True)

    def find_adapter(self, domain: str) -> Type[WebsiteAdapter] | None:
        """查找域的最佳适配器。

        Args:
            domain: 查找适配器的域

        Returns:
            适配器类,如果未找到匹配则返回 None
        """
        for adapter_class in self._adapters:
            # 检查域是否匹配任何模式
            from nanobot.browser.permissions import normalize_domain
            normalized_domain = normalize_domain(domain)

            for pattern in adapter_class.DOMAINS:
                pattern_normalized = normalize_domain(pattern)

                # 处理通配符
                if pattern_normalized.startswith("*."):
                    import fnmatch
                    if fnmatch.fnmatch(normalized_domain, pattern_normalized):
                        return adapter_class
                else:
                    # 精确匹配
                    if normalized_domain == pattern_normalized:
                        return adapter_class

        return None

    def list_adapters(self) -> list[Type[WebsiteAdapter]]:
        """列出所有已注册的适配器。

        Returns:
            适配器类列表
        """
        return list(self._adapters)

    def create_adapter(self, domain: str) -> WebsiteAdapter | None:
        """为域创建适配器实例。

        Args:
            domain: 创建适配器的域

        Returns:
            适配器实例,如果未找到匹配则返回 None
        """
        adapter_class = self.find_adapter(domain)
        if adapter_class:
            return adapter_class()
        return None


# 全局注册表实例
_global_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    """获取全局适配器注册表。

    Returns:
        全局注册表实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
        _register_builtin_adapters(_global_registry)
    return _global_registry


def _register_builtin_adapters(registry: AdapterRegistry) -> None:
    """注册内置适配器。

    Args:
        registry: 要填充的注册表
    """
    # 在此处导入以避免循环导入
    from nanobot.browser.adapters.generic import GenericLoginAdapter
    from nanobot.browser.adapters.qq_mail import QQMailAdapter

    registry.register(QQMailAdapter)  # 较高优先级
    registry.register(GenericLoginAdapter)  # 后备


def register_custom_adapter(adapter_class: Type[WebsiteAdapter]) -> None:
    """向全局注册表注册自定义适配器。

    Args:
        adapter_class: 自定义适配器类

    示例:
        >>> class MyMailAdapter(WebsiteAdapter):
        ...     NAME = "mymail"
        ...     DOMAINS = ["*.mymail.com"]
        ...
        >>> register_custom_adapter(MyMailAdapter)
    """
    registry = get_adapter_registry()
    registry.register(adapter_class)

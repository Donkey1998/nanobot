"""网站登录适配器和登录编排。"""

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
    """使用三层策略执行登录。

    按顺序尝试:
    1. 专用适配器(如果域可用)
    2. 通用登录(基于启发式)
    3. 手动登录(后备)

    Args:
        session: 浏览器会话
        url: 登录的 URL
        username: 用户名(手动登录可能为 None)
        password: 密码(手动登录可能为 None)
        strategy: 登录策略: "auto", "adapter", "generic", "manual"

    Returns:
        表示结果的 LoginResult
    """
    from nanobot.browser.permissions import normalize_domain

    domain = normalize_domain(url)
    registry = get_adapter_registry()

    # 策略: 仅适配器
    if strategy == "adapter":
        adapter = registry.find_adapter(domain)
        if adapter:
            instance = adapter()
            return await instance.login(session, username, password)
        return LoginResult.failed(f"No adapter found for {domain}", suggested_strategy="generic")

    # 策略: 仅通用
    if strategy == "generic":
        from nanobot.browser.adapters.generic import GenericLoginAdapter
        adapter = GenericLoginAdapter()
        return await adapter.login(session, username, password)

    # 策略: 仅手动
    if strategy == "manual":
        adapter = ManualLoginAdapter()
        return await adapter.login(session, login_url=url)

    # 策略: auto(三层)
    # 第 1 层: 尝试专用适配器
    adapter_class = registry.find_adapter(domain)
    if adapter_class:
        adapter = adapter_class()
        result = await adapter.login(session, username, password)

        if result.status == LoginStatus.SUCCESS:
            return result

        # 如果适配器失败,则回退到通用
        if result.status == LoginStatus.FAILED:
            # 尝试通用登录作为后备
            pass

    # 第 2 层: 尝试通用登录
    from nanobot.browser.adapters.generic import GenericLoginAdapter
    generic = GenericLoginAdapter()
    result = await generic.login(session, username, password)

    if result.status == LoginStatus.SUCCESS:
        return result

    # 第 3 层: 手动登录后备
    manual = ManualLoginAdapter()
    return await manual.login(session, login_url=url)

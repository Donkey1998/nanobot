"""网站登录自动化的基础适配器接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class LoginStatus(Enum):
    """登录尝试的状态。"""

    SUCCESS = "success"
    FAILED = "failed"
    REQUIRES_CREDENTIALS = "requires_credentials"
    REQUIRES_USER_INPUT = "requires_user_input"
    REQUIRES_CAPTCHA = "requires_captcha"


@dataclass
class LoginResult:
    """登录尝试的结果。"""

    status: LoginStatus
    message: str
    # 如果 REQUIRES_CREDENTIALS,提示这些字段
    required_fields: list[str] | None = None
    # 如果失败,可能建议使用不同策略重试
    suggested_strategy: str | None = None

    @classmethod
    def success(cls, message: str = "Login successful") -> "LoginResult":
        """创建成功结果。"""
        return cls(status=LoginStatus.SUCCESS, message=message)

    @classmethod
    def failed(cls, message: str, suggested_strategy: str | None = None) -> "LoginResult":
        """创建失败结果。"""
        return cls(status=LoginStatus.FAILED, message=message, suggested_strategy=suggested_strategy)

    @classmethod
    def requires_credentials(cls, fields: list[str]) -> "LoginResult":
        """创建需要凭据的结果。"""
        return cls(status=LoginStatus.REQUIRES_CREDENTIALS, message="Credentials required", required_fields=fields)

    @classmethod
    def requires_user_input(cls, message: str = "Manual login required") -> "LoginResult":
        """创建需要手动用户输入的结果。"""
        return cls(status=LoginStatus.REQUIRES_USER_INPUT, message=message)


class WebsiteAdapter(ABC):
    """网站登录适配器的抽象基类。

    每个适配器处理特定网站或服务的登录流程。
    适配器应该对页面结构变化具有鲁棒性,并提供
    清晰的错误消息。

    示例:
        >>> class MyMailAdapter(WebsiteAdapter):
        ...     NAME = "mymail"
        ...     DOMAINS = ["*.mymail.com", "mymail.com"]
        ...
        ...     async def login(self, session, username, password):
        ...         # 实现
        ...         return LoginResult.success()
    """

    # 适配器元数据(在子类中覆盖)
    NAME: str = "base"  # 唯一标识符
    DOMAINS: list[str] = []  # 此适配器处理的域模式
    DISPLAY_NAME: str = "Base Adapter"  # 人类可读名称

    def __init__(self) -> None:
        """初始化适配器。"""
        pass

    @abstractmethod
    async def login(
        self,
        session: "nanobot.browser.session.BrowserSession",
        username: str | None = None,
        password: str | None = None,
    ) -> LoginResult:
        """为此网站执行登录。

        Args:
            session: 活动浏览器会话
            username: 用户名(如果尚未提供可能为 None)
            password: 密码(如果尚未提供可能为 None)

        Returns:
            表示结果的 LoginResult

        Raises:
            BrowserTimeoutError: 如果操作超时
            ElementNotFoundError: 如果找不到所需元素
        """
        raise NotImplementedError

    async def verify_login(self, session: "nanobot.browser.session.BrowserSession") -> bool:
        """验证用户是否已登录。

        在登录后调用以确认成功。覆盖以提供
        特定于站点的验证。

        Args:
            session: 活动浏览器会话

        Returns:
            如果已登录则返回 True,否则返回 False
        """
        # 默认验证: 检查 URL 是否从登录页更改
        current_url = session.page.url
        login_indicators = ["/login", "/signin", "/auth", "/login.html"]
        return not any(indicator in current_url.lower() for indicator in login_indicators)

    def matches_domain(self, domain: str) -> bool:
        """检查此适配器是否处理给定域。

        Args:
            domain: 要检查的域(例如 "mail.qq.com")

        Returns:
            如果此适配器处理域则返回 True
        """
        from nanobot.browser.permissions import check_domain_allowed
        return check_domain_allowed(domain, tuple(self.DOMAINS))

    @classmethod
    def get_priority(cls) -> int:
        """获取域匹配的适配器优先级。

        较高优先级的适配器首先尝试。
        基本优先级为 0。特定适配器应覆盖。

        Returns:
            优先级值(越高 = 越特定)
        """
        return 0

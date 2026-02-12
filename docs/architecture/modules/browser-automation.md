# 浏览器自动化模块

> **文件位置**: [nanobot/browser/](../../../nanobot/browser/)
> **主要文件**: session.py (212 行), adapters/base.py (139 行), adapters/registry.py
> **最后更新**: 2026-02-10

---

## 1. 概述

浏览器自动化模块提供基于 Playwright 的网页操作和身份认证能力，支持自动登录、页面交互和可访问性树提取。

### 核心职责

- **会话管理**: 管理 Playwright 浏览器实例的生命周期
- **页面交互**: 导航、点击、输入、等待等操作
- **自动登录**: 多层登录策略（专用→通用→手动）
- **凭证管理**: 系统密钥环安全存储登录凭证
- **权限控制**: 域名白名单限制访问范围
- **快照提取**: 提取页面可访问性树（MCP 兼容）

### 主要组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **会话管理** | [session.py](../../../nanobot/browser/session.py) | Playwright 浏览器生命周期 |
| **页面交互** | [actions.py](../../../nanobot/browser/actions.py) | 导航、点击、输入、等待 |
| **页面快照** | [snapshot.py](../../../nanobot/browser/snapshot.py) | 可访问性树提取 |
| **凭证管理** | [credentials.py](../../../nanobot/browser/credentials.py) | 系统密钥环存储 |
| **权限控制** | [permissions.py](../../../nanobot/browser/permissions.py) | 域名白名单 |

### 适配器系统

| 适配器 | 文件 | 场景 |
|--------|------|------|
| **QQ Mail** | [adapters/qq_mail.py](../../../nanobot/browser/adapters/qq_mail.py) | QQ 邮箱专用 |
| **通用登录** | [adapters/generic.py](../../../nanobot/browser/adapters/generic.py) | 60-70% 标准登录表单 |
| **手动登录** | [adapters/manual.py](../../../nanobot/browser/adapters/manual.py) | 验证码、复杂流程 |

### 相关模块

- [工具系统](tools-system.md) - browser 工具的实现
- [配置系统](config-system.md) - browser 配置

---

## 2. 设计理念

### 2.1 适配器模式

为不同网站提供专用的登录适配器，同时提供通用和手动回退方案。

**三层策略**:
1. **专用适配器**: 针对特定网站优化（如 QQ Mail）
2. **通用适配器**: 启发式规则处理标准登录表单
3. **手动适配器**: 用户手动完成复杂流程

### 2.2 安全优先

- **域名白名单**: 只允许访问配置的域名
- **系统密钥环**: 使用操作系统密钥环存储凭证
- **配置文件保护**: 限制凭证文件权限
- **超时控制**: 防止操作挂起

### 2.3 MCP 兼容

页面快照使用可访问性树格式，与 MCP (Model Context Protocol) 兼容，便于 LLM 理解页面结构。

---

## 3. 核心机制

### 3.1 浏览器会话

`BrowserSession` 管理单个浏览器实例。

**代码位置**: [session.py:18-212](../../../nanobot/browser/session.py#L18-L212)

**特点**:
- 持久化用户数据目录（cookies、localStorage）
- 支持有头/无头模式
- 可配置超时
- 异步上下文管理器支持

### 3.2 网站适配器

所有适配器继承自 `WebsiteAdapter` 基类。

**代码位置**: [adapters/base.py:50-139](../../../nanobot/browser/adapters/base.py#L50-L139)

**关键方法**:
```python
async def login(self, session, username, password) -> LoginResult:
    """执行登录，返回结果"""

async def verify_login(self, session) -> bool:
    """验证登录是否成功"""

def matches_domain(self, domain: str) -> bool:
    """检查是否处理给定域"""

@classmethod
def get_priority(cls) -> int:
    """获取优先级（越高越优先）"""
```

### 3.3 适配器注册表

`AdapterRegistry` 管理所有适配器并支持域名匹配。

**查找逻辑**:
1. 按优先级排序适配器
2. 检查域名是否匹配（支持通配符）
3. 返回第一个匹配的适配器

### 3.4 登录编排

```
BrowserTool.login(domain, strategy)
    ↓
AdapterRegistry.find_adapter(domain)
    ↓
┌─────────────────────────────────────────┐
│ Layer 1: 专用适配器 (如 QQMailAdapter)   │
│ - 导航到登录页                           │
│ - 填写表单                               │
│ - 点击登录                               │
│ - 验证成功                               │
├─────────────────────────────────────────┤
│ Layer 2: 通用适配器 (GenericLoginAdapter)│
│ - 启发式查找登录表单                     │
│ - 填写用户名/密码                        │
│ - 点击提交                               │
├─────────────────────────────────────────┤
│ Layer 3: 手动登录 (ManualLoginAdapter)   │
│ - 打开可见浏览器                         │
│ - 用户手动操作                           │
│ - 轮询等待登录完成（最多 5 分钟）        │
└─────────────────────────────────────────┘
```

---

## 4. 关键接口

### 4.1 BrowserSession

#### 构造函数

```python
def __init__(
    self,
    allowed_domains: list[str],
    headless: bool = True,
    timeout: int = 30000,
    profile_dir: str | Path | None = None,
    user_data_dir: str | Path | None = None,
)
```

#### 方法

```python
async def start(self) -> None:
    """启动浏览器会话"""

async def stop(self) -> None:
    """停止浏览器会话并保存状态"""

async def navigate(self, url: str, wait_until: str = "load") -> None:
    """导航到 URL"""

async def wait_for_load_state(self, state: str = "networkidle") -> None:
    """等待特定的加载状态"""

@property
def page(self) -> Page:
    """获取活动页面对象"""

@property
def context(self) -> BrowserContext:
    """获取浏览器上下文"""

@classmethod
def get_profile_path(cls, domain: str, base_dir: str | Path | None = None) -> Path:
    """获取特定域的配置文件路径"""
```

### 4.2 WebsiteAdapter

#### 属性

```python
NAME: str = "base"  # 唯一标识符
DOMAINS: list[str] = []  # 处理的域模式（支持通配符）
DISPLAY_NAME: str = "Base Adapter"  # 人类可读名称
```

#### 方法

```python
@abstractmethod
async def login(self, session, username, password) -> LoginResult:
    """执行登录"""

async def verify_login(self, session) -> bool:
    """验证登录是否成功"""

def matches_domain(self, domain: str) -> bool:
    """检查是否处理给定域"""

@classmethod
def get_priority(cls) -> int:
    """获取优先级"""
```

### 4.3 LoginResult

```python
@dataclass
class LoginResult:
    status: LoginStatus  # SUCCESS, FAILED, REQUIRES_CREDENTIALS, etc.
    message: str
    required_fields: list[str] | None = None
    suggested_strategy: str | None = None
```

---

## 5. 使用示例

### 5.1 基础浏览器操作

```python
import asyncio
from nanobot.browser.session import BrowserSession

async def main():
    # 创建会话
    session = BrowserSession(
        allowed_domains=["*.example.com"],
        headless=True,
        timeout=30000
    )

    async with session:
        # 导航到网页
        await session.navigate("https://example.com")

        # 获取页面标题
        title = await session.page.title()
        print(f"Title: {title}")

        # 截图
        await session.page.screenshot(path="screenshot.png")

asyncio.run(main())
```

### 5.2 使用适配器登录

```python
from nanobot.browser.adapters.registry import AdapterRegistry
from nanobot.browser.session import BrowserSession
from nanobot.browser.credentials import CredentialManager

async def login_and_use():
    # 创建会话
    session = BrowserSession(
        allowed_domains=["*.qq.com"],
        headless=True
    )

    await session.start()

    # 查找适配器
    registry = AdapterRegistry()
    adapter = registry.find_adapter("mail.qq.com")

    # 获取凭证
    creds = CredentialManager()
    username, password = creds.get("mail.qq.com")

    # 执行登录
    result = await adapter.login(session, username, password)

    if result.status == LoginStatus.SUCCESS:
        print("登录成功！")
        # 使用已登录的会话
        await session.navigate("https://mail.qq.com")
        # ... 执行操作
    else:
        print(f"登录失败: {result.message}")

    await session.stop()

asyncio.run(login_and_use())
```

### 5.3 创建自定义适配器

```python
from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult

class MySiteAdapter(WebsiteAdapter):
    NAME = "mysite"
    DOMAINS = ["*.mysite.com", "mysite.com"]
    DISPLAY_NAME = "My Site Login"

    def get_priority(cls) -> int:
        return 10  # 高优先级

    async def login(self, session, username, password):
        # 导航到登录页
        await session.navigate("https://mysite.com/login")

        # 填写表单
        await session.page.fill("#username", username)
        await session.page.fill("#password", password)

        # 点击登录按钮
        await session.page.click("#login-button")

        # 等待导航
        await session.wait_for_load_state("networkidle")

        # 验证登录
        if await self.verify_login(session):
            return LoginResult.success("Login successful")
        else:
            return LoginResult.failed("Login failed")

    async def verify_login(self, session):
        # 检查是否在登录后页面
        return "/dashboard" in session.page.url
```

### 5.4 使用权限控制

```python
from nanobot.browser.permissions import require_domain_allowed

async def navigate_with_permission(session: BrowserSession, url: str):
    try:
        # 检查权限并导航
        require_domain_allowed(url, session.allowed_domains)
        await session.navigate(url)
    except PermissionDenied as e:
        print(f"访问被拒绝: {e}")
```

---

## 6. 扩展指南

### 6.1 添加新的页面交互

```python
class BrowserActions:
    async def fill_form(self, session, form_data):
        """智能填写表单"""
        for field, value in form_data.items():
            # 尝试多种选择器策略
            selectors = [
                f"#{field}",
                f"[name={field}]",
                f"[placeholder*={field}]",
            ]

            for selector in selectors:
                try:
                    await session.page.fill(selector, value, timeout=1000)
                    break
                except:
                    continue
```

### 6.2 添加元素等待策略

```python
async def wait_for_element(session, selector, strategy="visible"):
    """灵活的元素等待"""
    if strategy == "visible":
        await session.page.wait_for_selector(selector, state="visible")
    elif strategy == "attached":
        await session.page.wait_for_selector(selector, state="attached")
    elif strategy == "hidden":
        await session.page.wait_for_selector(selector, state="hidden")
```

### 6.3 添加页面快照自定义

```python
async def custom_snapshot(session, include_hidden=False):
    """自定义页面快照"""
    return await session.page.accessibility.snapshot(
        interesting_only=True,
        root=None
    )
```

### 6.4 实现登录状态持久化

```python
class PersistentBrowserSession(BrowserSession):
    async def save_login_state(self, name: str):
        """保存登录状态（cookies）"""
        state_path = self.get_profile_path(name) / "state.json"
        cookies = await self.context.cookies()
        state_path.write_text(json.dumps(cookies))

    async def load_login_state(self, name: str):
        """加载登录状态"""
        state_path = self.get_profile_path(name) / "state.json"
        if state_path.exists():
            cookies = json.loads(state_path.read_text())
            await self.context.add_cookies(cookies)
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/browser/session.py](../../../nanobot/browser/session.py) - 浏览器会话（212 行）
- [nanobot/browser/actions.py](../../../nanobot/browser/actions.py) - 页面交互操作
- [nanobot/browser/snapshot.py](../../../nanobot/browser/snapshot.py) - 页面快照
- [nanobot/browser/credentials.py](../../../nanobot/browser/credentials.py) - 凭证管理
- [nanobot/browser/permissions.py](../../../nanobot/browser/permissions.py) - 权限控制
- [nanobot/browser/adapters/base.py](../../../nanobot/browser/adapters/base.py) - 适配器基类（139 行）
- [nanobot/browser/adapters/registry.py](../../../nanobot/browser/adapters/registry.py) - 适配器注册表
- [nanobot/browser/adapters/qq_mail.py](../../../nanobot/browser/adapters/qq_mail.py) - QQ Mail 适配器
- [nanobot/browser/adapters/generic.py](../../../nanobot/browser/adapters/generic.py) - 通用登录适配器
- [nanobot/browser/adapters/manual.py](../../../nanobot/browser/adapters/manual.py) - 手动登录适配器

### 依赖模块

- [nanobot/agent/tools/browser.py](../../../nanobot/agent/tools/browser.py) - Browser 工具

### 相关文档

- [工具系统模块文档](tools-system.md)
- [配置系统模块文档](config-system.md)

## 外部依赖

- **Playwright**: [https://playwright.dev](https://playwright.dev) - 浏览器自动化框架
- **keyring**: [https://github.com/jaraco/keyring](https://github.com/jaraco/keyring) - 系统密钥环访问

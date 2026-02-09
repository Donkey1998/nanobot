# nanobot 浏览器控制功能实现计划

## Context

为实现 Agent 控制浏览器进行网页交互的能力，需要在 nanobot 项目中集成浏览器自动化功能。

**初始场景**：打开 QQ 邮箱登录页面，支持用户手动登录（扫码/账号密码），登录后提取收件箱邮件列表（发件人、主题、时间、摘要）。

**通用性设计**：
- ✅ **支持所有基于Web的邮箱**：Gmail、Outlook、163、Yahoo Mail 等
- ✅ **支持任何Web登录系统**：不限于邮箱，可扩展到任意网站
- ✅ **可配置适配器**：通过配置添加新网站的登录流程

**设计理念**：参考 OpenClaw 的 **snapshot → act 两阶段模式**，但适配 Python 和 nanobot 的 Tool 架构。

---

## 支持范围与扩展性

### 支持的邮箱服务

**已测试**（初始场景）：
- ✅ QQ邮箱（mail.qq.com）

**可直接支持**（添加域名白名单即可）：
- 📧 Gmail（mail.google.com）
- 📧 Outlook / Hotmail（outlook.live.com）
- 📧 163邮箱（mail.163.com）
- 📧 126邮箱（mail.126.com）
- 📧 Yahoo Mail（mail.yahoo.com）
- 📧 AOL Mail（mail.aol.com）
- 📧 iCloud Mail（icloud.com）

**理论上支持**（可能需要适配器）：
- 任何基于 Web 的邮箱系统
- 企业邮箱（如腾讯企业邮、阿里企业邮）
- 自建邮箱系统（如 Roundcube、Horde）

### 通用性原理

这套方案为什么能支持多种邮箱？

1. **标准 Web 技术**：所有邮箱都基于 HTML/CSS/JavaScript
2. **可识别的登录表单**：都有用户名/密码输入框
3. **DOM 操作**：Playwright 可以操作任何网页元素
4. **快照机制**：自动提取页面结构，无需硬编码

### 不同邮箱的适配难度

| 邮箱服务 | 自动登录难度 | 说明 |
|---------|------------|------|
| QQ邮箱 | ⭐⭐⭐ | 有验证码、二次验证 |
| Gmail | ⭐⭐⭐⭐ | 通常需要 OAuth/2FA |
| Outlook | ⭐⭐⭐ | 标准表单，有时有验证码 |
| 163邮箱 | ⭐⭐ | 简单表单登录 |
| Yahoo | ⭐⭐⭐ | 需要处理二次验证 |

### 网站适配器设计

为了支持不同网站的登录流程，可以引入适配器模式：

**路径**：`nanobot/browser/adapters/`

```python
# base.py - 适配器基类
class WebsiteAdapter(ABC):
    """网站登录适配器基类"""

    @property
    @abstractmethod
    def domain(self) -> str:
        """网站域名"""

    @abstractmethod
    async def detect_login_page(self, snapshot: dict) -> bool:
        """检测是否在登录页"""

    @abstractmethod
    async def perform_login(self, page: Page, username: str, password: str) -> bool:
        """执行登录操作"""

    @abstractmethod
    async def detect_login_success(self, snapshot: dict) -> bool:
        """检测登录是否成功"""

# qq_mail.py - QQ邮箱适配器
class QQMailAdapter(WebsiteAdapter):
    domain = "mail.qq.com"

    async def perform_login(self, page: Page, username: str, password: str) -> bool:
        # 点击"账号密码登录"按钮
        await page.click("#pwd-btn")
        # 输入邮箱
        await page.fill("#email-input", username)
        # 点击下一步
        await page.click("#next-btn")
        # 等待密码框出现
        await page.wait_for_selector("#password-input")
        # 输入密码
        await page.fill("#password-input", password)
        # 点击登录
        await page.click("#login-btn")
        return True

# gmail.py - Gmail 适配器
class GmailAdapter(WebsiteAdapter):
    domain = "mail.google.com"

    async def perform_login(self, page: Page, username: str, password: str) -> bool:
        # Gmail 的登录流程
        await page.fill("#identifierId", username)
        await page.click("#identifierNext")
        await page.wait_for_selector("input[type=password]")
        await page.fill("input[type=password]", password)
        await page.click("#passwordNext")
        return True

# registry.py - 适配器注册
class AdapterRegistry:
    """管理所有网站适配器"""

    def __init__(self):
        self._adapters: dict[str, WebsiteAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        """注册默认适配器"""
        adapters = [QQMailAdapter(), GmailAdapter(), OutlookAdapter()]
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: WebsiteAdapter):
        """注册新适配器"""
        self._adapters[adapter.domain] = adapter

    def get_adapter(self, domain: str) -> WebsiteAdapter | None:
        """获取指定域名的适配器"""
        return self._adapters.get(domain)
```

### 扩展步骤：添加新邮箱支持

**以 Gmail 为例**：

1. **添加域名到白名单**：
   ```json
   {
     "browser": {
       "allowedDomains": ["mail.qq.com", "mail.google.com"]
     }
   }
   ```

2. **创建适配器**（如果自动登录需要特殊处理）：
   ```python
   # nanobot/browser/adapters/gmail.py
   class GmailAdapter(WebsiteAdapter):
       # ... 实现 Gmail 特定的登录逻辑
   ```

3. **注册适配器**：
   ```python
   registry.register(GmailAdapter())
   ```

4. **配置凭证**（可选）：
   ```bash
   nanobot browser add-credential mail.google.com
   ```

5. **测试**：
   ```python
   用户: 打开 Gmail
   Agent: [自动使用 Gmail 适配器]
   ```

### 配置驱动的通用登录

如果没有适配器，系统会使用通用登录流程：

```python
async def generic_login(page: Page, username: str, password: str):
    """通用登录流程（不依赖特定网站）"""
    # 1. 查找所有输入框
    inputs = await page.query_selector_all("input[type='text'], input[type='email']")

    # 2. 查找密码框
    password_inputs = await page.query_selector_all("input[type='password']")

    # 3. 填入用户名
    if inputs:
        await inputs[0].fill(username)

    # 4. 填入密码
    if password_inputs:
        await password_inputs[0].fill(password)

    # 5. 查找并点击登录按钮
    login_btn = await page.query_selector("button[type='submit'], button:has-text('登录'), button:has-text('Login')")
    if login_btn:
        await login_btn.click()
```

**优势**：
- 无需为每个网站编写适配器
- 适用于简单的表单登录
- 对于复杂登录，可以回退到手动模式

### 扩展到其他网站类型

**不仅是邮箱，还支持**：

1. **社交媒体**
   - Twitter/X、Facebook、LinkedIn、微博

2. **开发平台**
   - GitHub、GitLab、Gitee

3. **电商网站**
   - 淘宝、京东、Amazon

4. **SaaS 应用**
   - Slack、Discord、Notion

5. **内部系统**
   - 企业 OA、CRM、ERP 系统

**示例场景**：
```
用户: 打开 GitHub 并查看我的 PR 列表
Agent: [自动登录 GitHub]
       [导航到 Pull Requests 页面]
       [提取 PR 列表]

用户: 检查淘宝订单状态
Agent: [自动登录淘宝]
       [进入我的订单]
       [提取订单信息]
```

---

## 技术选型

### 选择：直接使用 Playwright Python

**理由**：
- 官方支持，稳定性高，API 清晰
- 与现有 Tool 体系无缝集成，无需额外抽象层
- 完全控制 snapshot → act 实现，符合 OpenClaw 思想
- 代码简洁，易于扩展
- 依赖少，维护成本低

**不使用其他方案**：
- browser-use：已有自己的 Agent 逻辑，与 nanobot 架构冲突
- Playwright MCP：需要引入 MCP 协议，增加复杂度
- FastAPI 服务化：单机 Agent 不需要独立 Browser Server

---

## 核心架构设计

### 目录结构

```
nanobot/
  agent/
    tools/
      browser.py          # 浏览器工具（Tool 实现）
  browser/
    __init__.py
    session.py            # 浏览器会话管理
    snapshot.py           # 页面快照（ARIA 树提取）
    actions.py            # 浏览器操作（点击、输入等）
    permissions.py        # 权限控制（URL 白名单）
    credentials.py        # 凭证管理（加密存储账号密码）
```

### 关键类设计

#### 1. BrowserSession（会话管理）

**路径**：`nanobot/browser/session.py`

```python
class BrowserSession:
    """管理浏览器会话和生命周期"""

    def __init__(self, profile_dir: Path, headless: bool = True):
        self.profile_dir = profile_dir
        self.headless = headless
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self) -> None:
        """启动浏览器（使用用户数据目录持久化登录状态）"""

    async def stop(self) -> None:
        """停止浏览器并保存状态"""

    async def navigate(self, url: str, allowed_domains: list[str]) -> None:
        """导航到 URL（检查域名白名单）"""

    @property
    def page(self) -> Page:
        """获取当前页面对象"""
```

#### 2. PageSnapshot（快照提取）

**路径**：`nanobot/browser/snapshot.py`

```python
class PageSnapshot:
    """提取页面结构化信息（参考 OpenClaw 的 ARIA 树）"""

    async def capture(self, page: Page) -> dict[str, Any]:
        """捕获页面快照：
        - URL 和标题
        - ARIA 树（可访问性树）
        - 可交互元素列表（带 ID、文本、角色）
        - 页面文本摘要
        """

    def format_for_llm(self, data: dict) -> str:
        """将快照格式化为 LLM 友好的文本

        示例输出：
        页面快照 - https://mail.qq.com
        标题: QQ邮箱，常联系

        可交互元素:
        [1] button: "登录" #login-btn
        [2] textbox: "邮箱" #email-input
        [3] link: "注册" href=/register
        """
```

#### 3. BrowserActions（操作执行）

**路径**：`nanobot/browser/actions.py`

```python
class BrowserActions:
    """执行浏览器操作（Act 阶段）"""

    async def click(self, page: Page, element_id: str) -> str:
        """点击元素（支持多种选择器）"""

    async def type_text(self, page: Page, element_id: str, text: str) -> str:
        """输入文本"""

    async def wait_for_selector(self, page: Page, selector: str, timeout: int = 5000) -> bool:
        """等待元素出现"""

    async def extract_text(self, page: Page, selector: str) -> str:
        """提取元素文本内容"""

    async def screenshot(self, page: Page) -> bytes:
        """截图（调试用）"""
```

#### 4. BrowserPermission（权限控制）

**路径**：`nanobot/browser/permissions.py`

```python
class BrowserPermission:
    """浏览器访问权限控制"""

    def __init__(self, allowed_domains: list[str] | None = None):
        # 默认白名单：常见可信域名
        self.allowed_domains = allowed_domains or [
            "mail.qq.com",
            "github.com",
            "gmail.com",
            "outlook.com"
        ]

    def is_url_allowed(self, url: str) -> tuple[bool, str]:
        """检查 URL 是否在白名单中

        Returns:
            (is_allowed, error_message)
        """

    def add_domain(self, domain: str) -> None:
        """添加域名到白名单"""
```

#### 5. CredentialManager（凭证管理）

**路径**：`nanobot/browser/credentials.py`

```python
import keyring
from pathlib import Path

class CredentialManager:
    """管理网站登录凭证（加密存储）"""

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".nanobot" / "credentials.json"
        self._credentials: dict[str, dict[str, str]] = {}
        self._load_credentials()

    def get_credential(self, domain: str) -> dict[str, str] | None:
        """获取指定域名的凭证

        Returns:
            {"username": "user@qq.com", "password": "decrypted_password"} 或 None
        """

    def save_credential(self, domain: str, username: str, password: str) -> None:
        """保存凭证（使用系统密钥环加密）"""

    def delete_credential(self, domain: str) -> None:
        """删除凭证"""

    def has_credential(self, domain: str) -> bool:
        """检查是否已保存凭证"""

    def _load_credentials(self) -> None:
        """从配置文件加载凭证列表"""

    def _save_credentials(self) -> None:
        """保存凭证列表到配置文件"""
```

**安全实现细节**：
- **密码存储**：使用 `keyring` 库调用系统密钥环（Windows Credential Manager、macOS Keychain、Linux Secret Service）
- **配置文件**：仅存储用户名和元数据，不存储密码
- **加密密钥**：由操作系统管理，无需应用程序硬编码
- **权限控制**：配置文件权限设置为 `0600`（仅所有者可读写）

**依赖**：
```toml
dependencies = [
    "keyring>=25.0.0",  # 系统密钥环访问
]
```

#### 6. BrowserTool（Tool 集成）

**路径**：`nanobot/agent/tools/browser.py`

```python
from nanobot.agent.tools.base import Tool

class BrowserTool(Tool):
    """浏览器控制工具：snapshot → act 两阶段模式"""

    def __init__(self, profile_dir: Path, headless: bool = True,
                 allowed_domains: list[str] | None = None,
                 enable_auto_login: bool = False):
        self.session = BrowserSession(profile_dir, headless)
        self.snapshot = PageSnapshot()
        self.actions = BrowserActions()
        self.permission = BrowserPermission(allowed_domains)
        self.credentials = CredentialManager() if enable_auto_login else None
        self._started = False

    @property
    def name(self) -> str:
        return "browser"

    @property
    def description(self) -> str:
        return """控制浏览器进行网页交互。支持：
- snapshot: 获取页面结构和可交互元素
- navigate: 打开网页
- click: 点击元素
- type: 输入文本
- extract: 提取文本内容
- start/stop: 启动/停止浏览器
- auto_login: 自动登录（如果已配置凭证）

注意：只能访问白名单中的域名。"""

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "navigate", "snapshot", "click", "type", "extract", "auto_login"],
                    "description": "要执行的操作"
                },
                "url": {"type": "string", "description": "URL（用于 navigate）"},
                "element_id": {"type": "string", "description": "元素 ID（用于 click/type/extract）"},
                "text": {"type": "string", "description": "输入文本（用于 type）"},
                "selector": {"type": "string", "description": "CSS 选择器（用于 extract）"},
                "use_credentials": {"type": "boolean", "description": "是否使用已保存的凭证登录（用于 auto_login）"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> str:
        """执行浏览器操作"""
        if action == "auto_login":
            return await self._auto_login(**kwargs)
        # ... 其他操作
```

---

## 权限控制实现

### 配置文件

**路径**：`~/.nanobot/config.json`

```json
{
  "browser": {
    "enabled": true,
    "headless": false,
    "profileDir": "~/.nanobot/browser-profiles",
    "allowedDomains": [
      "mail.qq.com",
      "github.com",
      "gmail.com"
    ],
    "enableAutoLogin": true,
    "credentialsPath": "~/.nanobot/credentials.json"
  }
}
```

**凭证配置文件**（`~/.nanobot/credentials.json`，可选）：

```json
{
  "mail.qq.com": {
    "username": "user@qq.com",
    "autoLogin": true,
    "lastUsed": "2026-02-08T10:30:00Z"
  }
}
```

**注意**：
- 实际密码通过系统密钥环（keyring）加密存储，不在配置文件中
- `credentials.json` 仅保存用户名和元数据
- 文件权限应设置为 `600`（仅所有者可读写）

### 权限检查流程

1. **navigate 操作**：检查 URL 域名是否在 `allowedDomains` 中
2. **白名单默认值**：包含常见可信域名
3. **运行时扩展**：可通过配置添加新域名
4. **拒绝处理**：返回清晰的错误信息，说明原因

---

## QQ 邮箱场景实现流程

### 步骤 1：启动并打开登录页

```
用户: 打开 QQ 邮箱
Agent: browser(action="start")
       → "浏览器已启动（headless=false）"

Agent: browser(action="navigate", url="https://mail.qq.com")
       → "已导航到: https://mail.qq.com"

Agent: browser(action="snapshot")
       → 返回页面快照（登录按钮、二维码等）
```

**Snapshot 返回示例**：
```
页面快照 - https://mail.qq.com
标题: QQ邮箱，常联系

可交互元素:
[1] button: "扫码登录" #qr-btn
[2] button: "账号密码登录" #pwd-btn
[3] img: "二维码" #qr-code
[4] link: "注册账号" href=/register

提示: 请选择登录方式（扫码或账号密码）
```

### 步骤 2：登录方式选择

#### 选项 A：账号密码自动登录

**适用场景**：用户已将账号密码配置到 nanobot，希望自动完成登录流程

```
用户: 用账号密码登录
Agent: [从配置中读取账号密码]
       browser(action="type", element_id="email-input", text="user@qq.com")
       → "已输入邮箱: user@qq.com"

Agent: browser(action="click", element_id="next-btn")
       → "已点击下一步按钮"

Agent: browser(action="snapshot")
       → 检测到密码输入框

Agent: browser(action="type", element_id="password-input", text="***")
       → "已输入密码"

Agent: browser(action="click", element_id="login-btn")
       → "已点击登录按钮"

[等待登录完成...]

Agent: browser(action="snapshot")
       → 检测到登录成功，显示收件箱入口
```

**配置文件示例**（`~/.nanobot/credentials.json`）：
```json
{
  "mail.qq.com": {
    "username": "user@qq.com",
    "password": "encrypted_password_here",
    "autoLogin": true
  }
}
```

**安全考虑**：
- **密码加密存储**：使用系统密钥环（keyring）或环境变量存储，不明文保存
- **权限控制**：凭证文件权限设置为 `600`（仅所有者可读写）
- **可选启用**：自动登录功能默认关闭，需要用户明确配置才启用

**异常处理**：
1. **验证码**：检测到验证码时，自动切换为手动模式
   ```
   Agent: 检测到需要验证码，请手动处理
   [暂停自动化，等待用户手动输入验证码]
   ```
2. **安全验证**：需要手机验证码时，提示用户
   ```
   Agent: 需要手机验证码，请输入收到的验证码：
   用户: 123456
   Agent: [自动填入验证码并提交]
   ```
3. **登录失败**：密码错误或账号异常时，提供友好提示
   ```
   Agent: 登录失败：密码错误或账号异常
   建议：请检查账号密码配置，或切换为扫码登录
   ```

#### 选项 B：手动登录

**适用场景**：扫码登录或用户不想保存密码

```
用户: 用扫码登录
Agent: "请使用手机 QQ 扫描屏幕上的二维码"

[等待用户扫码，定期调用 snapshot 检测变化...]

Agent: browser(action="snapshot")
       → 检测到已登录，显示收件箱入口
```

**手动登录的优势**：
- ✅ 更安全：无需存储密码
- ✅ 更简单：无需处理验证码、二次验证等复杂流程
- ✅ 更通用：支持所有登录方式（扫码、人脸、指纹等）

**登录状态检测**：
- 检测 URL 变化：从登录页跳转到主页面
- 检测关键元素出现：如"收件箱"、"写邮件"等按钮
- 检测登录按钮消失：登录按钮不再显示
- 轮询间隔：每 3 秒检测一次，超时时间 2 分钟

### 步骤 3：提取邮件列表

```
Agent: browser(action="click", element_id="inbox")
Agent: browser(action="snapshot")
       → 返回邮件列表结构

Agent: browser(action="extract", selector=".mail_list")
       → 提取邮件详细信息
```

**最终输出示例**：
```
收件箱内容（共 15 封未读）：
1. GitHub - PR 评论: "Good job!" (5分钟前)
2. Amazon - 订单已发货 (1小时前)
3. 工作群 - 明天会议提醒 (昨天)
4. 订阅 - 周刊第 100 期 (2天前)
...
```

---

## 与现有代码集成

### 1. 工具注册

**修改文件**：`nanobot/agent/loop.py`

```python
from nanobot.agent.tools.browser import BrowserTool

class AgentLoop:
    def _register_default_tools(self) -> None:
        # ... 现有工具注册

        # 浏览器工具（根据配置启用）
        if self.config.browser.enabled:
            browser_tool = BrowserTool(
                profile_dir=self.config.browser.profile_dir,
                headless=self.config.browser.headless,
                allowed_domains=self.config.browser.allowed_domains
            )
            self.tools.register(browser_tool)
```

### 2. 配置 Schema

**修改文件**：`nanobot/config/schema.py`

```python
from pydantic import BaseModel

class BrowserConfig(BaseModel):
    enabled: bool = False
    headless: bool = True
    profile_dir: Path = Path.home() / ".nanobot" / "browser-profiles"
    allowed_domains: list[str] = [
        "mail.qq.com",
        "github.com"
    ]

class Config(BaseModel):
    # ... 现有配置
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
```

### 3. 依赖添加

**修改文件**：`pyproject.toml`

```toml
dependencies = [
    # ... 现有依赖
    "playwright>=1.40.0",
    "keyring>=25.0.0",  # 凭证加密存储
]

[project.optional-dependencies]
browser = [
    "playwright>=1.40.0",
    "keyring>=25.0.0",
]
```

### 4. 导出 BrowserTool

**修改文件**：`nanobot/agent/tools/__init__.py`

```python
from nanobot.agent.tools.browser import BrowserTool

__all__ = ["BrowserTool", ...]
```

---

## 实现步骤（分阶段）

### 阶段 1：基础设施（1-2天）

**目标**：能启动浏览器并访问网页

1. 添加 Playwright 依赖到 `pyproject.toml`
2. 实现 `BrowserSession` 类
   - `start()`: 启动浏览器，支持 headless 配置
   - `stop()`: 停止浏览器
   - `navigate()`: 导航到 URL
3. 单元测试：
   ```bash
   pytest tests/browser/test_session.py
   ```

**验收标准**：
- 能启动浏览器（headless 和非 headless 模式）
- 能导航到指定 URL
- 能正常关闭浏览器

### 阶段 2：核心功能（2-3天）

**目标**：实现 snapshot → act 核心能力

1. 实现 `PageSnapshot` 类
   - `capture()`: 提取 ARIA 树
   - `format_for_llm()`: 格式化输出
2. 实现 `BrowserActions` 类
   - `click()`: 点击元素
   - `type_text()`: 输入文本
   - `wait_for_selector()`: 等待元素
3. 实现 `BrowserPermission` 权限控制
   - URL 白名单检查
4. 实现 `CredentialManager` 凭证管理
   - 使用 keyring 加密存储密码
   - 配置文件读写（用户名、元数据）
   - 权限检查（文件权限 0600）
5. 实现 `BrowserTool` 完整接口
   - 集成 session、snapshot、actions、credentials
   - 实现 Tool 基类要求的方法
   - 添加 `auto_login` 操作
6. 集成到 `AgentLoop` 工具注册

**验收标准**：
- 能获取页面快照
- 能点击、输入等操作
- 权限控制生效
- 凭证能安全存储和读取
- 自动登录功能可用

### 阶段 3：QQ 邮箱场景（1-2天）

**目标**：完成初始用户场景

1. 适配 QQ 邮箱登录页
   - 识别登录按钮和二维码
   - 实现登录状态检测
2. 实现邮件列表提取
   - 定位邮件列表元素
   - 提取发件人、主题、时间
3. Profile 持久化
   - 保存登录状态
   - 重启后恢复会话
4. 调试和优化
   - 元素定位准确性
   - 超时处理
   - 错误恢复

**验收标准**：
- 能打开 QQ 邮箱登录页
- 用户扫码后能检测到登录成功
- 能提取邮件列表并格式化输出
- 登录状态持久化

### 阶段 4：增强功能（可选）

**目标**：提升稳定性和可用性

1. 截图支持（调试）
   - `screenshot()` 操作
   - 保存到文件或返回 base64
2. 智能等待
   - 自动等待元素可交互
   - 网络空闲等待
3. 错误恢复
   - 超时重试
   - 元素未找到的友好提示
4. 日志增强
   - 记录所有浏览器操作
   - 性能指标（加载时间等）

---

## 关键文件清单

### 新增文件

1. `nanobot/browser/__init__.py` - 包初始化
2. `nanobot/browser/session.py` - 会话管理（核心）
3. `nanobot/browser/snapshot.py` - 快照提取（核心）
4. `nanobot/browser/actions.py` - 操作执行
5. `nanobot/browser/permissions.py` - 权限控制
6. `nanobot/browser/credentials.py` - 凭证管理（加密存储）
7. `nanobot/agent/tools/browser.py` - Tool 实现
8. `tests/browser/test_session.py` - 会话测试
9. `tests/browser/test_snapshot.py` - 快照测试
10. `tests/browser/test_credentials.py` - 凭证测试

### 修改文件

1. `nanobot/agent/loop.py` - 注册浏览器工具
2. `nanobot/config/schema.py` - 添加 BrowserConfig
3. `nanobot/agent/tools/__init__.py` - 导出 BrowserTool
4. `pyproject.toml` - 添加 Playwright 依赖

---

## 依赖安装

```bash
# 安装依赖
pip install playwright

# 安装 Chromium 浏览器（二进制）
playwright install chromium

# 开发环境安装（带浏览器）
pip install -e ".[browser]"
```

---

## 测试验证

### 单元测试

```bash
# 测试会话管理
pytest tests/browser/test_session.py -v

# 测试快照提取
pytest tests/browser/test_snapshot.py -v

# 测试完整流程
pytest tests/browser/test_integration.py -v
```

### 手动测试

```bash
# 启动 nanobot
nanobot agent

# 对话测试
用户: 打开 QQ 邮箱
用户: 查看收件箱
用户: 提取第一封邮件的内容
```

---

## 设计原则

### 优点

1. **简洁性**：直接使用 Playwright，无额外抽象层
2. **集成性**：完美融入现有 Tool 体系
3. **可扩展性**：易于添加新操作（滚动、下拉等）
4. **可调试性**：支持非 headless 模式，人工介入
5. **持久化**：Profile 支持登录状态保存
6. **安全性**：
   - 白名单机制控制访问域名
   - 密码通过系统密钥环加密存储
   - 配置文件权限严格控制
   - 自动登录功能可选启用

### 两种登录方式对比

| 特性 | 账号密码自动登录 | 手动登录 |
|------|-----------------|---------|
| **便利性** | ⭐⭐⭐⭐⭐ 完全自动化 | ⭐⭐⭐ 需要人工介入 |
| **安全性** | ⭐⭐⭐ 需要存储密码 | ⭐⭐⭐⭐⭐ 无需存储密码 |
| **通用性** | ⭐⭐⭐ 可能需要处理验证码 | ⭐⭐⭐⭐⭐ 支持所有登录方式 |
| **维护成本** | ⭐⭐ 需要适配不同网站 | ⭐⭐⭐⭐⭐ 无需维护 |
| **推荐场景** | 频繁访问同一网站 | 安全敏感或偶尔访问 |

**建议**：
- 开发/测试环境：使用自动登录提高效率
- 生产环境：默认使用手动登录，安全优先
- 混合使用：提供选项让用户根据场景选择

### 权衡

1. **单进程**：浏览器与 Agent 同进程，不适合分布式
2. **单例限制**：一次一个浏览器会话（后续可扩展）
3. **资源占用**：浏览器需要较多内存（~200MB）
4. **凭证依赖**：自动登录需要依赖系统密钥环，某些环境可能不可用

---

## 示例对话流程

### 示例 1：自动登录（已配置凭证）

```
用户: 帮我查看 QQ 邮箱的收件箱

Agent: [调用 browser(action="start", headless=false)]
      浏览器已启动（非 headless 模式）

Agent: [调用 browser(action="navigate", url="https://mail.qq.com")]
      已导航到 QQ 邮箱

Agent: [调用 browser(action="snapshot")]
      页面显示扫码登录和账号密码登录选项。

Agent: 检测到已保存的登录凭证，是否使用自动登录？
      用户: 是

Agent: [调用 browser(action="auto_login", use_credentials=true)]
      正在使用已保存的账号登录...
      已输入邮箱: ***@qq.com
      已输入密码: ****
      正在提交登录表单...

Agent: [调用 browser(action="snapshot")]
      检测到登录成功，正在进入收件箱...

Agent: [调用 browser(action="click", element_id="inbox")]
      [调用 browser(action="extract", selector=".mail_list")]

      收件箱内容（共 15 封未读）：
      1. GitHub - "PR 评论: Good job!" (5分钟前)
      2. Amazon - "订单已发货" (1小时前)
      3. 工作群 - "明天会议提醒" (昨天)
      4. 订阅 - "周刊第 100 期" (2天前)
      ...
```

### 示例 2：手动登录（扫码）

```
用户: 帮我查看 QQ 邮箱的收件箱

Agent: [调用 browser(action="start", headless=false)]
      浏览器已启动（非 headless 模式）

Agent: [调用 browser(action="navigate", url="https://mail.qq.com")]
      已导航到 QQ 邮箱

Agent: [调用 browser(action="snapshot")]
      页面显示扫码登录和账号密码登录选项。

Agent: 请选择登录方式：扫码登录或账号密码登录？

用户: 扫码登录

Agent: 请使用手机 QQ 扫描屏幕上的二维码

[Agent 每 3 秒调用一次 snapshot 检测登录状态...]

Agent: [调用 browser(action="snapshot")]
      检测到已登录，正在进入收件箱...

Agent: [调用 browser(action="click", element_id="inbox")]
      [调用 browser(action="extract", selector=".mail_list")]

      收件箱内容（共 15 封未读）：
      1. GitHub - "PR 评论: Good job!" (5分钟前)
      2. Amazon - "订单已发货" (1小时前)
      3. 工作群 - "明天会议提醒" (昨天)
      4. 订阅 - "周刊第 100 期" (2天前)
      ...
```

---

## 后续扩展方向

### 短期扩展（1-2个月）

1. **网站适配器库**
   - 实现常见邮箱适配器（Gmail、Outlook、163）
   - 实现社交媒体适配器（GitHub、Twitter、LinkedIn）
   - 提供适配器模板和开发文档

2. **多账号管理**
   - 支持同一网站多个账号（如工作/个人邮箱）
   - 账号切换功能
   - 账号分组和标签

3. **智能登录流程**
   - 自动识别登录表单类型
   - 自动处理常见验证码（OCR识别）
   - 智能等待和重试机制

4. **操作录制与回放**
   - 录制用户操作序列
   - 保存为可复用的脚本
   - 支持参数化（如不同账号）

### 中期扩展（3-6个月）

5. **多标签页管理**
   - 同时操作多个页面
   - 标签页间数据传递
   - 并发操作控制

6. **文件操作**
   - 文件下载处理
   - 文件上传（如附件）
   - 截图和 PDF 导出

7. **复杂交互支持**
   - 拖拽操作
   - 右键菜单
   - 键盘快捷键
   - 滚动和分页

8. **会话管理增强**
   - 多 Profile 支持（独立浏览器实例）
   - 会话持久化（保存/恢复状态）
   - 代理配置（支持不同代理）

### 长期愿景（6-12个月）

9. **视觉 AI 增强**
   - 结合计算机视觉识别元素
   - 处理动态内容和 Canvas
   - 验证码智能识别

10. **工作流编排**
    - 支持复杂的多步骤任务
    - 条件分支和循环
    - 错误恢复和回滚

11. **分布式执行**
    - 支持多机器并行执行
    - 任务队列和调度
    - 负载均衡

12. **凭证管理增强**
    - 支持多个账号（同一网站多个账号）
    - 凭证过期自动提醒
    - OAuth/Token 认证支持
    - 跨设备同步凭证（加密云端备份）

13. **MCP 协议支持**
    - 对外提供 Browser Server
    - 支持远程调用
    - 多租户隔离

### 应用场景扩展

**个人助理**：
- 自动登录银行/信用卡网站查看账单
- 社交媒体账号管理（发布、查看、回复）
- 订阅和会员管理（续费提醒、优惠信息）

**开发工具**：
- 自动化测试（Web 应用 E2E 测试）
- CI/CD 集成（自动部署后验证）
- 爬虫和数据采集（合规前提下）

**企业应用**：
- RPA（机器人流程自动化）
- 数据录入和报表生成
- 客户服务（自动查询订单、物流）
- 运维自动化（服务器后台操作）

---

## 与现有方案的对比

---

## 与现有方案的对比

### vs. browser-use

| 特性 | nanobot (本方案) | browser-use |
|------|----------------|------------|
| **架构** | 无侵入，纯 Tool 集成 | 内置 Agent 逻辑 |
| **控制权** | 完全控制，可定制 | 遵循其设计模式 |
| **多步骤规划** | 由 LLM 自主决定 | 由其 Planner 控制 |
| **适用场景** | 已有 Agent 系统，只需浏览器能力 | 从零构建浏览器 Agent |
| **学习曲线** | 低（熟悉 Tool 即可） | 中（需理解其概念） |
| **灵活性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**结论**：如果你已经在使用 nanobot 或其他 Agent 框架，本方案更合适。如果要独立开发浏览器 Agent，browser-use 更现成。

### vs. Selenium / 传统自动化

| 特性 | nanobot (本方案) | Selenium |
|------|----------------|---------|
| **AI 驱动** | ✅ LLM 理解页面语义 | ❌ 需硬编码选择器 |
| **适应性** | ✅ 页面改版不受影响 | ❌ 需维护选择器 |
| **易用性** | ✅ 自然语言交互 | ❌ 编写代码 |
| **执行速度** | ⭐⭐⭐（LLM 调用开销） | ⭐⭐⭐⭐⭐ |
| **适用场景** | 动态、复杂页面 | 稳定、重复性任务 |

**结论**：传统自动化适合固定流程，本方案适合需要理解和适应的动态任务。

### vs. Puppeteer / Playwright 脚本

| 特性 | nanobot (本方案) | 脚本方式 |
|------|----------------|---------|
| **开发效率** | ⭐⭐⭐⭐⭐（对话即程序） | ⭐⭐（需编码调试） |
| **维护成本** | ⭐⭐⭐⭐⭐（自动适应） | ⭐⭐（页面改版需修改） |
| **可扩展性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **执行速度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **学习门槛** | ⭐⭐⭐⭐⭐（无需编程） | ⭐⭐（需编程知识） |

**结论**：脚本适合高性能、大规模执行；本方案适合快速原型和灵活任务。

### 独特优势

1. **与 Agent 深度集成**
   - 不是独立的浏览器工具，而是 Agent 的一个能力
   - 可以与其他工具（文件系统、数据库、API）协同工作
   - 统一的消息流和上下文管理

2. **对话式编程**
   - 用户用自然语言描述需求
   - Agent 自动规划执行步骤
   - 实时反馈和调整

3. **智能适应**
   - 页面结构变化时自动重新理解
   - 无需维护复杂的选择器
   - 支持多种登录方式自动选择

4. **渐进式自动化**
   - 从手动登录开始
   - 逐步添加自动化能力
   - 按需配置凭证

5. **安全和可控**
   - 域名白名单限制访问范围
   - 凭证加密存储
   - 操作审计日志

---

## 参考资料

- [浏览器选型.md](./浏览器选型.md) - 详细的 Python 浏览器 Agent 方案选型参考
- [OpenClaw GitHub](https://github.com/openclaw/openclaw) - TypeScript 参考实现
- [Playwright Python 文档](https://playwright.dev/python/docs/intro)
- [nanobot 架构](./README.md) - 项目整体架构说明

---

**文档版本**: 1.1
**创建日期**: 2026-02-08
**最后更新**: 2026-02-08

---

## 常见问题

### Q1: 这个方案只能用于 QQ 邮箱吗？

**A:** 不是！这是一个**通用的浏览器自动化方案**，QQ 邮箱只是初始示例场景。它可以支持：
- ✅ 所有 Web 邮箱（Gmail、Outlook、163、Yahoo 等）
- ✅ 所有需要登录的网站（GitHub、Twitter、淘宝等）
- ✅ 企业内部系统（OA、CRM、ERP）

### Q2: 如何添加对新网站的支持？

**A:** 三种方式，从简单到复杂：

1. **仅添加域名白名单**（最简单）
   ```json
   {"allowedDomains": ["mail.qq.com", "github.com"]}
   ```

2. **使用通用登录流程**（适合简单表单）
   - 系统自动识别输入框和按钮
   - 无需编写代码

3. **编写适配器**（适合复杂登录）
   ```python
   class GitHubAdapter(WebsiteAdapter):
       domain = "github.com"
       async def perform_login(self, page, username, password):
           # GitHub 特定的登录逻辑
   ```

### Q3: 不同网站的登录流程差异很大怎么办？

**A:**
- 对于常见网站，提供预置适配器
- 对于特殊网站，支持手动登录作为后备
- 适配器可以逐步完善，无需一次性完美

### Q4: 如何处理网站的验证码和二次验证？

**A:**
- 检测到验证码时自动切换到手动模式
- 提示用户手动处理，然后继续自动化
- 后续可集成 OCR 验证码识别

### Q5: 支持移动端网站吗？

**A:**
- 支持！Playwright 可以模拟移动设备
- 配置不同的 User Agent 和视口大小
- 可以同时支持桌面端和移动端

### Q6: 性能如何？比 Selenium 快吗？

**A:**
- 单次执行：比 Selenium/脚本慢（有 LLM 调用开销）
- 开发效率：比 Selenium 快很多（无需编码调试）
- 维护成本：比 Selenium 低很多（自动适应页面变化）
- **适用场景不同**：本方案不是用来替代传统自动化的，而是提供 AI 驱动的灵活性

### Q7: 可以同时操作多个浏览器吗？

**A:**
- 当前版本：单个浏览器实例
- 后续扩展：支持多 Profile 和多标签页
- 可以实现多个网站并行操作

### Q8: 凭证安全吗？会被盗号吗？

**A:**
- ✅ 密码使用系统密钥环加密（Windows Credential Manager、macOS Keychain）
- ✅ 配置文件权限严格限制（0600）
- ✅ 域名白名单防止钓鱼网站
- ✅ 所有操作可审计
- ⚠️ 建议使用独立账号，避免使用主账号

### Q9: 商业使用有限制吗？

**A:**
- 本方案是开源的，可自由使用和修改
- Playwright 本身是开源的
- 请遵守目标网站的服务条款（ToS）
- 不要用于恶意爬虫或攻击

### Q10: 下一步如何开始？

**A:**
1. 查看实现步骤中的"阶段 1：基础设施"
2. 安装依赖：`pip install playwright && playwright install chromium`
3. 实现核心类：`BrowserSession`、`PageSnapshot`、`BrowserActions`
4. 用 QQ 邮箱作为第一个测试场景
5. 逐步添加更多网站支持

---

## 总结

这是一个**通用的 AI 驱动浏览器自动化方案**，具有以下特点：

1. **不限于邮箱** - 可以自动化任何基于 Web 的操作
2. **渐进式支持** - 从手动登录开始，逐步添加自动化
3. **适配器模式** - 灵活支持不同网站的特定需求
4. **安全可控** - 白名单、加密存储、审计日志
5. **易于扩展** - 清晰的架构，便于添加新功能

**核心优势**：让你用自然语言控制浏览器，而不是编写复杂的自动化脚本。

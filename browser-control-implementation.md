# nanobot 浏览器控制功能实现计划

## Context

为实现 Agent 控制浏览器进行网页交互的能力，需要在 nanobot 项目中集成浏览器自动化功能。

**初始场景**：打开 QQ 邮箱登录页面，支持用户手动登录（扫码/账号密码），登录后提取收件箱邮件列表（发件人、主题、时间、摘要）。

**设计理念**：参考 OpenClaw 的 **snapshot → act 两阶段模式**，但适配 Python 和 nanobot 的 Tool 架构。

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

#### 5. BrowserTool（Tool 集成）

**路径**：`nanobot/agent/tools/browser.py`

```python
from nanobot.agent.tools.base import Tool

class BrowserTool(Tool):
    """浏览器控制工具：snapshot → act 两阶段模式"""

    def __init__(self, profile_dir: Path, headless: bool = True,
                 allowed_domains: list[str] | None = None):
        self.session = BrowserSession(profile_dir, headless)
        self.snapshot = PageSnapshot()
        self.actions = BrowserActions()
        self.permission = BrowserPermission(allowed_domains)
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

注意：只能访问白名单中的域名。"""

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "navigate", "snapshot", "click", "type", "extract"],
                    "description": "要执行的操作"
                },
                "url": {"type": "string", "description": "URL（用于 navigate）"},
                "element_id": {"type": "string", "description": "元素 ID（用于 click/type/extract）"},
                "text": {"type": "string", "description": "输入文本（用于 type）"},
                "selector": {"type": "string", "description": "CSS 选择器（用于 extract）"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> str:
        """执行浏览器操作"""
        # 实现各种操作的逻辑
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
    ]
  }
}
```

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

### 步骤 2：用户手动登录

```
用户: 用扫码登录
Agent: "请使用手机 QQ 扫描屏幕上的二维码"

[等待用户扫码，定期调用 snapshot 检测变化...]

Agent: browser(action="snapshot")
       → 检测到已登录，显示收件箱入口
```

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
]

[project.optional-dependencies]
browser = [
    "playwright>=1.40.0",
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
3. 实现 `BrowserTool` 完整接口
   - 集成 session、snapshot、actions
   - 实现 Tool 基类要求的方法
4. 实现 `BrowserPermission` 权限控制
   - URL 白名单检查
5. 集成到 `AgentLoop` 工具注册

**验收标准**：
- 能获取页面快照
- 能点击、输入等操作
- 权限控制生效

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
6. `nanobot/agent/tools/browser.py` - Tool 实现
7. `tests/browser/test_session.py` - 会话测试
8. `tests/browser/test_snapshot.py` - 快照测试

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
6. **安全性**：白名单机制控制访问

### 权衡

1. **单进程**：浏览器与 Agent 同进程，不适合分布式
2. **单例限制**：一次一个浏览器会话（后续可扩展）
3. **资源占用**：浏览器需要较多内存（~200MB）

---

## 示例对话流程

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

1. **多 Profile**：支持多个独立账号
2. **多标签页**：同时操作多个页面
3. **文件下载**：处理下载操作
4. **表单提交**：智能填充复杂表单
5. **智能等待**：基于页面状态的动态等待
6. **视觉定位**：结合截图的元素定位
7. **MCP 协议**：对外提供 Browser Server

---

## 参考资料

- [浏览器选型.md](./浏览器选型.md) - 详细的 Python 浏览器 Agent 方案选型参考
- [OpenClaw GitHub](https://github.com/openclaw/openclaw) - TypeScript 参考实现
- [Playwright Python 文档](https://playwright.dev/python/docs/intro)
- [nanobot 架构](./README.md) - 项目整体架构说明

---

**文档版本**: 1.0
**创建日期**: 2026-02-08
**最后更新**: 2026-02-08

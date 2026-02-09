# Proposal: Add Browser Control

## Why

Agent 需要能够控制浏览器与网页进行交互，以实现自动化任务（如自动登录邮箱、提取信息、操作 Web 应用）。当前 nanobot 只能通过 HTTP API 访问 Web，无法处理需要浏览器环境才能完成的复杂交互流程（如扫码登录、动态加载的内容、需要 JavaScript 执行的操作）。

**初始场景**：打开 QQ 邮箱登录页面，支持用户手动登录（扫码/账号密码），登录后提取收件箱邮件列表（发件人、主题、时间、摘要）。

**通用性目标**：不仅支持 QQ 邮箱，还能支持所有基于 Web 的邮箱（Gmail、Outlook、163 等）和任何需要登录的 Web 系统。

## What Changes

### 核心功能添加

- **Playwright 集成**：添加 Playwright 作为核心依赖，提供浏览器自动化能力
- **浏览器会话管理**：实现 BrowserSession 类，管理浏览器生命周期（启动、导航、停止、持久化）
- **页面快照（Snapshot）**：实现 PageSnapshot 类，提取页面结构（ARIA 树、可交互元素），为 LLM 理解页面提供结构化数据
- **浏览器操作（Actions）**：实现 BrowserActions 类，提供点击、输入、等待、提取文本等基础操作
- **权限控制**：实现 URL 白名单机制，限制可访问的域名，确保安全性
- **凭证管理**：使用 keyring 加密存储登录凭证（密码），支持自动登录功能
- **Tool 集成**：创建 BrowserTool，将浏览器能力集成到现有 Tool 体系

### 适配器模式（混合策略）

- **适配器基类**：定义 WebsiteAdapter 接口，支持特定网站的定制化登录流程
- **三层登录策略**：
  1. **专用适配器**：高频网站（QQ 邮箱等）使用专用适配器，保证成功率
  2. **通用登录**：启发式规则 + AI 辅助，处理 60-70% 的标准登录表单
  3. **手动登录**：万能兜底，支持扫码/用户手动输入，自动检测登录完成
- **适配器注册表**：管理所有适配器，支持内置和用户自定义适配器
- **初始适配器**：提供 QQ 邮箱适配器作为完整示例

### 配置和集成

- **配置 Schema**：添加 BrowserConfig 到 nanobot 配置系统
- **AgentLoop 集成**：在 AgentLoop 中注册 BrowserTool（根据配置启用）
- **依赖管理**：添加 `playwright` 和 `keyring` 到 pyproject.toml

## Capabilities

### New Capabilities

- **browser-automation**: 浏览器自动化核心能力，包括会话管理、页面导航、元素操作、快照提取
- **web-authentication**: Web 登录和认证能力，支持适配器模式、通用登录、手动登录三种策略
- **credential-management**: 凭证管理能力，加密存储网站登录凭证，支持自动登录

### Modified Capabilities

None (no existing spec requirements are changing)

## Impact

### 新增依赖

- `playwright>=1.40.0`: 浏览器自动化库
- `keyring>=25.0.0`: 系统密钥环访问，用于加密存储密码

### 新增文件

```
nanobot/
├── browser/                      # 新增浏览器模块
│   ├── __init__.py
│   ├── session.py               # 会话管理
│   ├── snapshot.py              # 页面快照
│   ├── actions.py               # 浏览器操作
│   ├── permissions.py           # 权限控制
│   ├── credentials.py           # 凭证管理
│   └── adapters/                # 适配器
│       ├── __init__.py
│       ├── base.py              # 适配器基类
│       ├── registry.py          # 适配器注册
│       ├── qq_mail.py           # QQ 邮箱适配器
│       └── generic.py           # 通用登录适配器
└── agent/
    └── tools/
        └── browser.py           # BrowserTool 实现
```

### 修改文件

- `nanobot/agent/loop.py`: 在 `_register_default_tools()` 中注册 BrowserTool
- `nanobot/config/schema.py`: 添加 BrowserConfig 类
- `nanobot/agent/tools/__init__.py`: 导出 BrowserTool
- `pyproject.toml`: 添加 playwright 和 keyring 依赖

### 配置变更

用户需要安装 Chromium 浏览器二进制文件：
```bash
playwright install chromium
```

新增配置项（`~/.nanobot/config.json`）：
```json
{
  "browser": {
    "enabled": true,
    "headless": true,
    "profileDir": "~/.nanobot/browser-profiles",
    "allowedDomains": ["mail.qq.com", "github.com", "gmail.com"],
    "autoLoginDomains": [],
    "credentialsPath": "~/.nanobot/credentials.json",
    "timeout": 30000
  }
}
```

### API 变更

无破坏性变更。BrowserTool 作为可选工具，默认关闭，需要配置 `browser.enabled=true` 才启用。

### 安全考虑

- **URL 白名单**：通过 `allowedDomains` 限制可访问的域名，防止访问恶意网站
- **凭证加密**：使用系统密钥环（keyring）加密存储密码，不在配置文件中明文保存
- **权限控制**：凭证文件权限设置为 0600（仅所有者可读写）
- **可选自动登录**：自动登录功能默认关闭，需要用户明确配置才启用

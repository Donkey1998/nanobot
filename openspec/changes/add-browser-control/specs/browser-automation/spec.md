# Spec: Browser Automation

## ADDED Requirements

### Requirement: Browser session lifecycle management

系统必须提供完整的浏览器会话管理能力，包括启动、导航、停止和持久化。

#### Scenario: 启动新的浏览器会话
- **WHEN** 用户请求启动浏览器并指定目标域名
- **THEN** 系统应当启动 Chromium 浏览器实例
- **AND** 系统应当创建或加载该域名的持久化配置文件
- **AND** 系统应当返回会话标识符

#### Scenario: 导航到指定 URL
- **WHEN** 用户使用有效的会话标识符请求导航到 URL
- **AND** 该 URL 的域名在白名单中
- **THEN** 系统应当导航到指定 URL
- **AND** 系统应当等待页面加载完成

#### Scenario: 停止浏览器会话
- **WHEN** 用户请求停止会话
- **THEN** 系统应当关闭浏览器实例
- **AND** 系统应当保存会话状态（Cookie、LocalStorage）

#### Scenario: 访问白名单之外的域名
- **WHEN** 用户请求导航到 URL
- **AND** 该 URL 的域名不在白名单中
- **THEN** 系统应当拒绝请求并返回错误
- **AND** 错误信息必须包含被拒绝的域名

### Requirement: Page snapshot extraction

系统必须能够提取页面的结构化快照，包含可交互元素的语义信息。

#### Scenario: 提取页面 ARIA 树
- **WHEN** 用户请求页面快照
- **THEN** 系统应当返回页面的可访问性树（accessibility tree）
- **AND** 快照必须包含每个元素的角色（role）、名称（name）、状态（states）
- **AND** 快照必须包含元素的层次结构

#### Scenario: 快照包含可交互元素
- **WHEN** 页面包含链接、按钮、表单字段
- **THEN** 快照必须标识所有可交互元素
- **AND** 每个元素必须包含可用于定位的属性（如 aria-label、id、data-testid）

#### Scenario: 快照过滤隐藏元素
- **WHEN** 页面包含 `display: none` 或 `aria-hidden="true"` 的元素
- **THEN** 快照不应包含这些隐藏元素
- **AND** 快照不应包含装饰性内容

#### Scenario: 等待动态内容加载
- **WHEN** 页面包含异步加载的内容
- **THEN** 系统应当在快照前等待网络空闲（networkidle）
- **AND** 系统应当提供可配置的超时时间

### Requirement: Browser actions execution

系统必须提供基础浏览器操作，包括点击、输入、等待和文本提取。

#### Scenario: 点击元素
- **WHEN** 用户请求点击指定的可交互元素
- **AND** 元素在页面中可见且可点击
- **THEN** 系统应当执行点击操作
- **AND** 系统应当等待导航或网络操作完成

#### Scenario: 输入文本到表单字段
- **WHEN** 用户请求在指定的输入框中输入文本
- **AND** 输入框可见且可编辑
- **THEN** 系统应当清除输入框的现有内容
- **AND** 系统应当输入指定文本
- **AND** 系统应当触发输入事件（确保前端框架捕获变化）

#### Scenario: 等待元素出现
- **WHEN** 用户请求等待指定的元素出现
- **THEN** 系统应当轮询检查元素是否出现在 DOM 中
- **AND** 如果元素在超时时间内出现，系统应当返回成功
- **AND** 如果超时，系统应当返回失败

#### Scenario: 提取元素文本
- **WHEN** 用户请求提取指定元素的文本内容
- **AND** 元素存在于页面中
- **THEN** 系统应当返回元素的可见文本
- **AND** 系统应当去除多余的空白字符

#### Scenario: 操作不存在的元素
- **WHEN** 用户请求操作不存在的元素
- **THEN** 系统应当返回错误
- **AND** 错误信息必须包含元素定位符和超时时间

### Requirement: URL whitelist enforcement

系统必须通过白名单机制限制可访问的域名。

#### Scenario: 允许访问白名单域名
- **WHEN** 用户请求导航到白名单中的域名
- **THEN** 系统应当允许访问
- **AND** 系统应当正常执行操作

#### Scenario: 拒绝访问非白名单域名
- **WHEN** 用户请求导航到不在白名单中的域名
- **THEN** 系统应当拒绝请求
- **AND** 系统应当返回 PermissionDenied 错误

#### Scenario: 支持通配符域名
- **WHEN** 白名单配置为 `*.example.com`
- **THEN** 系统应当允许访问 `mail.example.com`
- **AND** 系统应当允许访问 `docs.example.com`
- **AND** 系统应当拒绝访问 `evil.com`

#### Scenario: 白名单为空时拒绝所有访问
- **WHEN** 白名单配置为空数组
- **THEN** 系统应当拒绝所有域名访问请求

### Requirement: Browser profile persistence

系统必须持久化浏览器配置文件以保存会话状态。

#### Scenario: 首次访问创建新配置文件
- **WHEN** 用户首次访问特定域名
- **THEN** 系统应当在 `~/.nanobot/browser-profiles/<domain>/` 创建新配置文件
- **AND** 系统应当使用该配置文件启动浏览器

#### Scenario: 后续访问加载现有配置文件
- **WHEN** 用户后续访问相同域名
- **THEN** 系统应当加载该域名的现有配置文件
- **AND** 系统应当恢复之前的 Cookie 和 LocalStorage

#### Scenario: 配置文件隔离
- **WHEN** 用户访问 `mail.example.com` 和 `docs.example.com`
- **THEN** 系统应当为每个域名创建独立的配置文件
- **AND** 两个域名的会话状态不应互相影响

### Requirement: Browser configuration

系统必须提供配置选项以控制浏览器行为。

#### Scenario: 配置无头模式
- **WHEN** 用户配置 `browser.headless: true`
- **THEN** 浏览器应当以无头模式启动（不显示窗口）
- **AND** 当配置为 `false` 时，浏览器应当显示窗口

#### Scenario: 配置超时时间
- **WHEN** 用户配置 `browser.timeout: 30000`
- **THEN** 所有浏览器操作应当使用该超时时间
- **AND** 超时时应当返回 TimeoutError

#### Scenario: 配置数据目录
- **WHEN** 用户配置 `browser.profileDir: "/custom/path"`
- **THEN** 系统应当使用指定路径存储浏览器配置文件

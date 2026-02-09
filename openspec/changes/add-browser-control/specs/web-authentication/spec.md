# Spec: Web Authentication

## ADDED Requirements

### Requirement: Website adapter interface

系统必须定义统一的网站适配器接口，支持特定网站的定制化登录流程。

#### Scenario: 适配器实现登录方法
- **WHEN** 开发者创建网站适配器
- **THEN** 适配器必须实现 `login()` 方法
- **AND** 适配器必须接受 BrowserSession 实例作为参数
- **AND** 适配器必须返回登录结果（成功/失败）

#### Scenario: 适配器支持凭证获取
- **WHEN** 适配器需要用户凭证
- **THEN** 适配器必须能够从 CredentialManager 获取用户名和密码
- **AND** 如果凭证不存在，适配器必须提示用户输入

#### Scenario: 适配器验证登录成功
- **WHEN** 适配器完成登录流程
- **THEN** 适配器必须验证用户已成功登录
- **AND** 验证方法可以包括：检查特定 URL、查找特定元素、检测 Cookie

### Requirement: Adapter registry

系统必须提供适配器注册表，管理所有可用的网站适配器。

#### Scenario: 注册内置适配器
- **WHEN** 系统启动
- **THEN** 系统必须自动注册所有内置适配器
- **AND** 内置适配器必须包括 QQ 邮箱适配器

#### Scenario: 用户注册自定义适配器
- **WHEN** 用户创建自定义适配器类
- **THEN** 用户必须能够通过注册表注册适配器
- **AND** 注册时必须指定适配器处理的域名模式

#### Scenario: 查找匹配的适配器
- **WHEN** 系统需要处理特定域名的登录
- **THEN** 系统必须查询注册表查找匹配的适配器
- **AND** 如果找到多个匹配适配器，系统必须选择最具体的匹配（优先精确匹配）

#### Scenario: 未找到适配器
- **WHEN** 系统查询注册表未找到匹配的适配器
- **THEN** 系统必须返回 None 或空结果

### Requirement: Three-tier login strategy

系统必须实现三层登录策略：专用适配器 → 通用登录 → 手动登录。

#### Scenario: 使用专用适配器登录
- **WHEN** 系统找到匹配的专用适配器
- **THEN** 系统必须使用该适配器执行登录
- **AND** 如果适配器登录失败，系统必须回退到通用登录

#### Scenario: 使用通用登录
- **WHEN** 未找到专用适配器
- **OR** 专用适配器登录失败
- **THEN** 系统必须尝试通用登录流程
- **AND** 通用登录必须使用启发式规则查找登录表单
- **AND** 通用登录必须能够填写用户名和密码字段
- **AND** 如果通用登录失败，系统必须回退到手动登录

#### Scenario: 使用手动登录
- **WHEN** 专用适配器和通用登录都失败
- **OR** 用户主动选择手动登录
- **THEN** 系统必须打开登录页面
- **AND** 系统必须提示用户手动完成登录
- **AND** 系统必须定期检测登录是否完成
- **AND** 用户必须能够确认登录完成

### Requirement: Generic login heuristics

通用登录必须使用启发式规则识别和处理标准登录表单。

#### Scenario: 识别登录表单
- **WHEN** 页面包含登录表单
- **THEN** 系统必须查找包含以下特征的表单：
  - `<form>` 元素，action 包含 "login" 或 "signin"
  - 包含 `type="password"` 的输入框
  - 包含 `type="text"` 或 `type="email"` 的输入框

#### Scenario: 填写凭证
- **WHEN** 系统识别出登录表单
- **AND** 用户提供用户名和密码
- **THEN** 系统必须填写用户名字段（查找 name/email/username 相关属性）
- **AND** 系统必须填写密码字段
- **AND** 系统必须点击提交按钮（查找 type="submit" 或文本包含 "登录"/"Sign in"）

#### Scenario: 处理记住登录选项
- **WHEN** 登录表单包含"记住我"复选框
- **THEN** 系统必须勾选该选项
- **AND** 系统必须确保后续访问保持登录状态

#### Scenario: 登录失败重试
- **WHEN** 通用登录后检测到错误消息
- **THEN** 系统必须记录失败
- **AND** 系统必须回退到手动登录

### Requirement: Manual login detection

系统必须能够检测用户手动完成登录的状态。

#### Scenario: 检测 URL 变化
- **WHEN** 用户手动完成登录
- **AND** 登录后页面跳转到新的 URL
- **THEN** 系统必须检测到 URL 变化
- **AND** 系统必须判断登录已完成

#### Scenario: 检测特定元素出现
- **WHEN** 登录成功后页面出现特定元素（如用户头像、欢迎消息）
- **THEN** 系统必须检测到该元素
- **AND** 系统必须判断登录已完成

#### Scenario: 检测 Cookie 变化
- **WHEN** 用户手动完成登录
- **AND** 网站设置认证 Cookie
- **THEN** 系统必须检测到新的认证相关 Cookie
- **AND** 系统必须判断登录已完成

#### Scenario: 用户手动确认
- **WHEN** 自动检测不可靠
- **THEN** 系统必须提供"我已完成登录"按钮
- **AND** 用户点击按钮后，系统必须继续执行后续操作

### Requirement: QQ Mail adapter

系统必须提供 QQ 邮箱专用适配器作为完整示例。

#### Scenario: QQ 邮箱自动登录
- **WHEN** 用户使用 QQ 邮箱适配器
- **AND** 用户提供 QQ 号码和密码
- **THEN** 适配器必须导航到 `mail.qq.com`
- **AND** 适配器必须填写 QQ 号码和密码
- **AND** 适配器必须处理可能的验证码（提示用户输入）
- **AND** 适配器必须验证登录成功

#### Scenario: QQ 邮箱扫码登录
- **WHEN** 用户选择扫码登录
- **THEN** 适配器必须点击"扫码登录"选项
- **AND** 适配器必须显示二维码
- **AND** 适配器必须等待用户使用手机 QQ 扫码
- **AND** 适配器必须检测登录成功

#### Scenario: QQ 邮箱登录验证
- **WHEN** QQ 邮箱登录流程完成
- **THEN** 适配器必须验证当前 URL 包含登录后的路径
- **AND** 适配器必须验证页面包含收件箱元素

### Requirement: Login state verification

系统必须验证用户是否已成功登录。

#### Scenario: 验证成功登录
- **WHEN** 登录流程完成
- **THEN** 系统必须验证登录状态
- **AND** 验证方法可以包括：
  - 检查 URL 是否匹配预期模式
  - 查找特定元素（如用户名、登出按钮）
  - 检查认证 Cookie 是否存在
  - 尝试访问需要认证的页面

#### Scenario: 登录失败处理
- **WHEN** 验证发现登录未成功
- **THEN** 系统必须返回登录失败错误
- **AND** 错误信息必须包含失败原因
- **AND** 系统必须提供重试选项

### Requirement: Auto-login configuration

系统必须支持配置自动登录的域名。

#### Scenario: 启用自动登录
- **WHEN** 用户配置 `browser.autoLoginDomains: ["mail.qq.com", "gmail.com"]`
- **THEN** 系统必须在访问这些域名时自动尝试登录
- **AND** 系统必须从凭证管理器获取用户凭证

#### Scenario: 禁用自动登录
- **WHEN** 用户未配置 `browser.autoLoginDomains`
- **OR** 配置为空数组
- **THEN** 系统不得自动尝试登录
- **AND** 系统必须等待用户手动登录

#### Scenario: 自动登录失败回退
- **WHEN** 自动登录失败
- **THEN** 系统必须回退到手动登录
- **AND** 系统必须提示用户手动完成登录

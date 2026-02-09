# Spec: Credential Management

## ADDED Requirements

### Requirement: Secure password storage

系统必须使用系统密钥环（keyring）加密存储网站登录密码。

#### Scenario: 存储新密码
- **WHEN** 用户为特定网站保存密码
- **THEN** 系统必须使用 keyring 存储密码
- **AND** 密码不得以明文形式存储在配置文件中
- **AND** 存储键必须包含服务名称和用户名

#### Scenario: 检索已存储密码
- **WHEN** 用户需要登录已保存密码的网站
- **THEN** 系统必须从 keyring 检索密码
- **AND** 系统必须使用服务名称和用户名查找密码

#### Scenario: 密码不存在
- **WHEN** 用户尝试检索不存在的密码
- **THEN** 系统必须返回 None 或空结果
- **AND** 系统不得抛出异常

#### Scenario: 删除密码
- **WHEN** 用户请求删除特定网站的密码
- **THEN** 系统必须从 keyring 删除该密码
- **AND** 系统必须确认删除成功

### Requirement: Credential file backup

系统必须维护凭证备份文件，记录所有已保存的网站和用户名。

#### Scenario: 创建凭证文件
- **WHEN** 用户首次保存密码
- **THEN** 系统必须创建凭证文件（默认 `~/.nanobot/credentials.json`）
- **AND** 凭证文件必须包含网站域名和用户名
- **AND** 凭证文件不得包含密码明文

#### Scenario: 更新凭证文件
- **WHEN** 用户保存新密码或删除密码
- **THEN** 系统必须更新凭证文件
- **AND** 文件必须保持 JSON 格式

#### Scenario: 凭证文件权限
- **WHEN** 系统创建或更新凭证文件
- **THEN** 文件权限必须设置为 0600（仅所有者可读写）
- **AND** 在不支持的系统上，系统必须记录警告

#### Scenario: 凭证文件损坏处理
- **WHEN** 凭证文件损坏或格式错误
- **THEN** 系统必须尝试从 keyring 恢复数据
- **AND** 系统必须记录错误并继续运行

### Requirement: Credential service name format

系统必须使用统一的键格式存储和检索凭证。

#### Scenario: 服务名称格式
- **WHEN** 系统存储网站凭证
- **THEN** 服务名称必须使用格式 `nanobot-browser://<domain>`
- **AND** 用户名必须使用实际登录用户名
- **AND** 例如：`nanobot-browser://mail.qq.com`，用户名：`123456`

#### Scenario: 域名规范化
- **WHEN** 用户输入 `https://mail.qq.com/` 或 `http://mail.qq.com`
- **THEN** 系统必须规范化为 `mail.qq.com`
- **AND** 系统必须使用规范化后的域名作为服务名

### Requirement: Credential migration

系统必须支持从明文存储迁移到加密存储。

#### Scenario: 检查明文凭证
- **WHEN** 系统启动
- **THEN** 系统必须检查是否存在旧的明文凭证文件
- **AND** 如果存在，系统必须警告用户

#### Scenario: 迁移到加密存储
- **WHEN** 用户运行迁移命令
- **THEN** 系统必须读取明文凭证文件
- **AND** 系统必须将密码存储到 keyring
- **AND** 系统必须删除明文凭证文件
- **AND** 系统必须创建新的加密备份文件

#### Scenario: 迁移失败回滚
- **WHEN** 迁移过程中出现错误
- **THEN** 系统必须保留原始明文文件
- **AND** 系统必须记录详细错误信息
- **AND** 系统不得删除原始数据

### Requirement: Credential configuration

系统必须提供配置选项以控制凭证管理行为。

#### Scenario: 配置凭证文件路径
- **WHEN** 用户配置 `browser.credentialsPath: "/custom/path/credentials.json"`
- **THEN** 系统必须使用指定路径存储凭证文件

#### Scenario: 禁用自动登录
- **WHEN** 用户未配置 `browser.autoLoginDomains`
- **OR** 配置为空数组
- **THEN** 系统不得自动使用存储的凭证登录
- **AND** 系统必须等待用户手动登录或显式请求

### Requirement: Cross-platform keyring support

系统必须支持不同操作系统上的密钥环。

#### Scenario: macOS Keychain 支持
- **WHEN** 系统运行在 macOS 上
- **THEN** 系统必须使用 macOS Keychain 作为 keyring backend
- **AND** 凭证必须存储在用户的登录 Keychain 中

#### Scenario: Windows Credential Manager 支持
- **WHEN** 系统运行在 Windows 上
- **THEN** 系统必须使用 Windows Credential Manager 作为 keyring backend
- **AND** 凭证必须存储在 Windows 凭证管理器中

#### Scenario: Linux Secret Service 支持
- **WHEN** 系统运行在 Linux 上
- **AND** 系统有可用的 Secret Service API
- **THEN** 系统必须使用 Secret Service 作为 keyring backend

#### Scenario: 无头服务器回退
- **WHEN** 系统运行在无图形环境的服务器上
- **AND** 系统密钥环不可用
- **THEN** keyring 库必须自动降级到文件存储（加密）
- **AND** 系统必须记录警告信息

### Requirement: Credential security

系统必须确保凭证的安全性。

#### Scenario: 密码不在日志中暴露
- **WHEN** 系统记录操作日志
- **THEN** 日志不得包含密码明文
- **AND** 日志可以使用 `<hidden>` 或 `******` 替代密码

#### Scenario: 凭证不通过不安全通道传输
- **WHEN** 凭证在进程间传递
- **THEN** 系统必须使用安全机制（如内存传递）
- **AND** 系统不得将密码写入临时文件

#### Scenario: 内存中的密码保护
- **WHEN** 系统持有密码在内存中
- **THEN** 系统应当在使用后尽快清除密码
- **AND** 系统应当限制密码在内存中的停留时间

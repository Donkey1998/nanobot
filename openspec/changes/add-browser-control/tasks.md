# Tasks: Add Browser Control

## 1. 项目设置和依赖

- [x] 1.1 添加 `playwright>=1.40.0` 和 `keyring>=25.0.0` 到 `pyproject.toml`
- [x] 1.2 创建 `nanobot/browser/` 模块目录结构
- [x] 1.3 创建 `nanobot/browser/adapters/` 适配器子目录
- [x] 1.4 在 `nanobot/__init__.py` 中导出 browser 模块

## 2. 配置系统

- [x] 2.1 在 `nanobot/config/schema.py` 中添加 `BrowserConfig` 类
- [x] 2.2 在 `Config` 类中添加 `browser: BrowserConfig` 字段
- [ ] 2.3 更新配置文档说明新增的 browser 配置项

## 3. 浏览器会话管理

- [x] 3.1 实现 `nanobot/browser/session.py` - `BrowserSession` 类
  - 启动/停止浏览器方法
  - 会话持久化配置文件管理
  - 导航和等待加载方法
- [x] 3.2 实现域名白名单验证逻辑
- [x] 3.3 添加浏览器超时和错误处理

## 4. 页面快照

- [x] 4.1 实现 `nanobot/browser/snapshot.py` - `PageSnapshot` 类
  - 提取 ARIA 可访问性树
  - 过滤隐藏元素和装饰内容
  - 格式化快照为结构化数据
- [x] 4.2 实现动态内容等待逻辑（networkidle）
- [ ] 4.3 添加快照缓存机制（可选优化）

## 5. 浏览器操作

- [x] 5.1 实现 `nanobot/browser/actions.py` - `BrowserActions` 类
  - 点击元素（支持多种定位策略）
  - 输入文本（清除 + 输入 + 触发事件）
  - 等待元素出现
  - 提取元素文本
- [x] 5.2 实现元素定位策略（ARIA 标签、id、data-testid、CSS 选择器）
- [x] 5.3 添加操作失败的详细错误信息

## 6. 权限控制

- [x] 6.1 实现 `nanobot/browser/permissions.py` - URL 白名单验证
- [x] 6.2 实现通配符域名匹配（`*.example.com`）
- [x] 6.3 添加 `PermissionDenied` 异常类

## 7. 凭证管理

- [x] 7.1 实现 `nanobot/browser/credentials.py` - `CredentialManager` 类
  - 使用 keyring 存储和检索密码
  - 凭证备份文件管理（JSON 格式）
  - 凭证文件权限设置（0600）
- [x] 7.2 实现域名规范化逻辑
- [ ] 7.3 实现凭证迁移工具（从明文到加密）
- [x] 7.4 添加日志中密码脱敏处理

## 8. 适配器基础框架

- [x] 8.1 实现 `nanobot/browser/adapters/base.py` - `WebsiteAdapter` 抽象基类
  - 定义 `login()` 接口
  - 定义 `verify_login()` 方法
  - 定义适配器元数据（域名、名称）
- [x] 8.2 实现 `nanobot/browser/adapters/registry.py` - `AdapterRegistry` 类
  - 注册适配器
  - 查找匹配适配器
  - 支持用户自定义适配器注册

## 9. 通用登录适配器

- [x] 9.1 实现 `nanobot/browser/adapters/generic.py` - `GenericLoginAdapter` 类
  - 启发式识别登录表单
  - 填写用户名和密码
  - 处理"记住我"选项
  - 点击登录按钮
- [x] 9.2 实现登录失败检测和错误处理
- [x] 9.3 添加常见登录表单模式支持

## 10. QQ 邮箱适配器

- [x] 10.1 实现 `nanobot/browser/adapters/qq_mail.py` - `QQMailAdapter` 类
  - 账号密码登录流程
  - 扫码登录流程
  - 验证码处理（提示用户输入）
  - 登录成功验证
- [x] 10.2 实现 QQ 邮箱特有的元素定位逻辑
- [x] 10.3 添加登录后页面验证（URL、元素检测）

## 11. 手动登录支持

- [x] 11.1 实现手动登录流程（打开登录页面、等待用户）
- [x] 11.2 实现登录完成检测
  - URL 变化检测
  - 特定元素出现检测
  - Cookie 变化检测
- [x] 11.3 实现用户手动确认机制

## 12. 三层登录策略

- [x] 12.1 实现 `nanobot/browser/adapters/__init__.py` 中的登录编排逻辑
  - 尝试专用适配器
  - 回退到通用登录
  - 最终回退到手动登录
- [x] 12.2 实现登录失败重试和错误处理
- [x] 12.3 添加登录状态验证

## 13. BrowserTool 实现

- [x] 13.1 实现 `nanobot/agent/tools/browser.py` - `BrowserTool` 类
  - `start_browser()` - 启动浏览器会话
  - `navigate(url)` - 导航到 URL
  - `click(element)` - 点击元素
  - `type_text(element, text)` - 输入文本
  - `snapshot()` - 获取页面快照
  - `login(url, strategy)` - 执行登录
  - `stop_browser()` - 停止浏览器
- [x] 13.2 实现工具参数验证和错误处理
- [x] 13.3 添加工具使用文档字符串

## 14. AgentLoop 集成

- [x] 14.1 在 `nanobot/agent/loop.py` 中导入 `BrowserTool`
- [x] 14.2 在 `_register_default_tools()` 中注册 `BrowserTool`（根据配置启用）
- [x] 14.3 添加浏览器配置检查逻辑（仅在 `browser.enabled=true` 时注册）

## 15. 模块导出

- [x] 15.1 在 `nanobot/agent/tools/__init__.py` 中导出 `BrowserTool`
- [x] 15.2 在 `nanobot/browser/__init__.py` 中导出主要类和函数

## 16. 测试

- [ ] 16.1 编写 `BrowserSession` 单元测试
- [ ] 16.2 编写 `PageSnapshot` 单元测试
- [ ] 16.3 编写 `BrowserActions` 单元测试
- [ ] 16.4 编写 `CredentialManager` 单元测试
- [ ] 16.5 编写适配器集成测试（使用 mock 浏览器）
- [ ] 16.6 编写 QQ 邮箱适配器端到端测试（可选）
- [ ] 16.7 编写 `BrowserTool` 集成测试

## 17. 文档

- [x] 17.1 创建 `docs/browser-control.md` 功能文档
- [ ] 17.2 添加配置示例到 `README.md` 或配置文档
- [x] 17.3 添加浏览器二进制安装说明（`playwright install chromium`）
- [x] 17.4 编写适配器开发指南（如何创建自定义适配器）

## 18. 发布准备

- [ ] 18.1 更新 CHANGELOG.md
- [ ] 18.2 添加版本迁移说明（如果有破坏性变更）
- [ ] 18.3 在 main 分支合并前进行完整测试
- [ ] 18.4 创建 GitHub Release（如需要）

## 可选 / 后续优化

- [ ] 19.1 添加多标签页支持
- [ ] 19.2 实现更智能的等待策略
- [ ] 19.3 支持浏览器扩展加载
- [ ] 19.4 添加文件下载处理
- [ ] 19.5 实现浏览器池（多实例支持）

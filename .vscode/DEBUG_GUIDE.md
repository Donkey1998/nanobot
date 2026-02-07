# Nanobot 调试指南

## 如何使用断点调试

### 方法一:使用 VSCode 调试配置

1. **打开要调试的文件** (例如 [context.py](nanobot/agent/context.py))
2. **设置断点**: 点击代码行号左侧,会出现红点
3. **打开调试面板**: 按 `Ctrl+Shift+D` (或点击侧边栏的调试图标)
4. **选择调试配置**: 在顶部下拉菜单中选择配置
5. **启动调试**: 点击绿色播放按钮或按 `F5`

### 可用的调试配置

| 配置名称 | 说明 | 使用场景 |
|---------|------|---------|
| **Nanobot: Agent 交互模式** | 启动交互式对话 | 调试 Agent 对话流程 |
| **Nanobot: Agent 单条消息** | 发送单条消息并退出 | 快速测试特定功能 |
| **Nanobot: Gateway 服务器** | 启动完整网关服务 | 调试完整服务流程 |
| **Nanobot: Status** | 显示状态信息 | 调试配置加载 |
| **Nanobot: Cron List** | 列出定时任务 | 调试 Cron 功能 |
| **Python: 当前文件** | 调试当前打开的文件 | 运行测试脚本 |

### 调试快捷键

- **F5**: 继续执行
- **F10**: 单步跳过
- **F11**: 单步进入
- **Shift+F11**: 单步跳出
- **Shift+F5**: 停止调试
- **Ctrl+Shift+F5**: 重启调试

### 方法二:命令行调试

你也可以直接在终端使用 Python 调试器:

```bash
# 安装 debugpy (如果尚未安装)
pip install debugpy

# 调试模式运行
python -m debugpy --listen 5678 --wait-for-client -m nanobot agent
```

### 方法三:代码中插入断点

在代码中插入断点:

```python
# 方式 1: 使用 breakpoint() (Python 3.7+)
def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
    parts = []
    breakpoint()  # 程序会在这里暂停
    # ... 后续代码

# 方式 2: 使用 pdb
import pdb; pdb.set_trace()

# 方式 3: 使用 ipdb (更好的体验,需安装)
# pip install ipdb
import ipdb; ipdb.set_trace()
```

### 调试技巧

#### 1. 查看 ContextBuilder 的执行流程

在 [context.py:70](nanobot/agent/context.py#L70) 设置断点:
```python
print (parts)  # 在这一行设置断点,查看构建的提示内容
```

#### 2. 调试异步函数

由于项目大量使用 `asyncio`,调试时注意:
- 使用 "Just My Code": false 可以看到异步框架内部的调用
- 在 `async` 函数中设置断点正常工作
- 查看协程状态: 检查变量时注意 awaitable 对象

#### 3. 查看变量和表达式

调试时可以在 "调试控制台" 中执行 Python 代码:
```python
# 查看当前作用域的变量
parts
self.workspace

# 调用函数
self._get_identity()
```

#### 4. 条件断点

右键点击断点,可以设置条件:
```python
# 例如:只在 skill_names 不为空时暂停
skill_names is not None
```

#### 5. 日志断点

在断点上右键 → "编辑断点" → 选择 "日志点":
```
技能名称: {skill_names}
部件数量: {len(parts)}
```
这样不会暂停执行,只输出信息。

### 常见调试场景

#### 调试 Agent 工具调用

在 [nanobot/agent/tools/](nanobot/agent/tools/) 目录下:
- [filesystem.py](nanobot/agent/tools/filesystem.py) - 文件操作工具
- [shell.py](nanobot/agent/tools/shell.py) - Shell 命令工具
- [web.py](nanobot/agent/tools/web.py) - Web 搜索工具

在相关函数中设置断点即可调试工具调用。

#### 调试 Agent 主循环

在 [agent/loop.py](nanobot/agent/loop.py) 中的关键函数:
- `process_direct()` - 处理直接消息
- `run()` - Agent 主循环

#### 调试配置加载

在 [config/loader.py](nanobot/config/loader.py) 中设置断点,查看配置如何被加载。

### 注意事项

1. **异步函数调试**: 确保在 `async def` 函数中设置断点,普通同步代码中可能看不到异步上下文
2. **环境变量**: 使用调试配置会自动设置 `PYTHONUNBUFFERED=1` 实现实时输出
3. **库代码调试**: 设置 `"justMyCode": false` 可以进入第三方库代码(如 litellm)
4. **热重载**: 修改代码后需要重启调试器

### 推荐工作流

1. 先在 "Status" 配置中测试配置是否正确
2. 使用 "Agent 单条消息" 快速验证功能
3. 需要完整交互时使用 "Agent 交互模式"
4. 调试服务相关功能使用 "Gateway 服务器"

### 获取更多帮助

- VSCode 调试文档: https://code.visualstudio.com/docs/python/debugging
- Python pdb 文档: https://docs.python.org/3/library/pdb.html


快速开始
最简单的方式:
在代码中设置断点:

打开 context.py
在第 70 行 (print (parts)) 的行号左侧点击,会出现一个红点 ✓
启动调试:

按 Ctrl+Shift+D 打开调试面板
在顶部下拉菜单选择 "Nanobot: Agent 单条消息"
点击绿色播放按钮 ▶️ 或按 F5
调试控制:

程序会在断点处暂停
F10 - 单步执行
F5 - 继续运行
可以查看左侧的变量面板
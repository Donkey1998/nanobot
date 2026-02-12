# 上下文构建器模块

> **文件位置**: [nanobot/agent/context.py](../../../nanobot/agent/context.py)
> **行数**: 约 232 行
> **最后更新**: 2026-02-10

---

## 1. 概述

上下文构建器模块（`ContextBuilder`）负责组装发送给 LLM 的完整上下文，包括系统提示、引导文件、记忆、技能和对话历史。它是 Agent"理解"任务的关键组件。

### 核心职责

- **系统提示生成**: 构建核心身份和运行环境信息
- **引导文件加载**: 加载工作区中的自定义引导文件
- **记忆集成**: 整合长期记忆和每日笔记
- **技能管理**: 实现渐进式技能加载策略
- **媒体支持**: 处理图片等多媒体内容
- **消息格式化**: 将各种内容组装成 LLM 可用的消息格式

### 设计目标

- **上下文完整性**: 确保 LLM 获得完成任务所需的所有信息
- **Token 效率**: 通过渐进式加载避免 Token 浪费
- **可定制性**: 通过引导文件支持个性化配置
- **多模态支持**: 处理文本、图片等多种输入

### 相关模块

- [Agent 循环](agent-loop.md) - 上下文构建器的使用者
- [记忆系统](#记忆集成) - 长期记忆存储
- [技能系统](skills-system.md) - 技能加载和管理

---

## 2. 设计理念

### 2.1 渐进式技能加载

**问题**: 将所有技能完整加载到上下文会造成 Token 浪费。

**解决方案**:
- **always=true 技能**: 完整加载到上下文
- **其他技能**: 仅显示 XML 摘要，LLM 使用 `read_file` 工具按需加载

**代码位置**: [context.py:54-69](../../../nanobot/agent/context.py#L54-L69)

```python
# 1. Always-loaded skills: include full content
always_skills = self.skills.get_always_skills()
if always_skills:
    always_content = self.skills.load_skills_for_context(always_skills)
    if always_content:
        parts.append(f"# Active Skills\n\n{always_content}")

# 2. Available skills: only show summary (agent uses read_file to load)
skills_summary = self.skills.build_skills_summary()
if skills_summary:
    parts.append(f"""# Skills

以下技能扩展了你的能力。要使用技能，请使用 read_file 工具读取其 SKILL.md 文件。
available="false" 的技能需要先安装依赖项 - 你可以尝试使用 apt/brew 安装它们。

{skills_summary}""")
```

### 2.2 分层上下文结构

上下文按优先级从高到低分层组装：

```
┌─────────────────────────────────────────────────────────┐
│  1. 核心身份 (Identity)                                   │
│     - 当前时间、运行环境、工作区路径                        │
│     - Agent 基本能力和职责                                 │
├─────────────────────────────────────────────────────────┤
│  2. 引导文件 (Bootstrap Files)                            │
│     - AGENTS.md (角色定义)                                │
│     - SOUL.md (个性特征)                                  │
│     - USER.md (用户偏好)                                  │
│     - TOOLS.md (工具说明)                                 │
│     - IDENTITY.md (身份定制)                              │
├─────────────────────────────────────────────────────────┤
│  3. 记忆上下文 (Memory)                                   │
│     - MEMORY.md (长期记忆)                                │
│     - YYYY-MM-DD.md (今日笔记)                            │
├─────────────────────────────────────────────────────────┤
│  4. 技能 (Skills)                                         │
│     - always=true 技能 (完整内容)                         │
│     - 其他技能 (XML 摘要)                                 │
├─────────────────────────────────────────────────────────┤
│  5. 对话历史 (History)                                    │
│     - 之前的对话消息                                      │
├─────────────────────────────────────────────────────────┤
│  6. 当前消息 (Current Message)                            │
│     - 用户输入 + 媒体附件                                 │
└─────────────────────────────────────────────────────────┘
```

### 2.3 可扩展的引导机制

通过工作区中的 Markdown 文件自定义 Agent 行为，无需修改代码。

**引导文件位置**: `{workspace}/{AGENTS.md,SOUL.md,USER.md,TOOLS.md,IDENTITY.md}`

---

## 3. 核心机制

### 3.1 系统提示构建

`build_system_prompt()` 方法负责构建完整的系统提示。

**代码位置**: [context.py:28-73](../../../nanobot/agent/context.py#L28-L73)

**流程**:
1. 获取核心身份（时间、环境、工作区）
2. 加载引导文件
3. 获取记忆上下文
4. 加载 always=true 技能
5. 构建其他技能的 XML 摘要

### 3.2 核心身份生成

`_get_identity()` 方法生成 Agent 的基本身份信息。

**代码位置**: [context.py:75-109](../../../nanobot/agent/context.py#L75-L109)

**包含内容**:
- 当前时间（日期、星期、时分）
- 运行环境（操作系统、架构、Python 版本）
- 工作区路径
- 记忆文件位置
- 自定义技能位置
- Agent 能力描述

### 3.3 引导文件加载

`_load_bootstrap_files()` 方法从工作区加载引导文件。

**代码位置**: [context.py:111-121](../../../nanobot/agent/context.py#L111-L121)

**引导文件列表**:
```python
BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
```

### 3.4 消息构建

`build_messages()` 方法组装完整的消息列表。

**代码位置**: [context.py:123-161](../../../nanobot/agent/context.py#L123-L161)

**参数**:
- `history`: 之前的对话消息
- `current_message`: 新的用户消息
- `media`: 图片等媒体文件路径（可选）
- `channel`: 当前渠道
- `chat_id`: 当前聊天 ID

### 3.5 多媒体支持

`_build_user_content()` 方法处理图片附件。

**代码位置**: [context.py:163-179](../../../nanobot/agent/context.py#L163-L179)

**格式**: base64 编码的 data URL
```
data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA...
```

### 3.6 工具结果添加

`add_tool_result()` 方法将工具执行结果添加到消息历史。

**代码位置**: [context.py:181-206](../../../nanobot/agent/context.py#L181-L206)

**格式**:
```python
{
    "role": "tool",
    "tool_call_id": "...",
    "name": "tool_name",
    "content": "工具执行结果"
}
```

### 3.7 助手消息添加

`add_assistant_message()` 方法添加 LLM 的响应消息。

**代码位置**: [context.py:208-231](../../../nanobot/agent/context.py#L208-L231)

**特点**:
- 支持工具调用（`tool_calls`）
- 支持纯文本响应
- 允许空内容（仅有工具调用）

---

## 4. 关键接口

### 4.1 构造函数

```python
def __init__(self, workspace: Path):
    self.workspace = workspace
    self.memory = MemoryStore(workspace)
    self.skills = SkillsLoader(workspace)
```

### 4.2 核心方法

#### `def build_system_prompt(self, skill_names: list[str] | None = None) -> str`

构建完整的系统提示。

**代码位置**: [context.py:28-73](../../../nanobot/agent/context.py#L28-L73)

**参数**:
- `skill_names`: 可选的要包含的技能列表

**返回**: 完整的系统提示字符串

#### `def build_messages(...) -> list[dict[str, Any]]`

构建完整的消息列表。

**代码位置**: [context.py:123-161](../../../nanobot/agent/context.py#L123-L161)

**签名**:
```python
def build_messages(
    self,
    history: list[dict[str, Any]],
    current_message: str,
    skill_names: list[str] | None = None,
    media: list[str] | None = None,
    channel: str | None = None,
    chat_id: str | None = None,
) -> list[dict[str, Any]]
```

**返回**: 可直接传给 LLM 的消息列表

#### `def add_tool_result(...) -> list[dict[str, Any]]`

添加工具执行结果到消息列表。

**代码位置**: [context.py:181-206](../../../nanobot/agent/context.py#L181-L206)

#### `def add_assistant_message(...) -> list[dict[str, Any]]`

添加助手消息到消息列表。

**代码位置**: [context.py:208-231](../../../nanobot/agent/context.py#L208-L231)

---

## 5. 使用示例

### 5.1 基础使用

```python
from pathlib import Path
from nanobot.agent.context import ContextBuilder

# 创建上下文构建器
workspace = Path("~/.nanobot/workspace").expanduser()
context = ContextBuilder(workspace)

# 构建系统提示
system_prompt = context.build_system_prompt()
print(system_prompt)

# 构建完整消息
messages = context.build_messages(
    history=[
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
    ],
    current_message="请帮我列出当前目录的文件",
    channel="cli",
    chat_id="direct"
)

# messages 现在可以直接传给 LLM
```

### 5.2 添加图片支持

```python
messages = context.build_messages(
    history=[],
    current_message="这张图片里是什么？",
    media=["/path/to/image.jpg"],  # 图片路径
    channel="telegram",
    chat_id="12345"
)
```

### 5.3 处理工具调用循环

```python
messages = context.build_messages(
    history=[],
    current_message="帮我创建一个新的 Python 文件",
    channel="cli",
    chat_id="direct"
)

# LLM 调用
response = await provider.chat(messages, tools=tool_definitions)

# 如果有工具调用
if response.has_tool_calls:
    messages = context.add_assistant_message(
        messages,
        response.content,
        tool_call_dicts=[...]
    )

    # 执行工具并添加结果
    for tool_call in response.tool_calls:
        result = await execute_tool(tool_call)
        messages = context.add_tool_result(
            messages,
            tool_call.id,
            tool_call.name,
            result
        )

    # 继续下一轮 LLM 调用
    next_response = await provider.chat(messages, tools=tool_definitions)
```

### 5.4 自定义引导文件

在工作区创建 `AGENTS.md`:

```markdown
# 工作区/skills/AGENTS.md

你是一个专注于 Python 开发的 AI 助手。

## 特点
- 精通 Python、Django、FastAPI
- 熟悉数据库设计和优化
- 了解容器化部署

## 工作方式
1. 首先理解需求
2. 设计解决方案
3. 编写高质量代码
4. 添加必要的注释和文档
```

创建 `SOUL.md`:

```markdown
# 工作区/skills/SOUL.md

## 个性
- 友好且专业
- 注重代码质量
- 喜欢简洁优雅的解决方案
- 不怕承认错误

## 沟通风格
- 使用清晰简洁的语言
- 解释技术决策
- 提供实用示例
```

这些文件会自动被加载到系统提示中。

---

## 6. 扩展指南

### 6.1 添加新的引导文件类型

扩展 `BOOTSTRAP_FILES` 列表：

```python
class CustomContextBuilder(ContextBuilder):
    BOOTSTRAP_FILES = [
        "AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md",
        "IDENTITY.md", "PROJECT.md",  # 添加新文件
    ]
```

### 6.2 自定义核心身份

重写 `_get_identity()` 方法：

```python
class CustomContextBuilder(ContextBuilder):
    def _get_identity(self) -> str:
        base = super()._get_identity()
        custom = "\n\n## 特殊配置\n- 你现在运行在特殊环境中\n- 遵守额外的安全规则"
        return base + custom
```

### 6.3 添加动态上下文

```python
class DynamicContextBuilder(ContextBuilder):
    def build_system_prompt(self, skill_names=None):
        base = super().build_system_prompt(skill_names)

        # 添加动态上下文
        git_branch = self._get_git_branch()
        env_status = self._get_environment_status()

        dynamic = f"""
## 当前环境状态
- Git 分支: {git_branch}
- 环境: {env_status}
"""
        return base + "\n\n" + dynamic

    def _get_git_branch(self):
        # 获取当前 Git 分支
        pass

    def _get_environment_status(self):
        # 获取环境状态
        pass
```

### 6.4 实现上下文压缩

对于长对话，可以压缩历史消息：

```python
class CompressingContextBuilder(ContextBuilder):
    def build_messages(self, history, current_message, **kwargs):
        # 压缩历史：只保留最近 N 轮对话
        compressed_history = self._compress_history(history, max_rounds=5)

        return super().build_messages(
            compressed_history,
            current_message,
            **kwargs
        )

    def _compress_history(self, history, max_rounds):
        # 实现压缩逻辑
        # 可以提取关键信息、总结早期对话等
        pass
```

### 6.5 添加上下文验证

```python
class ValidatingContextBuilder(ContextBuilder):
    def build_messages(self, history, current_message, **kwargs):
        messages = super().build_messages(history, current_message, **kwargs)

        # 验证上下文
        total_tokens = self._estimate_tokens(messages)
        if total_tokens > 100000:  # 假设限制
            warnings.warn(f"上下文过大: {total_tokens} tokens")

        return messages

    def _estimate_tokens(self, messages):
        # 粗略估算 token 数量
        # 英文约 4 字符/token，中文约 2 字符/token
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 3  # 粗略估计
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/agent/context.py](../../../nanobot/agent/context.py) - 上下文构建器主文件（232 行）

### 依赖模块

- [nanobot/agent/memory.py](../../../nanobot/agent/memory.py) - 记忆存储
- [nanobot/agent/skills.py](../../../nanobot/agent/skills.py) - 技能加载器

### 相关文档

- [Agent 循环模块文档](agent-loop.md)
- [技能系统模块文档](skills-system.md)

## 工作区结构

```
~/.nanobot/workspace/
├── AGENTS.md           # Agent 角色定义
├── SOUL.md             # 个性特征
├── USER.md             # 用户偏好
├── TOOLS.md            # 工具说明
├── IDENTITY.md         # 身份定制
├── memory/
│   ├── MEMORY.md       # 长期记忆
│   └── 2026-02-10.md   # 每日笔记
└── skills/
    ├── skill-name/
    │   └── SKILL.md    # 技能说明
    └── ...
```

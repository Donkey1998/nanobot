# nanobot LangChain/LangGraph 复刻开发计划

## 项目概述

本文档详细说明了如何使用 LangChain 和 LangGraph 框架完全重写 nanobot 项目。nanobot 是一个基于 ReAct 模式的轻量级 AI 助手框架(约 8000 行代码),通过重写可以:

- **减少 40% 代码量** - 从 ~8000 行降至 ~5000 行
- **提升可观测性** - LangSmith 自动追踪和可视化
- **增强调试能力** - 图结构可视化,执行流程清晰
- **改善扩展性** - 添加节点/边比修改循环代码更容易
- **享受社区生态** - LangChain 持续改进

## 核心决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| **迁移策略** | 完全重写 | 创建新项目 `nanobot-langgraph`,避免历史包袱 |
| **LLM 提供商** | LangChain 原生 | 使用 ChatOpenAI、ChatAnthropic 等,替代 LiteLLM |
| **核心功能** | ReAct 循环 + 记忆管理 + 子 Agent | 聚焦核心能力,其他功能可后续添加 |
| **目标渠道** | 飞书 + CLI | 满足个人使用需求,减少初期开发量 |
| **存储后端** | JSONL 文件(默认) + Redis(可选) | 保持简单,可选升级 |

---

## 架构映射

### 核心模块总览

nanobot 项目包含 **13 个核心模块**,分为 5 个层次:

```
┌─────────────────────────────────────────────────────────────┐
│                      核心处理层(3个模块)                     │
│  AgentLoop → StateGraph  |  ContextBuilder → PromptBuilder  │
│  LLMProvider → LangChain原生提供商                            │
├─────────────────────────────────────────────────────────────┤
│                  通信基础设施层(2个模块)                      │
│  MessageBus → MessageFlow  |  ChannelManager → 适配器       │
├─────────────────────────────────────────────────────────────┤
│                  能力扩展层(4个模块)                         │
│  ToolRegistry → LangChain工具  |  SkillsLoader → 技能加载   │
│  BrowserSession → Playwright  |  CronService → 调度节点     │
├─────────────────────────────────────────────────────────────┤
│                  状态管理层(3个模块)                         │
│  SessionManager → ChatMessageHistory  |  Subagent → 子图    │
│  MemoryStore → 持久化后端                                     │
├─────────────────────────────────────────────────────────────┤
│                  基础设施层(1个模块)                         │
│  Config → Pydantic Settings                                  │
└─────────────────────────────────────────────────────────────┘
```

### 模块映射表

| # | 原模块 | 原路径 | LangChain/LangGraph 实现 | 新路径 | 优先级 |
|---|--------|--------|--------------------------|--------|--------|
| **核心处理层** |||||||
| 1 | AgentLoop | `agent/loop.py` (427行) | StateGraph + 节点函数 | `graphs/agent_graph.py` | **P0** |
| 2 | ContextBuilder | `agent/context.py` (232行) | PromptBuilder + ChatPromptTemplate | `prompts/builder.py` | **P0** |
| 3 | LLMProvider | `providers/litellm_provider.py` (204行) | ChatOpenAI/ChatAnthropic 等原生类 | `core/llm.py` | **P0** |
| **通信基础设施层** |||||||
| 4 | MessageBus | `bus/queue.py` (82行) | MessageFlow (Runnable) | `core/message_flow.py` | **P0** |
| 5 | ChannelManager | `channels/manager.py` (162行) | 渠道适配器统一接口 | `channels/base.py` | **P1** |
| **能力扩展层** |||||||
| 6 | ToolRegistry | `agent/tools/registry.py` | LangChain StructuredTool 注册 | `tools/registry.py` | **P0** |
| 7 | SkillsLoader | `agent/skills.py` (229行) | 渐进式技能加载器 | `skills/loader.py` | **P1** |
| 8 | BrowserSession | `browser/` (多文件) | Playwright 集成 | `browser/session.py` | **P2** |
| 9 | CronService | `cron/service.py` (347行) | LangGraph 调度节点 | `scheduler/service.py` | **P2** |
| **状态管理层** |||||||
| 10 | SessionManager | `session/manager.py` (203行) | ChatMessageHistory | `memory/session.py` | **P0** |
| 11 | SubagentManager | `agent/subagent.py` (245行) | LangGraph 子图 | `graphs/subagent_graph.py` | **P1** |
| 12 | MemoryStore | `agent/memory.py` | 持久化后端(文件/Redis) | `memory/store.py` | **P1** |
| **基础设施层** |||||||
| 13 | Config | `config/` (schema+loader) | Pydantic Settings | `config/settings.py` | **P0** |

### 技术栈对比

| 组件类别 | 原实现技术 | LangChain/LangGraph 实现 | 优势 |
|---------|-----------|--------------------------|------|
| **LLM 接口** | LiteLLM(统一包装) | ChatOpenAI、ChatAnthropic 等原生类 | 性能更好,原生特性支持 |
| **Agent 循环** | 手动 while 循环 | StateGraph(声明式图) | 可视化、可调试、可中断 |
| **工具抽象** | 自定义 Tool 基类 | StructuredTool | 生态兼容,类型安全 |
| **记忆管理** | JSONL + 自定义 SessionManager | ChatMessageHistory | 多后端支持,自动序列化 |
| **消息传递** | asyncio.Queue | Runnable + Callbacks | 组合能力强,可观测性强 |
| **状态管理** | 手动字典管理 | TypedDict State | 类型提示明确,自动归约 |
| **可观测性** | 手动日志 | LangSmith 自动追踪 | 完整的执行轨迹,性能分析 |

### 架构优势对比

| 维度 | 原架构 | LangGraph 架构 |
|-----|--------|----------------|
| **代码量** | ~8000 行 | 预计 ~5000 行 (-37%) |
| **可维护性** | 循环逻辑分散 | 图结构清晰,节点独立 |
| **可调试性** | print 调试 | LangSmith 可视化追踪 |
| **可扩展性** | 修改循环代码 | 添加节点/边,非侵入式 |
| **可测试性** | 需要完整环境 | 节点独立,易于单测 |
| **可观测性** | 手动日志 | 自动追踪每个节点 |
| **学习曲线** | 低(纯Python) | 中(需理解LangGraph概念) |
| **生态集成** | 需要自己适配 | 直接使用 LangChain 生态 |

---

## 架构对比

### 原架构 vs 新架构

```
原架构 (nanobot):
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ MessageBus  │────▶│  AgentLoop   │────▶│   Tools     │
│ (队列)      │     │ (手动循环)   │     │  (自定义)   │
└─────────────┘     └──────────────┘     └─────────────┘

新架构 (nanobot-langgraph):
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ MessageFlow │────▶│ StateGraph   │────▶│ LangChain   │
│ (Runnable)  │     │ (声明式图)   │     │   Tools     │
└─────────────┘     └──────────────┘     └─────────────┘
```

### 组件映射表

| 原组件 | 原路径 | LangChain/LangGraph 实现 | 新路径 |
|--------|--------|--------------------------|--------|
| **AgentLoop** | `agent/loop.py` | `NanobotGraph` (StateGraph) | `graphs/agent_graph.py` |
| **ContextBuilder** | `agent/context.py` | `PromptBuilder` + ChatPromptTemplate | `prompts/builder.py` |
| **ToolRegistry** | `agent/tools/registry.py` | `LangChainToolRegistry` | `tools/registry.py` |
| **SessionManager** | `session/manager.py` | `MemoryManager` (ChatMessageHistory) | `memory/manager.py` |
| **SubagentManager** | `agent/subagent.py` | `SubgraphManager` (LangGraph 子图) | `graphs/subagent_graph.py` |
| **MessageBus** | `bus/queue.py` | `MessageFlow` (Runnable + Callbacks) | `core/message_flow.py` |
| **FeishuChannel** | `channels/feishu.py` | `FeishuAdapter` | `channels/feishu.py` |
| **CLI** | `cli/commands.py` | `CLIChannel` | `channels/cli.py` |

## 项目结构

```
nanobot-langgraph/
├── pyproject.toml                 # 项目配置
├── README.md                      # 项目说明
├── ARCHITECTURE.md                # 架构文档
├── MIGRATION.md                   # 迁移指南
│
├── nanobot_langgraph/             # 主包
│   ├── __init__.py
│   │
│   ├── core/                      # 核心组件
│   │   ├── __init__.py
│   │   ├── state.py              # AgentState 定义
│   │   └── message_flow.py       # 消息流处理(Runnable)
│   │
│   ├── graphs/                    # LangGraph 定义
│   │   ├── __init__.py
│   │   ├── agent_graph.py        # 主 Agent StateGraph
│   │   └── subagent_graph.py     # 子 Agent 子图
│   │
│   ├── tools/                     # 工具系统
│   │   ├── __init__.py
│   │   ├── registry.py           # 工具注册表
│   │   ├── base.py               # 工具基类
│   │   └── builtin/              # 内置工具
│   │       ├── filesystem.py     # 文件操作(读/写/编辑/列目录)
│   │       ├── shell.py          # Shell 执行
│   │       └── web.py            # Web 搜索和抓取
│   │
│   ├── memory/                    # 记忆管理
│   │   ├── __init__.py
│   │   └── manager.py            # ChatMessageHistory 管理
│   │
│   ├── prompts/                   # 提示工程
│   │   ├── __init__.py
│   │   └── builder.py            # 系统提示构建器
│   │
│   ├── channels/                  # 渠道适配器
│   │   ├── __init__.py
│   │   ├── base.py               # 渠道基类
│   │   ├── cli.py                # CLI 渠道
│   │   └── feishu.py             # 飞书渠道
│   │
│   ├── config/                    # 配置管理
│   │   ├── __init__.py
│   │   ├── schema.py             # 配置 Schema (Pydantic)
│   │   └── loader.py             # 配置加载器
│   │
│   └── cli/                       # 命令行接口
│       ├── __init__.py
│       └── commands.py           # Typer CLI 命令
│
└── tests/                         # 测试
    ├── __init__.py
    ├── test_agent_graph.py
    ├── test_tools.py
    └── test_memory.py
```

## 模块化迁移计划

本文档按模块组织,每个模块包含**业务架构说明**、**LangChain/LangGraph实现方案**、**实现任务清单**和**验收标准**。

---

## 层次一: 核心处理层 (3个模块)

### 模块 1: Agent循环 (AgentLoop) → StateGraph [P0]

#### 1.1 业务架构说明

**模块职责**
- 实现 ReAct 模式的智能体决策循环
- 协调 LLM 调用和工具执行
- 管理对话上下文和状态转换
- 处理子 Agent 通信和协调
- 防御性设计(迭代限制、异常隔离)

**关键特性**
- 消息循环处理:从消息总线接收用户消息
- 上下文构建:整合历史记录、记忆和技能

- LLM 交互:调用语言模型并解析响应
- 工具执行:根据 LLM 决策执行相应工具
- 迭代控制:最多 20 轮循环,防止无限循环
- 异常处理:工具失败不影响整体流程

**依赖关系**
```
依赖:
├── MessageBus (消息入站/出站)
├── ContextBuilder (上下文组装)
├── ToolRegistry (工具执行)
├── SessionManager (历史持久化)
└── SubagentManager (子任务创建)

被依赖:
├── 所有渠道(通过 MessageBus)
└── CLI 命令
```

**数据流**
```
用户消息
  ↓
MessageBus.inbound
  ↓
AgentLoop.consume_inbound()
  ├─ 获取/创建会话 (SessionManager)
  ├─ 构建完整上下文 (ContextBuilder)
  ├─ 进入 ReAct 循环:
  │  ├─ 调用 LLM (LLMProvider)
  │  ├─ 判断是否需要工具
  │  ├─ 执行工具 (ToolRegistry)
  │  └─ 重复或结束 (最多 20 轮)
  └─ 保存会话历史 (SessionManager)
  ↓
MessageBus.outbound
  ↓
用户接收响应
```

**设计原则**
- **单一职责**:只负责决策循环,不处理具体业务逻辑
- **状态机模式**:每个决策点都是清晰的状态转换
- **依赖注入**:所有外部依赖通过构造函数注入
- **异常隔离**:工具执行失败不影响主循环

#### 1.2 LangChain/LangGraph 实现方案

**技术选型**
- **StateGraph**:LangGraph 的核心组件,用于构建状态机
- **TypedDict**:定义状态结构,提供类型提示
- **ToolNode**:LangGraph 预构建的工具执行节点
- **Conditional Edge**:基于条件路由到不同节点

**架构映射**
```
原实现 → 新实现
├── while 循环 → StateGraph 的节点和边
├── 手动状态管理 → TypedDict State (自动归约)
├── if-else 路由 → Conditional Edge
├── 工具执行逻辑 → ToolNode
└── 异常处理 → 节点内部的 try-catch
```

**关键决策**
1. **使用 StateGraph 而不是 RunnableLambda**:
   - 需要条件路由和循环
   - 需要状态管理和中间检查点
   - 更好的可视化和调试能力

2. **保持消息历史为 Sequence**:
   - 使用 `operator.add` 自动追加新消息
   - 避免手动管理消息列表

3. **分离路由节点和决策节点**:
   - `should_continue`:纯函数,判断是否继续
   - `agent_node`:实际调用 LLM 的节点
   - 职责清晰,易于测试

**兼容性考虑**
- 保持与原项目相同的消息格式(HumanMessage/AIMessage)
- 支持相同的工具调用格式
- 兼容原有的会话历史格式(JSONL)

#### 1.3 实现任务清单

**Task 1.1: 定义 AgentState 状态结构**
- 创建 `graphs/state.py`
- 定义 `AgentState` TypedDict
  - `messages: Annotated[Sequence[BaseMessage], operator.add]` - 消息历史(自动追加)
  - `channel: str` - 渠道标识
  - `chat_id: str` - 会话ID
  - `sender_id: str` - 发送者ID
  - `iteration: int` - 当前迭代次数
  - `max_iterations: int` - 最大迭代次数
  - `workspace: str` - 工作区路径
  - `restrict_to_workspace: bool` - 是否限制工作区
  - `media: list[str] | None` - 媒体文件路径
- 添加类型提示和文档字符串

**Task 1.2: 实现 should_continue 路由函数**
- 创建 `graphs/agent_graph.py`
- 实现 `should_continue(state: AgentState) -> str` 函数
  - 检查最后一条消息是否为 AIMessage
  - 检查是否有 tool_calls
  - 检查是否达到 max_iterations
  - 返回 "continue" 或 "end"
- 添加单元测试覆盖各种情况

**Task 1.3: 实现 agent_node 决策节点**
- 实现 `agent_node(state: AgentState, config) -> dict` 函数
  - 从 config 获取模型实例
  - 从 config 获取工具列表
  - 绑定工具到模型
  - 调用 model.invoke()
  - 返回状态更新
- 处理 LLM 调用异常
- 添加日志记录

**Task 1.4: 创建和编译 StateGraph**
- 实现 `create_agent_graph()` 函数
  - 创建 StateGraph 实例
  - 添加 "agent" 节点
  - 设置入口点为 "agent"
  - 添加条件边(should_continue)
  - 编译并返回图
- 实现 `create_agent_graph_with_tools(tools)` 函数
  - 创建 StateGraph 实例
  - 添加 "agent" 和 "tools" 节点
  - 设置入口点和边
  - 编译并返回图

**Task 1.5: 集成上下文构建**
- 修改 `agent_node` 函数
  - 获取 ContextBuilder 实例
  - 构建完整上下文(系统提示 + 历史)
  - 传递给 LLM
- 支持 ContextBuilder 从 config 注入

**Task 1.6: 集成会话管理**
- 修改 `agent_node` 函数
  - 获取 SessionManager 实例
  - 加载会话历史
  - 合并历史和当前消息
  - 保存新的消息到历史
- 支持会话key格式: `{channel}:{chat_id}`

**Task 1.7: 添加子 Agent 支持**
- 实现 spawn_subagent 工具
  - 创建子 Agent 图实例
  - 在后台启动异步任务
  - 返回任务ID给主 Agent
- 实现结果汇报机制
  - 子 Agent 完成后通过消息总线汇报
  - 主 Agent 自然接收结果

#### 1.4 验收标准

**功能验证**
- □ 能够接收用户消息并正确处理
- □ 能够调用 LLM 并获取响应
- □ 能够执行工具调用并获取结果
- □ 能够在达到最大迭代次数时停止
- □ 能够返回正确的最终响应
- □ 支持多轮对话(上下文保持)
- □ 支持多用户并发会话

**集成验证**
- □ 与 ContextBuilder 集成正常
- □ 与 ToolRegistry 集成正常
- □ 与 SessionManager 集成正常
- □ 与 SubagentManager 集成正常
- □ 与 MessageBus 集成正常

**异常处理**
- □ LLM 调用失败时能够优雅处理
- □ 工具执行失败时能够重试或降级
- □ 迭代超限时能够返回部分结果
- □ 上下文构建失败时能够使用默认配置
- □ 会话保存失败不影响响应返回

**性能指标**
- □ 单次决策延迟 < 2 秒(使用 GPT-4o)
- □ 20 轮迭代完成时间 < 60 秒
- □ 内存占用增长合理(< 100MB/会话)
- □ 支持 10+ 并发会话

**可观测性**
- □ 每个节点执行有日志记录
- □ 错误有详细的堆栈跟踪
- □ 关键指标可导出(迭代次数、工具调用次数)
- □ 支持 LangSmith 追踪
- □ 图结构可视化正常(`graph.get_graph().print_ascii()`)

**兼容性验证**
- □ 消息格式与原项目兼容
- □ 会话历史格式兼容(JSONL)
- □ 工具调用格式兼容
- □ 性能不低于原实现(±10%)

---

### 模块 2: 上下文构建器 (ContextBuilder) → PromptBuilder [P0]

#### 2.1 业务架构说明

**模块职责**
- 组装发送给 LLM 的完整上下文
- 加载和格式化引导文件
- 整合长期记忆和短期记忆
- 实现渐进式技能加载策略
- 支持多模态内容(图片等)

**关键特性**
- **分层上下文结构**:
  1. 核心身份(当前时间、工作区、能力描述)
  2. 引导文件(AGENTS.md、SOUL.md、USER.md、TOOLS.md)
  3. 记忆上下文(长期记忆 + 今日笔记)
  4. 技能(always=true 的完整内容,其他只显示摘要)
  5. 历史消息(最近50条)
  6. 当前消息
- **渐进式技能加载**:
  - `always=true`: 完整加载到上下文
  - 其他技能:只显示 XML 摘要
  - LLM 通过 `read_file` 工具按需加载
- **Token 优化**:
  - 摘要格式: `<skill name="xxx" file="workspace/skills/xxx/SKILL.md">`
  - 避免加载不必要的技能内容

**依赖关系**
```
依赖:
├── MemoryStore (长期记忆)
├── SkillsLoader (技能加载)
└── Config (工作区路径、配置)

被依赖:
└── AgentLoop (每个决策周期)
```

**数据流**
```
AgentLoop 请求上下文
  ↓
ContextBuilder.build()
  ├─ 加载核心身份
  ├─ 加载引导文件 (从工作区)
  ├─ 加载记忆 (MemoryStore)
  ├─ 加载技能 (SkillsLoader)
  │  ├─ always=true → 完整内容
  │  └─ 其他 → XML 摘要
  ├─ 加载历史消息 (SessionManager)
  └─ 添加当前消息
  ↓
返回完整 Prompt (ChatPromptTemplate)
  ↓
传递给 LLM
```

**设计原则**
- **组合模式**:从多个来源组装上下文
- **策略模式**:不同的技能加载策略
- **缓存友好**:相同会话的上下文可以缓存
- **惰性加载**:技能内容按需加载

#### 2.2 LangChain/LangGraph 实现方案

**技术选型**
- **ChatPromptTemplate**:LangChain 的提示模板
- **SystemMessage/HumanMessage**:消息类型
- **Jinja2Templates**:支持复杂模板逻辑

**架构映射**
```
原实现 → 新实现
├── 手动字符串拼接 → ChatPromptTemplate
├── XML 格式化 → Template 变量
├── 技能摘要逻辑 → PromptBuilder
└── 多模态支持 → Message.content = [{"type": "text", "type": "image_url"}]
```

**关键决策**
1. **使用 ChatPromptTemplate 而不是字符串拼接**:
   - 更好的可维护性
   - 支持部分变量绑定
   - LangChain 生态兼容

2. **保持渐进式技能加载**:
   - 有效降低 Token 消耗
   - 提升响应速度

3. **支持多模态内容**:
   - 图片作为 base64 或 URL
   - 统一的内容格式

**兼容性考虑**
- 保持与原项目相同的引导文件格式
- 保持技能摘要的 XML 格式
- 支持相同的工作区结构

#### 2.3 实现任务清单

**Task 2.1: 定义 PromptBuilder 类**
- 创建 `prompts/builder.py`
- 实现 `PromptBuilder` 类
  - `__init__(workspace, config)`
  - `build(channel, chat_id, messages, media) -> ChatPromptTemplate`
- 添加类型提示和文档字符串

**Task 2.2: 实现核心身份构建**
- 实现 `_build_identity()` 方法
  - 当前时间
  - 工作区路径
  - Agent 能力描述
  - 工具列表摘要
- 返回格式化的字符串

**Task 2.3: 实现引导文件加载**
- 实现 `_load_bootstrap_files()` 方法
  - 从工作区加载 AGENTS.md
  - 从工作区加载 SOUL.md
  - 从工作区加载 USER.md
  - 从工作区加载 TOOLS.md
- 处理文件不存在的情况(使用默认内容)

**Task 2.4: 实现记忆加载**
- 实现 `_load_memory()` 方法
  - 加载 MEMORY.md(长期记忆)
  - 加载今日笔记(memory/YYYY-MM-DD.md)
- 与 MemoryStore 集成

**Task 2.5: 实现技能加载**
- 实现 `_load_skills()` 方法
  - 调用 SkillsLoader 加载所有技能
  - 区分 always=true 和普通技能
  - 生成 XML 摘要
- 返回格式化的技能内容

**Task 2.6: 实现历史消息整合**
- 实现 `_format_history()` 方法
  - 从 SessionManager 获取历史
  - 截断到最近 N 条(默认50)
  - 保持消息顺序

**Task 2.7: 支持多模态内容**
- 实现 `_handle_media()` 方法
  - 处理图片路径
  - 转换为 base64 或保持 URL
  - 构建多模态消息内容

**Task 2.8: 创建 ChatPromptTemplate**
- 实现 `_create_template()` 方法
  - 定义系统提示模板
  - 定义变量占位符
  - 支持部分变量绑定
- 返回 ChatPromptTemplate 实例

#### 2.4 验收标准

**功能验证**
- □ 能够正确加载所有引导文件
- □ 能够正确加载记忆内容
- □ 能够正确加载技能(always=true 和普通)
- □ 能够生成正确的 XML 摘要
- □ 能够处理多模态内容(图片)
- □ 能够处理文件不存在的情况
- □ 支持工作区覆盖内置配置

**集成验证**
- □ 与 MemoryStore 集成正常
- □ 与 SkillsLoader 集成正常
- □ 与 SessionManager 集成正常
- □ 与 AgentLoop 集成正常

**性能指标**
- □ 上下文构建时间 < 500ms
- □ 普通会话 Token 数 < 2000
- □ 大型技能不会导致 Token 溢出

**兼容性验证**
- □ 引导文件格式与原项目兼容
- □ 技能摘要格式兼容
- □ 工作区结构兼容

---

### 模块 3: LLM提供商 (LLMProvider) → LangChain原生提供商 [P0]

#### 3.1 业务架构说明

**模块职责**
- 统一多家 LLM 提供商接口
- 智能路由到对应提供商
- 支持 API Key、API Base 自定义
- 自动添加模型前缀
- 错误优雅处理和重试

**关键特性**
- **支持提供商**:OpenRouter、Anthropic、OpenAI、DeepSeek、Gemini、Moonshot、DashScope、vLLM 等
- **智能路由**:
  - 根据模型名称自动匹配提供商
  - 支持模型前缀自动补全
  - 支持自定义 API Base
- **统一接口**:所有提供商使用相同的调用方式
- **错误处理**:
  - 自动重试(网络错误、限流)
  - 降级策略(主提供商失败时切换备用)

**依赖关系**
```
依赖:
└── Config (API Key、模型配置)

被依赖:
├── AgentLoop (每个决策)
└── SubagentManager (子 Agent)
```

**数据流**
```
AgentLoop 请求 LLM 调用
  ↓
LLMProvider.chat(messages, tools)
  ├─ 解析模型名称
  ├─ 匹配提供商 (OpenRouter/Anthropic/...)
  ├─ 创建对应实例 (ChatOpenAI/ChatAnthropic/...)
  ├─ 绑定工具
  ├─ 调用 LLM
  └─ 处理响应/错误
  ↓
返回 LLMResponse (content + tool_calls)
```

**设计原则**
- **适配器模式**:统一不同提供商的接口
- **策略模式**:不同的提供商使用不同的策略
- **配置驱动**:所有配置从配置文件读取

#### 3.2 LangChain/LangGraph 实现方案

**技术选型**
- **ChatOpenAI**:OpenAI 模型的原生类
- **ChatAnthropic**:Anthropic 模型的原生类
- **模型注册表**:管理模型名称到提供商的映射

**架构映射**
```
原实现 → 新实现
├── LiteLLM 统一接口 → 直接使用 LangChain 原生类
├── 智能路由逻辑 → 工厂函数
└── 模型前缀处理 → 配置映射
```

**关键决策**
1. **不使用 LiteLLM**:
   - LangChain 原生类性能更好
   - 更直接的错误处理
   - 更好的特性支持(如流式输出)

2. **使用工厂模式创建模型**:
   - 根据模型名称自动选择提供商
   - 统一的配置管理

3. **支持环境变量和配置文件**:
   - 优先从配置文件读取
   - 环境变量作为覆盖

**兼容性考虑**
- 支持相同的模型名称格式
- 支持相同的 API Key 配置
- 保持错误处理行为一致

#### 3.3 实现任务清单

**Task 3.1: 定义模型配置 Schema**
- 创建 `core/llm.py`
- 定义 `LLMConfig` 模型
  - `provider: str` (openai/anthropic/openrouter/...)
  - `model: str`
  - `api_key: str`
  - `base_url: str | None`
  - `temperature: float`
  - `max_tokens: int | None`

**Task 3.2: 实现提供商工厂**
- 实现 `create_llm(config: LLMConfig)` 函数
  - 根据 provider 选择对应的 LangChain 类
  - 传递配置参数
  - 返回模型实例
- 支持的提供商:
  - `openai` → ChatOpenAI
  - `anthropic` → ChatAnthropic
  - `openrouter` → ChatOpenAI(base_url=...)
  - `deepseek` → ChatOpenAI(base_url=...)
  - 等等

**Task 3.3: 实现智能路由**
- 实现 `route_model(model_name: str) -> str` 函数
  - 解析模型名称
  - 匹配提供商规则
  - 返回提供商类型
- 支持模型前缀自动补全

**Task 3.4: 实现模型管理器**
- 实现 `LLMManager` 类
  - `get_model(model_name: str) → BaseChatModel`
  - `set_default(model_name: str)`
  - `list_models() → list[str]`
- 缓存模型实例
- 支持运行时切换模型

**Task 3.5: 添加错误处理和重试**
- 实现重试装饰器
  - 网络错误重试 3 次
  - 限流错误自动退避
  - 其他错误直接抛出
- 支持自定义重试策略

**Task 3.6: 集成到 Config**
- 扩展配置 Schema
  - `llm: LLMConfig`
  - `llm.fallback: list[LLMConfig]` (备用提供商)
- 从配置文件加载 LLM 配置

#### 3.4 验收标准

**功能验证**
- □ 支持所有计划的提供商
- □ 模型路由正确
- □ API Key 正确传递
- □ 自定义 API Base 生效
- □ 工具绑定正常
- □ 流式输出正常(可选)

**异常处理**
- □ API Key 错误时有清晰提示
- □ 网络错误时自动重试
- □ 限流错误时自动退避
- □ 不支持的模型名称时提示

**性能指标**
- □ 模型创建时间 < 100ms
- □ 单次调用延迟与提供商一致
- □ 重试不影响正常调用

**兼容性验证**
- □ 支持原项目的所有模型名称
- □ 配置格式兼容
- □ API 调用格式兼容

---

## 层次二: 通信基础设施层 (2个模块)

### 模块 4: 消息总线 (MessageBus) → MessageFlow [P0]

#### 4.1 业务架构说明

**模块职责**
- 解耦聊天平台和 Agent 的异步消息传递
- 提供入站和出站消息队列
- 支持多个生产者和消费者
- 实现消息的可靠传递

**关键特性**
- **双向队列**:
  - `inbound`: 用户消息 → Agent
  - `outbound`: Agent 响应 → 用户
- **生产者-消费者模式**:
  - 渠道适配器发布消息到 inbound
  - AgentLoop 从 inbound 消费消息
  - AgentLoop 发布响应到 outbound
  - 渠道适配器从 outbound 消费响应
- **异步非阻塞**:使用 asyncio.Queue
- **解耦设计**:渠道和 Agent 完全解耦

**依赖关系**
```
依赖:
└── asyncio (Python 标准库)

被依赖:
├── AgentLoop (消费者)
├── ChannelManager (生产者和分发者)
└── 所有渠道适配器
```

**数据流**
```
┌────────────┐
│   渠道      │ 发布消息
│ 适配器     │──────────────┐
└────────────┘              │
                            ▼
                    ┌───────────────┐
                    │ MessageBus    │
                    │  .inbound     │
                    └───────────────┘
                            │
                            │ 消费消息
                            ▼
                    ┌───────────────┐
                    │  AgentLoop    │
                    │  处理消息     │
                    └───────────────┘
                            │
                            │ 发布响应
                            ▼
                    ┌───────────────┐
                    │ MessageBus    │
                    │  .outbound    │
                    └───────────────┘
                            │
                            │ 分发响应
                            ▼
                    ┌──────────────┐
                    │ChannelManager│──▶ 各个渠道
                    └──────────────┘
```

**设计原则**
- **解耦**:生产者和消费者互不依赖
- **异步**:使用协程实现非阻塞
- **简单**:只负责消息传递,不处理业务逻辑

#### 4.2 LangChain/LangGraph 实现方案

**技术选型**
- **Runnable**:LangChain 的统一抽象
- **RunnableLambda**:包装自定义函数
- **RunnableParallel**:并行执行多个分支

**架构映射**
```
原实现 → 新实现
├── asyncio.Queue → 内部状态管理
├── 显式发布/消费 → Runnable 链式调用
└── ChannelManager 分发 → RunnablePassthrough + 分发回调
```

**关键决策**
1. **不完全使用 LangChain Runnable**:
   - 保留 asyncio.Queue 用于渠道和 Agent 之间的通信
   - 使用 Runnable 包装 Agent 处理逻辑
   - 结合两者优势

2. **分离消息传递和处理**:
   - `MessageBus`:只负责队列管理
   - `MessageFlow`:负责 Agent 处理流程(Runnable)

**兼容性考虑**
- 保持消息格式与原项目兼容
- 支持异步非阻塞
- 支持并发处理多个会话

#### 4.3 实现任务清单

**Task 4.1: 定义消息数据结构**
- 创建 `core/messages.py`
- 定义 `InboundMessage` 模型
  - `channel: str`
  - `chat_id: str`
  - `sender_id: str`
  - `content: str`
  - `media: list[str] | None`
  - `timestamp: datetime`
- 定义 `OutboundMessage` 模型
  - `channel: str`
  - `chat_id: str`
  - `content: str`
  - `media: list[str] | None`

**Task 4.2: 实现 MessageBus**
- 创建 `core/message_bus.py`
- 实现 `MessageBus` 类
  - `inbound: asyncio.Queue[InboundMessage]`
  - `outbound: asyncio.Queue[OutboundMessage]`
  - `async def publish_inbound(msg: InboundMessage)`
  - `async def publish_outbound(msg: OutboundMessage)`
  - `async def consume_inbound() -> InboundMessage`
  - `async def consume_outbound() -> OutboundMessage`
- 添加队列大小监控

**Task 4.3: 实现 MessageFlow (Runnable)**
- 创建 `core/message_flow.py`
- 实现 `create_message_flow(agent_graph, config)` 函数
  - 接收 InboundMessage
  - 转换为 AgentState
  - 调用 agent_graph
  - 转换为 OutboundMessage
  - 返回结果
- 使用 RunnableLambda 包装

**Task 4.4: 实现消息分发器**
- 实现 `MessageDispatcher` 类
  - `async def dispatch_outbound(msg: OutboundMessage, channels: dict)`
  - 根据 channel 路由到对应渠道
  - 调用渠道的 send_message 方法
- 处理分发失败的情况

**Task 4.5: 集成到 AgentLoop**
- 修改 AgentLoop
  - 从 MessageBus.inbound 消费消息
  - 处理消息
  - 发布响应到 MessageBus.outbound
- 支持优雅启停

#### 4.4 验收标准

**功能验证**
- □ 消息能够正确发布到 inbound 队列
- □ 消息能够从 inbound 队列正确消费
- □ 响应能够正确发布到 outbound 队列
- □ 响应能够正确分发到各个渠道
- □ 支持并发处理多个消息
- □ 队列满时能够阻塞或丢弃

**性能指标**
- □ 消息入队延迟 < 10ms
- □ 消息出队延迟 < 10ms
- □ 支持 100+ 消息/秒吞吐量
- □ 内存占用稳定

**异常处理**
- □ 渠道断开时不影响其他渠道
- □ 消息分发失败时能够记录日志
- □ 队列异常时能够恢复

**兼容性验证**
- □ 消息格式与原项目兼容
- □ 行为与原项目一致

---

### 模块 5: 渠道管理器 (ChannelManager) → 渠道适配器统一接口 [P1]

#### 5.1 业务架构说明

**模块职责**
- 协调多个聊天平台适配器
- 统一渠道生命周期管理
- 实现出站消息分发
- 权限控制(白名单)

**关键特性**
- **支持平台**:Telegram、Discord、Feishu、WhatsApp、CLI
- **适配器模式**:每个平台实现相同的接口
- **权限控制**:`allowFrom` 白名单配置
- **生命周期管理**:
  - `start()`:启动所有渠道
  - `stop()`:停止所有渠道
  - `restart()`:重启单个渠道
- **并发处理**:多个渠道同时运行

**依赖关系**
```
依赖:
├── MessageBus (消息入站/出站)
└── 各个渠道适配器

被依赖:
├── Gateway 命令
└── 系统启动流程
```

**数据流**
```
┌───────────────┐         ┌──────────────┐
│   Telegram    │         │    Discord   │
│   Channel     │         │    Channel   │
└───────┬───────┘         └──────┬───────┘
        │                        │
        │ publish_inbound        │
        └────────┬───────────────┘
                 ▼
        ┌──────────────────┐
        │   MessageBus     │
        │    .inbound      │
        └──────────────────┘
                 │
                 │ consume_inbound
                 ▼
        ┌──────────────────┐
        │   AgentLoop      │
        └──────────────────┘
                 │
                 │ publish_outbound
                 ▼
        ┌──────────────────┐
        │   MessageBus     │
        │   .outbound      │
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ ChannelManager   │
        │   分发器         │
        └────────┬─────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
  ┌──────┐  ┌──────┐  ┌──────┐
  │ Feishu│  │ CLI  │  │Discord│
  └──────┘  └──────┘  └──────┘
```

**设计原则**
- **接口隔离**:每个渠道实现相同接口
- **配置驱动**:从配置文件加载渠道配置
- **故障隔离**:单个渠道失败不影响其他渠道

#### 5.2 LangChain/LangGraph 实现方案

**技术选型**
- **抽象基类**:定义统一接口
- **适配器模式**:每个平台独立适配

**架构映射**
```
原实现 → 新实现
├── BaseChannel 抽象类 → 保持不变
├── ChannelManager → 保持不变
└── 权限控制逻辑 → 保持不变
```

**关键决策**
1. **保持原有设计**:
   - 渠道适配器设计已经很好
   - 不需要大的改动
   - 只需要适配新的消息格式

2. **优先实现核心渠道**:
   - P0:CLI(必需,用于测试)
   - P1:Feishu(主要使用渠道)
   - P2:Telegram、Discord(可选)

**兼容性考虑**
- 保持渠道接口不变
- 支持相同的配置格式
- 行为与原项目一致

#### 5.3 实现任务清单

**Task 5.1: 定义渠道基类**
- 创建 `channels/base.py`
- 实现 `BaseChannel` 抽象类
  - `async def start() → None`
  - `async def stop() → None`
  - `async def send(msg: OutboundMessage) → None`
  - `def is_allowed(sender_id: str) → bool`
- 添加类型提示和文档字符串

**Task 5.2: 实现 CLI 渠道**
- 创建 `channels/cli.py`
- 实现 `CLIChannel` 类
  - 继承 BaseChannel
  - 使用 Rich 渲染输出
  - 支持交互模式和单消息模式
  - 支持 Markdown 渲染
- 实现 Rich 集成
  - 代码高亮
  - Markdown 渲染
  - 面板和边框

**Task 5.3: 实现飞书渠道**
- 创建 `channels/feishu.py`
- 实现 `FeishuChannel` 类
  - 继承 BaseChannel
  - 使用 FastAPI 提供 HTTP 服务
  - 处理飞书事件
  - 发送消息到飞书
- 实现事件处理
  - URL 验证
  - 消息接收
  - 消息解析

**Task 5.4: 实现 ChannelManager**
- 创建 `channels/manager.py`
- 实现 `ChannelManager` 类
  - `__init__(config)`
  - `async def start_all()`
  - `async def stop_all()`
  - `async def dispatch_outbound(msg: OutboundMessage)`
  - `get_channel(channel_type: str) → BaseChannel`
- 根据配置创建渠道实例
- 实现并发启动

**Task 5.5: 实现权限控制**
- 在 BaseChannel 中实现 `is_allowed()`
- 支持通配符 `*`
- 支持列表配置
- 添加日志记录(拒绝访问时)

**Task 5.6: 添加渠道健康检查**
- 实现健康检查机制
  - 定期 ping 各渠道
  - 自动重连断开的渠道
  - 记录渠道状态
- 暴露健康检查接口

#### 5.4 验收标准

**功能验证**
- □ 所有渠道能够正常启动
- □ 所有渠道能够正常停止
- □ 消息能够正确路由到对应渠道
- □ 权限控制生效
- □ 支持多个渠道并发运行

**CLI 渠道验证**
- □ 交互模式正常
- □ 单消息模式正常
- □ Markdown 渲染美观
- □ 代码高亮正常
- □ 错误提示友好

**飞书渠道验证**
- □ 能够接收飞书消息
- □ 能够发送飞书消息
- □ 事件验证通过
- □ HTTP 服务稳定

**异常处理**
- □ 单个渠道失败不影响其他渠道
- □ 渠道断开时能够自动重连
- □ 配置错误时有清晰提示

**性能指标**
- □ 渠道启动时间 < 5 秒
- □ 消息分发延迟 < 100ms
- □ 支持 10+ 并发会话/渠道

---

## 层次三: 能力扩展层 (4个模块)

### 模块 6: 工具系统 (ToolRegistry) → LangChain StructuredTool [P0]

#### 6.1 业务架构说明

**模块职责**
- 管理所有可用工具
- 提供工具注册和执行接口
- 参数验证(JSON Schema)
- 错误处理和重试

**关键特性**
- **内置工具**:文件系统、Shell、Web、消息、spawn、cron、浏览器
- **工具接口**:name、description、parameters、execute()
- **注册表模式**:动态注册和查找工具
- **安全控制**:路径限制、命令超时

**依赖关系**
```
依赖:
├── 文件系统工具 → pathlib
├── Shell 工具 → asyncio
├── Web 工具 → httpx
└── 浏览器工具 → Playwright(可选)

被依赖:
├── AgentLoop (每个决策周期)
└── SubagentManager (子 Agent)
```

**数据流**
```
LLM 决策调用工具
  ↓
ToolRegistry.execute(name, params)
  ├─ 参数验证 (JSON Schema)
  ├─ 查找工具实例
  ├─ 调用 Tool.execute(**params)
  └─ 返回结果字符串
  ↓
添加到消息历史
```

**设计原则**
- 策略模式:所有工具实现相同接口
- 注册表模式:动态管理工具
- 安全第一:路径控制、超时控制

#### 6.2 LangChain/LangGraph 实现方案

**技术选型**
- **StructuredTool**:LangChain 的工具抽象
- **BaseTool**:工具基类
- **tool**:装饰器

**架构映射**
```
原实现 → 新实现
├── 自定义 Tool 基类 → StructuredTool
├── ToolRegistry → LangChainToolRegistry
├── JSON Schema → Pydantic 模型
└── execute() → StructuredTool.coroutine
```

**关键决策**
1. 使用 LangChain 原生工具
2. 保留工具注册表
3. 优先实现核心工具(P0/P1/P2)

**兼容性考虑**
- 保持工具名称和描述一致
- 支持相同的参数格式

#### 6.3 实现任务清单

**Task 6.1: 实现工具注册表**
- 创建 `tools/registry.py`
- 实现 `LangChainToolRegistry` 类
  - register、unregister、get、get_all、register_all
- 添加工具查找缓存

**Task 6.2: 实现文件系统工具**
- 创建 `tools/builtin/filesystem.py`
- 实现 read_file、write_file、edit_file、list_dir
- 添加路径验证(restrict_to_workspace)

**Task 6.3: 实现 Shell 工具**
- 创建 `tools/builtin/shell.py`
- 实现 exec 工具
- 添加超时控制

**Task 6.4: 实现 Web 工具**
- 创建 `tools/builtin/web.py`
- 实现 web_search、web_fetch
- 集成搜索 API 和 readability-lxml

**Task 6.5: 实现消息和 spawn 工具**
- 创建 `tools/builtin/message.py`
- 创建 `tools/builtin/spawn.py`
- 集成 ChannelManager 和 SubagentManager

**Task 6.6: 添加工具安全控制**
- 实现 WorkspaceValidator 类
- 集成到各工具中

#### 6.4 验收标准

**功能验证**
- □ 所有工具能够正常注册和执行
- □ 参数验证正常
- □ 错误处理正确

**安全验证**
- □ 路径限制生效
- □ Shell 超时控制生效

**性能指标**
- □ 工具注册延迟 < 10ms
- □ 工具查找延迟 < 1ms

**兼容性验证**
- □ 工具名称与原项目一致
- □ 参数格式一致

---

### 模块 7: 技能系统 (SkillsLoader) → 渐进式技能加载器 [P1]

#### 7.1 业务架构说明

**模块职责**
- 动态加载和管理 Agent 技能
- 实现渐进式加载策略
- 支持工作区覆盖内置技能
- 依赖检查和环境验证

**关键特性**
- **技能来源**:工作区 > 内置
- **渐进式加载**:
  - always=true → 完整内容
  - 其他 → XML 摘要
- **依赖检查**:bins、env

**依赖关系**
```
依赖:
├── Config (工作区路径)
└── 文件系统

被依赖:
└── ContextBuilder
```

**数据流**
```
ContextBuilder 请求技能
  ↓
SkillsLoader.load_skills()
  ├─ 扫描技能目录
  ├─ 合并技能列表
  ├─ 加载元数据
  └─ 格式化(always=true 完整,其他摘要)
  ↓
返回格式化的技能内容
```

**设计原则**
- 约定优于配置
- 覆盖优先
- 惰性加载

#### 7.2 LangChain/LangGraph 实现方案

**技术选型**
- **Pathlib**:路径操作
- **PyYAML**:解析 frontmatter

**架构映射**
```
保持原有设计,只适配新项目结构
```

**关键决策**
1. 保持原有设计
2. 简化实现

**兼容性考虑**
- 支持相同的技能目录结构
- 支持相同的元数据格式

#### 7.3 实现任务清单

**Task 7.1: 定义技能数据模型**
- 创建 `skills/models.py`
- 定义 SkillMetadata 模型

**Task 7.2: 实现 SkillsLoader**
- 创建 `skills/loader.py`
- 实现 SkillsLoader 类
  - load_skills、get_skill、list_skills

**Task 7.3: 实现技能解析**
- 实现 _parse_skill_file 方法
- 解析 YAML frontmatter

**Task 7.4: 实现依赖检查**
- 实现 _check_dependencies 方法

**Task 7.5: 实现渐进式加载**
- 实现 _format_skill_for_context 方法

**Task 7.6: 实现技能缓存**
- 添加文件变化监听
- 自动重新加载

#### 7.4 验收标准

**功能验证**
- □ 工作区技能覆盖内置技能
- □ always=true 完整加载
- □ 普通技能显示摘要
- □ 依赖检查正常

**性能指标**
- □ 技能加载时间 < 500ms

**兼容性验证**
- □ 目录结构兼容
- □ 元数据格式兼容

---

### 模块 8-9: 浏览器自动化和定时任务 [P2, 可选]

**说明**:这两个模块为可选功能,可在后期根据需求实现。详细内容省略,参考原项目实现:
- **模块8**:BrowserSession → Playwright 集成(`browser/`)
- **模块9**:CronService → 调度节点(`cron/`)

---

## 层次四: 状态管理层 (3个模块)

### 模块 10: 会话管理器 (SessionManager) → ChatMessageHistory [P0]

#### 10.1 业务架构说明

**模块职责**
- 持久化对话历史
- 管理会话生命周期
- 历史截断和排序
- 内存缓存优化

**关键特性**
- **存储格式**:JSONL(每行一个 JSON 对象)
- **存储位置**:`~/.nanobot-langgraph/sessions/{channel}_{chat_id}.jsonl`
- **内存缓存**:快速访问最近会话
- **历史截断**:默认最多 50 条消息
- **按更新排序**:优先加载活跃会话

**依赖关系**
```
依赖:
└── 文件系统(JSONL 文件)

被依赖:
├── AgentLoop (每个消息处理)
└── ContextBuilder (历史加载)
```

**数据流**
```
Agent 处理消息
  ↓
SessionManager.get_or_create(channel, chat_id)
  ├─ 检查内存缓存
  ├─ 未命中 → 从文件加载
  └─ 创建新会话
  ↓
返回会话历史
  ↓
Agent 处理完成
  ↓
SessionManager.save(session)
  ├─ 更新内存缓存
  └─ 追加到 JSONL 文件
```

**设计原则**
- **缓存优先**:内存缓存提升性能
- **持久化保证**:每次更新立即写入
- **简单可靠**:JSONL 格式易于调试

#### 10.2 LangChain/LangGraph 实现方案

**技术选型**
- **ChatMessageHistory**:LangChain 的历史管理类
- **文件后端**:自定义文件存储
- **Redis 后端**(可选):分布式部署

**架构映射**
```
原实现 → 新实现
├── SessionManager → MemoryManager
├── JSONL 文件 → ChatMessageHistory + 自定义存储
├── 内存缓存 → ChatMessageHistory 内置缓存
└── 历史截断 → 自定义逻辑
```

**关键决策**
1. **使用 ChatMessageHistory**:
   - 标准 LangChain 组件
   - 支持多种后端
   - 自动序列化

2. **自定义存储后端**:
   - 文件后端(默认)
   - Redis 后端(可选)

3. **保持 JSONL 格式**:
   - 与原项目兼容
   - 易于调试

**兼容性考虑**
- 支持原项目的 JSONL 格式
- 会话 key 格式兼容

#### 10.3 实现任务清单

**Task 10.1: 实现 MemoryManager**
- 创建 `memory/manager.py`
- 实现 `MemoryManager` 类
  - `__init__(storage_backend="file")`
  - `get_history(session_key) → ChatMessageHistory`
  - `async def save_history(session_key) → None`
- 实现内存缓存

**Task 10.2: 实现文件后端**
- 实现 `_load_from_file(session_key)` 方法
  - 读取 JSONL 文件
  - 转换为 LangChain 消息
  - 返回 ChatMessageHistory
- 实现 `_save_to_file(session_key, history)` 方法
  - 将消息转换为 JSON
  - 追加到 JSONL 文件

**Task 10.3: 实现历史截断**
- 实现 `_truncate_history(messages, max_count=50)` 方法
  - 保留最近的 N 条消息
  - 保持消息顺序

**Task 10.4: 实现 Redis 后端(可选)**
- 实现 `_load_from_redis(session_key)` 方法
- 实现 `_save_to_redis(session_key, history)` 方法

**Task 10.5: 集成到 AgentLoop**
- 修改 agent_node
  - 加载会话历史
  - 合并历史和当前消息
  - 保存新的消息

#### 10.4 验收标准

**功能验证**
- □ 会话能够正确创建
- □ 历史能够正确保存
- □ 历史能够正确加载
- □ 历史截断生效
- □ 支持多会话并发

**性能指标**
- □ 会话创建延迟 < 50ms
- □ 历史保存延迟 < 100ms
- □ 历史加载延迟 < 100ms

**兼容性验证**
- □ JSONL 格式与原项目兼容
- □ 会话 key 格式兼容

---

### 模块 11: 子 Agent 管理 (SubagentManager) → LangGraph 子图 [P1]

#### 11.1 业务架构说明

**模块职责**
- 创建和管理后台任务
- 并行处理独立任务
- 隔离子 Agent 上下文
- 自动结果汇报

**关键特性**
- **独立上下文**:无历史记录访问
- **限制工具集**:无 message、spawn 工具
- **专注系统提示**:单任务导向
- **后台并行**:不阻塞主 Agent
- **结果汇报**:完成后通过系统频道公布

**依赖关系**
```
依赖:
├── AgentLoop (创建子 Agent 图)
├── MessageBus (结果汇报)
└── ToolRegistry (限制工具)

被依赖:
├── spawn 工具
└── AgentLoop
```

**数据流**
```
主 Agent 调用 spawn 工具
  ↓
SubagentManager.spawn(prompt, tools)
  ↓
创建独立 asyncio 任务
  ├─ 独立上下文
  ├─ 限制工具集
  └─ 专注系统提示
  ↓
子 Agent 执行任务
  ↓
完成后通过系统频道公布结果
  ↓
主 Agent 自然总结给用户
```

**设计原则**
- **隔离**:子 Agent 完全独立
- **并行**:后台执行,不阻塞
- **简单**:自动汇报结果

#### 11.2 LangChain/LangGraph 实现方案

**技术选型**
- **StateGraph**:创建子 Agent 图
- **asyncio.create_task**:后台任务
- **asyncio.Queue**:消息传递

**架构映射**
```
原实现 → 新实现
├── SubagentManager → 子图 + 任务管理
├── 子 Agent 逻辑 → StateGraph
├── 后台任务 → asyncio.create_task
└── 结果汇报 → MessageBus 或 Queue
```

**关键决策**
1. **使用 LangGraph 子图**:
   - 复用 StateGraph 机制
   - 统一的调试和追踪

2. **结果汇报机制**:
   - 选项1:通过 MessageBus 发送到系统频道
   - 选项2:通过 asyncio.Queue 直接传递
   - 推荐:结合两者

**兼容性考虑**
- 保持与原项目相同的行为
- 子 Agent 工具限制一致

#### 11.3 实现任务清单

**Task 11.1: 定义 SubagentState**
- 在 `graphs/state.py` 中定义
  - task: str
  - messages: list[BaseMessage]
  - result: str | None

**Task 11.2: 创建子 Agent 图**
- 创建 `graphs/subagent_graph.py`
- 实现子 Agent 节点
- 实现工具节点
- 实现条件边

**Task 11.3: 实现子 Agent 系统提示**
- 定义 SUBAGENT_SYSTEM_PROMPT
- 强调专注和任务导向

**Task 11.4: 实现 spawn 工具**
- 在 `tools/builtin/spawn.py` 中
- 创建后台任务
- 保存任务引用
- 添加完成回调

**Task 11.5: 实现任务管理**
- 实现全局任务字典
- 实现 _running_tasks 管理
- 实现任务清理

**Task 11.6: 实现结果汇报**
- 实现结果格式化
- 通过 MessageBus 或 Queue 汇报
- 集成到主 Agent

#### 11.4 验收标准

**功能验证**
- □ 子 Agent 能够独立执行任务
- □ 并行子 Agent 正确隔离
- □ 结果正确路由回主 Agent
- □ 工具限制生效
- □ 任务完成后自动清理

**性能指标**
- □ 子 Agent 创建延迟 < 100ms
- □ 支持 10+ 并发子 Agent

**兼容性验证**
- □ 行为与原项目一致
- □ 工具限制一致

---

### 模块 12: 记忆存储 (MemoryStore) → 持久化后端 [P1]

#### 12.1 业务架构说明

**模块职责**
- 长期记忆存储和检索
- 今日笔记管理
- 记忆搜索和查询

**关键特性**
- **存储位置**:`~/.nanobot-langgraph/memory/`
- **文件类型**:
  - MEMORY.md(长期记忆)
  - YYYY-MM-DD.md(今日笔记)
- **简单接口**:read、write、search

**依赖关系**
```
依赖:
└── 文件系统

被依赖:
└── ContextBuilder
```

**数据流**
```
ContextBuilder 请求记忆
  ↓
MemoryStore.load_memory()
  ├─ 读取 MEMORY.md
  ├─ 读取今日笔记
  └─ 返回记忆内容
  ↓
添加到上下文
```

**设计原则**
- **简单**:基于文件的简单存储
- **灵活**:易于编辑和管理
- **可扩展**:未来可升级到数据库

#### 12.2 LangChain/LangGraph 实现方案

**技术选型**
- **文件系统**:Pathlib
- **未来**(可选):Redis、向量数据库

**架构映射**
```
保持原有实现,不需要 LangChain 集成
```

**关键决策**
1. **保持简单**:
   - 文件存储足够
   - 易于调试

2. **可扩展**:
   - 预留接口
   - 未来可升级

**兼容性考虑**
- 完全兼容原项目实现

#### 12.3 实现任务清单

**Task 12.1: 实现 MemoryStore**
- 创建 `memory/store.py`
- 实现 `MemoryStore` 类
  - `load_memory() → str`
  - `save_memory(content: str)`
  - `load_daily_notes(date: date) → str`
  - `save_daily_notes(date: date, content: str)`
  - `search(query: str) → list[str]`

**Task 12.2: 集成到 ContextBuilder**
- 在上下文构建时调用 MemoryStore
- 添加长期记忆和今日笔记

#### 12.4 验收标准

**功能验证**
- □ 能够加载长期记忆
- □ 能够加载今日笔记
- □ 能够保存记忆
- □ 搜索功能正常

---

## 层次五: 基础设施层 (1个模块)

### 模块 13: 配置系统 (Config) → Pydantic Settings [P0]

#### 13.1 业务架构说明

**模块职责**
- 管理所有配置
- 类型安全和验证
- 环境变量覆盖
- 配置迁移支持

**关键特性**
- **Pydantic 模型**:类型安全
- **环境变量**:自动覆盖
- **命名转换**:camelCase ↔ snake_case
- **配置文件**:JSON/TOML 格式

**配置结构**:
```json
{
  "providers": {...},
  "agents": {...},
  "channels": {...},
  "tools": {...},
  "browser": {...}
}
```

**依赖关系**
```
依赖:
└── Pydantic Settings

被依赖:
├── 所有模块
└── 启动流程
```

**数据流**
```
应用启动
  ↓
Config.load()
  ├─ 读取配置文件
  ├─ 应用环境变量覆盖
  ├─ 验证配置
  └─ 返回 Config 实例
  ↓
传递给各模块
```

**设计原则**
- **类型安全**:Pydantic 自动验证
- **配置即代码**:Schema 定义即文档
- **灵活性**:文件 + 环境变量

#### 13.2 LangChain/LangGraph 实现方案

**技术选型**
- **Pydantic v2**:数据验证
- **Pydantic Settings**:环境变量支持

**架构映射**
```
原实现 → 新实现
├── Config Schema → Pydantic 模型
├── Config Loader → Settings 加载器
└── 命名转换 → Field(alias=...)
```

**关键决策**
1. **使用 Pydantic v2**:
   - 性能更好
   - 类型提示更强

2. **环境变量优先**:
   - 配置文件提供默认值
   - 环境变量覆盖

**兼容性考虑**
- 支持原项目的配置结构
- 支持环境变量命名

#### 13.3 实现任务清单

**Task 13.1: 定义配置 Schema**
- 创建 `config/schema.py`
- 定义所有配置模型
  - `ModelConfig`:模型配置
  - `ChannelConfig`:渠道配置
  - `ToolConfig`:工具配置
  - `Settings`:全局配置

**Task 13.2: 实现配置加载器**
- 创建 `config/loader.py`
- 实现 `load_settings() → Settings`
  - 读取配置文件
  - 应用环境变量
  - 验证配置
- 实现 `save_settings(settings)`

**Task 13.3: 实现命名转换**
- 支持 camelCase 配置
- 自动转换为 snake_case

**Task 13.4: 实现配置迁移**
- 检测配置版本
- 自动迁移旧配置

**Task 13.5: 添加配置验证**
- 自定义验证器
- 友好的错误提示

#### 13.4 验收标准

**功能验证**
- □ 配置文件加载正常
- □ 环境变量覆盖生效
- □ 配置验证正常
- □ 命名转换正确
- □ 配置迁移正常

**类型安全**
- □ 类型提示正确
- □ 验证错误提示友好

---

## 实施路线图

基于模块依赖关系和优先级,将实施分为**5个阶段**:

### 阶段1: 基础框架 (第1-2周)

**目标**: 建立项目结构和配置系统

**核心模块**:
- ✅ 模块13: 配置系统(Config)
- ✅ 模块1(部分): AgentState 定义
- ✅ 项目初始化和环境搭建

**详细任务**:
1. 创建项目目录结构
2. 配置 pyproject.toml 和依赖
3. 实现配置系统(模块13)
   - 定义配置 Schema
   - 实现配置加载器
   - 支持环境变量覆盖
4. 定义 AgentState(模块13部分)
   - 创建状态 TypedDict
   - 定义所有字段
5. 搭建开发环境
   - 虚拟环境
   - 代码格式化工具
   - 测试框架

**验收标准**:
- □ 项目结构完整
- □ 依赖安装成功
- □ 配置加载正常
- □ AgentState 定义正确
- □ 测试框架可用

---

### 阶段2: 核心 Agent 循环 (第3-4周)

**目标**: 实现基本的 Agent 决策能力

**核心模块**:
- ✅ 模块1: Agent 循环(StateGraph) - 完整实现
- ✅ 模块3: LLM 提供商集成
- ✅ 模块6(部分): 工具系统基础(文件系统、Shell)
- ✅ 模块2: 上下文构建器

**详细任务**:
1. 实现 LLM 提供商(模块3)
   - 创建 LLM 工厂
   - 支持多个提供商
   - 错误处理和重试
2. 实现工具系统基础(模块6部分)
   - 工具注册表
   - 文件系统工具
   - Shell 工具
   - 安全控制
3. 实现上下文构建器(模块2)
   - 核心身份构建
   - 引导文件加载
   - 系统提示模板
4. 实现 Agent 循环(模块1)
   - StateGraph 创建
   - agent_node 实现
   - should_continue 路由
   - 工具节点集成
5. 基础对话测试
   - 单轮对话
   - 工具调用
   - 多轮对话

**验收标准**:
- □ LLM 调用正常
- □ 工具执行正常
- □ 上下文构建正确
- □ ReAct 循环正常
- □ 基础对话测试通过

---

### 阶段3: 状态管理和记忆 (第5周)

**目标**: 实现多轮对话和记忆功能

**核心模块**:
- ✅ 模块10: 会话管理器
- ✅ 模块12: 记忆存储
- ✅ 模块7: 技能系统

**详细任务**:
1. 实现会话管理器(模块10)
   - ChatMessageHistory 集成
   - 文件后端
   - 历史截断
   - 内存缓存
2. 实现记忆存储(模块12)
   - 长期记忆加载
   - 今日笔记管理
   - 搜索功能
3. 实现技能系统(模块7)
   - SkillsLoader 实现
   - 技能解析
   - 渐进式加载
   - 依赖检查
4. 集成到 Agent 循环
   - 加载会话历史
   - 保存会话历史
   - 整合记忆和技能

**验收标准**:
- □ 会话正确保存和加载
- □ 多轮对话正常
- □ 记忆加载正确
- □ 技能加载正常
- □ 历史截断生效

---

### 阶段4: 高级特性 (第6周)

**目标**: 实现子 Agent 和渠道集成

**核心模块**:
- ✅ 模块11: 子 Agent 管理
- ✅ 模块5: 渠道管理器
- ✅ 模块4(部分): MessageFlow + CLI 渠道
- ✅ 模块6(补充): Web、消息、spawn 工具

**详细任务**:
1. 实现子 Agent 管理(模块11)
   - 子 Agent StateGraph
   - spawn 工具
   - 任务管理
   - 结果汇报
2. 完善工具系统(模块6补充)
   - Web 工具
   - 消息工具
   - spawn 工具
3. 实现消息流(模块4部分)
   - MessageBus 实现
   - MessageFlow (Runnable)
   - 消息分发器
4. 实现渠道管理器(模块5)
   - BaseChannel 定义
   - ChannelManager 实现
   - 权限控制
5. 实现 CLI 渠道
   - CLIChannel 实现
   - Rich 集成
   - 交互模式
6. 并行任务测试
   - 多个子 Agent
   - 任务隔离
   - 结果汇报

**验收标准**:
- □ 子 Agent 独立执行
- □ 并行任务正常
- □ CLI 渠道正常
- □ Web 工具正常
- □ 消息分发正常

---

### 阶段5: 渠道集成和优化 (第7-8周)

**目标**: 完善飞书渠道,性能优化,测试和发布

**核心模块**:
- ✅ 模块5(补充): 飞书渠道
- ✅ 模块8-9(可选): 浏览器自动化、定时任务
- ✅ 性能优化和测试
- ✅ 文档和发布

**详细任务**:
1. 实现飞书渠道(模块5补充)
   - FeishuChannel 实现
   - FastAPI 服务
   - 事件处理
   - 消息发送
2. 可选功能(模块8-9)
   - 浏览器自动化(P2)
   - 定时任务(P2)
3. 性能优化
   - 工具缓存
   - 异步优化
   - 连接池
4. 测试
   - 单元测试(目标>70%)
   - 集成测试
   - 端到端测试
   - 性能测试
5. 文档编写
   - README.md
   - ARCHITECTURE.md
   - API.md
   - 示例代码
6. 发布准备
   - 版本标记
   - 构建包
   - PyPI 发布

**验收标准**:
- □ 飞书渠道正常
- □ 性能达标
- □ 测试覆盖率>70%
- □ 文档完整
- □ 成功发布 v0.1.0

---

## 风险管理

### 风险识别

| 风险类别 | 风险描述 | 影响 | 概率 | 应对策略 |
|---------|---------|------|------|----------|
| **技术风险** | LangGraph 版本兼容性问题 | 高 | 中 | 锁定依赖版本,跟踪上游更新 |
| **技术风险** | 性能不如原实现 | 中 | 低 | 性能基准测试,关键路径优化 |
| **技术风险** | 某些功能难以在 LangGraph 实现 | 中 | 中 | 提前验证 POC,准备降级方案 |
| **功能风险** | 工具调用格式不兼容 | 中 | 低 | 严格测试,兼容性适配层 |
| **功能风险** | 状态管理复杂度增加 | 中 | 中 | 清晰的状态设计,充分文档 |
| **时间风险** | 预估时间不足 | 高 | 中 | 预留 20% 缓冲时间,按优先级分阶段 |
| **资源风险** | 开发人员对 LangChain 不熟悉 | 中 | 高 | 提前学习培训,参考官方示例 |
| **资源风险** | 人力资源不足 | 高 | 低 | 外部协作,简化范围 |

### 关键风险应对

**1. LangGraph 版本兼容性**
- **风险**:LangGraph 快速迭代,API 可能变化
- **缓解**:
  - 锁定主要依赖版本
  - 订阅 Release Notes
  - 延迟升级策略
- **应急**:如果 API 变化,评估迁移成本,必要时锁定版本

**2. 性能不达预期**
- **风险**:LangChain 抽象可能带来性能开销
- **缓解**:
  - 建立性能基准
  - 持续性能监控
  - 关键路径优化
- **应急**:如果性能差距>20%,考虑混合方案(核心路径用原生实现)

**3. 功能实现困难**
- **风险**:某些功能可能在 LangGraph 中难以实现
- **缓解**:
  - 提前 POC 验证
  - 参考 LangGraph 社区方案
  - 准备降级方案
- **应急**:保留原实现代码,混合使用

**4. 时间延期**
- **风险**:低估实现复杂度,导致延期
- **缓解**:
  - 分阶段交付
  - 优先级驱动(P0 > P1 > P2)
  - 预留缓冲时间
- **应急**:砍掉 P2 功能,保证核心功能

**5. 人员熟悉度**
- **风险**:团队对 LangChain/LangGraph 不熟悉
- **缓解**:
  - 提前学习和培训
  - 参考官方示例和文档
  - 代码审查
- **应急**:寻求社区支持,咨询 LangChain 团队

---

## 质量保证

### 测试策略

#### 1. 单元测试
**目标覆盖率**: >70%

**重点测试**:
- 所有工具的执行逻辑
- 路由函数(should_continue)
- 状态转换
- 配置加载和验证
- 会话管理器
- 技能加载器

**测试框架**:pytest、pytest-asyncio、pytest-cov

#### 2. 集成测试
**目标**:验证模块间交互

**测试场景**:
- AgentLoop + ToolRegistry 集成
- AgentLoop + SessionManager 集成
- AgentLoop + ContextBuilder 集成
- MessageBus + ChannelManager 集成

#### 3. 端到端测试
**目标**:验证完整用户场景

**测试场景**:
- 单轮对话(无工具调用)
- 多轮对话(有记忆)
- 工具调用(文件操作)
- 子 Agent 创建和执行
- 并发会话处理

#### 4. 性能测试
**目标**:确保性能不低于原实现

**测试指标**:
- 单次 LLM 调用延迟 < 2秒
- 20 轮迭代完成时间 < 60秒
- 会话创建延迟 < 50ms
- 历史保存延迟 < 100ms

#### 5. 兼容性测试
**目标**:确保与原项目功能兼容

**测试项**:
- 消息格式兼容
- 会话历史格式兼容(JSONL)
- 工具调用格式兼容
- 配置格式兼容

---

### 代码审查

**审查重点**:
1. 关键代码:AgentLoop、ToolRegistry、StateGraph
2. 安全相关:路径验证、权限控制
3. 性能关键:工具执行、会话管理
4. 错误处理:异常捕获、重试逻辑

---

### 持续集成

**CI/CD 流程**:
1. 代码提交 → 自动 linter + 类型检查 + 单元测试
2. Pull Request → 代码审查 + 完整测试
3. 发布 → 自动构建 + 测试 + PyPI 发布

---

### 文档完整性

**必需文档**:
1. README.md:项目介绍、快速开始、安装指南
2. ARCHITECTURE.md:系统架构、模块说明、设计决策
3. API.md:公开 API、使用示例
4. MIGRATION.md:从原项目迁移指南
5. examples/:各种使用示例

---

### 发布标准

**v0.1.0 发布标准**:
- [ ] 所有 P0 模块实现完成
- [ ] 核心功能测试通过
- [ ] 测试覆盖率 >70%
- [ ] 文档完整
- [ ] 性能达标
- [ ] 无已知严重 Bug
- [ ] 至少 1 个完整渠道可用(CLI)

---

## 附录

### A. 参考文档

**原项目文档**:
- [项目架构分析.md](项目架构分析.md) - 完整的项目概览和模块说明
- [docs/architecture/modules/](docs/architecture/modules/) - 13个核心模块的详细架构文档

**LangChain/LangGraph 文档**:
- [LangChain 官方文档](https://python.langchain.com/)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangSmith 文档](https://docs.smith.langchain.com/)

### B. 快速参考

**模块优先级**:
- **P0(核心必须)**:模块 1、2、3、4、6、10、13
- **P1(重要应该)**:模块 5、7、11、12
- **P2(可选后期)**:模块 8、9

**关键决策**:
1. 使用 StateGraph 替代手动循环
2. 使用 LangChain 原生提供商替代 LiteLLM
3. 使用 ChatMessageHistory 替代自定义 SessionManager
4. 保持渐进式技能加载策略
5. 浏览器和定时任务作为可选功能

**预期收益**:
- 代码量减少 37%(8000 → 5000 行)
- 可观测性提升(LangSmith 自动追踪)
- 调试能力增强(图可视化)
- 扩展性改善(添加节点/边更容易)

### C. 时间表

| 阶段 | 时间 | 里程碑 |
|-----|------|-------|
| 阶段1: 基础框架 | 第1-2周 | 配置系统、AgentState 完成 |
| 阶段2: 核心 Agent | 第3-4周 | 基本对话能力验证 |
| 阶段3: 状态管理 | 第5周 | 多轮对话验证 |
| 阶段4: 高级特性 | 第6周 | 子 Agent 并行验证 |
| 阶段5: 渠道集成 | 第7-8周 | 发布 v0.1.0 |

**总计**: 约 8 周

---

## 总结

本文档提供了 nanobot 项目迁移到 LangChain/LangGraph 框架的完整计划,包括:

✅ **完整的架构映射**:13个核心模块的详细说明
✅ **业务架构说明**:每个模块的职责、特性、依赖、数据流
✅ **实现方案**:LangChain/LangGraph 技术选型和架构映射
✅ **任务清单**:每个模块的具体实现任务
✅ **验收标准**:明确的功能、集成、性能、兼容性验证标准
✅ **实施路线图**:基于依赖关系的5个阶段
✅ **风险管理**:识别关键风险和应对策略
✅ **质量保证**:测试策略、代码审查、CI/CD、文档标准

本计划的核心优势:
- **不提供代码**:只提供架构和实施指导,避免实现细节过时
- **模块化组织**:按模块而非时间组织,更清晰
- **可执行性强**:每个任务都有明确的验收标准
- **风险可控**:提前识别风险并准备应对策略

遵循本计划,预计在 8 周内完成核心功能的迁移,代码量减少 37%,同时保持功能兼容性和性能水平。

---

**文档版本**: v2.0
**创建日期**: 2025-02-16
**最后更新**: 2025-02-16
**基于**: nanobot 项目 main 分支分析

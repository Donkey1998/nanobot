# 会话管理模块

> **文件位置**: [nanobot/session/manager.py](../../../nanobot/session/manager.py)
> **行数**: 约 203 行
> **最后更新**: 2026-02-10

---

## 1. 概述

会话管理模块负责持久化对话历史，使 Agent 能够记住跨请求的上下文，实现多轮对话。

### 核心职责

- **会话存储**: 持久化对话历史到磁盘
- **内存缓存**: 快速访问最近使用的会话
- **历史截断**: 限制传递给 LLM 的消息数量
- **状态管理**: 跟踪会话的创建和更新时间

### 存储格式

- **位置**: `~/.nanobot/sessions/{channel}_{chat_id}.jsonl`
- **格式**: JSONL（每行一个 JSON 对象）
- **结构**: 元数据行 + 消息行

### 相关模块

- [Agent 循环](agent-loop.md) - 会话管理的主要使用者
- [上下文构建器](context-builder.md) - 使用会话历史构建上下文

---

## 2. 设计理念

### 2.1 JSONL 格式

使用 JSONL（JSON Lines）格式存储会话，便于读写和追加。

**示例**:
```jsonl
{"_type": "metadata", "created_at": "2026-02-10T10:00:00Z", "updated_at": "2026-02-10T10:30:00Z", "metadata": {}}
{"role": "user", "content": "你好", "timestamp": "2026-02-10T10:00:01Z"}
{"role": "assistant", "content": "你好！有什么可以帮助你的？", "timestamp": "2026-02-10T10:00:02Z"}
{"role": "user", "content": "帮我写一个 Python 函数", "timestamp": "2026-02-10T10:30:00Z"}
{"role": "assistant", "content": "当然！你想要什么样的函数？", "timestamp": "2026-02-10T10:30:01Z"}
```

### 2.2 内存缓存优先

优先使用内存缓存加速访问，未命中时从磁盘加载。

### 2.3 按更新时间排序

列表会话时按更新时间排序，优先显示活跃会话。

---

## 3. 核心机制

### 3.1 会话数据结构

**代码位置**: [manager.py:14-59](../../../nanobot/session/manager.py#L14-L59)

```python
@dataclass
class Session:
    key: str  # channel:chat_id
    messages: list[dict[str, Any]]  # 消息列表
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间
    metadata: dict[str, Any]  # 额外元数据
```

### 3.2 会话生命周期

```
get_or_create(key)
    ├─ 检查内存缓存
    ├─ 未命中 → 从磁盘加载
    └─ 仍不存在 → 创建新会话
    ↓
add_message(role, content)
    ├─ 添加到 messages 列表
    └─ 更新 updated_at
    ↓
save(session)
    ├─ 写入磁盘（JSONL 格式）
    └─ 更新内存缓存
```

### 3.3 历史截断

`get_history()` 方法限制返回的消息数量，避免 Token 浪费。

**代码位置**: [manager.py:39-53](../../../nanobot/session/manager.py#L39-L53)

```python
def get_history(self, max_messages: int = 50) -> list[dict[str, Any]]:
    recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
    return [{"role": m["role"], "content": m["content"]} for m in recent]
```

---

## 4. 关键接口

### 4.1 Session

#### 属性

```python
key: str  # 会话标识符（channel:chat_id）
messages: list[dict[str, Any]]  # 消息列表
created_at: datetime  # 创建时间
updated_at: datetime  # 最后更新时间
metadata: dict[str, Any]  # 额外元数据
```

#### 方法

```python
def add_message(self, role: str, content: str, **kwargs: Any) -> None:
    """添加消息到会话"""

def get_history(self, max_messages: int = 50) -> list[dict[str, Any]]:
    """获取 LLM 格式的历史记录"""

def clear(self) -> None:
    """清除所有消息"""
```

### 4.2 SessionManager

#### 构造函数

```python
def __init__(self, workspace: Path):
    self.workspace = workspace
    self.sessions_dir = ensure_dir(Path.home() / ".nanobot" / "sessions")
    self._cache: dict[str, Session] = {}
```

#### 方法

```python
def get_or_create(self, key: str) -> Session:
    """获取或创建会话"""

def save(self, session: Session) -> None:
    """保存会话到磁盘"""

def delete(self, key: str) -> bool:
    """删除会话"""

def list_sessions(self) -> list[dict[str, Any]]:
    """列出所有会话（按更新时间排序）"""

def _load(self, key: str) -> Session | None:
    """从磁盘加载会话"""

def _get_session_path(self, key: str) -> Path:
    """获取会话文件路径"""
```

---

## 5. 使用示例

### 5.1 基础使用

```python
from pathlib import Path
from nanobot.session.manager import SessionManager

# 创建会话管理器
manager = SessionManager(Path("~/.nanobot/workspace").expanduser())

# 获取或创建会话
session = manager.get_or_create("telegram:123456")

# 添加消息
session.add_message("user", "你好，我是新用户")
session.add_message("assistant", "欢迎！有什么可以帮助你的？")

# 保存会话
manager.save(session)
```

### 5.2 获取历史记录

```python
# 获取最近 50 条消息
history = session.get_history(max_messages=50)
# history = [
#     {"role": "user", "content": "..."},
#     {"role": "assistant", "content": "..."},
#     ...
# ]

# 获取最近 10 条消息
recent_history = session.get_history(max_messages=10)
```

### 5.3 列出所有会话

```python
# 列出所有会话
sessions = manager.list_sessions()

for session_info in sessions:
    print(f"会话: {session_info['key']}")
    print(f"  创建: {session_info['created_at']}")
    print(f"  更新: {session_info['updated_at']}")
```

### 5.4 删除会话

```python
# 删除会话
deleted = manager.delete("telegram:123456")
if deleted:
    print("会话已删除")
else:
    print("会话不存在")
```

### 5.5 会话元数据

```python
# 创建带元数据的会话
session = manager.get_or_create("cli:interactive")
session.metadata["user_type"] = "premium"
session.metadata["preferences"] = {"theme": "dark"}

# 使用元数据
if session.metadata.get("user_type") == "premium":
    # 提供高级功能
    pass
```

---

## 6. 扩展指南

### 6.1 添加会话搜索

```python
class SearchableSessionManager(SessionManager):
    def search_sessions(self, query: str) -> list[dict]:
        """在会话内容中搜索"""
        results = []
        for session_info in self.list_sessions():
            session = self.get_or_create(session_info["key"])
            # 搜索消息内容
            for msg in session.messages:
                if query.lower() in msg.get("content", "").lower():
                    results.append({
                        "key": session.key,
                        "match": msg["content"]
                    })
                    break
        return results
```

### 6.2 会话导出

```python
class ExportableSessionManager(SessionManager):
    def export_session(self, key: str, format: str = "json") -> str:
        """导出会话"""
        session = self.get_or_create(key)

        if format == "json":
            return json.dumps(asdict(session), indent=2)
        elif format == "markdown":
            # 转换为 Markdown 格式
            lines = [f"# Session: {key}\n"]
            for msg in session.messages:
                role = msg["role"].title()
                content = msg["content"]
                timestamp = msg.get("timestamp", "")
                lines.append(f"## {role} ({timestamp})\n\n{content}\n")
            return "\n".join(lines)
        elif format == "txt":
            # 纯文本格式
            lines = []
            for msg in session.messages:
                lines.append(f"[{msg['role']}] {msg['content']}")
            return "\n".join(lines)
```

### 6.3 会话统计

```python
class AnalyticsSessionManager(SessionManager):
    def get_session_stats(self, key: str) -> dict:
        """获取会话统计"""
        session = self.get_or_create(key)

        user_messages = [m for m in session.messages if m["role"] == "user"]
        assistant_messages = [m for m in session.messages if m["role"] == "assistant"]

        return {
            "total_messages": len(session.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "duration": (session.updated_at - session.created_at).total_seconds(),
            "avg_response_length": sum(len(m.get("content", "")) for m in assistant_messages) / max(len(assistant_messages), 1)
        }
```

### 6.4 会话压缩

对于长会话，可以压缩旧消息：

```python
class CompressingSessionManager(SessionManager):
    def compress_session(self, key: str, keep_recent: int = 20):
        """压缩会话，只保留最近 N 条消息的完整内容"""
        session = self.get_or_create(key)

        if len(session.messages) <= keep_recent:
            return

        # 保留旧消息的摘要
        old_messages = session.messages[:-keep_recent]
        summary = self._summarize_messages(old_messages)

        # 创建压缩会话
        compressed_messages = [
            {"role": "system", "content": f"对话历史摘要：{summary}"}
        ]
        compressed_messages.extend(session.messages[-keep_recent:])

        session.messages = compressed_messages
        self.save(session)

    def _summarize_messages(self, messages: list[dict]) -> str:
        """生成消息摘要"""
        # 可以调用 LLM 生成摘要
        # 或使用简单的启发式规则
        topics = set()
        for msg in messages:
            # 提取关键词
            pass
        return f"讨论了 {len(topics)} 个主题"
```

### 6.5 多租户支持

```python
class MultiTenantSessionManager(SessionManager):
    def __init__(self, workspace: Path, tenant_id: str):
        super().__init__(workspace)
        self.tenant_id = tenant_id
        # 使用租户隔离的会话目录
        self.sessions_dir = ensure_dir(
            Path.home() / ".nanobot" / "sessions" / tenant_id
        )

    def get_or_create(self, key: str) -> Session:
        # 添加租户前缀
        tenant_key = f"{self.tenant_id}:{key}"
        return super().get_or_create(tenant_key)
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/session/manager.py](../../../nanobot/session/manager.py) - 会话管理器（203 行）

### 依赖模块

- [nanobot/agent/loop.py](../../../nanobot/agent/loop.py) - 会话的使用者
- [nanobot/agent/context.py](../../../nanobot/agent/context.py) - 使用会话历史

### 相关文档

- [Agent 循环模块文档](agent-loop.md)
- [上下文构建器模块文档](context-builder.md)

## 数据目录结构

```
~/.nanobot/
└── sessions/
    ├── telegram_123456.jsonl
    ├── discord_789012.jsonl
    ├── cli_direct.jsonl
    └── ...
```

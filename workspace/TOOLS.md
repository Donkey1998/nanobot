# 可用工具

本文档描述了 nanobot 可用的工具。

## 文件操作

### read_file
读取文件的内容。
```
read_file(path: str) -> str
```

### write_file
将内容写入文件（如需要会创建父目录）。
```
write_file(path: str, content: str) -> str
```

### edit_file
通过替换特定文本来编辑文件。
```
edit_file(path: str, old_text: str, new_text: str) -> str
```

### list_dir
列出目录的内容。
```
list_dir(path: str) -> str
```

## Shell 执行

### exec
执行 Shell 命令并返回输出。
```
exec(command: str, working_dir: str = None) -> str
```

**安全说明：**
- 命令有 60 秒超时
- 输出在 10,000 个字符处截断
- 对破坏性操作要谨慎使用

## Web 访问

### web_search
使用 DuckDuckGo 搜索网络。
```
web_search(query: str) -> str
```

返回前 5 个搜索结果，包括标题、URL 和摘要。

### web_fetch
从 URL 获取并提取主要内容。
```
web_fetch(url: str) -> str
```

**说明：**
- 使用 trafilatura 提取内容
- 输出在 8,000 个字符处截断

## 通信

### message
向用户发送消息（内部使用）。
```
message(content: str, channel: str = None, chat_id: str = None) -> str
```

## 计划提醒 (Cron)

使用 `exec` 工具通过 `nanobot cron add` 创建计划提醒：

### 设置重复提醒
```bash
# 每天上午 9 点
nanobot cron add --name "morning" --message "早上好！☀️" --cron "0 9 * * *"

# 每 2 小时
nanobot cron add --name "water" --message "喝水！💧" --every 7200
```

### 设置一次性提醒
```bash
# 在特定时间（ISO 格式）
nanobot cron add --name "meeting" --message "会议开始！" --at "2025-01-31T15:00:00"
```

### 管理提醒
```bash
nanobot cron list              # 列出所有任务
nanobot cron remove <job_id>   # 移除任务
```

## 心跳任务管理

工作区中的 `HEARTBEAT.md` 文件每 30 分钟检查一次。
使用文件操作来管理周期性任务：

### 添加心跳任务
```python
# 追加新任务
edit_file(
    path="HEARTBEAT.md",
    old_text="## 示例任务",
    new_text="- [ ] 这里是新的周期性任务\n\n## 示例任务"
)
```

### 移除心跳任务
```python
# 移除特定任务
edit_file(
    path="HEARTBEAT.md",
    old_text="- [ ] 要移除的任务\n",
    new_text=""
)
```

### 重写所有任务
```python
# 替换整个文件
write_file(
    path="HEARTBEAT.md",
    content="# 心跳任务\n\n- [ ] 任务 1\n- [ ] 任务 2\n"
)
```

---

## 添加自定义工具

要添加自定义工具：
1. 在 `nanobot/agent/tools/` 中创建一个扩展 `Tool` 的类
2. 实现 `name`、`description`、`parameters` 和 `execute`
3. 在 `AgentLoop._register_default_tools()` 中注册

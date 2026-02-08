<div align="center">
  <img src="nanobot_logo.png" alt="nanobot" width="500">
  <h1>nanobot: 超轻量级个人 AI 助手</h1>
  <p>
    <a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
    <a href="https://pepy.tech/project/nanobot-ai"><img src="https://static.pepy.tech/badge/nanobot-ai" alt="Downloads"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat&logo=feishu&logoColor=white" alt="Feishu"></a>
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat&logo=wechat&logoColor=white" alt="WeChat"></a>
    <a href="https://discord.gg/MnCvHqpUGB"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

🐈 **nanobot** 是一个受 [Clawdbot](https://github.com/openclaw/openclaw) 启发的**超轻量级**个人 AI 助手

⚡️ 仅用 **~4,000** 行代码提供核心 agent 功能 —— 比 Clawdbot 的 430k+ 行代码**小 99%**。

📏 实时代码行数：**3,428 行**（随时运行 `bash core_agent_lines.sh` 验证）

## 📢 新闻

- **2026-02-06** ✨ 添加了 Moonshot/Kimi 提供商、Discord 频道和增强的安全硬化！
- **2026-02-05** ✨ 添加了飞书频道、DeepSeek 提供商和增强的定时任务支持！
- **2026-02-04** 🚀 发布 v0.1.3.post4，支持多提供商和 Docker！查看[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.3.post4)了解详情。
- **2026-02-03** ⚡ 集成了 vLLM 以支持本地 LLM 和改进的自然语言任务调度！
- **2026-02-02** 🎉 nanobot 正式发布！欢迎尝试 🐈 nanobot！

## nanobot 的主要特点：

🪶 **超轻量级**：仅约 4,000 行核心 agent 代码 — 比 Clawdbot 小 99%。

🔬 **研究就绪**：代码简洁、易读，易于理解、修改和扩展以进行研究。

⚡️ **闪电般快速**：最小的占用空间意味着更快的启动、更低的资源使用和更快的迭代。

💎 **易于使用**：一键部署即可使用。

## 🏗️ 架构

<p align="center">
  <img src="nanobot_arch.png" alt="nanobot architecture" width="800">
</p>

## ✨ 功能特性

<table align="center">
  <tr align="center">
    <th><p align="center">📈 24/7 实时市场分析</p></th>
    <th><p align="center">🚀 全栈软件工程师</p></th>
    <th><p align="center">📅 智能日常管理器</p></th>
    <th><p align="center">📚 个人知识助手</p></th>
  </tr>
  <tr>
    <td align="center"><p align="center"><img src="case/search.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/code.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/scedule.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/memory.gif" width="180" height="400"></p></td>
  </tr>
  <tr>
    <td align="center">发现 • 洞察 • 趋势</td>
    <td align="center">开发 • 部署 • 扩展</td>
    <td align="center">调度 • 自动化 • 组织</td>
    <td align="center">学习 • 记忆 • 推理</td>
  </tr>
</table>

## 📦 安装

**从源代码安装**（最新功能，推荐用于开发）

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

**使用 [uv](https://github.com/astral-sh/uv) 安装**（稳定、快速）

```bash
uv tool install nanobot-ai
```

**从 PyPI 安装**（稳定）

```bash
pip install nanobot-ai
```

## 🚀 快速开始

> [!TIP]
> 在 `~/.nanobot/config.json` 中设置你的 API 密钥。
> 获取 API 密钥：[OpenRouter](https://openrouter.ai/keys) （全球）· [DashScope](https://dashscope.console.aliyun.com) （Qwen）· [Brave Search](https://brave.com/search/api/) （可选，用于网络搜索）

**1. 初始化**

```bash
nanobot onboard
```

**2. 配置**（`~/.nanobot/config.json`）

对于 OpenRouter - 推荐全球用户使用：
```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  }
}
```

**3. 聊天**

```bash
nanobot agent -m "What is 2+2?"
```

就这样！你在 2 分钟内就有了一个可用的 AI 助手。

## 🖥️ 本地模型（vLLM）

使用你自己的本地模型运行 nanobot，使用 vLLM 或任何兼容 OpenAI 的服务器。

**1. 启动你的 vLLM 服务器**

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

**2. 配置**（`~/.nanobot/config.json`）

```json
{
  "providers": {
    "vllm": {
      "apiKey": "dummy",
      "apiBase": "http://localhost:8000/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "meta-llama/Llama-3.1-8B-Instruct"
    }
  }
}
```

**3. 聊天**

```bash
nanobot agent -m "Hello from my local LLM!"
```

> [!TIP]
> 对于不需要身份验证的本地服务器，`apiKey` 可以是任何非空字符串。

## 💬 聊天应用

通过 Telegram、Discord、WhatsApp 或飞书与你的 nanobot 对话 — 随时随地。

| 频道 | 设置 |
|---------|-------|
| **Telegram** | 简单（只需一个令牌） |
| **Discord** | 简单（机器人令牌 + intents） |
| **WhatsApp** | 中等（扫描二维码） |
| **Feishu** | 中等（应用凭证） |

<details>
<summary><b>Telegram</b>（推荐）</summary>

**1. 创建一个机器人**
- 打开 Telegram，搜索 `@BotFather`
- 发送 `/newbot`，按照提示操作
- 复制令牌

**2. 配置**

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

> 从 Telegram 上的 `@userinfobot` 获取你的用户 ID。

**3. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>Discord</b></summary>

**1. 创建一个机器人**
- 访问 https://discord.com/developers/applications
- 创建应用程序 → Bot → 添加 Bot
- 复制机器人令牌

**2. 启用 intents**
- 在 Bot 设置中，启用 **MESSAGE CONTENT INTENT**
- （可选）如果你计划使用基于成员数据的允许列表，启用 **SERVER MEMBERS INTENT**

**3. 获取你的用户 ID**
- Discord 设置 → 高级 → 启用 **开发者模式**
- 右键点击你的头像 → **复制用户 ID**

**4. 配置**

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

**5. 邀请机器人**
- OAuth2 → URL 生成器
- 范围：`bot`
- 机器人权限：`Send Messages`、`Read Message History`
- 打开生成的邀请 URL 并将机器人添加到你的服务器

**6. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>WhatsApp</b></summary>

需要 **Node.js ≥18**。

**1. 链接设备**

```bash
nanobot channels login
# 使用 WhatsApp → 设置 → 链接设备扫描二维码
```

**2. 配置**

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

**3. 运行**（两个终端）

```bash
# 终端 1
nanobot channels login

# 终端 2
nanobot gateway
```

</details>

<details>
<summary><b>Feishu (飞书)</b></summary>

使用 **WebSocket** 长连接 — 不需要公网 IP。

```bash
pip install nanobot-ai[feishu]
```

**1. 创建一个飞书机器人**
- 访问[飞书开放平台](https://open.feishu.cn/app)
- 创建一个新应用 → 启用 **Bot** 功能
- **权限**：添加 `im:message`（发送消息）
- **事件**：添加 `im.message.receive_v1`（接收消息）
  - 选择 **长连接** 模式（需要先运行 nanobot 建立连接）
- 从"凭证与基础信息"获取 **App ID** 和 **App Secret**
- 发布应用

**2. 配置**

```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "cli_xxx",
      "appSecret": "xxx",
      "encryptKey": "",
      "verificationToken": "",
      "allowFrom": []
    }
  }
}
```

> `encryptKey` 和 `verificationToken` 对于长连接模式是可选的。
> `allowFrom`：留空允许所有用户，或添加 `["ou_xxx"]` 来限制访问。

**3. 运行**

```bash
nanobot gateway
```

> [!TIP]
> 飞书使用 WebSocket 接收消息 — 不需要 webhook 或公网 IP！

</details>

## ⚙️ 配置

配置文件：`~/.nanobot/config.json`

### 提供商

> [!NOTE]
> Groq 通过 Whisper 提供免费的语音转录。如果配置，Telegram 语音消息将自动转录。

| 提供商 | 用途 | 获取 API 密钥 |
|----------|---------|-------------|
| `openrouter` | LLM（推荐，访问所有模型） | [openrouter.ai](https://openrouter.ai) |
| `anthropic` | LLM（Claude 直接访问） | [console.anthropic.com](https://console.anthropic.com) |
| `openai` | LLM（GPT 直接访问） | [platform.openai.com](https://platform.openai.com) |
| `deepseek` | LLM（DeepSeek 直接访问） | [platform.deepseek.com](https://platform.deepseek.com) |
| `groq` | LLM + **语音转录**（Whisper） | [console.groq.com](https://console.groq.com) |
| `gemini` | LLM（Gemini 直接访问） | [aistudio.google.com](https://aistudio.google.com) |
| `dashscope` | LLM（Qwen） | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |


### 安全性

> [!TIP]
> 对于生产部署，在配置中设置 `"restrictToWorkspace": true` 以沙盒化 agent。

| 选项 | 默认值 | 描述 |
|--------|---------|-------------|
| `tools.restrictToWorkspace` | `false` | 当为 `true` 时，将**所有** agent 工具（shell、文件读/写/编辑、列表）限制在工作区目录。防止路径遍历和越界访问。 |
| `channels.*.allowFrom` | `[]`（允许所有） | 用户 ID 白名单。空 = 允许所有人；非空 = 只有列出的用户可以交互。 |


## CLI 参考

| 命令 | 描述 |
|---------|-------------|
| `nanobot onboard` | 初始化配置和工作区 |
| `nanobot agent -m "..."` | 与 agent 聊天 |
| `nanobot agent` | 交互式聊天模式 |
| `nanobot gateway` | 启动网关 |
| `nanobot status` | 显示状态 |
| `nanobot channels login` | 链接 WhatsApp（扫描二维码） |
| `nanobot channels status` | 显示频道状态 |

<details>
<summary><b>定时任务（Cron）</b></summary>

```bash
# 添加任务
nanobot cron add --name "daily" --message "Good morning!" --cron "0 9 * * *"
nanobot cron add --name "hourly" --message "Check status" --every 3600

# 列出任务
nanobot cron list

# 移除任务
nanobot cron remove <job_id>
```

</details>

## 🐳 Docker

> [!TIP]
> `-v ~/.nanobot:/root/.nanobot` 标志将本地配置目录挂载到容器中，因此你的配置和工作区在容器重启后仍然存在。

在容器中构建和运行 nanobot：

```bash
# 构建镜像
docker build -t nanobot .

# 初始化配置（仅第一次）
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard

# 在主机上编辑配置以添加 API 密钥
vim ~/.nanobot/config.json

# 运行网关（连接到 Telegram/WhatsApp）
docker run -v ~/.nanobot:/root/.nanobot -p 18790:18790 nanobot gateway

# 或运行单个命令
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "Hello!"
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot status
```

## 📁 项目结构

```
nanobot/
├── agent/          # 🧠 核心 agent 逻辑
│   ├── loop.py     #    Agent 循环（LLM ↔ 工具执行）
│   ├── context.py  #    提示构建器
│   ├── memory.py   #    持久化内存
│   ├── skills.py   #    技能加载器
│   ├── subagent.py #    后台任务执行
│   └── tools/      #    内置工具（包括 spawn）
├── skills/         # 🎯 捆绑的技能（github、weather、tmux...）
├── channels/       # 📱 WhatsApp 集成
├── bus/            # 🚌 消息路由
├── cron/           # ⏰ 定时任务
├── heartbeat/      # 💓 主动唤醒
├── providers/      # 🤖 LLM 提供商（OpenRouter 等）
├── session/        # 💬 对话会话
├── config/         # ⚙️ 配置
└── cli/            # 🖥️ 命令
```

## 🤝 贡献和路线图

欢迎 PR！代码库故意保持小巧和易读。🤗

**路线图** — 选择一项并[打开 PR](https://github.com/HKUDS/nanobot/pulls)！

- [x] **语音转录** — 支持 Groq Whisper（问题 #13）
- [ ] **多模态** — 看见和听到（图像、语音、视频）
- [ ] **长期记忆** — 永不忘记重要上下文
- [ ] **更好的推理** — 多步骤规划和反思
- [ ] **更多集成** — Discord、Slack、电子邮件、日历
- [ ] **自我改进** — 从反馈和错误中学习

### 贡献者

<a href="https://github.com/HKUDS/nanobot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/nanobot&max=100&columns=12" />
</a>


## ⭐ Star History

<div align="center">
  <a href="https://star-history.com/#HKUDS/nanobot&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date&theme=dark" />
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date" />
      <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date" style="border-radius: 15px; box-shadow: 0 0 30px rgba(0, 217, 255, 0.3);" />
    </picture>
  </a>
</div>

<p align="center">
  <em> 感谢访问 ✨ nanobot！</em><br><br>
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.nanobot&style=for-the-badge&color=00d4ff" alt="Views">
</p>


<p align="center">
  <sub>nanobot 仅用于教育、研究和技术交流目的</sub>
</p>

# 飞书机器人配置指南

本指南介绍如何将 nanobot AI 助手接入飞书，通过 WebSocket 长连接实现消息收发。

## 前置要求

- Python >= 3.11
- 飞书账号
- nanobot 已安装

## 安装依赖

```bash
pip install lark-oapi
```

或安装完整依赖：

```bash
pip install nanobot-ai[feishu]
```

## 配置步骤

### 第一步：在飞书开放平台创建应用

1. **访问开放平台**

   登录 [飞书开放平台](https://open.feishu.cn/app)

2. **创建应用**

   - 点击「创建企业自建应用」
   - 填写应用名称（如：nanobot AI 助手）
   - 选择应用所属企业

3. **启用机器人能力**

   - 在应用管理页面，找到「能力」
   - 添加「机器人」能力并启用

4. **配置权限**

   添加以下权限：
   - `im:message` - 发送消息（必需）
   - `im:message:group_at_msg` - 接收群组 @ 消息（可选）
   - `im:chat` - 访问群组信息（如需在群组中使用）

5. **配置事件订阅**

   - 进入「事件」
   - 添加事件：`im.message.receive_v1`
   - **选择「长连接」模式**（推荐，无需公网 IP）
   - 点击「添加」保存

6. **发布应用**

   - 在「版本管理与发布」中
   - 点击「创建版本」
   - 填写版本号和更新说明
   - 点击「申请发布」

### 第二步：获取凭证

1. 在应用管理页面，找到「凭证与基础信息」
2. 复制以下信息：
   - **App ID**（格式如 `cli_xxx`）
   - **App Secret**

### 第三步：修改 nanobot 配置

配置文件位置：`~/.nanobot/config.json`（Windows 下为 `C:\Users\你的用户名\.nanobot\config.json`）

```json
{
  "providers": {
    "zhipu": {
      "apiKey": "你的智谱AI密钥"
    }
  },
  "agents": {
    "defaults": {
      "model": "zai/glm-4.7"
    }
  },
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "cli_a9028f7b49b89cb3",
      "appSecret": "71OVoWQGjGK4t29dND64FfwJRs7G5qBe",
      "encryptKey": "",
      "verificationToken": "",
      "allowFrom": []
    }
  }
}
```

**配置说明：**

| 字段 | 说明 | 必填 |
|------|------|------|
| `enabled` | 是否启用飞书渠道 | 是 |
| `appId` | 飞书应用的 App ID | 是 |
| `appSecret` | 飞书应用的 App Secret | 是 |
| `encryptKey` | 加密 Key（长连接模式可留空） | 否 |
| `verificationToken` | 验证 Token（长连接模式可留空） | 否 |
| `allowFrom` | 允许的用户 open_id 列表，空数组表示允许所有人 | 否 |

### 第四步：启动网关

```bash
nanobot gateway
```

看到以下日志表示启动成功：

```
INFO - Feishu bot started with WebSocket long connection
INFO - No public IP required - using WebSocket to receive events
```

### 第五步：在飞书中使用

1. 在飞书中搜索你的机器人应用名称
2. 向机器人发送消息即可开始对话
3. 机器人会收到消息并自动回复

## 高级配置

### 限制特定用户使用

如果只想让特定用户使用机器人，设置 `allowFrom`：

```json
{
  "channels": {
    "feishu": {
      "allowFrom": ["ou_xxx", "ou_yyy"]
    }
  }
}
```

如何获取用户的 open_id：
- 在飞书中与机器人对话后，查看日志中记录的 sender_id

### 在群组中使用

1. 将机器人添加到飞书群组
2. 在群组中 @机器人 即可触发回复
3. 确保已添加 `im:message:group_at_msg` 权限

### 切换模型

修改 `agents.defaults.model` 可以使用不同的 LLM：

```json
{
  "agents": {
    "defaults": {
      "model": "zai/glm-4.7"
    }
  },
  "providers": {
    "zhipu": {
      "apiKey": "你的密钥"
    }
  }
}
```

支持的模型示例：
- `zai/glm-4.7` - 智谱 GLM-4.7
- `zhipu/glm-4-flash` - 智谱 GLM-4-Flash（免费）
- `anthropic/claude-opus-4-5` - Claude Opus 4.5
- `openai/gpt-4o` - GPT-4o

## 常见问题

### Q: 启动报错 "Feishu SDK not installed"

A: 安装 lark-oapi：
```bash
pip install lark-oapi
```

### Q: 收不到消息

A: 检查以下几点：
1. 应用是否已发布
2. 事件订阅是否添加 `im.message.receive_v1`
3. 是否选择了「长连接」模式
4. App ID 和 App Secret 是否正确

### Q: 机器人不回复

A: 检查以下几点：
1. LLM API Key 是否正确配置
2. 网络是否正常
3. 查看控制台日志获取详细错误信息

### Q: 如何停止机器人？

A: 在运行 `nanobot gateway` 的终端按 `Ctrl+C`

### Q: 可以同时使用多个聊天平台吗？

A: 可以，在配置文件中同时启用多个渠道：
```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "xxx",
      "appSecret": "xxx"
    },
    "telegram": {
      "enabled": true,
      "token": "xxx"
    }
  }
}
```

## 技术说明

### WebSocket 长连接模式

nanobot 使用 WebSocket 长连接接收飞书消息，优势：
- 无需公网 IP
- 无需配置 webhook
- 实时性更好
- 连接更稳定

### 消息去重

机器人内置消息去重机制，最多缓存 1000 条已处理消息，防止重复处理。

### 正在输入提示

机器人收到消息后会自动给消息添加点赞表情，表示已收到并正在处理。

## 安全建议

1. **不要将配置文件提交到公开仓库**
   - 配置文件包含敏感信息（API Key、App Secret）

2. **使用 allowFrom 限制访问**
   - 生产环境建议设置 `allowFrom` 限制用户

3. **启用工作空间限制**
   - 设置 `tools.restrictToWorkspace: true` 限制文件访问范围

```json
{
  "tools": {
    "restrictToWorkspace": true
  }
}
```

## 相关链接

- [飞书开放平台](https://open.feishu.cn/app)
- [nanobot GitHub](https://github.com/HKUDS/nanobot)
- [lark-oapi SDK 文档](https://github.com/larksuite/lark-oapi-python)

---

如有问题，欢迎在 [GitHub Issues](https://github.com/HKUDS/nanobot/issues) 提问。

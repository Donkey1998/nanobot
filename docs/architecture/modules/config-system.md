# 配置系统模块

> **文件位置**: [nanobot/config/](../../../nanobot/config/)
> **主要文件**: schema.py (197 行), loader.py (107 行)
> **最后更新**: 2026-02-10

---

## 1. 概述

配置系统模块负责管理 nanobot 的所有配置，使用 Pydantic 实现类型安全和验证，支持环境变量覆盖。

### 核心职责

- **配置模型**: 定义所有配置项的类型和验证规则
- **配置加载**: 从 JSON 文件或环境变量加载配置
- **配置保存**: 将配置持久化到文件
- **命名转换**: camelCase ↔ snake_case 自动转换
- **配置迁移**: 自动处理旧版本配置格式

### 配置文件位置

- **默认路径**: `~/.nanobot/config.json`
- **环境变量前缀**: `NANOBOT_`
- **嵌套分隔符**: `__` (双下划线)

### 相关模块

- 所有模块都依赖配置系统

---

## 2. 设计理念

### 2.1 Pydantic 类型安全

使用 Pydantic BaseModel 定义配置，自动进行类型验证和转换。

### 2.12 分层配置结构

```
Config (根)
├── agents (Agent 配置)
├── channels (渠道配置)
├── providers (LLM 提供商配置)
├── gateway (网关配置)
├── tools (工具配置)
└── browser (浏览器配置)
```

### 2.3 环境变量覆盖

支持通过环境变量覆盖配置文件，便于容器化部署。

**示例**:
```bash
export NANOBOT__PROVIDERS__ANTHROPIC__API_KEY="sk-ant-..."
export NANOBOT__AGENTS__DEFAULTS__MODEL="anthropic/claude-sonnet-4-5"
```

---

## 3. 核心机制

### 3.1 配置加载流程

```
load_config()
    ├─ 读取配置文件（~/.nanobot/config.json）
    ├─ 解析 JSON
    ├─ 配置迁移（_migrate_config）
    ├─ 命名转换（convert_keys: camelCase → snake_case）
    └─ Pydantic 验证（Config.model_validate）
```

### 3.2 配置保存流程

```
save_config()
    ├─ 转换为字典（model_dump）
    ├─ 命名转换（convert_to_camel: snake_case → camelCase）
    └─ 写入 JSON 文件
```

### 3.3 提供商自动匹配

`_match_provider()` 方法根据模型名称自动选择对应的提供商配置。

**代码位置**: [schema.py:138-163](../../../nanobot/config/schema.py#L138-L163)

---

## 4. 关键接口

### 4.1 Config 数据模型

#### 主要配置节

```python
class Config(BaseSettings):
    agents: AgentsConfig              # Agent 配置
    channels: ChannelsConfig          # 渠道配置
    providers: ProvidersConfig        # 提供商配置
    gateway: GatewayConfig            # 网关配置
    tools: ToolsConfig                # 工具配置
    browser: BrowserConfig            # 浏览器配置
```

#### Agent 配置

```python
class AgentsConfig(BaseModel):
    defaults: AgentDefaults

class AgentDefaults(BaseModel):
    workspace: str = "~/.nanobot/workspace"
    model: str = "anthropic/claude-opus-4-5"
    max_tokens: int = 8192
    temperature: float = 0.7
    max_tool_iterations: int = 20
```

#### 渠道配置

```python
class ChannelsConfig(BaseModel):
    telegram: TelegramConfig
    discord: DiscordConfig
    feishu: FeishuConfig
    whatsapp: WhatsAppConfig
```

#### 提供商配置

```python
class ProvidersConfig(BaseModel):
    anthropic: ProviderConfig
    openai: ProviderConfig
    openrouter: ProviderConfig
    deepseek: ProviderConfig
    groq: ProviderConfig
    zhipu: ProviderConfig
    dashscope: ProviderConfig
    vllm: ProviderConfig
    gemini: ProviderConfig
    moonshot: ProviderConfig
```

#### 工具配置

```python
class ToolsConfig(BaseModel):
    web: WebToolsConfig
    exec: ExecToolConfig
    restrict_to_workspace: bool = False
```

#### 浏览器配置

```python
class BrowserConfig(BaseModel):
    enabled: bool = False
    headless: bool = True
    timeout: int = 30000
    profile_dir: str | None = None
    credentials_path: str | None = None
    allowed_domains: list[str] = []
    auto_login_domains: list[str] = []
```

### 4.2 配置加载函数

```python
def load_config(config_path: Path | None = None) -> Config:
    """从文件加载配置或创建默认配置"""

def save_config(config: Config, config_path: Path | None = None) -> None:
    """将配置保存到文件"""

def get_config_path() -> Path:
    """获取默认配置文件路径"""

def get_data_dir() -> Path:
    """获取 nanobot 数据目录"""
```

---

## 5. 使用示例

### 5.1 加载配置

```python
from pathlib import Path
from nanobot.config.loader import load_config

# 加载默认配置
config = load_config()

# 加载指定配置文件
config = load_config(Path("/path/to/config.json"))

# 访问配置
print(f"工作区: {config.workspace_path}")
print(f"模型: {config.agents.defaults.model}")
print(f"Telegram 启用: {config.channels.telegram.enabled}")
```

### 5.2 保存配置

```python
from nanobot.config.loader import save_config
from nanobot.config.schema import Config

# 修改配置
config.agents.defaults.model = "anthropic/claude-sonnet-4-5"
config.channels.telegram.enabled = True
config.channels.telegram.token = "your-bot-token"

# 保存配置
save_config(config)
```

### 5.3 获取 API Key

```python
# 自动匹配提供商
api_key = config.get_api_key("anthropic/claude-sonnet-4-5")

# 获取默认模型的 API Key
api_key = config.get_api_key()  # 使用默认模型

# 获取 API Base
api_base = config.get_api_base("openrouter/gpt-4")
```

### 5.4 环境变量覆盖

```bash
# 设置环境变量
export NANOBOT__PROVIDERS__ANTHROPIC__API_KEY="sk-ant-..."
export NANOBOT__CHANNELS__TELEGRAM__TOKEN="your-token"
export NANOBOT__TOOLS__RESTRICT_TO_WORKSPACE="true"

# 运行 nanobot（会自动读取环境变量）
nanobot gateway
```

### 5.5 完整配置文件示例

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-sonnet-4-5",
      "maxTokens": 8192,
      "temperature": 0.7,
      "maxToolIterations": 20
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-...",
      "apiBase": null
    },
    "openai": {
      "apiKey": "",
      "apiBase": null
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "your-telegram-bot-token",
      "allowFrom": ["*"],
      "proxy": null
    },
    "discord": {
      "enabled": false,
      "token": "",
      "allowFrom": [],
      "gatewayUrl": "wss://gateway.discord.gg/?v=10&encoding=json",
      "intents": 37377
    }
  },
  "tools": {
    "web": {
      "search": {
        "apiKey": "your-brave-api-key",
        "maxResults": 5
      }
    },
    "exec": {
      "timeout": 60
    },
    "restrictToWorkspace": false
  },
  "browser": {
    "enabled": false,
    "headless": true,
    "timeout": 30000,
    "profileDir": null,
    "credentialsPath": null,
    "allowedDomains": ["*.example.com"],
    "autoLoginDomains": []
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790
  }
}
```

---

## 6. 扩展指南

### 6.1 添加新的配置节

```python
# 在 schema.py 中添加
class MyFeatureConfig(BaseModel):
    enabled: bool = False
    setting1: str = "default"
    setting2: int = 100

class Config(BaseSettings):
    # ... 现有配置 ...
    my_feature: MyFeatureConfig = Field(default_factory=MyFeatureConfig)
```

### 6.2 添加配置验证

```python
from pydantic import field_validator

class AgentDefaults(BaseModel):
    model: str = "anthropic/claude-opus-4-5"
    max_tokens: int = 8192

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 100 or v > 100000:
            raise ValueError("max_tokens 必须在 100-100000 之间")
        return v
```

### 6.3 添加配置秘钥加密

```python
from cryptography.fernet import Fernet

class EncryptedConfig:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt_api_key(self, api_key: str) -> str:
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_api_key(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()

# 在保存配置时加密敏感字段
def save_config_encrypted(config: Config):
    encrypted_config = config.model_copy()
    # 加密 API keys
    for provider in encrypted_config.providers.__dict__.values():
        if provider.api_key:
            provider.api_key = encrypt(provider.api_key)
    # 保存...
```

### 6.4 添加配置文件热重载

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloadHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if event.src_path.endswith("config.json"):
            self.callback()

class HotReloadConfig:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.observer = Observer()

    def start_watching(self):
        handler = ConfigReloadHandler(self._reload)
        self.observer.schedule(handler, str(self.config_path.parent))
        self.observer.start()

    def _reload(self):
        print("配置文件已更改，重新加载...")
        self.config = load_config(self.config_path)

    def stop_watching(self):
        self.observer.stop()
```

### 6.5 添加配置文件继承

```python
class HierarchicalConfig:
    def load_config_with_base(self, config_path: Path, base_path: Path = None) -> Config:
        """支持继承基础配置"""
        # 加载基础配置
        if base_path and base_path.exists():
            base_data = json.loads(base_path.read_text())
        else:
            base_data = {}

        # 加载用户配置
        if config_path.exists():
            user_data = json.loads(config_path.read_text())
        else:
            user_data = {}

        # 合并配置（用户配置覆盖基础配置）
        merged_data = {**base_data, **user_data}

        # 转换并验证
        return Config.model_validate(convert_keys(merged_data))
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/config/schema.py](../../../nanobot/config/schema.py) - 配置模型（197 行）
- [nanobot/config/loader.py](../../../nanobot/config/loader.py) - 配置加载器（107 行）

### 依赖模块

- 所有模块都依赖配置系统

### 相关文档

- [LLM 提供商模块文档](llm-provider.md)
- [渠道管理器模块文档](channel-manager.md)
- [浏览器自动化模块文档](browser-automation.md)

## 配置文件位置

```
~/.nanobot/
└── config.json  # 主配置文件
```

## 环境变量

```
NANOBOT__PROVIDERS__<PROVIDER>__API_KEY
NANOBOT__PROVIDERS__<PROVIDER>__API_BASE
NANOBOT__AGENTS__DEFAULTS__MODEL
NANOBOT__CHANNELS__<CHANNEL>__ENABLED
NANOBOT__TOOLS__RESTRICT_TO_WORKSPACE
NANOBOT__BROWSER__ENABLED
...
```

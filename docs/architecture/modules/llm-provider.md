# LLM 提供商模块

> **文件位置**: [nanobot/providers/litellm_provider.py](../../../nanobot/providers/litellm_provider.py)
> **行数**: 约 204 行
> **最后更新**: 2026-02-10

---

## 1. 概述

LLM 提供商模块（`LiteLLMProvider`）是 nanobot 框架与大语言模型通信的统一抽象层，通过 LiteLLM 库支持多家 LLM 提供商。

### 核心职责

- **统一接口**: 为多个 LLM 提供商提供一致的调用接口
- **提供商检测**: 根据模型名称自动识别并配置提供商
- **工具调用**: 支持 OpenAI 格式的函数调用（Function Calling）
- **错误处理**: 优雅处理 LLM 调用失败

### 支持的提供商

| 提供商 | 模型前缀 | 说明 |
|--------|----------|------|
| **OpenRouter** | `openrouter/` | 聚合多家，推荐使用 |
| **Anthropic** | `anthropic/` | Claude 系列 |
| **OpenAI** | `openai/` | GPT 系列 |
| **DeepSeek** | `deepseek/` | 深度求索 |
| **Gemini** | `gemini/` | Google 模型 |
| **智谱/Z.ai** | `zai/`, `zhipu/` | GLM 系列 |
| **DashScope** | `dashscope/` | 阿里云通义千问 |
| **Moonshot** | `moonshot/` | 月之暗面 Kimi |
| **Groq** | `groq/` | Groq 快速推理 |
| **vLLM** | `hosted_vllm/` | 本地模型 |

### 相关模块

- [Agent 循环](agent-loop.md) - LLM 提供商的主要使用者
- [配置系统](config-system.md) - 提供商配置管理

---

## 2. 设计理念

### 2.1 统一抽象

通过 LiteLLM 库实现统一的 LLM 接口，让 Agent 可以灵活切换模型而无需修改业务逻辑。

**好处**:
- **供应商无关**: 不被单一供应商锁定
- **成本优化**: 可以根据任务类型选择不同成本的模型
- **冗余备份**: 主提供商故障时可以快速切换
- **本地部署**: 支持私有化部署（vLLM）

### 2.2 智能提供商检测

根据模型名称和 API Key 自动推断提供商类型，减少配置复杂度。

**代码位置**: [litellm_provider.py:28-42](../../../nanobot/providers/litellm_provider.py#L28-L42)

```python
# 首先从模型名称检测提供商类型
self.is_zhipu = "zhipu" in default_model or "zhipuai" in default_model or "glm" in default_model or "zai" in default_model
self.is_anthropic = "anthropic" in default_model
self.is_openai = "openai" in default_model or "gpt" in default_model
self.is_gemini = "gemini" in default_model.lower()
self.is_groq = "groq" in default_model

# 通过 api_key 前缀或明确的 api_base 检测 OpenRouter
self.is_openrouter = (
    (api_key and api_key.startswith("sk-or-")) or
    (api_base and "openrouter" in api_base)
)

# 追踪是否使用自定义端点（vLLM 等）
self.is_vllm = bool(api_base) and not self.is_openrouter and not self.is_zhipu
```

### 2.3 模型前缀自动补全

自动为模型名称添加正确的提供商前缀，简化配置。

**代码位置**: [litellm_provider.py:99-133](../../../nanobot/providers/litellm_provider.py#L99-L133)

```python
# 对于 OpenRouter，如果尚未添加前缀则添加
if self.is_openrouter and not model.startswith("openrouter/"):
    model = f"openrouter/{model}"

# 对于智谱/Z.ai，确保前缀存在
if ("glm" in model.lower() or "zhipu" in model.lower()) and not (
    model.startswith("zhipu/") or
    model.startswith("zai/") or
    model.startswith("openrouter/")
):
    model = f"zai/{model}"

# 对于 vLLM，根据 LiteLLM 文档使用 hosted_vllm/ 前缀
if self.is_vllm:
    model = f"hosted_vllm/{model}"
```

---

## 3. 核心机制

### 3.1 LLM 调用流程

```
用户请求
    ↓
AgentLoop 调用 provider.chat()
    ↓
LiteLLMProvider.chat()
    ├─ 1. 检测模型类型并补全前缀
    ├─ 2. 构建请求参数
    ├─ 3. 调用 LiteLLM acompletion()
    └─ 4. 解析响应
        ├─ 提取文本内容
        ├─ 解析工具调用
        └─ 提取 token 使用情况
    ↓
返回 LLMResponse
```

### 3.2 工具调用支持

LiteLLM 完全支持 OpenAI 格式的函数调用。

**代码位置**: [litellm_provider.py:149-151](../../../nanobot/providers/litellm_provider.py#L149-L151)

```python
if tools:
    kwargs["tools"] = tools
    kwargs["tool_choice"] = "auto"
```

### 3.3 错误处理

LLM 调用失败时返回错误消息而不是抛出异常，保证系统稳定性。

**代码位置**: [litellm_provider.py:156-161](../../../nanobot/providers/litellm_provider.py#L156-L161)

```python
try:
    response = await acompletion(**kwargs)
    return self._parse_response(response)
except Exception as e:
    # 将错误作为内容返回以实现优雅处理
    return LLMResponse(
        content=f"Error calling LLM: {str(e)}",
        finish_reason="error",
    )
```

---

## 4. 关键接口

### 4.1 构造函数

```python
def __init__(
    self,
    api_key: str | None = None,
    api_base: str | None = None,
    default_model: str = "anthropic/claude-opus-4-5"
)
```

**参数说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | `str \| None` | `None` | API 密钥，可选 |
| `api_base` | `str \| None` | `None` | 自定义 API 基础 URL（用于 vLLM 等） |
| `default_model` | `str` | `"anthropic/claude-opus-4-5"` | 默认模型名称 |

**自动检测逻辑**:
- OpenRouter: API Key 以 `sk-or-` 开头
- 智谱: 模型名包含 `glm`、`zhipu` 或 `zai`
- Anthropic: 模型名包含 `anthropic` 或 `claude`
- OpenAI: 模型名包含 `openai` 或 `gpt`
- vLLM: 提供了 `api_base` 且不是 OpenRouter/智谱

### 4.2 核心方法

#### `async def chat(...) -> LLMResponse`

发送聊天完成请求。

**代码位置**: [litellm_provider.py:76-161](../../../nanobot/providers/litellm_provider.py#L76-L161)

**签名**:
```python
async def chat(
    self,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> LLMResponse
```

**参数说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `messages` | `list[dict]` | 必填 | 消息历史，格式 `[{"role": "...", "content": "..."}]` |
| `tools` | `list[dict] \| None` | `None` | OpenAI 格式的工具定义 |
| `model` | `str \| None` | `None` | 模型名称，`None` 时使用默认模型 |
| `max_tokens` | `int` | `4096` | 响应最大 token 数 |
| `temperature` | `float` | `0.7` | 采样温度 |

**返回**: `LLMResponse` 对象

#### `def _parse_response(self, response: Any) -> LLMResponse`

将 LiteLLM 响应解析为标准格式。

**代码位置**: [litellm_provider.py:163-199](../../../nanobot/providers/litellm_provider.py#L163-L199)

#### `def get_default_model(self) -> str`

获取默认模型名称。

**代码位置**: [litellm_provider.py:201-203](../../../nanobot/providers/litellm_provider.py#L201-L203)

---

## 5. 使用示例

### 5.1 基础使用

```python
import asyncio
from nanobot.providers.litellm_provider import LiteLLMProvider

async def main():
    # 使用 Anthropic Claude
    provider = LiteLLMProvider(
        api_key="sk-ant-...",
        default_model="anthropic/claude-sonnet-4-5"
    )

    messages = [
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ]

    response = await provider.chat(messages)
    print(response.content)
    # 输出: 你好！我是 Claude，一个由 Anthropic 开发的 AI 助手...

asyncio.run(main())
```

### 5.2 使用工具调用

```python
import asyncio
from nanobot.providers.litellm_provider import LiteLLMProvider

async def main():
    provider = LiteLLMProvider(
        api_key="sk-or-...",  # OpenRouter key
        default_model="openrouter/anthropic/claude-sonnet-4-5"
    )

    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    }]

    messages = [
        {"role": "user", "content": "北京今天天气怎么样？"}
    ]

    response = await provider.chat(messages, tools=tools)

    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            print(f"工具调用: {tool_call.name}")
            print(f"参数: {tool_call.arguments}")
    else:
        print(response.content)

asyncio.run(main())
```

### 5.3 使用本地 vLLM

```python
provider = LiteLLMProvider(
    api_key="dummy",  # vLLM 可能不需要真实 key
    api_base="http://localhost:8000/v1",
    default_model="Qwen/Qwen2.5-7B-Instruct"
)
```

### 5.4 切换提供商

```python
# 使用 Anthropic
anthropic_provider = LiteLLMProvider(api_key="sk-ant-...")

# 切换到 OpenAI（只需更改配置）
openai_provider = LiteLLMProvider(
    api_key="sk-openai-...",
    default_model="openai/gpt-4o"
)

# 切换到本地模型
local_provider = LiteLLMProvider(
    api_base="http://localhost:8000/v1",
    default_model="hosted_vllm/llama-3-8b"
)
```

### 5.5 处理多轮对话

```python
async def chat_loop(provider: LiteLLMProvider):
    messages = []

    while True:
        user_input = input("You: ")
        messages.append({"role": "user", "content": user_input})

        response = await provider.chat(messages)
        messages.append({"role": "assistant", "content": response.content})

        print(f"Assistant: {response.content}")
```

---

## 6. 扩展指南

### 6.1 添加新的提供商支持

LiteLLM 已支持 100+ 提供商。如果需要特殊处理，可以扩展 `LiteLLMProvider`：

```python
class CustomLiteLLMProvider(LiteLLMProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加新的提供商检测
        self.is_custom = "custom" in self.default_model

    async def chat(self, messages, tools=None, model=None, **kwargs):
        model = model or self.default_model

        # 自定义模型前缀处理
        if self.is_custom and not model.startswith("custom/"):
            model = f"custom/{model}"

        return await super().chat(messages, tools, model, **kwargs)
```

### 6.2 自定义错误处理

```python
class RobustLLMProvider(LiteLLMProvider):
    async def chat(self, *args, **kwargs):
        try:
            return await super().chat(*args, **kwargs)
        except Exception as e:
            # 实现重试逻辑
            for attempt in range(3):
                await asyncio.sleep(2 ** attempt)  # 指数退避
                try:
                    return await super().chat(*args, **kwargs)
                except Exception:
                    continue
            # 最终失败
            return LLMResponse(
                content=f"LLM 服务暂时不可用，请稍后重试",
                finish_reason="error"
            )
```

### 6.3 添加响应缓存

```python
from functools import lru_cache
import hashlib
import json

class CachedLLMProvider(LiteLLMProvider):
    def __init__(self, *args, cache=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = cache or {}

    async def chat(self, messages, tools=None, **kwargs):
        # 生成缓存键
        cache_key = hashlib.md5(
            json.dumps({"messages": messages, "tools": tools}).encode()
        ).hexdigest()

        if cache_key in self._cache:
            return self._cache[cache_key]

        response = await super().chat(messages, tools, **kwargs)
        self._cache[cache_key] = response
        return response
```

### 6.4 实现请求/响应日志

```python
class LoggingLLMProvider(LiteLLMProvider):
    async def chat(self, messages, tools=None, **kwargs):
        # 记录请求
        logger.info(f"LLM Request: {len(messages)} messages, tools={bool(tools)}")

        response = await super().chat(messages, tools, **kwargs)

        # 记录响应
        logger.info(
            f"LLM Response: {len(response.content)} chars, "
            f"{len(response.tool_calls)} tool calls, "
            f"tokens={response.usage.get('total_tokens', 'N/A')}"
        )

        return response
```

### 6.5 实现多提供商负载均衡

```python
class LoadBalancedProvider:
    def __init__(self, providers: list[LiteLLMProvider]):
        self.providers = providers
        self._current = 0

    async def chat(self, *args, **kwargs):
        # 轮询选择提供商
        provider = self.providers[self._current]
        self._current = (self._current + 1) % len(self.providers)

        try:
            return await provider.chat(*args, **kwargs)
        except Exception as e:
            # 失败时尝试下一个提供商
            logger.warning(f"Provider {self._current} failed: {e}")
            next_provider = self.providers[(self._current + 1) % len(self.providers)]
            return await next_provider.chat(*args, **kwargs)

# 使用示例
providers = [
    LiteLLMProvider(api_key="key1", default_model="provider1/model"),
    LiteLLMProvider(api_key="key2", default_model="provider2/model"),
]
load_balanced = LoadBalancedProvider(providers)
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/providers/litellm_provider.py](../../../nanobot/providers/litellm_provider.py) - LiteLLM 提供商实现（204 行）
- [nanobot/providers/base.py](../../../nanobot/providers/base.py) - 提供商基类和数据模型

### 依赖模块

- [nanobot/agent/loop.py](../../../nanobot/agent/loop.py) - 主要使用者
- [nanobot/config/schema.py](../../../nanobot/config/schema.py) - 配置模型

### 相关文档

- [Agent 循环模块文档](agent-loop.md)
- [配置系统模块文档](config-system.md)

## 外部依赖

- **LiteLLM**: [https://github.com/BerriAI/litellm](https://github.com/BerriAI/litellm) - 统一多家 LLM 提供商的 Python 库

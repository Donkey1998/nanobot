"""LiteLLM 提供商实现，支持多提供商接入。"""

import os
from typing import Any

import litellm
from litellm import acompletion

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class LiteLLMProvider(LLMProvider):
    """
    使用 LiteLLM 的 LLM 提供商，支持多提供商接入。

    通过统一接口支持 OpenRouter、Anthropic、OpenAI、Gemini 以及许多其他提供商。
    """
    
    def __init__(
        self, 
        api_key: str | None = None, 
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5"
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        
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

        # 追踪是否使用自定义端点（vLLM 等）- 排除已知提供商
        self.is_vllm = bool(api_base) and not self.is_openrouter and not self.is_zhipu

        # 根据提供商配置 LiteLLM
        if api_key:
            if self.is_openrouter:
                # OpenRouter 模式 - 设置密钥
                os.environ["OPENROUTER_API_KEY"] = api_key
            elif self.is_vllm:
                # vLLM/自定义端点 - 使用 OpenAI 兼容 API
                os.environ["HOSTED_VLLM_API_KEY"] = api_key
            elif "deepseek" in default_model:
                os.environ.setdefault("DEEPSEEK_API_KEY", api_key)
            elif "anthropic" in default_model:
                os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
            elif "openai" in default_model or "gpt" in default_model:
                os.environ.setdefault("OPENAI_API_KEY", api_key)
            elif "gemini" in default_model.lower():
                os.environ.setdefault("GEMINI_API_KEY", api_key)
            elif "zhipu" in default_model or "glm" in default_model or "zai" in default_model:
                os.environ.setdefault("ZAI_API_KEY", api_key)
            elif "dashscope" in default_model or "qwen" in default_model.lower():
                os.environ.setdefault("DASHSCOPE_API_KEY", api_key)
            elif "groq" in default_model:
                os.environ.setdefault("GROQ_API_KEY", api_key)
            elif "moonshot" in default_model or "kimi" in default_model:
                os.environ.setdefault("MOONSHOT_API_KEY", api_key)
                os.environ.setdefault("MOONSHOT_API_BASE", api_base or "https://api.moonshot.cn/v1")
        
        if api_base:
            litellm.api_base = api_base
        
        # 禁用 LiteLLM 的日志噪音
        litellm.suppress_debug_info = True
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        通过 LiteLLM 发送聊天完成请求。

        Args:
            messages: 包含 'role' 和 'content' 的消息字典列表。
            tools: 可选的工具定义列表，使用 OpenAI 格式。
            model: 模型标识符（例如 'anthropic/claude-sonnet-4-5'）。
            max_tokens: 响应中的最大令牌数。
            temperature: 采样温度。

        Returns:
            包含内容和/或工具调用的 LLMResponse。
        """
        model = model or self.default_model

        # 对于 OpenRouter，如果尚未添加前缀则添加
        if self.is_openrouter and not model.startswith("openrouter/"):
            model = f"openrouter/{model}"

        # 对于智谱/Z.ai，确保前缀存在
        # 处理如 "glm-4.7-flash" -> "zai/glm-4.7-flash" 的情况
        if ("glm" in model.lower() or "zhipu" in model.lower()) and not (
            model.startswith("zhipu/") or
            model.startswith("zai/") or
            model.startswith("openrouter/")
        ):
            model = f"zai/{model}"

        # 对于 DashScope/Qwen，确保 dashscope/ 前缀
        if ("qwen" in model.lower() or "dashscope" in model.lower()) and not (
            model.startswith("dashscope/") or
            model.startswith("openrouter/")
        ):
            model = f"dashscope/{model}"

        # 对于 Moonshot/Kimi，确保 moonshot/ 前缀（在 vLLM 检查之前）
        if ("moonshot" in model.lower() or "kimi" in model.lower()) and not (
            model.startswith("moonshot/") or model.startswith("openrouter/")
        ):
            model = f"moonshot/{model}"

        # 对于 Gemini，确保 gemini/ 前缀存在
        if "gemini" in model.lower() and not model.startswith("gemini/"):
            model = f"gemini/{model}"

        # 对于 vLLM，根据 LiteLLM 文档使用 hosted_vllm/ 前缀
        # 如果用户指定了 openai/ 前缀，则转换为 hosted_vllm/
        if self.is_vllm:
            model = f"hosted_vllm/{model}"

        # kimi-k2.5 只支持 temperature=1.0
        if "kimi-k2.5" in model.lower():
            temperature = 1.0

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # 对于自定义端点（vLLM 等），直接传递 api_base
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = await acompletion(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            # 将错误作为内容返回以实现优雅处理
            return LLMResponse(
                content=f"Error calling LLM: {str(e)}",
                finish_reason="error",
            )
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """将 LiteLLM 响应解析为我们的标准格式。"""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                # 如果需要，从 JSON 字符串解析参数
                args = tc.function.arguments
                if isinstance(args, str):
                    import json
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )
    
    def get_default_model(self) -> str:
        """获取默认模型。"""
        return self.default_model

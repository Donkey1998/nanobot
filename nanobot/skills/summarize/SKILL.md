---
name: summarize
description: 摘要或提取来自 URL、播客和本地文件的文本/转录（"转录此 YouTube/视频"的很好备选方案）。
homepage: https://summarize.sh
metadata: {"nanobot":{"emoji":"🧾","requires":{"bins":["summarize"]},"install":[{"id":"brew","kind":"brew","formula":"steipete/tap/summarize","bins":["summarize"],"label":"安装 summarize (brew)"}]}}
---

# 摘要

用于摘要 URL、本地文件和 YouTube 链接的快速 CLI。

## 何时使用（触发短语）

当用户要求以下任何内容时立即使用此技能：
- "使用 summarize.sh"
- "这个链接/视频是关于什么的？"
- "摘要此 URL/文章"
- "转录此 YouTube/视频"（尽力而为的转录提取；不需要 `yt-dlp`）

## 快速开始

```bash
summarize "https://example.com" --model google/gemini-3-flash-preview
summarize "/path/to/file.pdf" --model google/gemini-3-flash-preview
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto
```

## YouTube：摘要与转录

尽力而为的转录（仅限 URL）：

```bash
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto --extract-only
```

如果用户要求转录但它很大，首先返回紧凑的摘要，然后询问要扩展哪个部分/时间范围。

## 模型和密钥

为你选择的提供商设置 API 密钥：
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- xAI: `XAI_API_KEY`
- Google: `GEMINI_API_KEY`（别名：`GOOGLE_GENERATIVE_AI_API_KEY`、`GOOGLE_API_KEY`）

如果未设置，默认模型为 `google/gemini-3-flash-preview`。

## 有用的标志

- `--length short|medium|long|xl|xxl|<chars>`
- `--max-output-tokens <count>`
- `--extract-only`（仅限 URL）
- `--json`（机器可读）
- `--firecrawl auto|off|always`（备选提取）
- `--youtube auto`（如果设置了 `APIFY_API_TOKEN`，则使用 Apify 备选方案）

## 配置

可选配置文件：`~/.summarize/config.json`

```json
{ "model": "openai/gpt-5.2" }
```

可选服务：
- `FIRECRAWL_API_KEY` 用于被阻止的站点
- `APIFY_API_TOKEN` 用于 YouTube 备选方案

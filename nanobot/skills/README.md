# nanobot 技能

此目录包含扩展 nanobot 功能的内置技能。

## 技能格式

每个技能都是一个包含 `SKILL.md` 文件的目录，其中包含：
- YAML 前言（名称、描述、元数据）
- Agent 的 Markdown 指令

## 归属

这些技能改编自 [OpenClaw](https://github.com/openclaw/openclaw) 的技能系统。
技能格式和元数据结构遵循 OpenClaw 的约定以保持兼容性。

## 可用技能

| 技能 | 描述 |
|-------|-------------|
| `github` | 使用 `gh` CLI 与 GitHub 交互 |
| `weather` | 使用 wttr.in 和 Open-Meteo 获取天气信息 |
| `summarize` | 摘要 URL、文件和 YouTube 视频 |
| `tmux` | 远程控制 tmux 会话 |
| `skill-creator` | 创建新技能 |

"""Shell 执行工具。"""

import asyncio
import os
from typing import Any

from nanobot.agent.tools.base import Tool


class ExecTool(Tool):
    """执行 Shell 命令的工具。"""
    
    def __init__(self, timeout: int = 60, working_dir: str | None = None):
        self.timeout = timeout
        self.working_dir = working_dir
    
    @property
    def name(self) -> str:
        return "exec"
    
    @property
    def description(self) -> str:
        return "执行 Shell 命令并返回其输出。请谨慎使用。"
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Shell 命令"
                },
                "working_dir": {
                    "type": "string",
                    "description": "命令的可选工作目录"
                }
            },
            "required": ["command"]
        }
    
    async def execute(self, command: str, working_dir: str | None = None, **kwargs: Any) -> str:
        cwd = working_dir or self.working_dir or os.getcwd()
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"错误：命令在 {self.timeout} 秒后超时"
            
            output_parts = []
            
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"标准错误输出：\n{stderr_text}")
            
            if process.returncode != 0:
                output_parts.append(f"\n退出代码：{process.returncode}")
            
            result = "\n".join(output_parts) if output_parts else "（无输出）"
            
            # Truncate very long output
            max_len = 10000
            if len(result) > max_len:
                result = result[:max_len] + f"\n...（已截断，还有 {len(result) - max_len} 个字符）"
            
            return result
            
        except Exception as e:
            return f"执行命令错误：{str(e)}"

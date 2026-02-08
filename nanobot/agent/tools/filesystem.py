"""文件系统工具：读取、写入、编辑。"""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


def _resolve_path(path: str, allowed_dir: Path | None = None) -> Path:
    """Resolve path and optionally enforce directory restriction."""
    resolved = Path(path).expanduser().resolve()
    if allowed_dir and not str(resolved).startswith(str(allowed_dir.resolve())):
        raise PermissionError(f"Path {path} is outside allowed directory {allowed_dir}")
    return resolved


class ReadFileTool(Tool):
    """读取文件内容的工具。"""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "读取给定路径的文件内容。"
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径"
                }
            },
            "required": ["path"]
        }
    
    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"错误：找不到文件：{path}"
            if not file_path.is_file():
                return f"错误：不是文件：{path}"
            
            content = file_path.read_text(encoding="utf-8")
            return content
<<<<<<< HEAD
        except PermissionError as e:
            return f"错误：权限被拒绝：{e}"
        except Exception as e:
            return f"读取文件错误：{str(e)}"


class WriteFileTool(Tool):
    """写入内容到文件的工具。"""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "将内容写入到给定路径的文件。如需要会创建父目录。"
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                }
            },
            "required": ["path", "content"]
        }
    
    async def execute(self, path: str, content: str, **kwargs: Any) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
<<<<<<< HEAD
            return f"成功写入 {len(content)} 字节到 {path}"
        except PermissionError:
            return f"错误：权限被拒绝：{path}"
=======
            return f"Successfully wrote {len(content)} bytes to {path}"
        except PermissionError as e:
            return f"Error: {e}"
>>>>>>> main
        except Exception as e:
            return f"写入文件错误：{str(e)}"


class EditFileTool(Tool):
    """通过替换文本来编辑文件的工具。"""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "edit_file"
    
    @property
    def description(self) -> str:
        return "通过用 new_text 替换 old_text 来编辑文件。old_text 必须完全存在于文件中。"
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要编辑的文件路径"
                },
                "old_text": {
                    "type": "string",
                    "description": "要查找和替换的精确文本"
                },
                "new_text": {
                    "type": "string",
                    "description": "替换后的文本"
                }
            },
            "required": ["path", "old_text", "new_text"]
        }
    
    async def execute(self, path: str, old_text: str, new_text: str, **kwargs: Any) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"错误：找不到文件：{path}"
            
            content = file_path.read_text(encoding="utf-8")
            
            if old_text not in content:
                return f"错误：在文件中找不到 old_text。请确保完全匹配。"
            
            # Count occurrences
            count = content.count(old_text)
            if count > 1:
                return f"警告：old_text 出现了 {count} 次。请提供更多上下文使其唯一。"
            
            new_content = content.replace(old_text, new_text, 1)
            file_path.write_text(new_content, encoding="utf-8")
            
<<<<<<< HEAD
            return f"成功编辑 {path}"
        except PermissionError:
            return f"错误：权限被拒绝：{path}"
=======
            return f"Successfully edited {path}"
        except PermissionError as e:
            return f"Error: {e}"
>>>>>>> main
        except Exception as e:
            return f"编辑文件错误：{str(e)}"


class ListDirTool(Tool):
    """列出目录内容的工具。"""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "list_dir"
    
    @property
    def description(self) -> str:
        return "列出目录的内容。"
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要列出的目录路径"
                }
            },
            "required": ["path"]
        }
    
    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            dir_path = _resolve_path(path, self._allowed_dir)
            if not dir_path.exists():
                return f"错误：找不到目录：{path}"
            if not dir_path.is_dir():
                return f"错误：不是目录：{path}"
            
            items = []
            for item in sorted(dir_path.iterdir()):
                prefix = "📁 " if item.is_dir() else "📄 "
                items.append(f"{prefix}{item.name}")
            
            if not items:
                return f"目录 {path} 为空"
            
            return "\n".join(items)
<<<<<<< HEAD
        except PermissionError as e:
            return f"错误：权限被拒绝：{e}"
        except Exception as e:
            return f"列出目录错误：{str(e)}"

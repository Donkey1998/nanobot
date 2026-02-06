"""配置加载工具。"""

import json
from pathlib import Path
from typing import Any

from nanobot.config.schema import Config


def get_config_path() -> Path:
    """获取默认配置文件路径。"""
    return Path.home() / ".nanobot" / "config.json"


def get_data_dir() -> Path:
    """获取 nanobot 数据目录。"""
    from nanobot.utils.helpers import get_data_path
    return get_data_path()


def load_config(config_path: Path | None = None) -> Config:
    """
    从文件加载配置或创建默认配置。

    Args:
        config_path: 可选的配置文件路径。如未提供则使用默认路径。

    Returns:
        加载的配置对象。
    """
    path = config_path or get_config_path()
    
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            return Config.model_validate(convert_keys(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            print("使用默认配置。")
    
    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    将配置保存到文件。

    Args:
        config: 要保存的配置。
        config_path: 可选的保存路径。如未提供则使用默认路径。
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 转换为 camelCase 格式
    data = config.model_dump()
    data = convert_to_camel(data)
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def convert_keys(data: Any) -> Any:
    """将 camelCase 键转换为 snake_case 以用于 Pydantic。"""
    if isinstance(data, dict):
        return {camel_to_snake(k): convert_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_keys(item) for item in data]
    return data


def convert_to_camel(data: Any) -> Any:
    """将 snake_case 键转换为 camelCase。"""
    if isinstance(data, dict):
        return {snake_to_camel(k): convert_to_camel(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_camel(item) for item in data]
    return data


def camel_to_snake(name: str) -> str:
    """将 camelCase 转换为 snake_case。"""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def snake_to_camel(name: str) -> str:
    """将 snake_case 转换为 camelCase。"""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

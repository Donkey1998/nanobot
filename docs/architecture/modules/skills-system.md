# 技能系统模块

> **文件位置**: [nanobot/agent/skills.py](../../../nanobot/agent/skills.py)
> **行数**: 约 229 行
> **最后更新**: 2026-02-10

---

## 1. 概述

技能系统模块负责动态加载和管理 Agent 的技能（Skills），支持渐进式加载策略以优化 Token 使用。

### 核心职责

- **技能加载**: 从工作区或内置目录加载技能
- **元数据解析**: 解析 YAML frontmatter 中的技能元数据
- **需求检查**: 验证技能依赖（CLI 工具、环境变量）
- **渐进式加载**: 区分总是加载和按需加载的技能
- **摘要生成**: 生成技能的 XML 摘要供 LLM 浏览

### 技能来源优先级

```
工作区技能 (workspace/skills/{name}/SKILL.md)
    ↓ 未找到
内置技能 (nanobot/skills/{name}/SKILL.md)
```

### 相关模块

- [上下文构建器](context-builder.md) - 使用技能构建系统提示

---

## 2. 设计理念

### 2.1 渐进式加载策略

**问题**: 将所有技能完整加载到上下文会造成 Token 浪费。

**解决方案**:
- **always=true 技能**: 完整加载到上下文
- **其他技能**: 仅显示 XML 摘要，LLM 使用 `read_file` 工具按需加载

### 2.2 工作区优先

工作区中的技能会覆盖内置技能，允许用户自定义技能而无需修改代码。

### 2.3 依赖检查

在列出技能时自动检查依赖是否满足，标记不可用的技能。

---

## 3. 核心机制

### 3.1 技能元数据

技能使用 YAML frontmatter 存储元数据：

```yaml
---
description: "Python 开发技能"
requires:
  bins: ["python", "pip"]
  env: ["PYTHONPATH"]
always: true
---
```

**支持的元数据**:
- `description`: 技能描述
- `requires.bins`: 需要的 CLI 工具
- `requires.env`: 需要的环境变量
- `always`: 是否总是加载（true/false）

### 3.2 技能加载流程

```
SkillsLoader.list_skills()
    ├─ 扫描工作区技能目录
    ├─ 扫描内置技能目录
    ├─ 过滤重复（工作区优先）
    └─ 按要求过滤（可选）

load_skill(name)
    ├─ 尝试从工作区加载
    └─ 回退到内置技能

get_skill_metadata(name)
    └─ 解析 YAML frontmatter
```

### 3.3 技能摘要生成

`build_skills_summary()` 生成 XML 格式的技能摘要。

**代码位置**: [skills.py:101-140](../../../nanobot/agent/skills.py#L101-L140)

**格式**:
```xml
<skills>
  <skill available="true">
    <name>python</name>
    <description>Python 开发技能</description>
    <location>/workspace/skills/python/SKILL.md</location>
  </skill>
  <skill available="false">
    <name>docker</name>
    <description>Docker 容器管理</description>
    <location>/workspace/skills/docker/SKILL.md</location>
    <requires>CLI: docker</requires>
  </skill>
</skills>
```

---

## 4. 关键接口

### 4.1 SkillsLoader

#### 构造函数

```python
def __init__(
    self,
    workspace: Path,
    builtin_skills_dir: Path | None = None
):
    self.workspace = workspace
    self.workspace_skills = workspace / "skills"
    self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR
```

#### 方法

```python
def list_skills(self, filter_unavailable: bool = True) -> list[dict[str, str]]:
    """列出所有可用的技能"""

def load_skill(self, name: str) -> str | None:
    """按名称加载技能"""

def load_skills_for_context(self, skill_names: list[str]) -> str:
    """加载特定技能以包含在 Agent 上下文中"""

def build_skills_summary(self) -> str:
    """构建所有技能的 XML 摘要"""

def get_always_skills(self) -> list[str]:
    """获取标记为 always=true 且满足要求的技能"""

def get_skill_metadata(self, name: str) -> dict | None:
    """从技能的前置元数据中获取元数据"""
```

---

## 5. 使用示例

### 5.1 列出所有技能

```python
from pathlib import Path
from nanobot.agent.skills import SkillsLoader

workspace = Path("~/.nanobot/workspace").expanduser()
loader = SkillsLoader(workspace)

# 列出所有可用技能
skills = loader.list_skills(filter_unavailable=True)

for skill in skills:
    print(f"名称: {skill['name']}")
    print(f"路径: {skill['path']}")
    print(f"来源: {skill['source']}")
    print()
```

### 5.2 加载技能内容

```python
# 加载技能内容
content = loader.load_skill("python")

if content:
    print(content)
else:
    print("技能不存在")
```

### 5.3 获取技能元数据

```python
metadata = loader.get_skill_metadata("python")

print(f"描述: {metadata.get('description')}")
print(f"总是加载: {metadata.get('always')}")
print(f"需要: {metadata.get('requires')}")
```

### 5.4 创建自定义技能

在工作区创建技能：

```
~/.nanobot/workspace/skills/my-skill/
└── SKILL.md
```

**SKILL.md 内容**:
```markdown
---
description: "我的自定义技能"
requires:
  bins: ["git"]
  env: []
always: false
---

# 我的自定义技能

这是一个自定义技能，用于...

## 使用方法

1. 步骤一
2. 步骤二

## 注意事项

- 注意事项一
- 注意事项二
```

### 5.5 检查技能依赖

```python
# 获取技能元数据
metadata = loader.get_skill_metadata("my-skill")

# 检查依赖
skill_meta = loader._parse_nanobot_metadata(metadata.get("metadata", ""))
is_available = loader._check_requirements(skill_meta)

if not is_available:
    missing = loader._get_missing_requirements(skill_meta)
    print(f"技能不可用，缺少: {missing}")
```

---

## 6. 扩展指南

### 6.1 添加技能版本控制

```yaml
---
description: "Docker 管理技能"
version: "1.0.0"
requires:
  bins: ["docker"]
---
```

```python
class VersionedSkillsLoader(SkillsLoader):
    def get_skill_version(self, name: str) -> str | None:
        """获取技能版本"""
        metadata = self.get_skill_metadata(name) or {}
        return metadata.get("version")

    def list_outdated_skills(self) -> list[dict]:
        """列出过期的技能"""
        # 检查技能是否有更新版本
        pass
```

### 6.2 添加技能依赖安装

```python
class InstallableSkillsLoader(SkillsLoader):
    async def install_skill_dependencies(self, name: str) -> str:
        """安装技能依赖"""
        metadata = self.get_skill_metadata(name) or {}
        skill_meta = self._parse_nanobot_metadata(metadata.get("metadata", ""))
        requires = skill_meta.get("requires", {})

        install_commands = []

        # 安装 CLI 工具
        for bin_name in requires.get("bins", []):
            if not shutil.which(bin_name):
                install_commands.append(f"安装 {bin_name}")

        if install_commands:
            return f"需要安装: {', '.join(install_commands)}"

        return "所有依赖已满足"
```

### 6.3 添加技能搜索

```python
class SearchableSkillsLoader(SkillsLoader):
    def search_skills(self, query: str) -> list[dict]:
        """搜索技能"""
        results = []
        query_lower = query.lower()

        for skill in self.list_skills(filter_unavailable=False):
            # 搜索名称和描述
            name = skill["name"].lower()
            desc = self._get_skill_description(skill["name"]).lower()

            if query_lower in name or query_lower in desc:
                results.append(skill)

        return results
```

### 6.4 添加技能分类

```yaml
---
description: "Python 开发技能"
category: "programming"
tags: ["python", "development"]
---
```

```python
class CategorizedSkillsLoader(SkillsLoader):
    def get_skills_by_category(self, category: str) -> list[dict]:
        """按类别获取技能"""
        results = []

        for skill in self.list_skills(filter_unavailable=False):
            metadata = self.get_skill_metadata(skill["name"]) or {}
            if metadata.get("category") == category:
                results.append(skill)

        return results

    def list_categories(self) -> list[str]:
        """列出所有类别"""
        categories = set()

        for skill in self.list_skills(filter_unavailable=False):
            metadata = self.get_skill_metadata(skill["name"]) or {}
            if metadata.get("category"):
                categories.add(metadata["category"])

        return sorted(categories)
```

### 6.5 添加技能验证

```python
class ValidatingSkillsLoader(SkillsLoader):
    def validate_skill(self, name: str) -> dict:
        """验证技能文件"""
        content = self.load_skill(name)

        if not content:
            return {"valid": False, "errors": ["技能文件不存在"]}

        errors = []

        # 检查 YAML frontmatter
        if not content.startswith("---"):
            errors.append("缺少 YAML frontmatter")

        # 检查必需字段
        metadata = self.get_skill_metadata(name)
        if not metadata or not metadata.get("description"):
            errors.append("缺少 description 字段")

        # 检查内容
        body = self._strip_frontmatter(content)
        if len(body) < 50:
            errors.append("技能内容太短")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/agent/skills.py](../../../nanobot/agent/skills.py) - 技能加载器（229 行）

### 依赖模块

- [nanobot/agent/context.py](../../../nanobot/agent/context.py) - 使用技能构建上下文

### 相关文档

- [上下文构建器模块文档](context-builder.md)

## 技能目录结构

```
~/.nanobot/workspace/
└── skills/
    ├── my-skill/
    │   └── SKILL.md          # 工作区技能
    └── ...

nanobot/
└── skills/
    ├── python/
    │   └── SKILL.md          # 内置技能
    ├── docker/
    │   └── SKILL.md
    └── ...
```

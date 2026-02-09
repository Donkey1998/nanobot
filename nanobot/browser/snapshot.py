"""用于 LLM 消费的页面快照提取。"""

import asyncio
from typing import Any

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from nanobot.browser.session import BrowserTimeoutError


class PageSnapshot:
    """为 LLM 理解提取结构化页面快照。

    使用 Playwright 的可访问性树获取语义页面结构,
    包括交互元素的角色、标签和状态。

    示例:
        >>> snapshot = PageSnapshot(page)
        >>> tree = await snapshot.get_tree()
        >>> print(tree.to_text())
    """

    def __init__(self, page: Page, timeout: int = 30000) -> None:
        """初始化页面快照。

        Args:
            page: Playwright Page 对象
            timeout: 快照操作的超时时间(毫秒)
        """
        self.page = page
        self.timeout = timeout

    async def get_tree(self, wait_for_network_idle: bool = True) -> "AccessibilityNode":
        """获取当前页面的可访问性树。

        Args:
            wait_for_network_idle: 在快照之前等待网络空闲(用于动态内容)

        Returns:
            根 AccessibilityNode

        Raises:
            BrowserTimeoutError: 如果快照超时
        """
        # 等待动态内容
        if wait_for_network_idle:
            try:
                await self.page.wait_for_load_state("networkidle", timeout=self.timeout / 1000)
            except PlaywrightTimeoutError:
                # 无论如何继续 - 某些页面永远不会达到网络空闲
                pass

        # 获取可访问性树 - 使用 try/except 以确保兼容性
        try:
            # 首先尝试可访问性 API(如果可用)
            if hasattr(self.page, 'accessibility'):
                tree = await asyncio.wait_for(
                    self.page.accessibility.snapshot(),
                    timeout=self.timeout / 1000,
                )
            else:
                # 后备: 从页面内容创建简单树
                tree = await self._create_simple_tree()
        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError("Failed to get page snapshot within timeout") from exc
        except Exception:
            # 如果可访问性失败,创建简单树
            tree = await self._create_simple_tree()

        return AccessibilityNode.from_playwright(tree)

    async def _create_simple_tree(self) -> dict:
        """从页面内容创建简单的类似可访问性的树。"""
        try:
            # 获取页面标题和 URL
            title = await self.page.title()
            url = self.page.url

            # 获取所有文本内容
            text_content = await self.page.inner_text("body")

            return {
                "role": "WebArea",
                "name": title,
                "url": url,
                "children": [
                    {
                        "role": "text",
                        "name": text_content[:1000],  # 限制文本长度
                    }
                ]
            }
        except Exception:
            # 终极后备
            return {
                "role": "WebArea",
                "name": "Page",
            }

    async def get_text(self, wait_for_network_idle: bool = True) -> str:
        """获取页面的文本表示。

        Args:
            wait_for_network_idle: 在快照之前等待网络空闲

        Returns:
            页面的格式化文本表示
        """
        tree = await self.get_tree(wait_for_network_idle)
        return tree.to_text()

    async def get_interactive_elements(self, wait_for_network_idle: bool = True) -> list[dict[str, Any]]:
        """从页面获取所有交互元素。

        Args:
            wait_for_network_idle: 在快照之前等待网络空闲

        Returns:
            交互元素列表及其属性
        """
        tree = await self.get_tree(wait_for_network_idle)
        return tree.get_interactive_elements()


class AccessibilityNode:
    """可访问性树中的节点。"""

    def __init__(
        self,
        role: str,
        name: str = "",
        children: list["AccessibilityNode"] | None = None,
        **attributes: Any,
    ) -> None:
        """初始化可访问性节点。

        Args:
            role: ARIA 角色(例如 "button", "link", "textbox")
            name: 元素的可访问名称
            children: 子节点
            **attributes: 附加的可访问性属性
        """
        self.role = role
        self.name = name
        self.children = children or []
        self.attributes = attributes

    @classmethod
    def from_playwright(cls, data: dict[str, Any] | None) -> "AccessibilityNode":
        """从 Playwright 可访问性快照创建节点。

        Args:
            data: Playwright 可访问性快照数据

        Returns:
            AccessibilityNode
        """
        if data is None:
            return cls(role="root", name="Document")

        role = data.get("role", "unknown")
        name = data.get("name", "")

        # 过滤装饰性和隐藏元素
        ignored_roles = {"none", "presentation", "Generic"}
        if role in ignored_roles:
            # 检查子项是否有内容
            if "children" in data and data["children"]:
                # 返回第一个有意义的子项
                for child_data in data["children"]:
                    child = cls.from_playwright(child_data)
                    if child.role != "unknown":
                        return child
            return cls(role="ignored", name=name)

        # 提取有用的属性
        attributes = {}
        for key in ["checked", "expanded", "focused", "pressed", "selected", "disabled"]:
            if key in data:
                attributes[key] = data[key]

        # 构建子项
        children = []
        if "children" in data:
            for child_data in data["children"]:
                child = cls.from_playwright(child_data)
                if child.role != "ignored":
                    children.append(child)

        return cls(role=role, name=name, children=children, **attributes)

    def to_text(self, indent: int = 0, max_depth: int = 20) -> str:
        """将节点转换为文本表示。

        Args:
            indent: 当前缩进级别
            max_depth: 要遍历的最大深度

        Returns:
            文本表示
        """
        if max_depth <= 0:
            return ""

        prefix = "  " * indent
        lines = []

        # 添加此节点
        if self.role != "ignored":
            attr_str = ""
            if self.attributes:
                attrs = [f"{k}={v}" for k, v in self.attributes.items()]
                attr_str = f" [{', '.join(attrs)}]"

            name = self.name.replace("\n", " ")[:50]  # 截断长名称
            lines.append(f"{prefix}{self.role}: {name}{attr_str}")

        # 添加子项
        for child in self.children:
            lines.append(child.to_text(indent + 1, max_depth - 1))

        return "\n".join(lines)

    def get_interactive_elements(self) -> list[dict[str, Any]]:
        """获取子树中的所有交互元素。

        Returns:
            交互元素列表
        """
        interactive_roles = {
            "button", "link", "textbox", "searchbox", "textarea",
            "combobox", "listbox", "checkbox", "radio", "slider",
            "spinbutton", "menu", "menuitem", "tab", "treeitem",
        }

        elements = []

        if self.role in interactive_roles:
            elements.append({
                "role": self.role,
                "name": self.name,
                **self.attributes,
            })

        for child in self.children:
            elements.extend(child.get_interactive_elements())

        return elements

    def find_by_name(self, name: str, fuzzy: bool = False) -> "AccessibilityNode | None":
        """按名称查找节点。

        Args:
            name: 要搜索的名称
            fuzzy: 使用模糊匹配(包含)

        Returns:
            匹配的节点或 None
        """
        if self.name:
            if fuzzy and name.lower() in self.name.lower():
                return self
            elif not fuzzy and name.lower() == self.name.lower():
                return self

        for child in self.children:
            result = child.find_by_name(name, fuzzy)
            if result:
                return result

        return None

    def find_by_role(self, role: str) -> list["AccessibilityNode"]:
        """查找具有特定角色的所有节点。

        Args:
            role: 要搜索的角色

        Returns:
            匹配节点列表
        """
        nodes = []

        if self.role.lower() == role.lower():
            nodes.append(self)

        for child in self.children:
            nodes.extend(child.find_by_role(role))

        return nodes

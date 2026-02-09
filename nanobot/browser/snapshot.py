"""Page snapshot extraction for LLM consumption."""

import asyncio
from typing import Any

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from nanobot.browser.session import BrowserTimeoutError


class PageSnapshot:
    """Extract structured page snapshots for LLM understanding.

    Uses Playwright's accessibility tree to get semantic page structure
    with roles, labels, and states for interactive elements.

    Example:
        >>> snapshot = PageSnapshot(page)
        >>> tree = await snapshot.get_tree()
        >>> print(tree.to_text())
    """

    def __init__(self, page: Page, timeout: int = 30000) -> None:
        """Initialize page snapshot.

        Args:
            page: Playwright Page object
            timeout: Timeout for snapshot operations (milliseconds)
        """
        self.page = page
        self.timeout = timeout

    async def get_tree(self, wait_for_network_idle: bool = True) -> "AccessibilityNode":
        """Get the accessibility tree of the current page.

        Args:
            wait_for_network_idle: Wait for network idle before snapshot (for dynamic content)

        Returns:
            Root AccessibilityNode

        Raises:
            BrowserTimeoutError: If snapshot times out
        """
        # Wait for dynamic content
        if wait_for_network_idle:
            try:
                await self.page.wait_for_load_state("networkidle", timeout=self.timeout / 1000)
            except PlaywrightTimeoutError:
                # Continue anyway - some pages never reach network idle
                pass

        # Get accessibility tree - use try/except for compatibility
        try:
            # Try accessibility API first (if available)
            if hasattr(self.page, 'accessibility'):
                tree = await asyncio.wait_for(
                    self.page.accessibility.snapshot(),
                    timeout=self.timeout / 1000,
                )
            else:
                # Fallback: create simple tree from page content
                tree = await self._create_simple_tree()
        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError("Failed to get page snapshot within timeout") from exc
        except Exception:
            # If accessibility fails, create simple tree
            tree = await self._create_simple_tree()

        return AccessibilityNode.from_playwright(tree)

    async def _create_simple_tree(self) -> dict:
        """Create a simple accessibility-like tree from page content."""
        try:
            # Get page title and URL
            title = await self.page.title()
            url = self.page.url

            # Get all text content
            text_content = await self.page.inner_text("body")

            return {
                "role": "WebArea",
                "name": title,
                "url": url,
                "children": [
                    {
                        "role": "text",
                        "name": text_content[:1000],  # Limit text length
                    }
                ]
            }
        except Exception:
            # Ultimate fallback
            return {
                "role": "WebArea",
                "name": "Page",
            }

    async def get_text(self, wait_for_network_idle: bool = True) -> str:
        """Get a text representation of the page.

        Args:
            wait_for_network_idle: Wait for network idle before snapshot

        Returns:
            Formatted text representation of the page
        """
        tree = await self.get_tree(wait_for_network_idle)
        return tree.to_text()

    async def get_interactive_elements(self, wait_for_network_idle: bool = True) -> list[dict[str, Any]]:
        """Get all interactive elements from the page.

        Args:
            wait_for_network_idle: Wait for network idle before snapshot

        Returns:
            List of interactive elements with their attributes
        """
        tree = await self.get_tree(wait_for_network_idle)
        return tree.get_interactive_elements()


class AccessibilityNode:
    """A node in the accessibility tree."""

    def __init__(
        self,
        role: str,
        name: str = "",
        children: list["AccessibilityNode"] | None = None,
        **attributes: Any,
    ) -> None:
        """Initialize accessibility node.

        Args:
            role: ARIA role (e.g., "button", "link", "textbox")
            name: Accessible name of the element
            children: Child nodes
            **attributes: Additional accessibility attributes
        """
        self.role = role
        self.name = name
        self.children = children or []
        self.attributes = attributes

    @classmethod
    def from_playwright(cls, data: dict[str, Any] | None) -> "AccessibilityNode":
        """Create node from Playwright accessibility snapshot.

        Args:
            data: Playwright accessibility snapshot data

        Returns:
            AccessibilityNode
        """
        if data is None:
            return cls(role="root", name="Document")

        role = data.get("role", "unknown")
        name = data.get("name", "")

        # Filter out decorative and hidden elements
        ignored_roles = {"none", "presentation", "Generic"}
        if role in ignored_roles:
            # Check if children have content
            if "children" in data and data["children"]:
                # Return first meaningful child
                for child_data in data["children"]:
                    child = cls.from_playwright(child_data)
                    if child.role != "unknown":
                        return child
            return cls(role="ignored", name=name)

        # Extract useful attributes
        attributes = {}
        for key in ["checked", "expanded", "focused", "pressed", "selected", "disabled"]:
            if key in data:
                attributes[key] = data[key]

        # Build children
        children = []
        if "children" in data:
            for child_data in data["children"]:
                child = cls.from_playwright(child_data)
                if child.role != "ignored":
                    children.append(child)

        return cls(role=role, name=name, children=children, **attributes)

    def to_text(self, indent: int = 0, max_depth: int = 20) -> str:
        """Convert node to text representation.

        Args:
            indent: Current indentation level
            max_depth: Maximum depth to traverse

        Returns:
            Text representation
        """
        if max_depth <= 0:
            return ""

        prefix = "  " * indent
        lines = []

        # Add this node
        if self.role != "ignored":
            attr_str = ""
            if self.attributes:
                attrs = [f"{k}={v}" for k, v in self.attributes.items()]
                attr_str = f" [{', '.join(attrs)}]"

            name = self.name.replace("\n", " ")[:50]  # Truncate long names
            lines.append(f"{prefix}{self.role}: {name}{attr_str}")

        # Add children
        for child in self.children:
            lines.append(child.to_text(indent + 1, max_depth - 1))

        return "\n".join(lines)

    def get_interactive_elements(self) -> list[dict[str, Any]]:
        """Get all interactive elements in subtree.

        Returns:
            List of interactive elements
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
        """Find a node by name.

        Args:
            name: Name to search for
            fuzzy: Use fuzzy matching (contains)

        Returns:
            Matching node or None
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
        """Find all nodes with a specific role.

        Args:
            role: Role to search for

        Returns:
            List of matching nodes
        """
        nodes = []

        if self.role.lower() == role.lower():
            nodes.append(self)

        for child in self.children:
            nodes.extend(child.find_by_role(role))

        return nodes

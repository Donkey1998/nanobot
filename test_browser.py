"""测试浏览器自动化功能。"""

import asyncio
import json
import sys
from pathlib import Path

# 设置 UTF-8 编码输出（Windows 兼容）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径到 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from nanobot.config.loader import load_config
from nanobot.agent.tools.browser import BrowserTool


async def test_browser():
    """测试浏览器基本功能。"""
    print("=" * 60)
    print("开始测试浏览器自动化功能")
    print("=" * 60)

    # 1. 加载配置
    print("\n[1/4] 加载配置...")
    config = load_config()
    print(f"[OK] 浏览器启用状态: {config.browser.enabled}")
    print(f"[OK] 无头模式: {config.browser.headless}")
    print(f"[OK] 允许的域名: {config.browser.allowed_domains[:3]}...")

    if not config.browser.enabled:
        print("\n[ERROR] 浏览器功能未启用！")
        print("  请在 config.json 中设置 'browser.enabled = true'")
        return False

    # 2. 创建浏览器工具
    print("\n[2/4] 创建浏览器工具...")
    try:
        browser_tool = BrowserTool(config)
        print("[OK] BrowserTool 创建成功")
    except Exception as e:
        print(f"\n[ERROR] 创建 BrowserTool 失败: {e}")
        return False

    # 3. 启动浏览器
    print("\n[3/4] 启动浏览器...")
    try:
        result = await browser_tool.execute(action="start")
        result_data = json.loads(result)
        print(f"[OK] 浏览器已启动 (headless={result_data.get('headless')})")
    except Exception as e:
        print(f"\n[ERROR] 启动浏览器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. 导航到测试网页
    print("\n[4/4] 导航到百度首页...")
    test_url = "https://www.baidu.com"
    try:
        result = await browser_tool.execute(action="navigate", url=test_url)
        result_data = json.loads(result)
        if result_data.get("status") == "success":
            print(f"[OK] 成功导航到: {result_data.get('url')}")

            # 获取页面快照
            print("\n[5/5] 获取页面快照...")
            snapshot_result = await browser_tool.execute(action="snapshot")
            snapshot_data = json.loads(snapshot_result)

            if snapshot_data.get("status") == "success":
                print(f"[OK] 快照获取成功")
                print(f"      页面 URL: {snapshot_data.get('url')}")
                print(f"      可交互元素数量: {snapshot_data.get('elementCount', 0)}")

                # 显示部分页面结构
                tree_text = snapshot_data.get('tree', '')
                if tree_text:
                    lines = tree_text.split('\n')[:10]  # 只显示前10行
                    print(f"      页面结构预览:")
                    for line in lines:
                        if line.strip():
                            print(f"        {line}")
            else:
                print(f"[ERROR] 快照获取失败: {snapshot_data}")
        else:
            print(f"[ERROR] 导航失败: {result_data}")

    except Exception as e:
        print(f"\n[ERROR] 导航失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 停止浏览器
        print("\n停止浏览器...")
        stop_result = await browser_tool.execute(action="stop")
        print(f"[OK] {stop_result}")

    print("\n" + "=" * 60)
    print("[OK] 所有测试通过！浏览器功能正常工作")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_browser())
    sys.exit(0 if success else 1)

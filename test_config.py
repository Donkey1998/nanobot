"""测试配置加载。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nanobot.config.loader import load_config

config = load_config()

print("浏览器配置:")
print(f"  enabled: {config.browser.enabled}")
print(f"  headless: {config.browser.headless}")
print(f"  timeout: {config.browser.timeout} (type: {type(config.browser.timeout).__name__})")
print(f"  allowed_domains: {config.browser.allowed_domains}")

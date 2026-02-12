# Browser Control

Browser automation features for nanobot using Playwright.

## Overview

The browser control feature enables nanobot to interact with websites that require JavaScript execution, complex authentication flows, or dynamic content loading. This is particularly useful for:

- Webmail systems (e.g., QQ Mail, Gmail)
- Sites with OAuth/SSO login
- Single Page Applications (SPAs)
- Sites requiring CAPTCHA handling (manual login)

## Installation

### 1. Install Python Dependencies

```bash
pip install playwright keyring
```

### 2. Download Browser Binaries

```bash
playwright install chromium
```

## Configuration

Enable browser control in `~/.nanobot/config.json`:

```json
{
  "browser": {
    "enabled": true,
    "headless": true,
    "timeout": 30000,
    "allowedDomains": ["*.qq.com", "*.example.com"],
    "autoLoginDomains": ["mail.qq.com"]
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable browser automation features |
| `headless` | boolean | `true` | Run browser without GUI (set to `false` for manual login) |
| `timeout` | integer | `30000` | Operation timeout in milliseconds |
| `allowedDomains` | array | `[]` | Whitelist of allowed domain patterns (e.g., `["*.example.com"]`) |
| `autoLoginDomains` | array | `[]` | Domains to automatically attempt login |
| `profileDir` | string | `~/.nanobot/browser-profiles/` | Browser profile storage path |
| `credentialsPath` | string | `~/.nanobot/credentials.json` | Credentials backup file path |

## Usage

### Browser Tool

The browser tool provides the following actions:

#### Start Browser

```json
{
  "action": "start"
}
```

#### Navigate to URL

```json
{
  "action": "navigate",
  "url": "https://mail.qq.com"
}
```

#### Take Page Snapshot

```json
{
  "action": "snapshot"
}
```

Returns the page's accessibility tree with interactive elements.

#### Click Element

```json
{
  "action": "click",
  "locator": "Login button",
  "strategy": "auto"
}
```

#### Type Text

```json
{
  "action": "type",
  "locator": "Email input",
  "text": "user@example.com",
  "strategy": "auto"
}
```

#### Login

```json
{
  "action": "login",
  "url": "https://mail.qq.com",
  "username": "123456",
  "password": "password123",
  "strategy": "auto"
}
```

#### Stop Browser

```json
{
  "action": "stop"
}
```

### Element Location Strategies

| Strategy | Description | Example |
|----------|-------------|---------|
| `auto` | Try multiple strategies (default) | - |
| `aria` | ARIA label | `[aria-label="Login"]` |
| `id` | Element ID | `#login-button` |
| `testid` | data-testid attribute | `[data-testid="submit"]` |
| `css` | CSS selector | `.btn-primary` |
| `text` | Text content | `:text("Login")` |

## Login Strategies

The browser control uses a three-tier login strategy:

### 1. Specialized Adapter (High Priority)

Custom adapters for specific websites handle unique login flows.

**Built-in adapters:**
- **QQ Mail** (`mail.qq.com`, `*.qq.com`): Handles both password and QR code login

### 2. Generic Login (Fallback)

Heuristic-based login for standard username/password forms:
- Finds password field (anchor element)
- Locates username/email field before password
- Fills credentials and clicks submit
- Handles "remember me" checkbox

Works with ~60-70% of standard login forms.

### 3. Manual Login (Final Fallback)

Opens browser for user to complete login manually. Useful for:
- Sites with CAPTCHA
- Complex multi-factor authentication
- Adapter failures

## Credential Management

Credentials are securely stored using the system keyring:

### Saving Credentials

Credentials are automatically saved after successful login if using the browser tool.

### Storage Locations

- **macOS**: Keychain
- **Windows**: Credential Manager
- **Linux**: Secret Service (libsecret)

A backup file at `~/.nanobot/credentials.json` tracks which credentials exist (passwords are NOT stored in plain text).

## Security

### URL Whitelist

Only domains in `allowedDomains` can be accessed. This prevents:
- Phishing attacks
- Unintended resource consumption
- Access to malicious websites

### Domain Patterns

Use `*.` wildcards for subdomain matching:
- `*.example.com` matches `mail.example.com`, `docs.example.com`
- `example.com` matches only `example.com` (exact match)

## Custom Adapters

Create custom login adapters for sites not covered by built-in adapters:

```python
from nanobot.browser.adapters.base import WebsiteAdapter, LoginResult

class MySiteAdapter(WebsiteAdapter):
    NAME = "mysite"
    DOMAINS = ["*.mysite.com"]
    DISPLAY_NAME = "My Site"

    async def login(self, session, username, password):
        # Navigate to login page
        await session.navigate("https://mysite.com/login")

        # Fill credentials
        actions = BrowserActions(session.page)
        await actions.type_text("#username", username, strategy="css")
        await actions.type_text("#password", password, strategy="css")
        await actions.click("#login-btn", strategy="css")

        # Verify login
        if await self.verify_login(session):
            return LoginResult.success()

        return LoginResult.failed("Login verification failed")

    async def verify_login(self, session):
        # Check if login succeeded
        return "/dashboard" in session.page.url

# Register the adapter
from nanobot.browser.adapters import register_custom_adapter
register_custom_adapter(MySiteAdapter)
```

## Troubleshooting

### Playwright Not Found

```bash
pip install playwright
playwright install chromium
```

### Permission Denied

Add the domain to `allowedDomains` in config:
```json
{
  "browser": {
    "allowedDomains": ["example.com", "*.example.com"]
  }
}
```

### Login Timeout

Increase timeout in config:
```json
{
  "browser": {
    "timeout": 60000
  }
}
```

### Manual Login Required

For sites with CAPTCHA or complex MFA, set `headless: false` and use `strategy: "manual"` in the login action.

## Architecture

```
nanobot/
├── browser/
│   ├── __init__.py           # Module exports
│   ├── session.py            # Browser session management
│   ├── snapshot.py           # Page accessibility tree extraction
│   ├── actions.py            # Click, type, wait operations
│   ├── permissions.py        # URL whitelist enforcement
│   ├── credentials.py        # Keyring-based credential storage
│   └── adapters/
│       ├── __init__.py       # Login orchestration (3-tier strategy)
│       ├── base.py           # Adapter base interface
│       ├── registry.py       # Adapter registration and lookup
│       ├── generic.py        # Generic heuristic login
│       ├── qq_mail.py        # QQ Mail adapter
│       └── manual.py         # Manual login fallback
└── agent/
    └── tools/
        └── browser.py        # BrowserTool (LLM interface)
```

## Examples

### QQ Mail Login

```python
# Agent will use QQ Mail adapter automatically
result = await browser_tool.execute(
    action="login",
    url="https://mail.qq.com",
    username="123456789",
    password="mypassword"
)
```

### Manual Login with QR Code

```python
# For QR code login, browser must be visible (headless: false)
result = await browser_tool.execute(
    action="login",
    url="https://mail.qq.com",
    strategy="manual"
)
# Scan QR code with mobile phone, wait for completion
```

### Navigate and Extract Content

```python
# Start browser
await browser_tool.execute(action="start")

# Navigate
await browser_tool.execute(
    action="navigate",
    url="https://example.com"
)

# Get snapshot
snapshot = await browser_tool.execute(action="snapshot")

# Stop browser
await browser_tool.execute(action="stop")
```

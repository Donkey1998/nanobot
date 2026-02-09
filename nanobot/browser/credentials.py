"""使用系统密钥环管理凭据。"""

import json
import stat
from pathlib import Path
from typing import NamedTuple

import keyring


class Credential(NamedTuple):
    """网站凭据。"""

    domain: str
    username: str

    @property
    def service_name(self) -> str:
        """获取此凭据的密钥环服务名称。"""
        return f"nanobot-browser://{self.domain}"


class CredentialManager:
    """使用系统密钥环管理登录凭据。

    凭据存储在 OS 密钥环(macOS Keychain、Windows 凭据管理器、
    Linux Secret Service)中以确安全。备份文件跟踪存在的凭据。

    示例:
        >>> manager = CredentialManager()
        >>> manager.save("mail.qq.com", "123456", "password123")
        >>> password = manager.get("mail.qq.com", "123456")
    """

    DEFAULT_CREDENTIALS_FILE = Path.home() / ".nanobot" / "credentials.json"

    def __init__(self, credentials_file: Path | str | None = None) -> None:
        """初始化凭据管理器。

        Args:
            credentials_file: 凭据备份文件路径(默认: ~/.nanobot/credentials.json)
        """
        self._credentials_file = Path(credentials_file) if credentials_file else self.DEFAULT_CREDENTIALS_FILE
        self._ensure_credentials_file()

    def _ensure_credentials_file(self) -> None:
        """确保凭据文件存在并具有正确的权限。"""
        if not self._credentials_file.exists():
            self._credentials_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_credentials({})
        else:
            # 确保正确的权限(0600 - 仅所有者可读写)
            try:
                self._credentials_file.chmod(0o600)
            except OSError:
                # 某些系统不支持 chmod
                pass

    def _read_credentials(self) -> dict[str, list[str]]:
        """读取凭据备份文件。

        Returns:
            域 -> 用户名列表的字典
        """
        try:
            with open(self._credentials_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 文件损坏,返回空
            return {}

    def _write_credentials(self, data: dict[str, list[str]]) -> None:
        """写入凭据备份文件。

        Args:
            data: 域 -> 用户名列表的字典
        """
        with open(self._credentials_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

        # 设置安全权限
        try:
            self._credentials_file.chmod(0o600)
        except OSError:
            pass

    def save(self, domain: str, username: str, password: str) -> None:
        """保存凭据。

        Args:
            domain: 域名(例如 "mail.qq.com")
            username: 用户名
            password: 密码(将存储在密钥环中)

        示例:
            >>> manager.save("mail.qq.com", "123456", "password123")
        """
        # 标准化域名
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        credential = Credential(domain, username)

        # 存储在密钥环中
        keyring.set_password(credential.service_name, username, password)

        # 更新备份文件
        creds = self._read_credentials()
        if domain not in creds:
            creds[domain] = []
        if username not in creds[domain]:
            creds[domain].append(username)
            creds[domain].sort()
            self._write_credentials(creds)

    def get(self, domain: str, username: str) -> str | None:
        """从密钥环中检索密码。

        Args:
            domain: 域名
            username: 用户名

        Returns:
            如果找到则返回密码,否则返回 None
        """
        # 标准化域名
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        credential = Credential(domain, username)

        # 从密钥环获取
        return keyring.get_password(credential.service_name, username)

    def delete(self, domain: str, username: str) -> bool:
        """删除凭据。

        Args:
            domain: 域名
            username: 用户名

        Returns:
            如果删除则返回 True,如果未找到则返回 False
        """
        # 标准化域名
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        credential = Credential(domain, username)

        # 从密钥环删除
        try:
            keyring.delete_password(credential.service_name, username)
        except keyring.errors.PasswordDeleteError:
            return False

        # 更新备份文件
        creds = self._read_credentials()
        if domain in creds and username in creds[domain]:
            creds[domain].remove(username)
            if not creds[domain]:
                del creds[domain]
            self._write_credentials(creds)
            return True

        return False

    def list_credentials(self, domain: str | None = None) -> list[Credential]:
        """列出所有保存的凭据。

        Args:
            domain: 按域过滤(可选)

        Returns:
            凭据列表
        """
        creds = self._read_credentials()

        if domain:
            from nanobot.browser.permissions import normalize_domain
            domain = normalize_domain(domain)
            if domain not in creds:
                return []
            usernames = creds[domain]
            return [Credential(domain, u) for u in usernames]

        result = []
        for d, usernames in creds.items():
            result.extend([Credential(d, u) for u in usernames])
        return result

    def has_credential(self, domain: str, username: str) -> bool:
        """检查凭据是否存在。

        Args:
            domain: 域名
            username: 用户名

        Returns:
            如果凭据存在则返回 True
        """
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        creds = self._read_credentials()
        return domain in creds and username in creds[domain]


def mask_password(password: str | None) -> str:
    """掩码密码用于日志记录(不记录实际密码)。

    Args:
        password: 要掩码的密码

    Returns:
        掩码字符串(例如 "********")
    """
    if password is None:
        return "<none>"
    return "********"

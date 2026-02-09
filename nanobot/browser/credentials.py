"""Credential management using system keyring."""

import json
import stat
from pathlib import Path
from typing import NamedTuple

import keyring


class Credential(NamedTuple):
    """A website credential."""

    domain: str
    username: str

    @property
    def service_name(self) -> str:
        """Get the keyring service name for this credential."""
        return f"nanobot-browser://{self.domain}"


class CredentialManager:
    """Manage login credentials using system keyring.

    Credentials are stored in the OS keyring (macOS Keychain, Windows Credential Manager,
    Linux Secret Service) for security. A backup file tracks which credentials exist.

    Example:
        >>> manager = CredentialManager()
        >>> manager.save("mail.qq.com", "123456", "password123")
        >>> password = manager.get("mail.qq.com", "123456")
    """

    DEFAULT_CREDENTIALS_FILE = Path.home() / ".nanobot" / "credentials.json"

    def __init__(self, credentials_file: Path | str | None = None) -> None:
        """Initialize credential manager.

        Args:
            credentials_file: Path to credentials backup file (default: ~/.nanobot/credentials.json)
        """
        self._credentials_file = Path(credentials_file) if credentials_file else self.DEFAULT_CREDENTIALS_FILE
        self._ensure_credentials_file()

    def _ensure_credentials_file(self) -> None:
        """Ensure credentials file exists with proper permissions."""
        if not self._credentials_file.exists():
            self._credentials_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_credentials({})
        else:
            # Ensure correct permissions (0600 - owner read/write only)
            try:
                self._credentials_file.chmod(0o600)
            except OSError:
                # Some systems don't support chmod
                pass

    def _read_credentials(self) -> dict[str, list[str]]:
        """Read credentials backup file.

        Returns:
            Dict mapping domain -> list of usernames
        """
        try:
            with open(self._credentials_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # File corrupted, return empty
            return {}

    def _write_credentials(self, data: dict[str, list[str]]) -> None:
        """Write credentials backup file.

        Args:
            data: Dict mapping domain -> list of usernames
        """
        with open(self._credentials_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

        # Set secure permissions
        try:
            self._credentials_file.chmod(0o600)
        except OSError:
            pass

    def save(self, domain: str, username: str, password: str) -> None:
        """Save a credential.

        Args:
            domain: Domain name (e.g., "mail.qq.com")
            username: Username
            password: Password (will be stored in keyring)

        Example:
            >>> manager.save("mail.qq.com", "123456", "password123")
        """
        # Normalize domain
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        credential = Credential(domain, username)

        # Store in keyring
        keyring.set_password(credential.service_name, username, password)

        # Update backup file
        creds = self._read_credentials()
        if domain not in creds:
            creds[domain] = []
        if username not in creds[domain]:
            creds[domain].append(username)
            creds[domain].sort()
            self._write_credentials(creds)

    def get(self, domain: str, username: str) -> str | None:
        """Retrieve a password from keyring.

        Args:
            domain: Domain name
            username: Username

        Returns:
            Password if found, None otherwise
        """
        # Normalize domain
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        credential = Credential(domain, username)

        # Get from keyring
        return keyring.get_password(credential.service_name, username)

    def delete(self, domain: str, username: str) -> bool:
        """Delete a credential.

        Args:
            domain: Domain name
            username: Username

        Returns:
            True if deleted, False if not found
        """
        # Normalize domain
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        credential = Credential(domain, username)

        # Delete from keyring
        try:
            keyring.delete_password(credential.service_name, username)
        except keyring.errors.PasswordDeleteError:
            return False

        # Update backup file
        creds = self._read_credentials()
        if domain in creds and username in creds[domain]:
            creds[domain].remove(username)
            if not creds[domain]:
                del creds[domain]
            self._write_credentials(creds)
            return True

        return False

    def list_credentials(self, domain: str | None = None) -> list[Credential]:
        """List all saved credentials.

        Args:
            domain: Filter by domain (optional)

        Returns:
            List of credentials
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
        """Check if a credential exists.

        Args:
            domain: Domain name
            username: Username

        Returns:
            True if credential exists
        """
        from nanobot.browser.permissions import normalize_domain
        domain = normalize_domain(domain)

        creds = self._read_credentials()
        return domain in creds and username in creds[domain]


def mask_password(password: str | None) -> str:
    """Mask password for logging (don't log actual passwords).

    Args:
        password: Password to mask

    Returns:
        Masked string (e.g., "********")
    """
    if password is None:
        return "<none>"
    return "********"

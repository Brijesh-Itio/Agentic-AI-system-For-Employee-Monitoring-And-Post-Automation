"""
Direct server file access — a parallel escape hatch to automation/seo/cms/*
for the files a CMS REST API can't reach at all: server-level files like
wp-content/mu-plugins/*.php and .htaccess. Grew directly out of
degemasecureltd.com's mu-plugin crash, where the only way into the site
(wp-admin) was itself the thing the broken file had taken down — this
lets the app reach the filesystem underneath WordPress instead of going
through it.

Two real, different protocols, not one: SFTP (SSH-based, paramiko) was
built first on the assumption every host offers it. In practice a real
site tested against this session (webpays.com) only exposed classic FTP /
Explicit FTPS on port 21, not SFTP at all — a genuinely different
protocol family despite the similar name, confirmed by that host's own
control panel. SftpClient and FtpClient below implement the same public
surface (is_reachable/list_dir/read_file/write_file/rename_file/
delete_file) so api/routes/seo.py's server/* endpoints don't need to know
which one they're talking to — client_for_site() picks based on the
site's saved ssh_protocol.

Each call opens its own connection and closes it when done; this is
deliberately not a long-lived pooled client, since these are one-off
diagnostic/fix operations (read a log, rename a file) rather than a
sustained integration like the CMS clients.
"""
import ftplib
import io
import logging
import stat
from dataclasses import dataclass
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)

DEFAULT_SFTP_PORT = 22
DEFAULT_FTP_PORT = 21
CONNECT_TIMEOUT_SECONDS = 10


@dataclass
class ServerDirEntry:
    name: str
    is_dir: bool
    size: Optional[int] = None


@dataclass
class SftpConfig:
    host: str
    username: str
    password: str
    port: int = DEFAULT_SFTP_PORT


class SftpClient:
    def __init__(self, config: SftpConfig):
        self._config = config

    def _connect(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self._config.host,
            port=self._config.port,
            username=self._config.username,
            password=self._config.password,
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
        return client

    def is_reachable(self) -> tuple[bool, Optional[str]]:
        try:
            client = self._connect()
            client.close()
            return True, None
        except Exception as exc:
            logger.warning("SFTP connection check failed for %s: %s", self._config.host, exc)
            return False, str(exc)

    def read_file(self, remote_path: str) -> str:
        client = self._connect()
        try:
            sftp = client.open_sftp()
            with sftp.open(remote_path, "r") as f:
                return f.read().decode("utf-8", errors="replace")
        finally:
            client.close()

    def write_file(self, remote_path: str, content: str) -> None:
        client = self._connect()
        try:
            sftp = client.open_sftp()
            with sftp.open(remote_path, "w") as f:
                f.write(content.encode("utf-8"))
        finally:
            client.close()

    def rename_file(self, remote_path: str, new_path: str) -> None:
        client = self._connect()
        try:
            sftp = client.open_sftp()
            sftp.rename(remote_path, new_path)
        finally:
            client.close()

    def delete_file(self, remote_path: str) -> None:
        client = self._connect()
        try:
            sftp = client.open_sftp()
            sftp.remove(remote_path)
        finally:
            client.close()

    def list_dir(self, remote_path: str) -> list[ServerDirEntry]:
        client = self._connect()
        try:
            sftp = client.open_sftp()
            entries = [
                ServerDirEntry(name=attr.filename, is_dir=stat.S_ISDIR(attr.st_mode), size=attr.st_size)
                for attr in sftp.listdir_attr(remote_path)
            ]
            # Directories first, then alphabetical within each group — the
            # ordering a file manager UI expects.
            return sorted(entries, key=lambda e: (not e.is_dir, e.name.lower()))
        finally:
            client.close()


@dataclass
class FtpConfig:
    host: str
    username: str
    password: str
    port: int = DEFAULT_FTP_PORT
    use_tls: bool = True  # Explicit FTPS (AUTH TLS on the control channel) — plain FTP has no encryption at all


class FtpClient:
    """Plain FTP or Explicit FTPS via stdlib ftplib — no extra dependency.
    Explicit FTPS connects like plain FTP then upgrades via AUTH TLS
    (ftplib.FTP_TLS), matching what cPanel-style hosts label "FTP /
    Explicit FTPS" on port 21. Implicit FTPS (auto-TLS from connect,
    usually port 990) is a different, less common variant not built here
    — nothing in this session's real testing needed it."""

    def __init__(self, config: FtpConfig):
        self._config = config

    def _connect(self):
        ftp = ftplib.FTP_TLS(timeout=CONNECT_TIMEOUT_SECONDS) if self._config.use_tls else ftplib.FTP(timeout=CONNECT_TIMEOUT_SECONDS)
        ftp.connect(self._config.host, self._config.port)
        ftp.login(self._config.username, self._config.password)
        if self._config.use_tls:
            ftp.prot_p()  # secure the data channel too, not just the control channel
        return ftp

    def is_reachable(self) -> tuple[bool, Optional[str]]:
        try:
            ftp = self._connect()
            ftp.quit()
            return True, None
        except Exception as exc:
            logger.warning("FTP connection check failed for %s: %s", self._config.host, exc)
            return False, str(exc)

    def read_file(self, remote_path: str) -> str:
        ftp = self._connect()
        try:
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {remote_path}", buf.write)
            return buf.getvalue().decode("utf-8", errors="replace")
        finally:
            ftp.quit()

    def write_file(self, remote_path: str, content: str) -> None:
        ftp = self._connect()
        try:
            ftp.storbinary(f"STOR {remote_path}", io.BytesIO(content.encode("utf-8")))
        finally:
            ftp.quit()

    def rename_file(self, remote_path: str, new_path: str) -> None:
        ftp = self._connect()
        try:
            ftp.rename(remote_path, new_path)
        finally:
            ftp.quit()

    def delete_file(self, remote_path: str) -> None:
        ftp = self._connect()
        try:
            ftp.delete(remote_path)
        finally:
            ftp.quit()

    def list_dir(self, remote_path: str) -> list[ServerDirEntry]:
        ftp = self._connect()
        try:
            entries = []
            try:
                # MLSD (RFC 3659) — structured listing with a real "type"
                # fact (file/dir), supported by most modern FTP/FTPS
                # servers. Preferred over LIST, which has no standard
                # machine-parseable format.
                for name, facts in ftp.mlsd(remote_path):
                    if name in (".", ".."):
                        continue
                    entry_type = facts.get("type", "file")
                    size = facts.get("size")
                    entries.append(
                        ServerDirEntry(
                            name=name,
                            is_dir=entry_type in ("dir", "cdir", "pdir"),
                            size=int(size) if size and size.isdigit() else None,
                        )
                    )
            except ftplib.error_perm:
                # Server doesn't support MLSD — fall back to a plain name
                # list with no type info (best-effort, treated as files).
                logger.info("MLSD unsupported by %s — falling back to NLST (no file/dir distinction)", self._config.host)
                entries = [ServerDirEntry(name=name, is_dir=False) for name in ftp.nlst(remote_path)]
            return sorted(entries, key=lambda e: (not e.is_dir, e.name.lower()))
        finally:
            ftp.quit()


def client_for_site(site):
    """None when the site has no server-access credentials saved yet —
    callers turn that into a 400, same as an unset CMS client would."""
    if not (site.ssh_host and site.ssh_username and site.ssh_password):
        return None
    protocol = (site.ssh_protocol or "sftp").strip().lower()
    port = int(site.ssh_port) if site.ssh_port and site.ssh_port.strip().isdigit() else None

    if protocol == "sftp":
        return SftpClient(
            SftpConfig(
                host=site.ssh_host,
                username=site.ssh_username,
                password=site.ssh_password,
                port=port or DEFAULT_SFTP_PORT,
            )
        )
    if protocol in ("ftp", "ftps"):
        return FtpClient(
            FtpConfig(
                host=site.ssh_host,
                username=site.ssh_username,
                password=site.ssh_password,
                port=port or DEFAULT_FTP_PORT,
                use_tls=protocol == "ftps",
            )
        )
    logger.warning("Unknown server-access protocol %r for site %s — defaulting to sftp", protocol, site.id)
    return SftpClient(
        SftpConfig(host=site.ssh_host, username=site.ssh_username, password=site.ssh_password, port=port or DEFAULT_SFTP_PORT)
    )

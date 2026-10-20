#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Private immutable, content-addressed storage for research artifacts."""

from __future__ import annotations

import hashlib
import errno
import json
import os
import re
import secrets
import stat

from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from research_contract import canonical_json_bytes

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PRIVATE_PATH_RE = re.compile(
    r"(?:^|[\s\"'(`=:,;\[])(?:/(?!/)[^\s\"'`]+|[A-Za-z]:[\\/][^\s\"'`]+|\\\\[^\\\s]+\\[^\s\"'`]+)"
)
_BEARER_RE = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "auth",
        "credential",
        "credentials",
        "password",
        "passwd",
        "secret",
        "headers",
        "private_headers",
        "cookie",
        "cookies",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "apikey",
        "signed_url",
        "provider_payload",
        "raw_payload",
        "raw_response",
    }
)
_TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
    }
)
_SENSITIVE_QUERY_PARTS = (
    "token",
    "signature",
    "credential",
    "authorization",
    "api_key",
    "apikey",
    "signed",
    "x-amz-",
    "x-goog-",
    "sig",
    "session",
    "cookie",
    "password",
    "secret",
)
_KINDS = {"bundles": ".json", "sources": ".txt", "tombstones": ".json"}


class ArchiveViolation(Exception):
    """An archive containment, confidentiality, or integrity invariant failed."""


class ArchiveCollisionError(ArchiveViolation):
    """A content-addressed path already contains different bytes."""


def _normalized_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _is_sensitive_field(key: object) -> bool:
    normalized = _normalized_key(key)
    compact = normalized.replace("_", "")
    return normalized in _SENSITIVE_KEYS or any(
        marker in compact
        for marker in (
            "authorization", "credential", "password", "passwd", "secret",
            "cookie", "session", "accesstoken", "refreshtoken", "idtoken",
            "apikey", "privateheaders", "providerpayload", "rawpayload", "rawresponse",
        )
    )


def _is_sensitive_query_key(key: str) -> bool:
    lowered = key.strip().lower().replace("-", "_")
    return lowered.startswith("utm_") or lowered in _TRACKING_QUERY_KEYS or any(
        part in lowered for part in _SENSITIVE_QUERY_PARTS
    )


def sanitize_canonical_url(url: str) -> str:
    """Return a stable public HTTP(S) URL with replayable query data removed."""
    if not isinstance(url, str) or not url.strip():
        raise ArchiveViolation("canonical URL must be non-empty text")
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise ArchiveViolation("invalid canonical URL") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ArchiveViolation("canonical URL must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise ArchiveViolation("canonical URL credentials are forbidden")
    if not parsed.hostname:
        raise ArchiveViolation("canonical URL must include a host")
    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    netloc = host if port is None or default_port else f"{host}:{port}"
    safe_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_sensitive_query_key(key)
    ]
    safe_query.sort()
    return urlunsplit((scheme, netloc, parsed.path or "/", urlencode(safe_query), ""))


def _assert_no_sensitive(value: object, path: str = "payload") -> None:
    if is_dataclass(value) and not isinstance(value, type):
        _assert_no_sensitive(
            {item.name: getattr(value, item.name) for item in fields(value)}, path
        )
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _is_sensitive_field(key):
                raise ArchiveViolation(f"sensitive field rejected at {path}.{key}")
            _assert_no_sensitive(nested, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _assert_no_sensitive(nested, f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    lowered = value.lower()
    if _BEARER_RE.search(value) or re.search(
        r"\b(?:authorization|cookie|set-cookie|session)\s*[:=]", value, re.I
    ):
        raise ArchiveViolation(f"sensitive credential rejected at {path}")
    if _PRIVATE_PATH_RE.search(value):
        raise ArchiveViolation(f"private absolute path rejected at {path}")
    if re.search(
        r"(?:[?&]|\b)(?:token|access[_-]?token|refresh[_-]?token|api[_-]?key|credential|password|secret|session|cookie|x-amz-(?:signature|credential|security-token)|x-goog-(?:signature|credential)|signature|sig)=",
        lowered,
    ):
        raise ArchiveViolation(f"sensitive signed or tokenized URL rejected at {path}")


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _normalize_canonical_urls(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        value = {item.name: getattr(value, item.name) for item in fields(value)}
    if isinstance(value, Mapping):
        normalized = {}
        for key, nested in value.items():
            if _normalized_key(key) == "canonical_url":
                normalized[key] = sanitize_canonical_url(nested)
            else:
                normalized[key] = _normalize_canonical_urls(nested)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize_canonical_urls(item) for item in value]
    return value


class ResearchArchive:
    """Small deterministic archive API with immutable publication semantics."""

    def __init__(
        self,
        root: str | Path,
        *,
        forbidden_roots: Iterable[str | Path],
        max_bundle_bytes: int = 2_000_000,
        max_source_bytes: int = 1_000_000,
    ) -> None:
        forbidden = tuple(
            Path(item).expanduser().resolve(strict=False) for item in forbidden_roots
        )
        if not forbidden:
            raise ArchiveViolation("forbidden_roots must explicitly include repo/vault roots")
        self._configured_root = Path(root).expanduser().absolute()
        current = Path(self._configured_root.anchor)
        for part in self._configured_root.parts[1:]:
            current = current / part
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                break
            if stat.S_ISLNK(mode):
                raise ArchiveViolation("archive root ancestor symlink rejected")
        self.root = self._configured_root.resolve(strict=False)
        if any(
            self.root == item
            or self.root.is_relative_to(item)
            or item.is_relative_to(self.root)
            for item in forbidden
        ):
            raise ArchiveViolation("archive root overlaps a forbidden root")
        if not isinstance(max_bundle_bytes, int) or max_bundle_bytes <= 0:
            raise ArchiveViolation("bundle byte cap must be positive")
        if not isinstance(max_source_bytes, int) or max_source_bytes <= 0:
            raise ArchiveViolation("source byte cap must be positive")
        self._forbidden_roots = forbidden
        self.max_bundle_bytes = max_bundle_bytes
        self.max_source_bytes = max_source_bytes

    def _check_root(self) -> None:
        if self._configured_root.is_symlink():
            raise ArchiveViolation("archive root symlink rejected")
        resolved = self.root.resolve(strict=False)
        if resolved != self.root:
            raise ArchiveViolation("archive root changed through a symlink")
        if any(
            resolved == item
            or resolved.is_relative_to(item)
            or item.is_relative_to(resolved)
            for item in self._forbidden_roots
        ):
            raise ArchiveViolation("archive root overlaps a forbidden root")

    def _check_symlinks(self, target: Path) -> None:
        self._check_root()
        try:
            relative = target.relative_to(self.root)
        except ValueError as exc:
            raise ArchiveViolation("archive child escapes configured root") from exc
        current = self.root
        for part in relative.parts:
            current = current / part
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(mode):
                raise ArchiveViolation(f"symlink archive component rejected: {current}")

    def resolve_child(self, *children: str | Path) -> Path:
        self._check_root()
        parts: list[str] = []
        for child in children:
            candidate = Path(child)
            if candidate.is_absolute():
                raise ArchiveViolation("absolute archive child rejected")
            if ".." in candidate.parts:
                raise ArchiveViolation("archive child traversal rejected")
            parts.extend(part for part in candidate.parts if part not in {"", "."})
        target = self.root.joinpath(*parts)
        self._check_symlinks(target)
        return target

    def _open_root_fd(self, *, create: bool) -> int:
        """Walk from filesystem root with O_NOFOLLOW so ancestors cannot race."""
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self._configured_root.anchor, flags)
        try:
            for part in self._configured_root.parts[1:]:
                try:
                    next_fd = os.open(part, flags, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise ArchiveViolation("archive root is missing")
                    os.mkdir(part, 0o700, dir_fd=fd)
                    next_fd = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            mode = os.fstat(fd).st_mode
            if not stat.S_ISDIR(mode):
                raise ArchiveViolation("archive root is not a directory")
            os.fchmod(fd, 0o700)
            return fd
        except Exception:
            os.close(fd)
            raise

    def _open_kind_fd(self, kind: str, *, create: bool) -> int:
        self._validate_kind(kind)
        root_fd = self._open_root_fd(create=create)
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            try:
                kind_fd = os.open(kind, flags, dir_fd=root_fd)
            except FileNotFoundError:
                if not create:
                    raise ArchiveViolation("archive kind directory is missing")
                os.mkdir(kind, 0o700, dir_fd=root_fd)
                kind_fd = os.open(kind, flags, dir_fd=root_fd)
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise ArchiveViolation("symlink archive kind rejected") from exc
                raise
            if not stat.S_ISDIR(os.fstat(kind_fd).st_mode):
                os.close(kind_fd)
                raise ArchiveViolation("archive kind path is not a directory")
            os.fchmod(kind_fd, 0o700)
            return kind_fd
        finally:
            os.close(root_fd)

    def _ensure_directory(self, kind: str) -> Path:
        fd = self._open_kind_fd(kind, create=True)
        os.close(fd)
        return self.resolve_child(kind)

    @staticmethod
    def _validate_hash(digest: str) -> str:
        if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
            raise ArchiveViolation("invalid sha256 hash")
        return digest

    @staticmethod
    def _validate_kind(kind: str) -> str:
        if kind not in _KINDS:
            raise ArchiveViolation("invalid archive kind")
        return kind

    def path_for(self, kind: str, digest: str) -> Path:
        kind = self._validate_kind(kind)
        digest = self._validate_hash(digest)
        return self.resolve_child(kind, digest.removeprefix("sha256:") + _KINDS[kind])

    def _read_existing_for_publish(self, kind_fd: int, name: str, limit: int) -> bytes:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(name, flags, dir_fd=kind_fd)
        try:
            mode = os.fstat(fd).st_mode
            if not stat.S_ISREG(mode):
                raise ArchiveCollisionError("existing content path is not a regular file")
            if stat.S_IMODE(mode) != 0o600:
                raise ArchiveViolation("existing archived file permission must be 0600")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                return stream.read(limit + 1)
        finally:
            os.close(fd)

    def _publish(self, kind: str, digest: str, data: bytes, limit: int) -> str:
        if len(data) > limit:
            raise ArchiveViolation(f"{kind[:-1]} byte cap exceeded")
        digest = self._validate_hash(digest)
        suffix = _KINDS[self._validate_kind(kind)]
        target_name = digest.removeprefix("sha256:") + suffix
        kind_fd = self._open_kind_fd(kind, create=True)
        temp_name = ".archive-tmp-" + secrets.token_hex(16)
        temp_fd = -1
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            temp_fd = os.open(temp_name, flags, 0o600, dir_fd=kind_fd)
            os.fchmod(temp_fd, 0o600)
            with os.fdopen(temp_fd, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(temp_fd)
            os.close(temp_fd)
            temp_fd = -1
            try:
                os.link(
                    temp_name, target_name,
                    src_dir_fd=kind_fd, dst_dir_fd=kind_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                existing = self._read_existing_for_publish(kind_fd, target_name, limit)
                if existing != data:
                    raise ArchiveCollisionError("existing hash path has different bytes")
            os.fsync(kind_fd)
            return digest
        finally:
            if temp_fd >= 0:
                os.close(temp_fd)
            try:
                os.unlink(temp_name, dir_fd=kind_fd)
            except FileNotFoundError:
                pass
            os.close(kind_fd)

    def write_bundle(self, payload: object) -> str:
        payload = _normalize_canonical_urls(payload)
        _assert_no_sensitive(payload)
        try:
            data = canonical_json_bytes(payload)
        except (TypeError, ValueError) as exc:
            raise ArchiveViolation("bundle is not canonical JSON") from exc
        digest = _digest(data)
        return self._publish("bundles", digest, data, self.max_bundle_bytes)

    def write_source(self, snapshot: str) -> str:
        if not isinstance(snapshot, str):
            raise ArchiveViolation("source snapshot must be UTF-8 text")
        _assert_no_sensitive(snapshot, "source")
        data = snapshot.encode("utf-8")
        digest = _digest(data)
        return self._publish("sources", digest, data, self.max_source_bytes)

    def _read_bytes(self, kind: str, digest: str, limit: int) -> bytes:
        digest = self._validate_hash(digest)
        suffix = _KINDS[self._validate_kind(kind)]
        name = digest.removeprefix("sha256:") + suffix
        kind_fd = self._open_kind_fd(kind, create=False)
        fd = -1
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(name, flags, dir_fd=kind_fd)
            except FileNotFoundError as exc:
                raise ArchiveViolation("archived content is missing") from exc
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise ArchiveViolation("symlink archived content rejected") from exc
                raise
            mode = os.fstat(fd).st_mode
            if not stat.S_ISREG(mode):
                raise ArchiveViolation("archived content is not a regular file")
            if stat.S_IMODE(mode) != 0o600:
                raise ArchiveViolation("archived file permission must be 0600")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(limit + 1)
        except OSError as exc:
            raise ArchiveViolation("cannot safely open archived content") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            os.close(kind_fd)
        if len(data) > limit:
            raise ArchiveViolation(f"{kind[:-1]} byte cap exceeded")
        if _digest(data) != digest:
            raise ArchiveViolation("archived content hash mismatch")
        return data

    def _read_json(self, kind: str, digest: str, limit: int) -> object:
        data = self._read_bytes(kind, digest, limit)
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArchiveViolation("archived JSON is invalid") from exc
        if canonical_json_bytes(payload) != data:
            raise ArchiveViolation("archived JSON is not canonical")
        _assert_no_sensitive(payload)
        return payload

    def read_bundle(self, digest: str) -> object:
        return self._read_json("bundles", digest, self.max_bundle_bytes)

    def read_source(self, digest: str) -> str:
        data = self._read_bytes("sources", digest, self.max_source_bytes)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArchiveViolation("source snapshot is not UTF-8") from exc
        _assert_no_sensitive(text, "source")
        return text

    def read_tombstone(self, digest: str) -> object:
        return self._read_json("tombstones", digest, self.max_bundle_bytes)

    def delete(
        self,
        kind: str,
        digest: str,
        *,
        selector: object,
        reason: str,
        deleted_at: str,
    ) -> str:
        if kind not in {"bundles", "sources"}:
            raise ArchiveViolation("governed delete kind must be bundles or sources")
        self._validate_hash(digest)
        if not isinstance(reason, str) or not reason.strip():
            raise ArchiveViolation("governed delete reason is required")
        if not isinstance(deleted_at, str) or not deleted_at.strip():
            raise ArchiveViolation("governed delete deleted_at is required")
        base_tombstone = {
            "hash": digest,
            "selector": selector,
            "reason": reason,
            "deleted_at": deleted_at,
        }
        _assert_no_sensitive(base_tombstone, "tombstone")

        pending = {**base_tombstone, "status": "pending"}
        pending_data = canonical_json_bytes(pending)
        pending_hash = _digest(pending_data)
        # Governance record is durable before content removal.
        self._publish("tombstones", pending_hash, pending_data, self.max_bundle_bytes)

        limit = self.max_bundle_bytes if kind == "bundles" else self.max_source_bytes
        suffix = _KINDS[kind]
        name = digest.removeprefix("sha256:") + suffix
        try:
            self._read_bytes(kind, digest, limit)
        except ArchiveViolation as exc:
            if "missing" not in str(exc):
                raise
        else:
            kind_fd = self._open_kind_fd(kind, create=False)
            target_fd = -1
            try:
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                target_fd = os.open(name, flags, dir_fd=kind_fd)
                opened = os.fstat(target_fd)
                named = os.stat(name, dir_fd=kind_fd, follow_symlinks=False)
                if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
                    raise ArchiveViolation("governed delete target changed during validation")
                if not stat.S_ISREG(opened.st_mode):
                    raise ArchiveViolation("governed delete target is not regular")
                if stat.S_IMODE(opened.st_mode) != 0o600:
                    raise ArchiveViolation("governed delete target permission must be 0600")
                os.unlink(name, dir_fd=kind_fd)
                os.fsync(kind_fd)
            finally:
                if target_fd >= 0:
                    os.close(target_fd)
                os.close(kind_fd)

        completed = {**base_tombstone, "status": "completed"}
        completed_data = canonical_json_bytes(completed)
        completed_hash = _digest(completed_data)
        self._publish("tombstones", completed_hash, completed_data, self.max_bundle_bytes)
        return completed_hash

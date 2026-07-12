#!/usr/bin/env python3
"""Platform-neutral, metadata-only yt-dlp provider for video adapters."""

from __future__ import annotations

import json
import subprocess
from typing import Mapping


class YtDlpMetadataProvider:
    """Run yt-dlp with a fixed argv; return metadata without downloading media."""

    def __init__(self, binary: str = "yt-dlp"):
        self.binary = binary

    def __call__(self, url: str, timeout_s: float) -> Mapping[str, object]:
        return self.fetch(url, timeout_s)

    def fetch(self, url: str, timeout_s: float) -> Mapping[str, object]:
        argv = [
            self.binary,
            "--dump-single-json",
            "--skip-download",
            "--no-playlist",
            "--no-warnings",
            url,
        ]
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("video metadata provider timed out") from exc
        if result.returncode != 0:
            lowered = (result.stderr or "").lower()
            if any(marker in lowered for marker in ("login", "cookie", "authentication")):
                raise PermissionError("video authentication required")
            if any(marker in lowered for marker in ("unsupported url", "not found", "homepage")):
                raise LookupError("video source unavailable or platform changed")
            raise RuntimeError("video metadata provider failed")
        try:
            payload = json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise LookupError("video metadata response invalid") from exc
        if not isinstance(payload, Mapping) or not payload.get("id"):
            raise LookupError("video metadata missing stable identity")
        return payload


__all__ = ["YtDlpMetadataProvider"]

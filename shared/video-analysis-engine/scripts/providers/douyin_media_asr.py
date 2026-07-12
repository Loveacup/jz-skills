#!/usr/bin/env python3
"""Single-video Douyin media download + H200 ASR composition provider."""

from __future__ import annotations

import os
import subprocess
import tempfile
import warnings
from pathlib import Path
from typing import Callable, Mapping, Optional

import requests


MetadataProvider = Callable[[str, float], Mapping[str, object]]
DEFAULT_H200_ASR_ENDPOINT = "http://127.0.0.1:8088/ASR/transcribe"
DEFAULT_ASR_ENDPOINT_FILE = "~/.config/video-analysis-engine/asr_endpoint"


def _endpoint_from_file(values: Mapping[str, str]) -> str:
    raw_path = (values.get("VIDEO_ANALYSIS_ASR_ENDPOINT_FILE") or DEFAULT_ASR_ENDPOINT_FILE).strip()
    try:
        return Path(raw_path).expanduser().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


class DouyinMediaAsrProvider:
    """Enrich public metadata with an H200 transcript using ephemeral audio."""

    def __init__(
        self,
        metadata_provider: MetadataProvider,
        endpoint: str,
        *,
        runner: Callable = subprocess.run,
        post: Callable = requests.post,
        binary: str = "yt-dlp",
        language: str = "zh",
        temp_root: Optional[Path] = None,
    ):
        if not endpoint:
            raise ValueError("H200 endpoint 不能为空")
        self._metadata_provider = metadata_provider
        self._endpoint = endpoint
        self._runner = runner
        self._post = post
        self._binary = binary
        self._language = language
        self._temp_root = temp_root

    @classmethod
    def from_env(
        cls,
        metadata_provider: MetadataProvider,
        env: Optional[Mapping[str, str]] = None,
        **kwargs,
    ) -> "DouyinMediaAsrProvider":
        values = os.environ if env is None else env
        endpoint = (values.get("VIDEO_ANALYSIS_ASR_ENDPOINT") or "").strip()
        if not endpoint:
            legacy_endpoint = (values.get("BILI_ASR_ENDPOINT") or "").strip()
            if legacy_endpoint:
                warnings.warn(
                    "BILI_ASR_ENDPOINT 已弃用，请迁移到 VIDEO_ANALYSIS_ASR_ENDPOINT",
                    DeprecationWarning,
                    stacklevel=2,
                )
                endpoint = legacy_endpoint
        endpoint = endpoint or _endpoint_from_file(values) or DEFAULT_H200_ASR_ENDPOINT

        language = (values.get("VIDEO_ANALYSIS_ASR_LANGUAGE") or "").strip().lower()
        if not language:
            legacy_language = (values.get("BILI_ASR_LANGUAGE") or "").strip().lower()
            if legacy_language:
                warnings.warn(
                    "BILI_ASR_LANGUAGE 已弃用，请迁移到 VIDEO_ANALYSIS_ASR_LANGUAGE",
                    DeprecationWarning,
                    stacklevel=2,
                )
                language = legacy_language
        language = language or "zh"
        if language not in {"zh", "en", "auto"}:
            raise ValueError("VIDEO_ANALYSIS_ASR_LANGUAGE 只允许 zh|en|auto")
        return cls(
            metadata_provider=metadata_provider,
            endpoint=endpoint,
            language=language,
            **kwargs,
        )

    def __call__(self, url: str, timeout_s: float) -> Mapping[str, object]:
        metadata = dict(self._metadata_provider(url, timeout_s))
        temp_parent = str(self._temp_root) if self._temp_root is not None else None
        with tempfile.TemporaryDirectory(prefix="video-analysis-douyin-", dir=temp_parent) as tmp:
            tmpdir = Path(tmp)
            output_template = tmpdir / "audio.%(ext)s"
            argv = [
                self._binary,
                "--no-playlist",
                "-f",
                "bestaudio/best",
                "-x",
                "--audio-format",
                "wav",
                "--audio-quality",
                "0",
                "-o",
                str(output_template),
                url,
            ]
            try:
                result = self._runner(
                    argv,
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=False,
                    timeout=timeout_s,
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("Douyin media download timed out") from exc
            if result.returncode != 0:
                raise RuntimeError("Douyin media download failed")
            audio_files = sorted(tmpdir.glob("audio.*"))
            if not audio_files:
                raise RuntimeError("Douyin media download produced no audio")
            text = self._transcribe(audio_files[0], timeout_s)

        metadata["transcript_text"] = text
        metadata["transcript_language"] = self._language
        metadata["transcript_source"] = "h200-asr"
        return metadata

    def _transcribe(self, audio_path: Path, timeout_s: float) -> str:
        language = {
            "zh": "Chinese",
            "en": "English",
            "auto": "auto",
        }.get(self._language, self._language)
        with audio_path.open("rb") as audio:
            try:
                response = self._post(
                    self._endpoint,
                    files={"file": (audio_path.name, audio, "audio/wav")},
                    data={"language": language},
                    timeout=timeout_s,
                )
            except requests.Timeout as exc:
                raise TimeoutError("H200 ASR timed out") from exc
        if response.status_code != 200:
            raise RuntimeError("H200 ASR request failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("H200 ASR returned invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise RuntimeError("H200 ASR returned invalid payload")
        text = str(
            payload.get("text")
            or payload.get("result")
            or payload.get("transcription")
            or ""
        ).strip()
        if not text:
            raise RuntimeError("H200 ASR returned empty transcript")
        return text


__all__ = ["DouyinMediaAsrProvider"]

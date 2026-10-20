from pathlib import Path

import pytest

from fetch_subtitle_auto import resolve_subtitle_cache_dir, subtitle_artifact_path


def test_canonical_cache_env_wins(tmp_path):
    canonical = tmp_path / "canonical"
    legacy = tmp_path / "legacy"
    env = {
        "VIDEO_ANALYSIS_CACHE_DIR": str(canonical),
        "BILI_ANALYSIS_CACHE_DIR": str(legacy),
    }
    assert resolve_subtitle_cache_dir(env) == canonical.resolve()
    assert canonical.is_dir()


def test_legacy_cache_env_warns(tmp_path):
    legacy = tmp_path / "legacy"
    with pytest.warns(DeprecationWarning, match="BILI_ANALYSIS_CACHE_DIR"):
        resolved = resolve_subtitle_cache_dir({"BILI_ANALYSIS_CACHE_DIR": str(legacy)})
    assert resolved == legacy.resolve()


def test_default_cache_is_under_skill_root():
    resolved = resolve_subtitle_cache_dir({})
    assert resolved.name == ".p6r-cache"
    assert resolved.parent.name == "video-analysis-engine"


def test_artifact_path_is_persistent_and_sanitized(tmp_path):
    path = subtitle_artifact_path(
        "BV14fTc6TEi5",
        "subtitle_whisper",
        "txt",
        env={"VIDEO_ANALYSIS_CACHE_DIR": str(tmp_path)},
    )
    assert path == (tmp_path / "BV14fTc6TEi5_subtitle_whisper.txt").resolve()
    with pytest.raises(ValueError, match="invalid BVID"):
        subtitle_artifact_path("../../escape", "subtitle_whisper", "txt", env={})

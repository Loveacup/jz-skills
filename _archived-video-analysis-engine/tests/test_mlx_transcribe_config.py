# -*- coding: utf-8 -*-
"""Regression: mlx helper resolves CLI/env configuration deterministically."""

from argparse import Namespace

import mlx_transcribe


def test_mlx_config_prefers_cli_then_env_then_default():
    args = Namespace(
        model="cli-model",
        model_path=None,
        language=None,
        language_pos=None,
    )
    config = mlx_transcribe.resolve_mlx_asr_config(
        args,
        env={
            "BILI_ASR_MODEL": "env-model",
            "BILI_ASR_MODEL_PATH": "/env/snapshot",
            "BILI_ASR_LANGUAGE": "en",
        },
    )
    assert config.model == "cli-model"
    assert config.model_path == "/env/snapshot"
    assert config.language == "en"


def test_mlx_model_reference_prefers_path_then_model_then_local(monkeypatch):
    config = mlx_transcribe.MlxAsrConfig(
        model="repo/model", model_path="/explicit/snapshot", language="zh"
    )
    assert mlx_transcribe.resolve_model_ref(config) == "/explicit/snapshot"

    config = mlx_transcribe.MlxAsrConfig(
        model="repo/model", model_path=None, language="zh"
    )
    assert mlx_transcribe.resolve_model_ref(config) == "repo/model"

    monkeypatch.setattr(mlx_transcribe, "resolve_local_model", lambda: "/local/snapshot")
    config = mlx_transcribe.MlxAsrConfig(model=None, model_path=None, language="zh")
    assert mlx_transcribe.resolve_model_ref(config) == "/local/snapshot"

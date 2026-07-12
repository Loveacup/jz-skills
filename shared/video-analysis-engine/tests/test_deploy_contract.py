from pathlib import Path
import os
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]
SYNC_ALL = REPO_ROOT / "deploy" / "sync-all.sh"
SYNC_BACK = REPO_ROOT / "deploy" / "sync-back.sh"


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_gitignore_blocks_canonical_private_paths():
    private_paths = (
        "shared/video-analysis-engine/.cookies/bilibili.txt",
        "shared/video-analysis-engine/.p6r-cache/evidence.json",
        "shared/video-analysis-engine/.cache/local.bin",
        "shared/video-analysis-engine/cache/local.bin",
        "shared/video-analysis-engine/__pycache__/module.pyc",
        "shared/video-analysis-engine/.pytest_cache/state",
    )
    for path in private_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, f"private path is not ignored: {path}"


def test_forward_deploy_excludes_private_payload_and_preserves_legacy_assets(tmp_path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    engine = repo / "shared/video-analysis-engine"
    legacy = repo / "shared/bilibili-video-analyzer"

    _write(engine / "SKILL.md", "canonical")
    _write(engine / "scripts/run.py", "public")
    _write(engine / ".cookies/bilibili.txt", "secret")
    _write(engine / ".p6r-cache/evidence.json", "private")
    _write(engine / ".cache/local.bin", "private")
    _write(engine / "cache/local.bin", "private")
    _write(engine / "__pycache__/x.pyc", "private")
    _write(engine / ".pytest_cache/state", "private")
    _write(legacy / "SKILL.md", "shim")

    _write(runtime / "video-analysis-engine/stale.txt", "stale")
    _write(runtime / "bilibili-video-analyzer/scripts/old.py", "keep")
    _write(runtime / "bilibili-video-analyzer/references/old.md", "keep")
    _write(runtime / "bilibili-video-analyzer/.cookies/bilibili.txt", "keep")

    command = (
        f'source "{SYNC_ALL}"; '
        f'REPO_ROOT="{repo}"; '
        f'deploy_video_analysis_family "{runtime}"'
    )
    subprocess.run(["bash", "-c", command], check=True, text=True, capture_output=True)

    assert (runtime / "video-analysis-engine/SKILL.md").read_text() == "canonical"
    assert (runtime / "video-analysis-engine/scripts/run.py").is_file()
    assert not (runtime / "video-analysis-engine/stale.txt").exists()
    for private in (".cookies", ".p6r-cache", ".cache", "cache", "__pycache__", ".pytest_cache"):
        assert not (runtime / "video-analysis-engine" / private).exists()

    assert (runtime / "bilibili-video-analyzer/SKILL.md").read_text() == "shim"
    assert (runtime / "bilibili-video-analyzer/scripts/old.py").is_file()
    assert (runtime / "bilibili-video-analyzer/references/old.md").is_file()
    assert (runtime / "bilibili-video-analyzer/.cookies/bilibili.txt").is_file()


def test_reverse_sync_rejects_repo_owned_engine_without_mutation(tmp_path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    _write(repo / "shared/video-analysis-engine/SKILL.md", "repo-canonical")
    _write(runtime / "video-analysis-engine/SKILL.md", "runtime-drift")
    _write(runtime / "video-analysis-engine/.cookies/bilibili.txt", "secret")
    _write(runtime / "video-analysis-engine/.p6r-cache/evidence.json", "private")

    env = os.environ | {
        "JZ_SKILLS_REPO_ROOT": str(repo),
        "JZ_SKILLS_HERMES_BASE": str(runtime),
    }
    result = subprocess.run(
        [str(SYNC_BACK), "--apply", "--only", "shared/video-analysis-engine"],
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 3
    assert "reverse sync is forbidden" in result.stderr
    assert (repo / "shared/video-analysis-engine/SKILL.md").read_text() == "repo-canonical"
    assert not (repo / "shared/video-analysis-engine/.cookies").exists()
    assert not (repo / "shared/video-analysis-engine/.p6r-cache").exists()


def test_legacy_reverse_sync_updates_only_shim(tmp_path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    _write(repo / "shared/bilibili-video-analyzer/SKILL.md", "old-shim")
    _write(runtime / "bilibili-video-analyzer/SKILL.md", "new-shim")
    _write(runtime / "bilibili-video-analyzer/scripts/old.py", "legacy")
    _write(runtime / "bilibili-video-analyzer/.cookies/bilibili.txt", "secret")

    env = os.environ | {
        "JZ_SKILLS_REPO_ROOT": str(repo),
        "JZ_SKILLS_HERMES_BASE": str(runtime),
    }
    result = subprocess.run(
        [str(SYNC_BACK), "--apply", "--only", "shared/bilibili-video-analyzer"],
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (repo / "shared/bilibili-video-analyzer/SKILL.md").read_text().strip() == "new-shim"
    assert not (repo / "shared/bilibili-video-analyzer/scripts").exists()
    assert not (repo / "shared/bilibili-video-analyzer/.cookies").exists()

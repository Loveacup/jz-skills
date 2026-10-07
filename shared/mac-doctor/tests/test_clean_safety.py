import datetime as dt
import json
import os
import errno
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from macdoctor import clean


@pytest.fixture

def sandbox(tmp_path, monkeypatch):
    home = tmp_path / "home"
    data = tmp_path / "data"
    home.mkdir()
    (home / ".Trash").mkdir()
    data.mkdir()
    monkeypatch.setenv("MAC_DOCTOR_HOME", str(home))
    monkeypatch.setenv("MAC_DOCTOR_DATA_DIR", str(data))
    # Exercise the Trash engine; the shipped default is covered by the kill-switch test.
    monkeypatch.setattr(clean, "CAUTION_APPLY_ENABLED", True)
    return home, data


def success_runner(argv, timeout=15, **kwargs):
    env = kwargs.get("env") or os.environ
    home = Path(env.get("MAC_DOCTOR_HOME", "/tmp"))
    if argv[0] == "du":
        return SimpleNamespace(returncode=0, stdout="1\titem\n", stderr="")
    if argv[0] == "diskutil":
        return SimpleNamespace(returncode=1, stdout="", stderr="unavailable")
    if argv[0] == "lsof":
        return SimpleNamespace(returncode=1, stdout="", stderr="")
    if argv[:3] == ["npm", "config", "get"]:
        return SimpleNamespace(returncode=0, stdout=env.get("npm_config_cache", str(home / ".npm")), stderr="")
    if argv[:3] == ["uv", "cache", "dir"]:
        return SimpleNamespace(returncode=0, stdout=env.get("UV_CACHE_DIR", str(home / ".cache/uv")), stderr="")
    if argv[:4] == ["python3", "-m", "pip", "cache"]:
        return SimpleNamespace(returncode=0, stdout=env.get("PIP_CACHE_DIR", str(home / "Library/Caches/pip")), stderr="")
    if argv[:2] == ["brew", "--cache"]:
        return SimpleNamespace(returncode=0, stdout=str(home / "Library/Caches/Homebrew"), stderr="")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def make_item(home, target_id="npm-cache", path=None, action=None):
    target = next(t for t in clean.load_targets() if t["id"] == target_id)
    item_path = Path(path) if path else Path(target["paths"][0].format(home=home))
    item_path.parent.mkdir(parents=True, exist_ok=True)
    if not item_path.exists():
        item_path.mkdir(parents=True)
    st = item_path.lstat()
    scope = Path(target["scope_path"].format(home=home)).resolve(strict=False) if target.get("scope_path") else None
    file_type = "directory" if os.path.isdir(item_path) else "file"
    return {"target": target_id, "path": str(item_path), "size_bytes": 1024,
            "dev": st.st_dev, "inode": st.st_ino, "mtime": st.st_mtime,
            "file_type": file_type,
            "class": target["class"], "action": action or target["action"],
            "native_cmd": target.get("native_cmd"), "native_env": target.get("native_env", {}),
            "native_scope": str(scope) if scope else None, "inuse_check": target["inuse_check"],
            "min_age_days": target.get("min_age_days", 0), "rebuildable": target["rebuildable"]}

def save_plan(data, item, expires=None, plan_id="plan-test"):
    plan = {"plan_id": plan_id, "host": "test", "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "expires_at": (expires or dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat(),
            "items": [item]}
    dest = clean.paths.plans_dir() / f"{plan_id}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(plan))
    return plan


def receipts(data):
    file = data / "clean-receipts.jsonl"
    return [json.loads(line) for line in file.read_text().splitlines()] if file.exists() else []


def test_catalogue_has_no_never_plan_items_and_safe_requires_native():
    targets = clean.load_targets()
    required = {"id", "title", "class", "paths", "action", "inuse_check", "rebuildable", "why", "restore_note"}
    assert all(required <= t.keys() for t in targets)
    assert all(t["class"] in {"SAFE", "CAUTION", "NEVER", "REPORT"} for t in targets)
    assert all(t["action"] in {"native", "trash", "report"} for t in targets)
    assert all(t["class"] != "SAFE" or (t["action"] == "native" and t.get("native_cmd")) for t in targets)
    assert all(t["class"] != "CAUTION" or t["action"] == "trash" for t in targets)
    assert all(t["class"] != "NEVER" for t in clean.scan(targets=[]))


def test_native_commands_use_the_reviewed_tool_allowlist():
    targets = {t["id"]: t for t in clean.load_targets()}
    approved = {
        "npm-cache": ["npm", "cache", "clean", "--force", "--cache", "{scope}"],
        "uv-cache": ["uv", "cache", "clean"],
        "pip-cache": ["python3", "-m", "pip", "--cache-dir", "{scope}", "cache", "purge"],
    }
    assert {key: targets[key]["native_cmd"] for key in approved} == approved
    brew = targets["brew-cache"]
    assert brew["class"] == "REPORT" and brew["action"] == "report"
    assert brew["dry_run_cmd"] == ["brew", "cleanup", "--dry-run"]



def test_brew_cleanup_is_report_only_and_storage_parses_dry_run(sandbox):
    home, _ = sandbox
    target = next(t for t in clean.load_targets() if t["id"] == "brew-cache")
    output = "Would remove /opt/homebrew/Cellar/foo/1.0 (2.5MB)\nWould remove 3 old files (10KB)\n"
    calls = []
    def runner(argv, timeout=15, **kwargs):
        calls.append((argv, timeout))
        if argv[:2] == ["brew", "--cache"]:
            return SimpleNamespace(returncode=0, stdout=str(home / "Library/Caches/Homebrew"), stderr="")
        if argv[0] == "du":
            return SimpleNamespace(returncode=0, stdout="2\tcache\n", stderr="")
        if argv == ["brew", "cleanup", "--dry-run"]:
            return SimpleNamespace(returncode=0, stdout=output, stderr="")
        return success_runner(argv, timeout=timeout, **kwargs)
    report = clean.scan([target], runner=runner)[0]
    assert report["class"] == "REPORT"
    assert report["size_bytes"] == 2048
    assert report["dry_run_item_count"] == 2
    assert report["dry_run_size_bytes"] == 2_631_680
    assert report["manual_command"] == "brew cleanup"
    assert (["brew", "cleanup", "--dry-run"], clean.COMMAND_TIMEOUT) in calls
    with pytest.raises(ValueError, match="report-only"):
        clean.make_plan(["brew-cache"])


def test_time_machine_snapshots_are_report_only_and_never_planned(sandbox):
    _, _ = sandbox
    target = next(t for t in clean.load_targets() if t["id"] == "tm-local-snapshot")
    runner = lambda *a, **k: SimpleNamespace(returncode=0,
        stdout="Snapshots for disk /:\\ncom.apple.TimeMachine.2026-10-01-123456\\ncom.apple.TimeMachine.2026-10-02-010203\\n",
        stderr="")
    report = clean.scan([target], runner=runner)[0]
    assert report["class"] == "REPORT" and report["count"] == 2
    assert report["estimated_purgeable_bytes"] == "unknown"
    assert report["manual_commands"] == [
        "tmutil deletelocalsnapshots 2026-10-01-123456",
        "tmutil deletelocalsnapshots 2026-10-02-010203"]
    with pytest.raises(ValueError, match="report-only"):
        clean.make_plan(["tm-local-snapshot"])
    plan = clean.make_plan([], runner=success_runner)
    assert not plan["items"]

def test_plan_excludes_never_and_writes_only_selected_targets(sandbox):
    home, _ = sandbox
    cache = home / ".npm/_cacache"
    cache.mkdir(parents=True)
    plan = clean.make_plan(["npm-cache"], runner=success_runner)
    assert plan["items"] and {i["target"] for i in plan["items"]} == {"npm-cache"}
    assert all(i["class"] != "NEVER" for i in plan["items"])
    assert (clean.paths.plans_dir() / f"{plan['plan_id']}.json").exists()


def test_apply_without_yes_refuses(sandbox):
    _, data = sandbox
    result = clean.apply("absent", yes=False)
    assert result["refused"] and result["reason"] == "--yes is required"
    assert not receipts(data)


def test_expired_plan_refuses_without_running_action(sandbox):
    home, data = sandbox
    item = make_item(home)
    save_plan(data, item, dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1))
    ran = []
    result = clean.apply("plan-test", yes=True, runner=lambda *a, **k: ran.append(a))
    assert result["refused"] and not ran and not receipts(data)


def test_changed_fingerprint_refuses(sandbox):
    home, data = sandbox
    item = make_item(home)
    Path(item["path"]).touch()
    save_plan(data, item)
    result = clean.apply("plan-test", yes=True, runner=success_runner)
    assert result["items"][0]["result"] == "refused"
    assert "fingerprint" in result["items"][0]["reason"]


def test_symlink_escaping_declared_root_refuses(sandbox, tmp_path):
    home, data = sandbox
    outside = tmp_path / "outside"
    outside.mkdir()
    link = home / ".npm/_cacache"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)
    st = link.lstat()
    item = make_item(home, path=link)
    save_plan(data, item)
    result = clean.apply("plan-test", yes=True, runner=success_runner)
    assert result["items"][0]["result"] == "refused"
    assert "outside" in result["items"][0]["reason"] or "symlink" in result["items"][0]["reason"]



def test_profile_model_path_does_not_match_any_cache_pattern(sandbox):
    home, data = sandbox
    model = home / ".hermes/profiles/other/home/.cache/qmd"
    model.mkdir(parents=True)
    os.utime(model, (1, 1))
    item = make_item(home, "hermes-profile-dev-cache", path=model)
    save_plan(data, item)
    calls = []
    result = clean.apply("plan-test", allow_caution=True, yes=True,
                         runner=lambda argv, **kw: calls.append(argv) or success_runner(argv, **kw))
    assert result["items"][0]["result"] == "refused"
    assert "pattern" in result["items"][0]["reason"]
    assert not any(argv[0] == "osascript" for argv in calls)


def test_forged_inuse_false_is_rejected_from_catalogue_policy(sandbox):
    home, data = sandbox
    cache = home / ".cache/uv"
    cache.mkdir(parents=True)
    item = make_item(home, "uv-cache")
    item["inuse_check"] = False
    save_plan(data, item)
    dispatched = []
    result = clean.apply("plan-test", yes=True,
                         runner=lambda argv, **kw: dispatched.append(argv) or success_runner(argv, **kw))
    assert result["items"][0]["result"] == "refused"
    assert "policy" in result["items"][0]["reason"]
    assert not any(argv[:2] == ["uv", "cache"] for argv in dispatched)


def test_lsof_permission_diagnostic_is_unknown_not_idle(sandbox):
    home, data = sandbox
    cache = home / ".cache/uv"
    cache.mkdir(parents=True)
    save_plan(data, make_item(home, "uv-cache"))
    dispatched = []
    def runner(argv, timeout=15, **kwargs):
        if argv[:2] == ["lsof", "+D"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="lsof: permission denied")
        dispatched.append(argv)
        return success_runner(argv, timeout=timeout, **kwargs)
    result = clean.apply("plan-test", yes=True, runner=runner)
    assert result["items"][0]["result"] == "refused"
    assert "in-use" in result["items"][0]["reason"]
    assert not any(argv[:2] == ["uv", "cache"] for argv in dispatched)


def test_lsof_idle_exit_after_path_vanishes_is_unknown(sandbox):
    home, data = sandbox
    cache = home / ".cache/uv"
    cache.mkdir(parents=True)
    save_plan(data, make_item(home, "uv-cache"))
    def runner(argv, timeout=15, **kwargs):
        if argv[:2] == ["lsof", "+D"]:
            cache.rmdir()
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        return success_runner(argv, timeout=timeout, **kwargs)
    result = clean.apply("plan-test", yes=True, runner=runner)
    assert result["items"][0]["result"] == "refused"
    assert "in-use" in result["items"][0]["reason"]


def test_native_scope_mismatch_at_apply_refuses_before_dispatch(sandbox):
    home, data = sandbox
    cache = home / ".npm/_cacache"
    cache.mkdir(parents=True)
    save_plan(data, make_item(home))
    dispatched = []
    def runner(argv, timeout=15, **kwargs):
        if argv[:3] == ["npm", "config", "get"]:
            return SimpleNamespace(returncode=0, stdout=str(home / "unapproved-cache"), stderr="")
        dispatched.append(argv)
        return success_runner(argv, timeout=timeout, **kwargs)
    result = clean.apply("plan-test", yes=True, runner=runner)
    assert result["items"][0]["result"] == "refused"
    assert "mismatch" in result["items"][0]["reason"]
    assert not any(argv[:2] == ["npm", "cache"] for argv in dispatched)


def test_trash_fd_walk_rejects_ancestor_symlink_swapped_between_steps(sandbox):
    home, data = sandbox
    derived = home / "Library/Developer/Xcode/DerivedData"
    derived.mkdir(parents=True)
    os.utime(derived, (1, 1))
    (home / "Documents/Xcode/DerivedData").mkdir(parents=True)
    save_plan(data, make_item(home, "xcode-derived-data"))
    library = home / "Library"
    swapped = []
    def hook(index, opened_path):
        if opened_path == library and not swapped:
            library.rename(home / "Library.saved")
            library.symlink_to(home / "Documents", target_is_directory=True)
            swapped.append(True)
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner,
                         trash_walk_hook=hook)
    assert result["items"][-1]["result"] == "refused"
    assert "symlink" in result["items"][-1]["reason"] or "ancestry" in result["items"][-1]["reason"]
    assert not (home / ".Trash" / "DerivedData mac-doctor plan-tes 1").exists()


def test_attempt_receipt_enospc_aborts_before_native_action(sandbox, monkeypatch):
    home, data = sandbox
    (home / ".npm/_cacache").mkdir(parents=True)
    save_plan(data, make_item(home))
    dispatched = []
    def fail_attempt(row):
        if row["phase"] == "attempt":
            raise OSError(28, "No space left on device")
    monkeypatch.setattr(clean, "_append_receipt", fail_attempt)
    result = clean.apply("plan-test", yes=True,
                         runner=lambda argv, **kw: dispatched.append(argv) or success_runner(argv, **kw))
    assert result["refused"] and "aborted" in result["reason"]
    assert not any(argv[:2] == ["npm", "cache"] for argv in dispatched)

def test_hard_deny_path_in_forged_plan_refuses_with_receipt(sandbox):
    home, data = sandbox
    item = make_item(home, path=home / "Library/Keychains")
    save_plan(data, item)
    result = clean.apply("plan-test", yes=True, runner=success_runner)
    assert result["items"][0]["result"] == "refused"
    assert len(receipts(data)) == 1


def test_in_use_item_is_refused(sandbox):
    home, data = sandbox
    target = next(t for t in clean.load_targets() if t["id"] == "uv-cache")
    p = home / ".cache/uv"
    p.mkdir(parents=True)
    item = make_item(home, "uv-cache")
    save_plan(data, item)
    def runner(argv, timeout=15, **kwargs):
        if argv[:2] == ["lsof", "+D"]:
            return SimpleNamespace(returncode=0, stdout="pid\n", stderr="")
        return success_runner(argv, timeout=timeout, **kwargs)
    result = clean.apply("plan-test", yes=True, runner=runner)
    assert result["items"][0]["result"] == "refused"
    assert "in-use" in result["items"][0]["reason"]


def test_lsof_timeout_refuses(sandbox):
    home, data = sandbox
    p = home / ".cache/uv"
    p.mkdir(parents=True)
    save_plan(data, make_item(home, "uv-cache"))
    def runner(argv, timeout=15, **kwargs):
        if argv[:2] == ["lsof", "+D"]:
            raise subprocess.TimeoutExpired(argv, timeout)
        return success_runner(argv, timeout=timeout, **kwargs)
    result = clean.apply("plan-test", yes=True, runner=runner)
    assert result["items"][0]["result"] == "refused"


def test_receipt_log_unwritable_aborts_before_commands(sandbox, monkeypatch, tmp_path):
    home, data = sandbox
    save_plan(data, make_item(home))
    blocked = tmp_path / "directory-is-not-a-file"
    blocked.mkdir()
    monkeypatch.setattr(clean.paths, "receipts_file", lambda: blocked)
    ran = []
    result = clean.apply("plan-test", yes=True, runner=lambda *a, **k: ran.append(a))
    assert result["refused"] and not ran


def test_caution_requires_allow_caution(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    result = clean.apply("plan-test", yes=True, runner=success_runner)
    assert result["items"][0]["result"] == "refused"
    assert result["items"][0]["reason"] == "class not allowed"


def test_caution_apply_disabled_by_default_refuses_without_moving(sandbox, monkeypatch):
    home, data = sandbox
    monkeypatch.setattr(clean, "CAUTION_APPLY_ENABLED", False)
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    result = clean.apply("plan-test", yes=True, allow_caution=True, runner=success_runner)
    assert result["items"][0]["result"] == "refused"
    assert "review-only" in result["items"][0]["reason"]
    assert p.is_dir()
    assert list((home / ".Trash").iterdir()) == []


def test_forged_delete_action_is_refused_and_receipted_without_rm_path(sandbox):
    home, data = sandbox
    save_plan(data, make_item(home, action="delete"))
    calls = []
    result = clean.apply("plan-test", yes=True, runner=lambda argv, **kw: calls.append(argv) or success_runner(argv, **kw))
    assert result["items"][0]["result"] == "refused"
    assert len(receipts(data)) == 1
    assert not any(argv[0] in {"rm", "unlink"} for argv in calls)


def test_unicode_cache_moves_to_account_trash_with_restore_path(sandbox, tmp_path, monkeypatch):
    _, data = sandbox
    home = tmp_path / "用户-中文"
    home.mkdir()
    (home / ".Trash").mkdir()
    monkeypatch.setenv("MAC_DOCTOR_HOME", str(home))
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    outcome = result["items"][-1]
    assert outcome["result"] == "done"
    assert "用户-中文" in outcome["trash_path"]
    assert not p.exists() and Path(outcome["trash_path"]).exists()


def test_trash_collision_uses_next_unique_name(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    collision = home / ".Trash/ms-playwright mac-doctor plan-tes 1"
    collision.mkdir()
    save_plan(data, make_item(home, "playwright-browsers"))
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    outcome = result["items"][-1]
    assert outcome["result"] == "done"
    assert Path(outcome["trash_path"]).name == "ms-playwright mac-doctor plan-tes 2"
    assert collision.is_dir()


def test_cross_volume_trash_rename_is_refused(sandbox, monkeypatch):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    def exdev(*args, **kwargs):
        raise OSError(errno.EXDEV, "cross-device link")
    monkeypatch.setattr(clean, "_renameatx_exclusive", exdev)
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    assert result["items"][-1]["result"] == "refused"
    assert "cross-volume" in result["items"][-1]["reason"]
    assert p.exists()


def test_leaf_swap_after_pin_fails_without_moving_back(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    approved = p.with_name("ms-playwright.approved")
    save_plan(data, make_item(home, "playwright-browsers"))
    swapped = []
    def hook(step, name):
        if step == "before-rename" and not swapped:
            p.rename(approved)
            p.mkdir()
            (p / "marker").write_text("unapproved")
            swapped.append(True)
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner,
                         trash_walk_hook=hook)
    outcome = result["items"][-1]
    assert outcome["result"] == "failed"
    assert outcome["manual_recovery"] is True
    assert outcome["actual_location"] == str(home / ".Trash" / "ms-playwright mac-doctor plan-tes 1")
    assert outcome["approved_object_location"] == str(approved)
    assert (Path(outcome["actual_location"]) / "marker").read_text() == "unapproved"
    assert approved.is_dir()
    assert not p.exists()


def test_pinned_object_mtime_change_fails_without_move_back(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    def hook(step, name):
        if step == "after-rename":
            os.utime(home / ".Trash" / name, (5, 5))
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner,
                         trash_walk_hook=hook)
    outcome = result["items"][-1]
    assert outcome["result"] == "failed"
    assert "pinned source mtime changed" in outcome["reason"]
    assert outcome["manual_recovery"] is True
    assert Path(outcome["actual_location"]).exists()
    assert not p.exists()


def test_trash_collision_uses_next_unique_name(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    collision = home / ".Trash/ms-playwright mac-doctor plan-tes 1"
    collision.mkdir()
    save_plan(data, make_item(home, "playwright-browsers"))
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    outcome = result["items"][-1]
    assert outcome["result"] == "done"
    assert Path(outcome["trash_path"]).name == "ms-playwright mac-doctor plan-tes 2"
    assert collision.is_dir()


def test_destination_replaced_after_move_fails_without_touching_unrelated_data(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    trash = home / ".Trash"
    approved_relocated = trash / "approved-relocated"
    save_plan(data, make_item(home, "playwright-browsers"))
    def hook(step, name):
        if step == "after-rename":
            (trash / name).rename(approved_relocated)
            (trash / name).mkdir()
            (trash / name / "unrelated").write_text("keep")
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner,
                         trash_walk_hook=hook)
    outcome = result["items"][-1]
    assert outcome["result"] == "failed"
    assert outcome["manual_recovery"] is True
    assert outcome["actual_location"] == str(trash / "ms-playwright mac-doctor plan-tes 1")
    assert outcome["approved_object_location"] == str(approved_relocated)
    assert (Path(outcome["actual_location"]) / "unrelated").read_text() == "keep"
    assert approved_relocated.is_dir()


def test_trash_renamed_midrun_reports_real_location(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    saved = home / "Trash.saved"
    save_plan(data, make_item(home, "playwright-browsers"))
    def hook(step, name):
        if step == "after-rename":
            (home / ".Trash").rename(saved)
            (home / ".Trash").mkdir()
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner,
                         trash_walk_hook=hook)
    outcome = result["items"][-1]
    assert outcome["result"] == "failed"
    assert "Trash binding changed" in outcome["reason"]
    assert outcome["trash_path"] == str(saved / "ms-playwright mac-doctor plan-tes 1")
    assert Path(outcome["actual_location"]).exists()


def test_parent_moved_after_move_fails_without_move_back(sandbox):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    parent = p.parent
    saved_parent = parent.with_name("Caches.saved")
    save_plan(data, make_item(home, "playwright-browsers"))
    def hook(step, name):
        if step == "after-rename":
            parent.rename(saved_parent)
            parent.mkdir()
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner,
                         trash_walk_hook=hook)
    outcome = result["items"][-1]
    assert outcome["result"] == "failed"
    assert "source parent binding changed" in outcome["reason"]
    assert outcome["manual_recovery"] is True
    assert Path(outcome["actual_location"]).exists()
    assert not p.exists()


def test_fgetpath_failure_refuses_before_move(sandbox, monkeypatch):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    def fail_path(fd):
        raise OSError(errno.EIO, "F_GETPATH failed")
    monkeypatch.setattr(clean, "_fd_path", fail_path)
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    assert result["items"][-1]["result"] == "refused"
    assert "Trash path lookup failed" in result["items"][-1]["reason"]
    assert p.exists()
    assert list((home / ".Trash").iterdir()) == []


def test_unavailable_exclusive_rename_refuses(sandbox, monkeypatch):
    home, data = sandbox
    p = home / "Library/Caches/ms-playwright"
    p.mkdir(parents=True)
    os.utime(p, (1, 1))
    save_plan(data, make_item(home, "playwright-browsers"))
    def unavailable(*args, **kwargs):
        raise OSError(errno.ENOSYS, "unavailable")
    monkeypatch.setattr(clean, "_renameatx_exclusive", unavailable)
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    assert result["items"][-1]["result"] == "refused"
    assert p.is_dir()
    assert list((home / ".Trash").iterdir()) == []


def test_successful_mutation_has_durable_attempt_and_scoped_command(sandbox):
    home, data = sandbox
    first = make_item(home)
    save_plan(data, first)
    dispatched = []
    result = clean.apply("plan-test", yes=True,
                         runner=lambda argv, **kw: dispatched.append((argv, kw)) or success_runner(argv, **kw))
    rows = receipts(data)
    assert [row["phase"] for row in rows] == ["attempt", "outcome"]
    assert rows[-1]["result"] == "done"
    native_argv, native_kwargs = next(call for call in dispatched
                                      if call[0][0] == "npm" and call[0][1] != "config")
    assert native_argv == ["npm", "cache", "clean", "--force", "--cache", str(home / ".npm")]
    assert native_kwargs["env"]["HOME"] == str(home)
    assert [row["phase"] for row in result["items"]] == ["attempt", "outcome"]


def test_native_scope_mismatch_at_plan_refuses_to_create_plan(sandbox):
    home, _ = sandbox
    (home / ".npm/_cacache").mkdir(parents=True)
    def runner(argv, timeout=15, **kwargs):
        if argv[:3] == ["npm", "config", "get"]:
            return SimpleNamespace(returncode=0, stdout=str(home / "unapproved-cache"), stderr="")
        return success_runner(argv, timeout=timeout, **kwargs)
    with pytest.raises(ValueError, match="native scope refused"):
        clean.make_plan(["npm-cache"], runner=runner)


def test_unknown_scan_size_is_not_zero(sandbox):
    home, _ = sandbox
    p = home / ".npm/_cacache"
    p.mkdir(parents=True)
    record = clean.scan([next(t for t in clean.load_targets() if t["id"] == "npm-cache")],
                        runner=lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="denied"))[0]
    assert record["size_bytes"] == "unknown"


PROFILE_NATIVE_TARGETS = (
    "hermes-regent-uv-cache",
    "hermes-regent-npm-cache",
    "hermes-regent-pip-cache",
    "hermes-cron-worker-pip-cache",
)


@pytest.mark.parametrize("target_id", PROFILE_NATIVE_TARGETS)
def test_profile_native_cleanup_preserves_other_profiles_and_account_cache(sandbox, monkeypatch, target_id):
    home, _ = sandbox
    sentinels = {}
    for cache_id in (*PROFILE_NATIVE_TARGETS, "npm-cache", "uv-cache", "pip-cache"):
        item = make_item(home, cache_id)
        marker = Path(item["path"]) / "payload"
        marker.write_text(cache_id)
        os.utime(item["path"], (1, 1))
        sentinels[cache_id] = marker
    unapproved = home / "unapproved-cache"
    unapproved.mkdir()
    unapproved_marker = unapproved / "payload"
    unapproved_marker.write_text("keep")
    monkeypatch.setenv("HOME", str(home / "redirected-home"))
    for key in ("UV_CACHE_DIR", "PIP_CACHE_DIR", "npm_config_cache"):
        monkeypatch.setenv(key, str(unapproved))

    def runner(argv, timeout=15, **kwargs):
        env = kwargs.get("env") or os.environ
        if argv[:3] == ["uv", "cache", "clean"]:
            scope = Path(env["UV_CACHE_DIR"])
        elif argv[:3] == ["npm", "cache", "clean"]:
            scope = Path(argv[argv.index("--cache") + 1]) / "_cacache"
        elif argv[-2:] == ["cache", "purge"]:
            scope = Path(argv[argv.index("--cache-dir") + 1])
        else:
            return success_runner(argv, timeout=timeout, **kwargs)
        (scope / "payload").unlink()
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    plan = clean.make_plan([target_id], runner=runner)
    result = clean.apply(plan["plan_id"], yes=True, runner=runner)
    assert result["items"][-1]["result"] == "done"
    assert not sentinels[target_id].exists()
    assert {cache_id: marker.read_text() for cache_id, marker in sentinels.items()
            if cache_id != target_id} == {
                cache_id: cache_id for cache_id in sentinels if cache_id != target_id}
    assert unapproved_marker.read_text() == "keep"


@pytest.mark.parametrize("target_id", PROFILE_NATIVE_TARGETS)
@pytest.mark.parametrize("probe", [
    SimpleNamespace(returncode=0, stdout="open handle", stderr=""),
    SimpleNamespace(returncode=1, stdout="", stderr="permission denied"),
])
def test_profile_native_cleanup_refuses_busy_or_unknown_consumers(sandbox, target_id, probe):
    home, data = sandbox
    item = make_item(home, target_id)
    marker = Path(item["path"]) / "payload"
    marker.write_text("keep")
    os.utime(item["path"], (1, 1))
    save_plan(data, make_item(home, target_id))

    def runner(argv, timeout=15, **kwargs):
        if argv[:2] == ["lsof", "+D"]:
            return probe
        return success_runner(argv, timeout=timeout, **kwargs)

    result = clean.apply("plan-test", yes=True, runner=runner)
    assert result["items"][-1]["result"] == "refused"
    assert "in-use" in result["items"][-1]["reason"]
    assert [row["phase"] for row in receipts(data)] == ["outcome"]
    assert marker.read_text() == "keep"


@pytest.mark.parametrize("target_id", PROFILE_NATIVE_TARGETS)
def test_profile_native_cleanup_rejects_forged_other_profile_scope(sandbox, target_id):
    home, data = sandbox
    target = next(t for t in clean.load_targets() if t["id"] == target_id)
    other = home / ".hermes/profiles/other/home" / Path(
        target["paths"][0].split("/home/", 1)[1])
    item = make_item(home, target_id, path=other)
    marker = other / "payload"
    marker.write_text("keep")
    os.utime(other, (1, 1))
    item = make_item(home, target_id, path=other)
    item["native_scope"] = str(other.parent if target_id.endswith("npm-cache") else other)
    save_plan(data, item)
    result = clean.apply("plan-test", yes=True, runner=success_runner)
    assert result["items"][-1]["result"] == "refused"
    assert "pattern" in result["items"][-1]["reason"]
    assert marker.read_text() == "keep"


@pytest.mark.parametrize("target_id", PROFILE_NATIVE_TARGETS)
def test_profile_native_path_cannot_use_legacy_caution_action(sandbox, target_id):
    home, data = sandbox
    native_item = make_item(home, target_id)
    path = Path(native_item["path"])
    marker = path / "payload"
    marker.write_text("keep")
    os.utime(path, (1, 1))
    legacy_item = make_item(home, "hermes-profile-dev-cache", path=path)
    save_plan(data, legacy_item)
    result = clean.apply("plan-test", allow_caution=True, yes=True, runner=success_runner)
    assert result["items"][-1]["result"] == "refused"
    assert "pattern" in result["items"][-1]["reason"]
    assert marker.read_text() == "keep"


def expired_native_plan(home, data, target_ids=("npm-cache",), runner=success_runner):
    for target_id in target_ids:
        target = next(t for t in clean.load_targets() if t["id"] == target_id)
        path = Path(target["paths"][0].format(home=home))
        path.mkdir(parents=True, exist_ok=True)
    plan = clean.make_plan(list(target_ids), runner=runner)
    plan["expires_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)).isoformat()
    plan_path = clean.paths.plans_dir() / f"{plan['plan_id']}.json"
    plan_path.write_text(json.dumps(plan))
    return plan, plan_path.read_bytes()


def test_expired_unchanged_plan_renews_and_dispatches_fresh_plan(sandbox):
    home, data = sandbox
    approved, original_bytes = expired_native_plan(home, data)
    dispatched = []
    def runner(argv, **kwargs):
        if argv[:2] == ["npm", "cache"] and argv[1] == "cache":
            dispatched.append(argv)
        return success_runner(argv, **kwargs)

    result = clean.apply(approved["plan_id"], yes=True, renew_if_unchanged=True, runner=runner)
    fresh_id = result["plan_id"]
    assert not result["refused"]
    assert fresh_id != approved["plan_id"]
    assert result["approved_plan_id"] == approved["plan_id"]
    assert result["renewed_from"] == approved["plan_id"]
    assert dispatched == [["npm", "cache", "clean", "--force", "--cache", str(home / ".npm")]]
    original_path = clean.paths.plans_dir() / f"{approved['plan_id']}.json"
    assert original_path.read_bytes() == original_bytes
    fresh = json.loads((clean.paths.plans_dir() / f"{fresh_id}.json").read_text())
    assert fresh["expires_at"] > dt.datetime.now(dt.timezone.utc).isoformat()
    assert (dt.datetime.fromisoformat(fresh["expires_at"])
            - dt.datetime.fromisoformat(fresh["created_at"])) == clean.PLAN_TTL
    rows = receipts(data)
    assert rows and all(row["plan_id"] == fresh_id for row in rows)
    assert all(row["approved_plan_id"] == approved["plan_id"]
               and row["renewed_from"] == approved["plan_id"] for row in rows)


def test_expired_plan_default_still_refuses_without_dispatch(sandbox):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data)
    dispatched = []
    result = clean.apply(plan["plan_id"], yes=True, runner=lambda argv, **kwargs:
                         dispatched.append(argv) or success_runner(argv, **kwargs))
    assert result["refused"] and result["reason"] == "plan expired"
    assert not dispatched and not receipts(data)


def test_expired_renewal_still_requires_yes(sandbox):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data)
    dispatched = []
    result = clean.apply(plan["plan_id"], renew_if_unchanged=True,
                         runner=lambda argv, **kwargs: dispatched.append(argv))
    assert result["refused"] and result["reason"] == "--yes is required"
    assert not dispatched and not receipts(data)


@pytest.mark.parametrize("drift", ["inode", "size", "native_env", "policy", "unknown_key"])
def test_expired_renewal_rejects_item_manifest_drift(sandbox, drift):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data)
    item = plan["items"][0]
    if drift == "inode":
        item["inode"] += 1
    elif drift == "size":
        item["size_bytes"] += 1
    elif drift == "native_env":
        item["native_env"] = {"npm_config_cache": "/unapproved"}
    elif drift == "policy":
        item["native_cmd"] = ["npm", "cache", "clean"]
    else:
        item["future_policy_key"] = "must compare"
    path = clean.paths.plans_dir() / f"{plan['plan_id']}.json"
    path.write_text(json.dumps(plan))
    dispatched = []
    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True,
                         runner=lambda argv, **kwargs: dispatched.append(argv)
                         or success_runner(argv, **kwargs))
    assert result["refused"] and "manifest changed" in result["reason"]
    assert not any(argv[:2] == ["npm", "cache"] for argv in dispatched)


@pytest.mark.parametrize("change", ["remove", "add"])
def test_expired_renewal_rejects_added_or_removed_items(sandbox, change):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data, ("npm-cache", "uv-cache"))
    if change == "remove":
        plan["items"].pop()
    else:
        extra = make_item(home, "pip-cache")
        plan["items"].append(extra)
    (clean.paths.plans_dir() / f"{plan['plan_id']}.json").write_text(json.dumps(plan))
    dispatched = []
    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True,
                         runner=lambda argv, **kwargs: dispatched.append(argv)
                         or success_runner(argv, **kwargs))
    assert result["refused"]
    assert not any(argv[:3] in (["npm", "cache", "clean"], ["uv", "cache", "clean"])
                   or (argv[:4] == ["python3", "-m", "pip", "--cache-dir"]
                       and argv[-2:] == ["cache", "purge"]) for argv in dispatched)


def test_expired_renewal_rejects_host_mismatch(sandbox):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data)
    plan["host"] = "different-host"
    (clean.paths.plans_dir() / f"{plan['plan_id']}.json").write_text(json.dumps(plan))
    dispatched = []
    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True,
                         runner=lambda argv, **kwargs: dispatched.append(argv))
    assert result["refused"] and "SAFE/native" in result["reason"]
    assert not dispatched


@pytest.mark.parametrize("manifest", ["empty", "caution", "protected", "report"])
def test_expired_renewal_rejects_ineligible_manifest(sandbox, manifest):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data)
    if manifest == "empty":
        plan["items"] = []
    elif manifest == "caution":
        plan["items"][0].update({"class": "CAUTION", "action": "trash"})
    elif manifest == "protected":
        plan["items"][0]["class"] = "NEVER"
    else:
        plan["items"][0].update({"class": "REPORT", "action": "report"})
    (clean.paths.plans_dir() / f"{plan['plan_id']}.json").write_text(json.dumps(plan))
    dispatched = []
    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True,
                         runner=lambda argv, **kwargs: dispatched.append(argv))
    assert result["refused"] and not dispatched


@pytest.mark.parametrize("occupancy", ["occupied", "unknown"])
def test_expired_renewal_preserves_occupancy_guards(sandbox, occupancy):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data, ("uv-cache",))
    dispatched = []
    def runner(argv, **kwargs):
        if argv[0] == "lsof":
            return SimpleNamespace(returncode=0 if occupancy == "occupied" else 2,
                                   stdout="", stderr="busy" if occupancy == "occupied" else "permission denied")
        if argv[:2] == ["uv", "cache"] and argv[-1:] == ["clean"]:
            dispatched.append(argv)
        return success_runner(argv, **kwargs)

    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True, runner=runner)
    assert result["refused"] and result["items"][-1]["result"] == "refused"
    assert not dispatched


def test_expired_renewal_refuses_when_native_resolver_fails(sandbox):
    home, data = sandbox
    plan, _ = expired_native_plan(home, data)
    dispatched = []
    def runner(argv, **kwargs):
        if argv[:3] == ["npm", "config", "get"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="resolver failed")
        dispatched.append(argv)
        return success_runner(argv, **kwargs)

    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True, runner=runner)
    assert result["refused"] and "resolver failed" in result["reason"]
    assert not any(argv[:3] == ["npm", "cache", "clean"] for argv in dispatched)


@pytest.mark.parametrize("unknown_stage", ["approved", "fresh", "both"])
def test_expired_renewal_refuses_unknown_scan_sizes(sandbox, unknown_stage):
    home, data = sandbox
    dispatched = []
    def unknown_size_runner(argv, **kwargs):
        if argv[0] == "du":
            return SimpleNamespace(returncode=1, stdout="", stderr="size unavailable")
        if argv[:3] == ["npm", "cache", "clean"]:
            dispatched.append(argv)
        return success_runner(argv, **kwargs)
    planner = unknown_size_runner if unknown_stage in {"approved", "both"} else success_runner
    plan, _ = expired_native_plan(home, data, runner=planner)
    runner = unknown_size_runner if unknown_stage in {"fresh", "both"} else success_runner
    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=True, runner=runner)
    assert result["refused"] and "scan size is unknown" in result["reason"]
    assert result["items"] == [] and not dispatched and not receipts(data)


@pytest.mark.parametrize("renew", [False, True])
def test_native_receipts_conform_to_declared_fields(sandbox, renew):
    home, data = sandbox
    if renew:
        plan, _ = expired_native_plan(home, data)
    else:
        make_item(home)
        plan = clean.make_plan(["npm-cache"], runner=success_runner)
    result = clean.apply(plan["plan_id"], yes=True, renew_if_unchanged=renew,
                         runner=success_runner)
    assert not result["refused"]
    schema = json.loads((Path(__file__).parents[1] / "schema/clean-receipt.schema.json").read_text())
    for row in receipts(data):
        assert set(schema["required"]) <= row.keys()
        assert row.keys() <= schema["properties"].keys()
        if renew:
            for field in ("approved_plan_id", "renewed_from"):
                assert schema["properties"][field]["type"] == "string"
                assert row[field] == plan["plan_id"]

#!/usr/bin/env python3
"""Validate and resolve call-omp capability grants.

This is a mechanism adapter, not an authorization issuer.  A missing grant keeps
legacy read-only behavior.  A present v1 grant is accepted only for execute
packages and is mapped exactly; malformed grants fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

CONTRACT = "call-omp.capability-grant.v1"
LEGACY_TOOLS = ["read", "grep", "glob", "lsp", "web_search"]
KNOWN_TOOLS = {
    "read",
    "grep",
    "glob",
    "lsp",
    "web_search",
    "write",
    "edit",
    "bash",
    "python",
    "notebook",
    "browser",
    "computer",
    "task",
    "todo",
    "ask",
}
HOST_AFFECTING = {
    "write",
    "edit",
    "bash",
    "python",
    "notebook",
    "browser",
    "computer",
    "task",
}
GRANT_KEYS = {"contract", "tools", "approval", "cwd", "add_dirs"}


def emit(payload: dict[str, Any], rc: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(rc)


def reject(code: str, reason: str) -> None:
    emit({"ok": False, "code": code, "reason": reason}, 1)


def load_package(path: Path, state: bool) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        reject("package_unreadable", "cannot read a valid JSON package")
    if state:
        data = data.get("package") if isinstance(data, dict) else None
    if not isinstance(data, dict):
        reject("package_invalid", "package must be a JSON object")
    return data


def canonical_dir(value: str, field: str) -> str:
    if not os.path.isabs(value):
        reject("path_not_absolute", f"{field} must be absolute")
    resolved = os.path.realpath(value)
    if not os.path.isdir(resolved):
        reject("path_not_directory", f"{field} must resolve to an existing directory")
    return resolved


def path_covered(target: str, roots: list[str]) -> bool:
    for root in roots:
        try:
            if os.path.commonpath([target, root]) == root:
                return True
        except ValueError:
            continue
    return False


def fingerprint(spec: dict[str, Any]) -> str:
    raw = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate(package: dict[str, Any], phase: str) -> dict[str, Any]:
    grant_present = "capability_grant" in package
    grant = package.get("capability_grant")
    scope = package.get("scope") if isinstance(package.get("scope"), dict) else {}
    if not grant_present:
        spec = {
            "present": False,
            "contract": "legacy-readonly",
            "tools": LEGACY_TOOLS,
            "approval": "legacy_auto_approve",
            "cwd": scope.get("cwd") if isinstance(scope.get("cwd"), str) else "",
            "add_dirs": [],
            "host_affecting": False,
        }
        spec["fingerprint"] = fingerprint(spec)
        return spec

    if not isinstance(grant, dict):
        reject("grant_not_object", "capability_grant must be an object")
    if package.get("mode") != "execute":
        reject("grant_mode_forbidden", "capability_grant is accepted only for mode=execute")
    independence = (
        package.get("auditor", {}).get("independence_level")
        if isinstance(package.get("auditor"), dict)
        else None
    )
    if independence == "bundle_only":
        reject("grant_bundle_only_forbidden", "bundle_only cannot carry capability_grant")
    if package.get("channel", "shell") != "shell":
        reject(
            "grant_channel_unsupported",
            "capability_grant v1 requires channel=shell; RPC lacks a trustworthy per-attempt exit code and ACP does not preserve grants",
        )

    unknown = sorted(set(grant) - GRANT_KEYS)
    if unknown:
        reject("grant_unknown_fields", "unknown capability_grant fields: " + ",".join(unknown))
    if grant.get("contract") != CONTRACT:
        reject("grant_contract_invalid", f"contract must equal {CONTRACT}")

    tools = grant.get("tools")
    if not isinstance(tools, list) or not tools:
        reject("grant_tools_invalid", "tools must be a non-empty array")
    if any(not isinstance(tool, str) or not tool for tool in tools):
        reject("grant_tools_invalid", "every tool must be a non-empty string")
    if len(set(tools)) != len(tools):
        reject("grant_tools_duplicate", "tools must not contain duplicates")
    unknown_tools = sorted(set(tools) - KNOWN_TOOLS)
    if unknown_tools:
        reject("grant_tools_unknown", "unknown tools: " + ",".join(unknown_tools))

    if grant.get("approval") != "non_interactive":
        reject("grant_approval_invalid", "approval must equal non_interactive")
    cwd = grant.get("cwd", "")
    if not isinstance(cwd, str):
        reject("grant_cwd_invalid", "cwd must be a string")
    add_dirs = grant.get("add_dirs", [])
    if not isinstance(add_dirs, list) or any(not isinstance(p, str) or not p for p in add_dirs):
        reject("grant_add_dirs_invalid", "add_dirs must be an array of non-empty strings")
    if len(set(add_dirs)) != len(add_dirs):
        reject("grant_add_dirs_duplicate", "add_dirs must not contain duplicates")

    host_affecting = bool(set(tools) & HOST_AFFECTING)
    if not cwd:
        reject("grant_cwd_required", "every capability grant requires an explicit cwd")

    if phase == "launch":
        resolved_cwd = canonical_dir(cwd, "capability_grant.cwd") if cwd else ""
        resolved_add_dirs = [canonical_dir(p, "capability_grant.add_dirs[]") for p in add_dirs]

        scope_cwd = scope.get("cwd", "")
        if "cwd" in scope:
            if not isinstance(scope_cwd, str) or not scope_cwd:
                reject("scope_cwd_invalid", "scope.cwd must be a non-empty string when present")
            if canonical_dir(scope_cwd, "scope.cwd") != resolved_cwd:
                reject("scope_cwd_mismatch", "scope.cwd must equal capability_grant.cwd after canonicalization")

        allowed = scope.get("allowed_paths", [])
        denied = scope.get("denied_paths", [])
        if not isinstance(allowed, list) or any(not isinstance(p, str) or not p for p in allowed):
            reject("scope_allowed_invalid", "scope.allowed_paths must be an array of non-empty strings")
        if not isinstance(denied, list):
            reject("scope_denied_invalid", "scope.denied_paths must be an array")
        if denied:
            reject(
                "scope_denied_unenforceable",
                "capability grants require empty denied_paths; call-omp does not provide a path sandbox",
            )
        resolved_allowed = [canonical_dir(p, "scope.allowed_paths[]") for p in allowed]
        targets = ([resolved_cwd] if resolved_cwd else []) + resolved_add_dirs
        if targets and (not resolved_allowed or any(not path_covered(t, resolved_allowed) for t in targets)):
            reject("scope_not_covering_grant", "scope.allowed_paths must cover cwd and every add_dir")
        cwd, add_dirs = resolved_cwd, resolved_add_dirs

    spec = {
        "present": True,
        "contract": CONTRACT,
        "tools": tools,
        "approval": "non_interactive",
        "cwd": cwd,
        "add_dirs": add_dirs,
        "host_affecting": host_affecting,
    }
    spec["fingerprint"] = fingerprint(spec)
    return spec


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file")
    source.add_argument("--state")
    parser.add_argument("--phase", choices=("structure", "launch"), required=True)
    args = parser.parse_args()
    path = Path(args.file or args.state)
    package = load_package(path, state=bool(args.state))
    emit({"ok": True, "resolved": validate(package, args.phase)})


if __name__ == "__main__":
    main()

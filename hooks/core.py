#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROTECTED_MARKERS = ("/secrets/", "/.local/share/opencode-search/", "/GoogleDrive/", "/OneDrive/")
UNGATED_MARKERS = ("/.claude/", "/.codex/", "/.agents/skills/", "/.local/state/agent-engineering-standard/")
VERIFICATION_MARKER = "agent_engineering_standard_verified=1"
VERIFICATION_COMMAND_RE = re.compile(r"(?:check|doctor|json\.tool|lint|test|verify)")
MUTATING_BASH_PATTERNS = (
    " >",
    ">>",
    "| tee",
    "tee ",
    "sed -i",
    "perl -pi",
    "touch ",
    "truncate ",
    "cp ",
    "mv ",
    "rm ",
)
SOURCE_PATH_RE = re.compile(
    r"(?P<path>(?:\./|/)?[\w./-]+\.(?:py|js|jsx|ts|tsx|json|md|txt|yaml|yml|toml|sh|bash|zsh|ini|cfg|conf|html|css|go|rs|java|kt|c|h|cpp|hpp|rb|php|swift|sql|xml))"
)
SNAPSHOT_RETENTION_SECONDS = 7 * 24 * 60 * 60


@dataclass
class PatchStats:
    path: str
    is_new_file: bool
    added: int
    removed: int


def emit_json(payload: dict) -> int:
    print(json.dumps(payload))
    return 0


def read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def line_count(text: str) -> int:
    return 0 if not text else len(text.splitlines())


def patch_stats(command: str) -> list[PatchStats]:
    stats: list[PatchStats] = []
    current: PatchStats | None = None
    for line in command.splitlines():
        if line.startswith("*** Add File: "):
            if current:
                stats.append(current)
            current = PatchStats(path=line.removeprefix("*** Add File: ").strip(), is_new_file=True, added=0, removed=0)
            continue
        if line.startswith("*** Update File: "):
            if current:
                stats.append(current)
            current = PatchStats(path=line.removeprefix("*** Update File: ").strip(), is_new_file=False, added=0, removed=0)
            continue
        if line.startswith("*** Delete File: "):
            if current:
                stats.append(current)
            current = PatchStats(path=line.removeprefix("*** Delete File: ").strip(), is_new_file=False, added=0, removed=0)
            stats.append(current)
            current = None
            continue
        if line.startswith("*** Move to: ") and current:
            current.path = line.removeprefix("*** Move to: ").strip()
            continue
        if not current:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current.added += 1
            continue
        if line.startswith("-") and not line.startswith("---"):
            current.removed += 1
    if current:
        stats.append(current)
    return stats


def resolved_path(cwd: str | None, path: str) -> Path:
    base = Path(cwd) if cwd else Path.cwd()
    return Path(path) if path.startswith("/") else base / path


def snapshot_meta_dir(state_dir: Path) -> Path:
    return state_dir / "apply-patch-snapshots"


def session_baseline_key(payload: dict) -> str:
    return payload.get("session_id") or payload.get("cwd") or "default"


def snapshot_meta_path(state_dir: Path, baseline_key: str) -> Path:
    return snapshot_meta_dir(state_dir) / f"{baseline_key}.json"


def load_snapshot_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {"entries": {}}
    try:
        data = json.loads(meta_path.read_text())
    except Exception:
        return {"entries": {}}
    return data if isinstance(data.get("entries"), dict) else {"entries": {}}


def save_snapshot_meta(meta_path: Path, data: dict) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = meta_path.with_suffix(meta_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(meta_path)


def write_snapshot(state_dir: Path, payload: dict) -> None:
    if payload.get("tool_name") != "apply_patch":
        return
    baseline_key = session_baseline_key(payload)
    meta_path = snapshot_meta_path(state_dir, baseline_key)
    data = load_snapshot_meta(meta_path)
    cwd = payload.get("cwd")
    changed = False
    for stat in patch_stats(payload.get("tool_input", {}).get("command") or ""):
        if stat.path in data["entries"]:
            continue
        abs_path = resolved_path(cwd, stat.path)
        entry = {"path": stat.path, "abs_path": str(abs_path), "existed": abs_path.exists(), "snapshot": None}
        if abs_path.exists() and abs_path.is_file():
            entry["snapshot"] = f"{baseline_key}-{len(data['entries'])}.bin"
            snapshot_path = snapshot_meta_dir(state_dir) / entry["snapshot"]
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_bytes(abs_path.read_bytes())
        data["entries"][stat.path] = entry
        changed = True
    if changed:
        save_snapshot_meta(meta_path, data)


def restore_snapshot_entry(state_dir: Path, entry: dict) -> None:
    abs_path = Path(entry["abs_path"])
    if entry["existed"]:
        snapshot_path = snapshot_meta_dir(state_dir) / entry["snapshot"]
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(snapshot_path.read_bytes())
        return
    if abs_path.exists() and abs_path.is_file():
        abs_path.unlink()


def cleanup_snapshot(state_dir: Path, baseline_key: str, *, paths: list[str] | None = None) -> None:
    meta_path = snapshot_meta_path(state_dir, baseline_key)
    if not meta_path.exists():
        return
    data = load_snapshot_meta(meta_path)
    entries = data.get("entries", {})
    selected = list(entries) if paths is None else [path for path in paths if path in entries]
    for path in selected:
        snapshot = entries[path].get("snapshot")
        if snapshot:
            (snapshot_meta_dir(state_dir) / snapshot).unlink(missing_ok=True)
        entries.pop(path, None)
    if entries:
        save_snapshot_meta(meta_path, {"entries": entries})
    else:
        meta_path.unlink(missing_ok=True)


def cleanup_stale_snapshots(state_dir: Path, *, max_age_seconds: int = SNAPSHOT_RETENTION_SECONDS) -> None:
    root = snapshot_meta_dir(state_dir)
    if not root.exists():
        return
    cutoff = time.time() - max_age_seconds
    for path in root.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def line_count_bytes(data: bytes) -> int:
    return line_count(data.decode("utf-8", errors="replace"))


def enforce_post_apply_patch(payload: dict, state_dir: Path) -> str:
    if payload.get("tool_name") != "apply_patch":
        return ""
    baseline_key = session_baseline_key(payload)
    meta_path = snapshot_meta_path(state_dir, baseline_key)
    if not meta_path.exists():
        return ""
    entries = load_snapshot_meta(meta_path).get("entries", {})
    touched = []
    for stat in patch_stats(payload.get("tool_input", {}).get("command") or ""):
        if stat.path not in touched:
            touched.append(stat.path)
    violations = []
    for path in touched:
        entry = entries.get(path)
        if not entry or any(marker in path for marker in UNGATED_MARKERS):
            continue
        abs_path = Path(entry["abs_path"])
        current_exists = abs_path.exists() and abs_path.is_file()
        current_lines = line_count_bytes(abs_path.read_bytes()) if current_exists else 0
        if not entry["existed"] and current_exists and current_lines > 150:
            restore_snapshot_entry(state_dir, entry)
            violations.append(f"{path}: new file has {current_lines} lines, exceeds 150")
            continue
        snapshot = entry.get("snapshot")
        if entry["existed"] and snapshot:
            original = line_count_bytes((snapshot_meta_dir(state_dir) / snapshot).read_bytes())
            net = current_lines - original
            if net > 40:
                restore_snapshot_entry(state_dir, entry)
                violations.append(f"{path}: net change is +{net} lines, exceeds 40")
    if violations:
        cleanup_snapshot(state_dir, baseline_key, paths=touched)
    return "" if not violations else "Reverted oversized edit: " + "; ".join(violations) + ". Use a smaller change."


def evaluate_edit_guard(payload: dict) -> tuple[bool, str]:
    tool_input = payload.get("tool_input", {})
    tool_name = payload.get("tool_name", "")
    if tool_name == "apply_patch":
        command = tool_input.get("command") or ""
        for stat in patch_stats(command):
            if any(marker in stat.path for marker in UNGATED_MARKERS):
                continue
            if any(marker in stat.path for marker in PROTECTED_MARKERS) or stat.path.endswith(".env"):
                return False, f"Protected path: {stat.path}"
            net = stat.added - stat.removed
            if stat.is_new_file and stat.added > 150:
                return False, f"New file too large: {stat.added} lines exceeds 150."
            if not stat.is_new_file and net > 40:
                return False, f"Diff too large: +{net} net lines exceeds 40."
        return True, ""
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or ""
    if any(marker in file_path for marker in UNGATED_MARKERS):
        return True, ""
    if any(marker in file_path for marker in PROTECTED_MARKERS) or file_path.endswith(".env"):
        return False, f"Protected path: {file_path}"
    if tool_name == "MultiEdit":
        new_text = "\n".join(edit.get("new_string", "") for edit in tool_input.get("edits", []))
        old_text = "\n".join(edit.get("old_string", "") for edit in tool_input.get("edits", []))
    elif tool_name == "NotebookEdit":
        new_text = tool_input.get("new_source", "")
        old_text = tool_input.get("old_source", "")
    else:
        new_text = tool_input.get("new_string") or tool_input.get("content") or ""
        old_text = tool_input.get("old_string", "")
    abs_path = Path(file_path) if file_path.startswith("/") else Path.cwd() / file_path
    is_new_file = not abs_path.exists()
    added = line_count(new_text)
    removed = line_count(old_text)
    net = added - removed
    if is_new_file and added > 150:
        return False, f"New file too large: {added} lines exceeds 150."
    if not is_new_file and net > 40:
        return False, f"Diff too large: +{net} net lines exceeds 40."
    return True, ""


def pre_tool_use_main() -> int:
    payload = read_payload()
    if not payload:
        return emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Hook input was not valid JSON.",
                }
            }
        )
    write_snapshot(Path.home() / ".local" / "state" / "agent-engineering-standard", payload)
    allowed, reason = evaluate_edit_guard(payload)
    if allowed:
        return 0
    return emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def evaluate_bash_guard(payload: dict) -> tuple[bool, str]:
    tool_input = payload.get("tool_input", {})
    command = (tool_input.get("command") or tool_input.get("cmd") or tool_input.get("input") or "").strip()
    lowered = command.lower()
    if not command or VERIFICATION_MARKER in lowered:
        return True, ""
    if not any(pattern in lowered for pattern in MUTATING_BASH_PATTERNS):
        return True, ""
    match = SOURCE_PATH_RE.search(command)
    if not match:
        return True, ""
    path = match.group("path")
    if any(marker in path for marker in UNGATED_MARKERS):
        return True, ""
    return False, f"Shell-based file mutation is not allowed for {path}. Use Edit/Write/apply_patch so policy hooks can inspect the change."


def pre_bash_main() -> int:
    payload = read_payload()
    if not payload:
        return emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Hook input was not valid JSON.",
                }
            }
        )
    allowed, reason = evaluate_bash_guard(payload)
    if allowed:
        return 0
    return emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def load_state(load_json_fn, state_file: Path) -> dict:
    default = {
        "pending_verification": False,
        "last_edit_at": None,
        "last_verified_command": None,
        "session_id": None,
        "cwd": None,
    }
    try:
        return load_json_fn(state_file, default)
    except Exception:
        return dict(default)


def apply_scope(data: dict, payload: dict) -> None:
    session_id = payload.get("session_id")
    cwd = payload.get("cwd")
    if session_id:
        data["session_id"] = session_id
    if cwd:
        data["cwd"] = cwd


def save_state(state_dir: Path, state_file: Path, dump_json_fn, data: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_name(f".{state_file.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(dump_json_fn(data))
    tmp.replace(state_file)


def mark_edit(state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    payload = read_payload()
    return mark_edit_payload(payload, state_dir=state_dir, state_file=state_file, load_json_fn=load_json_fn, dump_json_fn=dump_json_fn)


def mark_edit_payload(payload: dict, *, state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    data = load_state(load_json_fn, state_file)
    apply_scope(data, payload)
    data["pending_verification"] = True
    data["last_edit_at"] = int(time.time())
    save_state(state_dir, state_file, dump_json_fn, data)
    print("{}")
    return 0


def inspect_bash(state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    payload = read_payload()
    tool_input = payload.get("tool_input", {})
    command = tool_input.get("command") or tool_input.get("cmd") or tool_input.get("input") or ""
    data = load_state(load_json_fn, state_file)
    apply_scope(data, payload)
    if bash_verification_passed(command, payload.get("tool_response")):
        data["pending_verification"] = False
        data["last_verified_command"] = command
        data["last_verified_at"] = int(time.time())
        cleanup_snapshot(state_dir, session_baseline_key(payload))
        cleanup_stale_snapshots(state_dir)
    save_state(state_dir, state_file, dump_json_fn, data)
    print("{}")
    return 0


def bash_verification_passed(command: str, response) -> bool:
    lowered = command.lower()
    if VERIFICATION_MARKER in lowered:
        return True
    if not VERIFICATION_COMMAND_RE.search(lowered):
        return False
    return response_succeeded(response)


def response_succeeded(response) -> bool:
    if isinstance(response, dict):
        for key in ("exit_code", "exitCode", "returncode", "return_code"):
            if response.get(key) == 0:
                return True
        return any(response_succeeded(value) for value in response.values())
    if isinstance(response, list):
        return any(response_succeeded(value) for value in response)
    if isinstance(response, str):
        return re.search(r"(?im)^(?:process )?exited with code 0$", response) is not None
    return False


def verification_state_main(argv: list[str], *, state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    if len(argv) < 2:
        raise SystemExit("usage: verification_state.py mark-edit|inspect-bash")
    if argv[1] == "mark-edit":
        return mark_edit(state_dir, state_file, load_json_fn, dump_json_fn)
    if argv[1] == "inspect-bash":
        return inspect_bash(state_dir, state_file, load_json_fn, dump_json_fn)
    raise SystemExit(f"unknown command: {argv[1]}")


def post_edit_main(*, state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    payload = read_payload()
    violation = enforce_post_apply_patch(payload, state_dir)
    if violation:
        return emit_json({"decision": "block", "reason": violation})
    return mark_edit_payload(payload, state_dir=state_dir, state_file=state_file, load_json_fn=load_json_fn, dump_json_fn=dump_json_fn)


def scope_matches(data: dict, payload: dict) -> bool:
    stored_session = data.get("session_id")
    current_session = payload.get("session_id")
    if stored_session and current_session:
        return stored_session == current_session
    stored_cwd = data.get("cwd")
    current_cwd = payload.get("cwd")
    if stored_cwd and current_cwd:
        return stored_cwd == current_cwd
    return True


def stop_verify_main(*, agent: str, state_file: Path, load_json_fn) -> int:
    payload = read_payload()
    data = load_json_fn(state_file, {"pending_verification": False})
    if not data.get("pending_verification"):
        if agent == "claude":
            print("{}")
        return 0
    if not scope_matches(data, payload):
        if agent == "claude":
            print("{}")
        return 0
    message = f"Verification is still pending for the last edit. Run a relevant check before claiming completion ({agent})."
    if agent == "codex":
        return emit_json({"decision": "block", "reason": message})
    return emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": message,
            }
        }
    )

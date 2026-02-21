#!/usr/bin/env python3
"""Shared helpers for workflow guard hooks."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WORKFLOW_MARKER = ".workflow-active"
PROJECT_MARKER = "PROJECT.md"
DEFAULT_TTL_HOURS = 4
MUTATING_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
BOOTSTRAP_EXEMPT_REL_PATHS = {
    ".claude/hooks/workflow-gate.py",
    ".claude/hooks/workflow-session-check.py",
    ".claude/hooks/workflow-activate.py",
}


def setup_utf8_stdio() -> None:
    """Avoid Windows GBK crashes when printing symbols or UTF-8 text."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            except Exception:
                pass


def parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def tool_name(payload: dict[str, Any]) -> str:
    value = payload.get("tool_name") or payload.get("tool") or payload.get("name") or ""
    return str(value)


def is_mutating_tool(name: str) -> bool:
    return name in MUTATING_TOOLS


def _to_candidate_dirs(raw: str | Path) -> list[Path]:
    p = Path(str(raw)).expanduser()
    candidates: list[Path] = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.append(Path.cwd() / p)
    return candidates


def _ascend_find_marker(start: Path, marker_name: str) -> Path | None:
    current = start if start.is_dir() else start.parent
    while True:
        marker = current / marker_name
        if marker.exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def find_project_root(paths: list[str] | None = None) -> Path | None:
    """Find root by PROJECT.md; fallback to CWD when marker is absent."""
    seen: set[Path] = set()
    candidate_starts: list[Path] = []

    if paths:
        for raw in paths:
            if not raw:
                continue
            for candidate in _to_candidate_dirs(raw):
                candidate_starts.append(candidate)

    for env_key in ("CLAUDE_PROJECT_DIR", "PWD"):
        env_value = os.getenv(env_key)
        if env_value:
            candidate_starts.append(Path(env_value).expanduser())

    candidate_starts.append(Path.cwd())

    for start in candidate_starts:
        resolved = start.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        found = _ascend_find_marker(resolved, PROJECT_MARKER)
        if found:
            return found

    return None


def collect_paths_from_payload(payload: dict[str, Any]) -> list[str]:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []

    collected: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            if "/" in value or "\\" in value or value.endswith((".py", ".md", ".json", ".txt")):
                collected.append(value)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if isinstance(value, dict):
            for key, sub_value in value.items():
                key_lower = str(key).lower()
                if "path" in key_lower or key_lower in {"file", "files"}:
                    walk(sub_value)
                elif isinstance(sub_value, (dict, list)):
                    walk(sub_value)

    walk(tool_input)
    return collected


def marker_path(project_root: Path) -> Path:
    return project_root / WORKFLOW_MARKER


def project_is_managed(project_root: Path | None) -> bool:
    return bool(project_root and (project_root / PROJECT_MARKER).exists())


def read_marker(project_root: Path) -> dict[str, Any] | None:
    path = marker_path(project_root)
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None

    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    dt = parse_iso_datetime(text)
    if not dt:
        return None
    return {"activated_at": dt.isoformat(), "ttl_hours": DEFAULT_TTL_HOURS}


def marker_age(marker_data: dict[str, Any]) -> timedelta | None:
    activated_at = parse_iso_datetime(str(marker_data.get("activated_at", "")))
    if not activated_at:
        return None
    return now_utc() - activated_at


def marker_is_fresh(marker_data: dict[str, Any], ttl_override_hours: int | None = None) -> tuple[bool, str]:
    age = marker_age(marker_data)
    if age is None:
        return False, "Invalid marker: missing or bad activated_at timestamp."

    ttl_hours = ttl_override_hours
    if ttl_hours is None:
        raw_ttl = marker_data.get("ttl_hours", DEFAULT_TTL_HOURS)
        try:
            ttl_hours = int(raw_ttl)
        except (TypeError, ValueError):
            ttl_hours = DEFAULT_TTL_HOURS

    if ttl_hours <= 0:
        ttl_hours = DEFAULT_TTL_HOURS

    if age > timedelta(hours=ttl_hours):
        return (
            False,
            f"Workflow marker expired ({age.total_seconds() / 3600:.2f}h > {ttl_hours}h). Re-activate workflow.",
        )
    return True, "Workflow marker is fresh."


def write_marker(project_root: Path, ttl_hours: int) -> Path:
    marker = marker_path(project_root)
    payload = {
        "activated_at": now_utc().isoformat(),
        "ttl_hours": ttl_hours,
        "activated_by": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
        "cwd": str(Path.cwd()),
    }
    marker.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return marker


def is_bootstrap_exempt(path_text: str, project_root: Path) -> bool:
    try:
        abs_path = (Path(path_text).expanduser() if Path(path_text).is_absolute() else (Path.cwd() / path_text)).resolve()
    except Exception:
        return False

    for rel in BOOTSTRAP_EXEMPT_REL_PATHS:
        expected = (project_root / rel).resolve()
        if abs_path == expected:
            return True
    return False


def deny(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def allow(message: str | None = None) -> None:
    if message:
        print(message)
    raise SystemExit(0)

#!/usr/bin/env python3
"""State manager for atomic reviewer-response units."""

from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None

VALID_STATES = ["prewrite", "draft", "checked", "final"]


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@contextmanager
def _lock(project_root: Path):
    lock_path = project_root / "logs" / ".state.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
        os.close(fd)


def _unit_files(project_root: Path) -> list[Path]:
    return sorted((project_root / "units").glob("*.json"))


def _state_path(project_root: Path) -> Path:
    return project_root / "logs" / "unit_state.json"


def _load_state(project_root: Path) -> dict:
    return _read_json(_state_path(project_root), {"updated_at": "", "units": {}, "pipeline": {}})


def _sync_units(project_root: Path, state: dict) -> dict:
    units = state.setdefault("units", {})
    for fp in _unit_files(project_root):
        u = _read_json(fp, {})
        uid = u.get("unit_id")
        if not uid:
            continue
        item = units.setdefault(uid, {})
        item.setdefault("state", "final" if u.get("section") == "email" else "draft")
        item["title"] = u.get("title", uid)
        item["reviewer"] = u.get("reviewer", "")
        item["section"] = u.get("section", "")
        item["comment_number"] = str(u.get("comment_number", ""))
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state


def cmd_init(args) -> int:
    root = Path(args.project_root)
    with _lock(root):
        state = {"updated_at": "", "units": {}, "pipeline": {"last_run": "", "last_status": ""}}
        state = _sync_units(root, state)
        _write_json(_state_path(root), state)
    print("STATE_INIT: PASS")
    print(f"- units tracked: {len(state['units'])}")
    return 0


def cmd_sync(args) -> int:
    root = Path(args.project_root)
    with _lock(root):
        state = _load_state(root)
        before = len(state.get("units", {}))
        state = _sync_units(root, state)
        after = len(state.get("units", {}))
        if args.pipeline_status:
            state.setdefault("pipeline", {})["last_status"] = args.pipeline_status
            state["pipeline"]["last_run"] = datetime.now(timezone.utc).isoformat()
        _write_json(_state_path(root), state)
    print("STATE_SYNC: PASS")
    print(f"- units before: {before}")
    print(f"- units after: {after}")
    return 0


def cmd_set(args) -> int:
    root = Path(args.project_root)
    if args.state not in VALID_STATES:
        print(f"STATE_SET: FAIL\n- invalid state: {args.state}")
        return 1
    with _lock(root):
        state = _load_state(root)
        state = _sync_units(root, state)
        units = state.setdefault("units", {})
        if args.unit_id not in units:
            print(f"STATE_SET: FAIL\n- unknown unit_id: {args.unit_id}")
            return 1
        units[args.unit_id]["state"] = args.state
        units[args.unit_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        if args.note:
            units[args.unit_id]["note"] = args.note
        _write_json(_state_path(root), state)
    print("STATE_SET: PASS")
    print(f"- unit: {args.unit_id}")
    print(f"- state: {args.state}")
    return 0


def cmd_show(args) -> int:
    root = Path(args.project_root)
    state = _load_state(root)
    if args.unit_id:
        unit = state.get("units", {}).get(args.unit_id)
        if unit is None:
            print("STATE_SHOW: FAIL")
            print(f"- unknown unit_id: {args.unit_id}")
            return 1
        print(json.dumps({args.unit_id: unit}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="State manager for reviewer-response atomic project")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--project-root", required=True)
    p_init.set_defaults(func=cmd_init)

    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--project-root", required=True)
    p_sync.add_argument("--pipeline-status", default="")
    p_sync.set_defaults(func=cmd_sync)

    p_set = sub.add_parser("set")
    p_set.add_argument("--project-root", required=True)
    p_set.add_argument("--unit-id", required=True)
    p_set.add_argument("--state", required=True)
    p_set.add_argument("--note", default="")
    p_set.set_defaults(func=cmd_set)

    p_show = sub.add_parser("show")
    p_show.add_argument("--project-root", required=True)
    p_show.add_argument("--unit-id", default="")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

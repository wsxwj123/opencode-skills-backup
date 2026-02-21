#!/usr/bin/env python3
"""Activate workflow session by writing .workflow-active marker."""

from __future__ import annotations

import argparse
from pathlib import Path

from workflow_common import DEFAULT_TTL_HOURS, PROJECT_MARKER, setup_utf8_stdio, write_marker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Activate workflow gate for the current project.")
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Project root path. Defaults to current working directory.",
    )
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=DEFAULT_TTL_HOURS,
        help=f"Session TTL in hours (default: {DEFAULT_TTL_HOURS}).",
    )
    parser.add_argument(
        "--require-project-marker",
        action="store_true",
        help=f"Fail if {PROJECT_MARKER} does not exist in project root.",
    )
    return parser.parse_args()


def main() -> int:
    setup_utf8_stdio()
    args = parse_args()

    root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    if not root.exists():
        print(f"Project root does not exist: {root}")
        return 1

    if args.require_project_marker and not (root / PROJECT_MARKER).exists():
        print(f"Missing {PROJECT_MARKER} in {root}")
        return 1

    ttl = args.ttl_hours if args.ttl_hours > 0 else DEFAULT_TTL_HOURS
    marker = write_marker(root, ttl)
    print(f"Workflow activated: {marker} (ttl={ttl}h)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

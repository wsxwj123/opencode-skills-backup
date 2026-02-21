#!/usr/bin/env python3
"""PreToolUse gate with optional auto-activation for managed projects."""

from __future__ import annotations

import argparse

from workflow_common import (
    DEFAULT_TTL_HOURS,
    allow,
    collect_paths_from_payload,
    deny,
    find_project_root,
    is_bootstrap_exempt,
    is_mutating_tool,
    marker_is_fresh,
    project_is_managed,
    read_marker,
    read_stdin_json,
    setup_utf8_stdio,
    tool_name,
    write_marker,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guard editing tools with workflow activation checks.")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=None,
        help="Optional TTL override in hours for marker freshness.",
    )
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=DEFAULT_TTL_HOURS,
        help=f"TTL used when auto-activating marker (default: {DEFAULT_TTL_HOURS}).",
    )
    parser.add_argument(
        "--auto-activate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-create/refresh .workflow-active when missing or stale.",
    )
    return parser.parse_args()


def main() -> None:
    setup_utf8_stdio()
    args = parse_args()
    payload = read_stdin_json()

    name = tool_name(payload)
    if not is_mutating_tool(name):
        allow()

    candidate_paths = collect_paths_from_payload(payload)
    project_root = find_project_root(candidate_paths)
    if not project_root or not project_is_managed(project_root):
        allow()

    for path_text in candidate_paths:
        if is_bootstrap_exempt(path_text, project_root):
            allow()

    ttl_hours = args.ttl_hours if args.ttl_hours and args.ttl_hours > 0 else DEFAULT_TTL_HOURS

    marker_data = read_marker(project_root)
    if not marker_data:
        if args.auto_activate:
            marker = write_marker(project_root, ttl_hours)
            allow(f"Workflow auto-activated: {marker} (ttl={ttl_hours}h)")
        deny(
            "Workflow not activated. Run:\n"
            "python3 \"$HOME/.claude/skills/workflow-guard/scripts/workflow-activate.py\" --project-root \"$PWD\""
        )

    fresh, reason = marker_is_fresh(marker_data, ttl_override_hours=args.max_age_hours)
    if not fresh:
        if args.auto_activate:
            marker = write_marker(project_root, ttl_hours)
            allow(f"Workflow marker refreshed automatically: {marker} (ttl={ttl_hours}h)")
        deny(reason)

    allow()


if __name__ == "__main__":
    main()

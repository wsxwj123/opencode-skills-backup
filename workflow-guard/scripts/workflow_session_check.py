#!/usr/bin/env python3
"""Check marker freshness with optional auto-activation."""

from __future__ import annotations

import argparse

from workflow_common import (
    DEFAULT_TTL_HOURS,
    PROJECT_MARKER,
    allow,
    collect_paths_from_payload,
    deny,
    find_project_root,
    marker_is_fresh,
    parse_iso_datetime,
    project_is_managed,
    read_marker,
    read_stdin_json,
    setup_utf8_stdio,
    write_marker,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check workflow session freshness.")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=None,
        help="Optional TTL override in hours.",
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
    parser.add_argument(
        "--strict",
        action="store_true",
        help=f"Block if project root cannot be located but {PROJECT_MARKER} likely applies.",
    )
    return parser.parse_args()


def main() -> None:
    setup_utf8_stdio()
    args = parse_args()
    payload = read_stdin_json()

    candidate_paths = collect_paths_from_payload(payload)
    project_root = find_project_root(candidate_paths)
    if not project_root:
        if args.strict:
            deny("Cannot determine project root for workflow session check.")
        allow()

    if not project_is_managed(project_root):
        allow()

    ttl_hours = args.ttl_hours if args.ttl_hours and args.ttl_hours > 0 else DEFAULT_TTL_HOURS

    marker_data = read_marker(project_root)
    if not marker_data:
        if args.auto_activate:
            marker = write_marker(project_root, ttl_hours)
            allow(f"Workflow auto-activated: {marker} (ttl={ttl_hours}h)")
        deny(
            "Workflow marker missing. Activate workflow first:\n"
            "python3 \"$HOME/.claude/skills/workflow-guard/scripts/workflow-activate.py\" --project-root \"$PWD\""
        )

    # Force parse once to provide clearer error when timestamp is malformed.
    timestamp = str(marker_data.get("activated_at", ""))
    if not parse_iso_datetime(timestamp):
        if args.auto_activate:
            marker = write_marker(project_root, ttl_hours)
            allow(f"Workflow marker repaired automatically: {marker} (ttl={ttl_hours}h)")
        deny("Workflow marker is invalid (bad activated_at timestamp). Re-activate workflow.")

    fresh, reason = marker_is_fresh(marker_data, ttl_override_hours=args.max_age_hours)
    if not fresh:
        if args.auto_activate:
            marker = write_marker(project_root, ttl_hours)
            allow(f"Workflow marker refreshed automatically: {marker} (ttl={ttl_hours}h)")
        deny(reason)

    allow()


if __name__ == "__main__":
    main()

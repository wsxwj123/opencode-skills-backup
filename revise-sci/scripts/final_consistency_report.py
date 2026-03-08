#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import read_json, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Write final consistency report")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    units = [read_json(path, {}) for path in sorted((project_root / "units").glob("*.json"))]
    state = read_json(project_root / "project_state.json", {})
    lines = [
        "# Final Consistency Report",
        "",
        f"- delivery_status: `{state.get('delivery_status', 'draft')}`",
        f"- total_comments: `{len(units)}`",
        f"- completed: `{sum(1 for unit in units if unit.get('status') == 'completed')}`",
        f"- needs_author_confirmation: `{sum(1 for unit in units if unit.get('status') == 'needs_author_confirmation')}`",
        "",
        "| comment_id | severity | status | target_document | source_trace |",
        "|---|---|---|---|---|",
    ]
    for unit in units:
        trace = ", ".join(src.get("provider_family", "unknown") for src in unit.get("evidence_sources", [])) or "unknown"
        lines.append(f"| {unit.get('comment_id','')} | {unit.get('severity','')} | {unit.get('status','')} | {unit.get('target_document','')} | {trace} |")
    if state.get("delivery_status") == "author_confirmation_required":
        lines.extend(["", "## Blocking Reasons", "", "- 当前至少一条评论仍需作者确认，故项目状态不是 ready_to_submit。"])
    write_text(project_root / "final_consistency_report.md", "\n".join(lines) + "\n")
    print('{"ok": true}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

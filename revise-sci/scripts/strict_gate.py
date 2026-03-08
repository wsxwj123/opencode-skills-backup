#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ALLOWED_PROVIDER_FAMILIES, placeholder_found, read_json


REQUIRED_RESPONSE_HEADINGS = [
    "# 回复审稿人的邮件",
    "#### 2) Response to Reviewer（中英对照）",
    "#### 5) Evidence Attachments",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate for revise-sci outputs")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    state = read_json(project_root / "project_state.json", {})
    units = [read_json(path, {}) for path in sorted((project_root / "units").glob("*.json"))]
    failures: list[str] = []

    for unit in units:
        for key in (
            "comment_id",
            "reviewer_comment_en",
            "reviewer_comment_zh_literal",
            "intent_zh",
            "response_en",
            "response_zh",
            "revised_excerpt_en",
            "revised_excerpt_zh",
        ):
            if placeholder_found(unit.get(key)):
                failures.append(f"{unit.get('comment_id', '<unknown>')}: placeholder in {key}")
        if unit.get("severity") == "major" and unit.get("status") not in {"completed", "needs_author_confirmation"}:
            failures.append(f"{unit.get('comment_id', '<unknown>')}: invalid major status")
        if not unit.get("modification_actions"):
            failures.append(f"{unit.get('comment_id', '<unknown>')}: missing modification_actions")
        if not unit.get("notes_core_zh") or not unit.get("notes_support_zh"):
            failures.append(f"{unit.get('comment_id', '<unknown>')}: missing notes")
        if not unit.get("evidence_sources"):
            failures.append(f"{unit.get('comment_id', '<unknown>')}: missing evidence_sources")
        for source in unit.get("evidence_sources", []):
            if source.get("provider_family") not in ALLOWED_PROVIDER_FAMILIES:
                failures.append(f"{unit.get('comment_id', '<unknown>')}: invalid provider family {source.get('provider_family')}")

    if len(list((project_root / "comment_records").glob("*.md"))) != len(units):
        failures.append("comment_records count does not match units count")

    response_md = project_root / "response_to_reviewers.md"
    if not response_md.exists():
        failures.append("missing response_to_reviewers.md")
    else:
        response_text = response_md.read_text(encoding="utf-8")
        for heading in REQUIRED_RESPONSE_HEADINGS:
            if heading not in response_text:
                failures.append(f"response_to_reviewers.md missing heading: {heading}")

    for required_file in (
        project_root / "response_to_reviewers.docx",
        Path(state.get("outputs", {}).get("output_md", project_root / "missing.md")),
        Path(state.get("outputs", {}).get("output_docx", project_root / "missing.docx")),
        project_root / "manuscript_edit_plan.md",
    ):
        if not required_file.exists():
            failures.append(f"missing output: {required_file}")

    if state.get("delivery_status") == "ready_to_submit" and any(unit.get("status") == "needs_author_confirmation" for unit in units):
        failures.append("delivery_status ready_to_submit conflicts with needs_author_confirmation units")

    if state.get("counts", {}).get("comment_units") not in {None, len(units)}:
        failures.append("project_state comment_units does not match units count")

    if failures:
        print("STRICT_GATE: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("STRICT_GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

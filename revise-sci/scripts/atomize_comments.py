#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import AtomicCommentHTMLParser, normalize_ws, read_docx_paragraphs, read_json, write_json


def reviewer_number(reviewer: str) -> int:
    match = re.search(r"(\d+)", reviewer)
    return int(match.group(1)) if match else 1


def format_comment_id(reviewer: str, severity: str, index: int) -> str:
    return f"R{reviewer_number(reviewer)}-{severity.capitalize()}-{index:02d}"


def parse_docx_comments(path: Path) -> list[dict[str, str]]:
    rows = read_docx_paragraphs(path)
    comments: list[dict[str, str]] = []
    current_reviewer = "Reviewer #1"
    current_severity = "major"
    current_text: list[str] = []
    current_comment_number = 0

    def flush_current() -> None:
        nonlocal current_text, current_comment_number
        if not current_text:
            return
        current_comment_number += 1
        comments.append(
            {
                "comment_id": format_comment_id(current_reviewer, current_severity, current_comment_number),
                "reviewer": current_reviewer,
                "severity": current_severity,
                "comment_text": normalize_ws(" ".join(current_text)),
            }
        )
        current_text = []

    severity_counters: dict[tuple[str, str], int] = {}
    for row in rows:
        text = row["text"]
        if re.match(r"^Reviewer\s*#?\d+", text, flags=re.IGNORECASE):
            flush_current()
            current_reviewer = normalize_ws(text.replace("Reviewer", "Reviewer "))
            current_severity = "major"
            current_comment_number = severity_counters.get((current_reviewer, current_severity), 0)
            continue
        lowered = text.lower()
        if lowered in {"major", "major comments", "major comment"}:
            flush_current()
            current_severity = "major"
            current_comment_number = severity_counters.get((current_reviewer, current_severity), 0)
            continue
        if lowered in {"minor", "minor comments", "minor comment"}:
            flush_current()
            current_severity = "minor"
            current_comment_number = severity_counters.get((current_reviewer, current_severity), 0)
            continue
        match = re.match(r"^(\d+)[\.\)]\s*(.+)$", text)
        if match:
            flush_current()
            current_text = [match.group(2)]
            current_comment_number = severity_counters.get((current_reviewer, current_severity), 0)
            severity_counters[(current_reviewer, current_severity)] = current_comment_number + 1
            comments.append(
                {
                    "comment_id": format_comment_id(current_reviewer, current_severity, severity_counters[(current_reviewer, current_severity)]),
                    "reviewer": current_reviewer,
                    "severity": current_severity,
                    "comment_text": normalize_ws(match.group(2)),
                }
            )
            current_text = []
            current_comment_number = severity_counters[(current_reviewer, current_severity)]
            continue
        if comments:
            comments[-1]["comment_text"] = normalize_ws(comments[-1]["comment_text"] + " " + text)
    return comments


def parse_html_comments(path: Path) -> list[dict[str, str]]:
    parser = AtomicCommentHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    units = []
    for item in parser.units:
        units.append(
            {
                "comment_id": item["comment_id"] or format_comment_id(item["reviewer"], item["severity"], len(units) + 1),
                "reviewer": item["reviewer"],
                "severity": item["severity"],
                "comment_text": item["comment_text"],
            }
        )
    return units


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomize review comments into comment units")
    parser.add_argument("--comments", required=True)
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    comments_path = Path(args.comments)
    project_root = Path(args.project_root)
    units_dir = project_root / "units"
    units_dir.mkdir(parents=True, exist_ok=True)

    if comments_path.suffix.lower() == ".html":
        parsed = parse_html_comments(comments_path)
    else:
        parsed = parse_docx_comments(comments_path)

    for idx, item in enumerate(parsed, start=1):
        payload = {
            "comment_id": item["comment_id"],
            "reviewer": item["reviewer"],
            "severity": item["severity"],
            "reviewer_comment_en": item["comment_text"],
            "reviewer_comment_zh_literal": "",
            "intent_zh": "",
            "response_zh": "",
            "response_en": "",
            "atomic_location": {},
            "original_excerpt_en": "",
            "revised_excerpt_en": "",
            "revised_excerpt_zh": "",
            "modification_actions": [],
            "notes_core_zh": [],
            "notes_support_zh": [],
            "evidence_sources": [],
            "target_document": "",
            "status": "not_started",
            "author_confirmation_reason": "",
        }
        write_json(units_dir / f"{idx:03d}_{item['comment_id']}.json", payload)

    state = read_json(project_root / "project_state.json", {})
    state.setdefault("counts", {})
    state["counts"]["comment_units"] = len(parsed)
    write_json(project_root / "project_state.json", state)

    print(json.dumps({"ok": True, "count": len(parsed)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

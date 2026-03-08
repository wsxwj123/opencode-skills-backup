#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ALLOWED_PROVIDER_FAMILIES, blocked_placeholder_found, normalize_ws, read_json


REQUIRED_RESPONSE_HEADINGS = [
    "# 回复审稿人的邮件",
    "#### 2) Response to Reviewer（中英对照）",
    "#### 5) Evidence Attachments",
]


def missing_atomic_fields(unit: dict) -> list[str]:
    atomic = unit.get("atomic_location") or {}
    if normalize_ws(unit.get("original_excerpt_en")) in {"", "无"}:
        return []
    required = {
        "section_file": atomic.get("section_file"),
        "paragraph_index": atomic.get("paragraph_index"),
        "matched_sentence": atomic.get("matched_sentence"),
    }
    return [key for key, value in required.items() if value in {"", None, "无"}]


def section_label(unit: dict) -> str:
    return "si section" if unit.get("target_document") == "si" else "manuscript section"


def completed_citation_units(units: list[dict]) -> list[dict]:
    return [
        unit
        for unit in units
        if unit.get("status") == "completed" and unit.get("editorial_intent") == "citation"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate for revise-sci outputs")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    state = read_json(project_root / "project_state.json", {})
    units = [read_json(path, {}) for path in sorted((project_root / "units").glob("*.json"))]
    failures: list[str] = []

    response_md = project_root / "response_to_reviewers.md"
    response_text = response_md.read_text(encoding="utf-8") if response_md.exists() else ""
    edit_plan_path = project_root / "manuscript_edit_plan.md"
    edit_plan_text = edit_plan_path.read_text(encoding="utf-8") if edit_plan_path.exists() else ""
    reference_sync_report = read_json(project_root / "reference_sync_report.json", {})
    covered_reference_comments = set(reference_sync_report.get("covered_comment_ids", []))
    literature_index_path = project_root / "data" / "literature_index.json"
    synthesis_matrix_path = project_root / "data" / "synthesis_matrix.json"
    synthesis_audit_path = project_root / "data" / "synthesis_matrix_audit.json"
    reference_registry_path = project_root / "data" / "reference_registry.json"
    reference_coverage_path = project_root / "data" / "reference_coverage_audit.json"
    literature_index = read_json(literature_index_path, [])
    synthesis_matrix = read_json(synthesis_matrix_path, [])
    synthesis_audit = read_json(synthesis_audit_path, {})
    reference_coverage = read_json(reference_coverage_path, {})
    citation_units = completed_citation_units(units)

    for artifact in (reference_registry_path, reference_coverage_path):
        if not artifact.exists():
            failures.append(f"missing reference artifact: {artifact.name}")
    if isinstance(reference_coverage, dict) and not reference_coverage.get("ok", True):
        failures.append("reference coverage audit reports unresolved numeric citation gaps")

    if citation_units:
        for artifact in (literature_index_path, synthesis_matrix_path, synthesis_audit_path):
            if not artifact.exists():
                failures.append(f"missing literature artifact: {artifact.name}")
        if isinstance(synthesis_audit, dict):
            if synthesis_audit.get("missing_claim", 0) > 0:
                failures.append("synthesis_matrix_audit reports missing_claim gaps")
            if synthesis_audit.get("missing_key_fields", 0) > 0:
                failures.append("synthesis_matrix_audit reports missing_key_fields gaps")

    for unit in units:
        comment_id = unit.get("comment_id", "<unknown>")
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
            if blocked_placeholder_found(unit.get(key)):
                failures.append(f"{comment_id}: placeholder in {key}")
        if unit.get("severity") == "major" and unit.get("status") not in {"completed", "needs_author_confirmation"}:
            failures.append(f"{comment_id}: invalid major status")
        if not unit.get("modification_actions"):
            failures.append(f"{comment_id}: missing modification_actions")
        if not unit.get("notes_core_zh") or not unit.get("notes_support_zh"):
            failures.append(f"{comment_id}: missing notes")
        if not unit.get("evidence_sources"):
            failures.append(f"{comment_id}: missing evidence_sources")
        for source in unit.get("evidence_sources", []):
            if source.get("provider_family") not in ALLOWED_PROVIDER_FAMILIES:
                failures.append(f"{comment_id}: invalid provider family {source.get('provider_family')}")

        atomic_failures = missing_atomic_fields(unit)
        if atomic_failures:
            failures.append(f"{comment_id}: incomplete atomic_location fields: {', '.join(atomic_failures)}")

        required_response_snippets = [
            unit.get("reviewer_comment_en", ""),
            unit.get("response_en", ""),
        ]
        if unit.get("status") == "completed":
            required_response_snippets.append(unit.get("revised_excerpt_en", ""))
        if any(snippet and snippet not in response_text for snippet in required_response_snippets):
            failures.append(f"{comment_id}: missing comment mapping in response_to_reviewers.md")

        if comment_id not in edit_plan_text:
            failures.append(f"{comment_id}: edit plan missing comment_id")
        elif unit.get("status") == "completed" and unit.get("revised_excerpt_en") not in edit_plan_text:
            failures.append(f"{comment_id}: edit plan missing revised excerpt")

        if unit.get("status") == "completed" and unit.get("editorial_intent") == "citation":
            if comment_id not in covered_reference_comments:
                failures.append(f"{comment_id}: completed citation unit missing reference_sync coverage")
            entry = None
            if isinstance(literature_index, list):
                for candidate in literature_index:
                    if comment_id in (candidate.get("comment_ids") or []) or comment_id in (candidate.get("claim_ids") or []):
                        entry = candidate
                        break
            if not entry:
                failures.append(f"{comment_id}: literature_index missing citation mapping")
            elif isinstance(synthesis_matrix, list):
                has_matrix_row = any(
                    row.get("global_id") == entry.get("global_id")
                    and (
                        row.get("claim_id") == comment_id
                        or comment_id in (row.get("comment_ids") or [])
                    )
                    for row in synthesis_matrix
                )
                if not has_matrix_row:
                    failures.append(f"{comment_id}: synthesis_matrix missing citation mapping")

        section_file = (unit.get("atomic_location") or {}).get("section_file", "")
        if unit.get("status") == "completed":
            if not section_file:
                failures.append(f"{comment_id}: missing section_file for completed unit")
            else:
                section_path = project_root / section_file
                if not section_path.exists():
                    failures.append(f"{comment_id}: missing output section file {section_path}")
                else:
                    section_text = section_path.read_text(encoding="utf-8")
                    if unit.get("revised_excerpt_en") not in section_text:
                        failures.append(f"{comment_id}: completed excerpt not found in {section_label(unit)}")

    if len(list((project_root / "comment_records").glob("*.md"))) != len(units):
        failures.append("comment_records count does not match units count")
    for unit in units:
        record_path = project_root / "comment_records" / f"{unit.get('comment_id', '')}.md"
        if not record_path.exists():
            failures.append(f"{unit.get('comment_id', '<unknown>')}: missing comment_record file")

    if not response_md.exists():
        failures.append("missing response_to_reviewers.md")
    else:
        for heading in REQUIRED_RESPONSE_HEADINGS:
            if heading not in response_text:
                failures.append(f"response_to_reviewers.md missing heading: {heading}")
        for label in ("**Text**", "**Image**", "**Table**"):
            if response_text.count(label) < len(units):
                failures.append(f"response_to_reviewers.md missing per-comment evidence block: {label}")

    manuscript_index = read_json(project_root / "manuscript_section_index.json", {"sections": []})
    section_files = {section.get("file") for section in manuscript_index.get("sections", [])}
    for unit in units:
        section_file = (unit.get("atomic_location") or {}).get("section_file")
        if section_file and unit.get("target_document") == "manuscript" and section_file not in section_files:
            failures.append(f"{unit.get('comment_id', '<unknown>')}: atomic section_file not found in manuscript index")

    for required_file in (
        project_root / "response_to_reviewers.docx",
        Path(state.get("outputs", {}).get("output_md", project_root / "missing.md")),
        Path(state.get("outputs", {}).get("output_docx", project_root / "missing.docx")),
        edit_plan_path,
        project_root / "reference_sync_report.json",
        reference_registry_path,
        reference_coverage_path,
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

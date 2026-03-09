#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ALLOWED_PROVIDER_FAMILIES, blocked_placeholder_found, find_ai_style_markers, normalize_ws, read_docx_paragraphs, read_json


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


def approved_search_governance_failures(project_root: Path, reference_coverage: dict) -> list[str]:
    failures: list[str] = []
    if not isinstance(reference_coverage, dict) or reference_coverage.get("reference_search_decision") != "approved":
        return failures

    manifest_path = project_root / "reference_search_manifest.json"
    strategy_path = project_root / "reference_search_strategy.json"
    status_path = project_root / "reference_search_status.json"
    rounds_path = project_root / "reference_search_rounds.json"
    task_path = project_root / "reference_search_task.md"
    execution_path = project_root / "reference_search_execution.json"
    paper_results_path = project_root / "paper_search_results.json"
    paper_validated_path = project_root / "paper_search_validated.json"
    guard_report_path = project_root / "paper_search_guard_report.json"
    literature_index_path = project_root / "data" / "literature_index.json"
    synthesis_matrix_path = project_root / "data" / "synthesis_matrix.json"
    synthesis_audit_path = project_root / "data" / "synthesis_matrix_audit.json"
    reference_sync_path = project_root / "reference_sync_report.json"

    for artifact in (manifest_path, task_path, strategy_path, status_path, rounds_path):
        if not artifact.exists():
            failures.append(f"reference search approved but {artifact.name} is missing")
    if failures:
        return failures

    manifest = read_json(manifest_path, {})
    strategy = read_json(strategy_path, {})
    status = read_json(status_path, {})
    rounds = read_json(rounds_path, {})
    guard_report = read_json(guard_report_path, {})
    execution = read_json(execution_path, {})

    if manifest.get("workflow") != "review-writing":
        failures.append("reference_search_manifest.json must declare workflow review-writing")
    if manifest.get("reference_search_decision") != "approved":
        failures.append("reference_search_manifest.json must keep reference_search_decision approved")
    if manifest.get("governance_active") is not True:
        failures.append("reference_search_manifest.json must keep governance_active true")
    if manifest.get("allowed_provider_families") != ["paper-search"]:
        failures.append("reference_search_manifest.json must restrict allowed_provider_families to paper-search")
    if "websearch" not in (manifest.get("forbidden_provider_families") or []):
        failures.append("reference_search_manifest.json must forbid websearch")
    verification_policy = manifest.get("verification_policy") or {}
    if verification_policy.get("dual_verification_required") is not True:
        failures.append("reference_search_manifest.json must require dual verification")
    if verification_policy.get("allow_unverified") is not False:
        failures.append("reference_search_manifest.json must disallow unverified search rows")
    if "citation_guard.py" not in normalize_ws(str(verification_policy.get("guard_command") or "")):
        failures.append("reference_search_manifest.json must include citation_guard.py as mandatory guard command")
    if len((manifest.get("workflow_rules") or {}).get("rounds") or []) != 3:
        failures.append("reference_search_manifest.json must describe exactly three search rounds")

    if strategy.get("workflow") != "review-writing":
        failures.append("reference_search_strategy.json must declare workflow review-writing")
    provider_policy = strategy.get("provider_policy") or {}
    if provider_policy.get("primary") != ["paper-search"]:
        failures.append("reference_search_strategy.json must restrict primary providers to paper-search")
    if "websearch" not in (provider_policy.get("forbidden") or []):
        failures.append("reference_search_strategy.json must forbid websearch")
    if "citation_guard.py" not in normalize_ws(str(strategy.get("mandatory_guard_command") or "")):
        failures.append("reference_search_strategy.json must declare citation_guard.py as mandatory guard command")
    if len(strategy.get("round_model") or []) != 3:
        failures.append("reference_search_strategy.json must declare a three-round model")
    required_outputs = strategy.get("required_outputs") or []
    for required in ("data/literature_index.json", "data/synthesis_matrix.json", "data/synthesis_matrix_audit.json"):
        if required not in required_outputs:
            failures.append(f"reference_search_strategy.json missing required output {required}")

    if rounds.get("workflow") != "review-writing":
        failures.append("reference_search_rounds.json must declare workflow review-writing")
    round_entries = rounds.get("rounds") or []
    if len(round_entries) != 3:
        failures.append("reference_search_rounds.json must describe exactly three rounds")
    else:
        for expected_round, round_entry in enumerate(round_entries, start=1):
            if round_entry.get("round") != expected_round:
                failures.append("reference_search_rounds.json round ordering is invalid")
            if round_entry.get("provider_family") != "paper-search":
                failures.append("reference_search_rounds.json must restrict provider_family to paper-search")
        if not any((round_entry.get("queries") or []) for round_entry in round_entries):
            failures.append("reference_search_rounds.json must include at least one executable search query")

    if status.get("reference_search_decision") != "approved":
        failures.append("reference_search_status.json must keep reference_search_decision approved")
    if status.get("governance_active") is not True:
        failures.append("reference_search_status.json must keep governance_active true")
    steps = status.get("steps") or {}
    if steps.get("search_round_plan_generated") is not rounds_path.exists():
        failures.append("reference_search_status.json step search_round_plan_generated is inconsistent with reference_search_rounds.json")
    if steps.get("paper_search_batch_imported") is not paper_results_path.exists():
        failures.append("reference_search_status.json step paper_search_batch_imported is inconsistent with paper_search_results.json")
    if steps.get("validated_batch_present") is not paper_validated_path.exists():
        failures.append("reference_search_status.json step validated_batch_present is inconsistent with paper_search_validated.json")
    guard_passed = bool((guard_report.get("summary") or {}).get("all_rows_guard_verified", False))
    if steps.get("citation_guard_passed") is not guard_passed:
        failures.append("reference_search_status.json step citation_guard_passed is inconsistent with paper_search_guard_report.json")
    if steps.get("literature_index_built") is not literature_index_path.exists():
        failures.append("reference_search_status.json step literature_index_built is inconsistent with literature_index artifact presence")
    if steps.get("synthesis_matrix_audited") is not synthesis_audit_path.exists():
        failures.append("reference_search_status.json step synthesis_matrix_audited is inconsistent with synthesis_matrix_audit artifact presence")
    if steps.get("reference_sync_completed") is not reference_sync_path.exists():
        failures.append("reference_search_status.json step reference_sync_completed is inconsistent with reference_sync_report.json")

    if paper_results_path.exists():
        if not paper_validated_path.exists():
            failures.append("approved reference search batch is missing paper_search_validated.json")
        if not guard_report_path.exists():
            failures.append("approved reference search batch is missing paper_search_guard_report.json")
        if not guard_passed:
            failures.append("approved reference search batch has not passed citation_guard.py")
        for artifact in (literature_index_path, synthesis_matrix_path, synthesis_audit_path):
            if not artifact.exists():
                failures.append(f"approved reference search batch is missing canonical artifact {artifact.name}")
    if execution_path.exists():
        if execution.get("ok") is not True:
            failures.append("reference_search_execution.json exists but reports ok=false")
        if execution.get("driver_mode") not in {"local-runner", "opencode-driver"}:
            failures.append("reference_search_execution.json has unsupported driver_mode")
    return failures


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
    revision_polish_manifest_path = project_root / "revision_polish_manifest.json"
    revision_polish_execution_path = project_root / "revision_polish_execution.json"
    literature_index = read_json(literature_index_path, [])
    synthesis_matrix = read_json(synthesis_matrix_path, [])
    synthesis_audit = read_json(synthesis_audit_path, {})
    reference_coverage = read_json(reference_coverage_path, {})
    revision_polish_execution = read_json(revision_polish_execution_path, {})
    reference_search_decision = normalize_ws(str((state.get("inputs") or {}).get("reference_search_decision") or "ask"))
    citation_units = completed_citation_units(units)

    for artifact in (revision_polish_manifest_path, revision_polish_execution_path):
        if not artifact.exists():
            failures.append(f"missing polish artifact: {artifact.name}")
    if isinstance(revision_polish_execution, dict) and revision_polish_execution.get("ok") is not True:
        failures.append("revision polish execution reports ok=false")

    for artifact in (reference_registry_path, reference_coverage_path):
        if not artifact.exists():
            failures.append(f"missing reference artifact: {artifact.name}")
    if isinstance(reference_coverage, dict) and not reference_coverage.get("ok", True):
        failures.append("reference coverage audit reports unresolved citation coverage gaps")
    if any((project_root / name).exists() for name in ("paper_search_results.json", "paper_search_validated.json", "paper_search_guard_report.json")) and reference_search_decision != "approved":
        failures.append("paper-search artifacts exist but reference_search_decision is not approved")
    if isinstance(reference_coverage, dict) and reference_coverage.get("reference_search_required") and reference_coverage.get("reference_search_decision") == "ask":
        failures.append("reference search decision required before searching and filling new references")
    if isinstance(reference_coverage, dict) and reference_coverage.get("reference_search_required") and reference_coverage.get("reference_search_decision") == "approved":
        failures.append("reference search approved but no validated retrieval batch has closed the reference gaps yet")
    failures.extend(approved_search_governance_failures(project_root, reference_coverage))

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
        revision_plan = unit.get("revision_plan") or {}
        if unit.get("status") == "completed" and revision_plan.get("scope") not in {"", "none", None}:
            if unit.get("polish_applied") is not True:
                failures.append(f"{comment_id}: completed revision is missing revision polishing state")
            if unit.get("polish_driver_mode") in {"", "pending", "not-required", None}:
                failures.append(f"{comment_id}: completed revision is missing a valid polish_driver_mode")
            polished_fragment = normalize_ws(str(revision_plan.get("polished_fragment") or revision_plan.get("raw_fragment") or ""))
            if not polished_fragment:
                failures.append(f"{comment_id}: polished fragment is missing")
            elif find_ai_style_markers(polished_fragment):
                failures.append(f"{comment_id}: polished fragment still contains banned AI-style markers")
            if unit.get("polish_guard_ok") is not True:
                failures.append(f"{comment_id}: polish_guard_ok is false")
            if unit.get("polish_scope_respected") is not True:
                failures.append(f"{comment_id}: polish_scope_respected is false")
            if unit.get("polish_meaning_changed") is not False:
                failures.append(f"{comment_id}: polish_meaning_changed must remain false")
            if unit.get("polish_locked_context_ok") is not True:
                failures.append(f"{comment_id}: polish_locked_context_ok is false")

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

    response_docx = project_root / "response_to_reviewers.docx"
    if not response_docx.exists():
        failures.append("missing output: response_to_reviewers.docx")
    else:
        try:
            response_docx_rows = read_docx_paragraphs(response_docx)
        except Exception:
            failures.append("response_to_reviewers.docx is not a readable docx")
        else:
            response_docx_texts = [normalize_ws(row.get("text", "")) for row in response_docx_rows if normalize_ws(row.get("text", ""))]
            if "回复审稿人的邮件" not in response_docx_texts:
                failures.append("response_to_reviewers.docx missing top-level title")
            if sum(1 for text in response_docx_texts if text.startswith("Comment ")) < len(units):
                failures.append("response_to_reviewers.docx missing comment headings")
            if response_docx_texts.count("2) Response to Reviewer（中英对照）") < len(units):
                failures.append("response_to_reviewers.docx missing response section headings")
            if response_docx_texts.count("5) Evidence Attachments") < len(units):
                failures.append("response_to_reviewers.docx missing evidence section headings")

    manuscript_index = read_json(project_root / "manuscript_section_index.json", {"sections": []})
    section_files = {section.get("file") for section in manuscript_index.get("sections", [])}
    for unit in units:
        section_file = (unit.get("atomic_location") or {}).get("section_file")
        if section_file and unit.get("target_document") == "manuscript" and section_file not in section_files:
            failures.append(f"{unit.get('comment_id', '<unknown>')}: atomic section_file not found in manuscript index")

    for required_file in (
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

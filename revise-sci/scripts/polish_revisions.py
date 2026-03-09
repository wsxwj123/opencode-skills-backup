#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import revise_units
from common import (
    build_section_markdown,
    find_ai_style_markers,
    normalize_ws,
    polish_changed_text_locally,
    read_json,
    write_json,
    write_text,
)


def polish_candidates(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        unit
        for unit in units
        if unit.get("status") == "completed"
        and (unit.get("revision_plan") or {}).get("scope") not in {"", "none", None}
    ]


def candidate_payload(unit: dict[str, Any]) -> dict[str, Any]:
    plan = unit.get("revision_plan") or {}
    return {
        "comment_id": unit.get("comment_id"),
        "editorial_intent": unit.get("editorial_intent"),
        "scope": plan.get("scope"),
        "section_heading": (unit.get("atomic_location") or {}).get("section_heading", ""),
        "paragraph_index": (unit.get("atomic_location") or {}).get("paragraph_index"),
        "original_fragment": plan.get("original_fragment", ""),
        "raw_fragment": plan.get("raw_fragment", ""),
        "paragraph_before": plan.get("paragraph_before", ""),
        "author_confirmation_reason": unit.get("author_confirmation_reason", ""),
    }


def build_manifest(project_root: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = {
        "workflow": "revise-sci-polish",
        "source_skills": ["article-writing", "review-writing", "humanizer-zh"],
        "scope_rule": "Only polish newly added or modified sentences. Do not rewrite untouched original text.",
        "anti_ai_rules": {
            "forbidden_terms": [
                "delve into",
                "comprehensive landscape",
                "pivotal role",
                "realm",
                "tapestry",
                "underscore",
                "testament",
                "Moreover",
                "Crucial",
                "Landscape",
                "Pivot",
                "Foster",
                "Spearhead",
            ],
            "forbidden_structures": [
                "not only... but also",
                "from A to B",
                "trailing -ing clause",
                "em dash",
            ],
            "style_constraints": [
                "Keep scientific meaning unchanged.",
                "Do not add citations, data, statistics, mechanisms, or claims.",
                "Stay within roughly ±15% of the raw changed fragment length.",
                "Prefer direct, evidence-bounded wording.",
                "Vary sentence rhythm but avoid decorative transitions.",
            ],
        },
        "output_schema": {"results": [{"comment_id": "R1-Major-01", "polished_fragment": "..." }]},
        "candidates": [candidate_payload(unit) for unit in candidates],
    }
    write_json(project_root / "revision_polish_manifest.json", manifest)
    return manifest


def build_polish_prompt(project_root: Path, output_path: Path, candidates: list[dict[str, Any]]) -> str:
    lines = [
        "# Revise-Sci Revision Polishing Task",
        "",
        f"PROJECT_ROOT={project_root.resolve()}",
        f"OUTPUT_JSON_PATH={output_path.resolve()}",
        "",
        "You are polishing manuscript revisions for a revise-sci project.",
        "Use article-writing, review-writing, and humanizer-zh constraints together.",
        "",
        "Hard constraints:",
        "1. Polish only the provided changed fragment. Do not rewrite untouched source text.",
        "2. Keep the scientific claim and evidence boundary unchanged.",
        "3. Do not add data, mechanisms, references, statistics, figure references, or stronger conclusions.",
        "4. Remove AI-style wording and templated transitions.",
        "5. Keep the output concise and close in length to the raw changed fragment.",
        "6. Avoid these terms and structures: delve into, comprehensive landscape, pivotal role, realm, tapestry, underscore, testament, Moreover, Crucial, Landscape, Pivot, Foster, Spearhead, not only... but also, trailing -ing clauses, em dash.",
        "",
        "Return only JSON with a top-level `results` array.",
        "Each row must contain `comment_id` and `polished_fragment`.",
        "",
        "Candidates:",
    ]
    for unit in candidates:
        payload = candidate_payload(unit)
        lines.extend(
            [
                f"- {payload['comment_id']} | scope={payload['scope']} | section={payload['section_heading']} | paragraph_index={payload['paragraph_index']}",
                f"  original_fragment: {payload['original_fragment'] or '无'}",
                f"  raw_fragment: {payload['raw_fragment'] or '无'}",
            ]
        )
    return "\n".join(lines) + "\n"


def validate_output_payload(payload: Any, candidates: list[dict[str, Any]]) -> list[str]:
    rows = payload.get("results", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return ["revision polish output must be a list or {'results': [...]} payload"]
    valid_ids = {unit.get("comment_id") for unit in candidates}
    errors: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append("revision polish rows must be JSON objects")
            continue
        comment_id = normalize_ws(str(row.get("comment_id", "")))
        fragment = normalize_ws(str(row.get("polished_fragment", "")))
        if not comment_id or comment_id not in valid_ids:
            errors.append("revision polish row has an unknown comment_id")
        if not fragment:
            errors.append(f"revision polish row {comment_id or '<unknown>'} is missing polished_fragment")
    return errors


def run_polish_driver(
    project_root: Path,
    candidates: list[dict[str, Any]],
    runner: str,
    opencode_driver: str,
) -> tuple[str, dict[str, Any] | None, dict[str, Any]]:
    output_path = project_root / "revision_polish_results.json"
    prompt = build_polish_prompt(project_root, output_path, candidates)
    write_text(project_root / "revision_polish_prompt.md", prompt)
    if not candidates:
        return "not-required", {"results": []}, {"ok": True, "driver_mode": "not-required", "result_rows": 0}

    if runner:
        command = shlex.split(runner) + ["--input-json", str(project_root / "revision_polish_manifest.json"), "--output", str(output_path), "--project-root", str(project_root)]
        completed = subprocess.run(command, text=True, capture_output=True)
        if completed.returncode == 0 and output_path.exists():
            payload = read_json(output_path, None)
            errors = validate_output_payload(payload, candidates)
            if not errors:
                rows = payload.get("results", []) if isinstance(payload, dict) else payload
                return "local-runner", payload, {"ok": True, "driver_mode": "local-runner", "command": command, "result_rows": len(rows)}
        return "local-heuristic-fallback", None, {
            "ok": True,
            "driver_mode": "local-heuristic-fallback",
            "fallback_reason": "configured revision polish runner failed or produced invalid output",
            "command": command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    if opencode_driver:
        command = shlex.split(opencode_driver) + ["--dir", str(project_root), prompt]
        completed = subprocess.run(command, text=True, capture_output=True)
        if completed.returncode == 0 and output_path.exists():
            payload = read_json(output_path, None)
            errors = validate_output_payload(payload, candidates)
            if not errors:
                rows = payload.get("results", []) if isinstance(payload, dict) else payload
                return "opencode-driver", payload, {"ok": True, "driver_mode": "opencode-driver", "command": command, "result_rows": len(rows)}
        return "local-heuristic-fallback", None, {
            "ok": True,
            "driver_mode": "local-heuristic-fallback",
            "fallback_reason": "opencode polish driver failed or produced invalid output",
            "command": command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    return "local-heuristic", None, {
        "ok": True,
        "driver_mode": "local-heuristic",
        "result_rows": len(candidates),
    }


def fragment_map_from_payload(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return {}
    rows = payload.get("results", []) if isinstance(payload, dict) else payload
    mapping: dict[str, str] = {}
    for row in rows or []:
        mapping[normalize_ws(str(row.get("comment_id", "")))] = normalize_ws(str(row.get("polished_fragment", "")))
    return mapping


def apply_polished_fragment(plan: dict[str, Any], polished_fragment: str) -> str:
    scope = plan.get("scope")
    paragraph_before = normalize_ws(plan.get("paragraph_before", ""))
    if scope == "sentence_replace":
        return revise_units.replace_sentence_at(paragraph_before, int(plan.get("target_sentence_index") or 0), polished_fragment)
    if scope == "sentence_append":
        return revise_units.append_sentence_to_paragraph(paragraph_before, polished_fragment)
    if scope == "paragraph_replace":
        return normalize_ws(polished_fragment)
    return normalize_ws(plan.get("paragraph_after_raw", paragraph_before))


def update_indexes(
    project_root: Path,
    manuscript_index: dict[str, Any],
    si_index: dict[str, Any],
    processed_units: list[dict[str, Any]],
) -> None:
    updated_text_by_section_paragraph: dict[tuple[str, int], str] = {}
    for unit in processed_units:
        if unit.get("status") != "completed":
            continue
        atomic = unit.get("atomic_location") or {}
        section_id = atomic.get("manuscript_section_id") or atomic.get("si_section_id")
        paragraph_index = atomic.get("paragraph_index")
        if not section_id or paragraph_index is None:
            continue
        updated_text_by_section_paragraph[(section_id, int(paragraph_index))] = unit.get("revised_excerpt_en", "")

    for index_name, index_data in (
        ("manuscript_section_index.json", manuscript_index),
        ("si_section_index.json", si_index),
    ):
        for section in index_data.get("sections", []):
            for paragraph in section.get("paragraphs", []):
                key = (section.get("section_id"), int(paragraph.get("paragraph_index")))
                if key in updated_text_by_section_paragraph:
                    paragraph["current_text"] = updated_text_by_section_paragraph[key]
            write_text(project_root / section["file"], build_section_markdown(section))
        write_json(project_root / index_name, index_data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Polish only revised fragments while preserving untouched manuscript text")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--revision-polish-runner", default="")
    parser.add_argument("--opencode-driver-command", default="")
    parser.add_argument("--disable-opencode-driver", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    manuscript_index = read_json(project_root / "manuscript_section_index.json", {"sections": []})
    si_index = read_json(project_root / "si_section_index.json", {"sections": []})
    units_paths = sorted((project_root / "units").glob("*.json"))
    units = [read_json(path, {}) for path in units_paths]
    candidates = polish_candidates(units)
    build_manifest(project_root, candidates)

    runner = normalize_ws(args.revision_polish_runner or os.environ.get("REVISE_SCI_REVISION_POLISH_RUNNER", ""))
    opencode_driver = normalize_ws(
        args.opencode_driver_command
        or os.environ.get("REVISE_SCI_REVISION_POLISH_OPENCODE_DRIVER_COMMAND", "")
        or ("opencode run" if shutil.which("opencode") and not args.disable_opencode_driver else "")
    )

    driver_mode, payload, execution = run_polish_driver(project_root, candidates, runner, opencode_driver)
    fragment_map = fragment_map_from_payload(payload)

    processed_units: list[dict[str, Any]] = []
    polished_comment_ids: list[str] = []
    for unit_path, unit in zip(units_paths, units):
        plan = unit.get("revision_plan") or {}
        if unit.get("status") == "completed" and plan.get("scope") not in {"", "none", None}:
            raw_fragment = normalize_ws(fragment_map.get(unit.get("comment_id", ""), plan.get("raw_fragment", "")))
            polished_fragment = polish_changed_text_locally(raw_fragment)
            polished_paragraph = apply_polished_fragment(plan, polished_fragment)
            unit["revised_excerpt_en"] = polished_paragraph
            unit["revision_plan"]["polished_fragment"] = polished_fragment
            unit["revision_plan"]["paragraph_after_polished"] = polished_paragraph
            unit["polish_applied"] = True
            unit["polish_driver_mode"] = driver_mode
            unit["polish_guard_ok"] = len(find_ai_style_markers(polished_fragment)) == 0
            polished_comment_ids.append(unit.get("comment_id"))
        else:
            unit["polish_applied"] = False
            unit["polish_driver_mode"] = "not-required"
            unit["polish_guard_ok"] = True
        processed_units.append(unit)
        write_json(unit_path, unit)
        write_text(project_root / "comment_records" / f"{unit['comment_id']}.md", revise_units.render_comment_record(unit))

    update_indexes(project_root, manuscript_index, si_index, processed_units)
    write_text(project_root / "response_to_reviewers.md", revise_units.render_response_to_reviewers(processed_units))
    write_text(project_root / "manuscript_edit_plan.md", revise_units.render_edit_plan(processed_units))

    state = read_json(project_root / "project_state.json", {})
    state["revision_polish"] = {
        "driver_mode": driver_mode,
        "candidate_count": len(candidates),
        "polished_comment_ids": polished_comment_ids,
    }
    write_json(project_root / "project_state.json", state)

    execution["candidate_count"] = len(candidates)
    execution["polished_comment_ids"] = polished_comment_ids
    write_json(project_root / "revision_polish_execution.json", execution)
    print(json.dumps({"ok": True, "driver_mode": driver_mode, "candidate_count": len(candidates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

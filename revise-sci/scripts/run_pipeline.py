#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from common import autodiscover_reference_source, compute_tree_signature, directory_signature, path_signature, read_json

STEP_ORDER = (
    "preflight",
    "citation_guard",
    "atomize_comments",
    "atomize_manuscript",
    "issue_index",
    "revise",
    "literature",
    "reference_registry",
    "export",
    "final_report",
    "gate",
)
REFERENCE_SEARCH_DECISIONS = ("ask", "approved", "declined")


def run_step(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def has_units(project_root: Path) -> bool:
    return (project_root / "units").exists() and any((project_root / "units").glob("*.json"))


def has_manuscript_sections(project_root: Path) -> bool:
    return (project_root / "manuscript_section_index.json").exists() and any((project_root / "manuscript_sections").glob("*.md"))


def has_issue_index(project_root: Path) -> bool:
    return (project_root / "index.json").exists() and (project_root / "issue_matrix.md").exists()


def has_revision_outputs(project_root: Path) -> bool:
    return (
        (project_root / "response_to_reviewers.md").exists()
        and (project_root / "manuscript_edit_plan.md").exists()
        and (project_root / "comment_records").exists()
        and any((project_root / "comment_records").glob("*.md"))
    )


def has_citation_guard_outputs(project_root: Path) -> bool:
    return (project_root / "paper_search_guard_report.json").exists() and (project_root / "paper_search_validated.json").exists()


def has_literature_outputs(project_root: Path) -> bool:
    return (
        (project_root / "data" / "literature_index.json").exists()
        and (project_root / "data" / "synthesis_matrix.json").exists()
        and (project_root / "data" / "synthesis_matrix_audit.json").exists()
    )


def has_reference_registry_outputs(project_root: Path) -> bool:
    return (
        (project_root / "data" / "reference_registry.json").exists()
        and (project_root / "data" / "reference_coverage_audit.json").exists()
    )


def resolve_references_source(args: argparse.Namespace) -> Path | None:
    if getattr(args, "references_source", ""):
        return Path(args.references_source).resolve()
    comments = Path(args.comments)
    manuscript = Path(args.manuscript)
    attachments = Path(args.attachments_dir) if getattr(args, "attachments_dir", "") else None
    project_root = Path(args.project_root)
    return autodiscover_reference_source(comments, attachments, project_root, manuscript)


def current_input_signatures(args: argparse.Namespace) -> dict:
    references_source = resolve_references_source(args)
    return {
        "comments_path": path_signature(Path(args.comments)),
        "manuscript_docx_path": path_signature(Path(args.manuscript)),
        "si_docx_path": path_signature(Path(args.si)) if args.si else path_signature(None),
        "attachments_dir_path": directory_signature(Path(args.attachments_dir)) if args.attachments_dir else directory_signature(None),
        "reference_docx_path": path_signature(Path(args.reference_docx)) if args.reference_docx else path_signature(None),
        "paper_search_results_path": path_signature(Path(args.paper_search_results)) if args.paper_search_results else path_signature(None),
        "references_source_path": path_signature(references_source),
        "reference_search_decision": getattr(args, "reference_search_decision", "ask"),
    }


def resume_inputs_changed(project_root: Path, args: argparse.Namespace) -> list[str]:
    state = read_json(project_root / "project_state.json", {})
    previous = state.get("input_signatures", {})
    current = current_input_signatures(args)
    changed = []
    for key, value in current.items():
        if previous.get(key) != value:
            changed.append(key)
    return changed


def current_skill_signature(script_dir: Path) -> str:
    return compute_tree_signature(script_dir.parent, patterns=("*.py", "*.md"))


def clear_project_outputs(project_root: Path) -> None:
    removable_dirs = [
        "units",
        "manuscript_sections",
        "si_sections",
        "comment_records",
        "data",
    ]
    removable_files = [
        "precheck_report.md",
        "attachments_manifest.json",
        "project_state.json",
        "index.json",
        "issue_matrix.md",
        "manuscript_section_index.json",
        "si_section_index.json",
        "response_to_reviewers.md",
        "response_to_reviewers.docx",
        "manuscript_edit_plan.md",
        "final_consistency_report.md",
        "paper_search_guard_report.json",
        "paper_search_validated.json",
        "literature_index_report.json",
        "reference_sync_report.json",
        "reference_search_manifest.json",
        "reference_search_task.md",
        "reference_search_strategy.json",
        "reference_search_status.json",
        "reference_search_rounds.json",
    ]
    for dirname in removable_dirs:
        path = project_root / dirname
        if path.exists():
            shutil.rmtree(path)
    for filename in removable_files:
        path = project_root / filename
        if path.exists():
            path.unlink()


def clear_step_outputs(project_root: Path, output_md: Path, output_docx: Path, step_name: str) -> None:
    if step_name == "preflight":
        clear_project_outputs(project_root)
        for artifact in (output_md, output_docx):
            if artifact.exists():
                artifact.unlink()
        return

    if step_name == "citation_guard":
        for filename in ("paper_search_guard_report.json", "paper_search_validated.json"):
            path = project_root / filename
            if path.exists():
                path.unlink()
        return

    if step_name == "atomize_comments":
        units_dir = project_root / "units"
        if units_dir.exists():
            shutil.rmtree(units_dir)
        return

    if step_name == "atomize_manuscript":
        for dirname in ("manuscript_sections", "si_sections"):
            path = project_root / dirname
            if path.exists():
                shutil.rmtree(path)
        for filename in ("manuscript_section_index.json", "si_section_index.json"):
            path = project_root / filename
            if path.exists():
                path.unlink()
        return

    if step_name == "issue_index":
        for filename in ("index.json", "issue_matrix.md"):
            path = project_root / filename
            if path.exists():
                path.unlink()
        return

    if step_name == "revise":
        records_dir = project_root / "comment_records"
        if records_dir.exists():
            shutil.rmtree(records_dir)
        for filename in ("response_to_reviewers.md", "response_to_reviewers.docx", "manuscript_edit_plan.md"):
            path = project_root / filename
            if path.exists():
                path.unlink()
        return

    if step_name == "literature":
        data_dir = project_root / "data"
        for filename in ("literature_index.json", "synthesis_matrix.json", "synthesis_matrix_audit.json", "literature_index_report.json"):
            path = data_dir / filename
            if path.exists():
                path.unlink()
        return

    if step_name == "reference_registry":
        data_dir = project_root / "data"
        for filename in ("reference_registry.json", "reference_coverage_audit.json"):
            path = data_dir / filename
            if path.exists():
                path.unlink()
        for filename in ("reference_sync_report.json", "reference_recovery_request.md"):
            path = project_root / filename
            if path.exists():
                path.unlink()
        for filename in ("reference_search_manifest.json", "reference_search_task.md", "reference_search_strategy.json", "reference_search_status.json", "reference_search_rounds.json"):
            path = project_root / filename
            if path.exists():
                path.unlink()
        if output_md.exists():
            output_md.unlink()
        return

    if step_name == "export":
        for artifact in (project_root / "response_to_reviewers.docx", output_docx):
            if artifact.exists():
                artifact.unlink()
        return

    if step_name == "final_report":
        report_path = project_root / "final_consistency_report.md"
        if report_path.exists():
            report_path.unlink()
        return


def clear_outputs_from_step(project_root: Path, output_md: Path, output_docx: Path, start_step: str) -> None:
    start_index = STEP_ORDER.index(start_step)
    for step_name in STEP_ORDER[start_index:]:
        clear_step_outputs(project_root, output_md, output_docx, step_name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the revise-sci pipeline end to end")
    parser.add_argument("--comments", required=True)
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--si", default="")
    parser.add_argument("--attachments-dir", default="")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-docx", required=True)
    parser.add_argument("--reference-docx", default="")
    parser.add_argument("--paper-search-results", default="")
    parser.add_argument("--references-source", default="")
    parser.add_argument("--reference-search-decision", choices=REFERENCE_SEARCH_DECISIONS, default="ask")
    parser.add_argument("--live-citation-verify", action="store_true")
    parser.add_argument("--offline-citation-verify", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resume-from", choices=STEP_ORDER)
    parser.add_argument("--force-rebuild", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = Path(args.project_root)
    output_md_path = Path(args.output_md)
    output_docx_path = Path(args.output_docx)
    py = sys.executable
    resolved_references_source = str(resolve_references_source(args) or "")
    skill_signature = current_skill_signature(script_dir)

    if args.resume and args.force_rebuild:
        print("--resume and --force-rebuild cannot be used together", file=sys.stderr)
        raise SystemExit(2)
    if args.resume_from and not args.resume:
        print("--resume-from requires --resume", file=sys.stderr)
        raise SystemExit(2)
    if args.live_citation_verify and args.offline_citation_verify:
        print("--live-citation-verify and --offline-citation-verify cannot be used together", file=sys.stderr)
        raise SystemExit(2)

    if args.force_rebuild:
        project_root.mkdir(parents=True, exist_ok=True)
        clear_project_outputs(project_root)

    if args.resume:
        state = read_json(project_root / "project_state.json", {})
        previous_skill_signature = state.get("skill_signature", "")
        if previous_skill_signature and previous_skill_signature != skill_signature:
            print("resume skill version changed", file=sys.stderr)
            raise SystemExit(1)
        changed_inputs = resume_inputs_changed(project_root, args)
        if changed_inputs:
            print(f"resume inputs changed: {', '.join(changed_inputs)}", file=sys.stderr)
            raise SystemExit(1)
        if args.resume_from:
            clear_outputs_from_step(project_root, output_md_path, output_docx_path, args.resume_from)

    common_args = [
        "--comments",
        args.comments,
        "--manuscript",
        args.manuscript,
        "--project-root",
        args.project_root,
        "--output-md",
        args.output_md,
        "--output-docx",
        args.output_docx,
        "--reference-search-decision",
        args.reference_search_decision,
    ]
    if args.si:
        common_args.extend(["--si", args.si])
    if args.attachments_dir:
        common_args.extend(["--attachments-dir", args.attachments_dir])
    if args.reference_docx:
        common_args.extend(["--reference-docx", args.reference_docx])
    if args.paper_search_results:
        common_args.extend(["--paper-search-results", args.paper_search_results])
    if resolved_references_source:
        common_args.extend(["--references-source", resolved_references_source])
    if args.live_citation_verify or (args.paper_search_results and not args.offline_citation_verify):
        common_args.append("--live-citation-verify")

    if not args.resume or not (project_root / "precheck_report.md").exists():
        run_step([py, str(script_dir / "preflight.py")] + common_args)
    if args.paper_search_results and (not args.resume or not has_citation_guard_outputs(project_root)):
        guard_args = [
            py,
            str(script_dir / "citation_guard.py"),
            "--paper-search-results",
            args.paper_search_results,
            "--project-root",
            args.project_root,
            "--allow-unverified",
        ]
        if args.offline_citation_verify:
            guard_args.append("--offline")
        else:
            guard_args.append("--live")
        run_step(guard_args)
    if not args.resume or not has_units(project_root):
        run_step([py, str(script_dir / "atomize_comments.py"), "--comments", args.comments, "--project-root", args.project_root])
    if not args.resume or not has_manuscript_sections(project_root):
        atomize_doc_args = [py, str(script_dir / "atomize_manuscript.py"), "--manuscript", args.manuscript, "--project-root", args.project_root]
        if args.si:
            atomize_doc_args.extend(["--si", args.si])
        run_step(atomize_doc_args)
    if not args.resume or not has_issue_index(project_root):
        run_step([py, str(script_dir / "build_issue_matrix.py"), "--project-root", args.project_root])
    if not args.resume or not has_revision_outputs(project_root):
        revise_args = [py, str(script_dir / "revise_units.py"), "--project-root", args.project_root]
        if args.paper_search_results:
            revise_args.extend(["--paper-search-results", str(project_root / "paper_search_validated.json")])
        run_step(revise_args)
        run_step([py, str(script_dir / "build_issue_matrix.py"), "--project-root", args.project_root])
    elif args.resume:
        run_step([py, str(script_dir / "build_issue_matrix.py"), "--project-root", args.project_root])
    if not args.resume or not has_literature_outputs(project_root):
        run_step([py, str(script_dir / "build_literature_index.py"), "--project-root", args.project_root])
        run_step(
            [
                py,
                str(script_dir / "matrix_manager.py"),
                "bootstrap",
                "--index",
                str(project_root / "data" / "literature_index.json"),
                "--matrix",
                str(project_root / "data" / "synthesis_matrix.json"),
                "--round",
                "2",
            ]
        )
        run_step(
            [
                py,
                str(script_dir / "matrix_manager.py"),
                "audit",
                "--matrix",
                str(project_root / "data" / "synthesis_matrix.json"),
                "--report",
                str(project_root / "data" / "synthesis_matrix_audit.json"),
            ]
        )
    run_step([py, str(script_dir / "merge_manuscript.py"), "--project-root", args.project_root, "--output-md", args.output_md])
    run_step([py, str(script_dir / "reference_sync.py"), "--project-root", args.project_root, "--output-md", args.output_md])
    if not args.resume or not has_reference_registry_outputs(project_root):
        reference_registry_args = [py, str(script_dir / "build_reference_registry.py"), "--project-root", args.project_root, "--output-md", args.output_md]
        if resolved_references_source:
            reference_registry_args.extend(["--references-source", resolved_references_source])
        reference_registry_args.extend(["--reference-search-decision", args.reference_search_decision])
        run_step(reference_registry_args)
    export_args = [
        py,
        str(script_dir / "export_docx.py"),
        "--project-root",
        args.project_root,
        "--output-md",
        args.output_md,
        "--output-docx",
        args.output_docx,
    ]
    if args.reference_docx:
        export_args.extend(["--reference-docx", args.reference_docx])
    run_step(export_args)
    run_step([py, str(script_dir / "final_consistency_report.py"), "--project-root", args.project_root])
    run_step([py, str(script_dir / "strict_gate.py"), "--project-root", args.project_root])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

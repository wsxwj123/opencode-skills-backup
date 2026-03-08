#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = Path(args.project_root)
    py = sys.executable
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
    ]
    if args.si:
        common_args.extend(["--si", args.si])
    if args.attachments_dir:
        common_args.extend(["--attachments-dir", args.attachments_dir])
    if args.reference_docx:
        common_args.extend(["--reference-docx", args.reference_docx])
    if args.paper_search_results:
        common_args.extend(["--paper-search-results", args.paper_search_results])

    if not args.resume or not (project_root / "precheck_report.md").exists():
        run_step([py, str(script_dir / "preflight.py")] + common_args)
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
            revise_args.extend(["--paper-search-results", args.paper_search_results])
        run_step(revise_args)
        run_step([py, str(script_dir / "build_issue_matrix.py"), "--project-root", args.project_root])
    elif args.resume:
        run_step([py, str(script_dir / "build_issue_matrix.py"), "--project-root", args.project_root])
    run_step([py, str(script_dir / "merge_manuscript.py"), "--project-root", args.project_root, "--output-md", args.output_md])
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

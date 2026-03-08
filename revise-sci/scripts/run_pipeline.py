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
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
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

    run_step([py, str(script_dir / "preflight.py")] + common_args)
    run_step([py, str(script_dir / "atomize_comments.py"), "--comments", args.comments, "--project-root", args.project_root])
    atomize_doc_args = [py, str(script_dir / "atomize_manuscript.py"), "--manuscript", args.manuscript, "--project-root", args.project_root]
    if args.si:
        atomize_doc_args.extend(["--si", args.si])
    run_step(atomize_doc_args)
    run_step([py, str(script_dir / "build_issue_matrix.py"), "--project-root", args.project_root])
    run_step([py, str(script_dir / "revise_units.py"), "--project-root", args.project_root])
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

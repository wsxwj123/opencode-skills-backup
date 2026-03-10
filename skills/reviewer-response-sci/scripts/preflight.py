#!/usr/bin/env python3
"""Preflight checks before running reviewer-response pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def check_docx_path(p: Path, label: str, errors: list[str]) -> None:
    if not p.exists():
        errors.append(f"Missing {label}: {p}")
        return
    if p.suffix.lower() != ".docx":
        errors.append(f"{label} must be .docx: {p}")
    if p.stat().st_size == 0:
        errors.append(f"{label} is empty: {p}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for reviewer-response pipeline")
    parser.add_argument("--comments", required=True)
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--si", default="")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-html", required=True)
    args = parser.parse_args()

    errors: list[str] = []

    comments = Path(args.comments)
    manuscript = Path(args.manuscript)
    si = Path(args.si) if args.si else None
    project_root = Path(args.project_root)
    output_html = Path(args.output_html)

    check_docx_path(comments, "comments_docx", errors)
    check_docx_path(manuscript, "manuscript_docx", errors)
    if si:
        check_docx_path(si, "si_docx", errors)

    # Output path sanity
    if output_html.suffix.lower() != ".html":
        errors.append(f"output_html must end with .html: {output_html}")

    # Project root must be creatable/writable
    try:
        project_root.mkdir(parents=True, exist_ok=True)
        probe = project_root / ".preflight_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        errors.append(f"project_root not writable: {project_root} ({e})")

    # python-docx availability
    try:
        import docx  # type: ignore # noqa: F401
    except Exception as e:  # noqa: BLE001
        errors.append(f"python-docx unavailable: {e}")

    if errors:
        print("PREFLIGHT: FAIL")
        for e in errors:
            print(f"- {e}")
        return 1

    summary = {
        "comments_docx": str(comments.resolve()),
        "manuscript_docx": str(manuscript.resolve()),
        "si_docx": str(si.resolve()) if si else "",
        "project_root": str(project_root.resolve()),
        "output_html": str(output_html.resolve()),
    }
    print("PREFLIGHT: PASS")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

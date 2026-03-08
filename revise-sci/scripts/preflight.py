#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import autodiscover_reference_source, compute_tree_signature, directory_signature, path_signature, write_json, write_text


def describe_file(path: Path) -> dict[str, object]:
    return {
        "name": path.name,
        "path": str(path.resolve()),
        "size": path.stat().st_size,
    }


def build_report(summary: dict[str, object], attachments: dict[str, object], missing_items: list[str]) -> str:
    lines = [
        "# 预检报告",
        "",
        "## 输入摘要",
        f"- comments_path: `{summary['comments_path']}`",
        f"- manuscript_docx_path: `{summary['manuscript_docx_path']}`",
        f"- si_docx_path: `{summary['si_docx_path'] or 'Not provided by user'}`",
        f"- attachments_dir_path: `{summary['attachments_dir_path'] or 'Not provided by user'}`",
        f"- project_root: `{summary['project_root']}`",
        f"- output_md_path: `{summary['output_md_path']}`",
        f"- output_docx_path: `{summary['output_docx_path']}`",
        f"- reference_docx_path: `{summary['reference_docx_path'] or 'Not provided by user'}`",
        f"- paper_search_results_path: `{summary['paper_search_results_path'] or 'Not provided by user'}`",
        f"- references_source_path: `{summary['references_source_path'] or 'Not provided by user'}`",
        f"- reference_search_decision: `{summary['reference_search_decision']}`",
        f"- citation_verify_mode: `{summary['citation_verify_mode']}`",
        "",
        "## 附件清单",
        f"- 附件数量: `{attachments['count']}`",
    ]
    for item in attachments["files"]:
        lines.append(f"- {item['name']} ({item['size']} bytes)")
    lines.extend(["", "## 缺失项"])
    if missing_items:
        for item in missing_items:
            lines.append(f"- {item}")
    else:
        lines.append("- 无")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for revise-sci")
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
    parser.add_argument("--reference-search-decision", choices=("ask", "approved", "declined"), default="ask")
    parser.add_argument("--live-citation-verify", action="store_true")
    args = parser.parse_args()

    comments = Path(args.comments)
    manuscript = Path(args.manuscript)
    si = Path(args.si) if args.si else None
    attachments_dir = Path(args.attachments_dir) if args.attachments_dir else None
    project_root = Path(args.project_root)
    output_md = Path(args.output_md)
    output_docx = Path(args.output_docx)
    reference_docx = Path(args.reference_docx) if args.reference_docx else None
    paper_search_results = Path(args.paper_search_results) if args.paper_search_results else None
    references_source = (
        Path(args.references_source)
        if args.references_source
        else autodiscover_reference_source(comments, attachments_dir, project_root, manuscript)
    )

    errors: list[str] = []
    missing_items: list[str] = []

    if not comments.exists():
        errors.append(f"Missing comments file: {comments}")
    elif comments.suffix.lower() not in {".docx", ".html"}:
        errors.append(f"comments_path must be .docx or .html: {comments}")
    if not manuscript.exists() or manuscript.suffix.lower() != ".docx":
        errors.append(f"manuscript_docx_path must be readable .docx: {manuscript}")
    if si is None:
        missing_items.append("si_docx_path")
    elif not si.exists() or si.suffix.lower() != ".docx":
        errors.append(f"si_docx_path must be readable .docx: {si}")
    if attachments_dir is None:
        missing_items.append("attachments_dir_path")
    elif not attachments_dir.exists() or not attachments_dir.is_dir():
        errors.append(f"attachments_dir_path must be a readable directory: {attachments_dir}")
    if reference_docx is None:
        missing_items.append("reference_docx_path")
    elif not reference_docx.exists() or reference_docx.suffix.lower() != ".docx":
        errors.append(f"reference_docx_path must be readable .docx: {reference_docx}")
    if paper_search_results is not None:
        if not paper_search_results.exists():
            errors.append(f"paper_search_results_path must be readable json: {paper_search_results}")
        else:
            try:
                json.loads(paper_search_results.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                errors.append(f"paper_search_results_path must be valid json: {paper_search_results}")
    if references_source is None:
        missing_items.append("references_source_path")
    elif not references_source.exists():
        errors.append(f"references_source_path must be readable: {references_source}")

    project_root.mkdir(parents=True, exist_ok=True)

    attachment_files = []
    if attachments_dir and attachments_dir.exists():
        attachment_files = [describe_file(p) for p in sorted(attachments_dir.iterdir()) if p.is_file()]
    attachments_manifest = {"count": len(attachment_files), "files": attachment_files}

    summary = {
        "comments_path": str(comments.resolve()),
        "manuscript_docx_path": str(manuscript.resolve()),
        "si_docx_path": str(si.resolve()) if si else "",
        "attachments_dir_path": str(attachments_dir.resolve()) if attachments_dir else "",
        "project_root": str(project_root.resolve()),
        "output_md_path": str(output_md.resolve()),
        "output_docx_path": str(output_docx.resolve()),
        "reference_docx_path": str(reference_docx.resolve()) if reference_docx else "",
        "paper_search_results_path": str(paper_search_results.resolve()) if paper_search_results else "",
        "references_source_path": str(references_source.resolve()) if references_source else "",
        "reference_search_decision": args.reference_search_decision,
        "citation_verify_mode": "live" if args.live_citation_verify else "offline",
    }
    skill_root = Path(__file__).resolve().parent.parent
    skill_signature = compute_tree_signature(skill_root, patterns=("*.py", "*.md"))

    write_json(project_root / "attachments_manifest.json", attachments_manifest)
    write_text(project_root / "precheck_report.md", build_report(summary, attachments_manifest, missing_items))
    write_json(
        project_root / "project_state.json",
        {
            "inputs": summary,
            "input_signatures": {
                "comments_path": path_signature(comments),
                "manuscript_docx_path": path_signature(manuscript),
                "si_docx_path": path_signature(si),
                "attachments_dir_path": directory_signature(attachments_dir),
                "reference_docx_path": path_signature(reference_docx),
                "paper_search_results_path": path_signature(paper_search_results),
                "references_source_path": path_signature(references_source),
                "reference_search_decision": args.reference_search_decision,
            },
            "outputs": {
                "response_md": str((project_root / "response_to_reviewers.md").resolve()),
                "response_docx": str((project_root / "response_to_reviewers.docx").resolve()),
            },
            "counts": {"comment_units": 0},
            "missing_items": missing_items,
            "delivery_status": "draft",
            "skill_signature": skill_signature,
        },
    )

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "summary": summary, "missing_items": missing_items}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

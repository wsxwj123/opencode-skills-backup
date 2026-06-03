#!/usr/bin/env python3
"""Merge section files into final manuscript."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ORDER = [
    "00_摘要_中文.md",
    "00_摘要_英文.md",
    "B1_预算说明_直接费用.md",
    "B2_预算说明_合作外拨.md",
    "B3_预算说明_其他来源.md",
    "P1_立项依据.md",
    "P2_研究内容.md",
    "P3_1_研究基础与可行性分析.md",
    "P3_2_工作条件.md",
    "P3_3_正在承担的相关项目.md",
    "P3_4_完成基金项目情况.md",
    "P4_其他需要说明的情况.md",
    "REF_参考文献.md",
]


def _p2_children(sections_dir: Path) -> list[Path]:
    pats = sorted(sections_dir.glob("P2_*.md"))
    children = [p for p in pats if p.name != "P2_研究内容.md"]

    def key(p: Path):
        m = re.match(r"P2_([0-9.]+)_", p.name)
        if not m:
            return (999,)
        return tuple(int(x) for x in m.group(1).split("."))

    return sorted(children, key=key)


def validate_order(sections_dir: Path) -> dict:
    present = {p.name for p in sections_dir.glob("*.md")}
    required = set(ORDER) - {"P2_研究内容.md"}

    missing = sorted(x for x in required if x not in present)
    if "P2_研究内容.md" not in present:
        p2_parts = _p2_children(sections_dir)
        if not p2_parts:
            missing.append("P2_研究内容.md or P2_xxx split files")

    return {
        "ok": not missing,
        "missing": missing,
        "present_count": len(present),
    }


def merge(sections_dir: Path, output_path: Path) -> list[str]:
    merged: list[str] = []
    used = []
    for name in ORDER:
        p = sections_dir / name
        if name == "P2_研究内容.md" and not p.exists():
            for c in _p2_children(sections_dir):
                merged.append(c.read_text(encoding="utf-8").strip())
                used.append(c.name)
            continue
        if p.exists():
            merged.append(p.read_text(encoding="utf-8").strip())
            used.append(name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n\f\n\n".join(x for x in merged if x), encoding="utf-8")
    return used


def merge_selected(sections_dir: Path, selected: list[str], output_path: Path) -> list[str]:
    merged: list[str] = []
    used: list[str] = []

    allowed = set(ORDER) | {"P2"}
    normalized: list[str] = []
    for item in selected:
        key = item.strip()
        if not key:
            continue
        if key == "P2":
            normalized.append("P2_研究内容.md")
            continue
        if key.endswith(".md"):
            normalized.append(key)
        elif key in ORDER:
            normalized.append(key)
        else:
            normalized.append(f"{key}.md")

    for name in normalized:
        if name not in allowed:
            continue
        p = sections_dir / name
        if name == "P2_研究内容.md" and not p.exists():
            for c in _p2_children(sections_dir):
                merged.append(c.read_text(encoding="utf-8").strip())
                used.append(c.name)
            continue
        if p.exists():
            merged.append(p.read_text(encoding="utf-8").strip())
            used.append(name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n\f\n\n".join(x for x in merged if x), encoding="utf-8")
    return used


def merge_docx(md_path: Path, docx_path: Path) -> dict:
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["pandoc", str(md_path), "-o", str(docx_path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return {"ok": False, "error": "pandoc not found"}

    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip()[:500]}
    return {"ok": True, "output": str(docx_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_merge = sub.add_parser("merge")
    p_merge.add_argument("--sections-dir", default="sections")
    p_merge.add_argument("--output", default="output/申请书_合并.md")
    p_merge.add_argument("--only", default="", help="Comma-separated section filenames or aliases, e.g. P1_立项依据.md,P2,REF_参考文献.md")

    p_docx = sub.add_parser("merge-docx")
    p_docx.add_argument("--input", default="output/申请书_合并.md")
    p_docx.add_argument("--output", default="output/申请书_合并.docx")

    p_valid = sub.add_parser("validate-order")
    p_valid.add_argument("--sections-dir", default="sections")

    args = parser.parse_args()

    if args.cmd == "validate-order":
        print(json.dumps(validate_order(Path(args.sections_dir)), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "merge":
        sections_dir = Path(args.sections_dir)
        if args.only.strip():
            selected = [x.strip() for x in args.only.split(",") if x.strip()]
            used = merge_selected(sections_dir, selected, Path(args.output))
            if not used:
                print(json.dumps({"ok": False, "error": "no selected sections found", "only": selected}, ensure_ascii=False, indent=2))
                return 2
        else:
            valid = validate_order(sections_dir)
            if not valid["ok"]:
                print(json.dumps(valid, ensure_ascii=False, indent=2))
                return 2
            used = merge(sections_dir, Path(args.output))
        print(json.dumps({"ok": True, "output": args.output, "merged_files": used}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "merge-docx":
        result = merge_docx(Path(args.input), Path(args.output))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

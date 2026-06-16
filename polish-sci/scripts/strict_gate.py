#!/usr/bin/env python3
"""Delivery gate for polish-sci. Fail-closed: any breach -> exit 1.

交付前对每个 polished 单元逐项核验,任一不过即 exit 1,阻断"声明润色完成":
  · numbers_ok        数值/统计量集合与原文一致(numeric_tokens_preserved)
  · certainty_ok      不确定性动词未升级(detect_certainty_upgrade)
  · citations_ok      引用标记 [n] / DOI 集合不变
  · no AI markers     find_ai_style_markers 无残留
  · meaning 未变      meaning_changed=false
  · 非占位            polished_by != PLACEHOLDER(确认确实润色过)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import (
    detect_certainty_upgrade,
    find_ai_style_markers,
    normalize_ws,
    numeric_tokens_preserved,
    read_json,
)

CITATION_RE = re.compile(r"\[\d+(?:\s*[-,]\s*\d+)*\]", re.IGNORECASE)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"]+", re.IGNORECASE)


def citation_set(text: str) -> set[str]:
    norm = normalize_ws(text)
    cites = {re.sub(r"\s+", "", m.group(0)) for m in CITATION_RE.finditer(norm)}
    cites |= {m.group(0).lower() for m in DOI_RE.finditer(norm)}
    return cites


def check_unit(unit: dict) -> tuple[bool, list[str]]:
    raw = unit.get("raw_text", "")
    polished = unit.get("polished_text", "")
    problems: list[str] = []

    if unit.get("polished_by") == "PLACEHOLDER":
        problems.append("unit not polished (PLACEHOLDER)")

    num = numeric_tokens_preserved(raw, polished)
    if not num["ok"]:
        problems.append(f"numeric changed: introduced={num['introduced']} dropped={num['dropped']}")

    cert = detect_certainty_upgrade(raw, polished)
    if not cert["ok"]:
        problems.append(f"certainty upgraded: {cert['introduced_strong_verbs']}")

    raw_cites, pol_cites = citation_set(raw), citation_set(polished)
    if raw_cites != pol_cites:
        problems.append(f"citations changed: lost={sorted(raw_cites - pol_cites)} added={sorted(pol_cites - raw_cites)}")

    markers = find_ai_style_markers(polished)
    if markers:
        problems.append(f"ai markers: {markers}")

    if bool(unit.get("meaning_changed", False)):
        problems.append("meaning_changed=true")

    return (not problems, problems)


def main() -> int:
    parser = argparse.ArgumentParser(description="polish-sci delivery gate (fail-closed)")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    polished_dir = project_root / "polished"
    index = read_json(project_root / "units_index.json", {"units": []})
    entries = index.get("units", [])

    if not entries:
        sys.stderr.write("[strict_gate] units_index.json 为空或缺失\n")
        print("STRICT_GATE: FAIL")
        return 1

    failures: list[dict] = []
    for entry in entries:
        idx = entry["idx"]
        unit = read_json(polished_dir / f"{idx}.json", None)
        if unit is None:
            failures.append({"idx": idx, "problems": ["polished unit missing"]})
            continue
        ok, problems = check_unit(unit)
        if not ok:
            failures.append({"idx": idx, "problems": problems})

    summary = {"checked": len(entries), "failed": len(failures), "failures": failures}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        print("STRICT_GATE: FAIL")
        sys.stderr.write("[strict_gate] fail-closed:不得向用户声明润色完成。\n")
        return 1
    print("STRICT_GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

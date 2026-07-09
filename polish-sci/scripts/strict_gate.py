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
    named_tokens_preserved,
    normalize_ws,
    numeric_order_preserved,
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


def citation_order(text: str) -> list[str]:
    """引用标记按文档顺序排成序列。[3][5] 绑的两句互换位置会改变顺序,
    集合比对看不出,顺序比对拦得下。"""
    norm = normalize_ws(text)
    return [re.sub(r"\s+", "", m.group(0)) for m in CITATION_RE.finditer(norm)]


def check_unit(unit: dict) -> tuple[bool, list[str]]:
    raw = unit.get("raw_text", "")
    polished = unit.get("polished_text", "")
    problems: list[str] = []

    if unit.get("polished_by") == "PLACEHOLDER":
        problems.append("unit not polished (PLACEHOLDER)")

    num = numeric_tokens_preserved(raw, polished)
    if not num["ok"]:
        problems.append(f"numeric changed: introduced={num['introduced']} dropped={num['dropped']}")

    numo = numeric_order_preserved(raw, polished)
    if not numo["ok"]:
        problems.append(f"numeric order changed: raw={numo['raw_seq']} polished={numo['polished_seq']}")

    named = named_tokens_preserved(raw, polished)
    if not named["ok"]:
        problems.append(
            "named/unit changed: "
            f"italic_dropped={named['italic_dropped']} italic_added={named['italic_added']} "
            f"unit_dropped={named['unit_dropped']} unit_added={named['unit_added']}"
        )

    cert = detect_certainty_upgrade(raw, polished)
    if not cert["ok"]:
        problems.append(f"certainty upgraded: {cert['introduced_strong_verbs']}")

    raw_cites, pol_cites = citation_set(raw), citation_set(polished)
    if raw_cites != pol_cites:
        problems.append(f"citations changed: lost={sorted(raw_cites - pol_cites)} added={sorted(pol_cites - raw_cites)}")

    raw_cite_seq, pol_cite_seq = citation_order(raw), citation_order(polished)
    if raw_cite_seq != pol_cite_seq:
        problems.append(f"citation order changed: raw={raw_cite_seq} polished={pol_cite_seq}")

    # 非散文(参考文献/作者名单/图注等)保留原文不润色,去AI检测不适用;红线(数值/引用/语气/meaning)仍查
    is_nonprose = unit.get("prose") is False or unit.get("polished_by") == "unchanged-nonprose"
    markers = [] if is_nonprose else find_ai_style_markers(polished)
    # 句长是软目标(科学方法学段落含数据列表的长句合法),记为警告不阻断交付;
    # 其余去AI标志(破折号/scare quotes/解释性冒号/套话/from-A-to-B 等)仍硬拦。
    blocking = [m for m in markers if not str(m).startswith("sentence >")]
    if blocking:
        problems.append(f"ai markers: {blocking}")

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
    nonprose: list[dict] = []
    for entry in entries:
        idx = entry["idx"]
        unit = read_json(polished_dir / f"{idx}.json", None)
        if unit is None:
            failures.append({"idx": idx, "problems": ["polished unit missing"]})
            continue
        if unit.get("prose") is False or unit.get("polished_by") == "unchanged-nonprose":
            raw_preview = normalize_ws(unit.get("raw_text", ""))[:120]
            nonprose.append({"idx": idx, "heading": unit.get("heading", ""), "raw_preview": raw_preview})
        ok, problems = check_unit(unit)
        if not ok:
            failures.append({"idx": idx, "problems": problems})

    summary = {"checked": len(entries), "failed": len(failures),
               "nonprose_unpolished": nonprose, "failures": failures}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # 被判为"非散文"而整段原样保留的段落:逐条点名给作者复核判定是否误判(拿不准应润色)。
    if nonprose:
        sys.stderr.write(f"[strict_gate] {len(nonprose)} 段判为非散文未润色,请逐段复核判定是否误判:\n")
        for item in nonprose:
            sys.stderr.write(f"  · unit {item['idx']} [{item['heading']}] {item['raw_preview']}\n")
    if failures:
        print("STRICT_GATE: FAIL")
        sys.stderr.write("[strict_gate] fail-closed:不得向用户声明润色完成。\n")
        return 1
    print("STRICT_GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

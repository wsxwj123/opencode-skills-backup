#!/usr/bin/env python3
"""prewrite_gate.py — nsfc-proposal 统一「开写前置闸门」。

在各 Phase 的 write-cycle 处、撰写某个 section 之前运行，把机械合规自检
升级为脚本级硬拦截（exit≠0 阻断）。只做机械可判定检查，不替代委托盲检。

CLI：python3 prewrite_gate.py --section <section_id> --root <project_root>

section_id ∈ {P1, P2, P3_1, P3_2, P3_3, P3_4}（固定写作顺序）。

硬检查（FAIL → exit 1）：
1. 上一节完成：固定顺序里本节的上一节，其 sections/<file>.md 存在且非空
2. 大纲/故事线就位：data/consistency_map.json 存在且非空（H/O/RC/KSQ 链路已登记）
3. 素材就位（适配）：
   - P2/P3_1：必须有 data/experimental_design.json（entries 非空）
   - P2 起：consistency_map 须含 M（methodologies）条目
4. 占位符清零：上一节 sections 文件无 CITE_PENDING/DATA_PENDING/【待 残留

降级 warning（不阻断）：
- 上一节盲检：.review_return_<gate>.json 未落盘 → 提示人工确认
- 缩略词一致：nsfc 无独立 abbreviation 脚本 → skip 并注明

输出：stdout 一行 JSON {"ok":bool,"section":...,"checks":[...],"warnings":[...]}
任一硬检查失败额外打印 PREWRITE_GATE: FAIL + 原因 并 exit 1。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

PLACEHOLDER_TOKENS = ("CITE_PENDING", "DATA_PENDING", "【待")

# 固定写作顺序
SECTION_ORDER = ["P1", "P2", "P3_1", "P3_2", "P3_3", "P3_4"]

# section_id -> sections/ 文件名前缀（用 glob 匹配真实文件名后缀）
SECTION_FILE_PREFIX = {
    "P1": "P1_",
    "P2": "P2_",
    "P3_1": "P3_1_",
    "P3_2": "P3_2_",
    "P3_3": "P3_3_",
    "P3_4": "P3_4_",
}

# section_id -> 盲检 gate 名（P3_* 共用 p3-dod）
SECTION_GATE = {
    "P1": "p1-dod",
    "P2": "p2-dod",
    "P3_1": "p3-dod",
    "P3_2": "p3-dod",
    "P3_3": "p3-dod",
    "P3_4": "p3-dod",
}


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def section_file(root, section_id):
    """返回 sections/<prefix>*.md 第一个匹配文件路径，无则 None。"""
    prefix = SECTION_FILE_PREFIX.get(section_id)
    if not prefix:
        return None
    matches = sorted(glob.glob(os.path.join(root, "sections", f"{prefix}*.md")))
    return matches[0] if matches else None


def file_nonempty(path):
    if not path:
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return bool(f.read().strip())
    except OSError:
        return False


def consistency_map_nonempty(root):
    cm = _load_json(os.path.join(root, "data/consistency_map.json"))
    if not isinstance(cm, dict):
        return False, False
    # 非空：任一实体列表非空
    nonempty = any(isinstance(v, list) and v for v in cm.values())
    # 含 M（methodologies）
    has_m = isinstance(cm.get("M"), list) and bool(cm.get("M"))
    if not has_m and isinstance(cm.get("methodologies"), list):
        has_m = bool(cm.get("methodologies"))
    return nonempty, has_m


def experimental_design_nonempty(root):
    ed = _load_json(os.path.join(root, "data/experimental_design.json"))
    if not isinstance(ed, dict):
        # 也容忍直接是 list
        if isinstance(ed, list):
            return bool(ed)
        return False
    entries = ed.get("entries")
    return isinstance(entries, list) and bool(entries)


def scan_placeholders(files):
    hits = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        for token in PLACEHOLDER_TOKENS:
            if token in content:
                hits.append((os.path.basename(fp), token))
    return hits


def main():
    parser = argparse.ArgumentParser(
        description="nsfc-proposal 开写前置闸门：上一节完成/consistency_map/素材就位/占位符硬检查。"
    )
    parser.add_argument("--section", required=True, help="section id ∈ {P1,P2,P3_1,P3_2,P3_3,P3_4}")
    parser.add_argument("--root", required=True, help="project root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    section = str(args.section).strip()
    checks = []
    warnings = []
    failures = []

    if not os.path.isdir(root):
        print(f"PREWRITE_GATE: FAIL root not a directory: {root}")
        print(json.dumps({"ok": False, "section": section, "checks": [],
                          "warnings": []}, ensure_ascii=False))
        return 1

    known_section = section in SECTION_ORDER
    if not known_section:
        warnings.append(f"section {section!r} not in fixed order {SECTION_ORDER}; prev/gate checks degraded")

    # ---- check 1: 上一节完成 ----
    if known_section:
        idx = SECTION_ORDER.index(section)
        if idx == 0:
            checks.append({"name": "prev_section_done", "ok": True, "note": "first section, skip"})
        else:
            prev = SECTION_ORDER[idx - 1]
            prev_fp = section_file(root, prev)
            if file_nonempty(prev_fp):
                checks.append({"name": "prev_section_done", "ok": True, "prev": prev})
            else:
                failures.append(f"previous section {prev} file missing or empty under sections/")
                checks.append({"name": "prev_section_done", "ok": False, "prev": prev})
    else:
        checks.append({"name": "prev_section_done", "ok": None, "note": "unknown section, skip"})

    # ---- check 2: consistency_map 就位（链路已登记） ----
    cm_nonempty, has_m = consistency_map_nonempty(root)
    if cm_nonempty:
        checks.append({"name": "consistency_map", "ok": True})
    else:
        failures.append("data/consistency_map.json missing or empty (H/O/RC/KSQ not registered)")
        checks.append({"name": "consistency_map", "ok": False})

    # ---- check 3: 素材就位（适配 section） ----
    # P2 / P3_1 需要 experimental_design.json
    if section in ("P2", "P3_1"):
        if experimental_design_nonempty(root):
            checks.append({"name": "experimental_design", "ok": True})
        else:
            failures.append("data/experimental_design.json missing or has no entries (required for M / feasibility)")
            checks.append({"name": "experimental_design", "ok": False})
    # P2 起 consistency_map 须含 M
    if section in ("P2", "P3_1", "P3_2", "P3_3", "P3_4"):
        if has_m:
            checks.append({"name": "methodologies_M", "ok": True})
        elif section == "P2":
            # P2 正是产出 M 的阶段，开写前 M 可能尚空 → 降级 warning
            warnings.append("consistency_map has no M entries yet; P2 is where M is authored, ensure M is registered before locking section")
            checks.append({"name": "methodologies_M", "ok": None, "note": "P2 authors M; warning only"})
        else:
            failures.append("consistency_map has no M (methodologies) entries; P3 must build on P2's M")
            checks.append({"name": "methodologies_M", "ok": False})

    # ---- warning: 上一节盲检落盘 ----
    if known_section:
        idx = SECTION_ORDER.index(section)
        if idx > 0:
            prev = SECTION_ORDER[idx - 1]
            prev_gate = SECTION_GATE.get(prev)
            blind_path = os.path.join(root, f".review_return_{prev_gate}.json")
            if os.path.exists(blind_path):
                checks.append({"name": "blind_review", "ok": True, "note": f"{prev_gate} return found"})
            else:
                warnings.append(f"no .review_return_{prev_gate}.json on disk; previous-section blind review must be confirmed manually")

    # ---- check 4: 占位符清零（上一节文件；P1 无上一节则扫已写的 sections/*.md） ----
    files_to_scan = []
    if known_section:
        idx = SECTION_ORDER.index(section)
        if idx > 0:
            prev_fp = section_file(root, SECTION_ORDER[idx - 1])
            if prev_fp:
                files_to_scan = [prev_fp]
    if not files_to_scan:
        files_to_scan = sorted(glob.glob(os.path.join(root, "sections", "P*.md")))
    placeholder_hits = scan_placeholders(files_to_scan)
    if placeholder_hits:
        detail = ", ".join(f"{fn}:{tok}" for fn, tok in placeholder_hits)
        failures.append(f"unresolved placeholders: {detail}")
        checks.append({"name": "placeholders", "ok": False, "detail": detail})
    else:
        checks.append({"name": "placeholders", "ok": True})

    # ---- 缩略词：nsfc 无独立 abbreviation 脚本 → skip ----
    checks.append({"name": "abbreviation", "ok": None, "note": "no standalone abbreviation script in nsfc-proposal; skip"})

    ok = not failures
    print(json.dumps({"ok": ok, "section": section, "checks": checks,
                      "warnings": warnings}, ensure_ascii=False))
    if not ok:
        for reason in failures:
            print(f"PREWRITE_GATE: FAIL {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

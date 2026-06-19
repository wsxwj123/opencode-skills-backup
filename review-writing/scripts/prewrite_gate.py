#!/usr/bin/env python3
"""prewrite_gate.py — review-writing 统一「开写前置闸门」。

在 Phase 3 撰写某个 section 之前运行（Per-Section Cycle 最前），把机械合规
自检升级为脚本级硬拦截（exit≠0 阻断）。只做机械可判定检查，不替代委托盲检。

CLI：python3 prewrite_gate.py --section <section_id> --root <project_root>

硬检查（FAIL → exit 1）：
1. 上一节完成：outline.md 顺序里本节的上一节 ∈ state.json.completed_sections
2. 大纲就位：outline.md 存在且本 section 有对应标题条目
3. 素材就位：synthesis_matrix.json（本 section 文献矩阵非空）
4. 占位符清零：上一节 drafts 文件无 CITE_PENDING/DATA_PENDING/【待 残留
5. 上一节盲检通过：<root>/.review_pass/<上一节>.json 存在且 passed:true
   （由 delegate_review.py verify --section <上一节> 落盘）；缺失 → 硬拦

降级 warning（不阻断）：
- 缩略词一致：review 无独立 abbreviation 脚本 → skip 并注明

输出：stdout 一行 JSON {"ok":bool,"section":...,"checks":[...],"warnings":[...]}
任一硬检查失败额外打印 PREWRITE_GATE: FAIL + 原因 并 exit 1。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

PLACEHOLDER_TOKENS = ("CITE_PENDING", "DATA_PENDING", "【待")


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_outline_order(root):
    """从 outline.md 解析「可写小节」id 顺序。

    只纳入真正可写的小节（带子编号，如 1.1 / 2.3）。其余标题一律不计入顺序链：
    - 章级标题（纯 `1`/`2`，来自 `### 1. Introduction`）——否则第一个小节 1.1
      的「上一节」会被误判成章标题 `1`，而 `1` 永不进 completed_sections → 1.1 卡死；
    - 配置段标题（`## Parameters`/`## Outline (...)` 等模板里的非小节标题）——
      否则它们会混进顺序链，同样污染第一个可写小节的「上一节」判定。
    这样 outline 模板下 order = ['1.1','1.2','2.1',...]，1.1 即第一个、idx==0 放行。
    """
    path = os.path.join(root, "outline.md")
    if not os.path.exists(path):
        return []
    subsection_pattern = re.compile(r"^(\d+\.\d+)\b")
    order = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    for line in lines:
        m = re.match(r"^(##+)\s+(.*)$", line)
        if not m:
            continue
        title = m.group(2).strip()
        if not title:
            continue
        sub_match = subsection_pattern.match(title)
        if sub_match:
            order.append(sub_match.group(1))
    return order


def completed_sections(root):
    payload = _load_json(os.path.join(root, "state.json"))
    if isinstance(payload, dict):
        done = payload.get("completed_sections")
        if isinstance(done, list):
            return [str(s) for s in done]
    return []


def _section_matches(section, section_list):
    if not isinstance(section_list, list):
        return False
    target = str(section).strip()
    for s in section_list:
        if str(s).strip() == target:
            return True
    return False


def matrix_rows_for_section(root, section):
    """统计 synthesis_matrix.json 中归属本 section 的条目数。"""
    for rel in ("data/synthesis_matrix.json", "data/literature_matrix.json"):
        payload = _load_json(os.path.join(root, rel))
        rows = payload if isinstance(payload, list) else None
        if rows is None and isinstance(payload, dict):
            for key in ("synthesis_matrix", "literature_matrix", "matrix", "rows"):
                if isinstance(payload.get(key), list):
                    rows = payload[key]
                    break
        if not rows:
            continue
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if (_section_matches(section, row.get("related_sections"))
                    or _section_matches(section, row.get("sections"))
                    or str(row.get("section_id", "")).strip() == str(section).strip()
                    or str(row.get("section", "")).strip() == str(section).strip()):
                count += 1
        if count > 0:
            return count
    return 0


def draft_files(root):
    d = os.path.join(root, "drafts")
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".md"))


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
        description="review-writing 开写前置闸门：上一节完成/大纲/文献矩阵/占位符硬检查。"
    )
    parser.add_argument("--section", required=True, help="section id，例如 2.1")
    parser.add_argument("--root", required=True, help="project root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    section = str(args.section)
    checks = []
    warnings = []
    failures = []

    if not os.path.isdir(root):
        print(f"PREWRITE_GATE: FAIL root not a directory: {root}")
        print(json.dumps({"ok": False, "section": section, "checks": [],
                          "warnings": []}, ensure_ascii=False))
        return 1

    # ---- check 2: 大纲就位 ----
    order = load_outline_order(root)
    if not order:
        failures.append("outline.md missing or has no section headings")
        checks.append({"name": "outline", "ok": False})
    elif section not in order:
        failures.append(f"section {section!r} not found in outline.md")
        checks.append({"name": "outline", "ok": False})
    else:
        checks.append({"name": "outline", "ok": True})

    # ---- check 1: 上一节完成 ----
    if order and section in order:
        idx = order.index(section)
        if idx == 0:
            checks.append({"name": "prev_section_done", "ok": True, "note": "first section, skip"})
        else:
            prev = order[idx - 1]
            done = prev in completed_sections(root)
            if done:
                checks.append({"name": "prev_section_done", "ok": True, "prev": prev})
            else:
                failures.append(f"previous section {prev!r} not in completed_sections")
                checks.append({"name": "prev_section_done", "ok": False, "prev": prev})
    else:
        checks.append({"name": "prev_section_done", "ok": False, "note": "no outline order"})

    # ---- check: 上一节盲检通过并落盘（硬） ----
    if order and section in order and order.index(section) > 0:
        prev = order[order.index(section) - 1]
        pass_path = os.path.join(root, ".review_pass", f"{prev}.json")
        marker = _load_json(pass_path)
        if isinstance(marker, dict) and marker.get("passed") is True:
            checks.append({"name": "blind_review", "ok": True, "prev": prev})
        else:
            failures.append(
                f"previous section {prev!r} blind review not passed or marker missing; "
                f"run: delegate_review.py verify --section {prev}")
            checks.append({"name": "blind_review", "ok": False, "prev": prev})
    else:
        checks.append({"name": "blind_review", "ok": True, "note": "first section, N/A"})

    # ---- check 3: 素材就位（本 section 文献矩阵非空） ----
    n_rows = matrix_rows_for_section(root, section)
    if n_rows > 0:
        checks.append({"name": "literature_matrix", "ok": True, "rows": n_rows})
    else:
        failures.append(f"synthesis_matrix has no rows for section {section!r}")
        checks.append({"name": "literature_matrix", "ok": False})

    # ---- check 4: 占位符清零（drafts） ----
    placeholder_hits = scan_placeholders(draft_files(root))
    if placeholder_hits:
        detail = ", ".join(f"{fn}:{tok}" for fn, tok in placeholder_hits)
        failures.append(f"unresolved placeholders: {detail}")
        checks.append({"name": "placeholders", "ok": False, "detail": detail})
    else:
        checks.append({"name": "placeholders", "ok": True})

    # ---- 缩略词：review 无独立脚本 → skip ----
    checks.append({"name": "abbreviation", "ok": None, "note": "no standalone abbreviation script in review-writing; skip"})

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

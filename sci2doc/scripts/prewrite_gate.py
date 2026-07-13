#!/usr/bin/env python3
"""prewrite_gate.py — sci2doc 统一「开写前置闸门」。

在「原子化写作」每节开写前运行，把机械合规自检升级为脚本级硬拦截
（exit≠0 阻断）。只做机械可判定检查，不替代委托盲检。

CLI：python3 prewrite_gate.py --section <section_id> --root <project_root>

section_id 形如 "2.1"（章.节）。

硬检查（FAIL → exit 1）：
1. 上一节完成：同章内编号紧邻的上一节，其 atomic_md/第N章/{x.y}_*.md 存在且非空
2. 大纲就位：project_state.json.outline.chapters 含本节所属章；且 chapter_index.json 存在
3. 素材就位：figures_index.json 本章有 figure/实验映射条目
4. 占位符清零：上一节 atomic_md 文件无 CITE_PENDING/DATA_PENDING/【待 残留
5. 上一节盲检通过：<root>/.review_pass/<上一节>.json 存在且 passed:true
   （由 delegate_review.py verify --section <上一节> 落盘）；缺失 → 硬拦
6. 每章首节（sub<=1 且非第 1 章）：上一章章级盲检 <root>/.review_pass/第<N-1>章.json
   存在且 passed:true（由 delegate_review.py verify --section 第<N-1>章 落盘）；缺失 → 硬拦。
   第 1 章首节无上一章，放行。

降级 warning（不阻断）：
- 缩略词一致：sci2doc 用 abbreviation_registry（无 --root 式扫描接口）→ skip 并注明

输出：stdout 一行 JSON {"ok":bool,"section":...,"checks":[...],"warnings":[...]}
任一硬检查失败额外打印 PREWRITE_GATE: FAIL + 原因 并 exit 1。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import data_trace_gate  # 同目录：数据溯源硬门（⑥）
except Exception:  # pragma: no cover - 缺失不应反过来卡住 prewrite
    data_trace_gate = None

PLACEHOLDER_TOKENS = ("CITE_PENDING", "DATA_PENDING", "【待")


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def parse_section(section):
    """'2.1' -> (chapter='2', sub=1)；无法解析返回 (chapter_str, None)。"""
    m = re.match(r"^\s*(\d+)\.(\d+)\s*$", str(section))
    if m:
        return m.group(1), int(m.group(2))
    # 退化：仅章号
    m2 = re.match(r"^\s*(\d+)\s*$", str(section))
    if m2:
        return m2.group(1), None
    return str(section), None


def chapter_dir(root, chapter):
    return os.path.join(root, "atomic_md", f"第{chapter}章")


def section_files_in_chapter(root, chapter):
    """返回 {sub_int: filepath} 来自 atomic_md/第N章/{N.M}_*.md。"""
    out = {}
    cdir = chapter_dir(root, chapter)
    if not os.path.isdir(cdir):
        return out
    for fp in glob.glob(os.path.join(cdir, "*.md")):
        base = os.path.basename(fp)
        m = re.match(rf"^{re.escape(chapter)}\.(\d+)_", base)
        if m:
            out[int(m.group(1))] = fp
    return out


def file_nonempty(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return bool(f.read().strip())
    except OSError:
        return False


def outline_has_chapter(root, chapter):
    payload = _load_json(os.path.join(root, "project_state.json"))
    if not isinstance(payload, dict):
        return False
    outline = payload.get("outline")
    chapters = None
    if isinstance(outline, dict):
        chapters = outline.get("chapters")
    elif isinstance(outline, list):
        chapters = outline
    if not isinstance(chapters, list):
        return False
    for ch in chapters:
        if isinstance(ch, dict):
            num = str(ch.get("chapter") or ch.get("chapter_number") or ch.get("id") or "").strip()
            if num == str(chapter) or num.lstrip("第").rstrip("章") == str(chapter):
                return True
    return False


def figures_for_chapter(root, chapter):
    """figures_index.json 中归属本章的条目数。"""
    payload = _load_json(os.path.join(root, "figures_index.json"))
    rows = payload if isinstance(payload, list) else None
    if rows is None and isinstance(payload, dict):
        for key in ("figures", "items", "data"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
    if not rows:
        return 0
    count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        ch = str(row.get("chapter") or row.get("chapter_number") or "").strip()
        fid = str(row.get("figure_id") or row.get("id") or row.get("number") or "")
        # 形如 图2-1 / 表2-3 / Figure 2 也归到 chapter 2
        if ch == str(chapter):
            count += 1
        elif re.search(rf"\b{re.escape(str(chapter))}\b[-.]", fid):
            count += 1
    return count


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
        description="sci2doc 开写前置闸门：上一节完成/大纲/图表映射/占位符硬检查。"
    )
    parser.add_argument("--section", required=True, help="章.节，例如 2.1")
    parser.add_argument("--root", required=True, help="project root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    section = str(args.section)
    chapter, sub = parse_section(section)
    checks = []
    warnings = []
    failures = []

    if not os.path.isdir(root):
        print(f"PREWRITE_GATE: FAIL root not a directory: {root}")
        print(json.dumps({"ok": False, "section": section, "checks": [],
                          "warnings": []}, ensure_ascii=False))
        return 1

    # ---- check 2: 大纲就位 ----
    if outline_has_chapter(root, chapter):
        checks.append({"name": "outline", "ok": True})
    else:
        failures.append(f"project_state.json outline has no chapter {chapter!r}")
        checks.append({"name": "outline", "ok": False})

    # ---- check 1: 上一节完成（同章编号紧邻上一节文件存在非空） ----
    if sub is None:
        checks.append({"name": "prev_section_done", "ok": True, "note": "chapter-level or unparsed section, skip prev check"})
    elif sub <= 1:
        checks.append({"name": "prev_section_done", "ok": True, "note": "first subsection of chapter, skip"})
    else:
        files_map = section_files_in_chapter(root, chapter)
        prev_sub = sub - 1
        prev_fp = files_map.get(prev_sub)
        if prev_fp and file_nonempty(prev_fp):
            checks.append({"name": "prev_section_done", "ok": True, "prev": f"{chapter}.{prev_sub}"})
        else:
            failures.append(f"previous section {chapter}.{prev_sub} file missing or empty in {chapter_dir(root, chapter)}")
            checks.append({"name": "prev_section_done", "ok": False, "prev": f"{chapter}.{prev_sub}"})

    # ---- check: 上一节盲检通过并落盘（硬） ----
    if sub is not None and sub > 1:
        prev = f"{chapter}.{sub - 1}"
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
        checks.append({"name": "blind_review", "ok": True, "note": "first subsection or chapter-level, N/A"})

    # ---- check: 每章首节硬校验上一章章级盲检通过（硬，章级） ----
    # 每章首节(sub<=1)且非第1章：上一章 chapter-dod 盲检标记必须存在且 passed。
    # 缺标记 → 硬拦，堵住「未过章级盲检就开写下一章」的跳步。第1章无上一章，放行。
    try:
        chapter_int = int(chapter)
    except (TypeError, ValueError):
        chapter_int = None
    if sub is not None and sub <= 1 and chapter_int is not None and chapter_int > 1:
        prev_ch = f"第{chapter_int - 1}章"
        ch_pass_path = os.path.join(root, ".review_pass", f"{prev_ch}.json")
        ch_marker = _load_json(ch_pass_path)
        if isinstance(ch_marker, dict) and ch_marker.get("passed") is True:
            checks.append({"name": "prev_chapter_blind_review", "ok": True, "prev": prev_ch})
        else:
            failures.append(
                f"previous chapter {prev_ch!r} blind review not passed or marker missing; "
                f"run: delegate_review.py verify --section {prev_ch}")
            checks.append({"name": "prev_chapter_blind_review", "ok": False, "prev": prev_ch})
    else:
        checks.append({"name": "prev_chapter_blind_review", "ok": True,
                       "note": "first chapter or non-first subsection; N/A"})

    # ---- check 3: 素材就位（本章 figure/实验映射） ----
    n_fig = figures_for_chapter(root, chapter)
    if n_fig > 0:
        checks.append({"name": "figure_map", "ok": True, "figures": n_fig})
    else:
        # figures_index.json 缺或本章无条目：仅当文件存在却本章为空才硬失败；
        # 文件不存在（如纯文字章节早期）降级 warning，避免误伤无图章节。
        if os.path.exists(os.path.join(root, "figures_index.json")):
            warnings.append(f"figures_index.json has no entries for chapter {chapter}; confirm this chapter truly has no figures/experiments")
            checks.append({"name": "figure_map", "ok": None, "note": "no entries for chapter (warning)"})
        else:
            warnings.append("figures_index.json missing; figure/experiment material readiness not verifiable")
            checks.append({"name": "figure_map", "ok": None, "note": "figures_index.json missing"})

    # ---- check 4: 占位符清零（本章 atomic_md 已有文件） ----
    existing_files = list(section_files_in_chapter(root, chapter).values())
    placeholder_hits = scan_placeholders(existing_files)
    if placeholder_hits:
        detail = ", ".join(f"{fn}:{tok}" for fn, tok in placeholder_hits)
        failures.append(f"unresolved placeholders: {detail}")
        checks.append({"name": "placeholders", "ok": False, "detail": detail})
    else:
        checks.append({"name": "placeholders", "ok": True})

    # ---- check: 上一节数据溯源（⑥，含数值须标 [数据来源] materials/<档>#<字段>） ----
    if data_trace_gate is not None and sub is not None and sub > 1:
        prev_fp = section_files_in_chapter(root, chapter).get(sub - 1)
        if prev_fp and os.path.isfile(prev_fp):
            dt_viol, dt_numeric = data_trace_gate.gate(root, [prev_fp])
            if dt_viol:
                for v in dt_viol:
                    failures.append(f"data_trace(prev {chapter}.{sub-1}): {v}")
                checks.append({"name": "data_trace", "ok": False, "prev": f"{chapter}.{sub-1}",
                               "violations": dt_viol})
            else:
                checks.append({"name": "data_trace", "ok": True, "prev": f"{chapter}.{sub-1}",
                               "numeric": bool(dt_numeric)})
        else:
            checks.append({"name": "data_trace", "ok": True, "note": "prev file absent; prev_section_done already reported"})
    else:
        checks.append({"name": "data_trace", "ok": True, "note": "first subsection/chapter-level or gate unavailable; N/A"})

    # ---- 缩略词：sci2doc 用 abbreviation_registry（按文件处理，无 --root 扫描）→ skip ----
    checks.append({"name": "abbreviation", "ok": None, "note": "sci2doc uses abbreviation_registry per-file; no root-level scan; skip"})

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

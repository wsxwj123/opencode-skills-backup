#!/usr/bin/env python3
"""prewrite_gate.py — general-sci-writing 统一「开写前置闸门」。

在 Phase 8 撰写某个 section 之前运行，把原本散落在提示词里的机械合规自检
升级为脚本级硬拦截（exit≠0 阻断开写）。本脚本只做"机械可判定"的检查，
不替代委托盲检（语义判断仍由 academic-blind-reviewer 负责）。

CLI：python3 prewrite_gate.py --section <section_id> --root <project_root>

硬检查（FAIL → exit 1）：
1. 上一节完成：storyline 顺序里本节的上一节，其 writing_progress 最新状态为 done/completed
2. 故事线就位：storyline.json 存在且本 section 有对应条目
3. 素材就位：subprocess 调 figure_analysis_gate.py（复用，不重写）
4. 占位符清零：上一节 manuscript 文件无 CITE_PENDING/DATA_PENDING/【待 残留
5. 缩略词一致：subprocess 调 abbreviation_consistency.py（复用，不重写）
6. 上一节盲检通过：<root>/.review_pass/<上一节>.json 存在且 passed:true
   （由 delegate_review.py verify --section <上一节> 落盘）；缺失 → 硬拦

输出：stdout 一行 JSON {"ok":bool,"section":...,"checks":[...],"warnings":[...]}
任一硬检查失败额外打印 PREWRITE_GATE: FAIL + 原因 并 exit 1。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

PLACEHOLDER_TOKENS = ("CITE_PENDING", "DATA_PENDING", "【待")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_storyline_order(root):
    """返回 storyline.json 的 section id 顺序列表，无则 []。"""
    payload = _load_json(os.path.join(root, "storyline.json"))
    if not isinstance(payload, dict):
        return []
    sections = payload.get("sections")
    order = []
    if isinstance(sections, list):
        for item in sections:
            if isinstance(item, dict):
                sid = item.get("id") or item.get("section_id")
                if sid:
                    order.append(str(sid))
    return order


def section_status_from_progress(root, section):
    """从 writing_progress.json 的 update_history 取该 section 最新 status。"""
    payload = _load_json(os.path.join(root, "writing_progress.json"))
    if not isinstance(payload, dict):
        return None
    history = payload.get("update_history")
    last = None
    if isinstance(history, list):
        for entry in history:
            if isinstance(entry, dict) and str(entry.get("section")) == str(section):
                last = entry.get("status")
    # 兜底：last_section 直读
    if last is None and str(payload.get("last_section")) == str(section):
        last = payload.get("status")
    return last


def manuscript_files_for_section(root, section):
    """猜测本 section 对应的 manuscript 文件（用于占位符扫描）。

    gsw manuscript 文件名不强绑 section_id，故扫所有 manuscripts/*.md 中
    内容含该 section_id 的文件；找不到则返回全部（保守扫描）。
    """
    md_dir = os.path.join(root, "manuscripts")
    if not os.path.isdir(md_dir):
        return []
    files = [os.path.join(md_dir, f) for f in os.listdir(md_dir)
             if f.endswith(".md") and f != "Full_Manuscript.md"
             and not f.startswith("Draft_Round")]
    return sorted(files)


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


def run_subprocess_gate(script_name, extra_args, root):
    """复用既有 gate 脚本（subprocess），返回 (ok, output)。"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        return None, f"{script_name} not found (skip)"
    cmd = [sys.executable, script_path] + extra_args + ["--root", root]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"{script_name} run error: {exc}"
    out = (proc.stdout or "").strip() + (("\n" + proc.stderr.strip()) if proc.stderr.strip() else "")
    return proc.returncode == 0, out


def main():
    parser = argparse.ArgumentParser(
        description="general-sci-writing 开写前置闸门：上一节完成/故事线/素材/占位符/缩略词硬检查。"
    )
    parser.add_argument("--section", required=True, help="storyline section_id，例如 results_3.2")
    parser.add_argument("--root", required=True, help="project root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    section = args.section
    checks = []
    warnings = []
    failures = []

    if not os.path.isdir(root):
        print(f"PREWRITE_GATE: FAIL root not a directory: {root}")
        print(json.dumps({"ok": False, "section": section, "checks": [],
                          "warnings": []}, ensure_ascii=False))
        return 1

    # ---- check 2 (先判故事线，因 check1 依赖其顺序) ----
    order = load_storyline_order(root)
    if not order:
        failures.append("storyline.json missing or has no sections")
        checks.append({"name": "storyline", "ok": False})
    elif section not in order:
        failures.append(f"section {section!r} not found in storyline.json")
        checks.append({"name": "storyline", "ok": False})
    else:
        checks.append({"name": "storyline", "ok": True})

    # ---- check 1: 上一节完成 ----
    if order and section in order:
        idx = order.index(section)
        if idx == 0:
            checks.append({"name": "prev_section_done", "ok": True, "note": "first section, skip"})
        else:
            prev = order[idx - 1]
            status = section_status_from_progress(root, prev)
            done = str(status).lower() in ("done", "completed", "finalized")
            if done:
                checks.append({"name": "prev_section_done", "ok": True, "prev": prev})
            else:
                failures.append(f"previous section {prev!r} status={status!r} (need done/completed)")
                checks.append({"name": "prev_section_done", "ok": False, "prev": prev})
    else:
        checks.append({"name": "prev_section_done", "ok": False, "note": "no storyline order"})

    # ---- check (硬): 上一节盲检通过并落盘 ----
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

    # ---- check 3: 素材就位（subprocess figure_analysis_gate.py，复用） ----
    fig_ok, fig_out = run_subprocess_gate("figure_analysis_gate.py", ["--section", section], root)
    if fig_ok is None:
        warnings.append(f"figure_analysis_gate.py unavailable: {fig_out}")
        checks.append({"name": "figure_analysis", "ok": None, "note": fig_out})
    elif fig_ok:
        checks.append({"name": "figure_analysis", "ok": True})
    else:
        failures.append(f"figure_analysis_gate failed: {fig_out}")
        checks.append({"name": "figure_analysis", "ok": False, "detail": fig_out})

    # ---- check 4: 占位符清零（上一节文件） ----
    placeholder_hits = scan_placeholders(manuscript_files_for_section(root, section))
    if placeholder_hits:
        detail = ", ".join(f"{fn}:{tok}" for fn, tok in placeholder_hits)
        failures.append(f"unresolved placeholders: {detail}")
        checks.append({"name": "placeholders", "ok": False, "detail": detail})
    else:
        checks.append({"name": "placeholders", "ok": True})

    # ---- check 5: 缩略词一致（subprocess abbreviation_consistency.py，复用） ----
    abbr_ok, abbr_out = run_subprocess_gate("abbreviation_consistency.py", [], root)
    if abbr_ok is None:
        warnings.append(f"abbreviation_consistency.py unavailable: {abbr_out}")
        checks.append({"name": "abbreviation", "ok": None, "note": abbr_out})
    elif abbr_ok:
        checks.append({"name": "abbreviation", "ok": True})
    else:
        failures.append(f"abbreviation_consistency failed: {abbr_out}")
        checks.append({"name": "abbreviation", "ok": False, "detail": abbr_out})

    ok = not failures
    print(json.dumps({"ok": ok, "section": section, "checks": checks,
                      "warnings": warnings}, ensure_ascii=False))
    if not ok:
        for reason in failures:
            print(f"PREWRITE_GATE: FAIL {reason}")
        return 1
    print("PREWRITE_GATE: PASS 仅覆盖流程前置(上一节完成/盲检标记/故事线/素材就位/"
          "占位清零/缩略词一致)，不代表本节内容有科学价值或够顶刊——那靠盲检与作者判断。",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

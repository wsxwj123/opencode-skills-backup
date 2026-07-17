#!/usr/bin/env python3
"""split_audit.py —— 反向核验第一层 · 逐分区偏移定位比对（功能② · INTERFACE §5，跨家共享）.

以 heading_manifest 的 char_offset 定切点（跳过 is_caption 行），得区间序列
[o_0,o_1),[o_1,o_2),…，逐区把 slice_i = text[o_i:o_{i+1}] 与"文件序第 i 个 atom"比对。
一次覆盖 漏/造/串/边界漂移/乱序 全五类，不假绿（取代旧"并集多重集"，盲审致命 C1）。

归一化白名单（§206-211，写死）：
  允许归一：① 分区首尾空白/换行（seam）；② 连续空白折叠为单个；③ 全角空格→半角。
  绝不归一：任何实际字符（含全半角标点变化）、段落数（按空行计）、图注文字。
段落数单独校验 —— 防"合并段落"被空白折叠吞掉（空白折叠会把 \\n\\n 也并成单空格）。

图注 parity 降级为 advisory[]，不改退出码（盲审 S1）。

退出码（INTERFACE §5，三态，v3 作废 exit3）：
  0  逐区全匹配（进第二层 LLM 核验）
  1  有区间不匹配（漏/造/串/漂移/乱），fail-closed
  2  用法错 / text 缺失 / headings 或 manifest 畸形 / headings 空 / atoms-glob 命中 0
只读：任何路径不写 atom/源/manifest；只写 --report（可选）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

FULLWIDTH_SPACE = "　"
DEFAULT_CAPTION_RE = re.compile(r"(?:图|表|Fig(?:ure)?|Table)\s*\d+[-–—]\d+", re.IGNORECASE)


def _die2(msg):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(2)


def _norm_content(s):
    """白名单归一：全角空格→半角、首尾修剪、连续空白折叠为单空格。不动任何实际字符。"""
    s = s.replace(FULLWIDTH_SPACE, " ")
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _para_count(s):
    """按空行切段落计数（连续空白折叠会吞段落边界，故段落数必须独立校验）。"""
    parts = re.split(r"\n[ \t]*\n", s.strip())
    return len([p for p in parts if p.strip()])


def _load_json(path, what):
    if not os.path.isfile(path):
        _die2("%s not found: %s" % (what, path))
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        _die2("malformed %s json: %s" % (what, e))


def main(argv=None):
    ap = argparse.ArgumentParser(description="逐分区偏移定位反向核验（fail-closed，只读）")
    ap.add_argument("--text", required=True)
    ap.add_argument("--headings", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--atoms-glob", required=True)
    ap.add_argument("--root", required=False, default=".")
    ap.add_argument("--report", required=False)
    ap.add_argument("--caption-pattern", action="append", default=None)
    args = ap.parse_args(argv)

    # --- 载入（畸形/缺失 → exit 2）---
    if not os.path.isfile(args.text):
        _die2("text not found: %s" % args.text)
    with open(args.text, encoding="utf-8") as f:
        text = f.read()

    hd = _load_json(args.headings, "headings")
    headings = hd.get("headings") if isinstance(hd, dict) else None
    if not isinstance(headings, list) or len(headings) == 0:
        _die2("headings empty or missing (空 headings 应走无标题路，不该来审计)")

    mf = _load_json(args.manifest, "manifest")
    if not isinstance(mf, dict) or not isinstance(mf.get("atoms"), list):
        _die2("manifest missing 'atoms'")

    atom_files = sorted(glob.glob(args.atoms_glob))
    if not atom_files:
        _die2("atoms-glob matched 0 files: %s" % args.atoms_glob)

    # --- 区间序列（切点 = 非图注标题偏移，升序）---
    cuts = sorted(h["char_offset"] for h in headings
                  if not h.get("is_caption") and isinstance(h.get("char_offset"), int))
    bounds = cuts + [len(text)]
    slices = [text[bounds[i]:bounds[i + 1]] for i in range(len(cuts))]

    caption_res = ([re.compile(p) for p in args.caption_pattern]
                   if args.caption_pattern else [DEFAULT_CAPTION_RE])

    hard_fails = []
    advisory = []

    # --- atom 数 vs 区间数 ---
    if len(atom_files) != len(slices):
        hard_fails.append({
            "kind": "atom_count_mismatch",
            "detail": "atom 文件数 %d ≠ 区间数 %d" % (len(atom_files), len(slices))})

    # --- 逐区比对 ---
    manifest_atoms = mf.get("atoms", [])
    n = min(len(atom_files), len(slices))
    for i in range(n):
        try:
            with open(atom_files[i], encoding="utf-8") as f:
                atom = f.read()
        except OSError as e:
            hard_fails.append({"kind": "atom_unreadable", "region_index": i,
                               "detail": str(e)})
            continue
        sl = slices[i]
        ps, pa = _para_count(sl), _para_count(atom)
        if ps != pa:
            hard_fails.append({
                "kind": "region_mismatch", "region_index": i,
                "atom": os.path.basename(atom_files[i]),
                "char_range": [bounds[i], bounds[i + 1]],
                "detail": "段落数不符：slice %d 段, atom %d 段（疑合并/漂移/漏造）" % (ps, pa)})
            continue
        if _norm_content(sl) != _norm_content(atom):
            hard_fails.append({
                "kind": "region_mismatch", "region_index": i,
                "atom": os.path.basename(atom_files[i]),
                "char_range": [bounds[i], bounds[i + 1]],
                "detail": "atom 内容与 slice 不符（漏/造/串/漂移/字符或标点改动）"})

    # --- 图注 parity（advisory，不改退出码）---
    for i, a in enumerate(manifest_atoms):
        claimed = set(a.get("figure_ids") or [])
        actual = set()
        if i < len(atom_files):
            try:
                with open(atom_files[i], encoding="utf-8") as f:
                    ac = f.read()
                for rx in caption_res:
                    actual.update(rx.findall(ac))
            except OSError:
                pass
        if claimed != actual:
            advisory.append({
                "kind": "figure_parity", "atom_index": i,
                "detail": "图注 figure_ids 声称 %s 与 atom 实含 %s 不一致"
                          % (sorted(claimed), sorted(actual))})

    if hard_fails:
        report = {"ok": False, "exit": 1, "hard_fails": hard_fails, "advisory": advisory}
        if args.report:
            _write_report(args.report, report)
        sys.stdout.write(json.dumps(
            {"ok": False, "exit": 1, "atoms": len(atom_files), "advisory": advisory},
            ensure_ascii=False) + "\n")
        sys.exit(1)

    report = {"ok": True, "exit": 0, "hard_fails": [], "advisory": advisory}
    if args.report:
        _write_report(args.report, report)
    sys.stdout.write(json.dumps(
        {"ok": True, "exit": 0, "atoms": len(atom_files), "advisory": advisory},
        ensure_ascii=False) + "\n")
    sys.exit(0)


def _write_report(path, obj):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

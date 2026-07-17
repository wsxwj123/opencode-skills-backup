#!/usr/bin/env python3
# delegate_write.py —— sci2doc 撰写子代理任务包 + 返回校验（INTERFACE §1/§2/§6）
#
# 子命令（试点批只含这两个，pack-prep 属推广批不在此）：
#   pack-write   主会话生成撰写任务包 .write_task_<section>.json（本节原料嵌入 + 全局框架给路径）
#   verify-write 机械校验撰写子代理返回 .write_return_<section>.json（V1-V9，编号权焊死保险 V2/V3）
#
# 退出码：0=OK；1=verify 校验不过（fail-closed）；2=用法错/文件不存在/JSON 畸形。

import argparse
import json
import os
import re
import sys

SECTION_RE = re.compile(r"^\d+(\.\d+)*$")
KEY_RE = re.compile(r"\[@([A-Za-z0-9:_\-]+)\]")
# 裸数字引用：[5] / [5,6] / [5-7]（中文标记 [数据来源]/[图] 等不含数字，不命中）
BARE_NUM_RE = re.compile(r"\[\s*\d+(\s*[-,，]\s*\d+)*\s*\]")


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_outline(root):
    """从 project_state.json / storyline.json 读 sections 列表。"""
    for fn in ("project_state.json", "storyline.json"):
        p = os.path.join(root, fn)
        if os.path.isfile(p):
            try:
                data = load_json(p)
            except Exception:
                die("outline JSON 畸形: %s" % fn)
            secs = data.get("sections") if isinstance(data, dict) else data
            if isinstance(secs, list):
                return secs
    return []


# ---------------------------------------------------------------------------
# pack-write
# ---------------------------------------------------------------------------

STYLE_RULES = {
    "forbidden": ["破折号", "scare quotes", "解释性冒号", "AI 禁词"],
    "citation": "正文引用只写 [@key]（key=literature_index 的 id 或 new:<slug>），绝不写裸数字 [5]",
    "table": "三线表用管道语法",
}
ROLE = ("撰写工人：看不到别节写作过程，只按本任务包写本节；全局框架按需 Read refs 路径"
        "（只读，禁写任何账本文件）；承重句只准挂内嵌 certified_claims 里的 ref_key。")


def cmd_pack_write(args):
    section = args.section
    root = args.root
    if not SECTION_RE.match(section):
        die("section 格式非法: %s" % section)
    if not os.path.isdir(root):
        die("root not a directory: %s" % root)

    sections = load_outline(root)
    sec = next((s for s in sections if s.get("section_id") == section), None)
    if sec is None:
        die("outline has no section: %s" % section)

    # 账本读取（JSON 畸形 → exit2）
    try:
        lit = load_json(os.path.join(root, "literature_index.json"))
    except FileNotFoundError:
        lit = []
    except Exception:
        die("literature_index JSON 畸形")
    if not isinstance(lit, list):
        lit = []
    try:
        claim_rows = load_json(os.path.join(root, "claim_evidence.json"))
    except FileNotFoundError:
        claim_rows = []
    except Exception:
        die("claim_evidence JSON 畸形")
    if isinstance(claim_rows, dict):
        claim_rows = claim_rows.get("claims", claim_rows.get("rows", []))
    if not isinstance(claim_rows, list):
        claim_rows = []

    load_bearing_outline = sec.get("load_bearing_claims") or []
    sec_rows = [r for r in claim_rows if r.get("section") == section]
    sec_lb_rows = [r for r in sec_rows if r.get("is_load_bearing")]

    # 承重句核证机械拦（INTERFACE §1.3 后两条）
    if load_bearing_outline and not sec_rows:
        die("本节有承重论点但缺 claim_evidence，先建证据对")
    if any(not r.get("user_confirmed") for r in sec_lb_rows):
        die("certified_claims 未完成人工核证")

    # certified_claims：本节已核证承重对
    certified = [
        {"claim_id": r.get("claim_id", ""), "claim_sentence": r.get("claim_sentence", ""),
         "ref_key": r.get("ref_id", ""), "verdict": r.get("verdict", ""),
         "evidence_quote": r.get("evidence_quote", "")}
        for r in sec_lb_rows
        if r.get("user_confirmed") and r.get("verdict") in ("support", "weak")
    ]

    # lit_section：chapter_matrix 按 section_id==X.Y 切片，回填 literature_index 全条
    try:
        matrix = load_json(os.path.join(root, "chapter_matrix.json"))
    except Exception:
        matrix = []
    rows = matrix if isinstance(matrix, list) else matrix.get("rows", []) if isinstance(matrix, dict) else []
    lit_by_id = {e.get("id"): e for e in lit}
    lit_section = []
    for mr in rows:
        if mr.get("section_id") == section:
            e = lit_by_id.get(mr.get("id"), {})
            lit_section.append({
                "key": mr.get("id"),
                "title": e.get("title") or mr.get("title", ""),
                "authors": e.get("authors", []),
                "year": e.get("year"),
                "journal": e.get("journal", ""),
                "doi": e.get("doi"),
                "pmid": e.get("pmid"),
                "abstract": e.get("abstract") or mr.get("abstract", ""),
                "article_type": e.get("article_type", mr.get("article_type", "unknown")),
                "current_number": e.get("current_number"),
            })

    warning = "lit_section empty" if not lit_section else None

    embed = {
        "role": ROLE,
        "section_id": section,
        "section_target": {
            "title": sec.get("title", ""),
            "core_argument": sec.get("core_argument", ""),
            "scientific_question": sec.get("scientific_question", ""),
            "load_bearing_claims": load_bearing_outline,
            "target_words": sec.get("target_words"),
        },
        "certified_claims": certified,
        "lit_section": lit_section,
        "figures": [],
        "neighbor_digest": [],
        "abbrev_table": [],
        "data_sources": [],
        "style_rules": STYLE_RULES,
        "return_contract": {
            "return_path": ".write_return_%s.json" % section,
            "fields": ["section_id", "markdown", "new_refs", "new_abbrev",
                       "new_claims", "placeholders"],
        },
    }
    refs = {
        "outline_path": os.path.join(root, "project_state.json"),
        "lit_index_path": os.path.join(root, "literature_index.json"),
        "matrix_path": os.path.join(root, "chapter_matrix.json"),
        "progress_path": os.path.join(root, "project_state.json"),
    }
    pack = {"section_id": section, "embed": embed, "refs": refs}

    out = args.out or os.path.join(root, ".write_task_%s.json" % section)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    sys.stderr.write("TASK_PATH=%s\n" % os.path.abspath(out))
    res = {"ok": True, "section": section, "task_path": out}
    if warning:
        res["warning"] = warning
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0)


# ---------------------------------------------------------------------------
# verify-write
# ---------------------------------------------------------------------------

def _fail1(msg):
    sys.stderr.write("VERIFY_WRITE: FAIL %s\n" % msg)
    print(json.dumps({"ok": False, "problems": [msg]}, ensure_ascii=False))
    sys.exit(1)


def cmd_verify_write(args):
    section = args.section
    root = args.root
    task_path = args.task or os.path.join(root, ".write_task_%s.json" % section)
    ret_path = args.ret or os.path.join(root, ".write_return_%s.json" % section)

    # V9：文件存在
    if not os.path.isfile(ret_path):
        die("文件不存在: %s" % ret_path)
    if not os.path.isfile(task_path):
        die("文件不存在: %s" % task_path)

    try:
        ret = load_json(ret_path)
    except Exception:
        die("返回必须是 JSON 对象（畸形 JSON）")
    task = load_json(task_path)

    # V8：JSON 对象 + 有 markdown 字段
    if not isinstance(ret, dict):
        die("返回必须是 JSON 对象")
    if "markdown" not in ret:
        die("缺 markdown 字段")

    markdown = ret.get("markdown")
    new_refs = ret.get("new_refs") or []
    new_claims = ret.get("new_claims") or []

    task_section_id = task.get("section_id") or task.get("embed", {}).get("section_id")
    lit_section = task.get("embed", {}).get("lit_section") or task.get("lit_section") or []

    try:
        lit = load_json(os.path.join(root, "literature_index.json"))
    except Exception:
        lit = []
    if not isinstance(lit, list):
        lit = []

    # V1：markdown 非空
    if not (isinstance(markdown, str) and markdown.strip()):
        _fail1("markdown 为空")

    # V2：无裸数字引用
    if BARE_NUM_RE.search(markdown):
        _fail1("正文出现裸数字引用，只允许 [@key]")

    # V5：new_refs 每条 key 合法（new: 前缀）且唯一——先于 V3，
    #     否则正文引了一个坏前缀 new_ref 键会被 V3 误报为"无法解析"而非 V5。
    seen = set()
    for nr in new_refs:
        key = nr.get("key", "")
        if not (isinstance(key, str) and key.startswith("new:")) or key in seen:
            _fail1("new_refs key 非法或重复")
        seen.add(key)
    # V4：new_refs 每条 doi/pmid 至少一个
    for nr in new_refs:
        if not (nr.get("doi") or nr.get("pmid")):
            _fail1("new_refs 条目缺 DOI 和 PMID")

    # 可解析集合
    verified_ids = {e.get("id") for e in lit if e.get("verified", True)}
    lit_section_keys = {item.get("key") for item in lit_section}
    valid_cite = verified_ids | lit_section_keys
    new_key_set = {nr.get("key") for nr in new_refs}

    # V3：每个 [@key] 可解析
    for key in KEY_RE.findall(markdown):
        if key.startswith("new:"):
            if key not in new_key_set:
                _fail1("引用键无法解析: %s" % key)
        elif key not in valid_cite:
            _fail1("引用键无法解析: %s" % key)

    # V6：section_id 一致
    if ret.get("section_id") != task_section_id:
        _fail1("section_id 不匹配")

    # V7：new_claims 的 ref_key 可解析（纯结构，非承重语义门）
    all_ids = {e.get("id") for e in lit} | new_key_set
    for nc in new_claims:
        rk = nc.get("ref_key")
        if rk not in all_ids:
            _fail1("new_claims 的 ref_key 无法解析: %s" % rk)

    print(json.dumps({"ok": True, "section": section,
                      "checks": ["V1", "V2", "V3", "V4", "V5", "V6", "V7"]},
                     ensure_ascii=False))
    sys.exit(0)


def main():
    p = argparse.ArgumentParser(description="sci2doc 撰写任务包 + 返回校验")
    sub = p.add_subparsers(dest="cmd", required=True)

    pw = sub.add_parser("pack-write")
    pw.add_argument("--section", required=True)
    pw.add_argument("--root", required=True)
    pw.add_argument("--out", default=None)

    vw = sub.add_parser("verify-write")
    vw.add_argument("--section", required=True)
    vw.add_argument("--root", required=True)
    vw.add_argument("--return", dest="ret", default=None)
    vw.add_argument("--task", dest="task", default=None)

    args = p.parse_args()
    if args.cmd == "pack-write":
        cmd_pack_write(args)
    elif args.cmd == "verify-write":
        cmd_verify_write(args)


if __name__ == "__main__":
    main()

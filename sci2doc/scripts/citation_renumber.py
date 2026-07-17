#!/usr/bin/env python3
# citation_renumber.py —— sci2doc 认键翻号 + 去重并表（INTERFACE §3）
#
# 两个子命令：
#   merge-refs  去重并表 new_refs（DOI→PMID→归一标题）+ upsert chapter_matrix + 记 new:slug→真id 映射
#   renumber    正文 [@key]→连续 [N]，按 reference_renderer.citation_sort_key 同一排序
#
# 退出码：0=OK；1=（renumber 翻号失败，本脚本未用到 1 态，保留）；2=用法错/校验不过/文件畸形。
#
# 账本主会话独写：本脚本是主会话侧脚本；[@new:slug]→真id 的映射持久化到 <root>/.newref_map.json，
#   供 renumber 解析未回写的 [@new:] 键（不改 atomic md 源，[@key] 是真源）。

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reference_renderer import citation_sort_key  # 单一排序真源，禁止复制逻辑

KEY_RE = re.compile(r"\[@([A-Za-z0-9:_\-]+)\]")          # 合法引用键
ANY_AT_RE = re.compile(r"\[@([^\]]*)\]")                 # 任意 [@...]（含畸形），用于查畸形键
KEY_CHARS_RE = re.compile(r"^[A-Za-z0-9:_\-]+$")


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def norm_doi(doi):
    if not doi:
        return ""
    d = str(doi).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d.rstrip("/.")


def norm_pmid(pmid):
    return str(pmid).strip() if pmid else ""


def norm_title(title):
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(title).lower())


def load_literature_index(root):
    path = os.path.join(root, "literature_index.json")
    if not os.path.isfile(path):
        die("literature_index 缺失或非数组")
    try:
        data = load_json(path)
    except Exception:
        die("literature_index 缺失或非数组")
    if not isinstance(data, list):
        die("literature_index 缺失或非数组")
    return path, data


def next_ref_id(entries):
    mx = 0
    for e in entries:
        m = re.search(r"\d+", str(e.get("id", "")))
        if m:
            mx = max(mx, int(m.group()))
    return "ref%03d" % (mx + 1)


def find_existing(entry_new, entries):
    """按 DOI 精确 → PMID 精确 → 归一标题 与现有条目比对，命中返回其 id，否则 None。"""
    nd = norm_doi(entry_new.get("doi"))
    np_ = norm_pmid(entry_new.get("pmid"))
    nt = norm_title(entry_new.get("title"))
    for e in entries:
        if nd and norm_doi(e.get("doi")) == nd:
            return e.get("id")
    for e in entries:
        if np_ and norm_pmid(e.get("pmid")) == np_:
            return e.get("id")
    for e in entries:
        if nt and norm_title(e.get("title")) == nt:
            return e.get("id")
    return None


# ---------------------------------------------------------------------------
# merge-refs
# ---------------------------------------------------------------------------

def cmd_merge_refs(args):
    root = args.root
    ret_path = args.ret or os.path.join(root, ".write_return.json")

    if not os.path.isfile(ret_path):
        die("文件不存在: %s" % ret_path)
    try:
        ret = load_json(ret_path)
    except Exception:
        die("返回必须是 JSON 对象（畸形 JSON）")
    if not isinstance(ret, dict):
        die("返回必须是 JSON 对象")

    new_refs = ret.get("new_refs")
    if not isinstance(new_refs, list):
        die("new_refs 非数组")

    index_path, entries = load_literature_index(root)

    section_id = ret.get("section_id")
    if new_refs and not section_id:
        die("return 缺 section_id")

    # 逐条校验
    for nr in new_refs:
        key = nr.get("key", "")
        if not (isinstance(key, str) and key.startswith("new:")):
            die("new_refs key 非法: %r" % key)
        if not (nr.get("doi") or nr.get("pmid")):
            die("new_refs 条目缺 DOI 和 PMID: %s" % key)

    mapping = {}
    merged = 0
    deduped = 0
    resolved_ids = []
    for nr in new_refs:
        key = nr["key"]
        hit = find_existing(nr, entries)
        if hit is not None:
            mapping[key] = hit
            deduped += 1
            resolved_ids.append(hit)
        else:
            new_id = next_ref_id(entries)
            entry = {
                "id": new_id,
                "title": nr.get("title", ""),
                "doi": nr.get("doi") or None,
                "pmid": nr.get("pmid") or None,
                "verified": True,
            }
            entries.append(entry)
            mapping[key] = new_id
            merged += 1
            resolved_ids.append(new_id)

    # 落库 literature_index（主会话单写）
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except Exception as e:
        die("literature_index 写入失败: %s" % e)

    # 持久化 new:slug→真id 映射，供 renumber 解析
    if mapping:
        map_path = os.path.join(root, ".newref_map.json")
        keymap = {}
        if os.path.isfile(map_path):
            try:
                keymap = load_json(map_path)
            except Exception:
                keymap = {}
        keymap.update(mapping)
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(keymap, f, ensure_ascii=False, indent=2)

    # upsert chapter_matrix（行键 (id, section_id)，幂等）
    if resolved_ids and section_id:
        try:
            _upsert_chapter_matrix(root, resolved_ids, section_id, entries)
        except Exception:
            die("chapter_matrix upsert 失败")

    print(json.dumps({"ok": True, "merged": merged, "deduped": deduped,
                      "mapping": mapping}, ensure_ascii=False))
    sys.exit(0)


def _upsert_chapter_matrix(root, ids, section_id, entries):
    path = os.path.join(root, "chapter_matrix.json")
    rows = []
    if os.path.isfile(path):
        data = load_json(path)
        rows = data if isinstance(data, list) else data.get("rows", [])
    by_id = {e.get("id"): e for e in entries}
    existing = {(r.get("id"), r.get("section_id")) for r in rows}
    for rid in ids:
        if (rid, section_id) in existing:
            continue
        e = by_id.get(rid, {})
        rows.append({
            "id": rid,
            "section_id": section_id,
            "chapter": section_id.split(".")[0],
            "title": e.get("title", ""),
            "abstract": e.get("abstract", ""),
            "article_type": e.get("article_type", "unknown"),
            "verified": e.get("verified", True),
        })
        existing.add((rid, section_id))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# renumber
# ---------------------------------------------------------------------------

def cmd_renumber(args):
    root = args.root
    chapter = args.chapter
    prefix = "RENUMBER_CHECK: FAIL " if args.check else ""

    def fail(msg):
        die(prefix + msg)

    _, entries = load_literature_index(root)

    chap_dir = os.path.join(root, "atomic_md", "第%d章" % chapter)
    if not os.path.isdir(chap_dir):
        fail("章目录不存在: %s" % chap_dir)

    md_files = sorted(
        os.path.join(chap_dir, fn) for fn in os.listdir(chap_dir) if fn.endswith(".md")
    )

    # new:slug→真id 映射
    keymap = {}
    map_path = os.path.join(root, ".newref_map.json")
    if os.path.isfile(map_path):
        try:
            keymap = load_json(map_path)
        except Exception:
            keymap = {}

    # id → 出现次数（查冲突）
    id_count = {}
    for e in entries:
        id_count[e.get("id")] = id_count.get(e.get("id"), 0) + 1

    # 扫描所有 md，查畸形键 + 收集引用键
    file_texts = {}
    cited_keys = []
    for path in md_files:
        text = open(path, encoding="utf-8").read()
        file_texts[path] = text
        for m in ANY_AT_RE.finditer(text):
            raw = m.group(0)
            grp = m.group(1)
            if not grp or not KEY_CHARS_RE.match(grp):
                fail("畸形引用键: %s" % raw)
            cited_keys.append(grp)

    # 解析每个键 → 真 id
    key_to_id = {}
    for key in cited_keys:
        if key in key_to_id:
            continue
        if key.startswith("new:"):
            rid = keymap.get(key)
            if not rid:
                fail("未知引用键: %s（先 merge-refs 再翻号）" % key)
        else:
            if key not in id_count:
                fail("未知引用键: %s（先 merge-refs 再翻号）" % key)
            rid = key
        if id_count.get(rid, 0) > 1:
            fail("id 冲突: %s" % rid)
        key_to_id[key] = rid

    # 编号：按 citation_sort_key 对全部 index 条目排序，第 N 条→[N]
    ordered = sorted(entries, key=citation_sort_key)
    id_to_num = {}
    for i, e in enumerate(ordered, start=1):
        id_to_num.setdefault(e.get("id"), i)

    mapping = {rid: id_to_num[rid] for rid in set(key_to_id.values()) if rid in id_to_num}

    if args.check:
        print(json.dumps({"ok": True, "chapter": chapter, "renumbered": len(cited_keys),
                          "mapping": mapping}, ensure_ascii=False))
        sys.exit(0)

    # 翻号：[@key]→[N]
    def repl(m):
        key = m.group(1)
        return "[%d]" % id_to_num[key_to_id[key]]

    renumbered = 0
    out_dir = args.out_dir or os.path.join(root, "renumber_out", "第%d章" % chapter)
    for path, text in file_texts.items():
        new_text, n = KEY_RE.subn(repl, text)
        renumbered += n
        if args.in_place:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
        else:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, os.path.basename(path)), "w", encoding="utf-8") as f:
                f.write(new_text)

    print(json.dumps({"ok": True, "chapter": chapter, "renumbered": renumbered,
                      "mapping": mapping}, ensure_ascii=False))
    sys.exit(0)


def main():
    p = argparse.ArgumentParser(description="sci2doc 认键翻号 + 去重并表")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge-refs", help="去重并表 new_refs + upsert chapter_matrix")
    m.add_argument("--root", required=True)
    m.add_argument("--return", dest="ret", default=None)

    r = sub.add_parser("renumber", help="[@key]→连续 [N]")
    r.add_argument("--root", required=True)
    r.add_argument("--chapter", type=int, required=True)
    r.add_argument("--out-dir", dest="out_dir", default=None)
    r.add_argument("--in-place", dest="in_place", action="store_true")
    r.add_argument("--check", action="store_true")

    args = p.parse_args()
    if not os.path.isdir(args.root):
        die("root not a directory: %s" % args.root)

    if args.cmd == "merge-refs":
        cmd_merge_refs(args)
    elif args.cmd == "renumber":
        cmd_renumber(args)


if __name__ == "__main__":
    main()

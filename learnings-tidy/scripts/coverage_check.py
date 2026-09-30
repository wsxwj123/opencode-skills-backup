#!/usr/bin/env python3
"""coverage_check.py —— 拿「事实指纹」在压缩后的文件里逐项回查，给命中/缺失表 + 覆盖率。

判据：硬事实只能「只增不减」。任何一项在压缩件里缺失，都要么回补，要么在报告里交代。

用法：
  python3 coverage_check.py --source <原文件> --target <压缩件> --facts <fp.json>
  python3 coverage_check.py --selftest        # 自检：证明它真能抓出被漏掉的事实

退出码：缺失为 0 → 0；有缺失 → 1（便于脚本判定）。只读输入；不联网。
"""
import argparse
import json
import sys
from collections import Counter


def load_facts(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(facts, target_text):
    """返回 (hits, miss)，都按 kind 排好序。"""
    hits, miss = [], []
    for it in facts.get("items", []):
        (hits if it["text"] in target_text else miss).append(it)
    key = lambda d: (d.get("kind", ""), d["text"])
    return sorted(hits, key=key), sorted(miss, key=key)


def report(facts, target_text, source=None):
    hits, miss = check(facts, target_text)
    total = len(hits) + len(miss)
    pct = (100.0 * len(hits) / total) if total else 100.0
    creds = facts.get("credentials", [])
    print("== coverage_check ==")
    if source:
        print("source: %s" % source)
    print("facts: %d   hits: %d   missing: %d   coverage: %.1f%%" % (total, len(hits), len(miss), pct))
    by_kind = Counter(it.get("kind", "?") for it in miss)
    if miss:
        print("MISSING (%d) —— 逐项交代或回补，缺一不可:" % len(miss))
        for it in miss:
            print("  [%s] %s" % (it.get("kind", "?"), it["text"]))
        print("  按类型: %s" % dict(by_kind))
    else:
        print("MISSING: 0 —— 全部硬事实命中。")
    if creds:
        print("凭证: 指纹记录 %d 处（形状 %s）——压缩件里必须为 0，按形状人工复核。"
              % (len(creds), ", ".join(sorted({c["shape"] for c in creds}))))
    return len(miss)


def _selftest():
    facts = {"items": [
        {"text": "LibreSSL SSL_read: bad decrypt", "kind": "code", "count": 1},
        {"text": "7897", "kind": "number", "count": 2},
        {"text": "2.1.269", "kind": "number", "count": 1},
        {"text": "/Users/wsxwj/.learnings/ERRORS.md", "kind": "path", "count": 1},
        {"text": "16000", "kind": "number", "count": 3},
    ], "credentials": []}
    # 目标里故意漏掉 7897 / 2.1.269 / 路径 三项，其余保留
    target = "报错 LibreSSL SSL_read: bad decrypt；上限 16000 token；重试 3 次。"
    hits, miss = check(facts, target)
    got_miss = {m["text"] for m in miss}
    want_miss = {"7897", "2.1.269", "/Users/wsxwj/.learnings/ERRORS.md"}
    if got_miss != want_miss:
        print("FAIL 缺失集合不符: got=%s want=%s" % (sorted(got_miss), sorted(want_miss)))
        return 1
    if {h["text"] for h in hits} != {"LibreSSL SSL_read: bad decrypt", "16000"}:
        print("FAIL 命中集合不符（把保留项误判了）")
        return 1
    # 反向：把漏掉的补回去，缺失必须清零（证明不是恒报缺失的摆设）
    full = target + " 端口 7897 版本 2.1.269 见 /Users/wsxwj/.learnings/ERRORS.md"
    if check(facts, full)[1]:
        print("FAIL 补全后仍在报缺失")
        return 1
    print("PASS coverage_check: 抓出 3 项故意漏掉的事实，补全后归零。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="压缩前后事实覆盖率回查")
    ap.add_argument("--source", help="原文件（仅用于标注）")
    ap.add_argument("--target", help="压缩件")
    ap.add_argument("--facts", help="fact_fingerprint 产出的 JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if not (args.target and args.facts):
        ap.error("需要 --target 与 --facts（--selftest 除外）")
    with open(args.target, encoding="utf-8", errors="replace") as fh:
        target_text = fh.read()
    miss = report(load_facts(args.facts), target_text, args.source)
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())

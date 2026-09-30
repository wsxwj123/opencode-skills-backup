#!/usr/bin/env python3
"""family_report.py —— 给「体检分档」提供数字：按分节 / 关键词分桶统计条目数与疑似同族。

分档要看三样：行数 W、条目数 N、重复族数 F（同族 = 同一主题/根因出现 >=2 条）。
本脚本用「分节标题 + 关键词表」做启发式分桶，只作 Step 1 的量化参考，最终由人确认。

用法：
  python3 family_report.py <file>
  python3 family_report.py <file> --keywords "zsh,子代理,16k,token"   # 覆盖默认关键词表
  python3 family_report.py --selftest        # 自检：证明同族识别有判别力

只读输入文件；不联网；输出走 stdout。
"""
import argparse
import re
import sys
from collections import Counter

DEFAULT_KEYWORDS = [
    "zsh", "glob", "NOMATCH", "子代理", "16k", "输出上限", "token", "OAuth", "凭证",
    "代理", "proxy", "worktree", "pytest", "playwright", "launchd", "heredoc",
    "引号", "锁", "编码", "Windows", "MCP", "Clash", "sed", "path", "缓存",
]
SECTION_RE = re.compile(r"^##\s+(?!#)(.*\S)\s*$")     # 二级标题 = 分节
ENTRY_RE = re.compile(r"^(?:###\s+|\d+\.\s+|[-*]\s+)\S")  # 条目起始行


def analyze(text, name, keywords=None):
    keywords = keywords or DEFAULT_KEYWORDS
    section, section_counts = "(无分节)", Counter()
    entries, families = [], Counter()
    kw_hits = {k: [] for k in keywords}
    for line in text.splitlines():
        ms = SECTION_RE.match(line)
        if ms:
            section = ms.group(1).strip()[:40]
            continue
        if ENTRY_RE.match(line):
            title = line.strip("-#*0123456789. \t")[:60]
            entries.append((section, title))
            section_counts[section] += 1
            low = line.lower()
            for k in keywords:
                if k.lower() in low:
                    families[k] += 1
                    if len(kw_hits[k]) < 3:
                        kw_hits[k].append(title)
    return {"file": name, "entries": entries, "sections": section_counts,
            "families": {k: v for k, v in families.items() if v >= 2}, "kw_hits": kw_hits}


def _selftest():
    sample = "\n".join([
        "# 库", "## 一 A", "### zsh glob 无匹配", "- 现象描述一",
        "### zsh 拆词", "- 现象描述二", "## 二 B", "### pokemon 训练", "- 现象描述三",
    ])
    rep = analyze(sample, "<selftest>", ["zsh", "pokemon"])
    if rep["families"].get("zsh") != 2:
        print("FAIL zsh 同族未识别: %s" % rep["families"])
        return 1
    if "pokemon" in rep["families"]:
        print("FAIL pokemon 只出现 1 次却算成同族")
        return 1
    if rep["sections"].get("一 A") != 4:
        print("FAIL 分节条目数不对: %s" % dict(rep["sections"]))
        return 1
    print("PASS family_report: 识别 zsh 同族(2)，不误报单例 pokemon，分节计数正确。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="按分节/关键词统计条目数与疑似同族")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--keywords", help="逗号分隔的关键词表（覆盖默认）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if not args.file:
        ap.error("需要 <file>（或 --selftest）")
    kws = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
    with open(args.file, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    rep = analyze(text, args.file, kws)
    print("== family_report == %s" % rep["file"])
    print("总条目(含标题行与 bullet): %d" % len(rep["entries"]))
    print("分节条目数:")
    for sec, n in rep["sections"].most_common():
        print("  %-28s %d" % (sec, n))
    if rep["families"]:
        print("疑似同族(关键词 -> 出现条数，>=2 才列):")
        for k, n in sorted(rep["families"].items(), key=lambda x: -x[1]):
            print("  %-12s %d   e.g. %s" % (k, n, " / ".join(rep["kw_hits"][k])))
    else:
        print("疑似同族: 无（关键词均只出现 <=1 次）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

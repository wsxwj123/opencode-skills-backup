#!/usr/bin/env python3
"""Word and page counting helpers for nsfc-proposal."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# \u5b57\u6570/\u9875\u6570\u786c\u4e0a\u9650\u2014\u2014\u5168\u4ed3\u552f\u4e00\u5b9a\u4e49\u5904\uff08INTERFACE-round24 \u00a71\uff09\u3002
# \u952e\u662f sections/ \u4e0b\u7684 basename\uff0c\u4e0e structure_profile.chapters[].filename \u540c\u4e00\u628a\u5c3a\u3002
# \u6d88\u8d39\u65b9\u4e00\u5f8b\u7ecf resolve_word_limit / resolve_page_limit \u53d6\u503c\uff0c\u4e0d\u8bb8\u53e6\u6284\u6570\u5b57\u3002
# ---------------------------------------------------------------------------
NSFC_WORD_MAX = {
    "00_\u6458\u8981_\u4e2d\u6587.md": 400,
    "00_\u6458\u8981_\u82f1\u6587.md": 300,
    "P3_4_\u5b8c\u6210\u57fa\u91d1\u9879\u76ee\u60c5\u51b5.md": 500,
    "P4_\u5176\u4ed6\u9700\u8981\u8bf4\u660e\u7684\u60c5\u51b5.md": 500,
}
NSFC_PAGE_MAX = 30

_WARN_LINE = "WORD_LIMIT: WARN structure_profile \u4e0d\u53ef\u7528\uff0c\u672c\u6b21\u6309\u56fd\u81ea\u7136\u9ed8\u8ba4\u4e0a\u9650"


def resolve_word_limit(root, filename):
    """\u5b57\u6570\u4e0a\u9650\u89e3\u6790\uff08INTERFACE-round24 \u00a72 \u4e5d\u884c\u5224\u5b9a\u8868\uff09\u3002

    \u7eaf\u51fd\u6570\uff1a\u7edd\u4e0d\u629b\u5f02\u5e38\u3001\u7edd\u4e0d sys.exit\u3001\u7edd\u4e0d\u5199\u6587\u4ef6\u3002filename \u662f sections/ \u4e0b\u7684
    basename\uff08\u4f20\u5168\u8def\u5f84\u4e0d\u505a\u5f52\u4e00\u5316\uff0c\u6309\u300c\u8868\u91cc\u67e5\u4e0d\u5230\u300d\u5904\u7406\uff09\u3002
    \u8fd4\u56de (limit, source)\uff0csource \u2208 {"structure_profile", "nsfc_default", "unset"}\u3002
    """
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import structure_profile
        prof = structure_profile.load(root)
    except Exception:
        # \u884c 9\uff1a\u8bfb\u53e3\u4e0d\u53ef\u7528 \u2192 \u6309\u56fd\u81ea\u7136\u9ed8\u8ba4\u5168\u91cf\u6267\u884c\uff0c\u4e0d\u9759\u9ed8\u3001\u4e0d\u5d29\uff08\u540c r23 WARN \u65b9\u5411\uff09
        print(_WARN_LINE, file=sys.stderr)
        return NSFC_WORD_MAX.get(filename), "nsfc_default"
    chapters = prof.get("chapters") if isinstance(prof, dict) else None
    if not isinstance(chapters, list) or not chapters:
        # \u884c 1-3\uff1a\u65e0\u771f\u6e90/\u574f/\u672a\u786e\u8ba4/\u65e0 chapters \u952e\uff08\u7ae0\u8282\u8868\u4e0d\u53d7\u7ba1\uff09\u2192 \u56fd\u81ea\u7136\u9ed8\u8ba4
        if filename in NSFC_WORD_MAX:
            return NSFC_WORD_MAX[filename], "nsfc_default"
        return None, "unset"      # \u884c 8\uff1a\u8868\u5916\u6587\u4ef6\u65e0\u9ed8\u8ba4\u53ef\u7528
    for ch in chapters:
        if isinstance(ch, dict) and ch.get("filename") == filename:
            wm = ch.get("word_max")
            if isinstance(wm, int) and not isinstance(wm, bool) and wm >= 0:
                return wm, "structure_profile"   # \u884c 4\uff1aword_max == 0 \u5408\u6cd5
            return None, "unset"  # \u884c 5/6\uff1a\u7f3a\u6216\u975e\u6cd5 \u2192 \u4e0d\u5224\u3001\u4ea4\u4eba\u5de5\uff0c\u7edd\u4e0d\u56de\u843d\u9ed8\u8ba4
    return None, "unset"          # \u884c 7\uff1a\u53d7\u7ba1\u4f46\u6ca1\u5217\u8be5\u7ae0


def resolve_page_limit(root):
    """\u9875\u6570\u4e0a\u9650\u89e3\u6790\uff08INTERFACE-round24 \u00a73\uff09\u3002\u6052\u8fd4\u56de (int, source)\uff0c\u6c38\u4e0d\u4e3a None\u3002

    \u8003\u5377\u53e3\u5f84\uff08\u4f18\u5148\u4e8e INTERFACE \u00a73 \u7b2c 1 \u884c\u5b57\u9762\uff09\uff1a\u58f0\u660e\u503c\u7b49\u4e8e NSFC_PAGE_MAX \u65f6
    \u62a5 nsfc_default\u2014\u2014DEFAULT_PROFILE \u81ea\u5e26 page_limit=30\uff0c\u56fd\u81ea\u7136\u9ed8\u8ba4\u9879\u76ee\u4e0d\u7b97\u300c\u58f0\u660e\u8fc7\u300d\u3002
    """
    try:
        with open(os.path.join(str(root), "proposal_profile.json"), encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return NSFC_PAGE_MAX, "nsfc_default"
    pl = data.get("page_limit") if isinstance(data, dict) else None
    if isinstance(pl, int) and not isinstance(pl, bool) and pl >= 0:
        if pl == NSFC_PAGE_MAX:
            return NSFC_PAGE_MAX, "nsfc_default"
        return pl, "proposal_profile"   # 0 \u662f\u5408\u6cd5\u58f0\u660e\uff08\u9875\u6570\u5fc5\u8d85\u53cd\u4f8b\u4f9d\u8d56\u5b83\uff09\uff0c\u4e0d\u56de\u843d
    return NSFC_PAGE_MAX, "nsfc_default"


HAN_RE = re.compile(r"[\u4e00-\u9fff]")
EN_RE = re.compile(r"[A-Za-z0-9_]+")
# Markdown formatting symbols to strip before counting (not content)
MD_RE = re.compile(r"[*#`\[\]!>|~^{}=\-]")


def count_text(text: str) -> int:
    # Strip markdown formatting characters, then count:
    # - each Chinese character as 1 word (matches Word \u5b57\u6570\u7edf\u8ba1)
    # - each continuous English/digit token as 1 word
    # Punctuation (\uff0c\u3002\uff01\uff1fetc.) is NOT counted, matching Word behaviour
    clean = MD_RE.sub(" ", text)
    han = len(HAN_RE.findall(clean))
    en = len(EN_RE.findall(clean))
    return han + en


def count_file(path: Path) -> int:
    return count_text(path.read_text(encoding="utf-8"))


def count_all(sections_dir: Path, pattern: str = "*.md") -> dict[str, int]:
    result: dict[str, int] = {}
    for p in sorted(sections_dir.glob(pattern)):
        result[p.name] = count_file(p)
    result["__total__"] = sum(v for k, v in result.items() if not k.startswith("__"))
    return result


def estimate_pages(total_words: int, words_per_page: int = 800) -> int:
    return math.ceil(total_words / words_per_page) if total_words > 0 else 0


def summary(sections_dir: Path, pattern: str = "*.md", words_per_page: int = 800) -> dict:
    data = count_all(sections_dir, pattern)
    total = data["__total__"]
    pages = estimate_pages(total, words_per_page)
    items = [{"file": k, "words": v} for k, v in data.items() if not k.startswith("__")]
    items = sorted(items, key=lambda x: x["words"], reverse=True)
    return {
        "word_count": data,
        "page_estimate": pages,
        "top_sections": items[:5],
    }


def _run_check(args) -> int:
    """check 子命令（INTERFACE-round24 §4）：纯读 + 打印，不写任何文件。
    rc 与判定正交：超限/上限不可判都是 rc 0（单行 JSON）；目标读不出才 rc 1。"""
    if args.file is not None:
        target = args.file
        try:
            count = count_file(Path(target))
        except (OSError, ValueError) as e:
            print("WORD_LIMIT: MISSING %s: %s" % (target, str(e) or type(e).__name__),
                  file=sys.stderr)
            return 1
        limit, source = resolve_word_limit(args.root, os.path.basename(target))
        kind = "words"
    else:
        target = args.pages
        if not os.path.isdir(target):
            print("WORD_LIMIT: MISSING %s: FileNotFoundError" % target, file=sys.stderr)
            return 1
        count = estimate_pages(count_all(Path(target))["__total__"])
        limit, source = resolve_page_limit(args.root)
        kind = "pages"
    if source == "unset":
        print("WORD_LIMIT: UNSET %s 结构真源受管但该章未声明 word_max，"
              "本项须人工裁决，不得判 pass" % target, file=sys.stderr)
        print("处置：给 structure_profile.json 里该章补 word_max（须带 word_max_evidence），"
              "或本项人工核定。", file=sys.stderr)
    ok = None if limit is None else count <= limit
    print(json.dumps({"kind": kind, "target": target, "count": count,
                      "limit": limit, "limit_source": source, "ok": ok},
                     ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_count = sub.add_parser("count")
    p_count.add_argument("path")

    p_all = sub.add_parser("count-all")
    p_all.add_argument("sections_dir")
    p_all.add_argument("--pattern", default="*.md")

    p_pages = sub.add_parser("page-estimate")
    p_pages.add_argument("total_words", type=int)
    p_pages.add_argument("--words-per-page", type=int, default=800)

    p_summary = sub.add_parser("summary")
    p_summary.add_argument("sections_dir")
    p_summary.add_argument("--pattern", default="*.md")
    p_summary.add_argument("--words-per-page", type=int, default=800)

    p_check = sub.add_parser("check")
    p_check.add_argument("--root", required=True)
    grp = p_check.add_mutually_exclusive_group(required=True)
    grp.add_argument("--file")
    grp.add_argument("--pages")

    args = parser.parse_args()

    if args.cmd == "check":
        return _run_check(args)

    if args.cmd == "count":
        print(count_file(Path(args.path)))
        return 0

    if args.cmd == "count-all":
        print(json.dumps(count_all(Path(args.sections_dir), args.pattern), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "page-estimate":
        print(estimate_pages(args.total_words, args.words_per_page))
        return 0

    if args.cmd == "summary":
        print(json.dumps(summary(Path(args.sections_dir), args.pattern, args.words_per_page), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

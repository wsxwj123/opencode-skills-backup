#!/usr/bin/env python3
"""Anti-AI Chinese style checks for nsfc-proposal."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BANNED_PATTERNS = [
    (r"不是[^，。]+而是", "pattern_not_but", "改为直接陈述句，避免对比模板"),
    (r"不仅[^，。]+而且", "pattern_not_only_but_also", "拆成两句事实陈述"),
    (r"值得注意的是", "filler_phrase", "删除该提示语，直接给结论"),
    (r"需要指出的是", "filler_phrase", "删除该提示语，直接给证据"),
    (r"至关重要|举足轻重|不可或缺", "overstatement", "用具体数据替代形容词"),
    (r"综上所述|总而言之", "template_transition", "用事实句结束段落"),
    (r"在此基础上|鉴于此", "ai_transition", "直接写因果关系"),
]

VAGUE_PATTERNS = [
    (r"近年来", "replace_with_exact_year_range", "改为具体年份范围，如2020年以来"),
    (r"大量研究表明", "replace_with_named_citations", "改为明确作者+文献编号"),
    (r"取得了显著进展", "replace_with_specific_progress", "改为具体进展内容"),
    (r"广泛应用", "replace_with_specific_scenarios", "列出应用场景"),
]

BULLET_PATTERNS = [
    (r"^\s*[\-\*•]\s", "bullet_list", "改为段落叙述"),
    (r"^\s*\d+[\.)]\s", "numbered_list", "改为段落叙述"),
    (r"^\s*[（\(][一二三四五六七八九十\d]+[）\)]", "cn_numbered_list", "改为段落叙述"),
]


def scan_text(text: str, allow_lists: bool = False) -> dict:
    issues = []

    for pattern, code, suggestion in BANNED_PATTERNS:
        for m in re.finditer(pattern, text):
            issues.append(
                {
                    "severity": "ERROR",
                    "code": code,
                    "span": [m.start(), m.end()],
                    "text": m.group(0),
                    "suggestion": suggestion,
                }
            )

    for pattern, code, suggestion in VAGUE_PATTERNS:
        for m in re.finditer(pattern, text):
            issues.append(
                {
                    "severity": "WARNING",
                    "code": code,
                    "span": [m.start(), m.end()],
                    "text": m.group(0),
                    "suggestion": suggestion,
                }
            )

    if not allow_lists:
        for i, line in enumerate(text.splitlines(), 1):
            for pattern, code, suggestion in BULLET_PATTERNS:
                if re.search(pattern, line):
                    issues.append(
                        {
                            "severity": "WARNING",
                            "code": code,
                            "line": i,
                            "text": line.strip(),
                            "suggestion": suggestion,
                        }
                    )

    return {"count": len(issues), "issues": issues}


def rhythm_check(text: str) -> dict:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    issues = []
    openers = []

    for idx, para in enumerate(paragraphs, 1):
        sents = [s for s in re.split(r"[。！？!?]", para) if s.strip()]
        lens = [len(s.strip()) for s in sents]
        for j in range(len(lens) - 2):
            window = lens[j : j + 3]
            if max(window) - min(window) < 5:
                issues.append({"paragraph": idx, "type": "flat_rhythm", "window": [j + 1, j + 3]})
        openers.append(para[:12])

    for i in range(len(openers) - 1):
        if openers[i] and openers[i] == openers[i + 1]:
            issues.append({"paragraph": i + 1, "type": "repeated_opener", "next_paragraph": i + 2, "text": openers[i]})

    return {"count": len(issues), "issues": issues}


def fix_suggest(text: str, allow_lists: bool = False) -> dict:
    scan = scan_text(text, allow_lists=allow_lists)
    suggestions = []
    for i in scan["issues"]:
        suggestions.append(
            {
                "code": i["code"],
                "original": i.get("text", ""),
                "suggestion": i.get("suggestion", ""),
            }
        )
    return {"count": len(suggestions), "suggestions": suggestions}


def scan_file(path: Path, allow_lists: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "path": str(path),
        "scan": scan_text(text, allow_lists=allow_lists),
        "rhythm": rhythm_check(text),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan")
    p_scan.add_argument("path")
    p_scan.add_argument("--allow-lists", action="store_true")

    p_scan_all = sub.add_parser("scan-all")
    p_scan_all.add_argument("sections_dir", nargs="?", default="sections")
    p_scan_all.add_argument("--allow-lists", action="store_true")

    p_fix = sub.add_parser("fix-suggest")
    p_fix.add_argument("path")
    p_fix.add_argument("--allow-lists", action="store_true")

    p_rhythm = sub.add_parser("rhythm-check")
    p_rhythm.add_argument("path")

    args = parser.parse_args()

    if args.cmd == "scan":
        print(json.dumps(scan_file(Path(args.path), allow_lists=args.allow_lists), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "scan-all":
        out = []
        for p in sorted(Path(args.sections_dir).glob("*.md")):
            allow = args.allow_lists or p.name.startswith("P3_3") or p.name.startswith("P3_4") or p.name.startswith("P4_")
            out.append(scan_file(p, allow_lists=allow))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "fix-suggest":
        text = Path(args.path).read_text(encoding="utf-8")
        print(json.dumps(fix_suggest(text, allow_lists=args.allow_lists), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "rhythm-check":
        text = Path(args.path).read_text(encoding="utf-8")
        print(json.dumps(rhythm_check(text), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

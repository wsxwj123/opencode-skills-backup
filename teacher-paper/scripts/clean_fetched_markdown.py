#!/usr/bin/env python3
"""对抓取得到的 Markdown 做轻量清洗。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NOISE_LINE_PATTERNS = [
    r"^Loading\.\.\.$",
    r"^Close$",
    r"^更多$",
    r"^Cancel$",
    r"^Allow$",
    r"^Got It$",
    r"^Scan to Follow$",
    r"^继续滑动看下一个$",
    r"^轻触阅读原文$",
    r"^微信扫一扫可打开此内容",
    r"^使用完整服务$",
    r"^预览时标签不可点$",
]

NOISE_BLOCK_PATTERNS = [
    r"赞赏二维码",
    r"微信扫一扫赞赏作者",
    r"Like the Author",
    r"Scan with Weixin",
    r"use this Mini Program",
    r"当前内容可能存在未经审核的第三方商业营销信息",
    r"选择留言身份",
    r"确认提交投诉",
]


def read_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    return sys.stdin.read()


def clean_markdown(text: str) -> str:
    lines = text.splitlines()
    kept = []
    in_code = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            kept.append(line)
            continue

        if in_code:
            kept.append(line)
            continue

        if any(re.search(p, line.strip(), flags=re.I) for p in NOISE_LINE_PATTERNS):
            continue
        if any(re.search(p, line, flags=re.I) for p in NOISE_BLOCK_PATTERNS):
            continue
        kept.append(line)

    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"!\[图片\]\(data:image/svg\+xml[^\n]*\)", "", cleaned)
    cleaned = re.sub(r"\n\|\s*\|\s*\|\n\|\s*---\s*\|\s*---\s*\|(?:\n\|[^\n]*)+", "", cleaned)
    return cleaned.strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="轻量清洗抓取得到的 Markdown")
    parser.add_argument("input", nargs="?", help="输入文件路径；不提供则从 stdin 读取")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()

    cleaned = clean_markdown(read_text(args.input))
    if args.output:
        Path(args.output).write_text(cleaned, encoding="utf-8")
    else:
        sys.stdout.write(cleaned)


if __name__ == "__main__":
    main()

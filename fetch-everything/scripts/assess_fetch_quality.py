#!/usr/bin/env python3
"""对抓取结果做轻量质量判定。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

BAD_PATTERNS = [
    r"环境异常",
    r"去验证",
    r"captcha",
    r"access denied",
    r"scan to (follow|continue|use)",
    r"微信扫一扫",
    r"loading\.\.\.",
    # Cloudflare / 反爬 challenge 盾页特征：命中即判低质，自动降级到隐身路线
    r"just a moment",
    r"checking (your|if the site)",
    r"attention required",
    r"cloudflare",
    r"ddos protection",
    r"enable javascript and cookies to continue",
    r"正在验证|请稍候",
]

# 正文/Markdown 结构信号（不含"任意非空行"这类几乎恒真的弱模式）
GOOD_PATTERNS = [
    r"\n\n",          # 段落分隔
    r"^\s{0,3}#{1,6}\s",  # Markdown 标题
    r"```",           # 代码块
    r"^\s*[-*+]\s",   # 列表
    r"https?://",     # 链接
]


def read_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    return sys.stdin.read()


def count_paragraphs(text: str) -> int:
    """统计正文段落。优先按空行分段；无空行（常见于中文抓取）时退化为按长行计数。"""
    blocks = [c for c in text.split("\n\n") if len(c.strip()) >= 20]
    if len(blocks) >= 2:
        return len(blocks)
    long_lines = [ln for ln in text.split("\n") if len(ln.strip()) >= 40]
    return max(len(blocks), len(long_lines))


def assess_text(text: str) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []
    stripped = text.strip()
    length = len(stripped)

    if length >= 600:
        score += 35
        reasons.append("内容长度较充足")
    elif length >= 250:
        score += 20
        reasons.append("内容长度基本可用")
    else:
        score -= 25
        reasons.append("内容偏短")

    bad_hits = [p for p in BAD_PATTERNS if re.search(p, stripped, flags=re.I)]
    if bad_hits:
        score -= 40
        reasons.append(f"命中异常/验证特征: {len(bad_hits)}")

    paragraph_count = count_paragraphs(stripped)
    if paragraph_count >= 5:
        score += 20
        reasons.append("存在多个正文段落")
    elif paragraph_count >= 2:
        score += 10
        reasons.append("存在少量正文段落")
    else:
        score -= 10
        reasons.append("正文段落不足")

    markdown_signals = sum(1 for p in GOOD_PATTERNS if re.search(p, stripped, flags=re.M))
    if markdown_signals >= 2:
        score += 10
        reasons.append("具备 Markdown/正文结构")

    ui_noise_hits = len(re.findall(r"(赞赏|更多|Close|Allow|Cancel|分享|扫一扫|轻触阅读原文)", stripped, flags=re.I))
    if ui_noise_hits >= 6:
        score -= 15
        reasons.append("尾部 UI 噪音较多")
    elif ui_noise_hits >= 2:
        score -= 5
        reasons.append("存在少量 UI 噪音")

    # 检测原始 HTML / JS 代码（非 Markdown 正文）
    html_tag_count = len(re.findall(r"<(?:div|script|style|span|meta|link|head|body|html)\b", stripped, flags=re.I))
    if html_tag_count >= 20:
        score -= 60
        reasons.append(f"疑似原始 HTML（标签数: {html_tag_count}）")
    elif html_tag_count >= 5:
        score -= 20
        reasons.append(f"混入较多 HTML 标签（标签数: {html_tag_count}）")

    # 检测 JS 代码密度
    js_indicators = len(re.findall(r"(?:function\s*\(|var\s+\w+\s*=|document\.\w+|window\.\w+|createElement|addEventListener)", stripped))
    if js_indicators >= 10:
        score -= 50
        reasons.append(f"疑似 JS 代码而非正文（JS 特征数: {js_indicators}）")

    passed = score >= 15 and not (bad_hits and length < 500) and html_tag_count < 20
    return {
        "score": score,
        "passed": passed,
        "reasons": reasons,
        "length": length,
        "paragraph_count": paragraph_count,
        "bad_pattern_hits": len(bad_hits),
        "ui_noise_hits": ui_noise_hits,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评估抓取文本质量")
    parser.add_argument("input", nargs="?", help="输入文件路径；不提供则从 stdin 读取")
    args = parser.parse_args()
    text = read_text(args.input)
    result = assess_text(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

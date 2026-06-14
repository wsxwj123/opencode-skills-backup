#!/usr/bin/env python3
"""对抓取结果做轻量质量判定。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

# 盾页 / 验证页 / 未渲染：命中任一即【一票否决】（无论内容多长都判失败，强制降级到浏览器路线）。
# 借鉴 crawl4ai 的否决式判定——这些特征出现在正文里的概率极低，宁可误判降级（浏览器重抓正常页也能成功）。
CHALLENGE_PATTERNS = [
    r"环境异常",
    r"去验证",
    r"captcha",
    r"access denied",
    r"just a moment",
    r"checking (your browser|if the site)",
    r"attention required",
    r"cloudflare",
    r"ddos protection",
    r"enable javascript and cookies to continue",
    r"正在验证|请稍候",
    # r.jina.ai 等返回的"页面未渲染完成"警告 → JS 空壳，必须降级到浏览器渲染
    r"maybe not yet fully loaded",
    r"consider .{0,20}specify a timeout",
]

# 软噪音：扣分但【不否决】（正常微信公众号正文尾部也常有这些，硬否决会误杀真正文）
SOFT_NOISE_PATTERNS = [
    r"scan to (follow|continue|use)",
    r"微信扫一扫",
    r"loading\.\.\.",
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

    challenge_hits = [p for p in CHALLENGE_PATTERNS if re.search(p, stripped, flags=re.I)]
    if challenge_hits:
        score -= 100  # 大幅扣分；并在下方 passed 处一票否决
        reasons.append(f"命中盾页/验证特征(硬否决): {len(challenge_hits)}")

    soft_noise = [p for p in SOFT_NOISE_PATTERNS if re.search(p, stripped, flags=re.I)]
    if soft_noise:
        score -= 10
        reasons.append(f"命中软噪音: {len(soft_noise)}")

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

    # 盾页/验证/未渲染特征一票否决，不再被长度架空
    passed = score >= 15 and not challenge_hits and html_tag_count < 20
    return {
        "score": score,
        "passed": passed,
        "reasons": reasons,
        "length": length,
        "paragraph_count": paragraph_count,
        "bad_pattern_hits": len(challenge_hits),
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

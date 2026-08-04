#!/usr/bin/env python3
"""Anti-AI style checker for literature reviews (review-writing variant).

Adapted from general-sci-writing/scripts/style_checker.py. Differences:
- Default input dir is `drafts` (review-writing drafts/section_XX_XX.md), not `manuscripts`.
- Passive voice target is the REVIEW threshold (<=30%), not the research-paper 50-70%.
  Reviews are written in a more active, synthesis-driven voice; >30% passive flags stiffness.
  Configurable via --passive-max (default 0.30).
- Adds a long-sentence check (single sentence >30 words) to back DoD item R5.

Measures:
- Sentence length variance (Perplexity/Burstiness)
- Passive voice ratio (review target <=30%)
- Long sentences (>30 words)
- Forbidden word/phrase hits
- Paragraph opening repetition
- Consecutive similar-length sentences
- Decorative em-dash / scare quotes / explanatory colon / trailing -ing clause

Outputs a JSON report with per-file and aggregate scores.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any


def is_merged_derivative(path: str) -> bool:
    """True for merge_manuscript.py outputs (Full_Manuscript.md / Draft_Round*_Manuscript.md).
    These carry the AUTO-GENERATED banner and duplicate the atomic sources, so
    scanning them produces false positives (e.g. banner em-dash)."""
    name = os.path.basename(path).lower()
    return name == "full_manuscript.md" or (name.startswith("draft_round") and name.endswith("_manuscript.md"))


# ── Forbidden words/phrases (AI-typical) ──────────────────────────────────────
FORBIDDEN_EXACT = {
    "delve into", "comprehensive landscape", "pivotal role", "realm",
    "tapestry", "underscore", "testament", "it is well known",
    "it is worth noting", "it should be noted", "importantly",
    "interestingly", "remarkably", "notably", "in recent years",
    "a growing body of evidence", "has garnered significant attention",
    "plays a crucial role", "a plethora of", "myriad of",
    "in the context of", "shed light on", "pave the way",
    "of paramount importance", "a key player",
}
# ── 中文 AI 套话（与上面英文表同级：命中即 high，计入 score）──────────────────
# 口径 = 英文表的中文镜像，一条中文对一条英文，两种语言同等待遇：
#   值得注意的是 ← it is worth noting / notably   综上所述/总而言之 ← taken together
#   越来越多的证据表明 ← a growing body of evidence  发挥关键作用 ← plays a crucial role
#   至关重要 ← of paramount importance            深入探讨 ← delve into
#
# 🔧 **要加/删一条套话，就改这个 set**（另一家 style_checker.py 是独立分叉副本，
#    两边都要改）。用户可见的说明：review-writing/references/writing_guidelines.md §4
#    「Chinese Mode」与 general-sci-writing/references/anti-ai-protocol.md。
#
# ponytail: 只收十条几乎没有正当用法的。刻意不收「此外/然而/近年来」这类正常连接词
# 与时间状语——真中文稿里高频且合法，收进来就是把正常稿判死（误伤比漏报更伤用户）。
# 真稿反馈说漏得多再加，别一次堆几百条。
FORBIDDEN_CN = {
    "值得注意的是", "综上所述", "总而言之", "不仅如此", "显而易见",
    "在此背景下", "深入探讨", "至关重要", "越来越多的证据表明", "发挥关键作用",
}
FORBIDDEN_PATTERNS = [
    re.compile(r"not only\b.*?\bbut also\b", re.IGNORECASE),
    re.compile(r"seamless[,\s]+intuitive[,\s]+and\s+powerful", re.IGNORECASE),
    # NOTE: removed `from\s+\w+\s+to\s+\w+` ("from X to Y"). In scientific reviews
    # this construction is high-frequency and legitimate ("from gut to joint",
    # "from adipogenic to osteogenic differentiation"); the false-positive rate
    # made the signal-to-noise ratio too poor to keep as an AI-rhetoric flag.
]

# ── Anti-AI: em-dash, scare quotes, explanatory colon ────────────────────────
# Em-dash (U+2014 —) used decoratively in prose (not in code/URLs/math).
EM_DASH_RE = re.compile(r"(?<!\d)—(?!\d)")
# 破折号配额：正常学术散文每千词 0–2 个 em dash，AI 生成文本显著更高。按密度而非
# 绝对数，否则 Polish Mode 导入的整篇长稿（8000 词）必然误伤。短文件给 2 个底线。
# ponytail: 阈值是启发式(每千词 2 个 + 底线 2)，真稿反馈说误报/漏报再调这两个数。
EM_DASH_PER_1K_WORDS = 2
EM_DASH_MIN_ALLOWANCE = 2


def em_dash_allowance(total_words: int) -> int:
    """本文件允许的 em dash 个数（超出即判密集滥用）。"""
    return max(EM_DASH_MIN_ALLOWANCE,
               int(max(0, total_words) / 1000 * EM_DASH_PER_1K_WORDS))
# Scare quotes: double-quoted phrase of 1-4 words not preceded by numeric citation
# context, to catch "synergistic", "perfect storm", etc.
SCARE_QUOTE_RE = re.compile(r'(?<!\[)(?<!\d)"([A-Za-z][^"]{1,40})"(?!\s*:)')
# Explanatory colon: "NounPhrase: Explanation" pattern in prose.
# Matches: Title-case phrase (1-4 words) followed by ": " then another capital+lower word.
# Excludes: digit before colon (ratio/time), all-caps acronym before colon.
EXPLANATORY_COLON_RE = re.compile(
    r"(?<!\d)([A-Z][a-z]{2,}(?:\s[A-Za-z][a-z]{1,}){0,3})\s*:\s+[A-Za-z][a-z]"
)

# ── Trailing participial clause (禁 -ing 分词悬垂从句) ──────────────────────
# Matches: ", <verb>ing" at end of sentence where verb is a common AI-typical
# commentary participle. Only triggers on sentence-final position.
TRAILING_ING_VERBS = (
    r"reflecting|ensuring|highlighting|demonstrating|symbolizing|underscoring"
    r"|suggesting|indicating|revealing|confirming|emphasizing|illustrating"
    r"|showing|proving|signifying|supporting|implying"
)
TRAILING_ING_RE = re.compile(
    rf",\s+(?:{TRAILING_ING_VERBS})\s+[a-z]",
    re.IGNORECASE,
)

# ── Passive voice detection (simplified) ──────────────────────────────────────
_BE_FORMS = r"(?:is|are|was|were|been|being|be)"
_PAST_PARTICIPLE = r"(?:[a-z]+ed|[a-z]+en|[a-z]+t)\b"
PASSIVE_RE = re.compile(
    rf"\b{_BE_FORMS}\s+(?:\w+\s+)?{_PAST_PARTICIPLE}",
    re.IGNORECASE,
)

# ── Sentence splitting ────────────────────────────────────────────────────────
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])")

# ── 中文支持：切句与计词 ──────────────────────────────────────────────────────
# 中文句子以「。！？」收尾且**不带空格**，上面那条英文规则一句都切不出来；再叠加
# 「按空格数词」的碎片过滤（中文不分词 → 整段只算 1 词 < 3），整段中文会被整体丢弃，
# 于是所有按句子算的检查（句长方差/连续等长/长句…）在中文稿上全部空转 → 恒满分。
# 下面两条只在文本里真有汉字时才起作用；纯英文输入的行为与旧实现逐字节一致。
CJK_CHAR_RE = re.compile(r"[一-鿿]")           # 汉字：用于计字数
# 汉字 + 中文标点 + 全角符号：剥掉之后再数剩余的英文词，避免把「，」当成一个词。
CJK_TEXT_RE = re.compile(r"[　-〿一-鿿＀-￯]")
# 在中文句末标点之后断句；连续的句末标点（？！）和紧跟的收尾引号/括号留在本句。
CJK_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？])(?![。！？…”’」』）】])")

# ponytail: 2 个汉字折 1 个英文词。选 2 是为了让「单句 >30 词」这条阈值在中文上
# 落到 >60 字，正好对上本技能自己的节奏建议（短句 ≤15 字、长句 30–60 字）。
# 启发式，真稿反馈说长句判早/判晚了就调这一个数。
CJK_CHARS_PER_WORD = 2

# ── Reference/figure/heading filters ─────────────────────────────────────────
# NOTE: there is deliberately no per-line reference format regex any more.
# Real drafts mix at least five entry styles ("1. Author…2020", "- [12] …",
# "1. [99] Author…" with or without a year, bare "[99] …"), and any whitelist
# leaks the ones it does not know — that leak was the single largest false-
# positive source (bullets / explanatory colons / author initials read as
# undefined abbreviations). Once we know we are inside a reference block we
# drop every line until the block is closed; see _extract_prose.
HEADING_RE = re.compile(r"^#+\s+", re.MULTILINE)
# Heading text (after stripping leading #/space) that marks a reference section.
REF_HEADING_RE = re.compile(r"^(?:References|参考文献|Bibliography)", re.IGNORECASE)
# A standalone reference label line that is not a markdown heading
# ("References" / "**References**" / "参考文献：" / "Bibliography").
# Anchored at both ends on purpose: a prose sentence that merely starts with
# "References were formatted per…" must NOT open the block, otherwise the
# whole rest of the file would be swallowed.
#
# ReDoS fix (2026-08-03) — do NOT turn this back into a regex. It used to be
#   ^\**\s*(?:References|参考文献|Bibliography)\s*\**\s*[:：]?\s*$
# where the adjacent optional quantifiers (\s* \** \s*) all compete for the
# same whitespace run: cubic backtracking on near-miss lines. Measured with a
# single .match() call:
#   "References" + " "*400  + "x"  →  0.067 s
#   "References" + " "*800  + "x"  →  0.512 s
#   "References" + " "*1600 + "x"  →  4.035 s   (≈×8 per doubling)
# The trigger shape is real: PDF/HTML-to-text TOC lines are exactly
# "References" + <long space run> + <page number>, and a few dozen of them
# hang the checker for minutes → users skip the check → silent failure.
# Merging segments into character classes ([\s*]*[:：]?[\s*]*$) is NOT a fix
# either: still O(n²), 29 s measured. Hence a plain left-to-right consumer —
# each greedy strip below is equivalent to the regex because no later segment
# can accept the characters an earlier segment consumes.
_REF_LABEL_KEYWORDS = ("references", "参考文献", "bibliography")


def _is_reference_label_line(stripped: str) -> bool:
    """Linear-time, semantics-preserving replacement for the retired regex."""
    s = stripped.lstrip("*")            # ^\**
    s = s.lstrip()                      # \s*
    for kw in _REF_LABEL_KEYWORDS:      # (?:References|参考文献|Bibliography), re.I
        # Compare a fixed-length slice, lowercased: indices stay in the
        # original string even for rare chars whose lower() changes length.
        if s[: len(kw)].lower() == kw:
            s = s[len(kw):]
            break
    else:
        return False
    s = s.lstrip()                      # \s*
    s = s.lstrip("*")                   # \**
    s = s.lstrip()                      # \s*
    if s[:1] in (":", "："):            # [:：]?
        s = s[1:]
    return not s.lstrip()               # \s*$
FIGURE_LEGEND_RE = re.compile(r"^(?:Figure|Fig\.?|Table)\s+\d", re.IGNORECASE | re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
CITATION_RE = re.compile(r"\[\d+(?:[,\-\s]*\d+)*\]")


def _extract_prose(text: str) -> str:
    """Strip non-prose elements from manuscript markdown."""
    text = CODE_BLOCK_RE.sub("", text)
    lines = text.splitlines()  # 跨平台：兼容 \r\n/\r 换行
    prose_lines = []
    in_ref_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Keep in_ref_block as-is: a reference section commonly has blank
            # lines between entries. The block is closed only by a non-ref
            # heading (see HEADING branch), not by an empty line.
            prose_lines.append("")
            continue
        if HEADING_RE.match(stripped):
            # A "## References"/"参考文献"/"Bibliography" heading opens the ref
            # block; any other heading closes it. Without this, the heading
            # branch swallowed "## References" first and the dedicated
            # label check below never fired.
            heading_text = HEADING_RE.sub("", stripped, count=1).strip()
            in_ref_block = bool(REF_HEADING_RE.match(heading_text))
            continue
        if _is_reference_label_line(stripped):
            in_ref_block = True
            continue
        if in_ref_block:
            # Inside a reference block every line is bibliography, whatever its
            # entry format. Only a non-reference heading (branch above) closes
            # the block. Trade-off: prose placed after a reference list without
            # its own heading is dropped, which can only hide style issues
            # (false negatives) — the old format whitelist produced dozens of
            # false positives per draft instead, which is the worse failure.
            continue
        if stripped.startswith("---"):
            continue
        if FIGURE_LEGEND_RE.match(stripped):
            continue
        prose_lines.append(line)
    return "\n".join(prose_lines)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (English punctuation + Chinese 。！？)."""
    text = CITATION_RE.sub("", text)  # remove [n] before splitting
    raw: list[str] = []
    for chunk in SENTENCE_RE.split(text):
        raw.extend(CJK_SENTENCE_SPLIT_RE.split(chunk))
    return [s.strip() for s in raw if s.strip() and _word_count(s) >= 3]


def _word_count(sentence: str) -> int:
    """词数；中文按「CJK_CHARS_PER_WORD 个汉字 = 1 词」折算。

    没有汉字时直接走旧路径（len(split())），保证纯英文文本结果一字不差。"""
    cjk = len(CJK_CHAR_RE.findall(sentence))
    if not cjk:
        return len(sentence.split())
    return len(CJK_TEXT_RE.sub(" ", sentence).split()) + cjk // CJK_CHARS_PER_WORD


def _opener_key(first_sentence: str) -> str:
    """段首指纹：英文取前 3 词，中文取前 6 字（= 3 个词当量，口径一致）。

    中文没有空格，沿用 split()[:3] 会把整段当成一个 opener，等于不查。"""
    if CJK_CHAR_RE.match(first_sentence[:1]):
        return first_sentence[: 3 * CJK_CHARS_PER_WORD]
    words = first_sentence.split()[:3]
    return " ".join(words).lower() if len(words) >= 2 else ""


def _is_cjk_dominant(text: str, total_words: int) -> bool:
    """半数以上词当量来自汉字 → 当中文稿处理（英文专属检查对它没有意义）。"""
    cjk_equiv = len(CJK_CHAR_RE.findall(text)) // CJK_CHARS_PER_WORD
    return total_words > 0 and cjk_equiv * 2 > total_words


def check_file(filepath: str, passive_max: float = 0.30) -> dict[str, Any]:
    """Run all checks on a single review draft file.

    passive_max: maximum acceptable passive-voice ratio (review default 0.30).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    prose = _extract_prose(raw_text)
    sentences = _split_sentences(prose)
    paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip() and _word_count(p) >= 10]

    total_words = sum(_word_count(s) for s in sentences)
    result: dict[str, Any] = {
        "file": os.path.basename(filepath),
        "total_sentences": len(sentences),
        "total_words": total_words,
        "issues": [],
        "hard_fail": False,  # 硬门禁命中（如破折号）：无论分数一律 fail-close
    }

    if not sentences:
        result["score"] = 100
        return result

    # ── 1. Sentence length variance (P/B check) ──────────────────────────────
    lengths = [_word_count(s) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean_len if mean_len > 0 else 0  # coefficient of variation

    result["sentence_stats"] = {
        "mean_length": round(mean_len, 1),
        "std_dev": round(std_dev, 1),
        "cv": round(cv, 3),
        "min": min(lengths),
        "max": max(lengths),
    }

    if cv < 0.25 and len(sentences) >= 5:
        result["issues"].append({
            "type": "low_sentence_variance",
            "severity": "high",
            "detail": f"CV={cv:.3f} (target: ≥0.35). Sentences too uniform — typical AI pattern.",
        })

    # ── 2. Consecutive similar-length sentences ──────────────────────────────
    consec_similar = 0
    max_consec = 0
    for i in range(1, len(lengths)):
        if abs(lengths[i] - lengths[i - 1]) < 5:
            consec_similar += 1
            max_consec = max(max_consec, consec_similar)
        else:
            consec_similar = 0

    if max_consec >= 3:
        result["issues"].append({
            "type": "consecutive_similar_length",
            "severity": "medium",
            "detail": f"{max_consec + 1} consecutive sentences with <5 word difference.",
        })

    # ── 3. Passive voice ratio ────────────────────────────────────────────────
    # Review style (DoD R5): passive <= passive_max (default 30%). Reviews favor
    # an active, synthesis-driven voice; excess passive reads stiff. No lower bound.
    passive_count = sum(1 for s in sentences if PASSIVE_RE.search(s))
    passive_ratio = passive_count / len(sentences) if sentences else 0
    result["passive_ratio"] = round(passive_ratio, 3)

    # PASSIVE_RE 认的是 be + 过去分词，中文稿上恒为 0；不对中文稿发这条提示。
    if passive_ratio > passive_max and not _is_cjk_dominant(prose, total_words):
        result["issues"].append({
            "type": "excessive_passive_voice",
            "severity": "info",  # 软提示：报告但不阻断、不扣分（见 SOFT_ISSUE_TYPES）
            "detail": f"Passive ratio {passive_ratio:.1%} (soft guide: <={passive_max:.0%}). Consider trimming passive constructions.",
        })

    # ── 3b. Long sentences (>30 words) ────────────────────────────────────────
    # 软提示：单句 >30 词只提醒不阻断（节奏建议，非硬门）。
    long_sentences = [(i, l) for i, l in enumerate(lengths) if l > 30]
    if long_sentences:
        result["issues"].append({
            "type": "long_sentence",
            "severity": "info",
            "detail": (
                f"{len(long_sentences)} sentence(s) exceed 30 words "
                f"(max={max(l for _, l in long_sentences)}). Consider splitting for rhythm."
            ),
        })

    # ── 4. Forbidden words/phrases ────────────────────────────────────────────
    forbidden_hits: list[dict[str, str]] = []
    lower_prose = prose.lower()
    for phrase in FORBIDDEN_EXACT:
        if phrase in lower_prose:
            forbidden_hits.append({"phrase": phrase, "type": "forbidden_word"})
    for phrase in FORBIDDEN_CN:  # 中文无大小写，直接在原文里找
        if phrase in prose:
            forbidden_hits.append({"phrase": phrase, "type": "forbidden_word_cn"})
    for pat in FORBIDDEN_PATTERNS:
        if pat.search(prose):
            forbidden_hits.append({"phrase": pat.pattern[:50], "type": "forbidden_pattern"})

    result["forbidden_hits"] = forbidden_hits
    if forbidden_hits:
        result["issues"].append({
            "type": "forbidden_ai_phrases",
            "severity": "high",
            "detail": f"{len(forbidden_hits)} AI-typical phrases detected: {', '.join(h['phrase'] for h in forbidden_hits[:5])}",
        })

    # ── 5. Paragraph opening repetition ───────────────────────────────────────
    openers = []
    for para in paragraphs:
        first_sentence = SENTENCE_RE.split(para)[0].strip() if para else ""
        opener = _opener_key(first_sentence)
        if opener:
            openers.append(opener)

    repeated_openers: list[str] = []
    for i in range(1, len(openers)):
        if openers[i] == openers[i - 1]:
            if openers[i] not in repeated_openers:
                repeated_openers.append(openers[i])

    if repeated_openers:
        result["issues"].append({
            "type": "repeated_paragraph_openers",
            "severity": "medium",
            "detail": f"Consecutive paragraphs start the same way: {', '.join(repeated_openers[:3])}",
        })

    # ── 6. Bullet point check (正文禁用) ─────────────────────────────────────
    # Exclude Vancouver-style reference lines (number. AuthorText YYYY) from
    # the numbered-list count — _extract_prose strips the References section
    # only when headed by a markdown heading; fallback: skip lines that look
    # like bibliography entries (contain a 4-digit year).
    bullet_lines = re.findall(r"^[\s]*[-*]\s+\w", prose, re.MULTILINE)
    _all_numbered = re.findall(r"^[\s]*\d+\.\s+.+", prose, re.MULTILINE)
    _ref_like = re.compile(r"\b(19|20)\d{2}\b")
    numbered_lines = [ln for ln in _all_numbered if not _ref_like.search(ln)]
    bullet_count = len(bullet_lines) + len(numbered_lines)
    if bullet_count > 0:
        result["issues"].append({
            "type": "bullet_points_in_prose",
            "severity": "high",
            "detail": f"{bullet_count} bullet/numbered list lines detected in prose body.",
        })

    # ── 7. Decorative em-dash (按密度判，不再一个就毙) ────────────────────────
    # em dash 在英文学术写作里是合法标点（插入语/同位补充），单个出现不是 AI 腔；
    # 判 AI 腔的是**密度**。原实现 >=1 即 hard_fail，把正常稿判成不合格，用户只能
    # 删掉合法标点来讨好检查。改为超出配额才算问题、配额内只提示。
    em_dash_count = len(EM_DASH_RE.findall(prose))
    em_dash_budget = em_dash_allowance(total_words)
    if em_dash_count > em_dash_budget:
        result["issues"].append({
            "type": "decorative_em_dash",
            "severity": "high",  # 超配额 = 密集滥用，计入 score 并置 hard_fail
            "detail": (f"{em_dash_count} em-dash(es) (—/——) in {total_words} words "
                       f"(配额 {em_dash_budget}). 破折号密集滥用是 AI 腔特征，"
                       f"删到配额内：用逗号/句号/重构替代。"),
        })
        result["hard_fail"] = True
    elif em_dash_count:
        result["issues"].append({
            "type": "decorative_em_dash",
            "severity": "info",  # 配额内：只提示，不扣分、不阻断
            "detail": (f"{em_dash_count} em-dash(es) (—/——) in {total_words} words "
                       f"(配额 {em_dash_budget}，未超)。合法用法无需处理；"
                       f"若是当停顿/强调用的装饰性破折号，建议改写。"),
        })

    # ── 8. Scare quotes (硬门禁, 禁止使用: 引号暗示新概念) ─────────────────────
    # 去AI必禁三项之一。与破折号同级：命中即 hard_fail 一票否决，不放行。
    scare_hits = SCARE_QUOTE_RE.findall(prose)
    # Filter obvious false positives: ALL CAPS acronyms, or phrases ≥5 words
    scare_hits = [h for h in scare_hits if len(h.split()) <= 4 and not h.isupper()]
    if len(scare_hits) >= 1:
        result["issues"].append({
            "type": "scare_quotes",
            "severity": "high",
            "detail": f"{len(scare_hits)} likely scare-quote phrase(s): {', '.join(repr(h) for h in scare_hits[:3])}. 禁止使用 scare quotes(硬门禁)，除非直接引用或已固化术语。",
        })
        result["hard_fail"] = True

    # ── 9. Explanatory colon in prose (硬门禁, 禁止使用: 解释性冒号) ────────────
    # 去AI必禁三项之一。与破折号同级：命中即 hard_fail 一票否决，不放行。
    expl_colon_hits = EXPLANATORY_COLON_RE.findall(prose)
    if len(expl_colon_hits) >= 1:
        result["issues"].append({
            "type": "explanatory_colon_in_prose",
            "severity": "high",
            "detail": f"{len(expl_colon_hits)} possible explanatory colon(s): {', '.join(repr(h) for h in expl_colon_hits[:3])}. 禁止使用解释性冒号(硬门禁)，改写为从句。",
        })
        result["hard_fail"] = True

    # ── 10. Trailing -ing participial clause (禁 -ing 分词悬垂从句) ──────────
    # Sentence-final ", reflecting/demonstrating/suggesting/..." is a hallmark
    # AI pattern. We scan each sentence for the pattern.
    trailing_ing_hits: list[str] = []
    for sent in sentences:
        m = TRAILING_ING_RE.search(sent)
        if m:
            trailing_ing_hits.append(sent[:80])
    if trailing_ing_hits:
        result["issues"].append({
            "type": "trailing_ing_clause",
            "severity": "medium",
            "detail": (
                f"{len(trailing_ing_hits)} trailing participial clause(s) detected "
                f"(e.g. ', reflecting/demonstrating/suggesting …'). "
                f"Rewrite as a new sentence. First hit: {repr(trailing_ing_hits[0])}"
            ),
        })

    # ── Score calculation ─────────────────────────────────────────────────────
    # severity == "info" 为软提示（长句 / 被动比例等），只报告不扣分、不影响 gate 通过。
    # 破折号是硬门禁（severity=high 计分 + hard_fail 一票否决）。high/medium/low 仍计分。
    score = 100
    for issue in result["issues"]:
        sev = issue["severity"]
        if sev == "info":
            continue
        if sev == "high":
            score -= 15
        elif sev == "medium":
            score -= 8
        else:
            score -= 3
    result["score"] = max(0, score)

    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Anti-AI style checker for review drafts")
    p.add_argument("--manuscript-dir", "--drafts-dir", dest="manuscript_dir",
                   default="drafts", help="Directory with review draft .md files")
    p.add_argument("--file", default="", help="Check a single file instead of directory")
    p.add_argument("--report", default="data/style_check_report.json", help="Output report path")
    p.add_argument("--threshold", type=int, default=70, help="Minimum passing score")
    p.add_argument("--passive-max", type=float, default=0.30,
                   help="Max acceptable passive-voice ratio (review default 0.30)")
    args = p.parse_args()

    files: list[str] = []
    if args.file:
        files = [args.file]
    elif os.path.isdir(args.manuscript_dir):
        files = sorted(glob.glob(os.path.join(args.manuscript_dir, "*.md")))
        # Skip merge-generated derivatives (carry the AUTO-GENERATED banner;
        # double-scanning them and the banner em-dash cause false positives).
        files = [f for f in files if not is_merged_derivative(f)]

    if not files:
        print(json.dumps({"ok": True, "message": "No manuscript files found", "files": []}))
        return 0

    results = [check_file(f, passive_max=args.passive_max) for f in files]
    scores = [r["score"] for r in results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 100
    any_hard_fail = any(r.get("hard_fail") for r in results)  # 破折号等硬门禁：一票否决
    all_pass = all(s >= args.threshold for s in scores) and not any_hard_fail
    total_issues = sum(len(r["issues"]) for r in results)

    report = {
        "ok": all_pass,
        "avg_score": avg_score,
        "threshold": args.threshold,
        "files_checked": len(results),
        "total_issues": total_issues,
        "files": results,
    }

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": all_pass, "avg_score": avg_score, "total_issues": total_issues, "files_checked": len(results)}))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Anti-AI style checker for scientific manuscripts.

Measures:
- Sentence length variance (Perplexity/Burstiness)
- Passive voice ratio
- Forbidden word/phrase hits
- Paragraph opening repetition
- Consecutive similar-length sentences

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
    # PhD-level 平实化：以下"编辑级炫技动词/形容词"对 PhD candidate 而言过于雕琢
    "elucidate", "unveil", "illuminate", "underpin", "epitomize",
    "precipitate", "engender", "pronounced", "substantial",
    "paramount", "salient", "germane",
}

# 启发式生僻词检测：词长 ≥13 且非已知领域术语 / 缩写 / 专名 → 疑似生僻或造词
# (PhD 常用词大多 ≤12 字符；专业术语虽长但通常用首字母大写或带 - / _)
RARE_WORD_RE = re.compile(r"\b[a-z]{13,}\b")
# 已知合法长词白名单(领域术语、词缀派生)——按需扩展
RARE_WHITELIST = {
    "pharmacokinetics", "pharmacodynamics", "biocompatibility",
    "nanotechnology", "immunohistochemistry", "biodistribution",
    "internalization", "characterization", "functionalization",
    "encapsulation", "transfection", "fluorescence", "concentration",
    "investigation", "experimental", "statistical", "significantly",
    "demonstrated", "representative", "corresponding", "respectively",
    "approximately", "subsequently", "consistently", "additionally",
    "specifically", "particularly", "comparatively", "ultrastructural",
    "transcriptomic", "proteomics", "metabolomics", "immunogenicity",
    "pharmacokinetic", "pharmacodynamic", "characterized",
    "characterize", "investigated", "investigation", "investigations",
    "evaluated", "performed", "manuscripts", "observations",
}

# 编造词启发式：含罕见词缀组合 (如 -omics 之外的造词 / -ability 滥用 / 两个根拼接)
NEOLOGISM_PATTERNS = [
    re.compile(r"\b\w+omics\b", re.IGNORECASE),  # 排除已知后会再过滤
    re.compile(r"\b\w{6,}ability\b", re.IGNORECASE),  # 长根+ability,如 diseasability
]
NEOLOGISM_WHITELIST = {
    "genomics", "proteomics", "metabolomics", "transcriptomics",
    "epigenomics", "lipidomics", "microbiomics", "phenomics",
    "ability", "capability", "availability", "stability",
    "permeability", "scalability", "applicability", "reliability",
    "reproducibility", "feasibility", "biocompatibility",
    "compatibility", "susceptibility", "accessibility",
}

# 修辞检测：明喻 (like a... / as ... as) / 拟人 (cells decide / molecules know)
RHETORIC_PATTERNS = [
    re.compile(r"\b(?:like|as if|as though)\s+a?\s+\w+", re.IGNORECASE),  # 明喻
    re.compile(r"\b(?:cells?|molecules?|proteins?|genes?)\s+(?:decide|know|want|believe|think|wish|hope|feel)\b", re.IGNORECASE),  # 拟人
    re.compile(r"\b(?:dance|symphony|orchestra|theater|battle|war)\s+of\b", re.IGNORECASE),  # 装饰隐喻
]
FORBIDDEN_PATTERNS = [
    re.compile(r"not only\b.*?\bbut also\b", re.IGNORECASE),
    re.compile(r"seamless[,\s]+intuitive[,\s]+and\s+powerful", re.IGNORECASE),
    re.compile(r"from\s+\w+\s+to\s+\w+", re.IGNORECASE),  # "from X to Y" pattern
]

# ── Passive voice detection (simplified) ──────────────────────────────────────
_BE_FORMS = r"(?:is|are|was|were|been|being|be)"
_PAST_PARTICIPLE = r"(?:[a-z]+ed|[a-z]+en|[a-z]+t)\b"
PASSIVE_RE = re.compile(
    rf"\b{_BE_FORMS}\s+(?:\w+\s+)?{_PAST_PARTICIPLE}",
    re.IGNORECASE,
)

# ── Sentence splitting ────────────────────────────────────────────────────────
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])")

# ── Reference/figure/heading filters ─────────────────────────────────────────
REF_LINE_RE = re.compile(r"^\d+\.\s+\w+.*?\d{4}", re.MULTILINE)
HEADING_RE = re.compile(r"^#+\s+", re.MULTILINE)
FIGURE_LEGEND_RE = re.compile(r"^(?:Figure|Fig\.?|Table)\s+\d", re.IGNORECASE | re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
CITATION_RE = re.compile(r"\[\d+(?:[,\-\s]*\d+)*\]")


def _extract_prose(text: str) -> str:
    """Strip non-prose elements from manuscript markdown."""
    text = CODE_BLOCK_RE.sub("", text)
    lines = text.split("\n")
    prose_lines = []
    in_ref_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            in_ref_block = False
            prose_lines.append("")
            continue
        if HEADING_RE.match(stripped):
            in_ref_block = False
            continue
        if stripped.startswith("---"):
            continue
        if FIGURE_LEGEND_RE.match(stripped):
            continue
        if re.match(r"^(References|参考文献)", stripped, re.IGNORECASE):
            in_ref_block = True
            continue
        if in_ref_block and REF_LINE_RE.match(stripped):
            continue
        if in_ref_block and not stripped:
            in_ref_block = False
            continue
        prose_lines.append(line)
    return "\n".join(prose_lines)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    text = CITATION_RE.sub("", text)  # remove [n] before splitting
    raw = SENTENCE_RE.split(text)
    return [s.strip() for s in raw if s.strip() and len(s.split()) >= 3]


def _word_count(sentence: str) -> int:
    return len(sentence.split())


def check_file(filepath: str) -> dict[str, Any]:
    """Run all checks on a single manuscript file."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    prose = _extract_prose(raw_text)
    sentences = _split_sentences(prose)
    paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip() and len(p.split()) >= 10]

    total_words = sum(_word_count(s) for s in sentences)
    result: dict[str, Any] = {
        "file": os.path.basename(filepath),
        "total_sentences": len(sentences),
        "total_words": total_words,
        "issues": [],
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
    passive_count = sum(1 for s in sentences if PASSIVE_RE.search(s))
    passive_ratio = passive_count / len(sentences) if sentences else 0
    result["passive_ratio"] = round(passive_ratio, 3)

    # 被动占比目标 50-70%(SCI Article 实验描述主流被动为主);<40% 过口语化, >70% 过冗余
    if passive_ratio < 0.40:
        result["issues"].append({
            "type": "insufficient_passive_voice",
            "severity": "medium",
            "detail": f"Passive ratio {passive_ratio:.1%} (target: 50-70% for SCI Article). Too active/informal — use more passive in Methods/Results.",
        })
    elif passive_ratio > 0.70:
        result["issues"].append({
            "type": "excessive_passive_voice",
            "severity": "low",
            "detail": f"Passive ratio {passive_ratio:.1%} (target: 50-70%). Slightly heavy on passive; allow active for author judgments in Discussion.",
        })

    # ── 3b. 长难句检测(单句 >30 词即扣) ──────────────────────────────────────
    long_sentences = [(i, ln) for i, ln in enumerate(lengths) if ln > 30]
    if long_sentences:
        result["issues"].append({
            "type": "long_complex_sentence",
            "severity": "high",
            "detail": f"{len(long_sentences)} sentence(s) >30 words (e.g., {long_sentences[0][1]}w). Split into shorter ones.",
        })

    # ── 3c. 修辞/拟人/明喻检测 ────────────────────────────────────────────────
    rhetoric_hits = []
    for pat in RHETORIC_PATTERNS:
        for m in pat.finditer(prose):
            rhetoric_hits.append(m.group(0)[:60])
    if rhetoric_hits:
        result["issues"].append({
            "type": "rhetorical_devices",
            "severity": "medium",
            "detail": f"{len(rhetoric_hits)} rhetorical/personification hit(s): {', '.join(rhetoric_hits[:3])}",
        })

    # ── 3d. 生僻词检测(≥13 字符且不在白名单) ──────────────────────────────────
    rare_hits = sorted({
        m.group(0) for m in RARE_WORD_RE.finditer(prose.lower())
        if m.group(0) not in RARE_WHITELIST
    })
    if rare_hits:
        result["issues"].append({
            "type": "obscure_vocabulary",
            "severity": "medium",
            "detail": f"{len(rare_hits)} possibly obscure/long word(s): {', '.join(rare_hits[:5])}",
        })

    # ── 3e. 编造词检测 ─────────────────────────────────────────────────────────
    neologism_hits = []
    for pat in NEOLOGISM_PATTERNS:
        for m in pat.finditer(prose.lower()):
            w = m.group(0).lower()
            if w not in NEOLOGISM_WHITELIST:
                neologism_hits.append(w)
    if neologism_hits:
        result["issues"].append({
            "type": "neologism_suspected",
            "severity": "high",
            "detail": f"{len(neologism_hits)} suspected fabricated word(s): {', '.join(set(neologism_hits))[:80]}",
        })

    # ── 4. Forbidden words/phrases ────────────────────────────────────────────
    forbidden_hits: list[dict[str, str]] = []
    lower_prose = prose.lower()
    for phrase in FORBIDDEN_EXACT:
        if phrase in lower_prose:
            forbidden_hits.append({"phrase": phrase, "type": "forbidden_word"})
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
        # Extract first 3 words as structural pattern
        words = first_sentence.split()[:3]
        if len(words) >= 2:
            openers.append(" ".join(words).lower())

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
    bullet_lines = re.findall(r"^[\s]*[-*]\s+\w", prose, re.MULTILINE)
    numbered_lines = re.findall(r"^[\s]*\d+\.\s+\w", prose, re.MULTILINE)
    bullet_count = len(bullet_lines) + len(numbered_lines)
    if bullet_count > 0:
        result["issues"].append({
            "type": "bullet_points_in_prose",
            "severity": "high",
            "detail": f"{bullet_count} bullet/numbered list lines detected in prose body.",
        })

    # ── Score calculation ─────────────────────────────────────────────────────
    score = 100
    for issue in result["issues"]:
        if issue["severity"] == "high":
            score -= 15
        elif issue["severity"] == "medium":
            score -= 8
        else:
            score -= 3
    result["score"] = max(0, score)

    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Anti-AI style checker for manuscripts")
    p.add_argument("--manuscript-dir", default="manuscripts", help="Directory with .md files")
    p.add_argument("--file", default="", help="Check a single file instead of directory")
    p.add_argument("--report", default="style_check_report.json", help="Output report path")
    p.add_argument("--threshold", type=int, default=70, help="Minimum passing score")
    args = p.parse_args()

    files: list[str] = []
    if args.file:
        files = [args.file]
    elif os.path.isdir(args.manuscript_dir):
        files = sorted(glob.glob(os.path.join(args.manuscript_dir, "*.md")))

    if not files:
        print(json.dumps({"ok": True, "message": "No manuscript files found", "files": []}))
        return 0

    results = [check_file(f) for f in files]
    scores = [r["score"] for r in results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 100
    all_pass = all(s >= args.threshold for s in scores)
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

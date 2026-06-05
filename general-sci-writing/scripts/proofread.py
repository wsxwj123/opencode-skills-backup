"""Proofread checker for SCI manuscript markdown files.

Catches the 80% of mechanical errors that survive Anti-AI style checks:
  1. Common misspellings (teh, occured, etc.)
  2. Chinese punctuation leaked into English text (，；：（）「」 etc.)
  3. Unit format issues (um → μm, degC → °C, x g → ×g)
  4. Inconsistent term spellings (nano-particles vs nanoparticles)
  5. Tense mixing hints (Methods should be past tense; etc.)
  6. Number format (10000 vs 10,000)

Usage:
    python scripts/proofread.py --manuscript-dir manuscripts --report proofread_report.json
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Common misspellings (a → b) ──────────────────────────────────────────────
MISSPELLINGS = {
    "teh": "the", "adn": "and", "nad": "and", "recieve": "receive",
    "occured": "occurred", "occuring": "occurring", "seperate": "separate",
    "definately": "definitely", "alot": "a lot", "untill": "until",
    "wich": "which", "thier": "their", "wierd": "weird",
    "occurence": "occurrence", "accomodate": "accommodate",
    "neccessary": "necessary", "neccesary": "necessary",
    "succesful": "successful", "succesfully": "successfully",
    "tommorow": "tomorrow", "infered": "inferred",
    "behaviuor": "behavior", "colour": "color (or 'colour' if BrE consistent)",
    "analyse": "analyze (or 'analyse' if BrE consistent)",
    "modelling": "modeling (or 'modelling' if BrE consistent)",
    "labelled": "labeled (or 'labelled' if BrE consistent)",
    "centre": "center (or 'centre' if BrE consistent)",
    "experiement": "experiment", "experiments": None,
    "phenotpye": "phenotype", "phenotype": None,
    "morpholgy": "morphology", "morphology": None,
    "stastistical": "statistical", "stastistics": "statistics",
    "stastically": "statistically", "siginificant": "significant",
    "siginificantly": "significantly",
    "compromized": "compromised", "compoared": "compared",
    "compairson": "comparison", "comparsion": "comparison",
    "expermental": "experimental",
    "evidenc": "evidence", "preformed": "performed (or 'preformed' if 'pre-formed')",
    "becuase": "because", "becasue": "because",
}
# 移除 None 值(占位)
MISSPELLINGS = {k: v for k, v in MISSPELLINGS.items() if v is not None}

# ── Chinese punctuation that leaked into English text ────────────────────────
CHINESE_PUNCT = {
    "，": ",", "；": ";", "：": ":", "（": "(", "）": ")",
    "！": "!", "？": "?", "“": "\"", "”": "\"",
    "‘": "'", "’": "'", "《": "<", "》": ">",
    "【": "[", "】": "]", "「": "\"", "」": "\"",
    "—": "—",  # em dash is fine but worth flagging mixed use
    "…": "...",
    "。": ".",
}

# ── Unit format issues ───────────────────────────────────────────────────────
UNIT_PATTERNS = [
    # (问题模式, 应改为, 描述)
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*um\b"), r"\1 μm", "ASCII 'um' should be 'μm'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*degC\b", re.IGNORECASE), r"\1 °C", "'degC' should be '°C'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*deg\s*C\b", re.IGNORECASE), r"\1 °C", "'deg C' should be '°C'"),
    (re.compile(r"(\d+(?:\.\d+)?)\s*[xX]\s*g\b"), r"\1 ×g", "centrifugation force: use '×g' not 'x g'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*ug\b"), r"\1 μg", "ASCII 'ug' should be 'μg'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*ul\b"), r"\1 μL", "ASCII 'ul' should be 'μL'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*uM\b"), r"\1 μM", "ASCII 'uM' should be 'μM'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*uA\b"), r"\1 μA", "ASCII 'uA' should be 'μA'"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*degree(s)?\b"), r"\1°", "'degrees' (when temperature) usually written as '°'"),
]

# ── Number format consistency (10000 vs 10,000) ──────────────────────────────
# 期刊偏好:Nature 用 comma 分隔 ≥1000;Cell 同;BMJ 系列同.
# 检测:同文档内出现大于 4 位数字、有的带逗号、有的不带 = 不一致
NUMBER_RE = re.compile(r"(?<![\d.,])\d{4,}(?![\d.,])")
NUMBER_WITH_COMMA_RE = re.compile(r"\d{1,3}(,\d{3})+")

# ── Term consistency tracking ────────────────────────────────────────────────
# 检测同概念多种写法:nano-particle/nanoparticle/NP/NPs 等
TERM_VARIANTS = [
    [r"nano.?particle", r"NPs?\b"],
    [r"in.?vitro", r"in vitro"],
    [r"in.?vivo", r"in vivo"],
    [r"co.?culture", r"coculture"],
    [r"cell.?line", r"cellline"],
    [r"flow.?cytometry"],
    [r"western.?blot"],
]

# ── Tense hints for Methods (should be past tense) ───────────────────────────
# 简单启发式:Methods 段内出现现在时第三人称单数 + 动作动词
PRESENT_TENSE_VERBS_RE = re.compile(
    r"\b(uses|performs|measures|treats|incubates|conducts|analyzes|tests|"
    r"applies|adds|washes|stains|isolates|extracts|determines|calculates)\b",
    re.IGNORECASE,
)

# ── Ref/heading/code skip filters ─────────────────────────────────────────────
HEADING_RE = re.compile(r"^#+\s+", re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
REF_LINE_RE = re.compile(r"^\d+\.\s+\w+", re.MULTILINE)
CITATION_RE = re.compile(r"\[\d+(?:[,\-\s]*\d+)*\]")


def _extract_prose(text):
    """Strip non-prose: code blocks, citations (for word matching)."""
    text = CODE_BLOCK_RE.sub("", text)
    return text


def check_misspellings(text):
    issues = []
    lower = text.lower()
    for wrong, right in MISSPELLINGS.items():
        pattern = re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            issues.append({
                "type": "misspelling",
                "severity": "high",
                "found": m.group(0),
                "suggest": right,
                "pos": m.start(),
            })
    return issues


def check_chinese_punct(text):
    issues = []
    for ch, en in CHINESE_PUNCT.items():
        for m in re.finditer(re.escape(ch), text):
            # 跳过明确合理出现的中文上下文(如中文文献标题在 caption 里) — 简单启发:这行有 ≥3 个中文汉字则跳过
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            line_end = line_end if line_end != -1 else len(text)
            line = text[line_start:line_end]
            cn_chars = len(re.findall(r"[一-鿿]", line))
            if cn_chars >= 3:
                continue
            issues.append({
                "type": "chinese_punct",
                "severity": "high",
                "found": ch,
                "suggest": en,
                "pos": m.start(),
            })
    return issues


def check_units(text):
    issues = []
    for pat, replacement, desc in UNIT_PATTERNS:
        for m in pat.finditer(text):
            issues.append({
                "type": "unit_format",
                "severity": "medium",
                "found": m.group(0),
                "suggest": desc,
                "pos": m.start(),
            })
    return issues


def check_number_consistency(text):
    """Within a single file: if any number ≥1000 has comma AND any doesn't → inconsistent."""
    nums_no_comma = NUMBER_RE.findall(text)
    nums_with_comma = NUMBER_WITH_COMMA_RE.findall(text)
    issues = []
    # 阈值:≥4 位数字
    big_nums = [n for n in nums_no_comma if len(n) >= 4]
    if big_nums and nums_with_comma:
        issues.append({
            "type": "number_format_inconsistent",
            "severity": "low",
            "detail": f"{len(big_nums)} numbers without comma + {len(nums_with_comma)} with comma — pick one style (Nature/Cell prefer comma separators for ≥1000)",
        })
    return issues


def check_term_consistency(text):
    issues = []
    for variants in TERM_VARIANTS:
        hits = []
        for v in variants:
            pat = re.compile(rf"\b{v}\b", re.IGNORECASE)
            matches = pat.findall(text)
            if matches:
                hits.append((v, len(matches)))
        if len(hits) >= 2:
            issues.append({
                "type": "term_variant",
                "severity": "low",
                "detail": f"multiple spellings used: " + ", ".join(f"'{v}' ({n}x)" for v, n in hits),
            })
    return issues


def check_methods_tense(text, filename):
    """Methods sections should be past tense. Heuristic: present-tense action verbs."""
    if not re.search(r"(?i)\bmethods?\b|^0?5[_-]?Methods", filename):
        return []
    issues = []
    for m in PRESENT_TENSE_VERBS_RE.finditer(text):
        issues.append({
            "type": "methods_tense",
            "severity": "low",
            "found": m.group(0),
            "suggest": "Methods is past tense — consider switching to '-ed' form",
            "pos": m.start(),
        })
    return issues[:5]  # 限制条数避免刷屏


def check_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        return {"file": filepath, "error": str(e), "issues": []}
    text = _extract_prose(raw)
    fn = os.path.basename(filepath)
    all_issues = []
    all_issues.extend(check_misspellings(text))
    all_issues.extend(check_chinese_punct(text))
    all_issues.extend(check_units(text))
    all_issues.extend(check_number_consistency(text))
    all_issues.extend(check_term_consistency(text))
    all_issues.extend(check_methods_tense(text, fn))
    # 计分:high 扣 5/medium 扣 2/low 扣 1,起点 100
    score = 100
    severity_weight = {"high": 5, "medium": 2, "low": 1}
    for i in all_issues:
        score -= severity_weight.get(i.get("severity", "low"), 1)
    score = max(0, score)
    return {
        "file": filepath,
        "score": score,
        "issues_total": len(all_issues),
        "issues_by_type": dict(_count_by_type(all_issues)),
        "issues": all_issues[:30],  # 截断细节避免报告过大
    }


def _count_by_type(issues):
    c = defaultdict(int)
    for i in issues:
        c[i.get("type", "unknown")] += 1
    return c


def main():
    p = argparse.ArgumentParser(description="Proofread SCI manuscript markdown")
    p.add_argument("--manuscript-dir", default="manuscripts")
    p.add_argument("--report", default="proofread_report.json")
    p.add_argument("--threshold", type=int, default=70)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    md_dir = Path(args.manuscript_dir)
    if not md_dir.exists():
        print(json.dumps({"ok": False, "error": f"dir not found: {md_dir}"}, ensure_ascii=False))
        sys.exit(1)
    files = sorted(md_dir.glob("*.md"))
    if not files:
        print(json.dumps({"ok": True, "status": "no_files", "manuscript_dir": str(md_dir)}, ensure_ascii=False))
        return 0

    results = [check_file(str(f)) for f in files]
    avg = round(sum(r["score"] for r in results) / len(results), 1)
    total_issues = sum(r["issues_total"] for r in results)
    all_pass = all(r["score"] >= args.threshold for r in results)
    summary = {
        "ok": all_pass,
        "avg_score": avg,
        "total_issues": total_issues,
        "files_checked": len(results),
        "threshold": args.threshold,
        "files": results,
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    # 简短控制台输出
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, ensure_ascii=False))
    if args.verbose:
        for r in results:
            if r["issues_total"]:
                print(f"  [{r['file']}] score={r['score']} types={r['issues_by_type']}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

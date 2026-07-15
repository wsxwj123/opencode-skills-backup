#!/usr/bin/env python3
"""style_checker.py 回归测试 — 自包含、纯 assert、无框架、standalone 可跑。

覆盖从未被测的去 AI 风格质检逻辑（基准=当前代码真实行为）。重点锁**硬门禁一票
否决**（破折号/scare quotes/解释性冒号 → hard_fail=True，无论分数一律不放行）与
其反例（干净稿不误报）。
  is_merged_derivative   合并派生物识别（避免扫 banner 假阳性）
  _passive_target        Nature/Science/Cell 无被动地板 vs 传统 0.4–0.7
  _extract_prose         剥离 code block / 标题 / 图注
  _split_sentences       去 [n] 引用 + 过滤 <3 词碎句
  check_file             干净→100 分/无 hard_fail；破折号/scare quote→hard_fail；
                          禁用 AI 词组→issue

Run: python3 test_style_checker.py   (rc=0 = 全过)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style_checker as SC


def _check(text, journal=""):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        return SC.check_file(path, journal)
    finally:
        os.remove(path)


def test_is_merged_derivative():
    assert SC.is_merged_derivative("Full_Manuscript.md") is True
    assert SC.is_merged_derivative("full_manuscript.md") is True, "大小写不敏感"
    assert SC.is_merged_derivative("Draft_Round2_Manuscript.md") is True
    # 普通原子节文件不是派生物
    assert SC.is_merged_derivative("04_Results.md") is False
    assert SC.is_merged_derivative("manuscripts/02_intro.md") is False


def test_passive_target():
    # active-voice 期刊：无下限，上限 0.70
    _, low, high = SC._passive_target("Nature Communications")
    assert low is None and high == 0.70, (low, high)
    # 传统期刊：50–70% 区间（下限 0.40）
    _, low2, high2 = SC._passive_target("Journal of Applied Physics")
    assert low2 == 0.40 and high2 == 0.70, (low2, high2)


def test_extract_prose_strips_noise():
    text = "# Heading\nbody one two.\n```\ncode block line\n```\nFigure 1. legend here.\n"
    prose = SC._extract_prose(text)
    assert "body one two." in prose, "正文应保留"
    assert "code block line" not in prose, "code block 应剥离"
    assert "Heading" not in prose, "标题应剥离"
    assert "legend here" not in prose, "图注应剥离"


def test_split_sentences():
    sents = SC._split_sentences("First real sentence here [1]. Second full sentence also. no")
    # [1] 被移除
    assert all("[1]" not in s for s in sents), "引用标记应移除"
    # 每句 >=3 词
    assert all(len(s.split()) >= 3 for s in sents), sents
    assert any("First real sentence" in s for s in sents)


def test_check_file_clean_passes():
    clean = ("We measured the sample. Then we analyzed the data carefully. "
             "Results were positive overall.")
    r = _check(clean)
    assert r["hard_fail"] is False, f"干净稿不应 hard_fail: {r['issues']}"
    assert r["score"] == 100, f"干净稿应满分: {r}"


def test_check_file_em_dash_hard_fail():
    # 破折号硬门禁：命中即 hard_fail，无论分数
    text = "We measured the sample here today — and then we analyzed the data fully now."
    r = _check(text)
    assert r["hard_fail"] is True, "破折号必须 hard_fail"
    assert any(i["type"] == "decorative_em_dash" for i in r["issues"]), r["issues"]


def test_check_file_scare_quotes_hard_fail():
    text = ('We observed a "synergistic" effect here today. '
            "It was measured twice very clearly.")
    r = _check(text)
    assert r["hard_fail"] is True, "scare quotes 必须 hard_fail"
    assert any(i["type"] == "scare_quotes" for i in r["issues"]), r["issues"]


def test_check_file_forbidden_phrase_flagged():
    text = ("We delve into the results here today. "
            "The sample was measured twice very clearly now.")
    r = _check(text)
    assert any(i["type"] == "forbidden_ai_phrases" for i in r["issues"]), r["issues"]
    assert any(h["phrase"] == "delve into" for h in r["forbidden_hits"]), r["forbidden_hits"]
    # 禁用词组是 high 严重度 → 扣分（<100）
    assert r["score"] < 100, r


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

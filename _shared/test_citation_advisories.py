#!/usr/bin/env python3
"""advisories 通道自检：两个纯函数的红线（零网络、零文件、可直接跑）。

红线只有三条，红了说明诊断会开始骗人：
  1. 撤稿通告（sim 0.764，现役判"同一篇"直接放行）必须被抓到；
  2. 正常引用零 advisory（假阳会让正确文献在自动丢弃路径上被静默丢掉）；
  3. 不可达优先于无命中；线上没有同类型标识符时不得判 "你打错了"。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from citation_guard_core import (  # noqa: E402
    classify_identifier_suggestion,
    detect_title_variant,
)

T = "Exosomal miR-21 promotes lung metastasis"


def test_title_variant() -> None:
    # 三桶各自命中，桶序即优先级。
    assert detect_title_variant(T, "Retraction notice to: " + T, "crossref")["code"] \
        == "retraction_notice_suspect"
    assert detect_title_variant(T, "Erratum to: " + T, "crossref")["code"] \
        == "erratum_notice_suspect"
    assert detect_title_variant("... management of sepsis, part 1",
                                "... management of sepsis, part 2", "crossref")["code"] \
        == "series_variant_suspect"
    assert detect_title_variant(T, "Retraction correction: " + T, "crossref")["code"] \
        == "retraction_notice_suspect"

    # 假阳红线：完全相同 / 仅标点差 / 两侧都是撤稿通告 / 差异词无标记词 / 已 blocking。
    for a, b in (
        (T, T),
        ("TGF-beta signaling in hepatic fibrosis", "TGF beta signaling in hepatic fibrosis"),
        ("Retraction notice to: " + T, "Retraction notice to: " + T),
        ("Cardiac risk in postmenopausal women", "Cardiac risk in premenopausal women"),
        ("Part I. Fundamentals of adaptive optics", "Part II. Applications of adaptive optics"),
        (T, "Dietary patterns and soil microbial diversity in alpine grassland"),
        ("", T),
    ):
        assert detect_title_variant(a, b, "crossref") is None, (a, b)

    adv = detect_title_variant(T, "Retraction notice to: " + T, "pubmed")
    assert set(adv) == {"code", "detail", "matched_title", "similarity", "source", "diff_tokens"}
    assert adv["source"] == "pubmed" and adv["diff_tokens"] == sorted(adv["diff_tokens"])
    assert "severity" not in adv and "level" not in adv  # 两档就够,不引入第三档


def test_classify_identifier() -> None:
    # 不可达优先于一切（限流不得退化成"标题可能是编的"）。
    assert classify_identifier_suggestion("10.1/a", "", None, False)["code"] \
        == "identifier_lookup_unavailable"
    assert classify_identifier_suggestion("10.1/a", "", {"doi": "10.1/b"}, False)["code"] \
        == "identifier_lookup_unavailable"
    assert classify_identifier_suggestion("10.1/a", "", None, True)["code"] \
        == "identifier_not_found"
    # DOI 大小写/空白不敏感；DOI 优先于 PMID。
    assert classify_identifier_suggestion(" 10.1/A ", "", {"doi": "10.1/a"}, True)["code"] \
        == "identifier_confirmed"
    assert classify_identifier_suggestion("10.1/a", "111",
                                          {"doi": "10.1/b", "pmid": "111"}, True)["code"] \
        == "identifier_differs"
    # PMID-only 撞 Crossref（pmid 恒 None）：只能是 type_mismatch,且不得给建议值。
    tm = classify_identifier_suggestion("", "123", {"doi": "10.1/x", "pmid": None}, True)
    assert tm["code"] == "identifier_type_mismatch"
    assert "suggested_doi" not in tm and "suggested_pmid" not in tm
    assert "None" not in tm["detail"]
    assert classify_identifier_suggestion("", "", {"doi": None, "pmid": None}, True)["code"] \
        == "identifier_type_mismatch"
    # differs 必须带 journal/year（标题几乎一样时,人工只能靠这两项分辨）。
    d = classify_identifier_suggestion("", "456", {"doi": None, "pmid": "789"}, True)
    assert d["suggested_pmid"] == "789" and "journal" in d and "year" in d


if __name__ == "__main__":
    test_title_variant()
    test_classify_identifier()
    print("PASS test_citation_advisories (2 checks)")

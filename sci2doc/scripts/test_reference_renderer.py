#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reference_renderer.py 回归测试（开发者维护工具，非运行时流程）。

覆盖 GB/T 7714 各类型渲染：render_journal/book/dissertation/conference/online/patent
断言类型标识 [J]/[M]/[D]/[C]/[EB/OL]/[P]、作者 >3 加“等”、卷期页拼装。

纯 assert，无框架依赖。用法：python3 test_reference_renderer.py
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from reference_renderer import (  # noqa: E402
    render_journal, render_book, render_dissertation,
    render_conference, render_online, render_patent, _fmt_authors,
)


def test_journal_type_and_volume_issue_pages():
    out = render_journal({
        "authors": ["Zhang S", "Li W"],
        "title": "A journal paper",
        "journal": "Nature",
        "year": "2021",
        "volume": "590",
        "issue": "7844",
        "pages": "123-130",
        "doi": "10.1038/x",
    })
    assert "[J]" in out
    assert "Nature" in out
    assert "590(7844)" in out, out       # 卷(期)
    assert "123-130" in out              # 页码
    assert "DOI: 10.1038/x" in out


def test_book_type_M():
    out = render_book({
        "authors": ["王五"],
        "title": "专著名",
        "publisher": "科学出版社",
        "pub_place": "北京",
        "year": "2019",
        "pages": "10-20",
    })
    assert "[M]" in out
    assert "北京: 科学出版社" in out
    assert out.endswith(".")


def test_dissertation_type_D():
    out = render_dissertation({
        "authors": ["赵六"],
        "title": "学位论文名",
        "pub_place": "上海",
        "institution": "复旦大学",
        "year": "2020",
    })
    assert "[D]" in out
    assert "复旦大学" in out
    assert "2020" in out


def test_conference_type_C():
    out = render_conference({
        "authors": ["Chen A"],
        "title": "A conference paper",
        "booktitle": "Proc of XYZ",
        "pub_place": "Beijing",
        "publisher": "IEEE",
        "year": "2018",
        "pages": "1-5",
    })
    assert "[C]" in out
    assert "Proc of XYZ" in out
    assert "1-5" in out


def test_online_type_ebol():
    out = render_online({
        "authors": ["某机构"],
        "title": "网络文献",
        "year": "2022",
        "access_date": "2023-01-01",
        "url": "https://example.org/x",
    })
    assert "[EB/OL]" in out
    assert "[2023-01-01]" in out
    assert "https://example.org/x" in out


def test_patent_type_P():
    out = render_patent({
        "authors": ["某公司"],
        "title": "一种装置",
        "patent_number": "CN123456A",
        "pub_date": "2021-05-01",
    })
    assert "[P]" in out
    assert "CN123456A" in out
    assert "2021-05-01" in out


def test_authors_more_than_three_chinese_deng():
    out = _fmt_authors(["张三", "李四", "王五", "赵六"])
    assert out.endswith("等"), out
    assert "张三" in out and "李四" in out and "王五" in out
    assert "赵六" not in out  # 第 4 位起省略


def test_authors_more_than_three_english_etal():
    out = _fmt_authors(["Zhang S", "Li W", "Wang H", "Zhao L"])
    assert "et al" in out
    assert "Zhao L" not in out


def test_authors_three_or_fewer_all_listed():
    out = _fmt_authors(["张三", "李四", "王五"])
    assert "等" not in out
    assert out == "张三, 李四, 王五"


def test_authors_empty_anonymous():
    assert _fmt_authors([]) == "佚名"


if __name__ == "__main__":
    test_journal_type_and_volume_issue_pages()
    print("OK render_journal [J] 卷期页 DOI")
    test_book_type_M()
    print("OK render_book [M]")
    test_dissertation_type_D()
    print("OK render_dissertation [D]")
    test_conference_type_C()
    print("OK render_conference [C]")
    test_online_type_ebol()
    print("OK render_online [EB/OL]")
    test_patent_type_P()
    print("OK render_patent [P]")
    test_authors_more_than_three_chinese_deng()
    print("OK 作者>3 中文加“等”")
    test_authors_more_than_three_english_etal()
    print("OK 作者>3 外文加 et al")
    test_authors_three_or_fewer_all_listed()
    print("OK 作者<=3 全列")
    test_authors_empty_anonymous()
    print("OK 空作者→佚名")
    print("ALL OK")

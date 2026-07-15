#!/usr/bin/env python3
"""merge_manuscript.py 回归测试 — 自包含、纯 assert、无框架、standalone 可跑。

合并稿是投稿产物：漏节 / 引用越界静默放行 / 参考文献丢失都会产出坏投稿包，
故属高危。覆盖从未被测的纯函数与端到端 run_merge：
  引用号解析              expand_citation_numbers（注意与 state_manager 行为不同：
                          逆序区间在此展开成完整升序范围）
  引用扫描               collect_citation_numbers（保出现序去重）
  文件发现/排序          discover_markdown_files（排合并稿、按前导序号排序）
  natural_key/leading_index
  参考文献剥离           split_out_references_section
  合并                   merge_markdown_files（relocate refs、--- 分隔、跳空文件）
  合并前引用越界检查      validate_merge_precheck（越界 ok=False / 空 index warn skip）
  参考文献格式化          format_reference_entry（vancouver/nature/citation 直传/str）
  端到端                 run_merge（产 md、含 References、坏 section→precheck 拦）

Run: python3 test_merge_manuscript.py   (rc=0 = 全过)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_manuscript as M

SCRIPT = Path(__file__).resolve().parent / "merge_manuscript.py"


def test_expand_citation_numbers():
    assert M.expand_citation_numbers("1-3,5") == [1, 2, 3, 5], "顺序区间展开"
    # 与 state_manager 不同：这里逆序区间展开成完整升序范围
    assert M.expand_citation_numbers("3-1") == [1, 2, 3], "逆序区间在此展开成升序范围"
    assert M.expand_citation_numbers("2, 2, 4") == [2, 4], "稳定去重"
    assert M.expand_citation_numbers("") == [], "空→空"


def test_collect_citation_numbers():
    # 保出现顺序去重（非排序）——锁死与 state_manager 的差异
    assert M.collect_citation_numbers("x [2] y [1,3-4]") == [2, 1, 3, 4], "保出现序"
    assert M.collect_citation_numbers("no cite") == []


def test_natural_key_and_leading_index():
    files = ["10_x.md", "2_x.md", "1_x.md"]
    assert sorted(files, key=M.natural_key) == ["1_x.md", "2_x.md", "10_x.md"], "自然排序"
    assert M.leading_index("04_results.md") == 4
    assert M.leading_index("abstract.md") == 9999, "无前导序号→兜底大值"


def test_discover_markdown_files_order_and_exclusion():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "05_Discussion.md").write_text("d", encoding="utf-8")
        (d / "01_Abstract.md").write_text("a", encoding="utf-8")
        (d / "04_Results.md").write_text("r", encoding="utf-8")
        (d / "Full_Manuscript.md").write_text("MERGED", encoding="utf-8")  # 必须排除
        found = [Path(p).name for p in M.discover_markdown_files(str(d), M.DEFAULT_PATTERNS)]
        assert "Full_Manuscript.md" not in found, "合并稿必须被排除"
        # 按前导序号升序
        assert found == ["01_Abstract.md", "04_Results.md", "05_Discussion.md"], found


def test_split_out_references_section():
    content = "Intro body [1].\n\n# References\n1. First ref.\n2. Second\ncontinued.\n"
    body, refs = M.split_out_references_section(content)
    assert body == "Intro body [1].", f"正文应剥离 References: {body!r}"
    # 多行条目应被拼接
    assert refs == ["First ref.", "Second continued."], refs
    # 无 References → 原样、空 refs
    b2, r2 = M.split_out_references_section("just body no refs")
    assert b2 == "just body no refs" and r2 == []


def test_merge_markdown_files():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        f1 = d / "a.md"; f1.write_text("Section A body.\n", encoding="utf-8")
        f2 = d / "b.md"; f2.write_text("Section B body.\n", encoding="utf-8")
        f3 = d / "empty.md"; f3.write_text("   \n", encoding="utf-8")  # 空文件应跳过
        merged, refs = M.merge_markdown_files([str(f1), str(f2), str(f3)])
        assert "Section A body." in merged and "Section B body." in merged
        assert "\n\n---\n\n" in merged, "节间应有 --- 分隔"
        assert merged.count("---") == 1, "空文件不产生多余分隔"


def test_validate_merge_precheck():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        idx = d / "literature_index.json"
        idx.write_text(json.dumps([{"a": 1}, {"b": 2}]), encoding="utf-8")  # 2 条
        good = d / "good.md"; good.write_text("cite [1] and [2]\n", encoding="utf-8")
        rep = M.validate_merge_precheck([str(good)], str(idx))
        assert rep["ok"] is True and rep["out_of_range"] == [], rep
        # 引用 [3] 越界 → ok False + errors
        bad = d / "bad.md"; bad.write_text("cite [3]\n", encoding="utf-8")
        rep2 = M.validate_merge_precheck([str(bad)], str(idx))
        assert rep2["ok"] is False and 3 in rep2["out_of_range"], rep2
        # 空 index → 跳过范围检查（warn，不拦）
        empty = d / "empty_index.json"; empty.write_text("[]", encoding="utf-8")
        rep3 = M.validate_merge_precheck([str(good)], str(empty))
        assert rep3["ok"] is True and any("skipped" in w for w in rep3["warnings"]), rep3


def test_format_reference_entry():
    assert M.format_reference_entry({"authors": "A", "title": "T", "journal": "J", "year": 2020}, 1) \
        == "1. A. T. J. 2020.", "vancouver"
    nat = M.format_reference_entry(
        {"authors": "A", "title": "T", "journal": "J", "year": 2020, "volume": "5", "pages": "1-9"},
        1, style="nature")
    assert nat == "1. A. T. J 5, 1-9 (2020).", nat
    # 预构建 citation 字段直传
    assert M.format_reference_entry({"citation": "Prebuilt."}, 2) == "2. Prebuilt."
    # 字符串条目
    assert M.format_reference_entry("raw str", 3) == "3. raw str"


def test_run_merge_end_to_end():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        man = d / "manuscripts"; man.mkdir()
        (man / "01_Abstract.md").write_text("Abstract text [1].\n", encoding="utf-8")
        (man / "04_Results.md").write_text("Results text [1].\n", encoding="utf-8")
        (d / "literature_index.json").write_text(
            json.dumps([{"authors": "Smith J", "title": "X", "journal": "Nat", "year": 2020}]),
            encoding="utf-8")
        out_md = d / "manuscripts" / "Full_Manuscript.md"
        # skip-docx 避免依赖 pandoc；cwd=d 让 index 相对路径命中
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--manuscript-dir", str(man),
             "--output-md", str(out_md), "--skip-docx"],
            capture_output=True, text=True, cwd=str(d))
        assert r.returncode == 0, f"合规合并应 exit 0\n{r.stdout}\n{r.stderr}"
        report = json.loads(r.stdout)
        assert report["ok"] is True, report
        assert report["files_merged_count"] == 2, report
        text = out_md.read_text(encoding="utf-8")
        assert "AUTO-GENERATED" in text, "应有防手改 banner"
        assert "# References" in text and "Smith J" in text, "参考文献应重定位到末尾"

        # 引用越界 → precheck 拦，exit 2
        (man / "04_Results.md").write_text("Results [9] out of range.\n", encoding="utf-8")
        r2 = subprocess.run(
            [sys.executable, str(SCRIPT), "--manuscript-dir", str(man),
             "--output-md", str(out_md), "--skip-docx"],
            capture_output=True, text=True, cwd=str(d))
        assert r2.returncode == 2, f"越界应硬拦 exit 2\n{r2.stdout}"
        assert "merge_precheck_failed" in r2.stdout, r2.stdout


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

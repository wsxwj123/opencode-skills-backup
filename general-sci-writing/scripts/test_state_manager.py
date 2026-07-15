#!/usr/bin/env python3
"""state_manager.py 回归测试 — 自包含、纯 assert、无框架、standalone 可跑。

覆盖 state_manager 里从未被测的高危核心逻辑（基准=当前代码真实行为）：
  引用号解析/压缩/重编号   expand/compress/collect_citation_numbers,
                          rewrite_citations_in_text（改用户引文，最高危）
  引用越界门禁            validate_number_integrity（chdir 造工程）
  快照/回滚               backup_project_state + restore_project_snapshot +
                          rollback_state（改用户稿件与状态，最高危）
  字数统计               calculate_word_counts（排 References / 按 section 过滤）
  参考文献格式化          format_reference_entry（vancouver/nature/str/空）
  section/文件名匹配      filename_matches_section / section_terms /
                          extract_numeric_section
  写作前置 refs 清单      required_refs_for_section（按 section 角色）
  归一化/相似度/计数      normalize_doi/title, title_similarity,
                          strip_references_markdown, count_index_entries

Run: python3 test_state_manager.py   (rc=0 = 全过)

注：extract_numeric_section 对带前导序号的名字（'04_results_3.2'）返回 '04' 而
非文档声称的 '3.2'（前导序号截胡）——见报告"疑似 bug"，此处只断言无前导序号的
安全用例，不把疑似 bug 当正确行为固化。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_manager as S


# ── 引用号解析 expand_citation_numbers ───────────────────────────────────────
def test_expand_citation_numbers():
    assert S.expand_citation_numbers("1-3,5") == [1, 2, 3, 5], "顺序区间应展开"
    # 逆序区间不展开成范围，只取两端点（当前真实行为，锁死防退化）
    assert S.expand_citation_numbers("3-1") == [3, 1], "逆序区间取两端点"
    assert S.expand_citation_numbers("") == [], "空串→空"
    assert S.expand_citation_numbers(" , ,") == [], "全空 token→空"
    assert S.expand_citation_numbers("a,2,x") == [2], "非数字 token 被丢弃"
    assert S.expand_citation_numbers("7") == [7], "单值"


# ── 引用号压缩 compress_citation_numbers ─────────────────────────────────────
def test_compress_citation_numbers():
    assert S.compress_citation_numbers([]) == "", "空→空串"
    assert S.compress_citation_numbers([1, 2, 3, 5, 5, 7]) == "1-3,5,7", "去重+连号成区间"
    assert S.compress_citation_numbers([5, 1, 2]) == "1-2,5", "先排序再压缩"
    assert S.compress_citation_numbers([9]) == "9", "单值不加连字符"
    # 与 expand 大致互逆（顺序输入）
    assert S.expand_citation_numbers(S.compress_citation_numbers([1, 2, 3, 8])) == [1, 2, 3, 8]


# ── collect_citation_numbers：扫方括号、排序去重 ─────────────────────────────
def test_collect_citation_numbers():
    assert S.collect_citation_numbers("a [3] b [1,2] c [1]") == [1, 2, 3], "排序去重"
    assert S.collect_citation_numbers("no citations here") == [], "无引用→空"
    assert S.collect_citation_numbers("range [2-4]") == [2, 3, 4], "区间展开"


# ── rewrite_citations_in_text：引文重编号（改用户引用，最高危）─────────────────
def test_rewrite_citations_in_text():
    # 映射 1→5, 2→1, 3→2；[2-3] 映射后为 [1,2] 应压回 "1-2"
    new, changed = S.rewrite_citations_in_text("see [1] and [2-3]", {1: 5, 2: 1, 3: 2})
    assert new == "see [5] and [1-2]", f"重编号+压缩错误: {new}"
    assert changed is True, "有改动 changed 必须 True"
    # 无匹配映射 → 原样、changed=False
    new2, changed2 = S.rewrite_citations_in_text("plain text no cite", {1: 5})
    assert new2 == "plain text no cite" and changed2 is False, "无引用不应标记 changed"
    # 恒等映射 → 文本不变、changed=False
    new3, changed3 = S.rewrite_citations_in_text("keep [1] and [2]", {1: 1, 2: 2})
    assert new3 == "keep [1] and [2]" and changed3 is False, "恒等映射不应改动"


# ── strip_references_markdown ────────────────────────────────────────────────
def test_strip_references_markdown():
    assert S.strip_references_markdown("body words\n# References\n1. x") == "body words\n"
    assert S.strip_references_markdown("正文\n## 参考文献\n1. y") == "正文\n"
    # 无 References 段 → 原样返回
    assert S.strip_references_markdown("just body") == "just body"
    assert S.strip_references_markdown("") == "", "空/None 安全"
    assert S.strip_references_markdown(None) == ""


# ── 归一化 / 相似度 ──────────────────────────────────────────────────────────
def test_normalize_and_similarity():
    assert S.normalize_doi("  10.1038/ABC ") == "10.1038/abc", "去空白+小写"
    assert S.normalize_doi("") == "" and S.normalize_doi(None) == ""
    assert S.normalize_title("Cancer: A  Study!") == "cancer a study", "标点归一为单空格"
    sim = S.title_similarity("cancer study", "cancer studies")
    assert 0.0 < sim <= 1.0, f"相似度应在 (0,1]，got {sim}"
    assert S.title_similarity("", "x") == 0.0, "空串相似度 0"


# ── format_reference_entry ───────────────────────────────────────────────────
def test_format_reference_entry():
    e = {"authors": "Smith J", "title": "X", "journal": "Nat",
         "year": 2020, "volume": "1", "pages": "2-9", "doi": "10.1/x"}
    vanc = S.format_reference_entry(e, 3)
    assert vanc.startswith("3. Smith J. X. Nat. 2020;1:2-9."), f"vancouver 格式: {vanc}"
    assert "doi:10.1/x" in vanc, "含 doi"
    nat = S.format_reference_entry(e, 1, style="nature")
    assert nat.startswith("1. Smith J. X. Nat 1, 2-9 (2020)"), f"nature 格式: {nat}"
    # 字符串条目：直接编号
    assert S.format_reference_entry("Raw ref text", 4) == "4. Raw ref text"
    # 空 dict → 仅编号
    assert S.format_reference_entry({}, 5) == "5."


# ── section / 文件名匹配 ─────────────────────────────────────────────────────
def test_section_matching():
    assert S.filename_matches_section("04_Results_3.1_Char.md", "results_3.1") is True
    # 不匹配：section 号不同
    assert S.filename_matches_section("04_Results_3.2.md", "results_3.1") is False
    # section_terms 生成分隔符变体
    terms = S.section_terms("results_3.1")
    assert "results_3.1" in terms and "results_3_1" in terms, terms
    # 无前导序号名字取到内层数字（安全用例）
    assert S.extract_numeric_section("results_3.1") == "3.1"
    assert S.extract_numeric_section("intro_2") == "2"
    assert S.extract_numeric_section("no_number") is None


# ── required_refs_for_section：按 section 角色给写作前置 refs ─────────────────
def test_required_refs_for_section():
    base = "references/anti-ai-protocol.md"
    # 所有角色都含 anti-ai-protocol
    for sec in ("04_results_3.1", "03_methods", "02_intro", "01_abstract", "uptake"):
        assert base in S.required_refs_for_section(sec), f"{sec} 缺 anti-ai-protocol"
    # abstract/title 只需 anti-ai-protocol
    assert S.required_refs_for_section("01_abstract") == [base], "摘要仅需 anti-ai"
    # results/discussion 需图依据 + 模板 + 引用政策
    rd = S.required_refs_for_section("04_results_3.1")
    assert any("figure_analysis" in r for r in rd) and any("citation-policy" in r for r in rd)
    # methods 需模板但不需图依据
    meth = S.required_refs_for_section("03_methods")
    assert any("writing-templates" in r for r in meth)
    assert not any("figure_analysis" in r for r in meth), "methods 不应含图依据"
    # 去重：无重复项
    assert len(rd) == len(set(rd)), "refs 应去重"


# ── count_index_entries ──────────────────────────────────────────────────────
def test_count_index_entries():
    assert S.count_index_entries([1, 2, 3]) == 3, "list 直接计数"
    assert S.count_index_entries({"references": [1, 2, 3]}) == 3, "dict 取 references"
    assert S.count_index_entries({"items": [1]}) == 1, "dict 取 items"
    assert S.count_index_entries("scalar") == 0, "标量→0"


# ── 需 chdir 的工程级函数 ────────────────────────────────────────────────────
class _InDir:
    """chdir 到 path，退出时恢复（避免污染其他测试的相对路径）。"""
    def __init__(self, path): self.path = str(path)
    def __enter__(self): self.old = os.getcwd(); os.chdir(self.path); return self.path
    def __exit__(self, *a): os.chdir(self.old)


def test_calculate_word_counts():
    with tempfile.TemporaryDirectory() as td, _InDir(td):
        os.makedirs("manuscripts")
        Path("manuscripts/02_intro.md").write_text(
            "one two three four\n# References\n1. cite text here\n", encoding="utf-8")
        Path("manuscripts/04_results.md").write_text("alpha beta\n", encoding="utf-8")
        # 排 References：intro 只数正文 4 词
        wc = S.calculate_word_counts(exclude_references=True)
        assert wc["sections"]["02_intro.md"] == 4, f"应排除 References: {wc}"
        assert wc["total"] == 6, f"total 4+2=6: {wc}"
        # 含 References：intro 数全部
        wc2 = S.calculate_word_counts(exclude_references=False)
        assert wc2["sections"]["02_intro.md"] > 4, "含 References 词数更多"
        # 按 section 过滤：只数 results
        wc3 = S.calculate_word_counts(section="results")
        assert set(wc3["sections"].keys()) == {"04_results.md"}, wc3


def test_validate_number_integrity():
    with tempfile.TemporaryDirectory() as td, _InDir(td):
        os.makedirs("manuscripts")
        # index 有 2 条；正文引用 [1][2] → 合法
        Path("literature_index.json").write_text(json.dumps([{"a": 1}, {"b": 2}]), encoding="utf-8")
        Path("manuscripts/04_results.md").write_text("see [1] and [2]\n", encoding="utf-8")
        r = S.validate_number_integrity()
        assert r["ok"] is True and r["out_of_range"] == [], f"合法引用应过: {r}"
        # 引用 [3] 越界（index 只 2 条）→ 拦
        Path("manuscripts/04_results.md").write_text("see [3]\n", encoding="utf-8")
        r2 = S.validate_number_integrity()
        assert r2["ok"] is False and 3 in r2["out_of_range"], f"越界必须报: {r2}"
        # 缺 index → ok False
        os.remove("literature_index.json")
        r3 = S.validate_number_integrity()
        assert r3["ok"] is False, "缺 index 必须报"


def test_snapshot_backup_restore_rollback():
    with tempfile.TemporaryDirectory() as td, _InDir(td):
        os.makedirs("manuscripts")
        Path("storyline.json").write_text('{"sections":[{"id":"intro"}]}', encoding="utf-8")
        Path("writing_progress.json").write_text('{"update_history":[]}', encoding="utf-8")
        Path("manuscripts/02_intro.md").write_text("ORIGINAL intro body\n", encoding="utf-8")

        snap = S.backup_project_state()
        assert os.path.isdir(snap), "快照目录应建立"

        # 破坏：改正文 + 删状态文件
        Path("manuscripts/02_intro.md").write_text("CORRUPTED\n", encoding="utf-8")
        os.remove("storyline.json")

        # 直接 restore 指定快照 → 还原
        res = S.restore_project_snapshot(snap)
        assert res["restored"] is True, res
        assert Path("manuscripts/02_intro.md").read_text(encoding="utf-8") == "ORIGINAL intro body\n", \
            "正文未还原"
        assert os.path.exists("storyline.json"), "状态文件未还原"

        # rollback_state(target=snapshot) 自动选最新快照 → 还原
        Path("manuscripts/02_intro.md").write_text("CORRUPT AGAIN\n", encoding="utf-8")
        rb = S.rollback_state(target="snapshot")
        assert rb["restored"] is True, rb
        assert Path("manuscripts/02_intro.md").read_text(encoding="utf-8") == "ORIGINAL intro body\n", \
            "rollback 未还原正文"

        # 未知 target → restored False，不炸
        assert S.rollback_state(target="bogus")["restored"] is False

    # 不存在的快照目录 → restored False（不抛异常）
    assert S.restore_project_snapshot("/nonexistent/snap")["restored"] is False


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

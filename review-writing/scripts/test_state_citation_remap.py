#!/usr/bin/env python3
"""Regression guard: state_manager 引用重编号核心（reindex/sync-apply 会用它改写
用户 drafts 里的 [n] 引用与 ## References 编号）。这是全技能最高危的纯逻辑——
一个 off-by-one 就静默改错读者看到的引用编号，且难以事后发现。

覆盖纯函数（可直接 import，无 IO）：
  _expand_citation_token   —— "5"/"3-6"/降序"6-3"/非法 token
  _compress_citation_numbers —— 连号压成区间、乱序去重、空
  _remap_citation_brackets —— 正文 [n] 批量重映射；strict 缺号不动 + 记 unresolved；
                              非 strict 缺号保留原号；区间展开后重压缩
  _remap_reference_section —— ## References 内的 "1. xxx" 行按映射改号，
                              节外与非引用行不动

内含一条【已知 bug 文档化断言】：_remap_reference_section 会吃掉被改写行的行尾
\\n（见 test_reference_section_KNOWN_newline_bug）。该断言锁的是当前(有缺陷)行为，
修好后此断言会失败以提醒更新——详见文件末注释与返回简报。
"""
from __future__ import annotations

import state_manager as sm


def test_expand_token():
    assert sm._expand_citation_token("5") == [5]
    assert sm._expand_citation_token("3-6") == [3, 4, 5, 6]
    # 降序区间也展开（虽罕见，锁住当前行为）
    assert sm._expand_citation_token("6-3") == [6, 5, 4, 3]
    # 非数字/非区间 → None（调用方据此放弃整段替换）
    assert sm._expand_citation_token("foo") is None
    assert sm._expand_citation_token("1,2") is None  # 逗号不在单 token 内展开


def test_compress_numbers():
    assert sm._compress_citation_numbers([1, 2, 3, 5]) == "1-3,5"
    # 乱序 + 重复 → 去重排序压缩
    assert sm._compress_citation_numbers([3, 1, 2, 2]) == "1-3"
    assert sm._compress_citation_numbers([1, 3, 5]) == "1,3,5"
    assert sm._compress_citation_numbers([7]) == "7"
    assert sm._compress_citation_numbers([]) == ""


def test_remap_brackets_basic_and_recompress():
    un = set()
    out, changed = sm._remap_citation_brackets(
        "See [1,2] and [5-6].", {1: 10, 2: 11, 5: 20, 6: 21}, True, un)
    # 1,2→10,11 压成 10-11；5-6→20,21 压成 20-21
    assert out == "See [10-11] and [20-21]." and changed == 2 and un == set(), (out, changed, un)


def test_remap_brackets_strict_missing_is_noop_and_recorded():
    # strict: 括号里出现未映射号 → 整段不动 + 记 unresolved（宁可不改也不错改）
    un = set()
    out, changed = sm._remap_citation_brackets("See [3].", {1: 10}, True, un)
    assert out == "See [3]." and changed == 0 and un == {3}, (out, changed, un)

    # strict 且同一括号里既有可映射又有缺号 → 仍整段不动
    un = set()
    out, changed = sm._remap_citation_brackets("See [1,3].", {1: 10}, True, un)
    assert out == "See [1,3]." and changed == 0 and 3 in un, (out, changed, un)


def test_remap_brackets_nonstrict_keeps_unmapped_number():
    # 非 strict: 缺号保留原值参与压缩，其余照映射
    un = set()
    out, changed = sm._remap_citation_brackets("See [1,3].", {1: 10}, False, un)
    # 1→10, 3 保留 → [3,10] 压成 "3,10"
    assert out == "See [3,10]." and 3 in un, (out, un)


def test_remap_brackets_ignores_nonnumeric_group():
    # 方括号里若非纯数字/区间（正则本就不匹配）→ 原样不动
    un = set()
    out, changed = sm._remap_citation_brackets("See [Fig 1] here.", {1: 9}, False, un)
    assert out == "See [Fig 1] here." and changed == 0, out


def test_reference_section_numbers_remapped_and_body_untouched():
    txt = "intro [1] text\n## References\n1. Foo\n2. Bar\n## Next\n3. NotARef line\n"
    un = set()
    out, changed = sm._remap_reference_section(txt, {1: 10, 2: 20}, True, un)
    # 安全不变量：References 段内 1.→10.、2.→20.（正文 [1] 与节外 "3." 不由本函数管）
    assert "10." in out and "20." in out, out
    assert "intro [1] text" in out, "节外正文不该被本函数改动"
    assert "## Next" in out and "3. NotARef line" in out, "下一节标题后的行不该被改号"
    assert changed == 2, changed


def test_reference_section_strict_missing_recorded():
    txt = "## References\n1. Foo\n9. Bar\n"
    un = set()
    out, changed = sm._remap_reference_section(txt, {1: 10}, True, un)
    assert 9 in un, "strict 下缺映射的条目号必须记入 unresolved"
    assert "10." in out, out


def test_reference_section_KNOWN_newline_bug():
    """【已知 bug 锁定】_remap_reference_section 改写引用行时丢弃行尾 \\n，
    把相邻条目粘连（'10. Foo20. Bar'）并吃掉文件末换行。根因：ref_num_re 的
    `(\\s+.*)$` 不含行尾换行，重建 new_line 时未补回。

    此断言锁当前(有缺陷)输出；一旦修复（保留换行），此断言会失败——那是预期信号，
    提示同步更新本测试。不改业务码。"""
    txt = "## References\n1. Foo\n2. Bar\n"
    out, _ = sm._remap_reference_section(txt, {1: 10, 2: 20}, False, set())
    assert out == "## References\n10. Foo20. Bar", (
        "若本断言失败，很可能是换行 bug 已修复，请把期望改为 "
        "'## References\\n10. Foo\\n20. Bar\\n'"
    )


if __name__ == "__main__":
    test_expand_token()
    test_compress_numbers()
    test_remap_brackets_basic_and_recompress()
    test_remap_brackets_strict_missing_is_noop_and_recorded()
    test_remap_brackets_nonstrict_keeps_unmapped_number()
    test_remap_brackets_ignores_nonnumeric_group()
    test_reference_section_numbers_remapped_and_body_untouched()
    test_reference_section_strict_missing_recorded()
    test_reference_section_KNOWN_newline_bug()
    print("OK: state_manager 引用重编号 — token展开/压缩/正文重映射/参考段改号 + 换行bug已锁定")

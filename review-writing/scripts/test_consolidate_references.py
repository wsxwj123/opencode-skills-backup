#!/usr/bin/env python3
"""Regression guard: consolidate_references.py —— Phase 4 把每节自带的
`## References` 块合并成文末唯一一份全局参考列表，就地改写 Final_Review.md。

风险：这一步直接覆盖最终投稿正文。两类静默事故必须挡住——
  1) strip_reference_blocks 把正文当参考块吃掉（丢正文）；
  2) consolidate 漏引/错序/漏标未在索引里的号，产坏投稿包。

覆盖纯函数（无网络/无外部依赖，tempfile 造输入）：
  strip_reference_blocks —— 剥离真参考块、遇到非条目正文行即停（不吞正文）；
  render_vancouver       —— 条目渲染字段拼装 + 缺字段降级；
  build_index_map        —— global_id 建索引（含 dict 包裹 papers）；
  consolidate            —— 端到端：升序输出、缺号标 [MISSING FROM INDEX]、幂等。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import consolidate_references as cr


def test_strip_removes_ref_block_but_keeps_body():
    txt = ("Body para.\n## References\n- [1] A.\n- [2] B.\n"
           "## Next\nMore body [1].\n")
    out = cr.strip_reference_blocks(txt)
    assert "[1] A." not in out and "[2] B." not in out, "参考条目应被剥离"
    assert "Body para." in out and "## Next" in out and "More body [1]." in out, \
        f"正文/下一节标题不能被吃: {out!r}"


def test_strip_stops_at_unexpected_body_line():
    # 参考块里混入一句真正文（非条目、非空、非标题）→ 就地停剥，保住该行
    txt = "## References\n- [1] A.\nThis is real prose, not a ref entry.\n"
    out = cr.strip_reference_blocks(txt)
    assert "This is real prose, not a ref entry." in out, \
        f"非条目正文行必须保留,不能被当参考吃掉: {out!r}"


def test_render_vancouver_full_and_degraded():
    full = cr.render_vancouver(
        {"authors": ["Smith J", "Doe A"], "title": "Title.",
         "journal": "Nature", "year": 2020, "doi": "10.1/x"}, 5)
    assert full == "- [5] Smith J, Doe A. Title. Nature. 2020. doi:10.1/x", full
    # 只有 title → 不崩、只拼 title
    assert cr.render_vancouver({"title": "Only title"}, 3) == "- [3] Only title.", \
        cr.render_vancouver({"title": "Only title"}, 3)


def test_build_index_map_supports_wrapped_dict():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "idx.json"
        p.write_text(json.dumps(
            {"papers": [{"global_id": 2, "title": "B"},
                        {"global_id": 1, "title": "A"}]}), encoding="utf-8")
        m = cr.build_index_map(str(p))
        assert set(m.keys()) == {1, 2} and m[1]["title"] == "A", m


def test_consolidate_ordering_missing_and_idempotent():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        md = root / "Final_Review.md"
        # 正文乱序引用 3、1，并用一个索引里没有的号 9
        md.write_text(
            "Sec one [3].\n## References\n- [3] old.\n\n"
            "Sec two [1] and [9].\n## References\n- [1] old.\n",
            encoding="utf-8")
        idx = root / "index.json"
        idx.write_text(json.dumps([
            {"global_id": 1, "title": "One", "year": 2019},
            {"global_id": 3, "title": "Three", "year": 2021},
        ]), encoding="utf-8")

        rc = cr.consolidate(str(md), str(idx))
        assert rc == 0
        first = md.read_text(encoding="utf-8")
        # 只剩文末一份 References
        assert first.count("## References") == 1, first
        # 升序 1,3,9 且 9 标缺失
        body_refs = first.split("## References", 1)[1]
        pos1, pos3, pos9 = (body_refs.index("[1]"), body_refs.index("[3]"),
                            body_refs.index("[9]"))
        assert pos1 < pos3 < pos9, f"参考应按号升序: {body_refs}"
        assert "[9] [MISSING FROM INDEX]" in body_refs, body_refs

        # 幂等：再跑一次输出不变
        cr.consolidate(str(md), str(idx))
        assert md.read_text(encoding="utf-8") == first, "重复合并应幂等"


if __name__ == "__main__":
    test_strip_removes_ref_block_but_keeps_body()
    test_strip_stops_at_unexpected_body_line()
    test_render_vancouver_full_and_degraded()
    test_build_index_map_supports_wrapped_dict()
    test_consolidate_ordering_missing_and_idempotent()
    print("OK: consolidate_references — 剥块不吞正文 + 渲染降级 + 升序/缺号标记/幂等")

#!/usr/bin/env python3
"""structure_signoff_gate 白盒自测：结构投影 / 五类差异 / 退出码。

黑盒验收考卷（tests/acceptance/test_gate_outline_fingerprint.py）钉的是对外行为；
这里补它够不着的内部不变量——投影只取结构不取正文、改序只算公共节的相对次序、
每类差异 10 条封顶、nsfc 链路字段绝不放正文进来。

跑法：python3 _shared/test_structure_signoff_gate.py
"""
from __future__ import annotations

import io
import json
import contextlib
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import structure_signoff_gate as g  # noqa: E402

GATE = Path(__file__).resolve().parent / "structure_signoff_gate.py"


def _gsw(root: Path, sections):
    root.mkdir(parents=True, exist_ok=True)
    (root / "storyline.json").write_text(json.dumps(
        {"sections": sections, "updated_at": "2026-01-01"}, ensure_ascii=False),
        encoding="utf-8")
    (root / "writing_progress.json").write_text(
        json.dumps({"update_history": []}), encoding="utf-8")
    return root


def _run(fn, *args):
    """跑子命令，返回 (rc, stdout)。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*args)
    return rc, buf.getvalue()


def test_projection_takes_structure_only():
    """投影只要 id/标题/层级；正文、进度、统计一律不进（否则每写一节都要重签）。"""
    nodes: list = []
    g._walk({"chapters": [
        {"id": "3", "title": " 第三章  绪 论 ", "status": "done",
         "body": "SENTINEL正文", "word_count": 8123,
         "sections": [{"id": "3.1", "title": "第一节", "status": "completed"}]},
    ]}, 2, nodes)
    assert nodes == [["3", "第三章 绪 论", 2], ["3.1", "第一节", 3]], nodes
    assert "SENTINEL" not in json.dumps(nodes, ensure_ascii=False)


def test_title_clipped_to_80():
    long = "标" * 200
    out = g._norm_title(long)
    assert len(out) == g.TITLE_MAX + 1 and out.endswith("…"), len(out)


def test_rw_level_from_hash_count():
    """层级取井号个数：`## 2.2` → 3 级会被 section_id 段数推法漏掉。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "outline.md").write_text(
            "# 综述大纲\n\n## 2.1 背景\n\n### 2.2 现状\n\n## 参数配置\n",
            encoding="utf-8")
        nodes, sources = g._proj_rw(root)
    assert nodes == [["2.1", "背景", 2], ["2.2", "现状", 3]], nodes
    assert sources == ["outline.md"]


def test_nsfc_links_reject_prose():
    """nsfc 只取 id 与链路：链路字段里混进正文（中文表述）必须被挡在外面。"""
    line = g._nsfc_links({"id": "H1", "text": "本课题拟阐明的机制",
                          "mapped_to_objective": ["O1", "整句中文说明"],
                          "supports_method": "M1"})
    assert line == "mapped_to_objective=O1;supports_method=M1", line


def test_diff_five_classes():
    old = [["2.1", "背景", 2], ["2.2", "现状", 2], ["2.3", "旧节", 2]]
    new = [["2.2", "研究现状与趋势", 3], ["2.1", "背景", 2], ["2.4", "新节", 2]]
    lines = g.diff_lines(old, new)
    joined = "\n".join(lines)
    assert "新增的节：" in joined and "2.4" in joined, joined
    assert "删除的节：" in joined and "2.3" in joined, joined
    assert "改名的节：" in joined and "研究现状与趋势" in joined, joined
    assert "顺序变化：" in joined and "2.1" in joined, joined
    assert "层级变化：" in joined and "2.2" in joined, joined


def test_pure_insert_is_not_reorder():
    """只在中间插一节，不该把后面所有节都报成"顺序变化"刷屏。"""
    old = [["1", "a", 2], ["2", "b", 2]]
    new = [["1", "a", 2], ["1.5", "c", 2], ["2", "b", 2]]
    lines = g.diff_lines(old, new)
    assert any(l.startswith("新增的节：") for l in lines), lines
    assert not any(l.startswith("顺序变化：") for l in lines), lines


def test_diff_caps_at_ten_with_remainder():
    old = [["0", "零", 2]]
    new = old + [[str(i), "节%d" % i, 2] for i in range(1, 13)]
    line = [l for l in g.diff_lines(old, new) if l.startswith("新增的节：")][0]
    assert "…等 2 项" in line, line          # 12 条列 10 条，余 2
    assert line.count("「") == g.DIFF_MAX, line


def test_confirm_binds_and_check_detects_change():
    with tempfile.TemporaryDirectory() as td:
        root = _gsw(Path(td) / "p", [{"id": "s1", "title": "引言"},
                                     {"id": "s2", "title": "方法"}])
        rc, _out = _run(g.cmd_confirm, root, "用户确认")
        assert rc == g.EX_OK
        doc = json.loads((root / "structure_signoff.json").read_text(encoding="utf-8"))
        fp = doc["outline_fingerprint"]
        assert fp["skill"] == "general-sci-writing" and len(fp["value"]) == 16, fp
        assert fp["nodes"] == [["s1", "引言", 2], ["s2", "方法", 2]], fp["nodes"]
        assert g.cmd_check(root) == g.EX_OK

        # 进度/统计变动不触发重签
        (root / "writing_progress.json").write_text(
            json.dumps({"update_history": [1], "word_count": 9000}), encoding="utf-8")
        assert g.cmd_check(root) == g.EX_OK

        # 只增不删的"细化扩展"同样要重签，且点名新增的那一节
        _gsw(root, [{"id": "s1", "title": "引言"}, {"id": "s2", "title": "方法"},
                    {"id": "s3", "title": "结果"}])
        rc, out = _run(g.cmd_check, root)
        assert rc == g.EX_RESIGN, (rc, out)
        assert g.RESIGN_MARK in out and "s3" in out, out
        # 拒绝理由不得含绕过路径
        for bad in ("outline_fingerprint", "enforcement_enabled", "关闭门禁"):
            assert bad not in out, (bad, out)


def test_check_fail_open_paths():
    with tempfile.TemporaryDirectory() as td:
        root = _gsw(Path(td) / "p", [{"id": "s1", "title": "引言"}])
        _run(g.cmd_confirm, root, "")
        (root / "storyline.json").write_text("{ 坏", encoding="utf-8")
        rc, _ = _run(g.cmd_check, root)          # 大纲坏了 ≠ 签字失效
        assert rc == g.EX_OK, rc
        # 存量签字（无绑定字段）一律放行 —— 一升级拦死所有在写项目是不可接受的
        (root / "structure_signoff.json").write_text(
            json.dumps({"confirmed": True}), encoding="utf-8")
        rc, out = _run(g.cmd_check, root)
        assert rc == g.EX_OK and "未绑定" in out, (rc, out)
        # confirmed 必须严格是 true：1 / "true" 都不算
        for bad in (1, "true", None):
            (root / "structure_signoff.json").write_text(
                json.dumps({"confirmed": bad}), encoding="utf-8")
            rc, _ = _run(g.cmd_check, root)
            assert rc == g.EX_UNSIGNED, bad


def test_usage_error_exit_64():
    """用法错必须与"还没签"的 2 分开，否则调用方分不清是谁的问题。"""
    proc = subprocess.run([sys.executable, str(GATE), "check"],
                          capture_output=True, timeout=60)
    assert proc.returncode == g.EX_USAGE, proc.returncode
    proc = subprocess.run([sys.executable, str(GATE), "verify", "--root", "."],
                          capture_output=True, timeout=60)
    assert proc.returncode == g.EX_USAGE, proc.returncode


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print("OK: %d 项 structure_signoff_gate 自测通过" % len(tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())

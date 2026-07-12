"""data_trace_gate 数据溯源硬门测试。"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import data_trace_gate as dtg  # noqa: E402


def _mk(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def _materials(tmp_path):
    d = tmp_path / "materials"
    d.mkdir()
    (d / "wb_data.md").write_text(
        "# WB\n## 可引用要点\n- Bax/Bcl-2 比值\n- PMG 20 μg/mL 处理\n", encoding="utf-8")
    return str(tmp_path)


def test_no_numeric_passes(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n0.md", "本节介绍实验背景，见图2-1，引用[3]。")
    v, nf = dtg.gate(root, [f])
    assert not v and nf == []


def test_numeric_without_marker_blocked(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n1.md", "PMG 20 μg/mL 使凋亡率升至 45.3%（p<0.05）。")
    v, nf = dtg.gate(root, [f])
    assert v and nf == ["n1.md"]


def test_numeric_with_valid_marker_passes(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n2.md",
            "PMG 20 μg/mL 使凋亡率升至 45.3%。[数据来源] materials/wb_data.md#PMG")
    v, _ = dtg.gate(root, [f])
    assert not v


def test_marker_missing_material_blocked(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n3.md", "凋亡率 45.3%。[数据来源] materials/ghost.md#x")
    v, _ = dtg.gate(root, [f])
    assert v


def test_marker_missing_field_blocked(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n4.md", "凋亡率 45.3%。[数据来源] materials/wb_data.md")
    v, _ = dtg.gate(root, [f])
    assert v


def test_field_not_in_material_blocked(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n5.md", "凋亡率 45.3%。[数据来源] materials/wb_data.md#缺失字段")
    v, _ = dtg.gate(root, [f])
    assert v


def test_figure_refs_not_numeric(tmp_path):
    root = _materials(tmp_path)
    f = _mk(tmp_path, "n6.md", "如图2-1和表3-2所示，见第2章，引用[12,15]。")
    v, nf = dtg.gate(root, [f])
    assert not v and nf == []


def test_selftest_runs():
    assert dtg._selftest() == 0

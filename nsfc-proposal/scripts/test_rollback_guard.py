#!/usr/bin/env python3
"""Smoke test：nsfc state_manager.py 的 rollback 丢稿守卫(F1) + init 归属冲突门(F8)。

自包含、纯 assert、用 tempfile 造合成项目，走 CLI，不改被测脚本主逻辑。

F1 rollback 丢稿守卫（4 例）：
  ① 全路径合法快照 → 恢复成功(exit 0)
  ② 裸快照名(仅 basename) → 自动解析恢复成功(exit 0)
  ③ 不存在的名 → 拒绝(exit≠0)，工作区 sections/ 内容原样
  ④ 空目录快照 → 拒绝(exit≠0)

F8 init 归属冲突门（4 例）：
  外来 skill state → 拒(exit≠0)；--force-shared → 放；同技能 → 放；全新目录 → 放。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "state_manager.py"


def _run(root: Path, *cli_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *cli_args],
        capture_output=True, text=True)


def _init(root: Path) -> None:
    r = _run(root, "init")
    assert r.returncode == 0, f"init failed: {r.stderr}"


def _p1(root: Path) -> Path:
    return root / "sections" / "P1_立项依据.md"


def test_f1_rollback_guard() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _init(root)
        _p1(root).write_text("MARKER_ORIGINAL", encoding="utf-8")

        snap = _run(root, "snapshot", "--name", "good")
        assert snap.returncode == 0, snap.stderr
        snap_path = Path(json.loads(snap.stdout)["snapshot"])
        snap_name = snap_path.name  # 裸名，如 20260714_120000_good

        # ① 全路径合法快照 → 恢复成功
        _p1(root).write_text("MARKER_CHANGED", encoding="utf-8")
        r1 = _run(root, "rollback", "--snapshot", str(snap_path))
        assert r1.returncode == 0, f"①full-path expected exit0, got {r1.returncode}: {r1.stderr}"
        assert _p1(root).read_text(encoding="utf-8") == "MARKER_ORIGINAL", "①未恢复原稿"

        # ② 裸快照名 → 自动解析恢复成功
        _p1(root).write_text("MARKER_CHANGED_2", encoding="utf-8")
        r2 = _run(root, "rollback", "--snapshot", snap_name)
        assert r2.returncode == 0, f"②bare-name expected exit0, got {r2.returncode}: {r2.stderr}"
        assert _p1(root).read_text(encoding="utf-8") == "MARKER_ORIGINAL", "②裸名未恢复原稿"

        # ③ 不存在的名 → 拒绝、exit≠0、工作区原样
        _p1(root).write_text("MARKER_KEEP", encoding="utf-8")
        r3 = _run(root, "rollback", "--snapshot", "does_not_exist_xyz")
        assert r3.returncode != 0, f"③nonexistent expected exit≠0, got {r3.returncode}"
        assert _p1(root).read_text(encoding="utf-8") == "MARKER_KEEP", "③工作区被误动"

        # ④ 空目录快照 → 拒绝
        empty = root / "snapshots" / "empty_snap"
        empty.mkdir(parents=True, exist_ok=True)
        r4 = _run(root, "rollback", "--snapshot", "empty_snap")
        assert r4.returncode != 0, f"④empty-snapshot expected exit≠0, got {r4.returncode}"
        assert _p1(root).read_text(encoding="utf-8") == "MARKER_KEEP", "④空快照误动工作区"

    print("F1 rollback 守卫：①全路径 ②裸名 ③不存在 ④空目录 全过")


def test_f8_owner_conflict() -> None:
    # 外来 skill state → 拒
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "project_state.json").write_text(
            json.dumps({"skill": "revise-sci"}, ensure_ascii=False), encoding="utf-8")
        r = _run(root, "init")
        assert r.returncode != 0, "外来skill应拒"
        assert "冲突" in (r.stdout + r.stderr), "缺冲突提示"

        # --force-shared → 放
        r2 = _run(root, "init", "--force-shared")
        assert r2.returncode == 0, f"--force-shared应放行: {r2.stderr}"

    # 同技能 state → 放
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "project_state.json").write_text(
            json.dumps({"skill": "nsfc-proposal"}, ensure_ascii=False), encoding="utf-8")
        r = _run(root, "init")
        assert r.returncode == 0, f"同技能应放行: {r.stderr}"

    # 全新空目录 → 放
    with tempfile.TemporaryDirectory() as td:
        r = _run(Path(td), "init")
        assert r.returncode == 0, f"全新目录应放行: {r.stderr}"

    print("F8 归属冲突门：外来拒 / force-shared放 / 同技能放 / 全新放 全过")


def test_f4_init_copies_json_skips_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _init(root)
        scripts = root / "scripts"
        assert (scripts / "gate_registry.json").exists(), "gate_registry.json 未拷入项目"
        stray = list(scripts.glob("test_*.py"))
        assert not stray, f"test_*.py 不应拷入项目: {stray}"
    print("F4 init 拷贝：含 gate_registry.json、无 test_*.py 全过")


if __name__ == "__main__":
    test_f1_rollback_guard()
    test_f8_owner_conflict()
    test_f4_init_copies_json_skips_test()
    print("ALL PASS")

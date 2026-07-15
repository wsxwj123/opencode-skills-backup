#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
state_manager.py 回归测试（开发者维护工具，非运行时流程）。

覆盖高危数据安全路径：
- safe_json_dump / safe_json_load 往返一致，且无 .tmp_state_* 残留
- update_json_locked：mutate 抛异常时原文件不被截断（旧内容完好、非 0 字节）
- backup_project_state / restore_snapshot：备份→改动→还原能恢复
- prune_snapshots(keep=N)：保留最新 N 个，不误删 atomic_md 稿件目录

纯 assert，无框架依赖。用法：python3 test_state_manager.py
"""

import glob
import json
import os
import sys
import tempfile
import shutil
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import state_manager as sm


# ---------------------------------------------------------------------------
# safe_json_dump / safe_json_load
# ---------------------------------------------------------------------------

def test_json_roundtrip_and_no_tmp_residue():
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "sub", "state.json")
        payload = {"中文键": ["值1", 2, {"nested": True}], "n": 3}
        sm.safe_json_dump(path, payload)
        loaded = sm.safe_json_load(path)
        assert loaded == payload, loaded
        # 目录内无 .tmp_state_* 残留
        residue = glob.glob(os.path.join(os.path.dirname(path), ".tmp_state_*"))
        assert residue == [], f"存在临时文件残留：{residue}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_json_load_missing_returns_default():
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "nope.json")
        assert sm.safe_json_load(path, default={"a": 1}) == {"a": 1}
        # default 深拷贝：修改返回值不影响后续调用
        r = sm.safe_json_load(path, default={"a": 1})
        r["a"] = 999
        assert sm.safe_json_load(path, default={"a": 1}) == {"a": 1}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# update_json_locked 原子性
# ---------------------------------------------------------------------------

def test_update_json_locked_mutate_raises_keeps_file_intact():
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "state.json")
        original = {"progress": {"last_chapter": "3"}, "keep": "me"}
        sm.safe_json_dump(path, original)
        size_before = os.path.getsize(path)

        def bad_mutate(_cur):
            raise RuntimeError("boom")

        raised = False
        try:
            sm.update_json_locked(path, {}, bad_mutate)
        except RuntimeError:
            raised = True
        assert raised, "mutate 异常应向上抛出"

        # 原文件不得被截断为空
        assert os.path.getsize(path) > 0
        assert os.path.getsize(path) == size_before
        assert sm.safe_json_load(path) == original
        # 无临时文件残留
        assert glob.glob(os.path.join(tmp, ".tmp_state_*")) == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_update_json_locked_success_persists():
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "state.json")
        sm.safe_json_dump(path, {"count": 0})

        def inc(cur):
            cur["count"] += 1
            return cur

        sm.update_json_locked(path, {}, inc)
        sm.update_json_locked(path, {}, inc)
        assert sm.safe_json_load(path)["count"] == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# backup / restore / prune
# ---------------------------------------------------------------------------

def _seed_project(root):
    sm.safe_json_dump(os.path.join(root, "project_state.json"), {"v": 1})
    sm.safe_json_dump(os.path.join(root, "thesis_profile.json"), {"degree": "master"})
    atomic = os.path.join(root, "atomic_md", "第1章")
    os.makedirs(atomic, exist_ok=True)
    with open(os.path.join(atomic, "1_引言.md"), "w", encoding="utf-8") as f:
        f.write("原始稿件内容")


def test_backup_then_restore_recovers_changes():
    tmp = tempfile.mkdtemp()
    try:
        _seed_project(tmp)
        snap = sm.backup_project_state(tmp)
        assert os.path.isdir(snap)

        # 破坏性改动
        sm.safe_json_dump(os.path.join(tmp, "project_state.json"), {"v": 999})
        with open(os.path.join(tmp, "atomic_md", "第1章", "1_引言.md"), "w", encoding="utf-8") as f:
            f.write("被误改的内容")

        sm.restore_snapshot(tmp, snap)
        assert sm.safe_json_load(os.path.join(tmp, "project_state.json")) == {"v": 1}
        with open(os.path.join(tmp, "atomic_md", "第1章", "1_引言.md"), encoding="utf-8") as f:
            assert f.read() == "原始稿件内容"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_prune_keeps_latest_n_and_spares_atomic_md():
    tmp = tempfile.mkdtemp()
    try:
        _seed_project(tmp)
        backup_root = os.path.join(tmp, "backups")
        os.makedirs(backup_root, exist_ok=True)
        # 造 5 个快照目录，mtime 递增
        made = []
        for i in range(5):
            d = os.path.join(backup_root, f"snapshot_2026010{i}_000000")
            os.makedirs(d)
            os.utime(d, (1000 + i, 1000 + i))
            made.append(d)

        sm.prune_snapshots(tmp, keep=2)
        remaining = [d for d in glob.glob(os.path.join(backup_root, "snapshot_*")) if os.path.isdir(d)]
        assert len(remaining) == 2, remaining
        # 保留的是最新的两个（mtime 最大）
        assert set(os.path.basename(d) for d in remaining) == {
            os.path.basename(made[4]), os.path.basename(made[3])}
        # 稿件目录不受影响
        assert os.path.isfile(os.path.join(tmp, "atomic_md", "第1章", "1_引言.md"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_json_roundtrip_and_no_tmp_residue()
    print("OK safe_json 往返 + 无 .tmp 残留")
    test_json_load_missing_returns_default()
    print("OK safe_json_load 缺失返回 default 深拷贝")
    test_update_json_locked_mutate_raises_keeps_file_intact()
    print("OK update_json_locked mutate 异常原文件完好")
    test_update_json_locked_success_persists()
    print("OK update_json_locked 成功持久化")
    test_backup_then_restore_recovers_changes()
    print("OK backup→改动→restore 还原")
    test_prune_keeps_latest_n_and_spares_atomic_md()
    print("OK prune 保留最新 N + 不误删 atomic_md")
    print("ALL OK")

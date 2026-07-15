#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
front_matter_renderer.py 回归测试（开发者维护工具，非运行时流程）。

覆盖 managed 文件保护逻辑 _is_managed_file / _write_managed_markdown：
- overwrite=False 且目标已存在的 managed 文件 → 覆盖更新
- 非 managed 的用户文件 → 永不被写（返回 skipped_unmanaged，内容不变）
- overwrite=True → 即便非 managed 也覆盖
- 不存在 → 创建

纯 assert，无框架依赖。缺 python-docx 时打印 SKIP。
用法：python3 test_front_matter_renderer.py
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    import front_matter_renderer as fmr
except Exception as e:
    print(f"SKIP test_front_matter_renderer：导入失败（{e}）")
    sys.exit(0)

MARKER = fmr.MANAGED_MARKER
MANAGED_CONTENT = f"{MARKER}\n\n新内容\n"


def test_is_managed_file():
    tmp = tempfile.mkdtemp()
    try:
        managed = Path(tmp) / "m.md"
        managed.write_text(f"{MARKER}\n内容", encoding="utf-8")
        user = Path(tmp) / "u.md"
        user.write_text("用户手写内容", encoding="utf-8")
        assert fmr._is_managed_file(managed) is True
        assert fmr._is_managed_file(user) is False
        assert fmr._is_managed_file(Path(tmp) / "missing.md") is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_write_creates_when_absent():
    tmp = tempfile.mkdtemp()
    try:
        p = Path(tmp) / "sub" / "front.md"
        status = fmr._write_managed_markdown(p, MANAGED_CONTENT, overwrite=False)
        assert status == "created"
        assert p.read_text(encoding="utf-8") == MANAGED_CONTENT
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_write_updates_existing_managed():
    tmp = tempfile.mkdtemp()
    try:
        p = Path(tmp) / "front.md"
        p.write_text(f"{MARKER}\n\n旧内容\n", encoding="utf-8")
        status = fmr._write_managed_markdown(p, MANAGED_CONTENT, overwrite=False)
        assert status == "updated"
        assert p.read_text(encoding="utf-8") == MANAGED_CONTENT
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_write_never_overwrites_user_file():
    tmp = tempfile.mkdtemp()
    try:
        p = Path(tmp) / "front.md"
        original = "用户手写的珍贵内容"
        p.write_text(original, encoding="utf-8")
        status = fmr._write_managed_markdown(p, MANAGED_CONTENT, overwrite=False)
        assert status == "skipped_unmanaged", status
        # 用户文件内容纹丝不动
        assert p.read_text(encoding="utf-8") == original
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_write_overwrite_true_forces_user_file():
    tmp = tempfile.mkdtemp()
    try:
        p = Path(tmp) / "front.md"
        p.write_text("用户内容", encoding="utf-8")
        status = fmr._write_managed_markdown(p, MANAGED_CONTENT, overwrite=True)
        assert status == "updated"
        assert p.read_text(encoding="utf-8") == MANAGED_CONTENT
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_is_managed_file()
    print("OK _is_managed_file")
    test_write_creates_when_absent()
    print("OK 不存在→created")
    test_write_updates_existing_managed()
    print("OK managed 文件→updated")
    test_write_never_overwrites_user_file()
    print("OK 非 managed 用户文件→skipped_unmanaged 不被写")
    test_write_overwrite_true_forces_user_file()
    print("OK overwrite=True 强制覆盖")
    print("ALL OK")

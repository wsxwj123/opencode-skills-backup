#!/usr/bin/env python3
"""凭据持久化自测：解析优先级 + chmod 位。无 fixture 框架，纯 assert。"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import zotero_manager as zm


def test_save_sets_perms_and_content(tmp_path):
    p = tmp_path / "sub" / "zotero.json"
    zm.save_credentials("111", "SECRETKEY", path=p)
    # 文件 600、目录 700
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(p.parent).st_mode) == 0o700
    cfg = zm.load_credentials(p)
    assert cfg == {"library_id": "111", "api_key": "SECRETKEY", "library_type": "user"}


def test_resolve_priority(tmp_path, monkeypatch):
    fake = tmp_path / "zotero.json"
    zm.save_credentials("CFG_ID", "CFG_KEY", path=fake)
    monkeypatch.setattr(zm, "CREDENTIALS_PATH", fake)

    # CLI 优先于 config
    assert zm.resolve_credentials("CLI_ID", "CLI_KEY") == ("CLI_ID", "CLI_KEY")
    # 只有部分 CLI 时回落 config 补齐
    assert zm.resolve_credentials("CLI_ID", None) == ("CLI_ID", "CFG_KEY")
    # 无 CLI 时全用 config
    assert zm.resolve_credentials(None, None) == ("CFG_ID", "CFG_KEY")


def test_mask_never_full():
    assert zm._mask("ABCD1234") == "****1234"
    assert zm._mask("ab") == "****"


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_save_sets_perms_and_content(Path(d) / "a")
    # 手动 monkeypatch 替身
    class _M:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    with tempfile.TemporaryDirectory() as d:
        test_resolve_priority(Path(d), _M())
    test_mask_never_full()
    print("OK: 凭据解析优先级 + chmod 位 + 脱敏 均通过")

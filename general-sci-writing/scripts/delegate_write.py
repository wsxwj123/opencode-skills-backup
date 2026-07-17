#!/usr/bin/env python3
# delegate_write.py —— general-sci-writing 撰写编排入口（薄封装：import 本家 vendored 共享核心）
#
# 逻辑全在 delegate_write_core.py（四家逐字节一致，L4 md5 守卫）。本文件只声明 gsw
# 的账本映射 config：本节文献切片来自 literature_matrix.json（section→refs 映射表）。
#
# gsw 适配（本家私有，不进共享核心）：gsw storyline 的小节键在 `id`（如 results_3.1），
# 而共享核心按 `section_id` 找节。开写打包前，从 storyline.json 机械派生一份带 section_id
# 的只读大纲 sidecar（.orch_outline.json，每次重生保证不陈旧），config 优先读它。这样既不
# 改共享核心、也不迁移 gsw 数据模型。storyline 仍是唯一真源。

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delegate_write_core import (  # noqa: E402
    BARE_NUM_RE, KEY_RE, SECTION_RE, main,
)

__all__ = ["BARE_NUM_RE", "KEY_RE", "SECTION_RE", "CONFIG", "main"]

CONFIG = {
    "family": "general-sci-writing",
    # gsw 小节 id：introduction / methods / discussion / conclusion（纯词）与 results_3.1
    # （词_点分号）并存，故不强制含数字。首字符字母，其后字母/数字/下划线/点。
    "section_regex": r"^[A-Za-z][A-Za-z0-9_.]*$",
    # gsw 大纲：优先读派生 sidecar（带 section_id），回退 storyline.json 原文。
    "outline_files": [".orch_outline.json", "storyline.json"],
    # 本节文献切片：literature_matrix.json，section→refs 映射表，按本 section 切（§7）
    "lit_section": {"mode": "matrix_map", "file": "literature_matrix.json"},
}


def _sync_outline_sidecar(root):
    """从 storyline.json 派生 .orch_outline.json：把每节 `id` 补成 `section_id`。

    共享核心只认 section_id；gsw storyline 用 id。机械补齐，不改真源、不迁数据。
    storyline 缺/畸形 → 静默跳过（核心随后报 outline has no section，契约不变）。
    """
    sp = os.path.join(root, "storyline.json")
    if not os.path.isfile(sp):
        return
    try:
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return
    secs = data.get("sections") if isinstance(data, dict) else data
    if not isinstance(secs, list):
        return
    norm = []
    for s in secs:
        if not isinstance(s, dict):
            continue
        sid = s.get("section_id") or s.get("id")
        if not sid:
            continue
        norm.append({**s, "section_id": sid})
    try:
        with open(os.path.join(root, ".orch_outline.json"), "w", encoding="utf-8") as f:
            json.dump({"sections": norm}, f, ensure_ascii=False)
    except OSError:
        pass


def _root_from_argv(argv):
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


if __name__ == "__main__":
    # pack-write / pack-prep 需大纲——先刷新 sidecar 再交共享核心。
    if len(sys.argv) > 1 and sys.argv[1] in ("pack-write", "pack-prep"):
        root = _root_from_argv(sys.argv)
        if root and os.path.isdir(root):
            _sync_outline_sidecar(root)
    main(CONFIG)

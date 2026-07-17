#!/usr/bin/env python3
# delegate_write.py —— review-writing 撰写编排入口（薄封装：import 本家 vendored 共享核心）
#
# 逻辑全在 delegate_write_core.py（四家逐字节一致，L4 md5 守卫）。本文件只声明 rw
# 的账本映射 config：本节文献切片来自 synthesis_matrix.json，按 related_sections 含本 section 切。

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delegate_write_core import (  # noqa: E402
    BARE_NUM_RE, KEY_RE, SECTION_RE, main,
)

__all__ = ["BARE_NUM_RE", "KEY_RE", "SECTION_RE", "CONFIG", "main"]

CONFIG = {
    "family": "review-writing",
    "section_regex": r"^\d+(\.\d+)*$",
    "outline_files": ["project_state.json", "storyline.json"],
    # 本节文献切片：synthesis_matrix.json 按 related_sections 含本 section 切（行键 gid，§7）
    "lit_section": {"mode": "matrix_related", "file": "synthesis_matrix.json"},
}


if __name__ == "__main__":
    main(CONFIG)

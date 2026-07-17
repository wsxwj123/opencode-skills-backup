#!/usr/bin/env python3
# delegate_write.py —— general-sci-writing 撰写编排入口（薄封装：import 本家 vendored 共享核心）
#
# 逻辑全在 delegate_write_core.py（四家逐字节一致，L4 md5 守卫）。本文件只声明 gsw
# 的账本映射 config：本节文献切片来自 literature_matrix.json（section→refs 映射表）。

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delegate_write_core import (  # noqa: E402
    BARE_NUM_RE, KEY_RE, SECTION_RE, main,
)

__all__ = ["BARE_NUM_RE", "KEY_RE", "SECTION_RE", "CONFIG", "main"]

CONFIG = {
    "family": "general-sci-writing",
    "section_regex": r"^[A-Za-z_]*\d+(\.\d+)*$",  # results_3.1 / 3.1 皆可
    "outline_files": ["project_state.json", "storyline.json"],
    # 本节文献切片：literature_matrix.json，section→refs 映射表，按本 section 切（§7）
    "lit_section": {"mode": "matrix_map", "file": "literature_matrix.json"},
}


if __name__ == "__main__":
    main(CONFIG)

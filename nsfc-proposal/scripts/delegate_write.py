#!/usr/bin/env python3
# delegate_write.py —— nsfc-proposal 撰写编排入口（薄封装：import 本家 vendored 共享核心）
#
# 逻辑全在 delegate_write_core.py（四家逐字节一致，L4 md5 守卫）。本文件只声明 nsfc
# 的账本映射 config：section 形态 P1..P7；本节文献切片无独立矩阵，
# 走 literature_index.entries[].used_in_sections 含本 PX 过滤（§7）。

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delegate_write_core import (  # noqa: E402
    BARE_NUM_RE, KEY_RE, SECTION_RE, main,
)

__all__ = ["BARE_NUM_RE", "KEY_RE", "SECTION_RE", "CONFIG", "main"]

CONFIG = {
    "family": "nsfc-proposal",
    "section_regex": r"^P\d+(\.\d+)*$",  # P1 / P2.3 等
    "outline_files": ["project_state.json", "storyline.json"],
    # 无独立矩阵：used_in_sections 含本 PX 过滤（§7）
    "lit_section": {"mode": "index_used_in", "file": None},
}


if __name__ == "__main__":
    main(CONFIG)

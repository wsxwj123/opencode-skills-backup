#!/usr/bin/env python3
"""回归测试：word_counter.py 的 count_text 计数公式 + estimate_pages 边界。

自包含、纯 assert、纯内存。计数公式=中文字数 + 英文/数字词块数 + 句内标点数。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import word_counter as w  # noqa: E402


def test_count_text() -> None:
    # 你好(2汉字) + abc/123(2词块) + ,。(2标点) = 6
    assert w.count_text("你好abc,123。") == 6, w.count_text("你好abc,123。")
    assert w.count_text("") == 0
    # 纯中文 4 字（空白不计）
    assert w.count_text("研究 内容") == 4, w.count_text("研究 内容")
    print("count_text 汉字+词块+标点公式：OK")


def test_estimate_pages() -> None:
    # 每页 800 字；0 或负 → 0；否则 ceil
    assert w.estimate_pages(0) == 0
    assert w.estimate_pages(1) == 1
    assert w.estimate_pages(800) == 1
    assert w.estimate_pages(801) == 2
    assert w.estimate_pages(1600) == 2
    print("estimate_pages 边界 0/1/800/801：OK")


if __name__ == "__main__":
    test_count_text()
    test_estimate_pages()
    print("ALL PASS")

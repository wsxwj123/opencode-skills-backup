#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据引句 ∈ 原文 的逐字比对（防捏造防线）。

用法：
  python3 verify_evidence.py <原文文件|-> [引句1] [引句2] ...
  <原文文件> 传 "-" 时原文从 stdin 读取；未给引句时引句从 stdin 逐行读入。

比对前归一化空白（换行/多空格/全角空格→单空格）；首尾标点边界放宽
（先精确匹配，失败再去首尾标点重试）。逐句输出 PASS/FAIL，全过退出0。
"""
import re
import sys

BOUNDARY = "“”‘’\"'，。！？、；：（）《》〈〉…—· "


def normalize(s):
    # 中文比对：引句通常不带空格而原文（尤其OCR）常带空格，故去除全部空白；
    # 同时归一化引号族（弯引号/直引号/单双引号互换），避免模型引述用弯引号而原文是直引号导致误报。
    s = re.sub(r"\s+", "", s)
    s = s.replace("“", '"').replace("”", '"')  # “ ” → "
    s = s.replace("‘", "'").replace("’", "'")  # ‘ ’ → '
    return s


def main():
    if len(sys.argv) < 2:
        print("用法：python3 verify_evidence.py <原文文件|-> [引句...]")
        sys.exit(2)
    if sys.argv[1] == "-":
        essay = normalize(sys.stdin.read())
    else:
        with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
            essay = normalize(f.read())
    quotes = sys.argv[2:] if len(sys.argv) > 2 else [l for l in sys.stdin if l.strip()]
    if not quotes:
        print("（无引句需要比对）")
        sys.exit(0)
    ok = True
    for q in quotes:
        hit = normalize(q) in essay
        if not hit:
            core = normalize(q).strip(BOUNDARY)
            if core:
                hit = core in essay
        print(f"{'PASS' if hit else 'FAIL'}: {q}")
        ok = ok and hit
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

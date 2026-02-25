#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享工具函数

避免 heading_level / classify_heading / normalize_text / infer_project_root_for_profile
在多个脚本中重复定义。
"""

import os
import re


def normalize_text(value):
    """标准化标题文本用于匹配。"""
    return re.sub(r"\s+", "", (value or "").lower())


def heading_level(style_name):
    """
    解析 Heading 样式级别；非标题返回 None。
    """
    if not style_name:
        return None
    m = re.match(r"^(?:Heading|标题)\s*(\d+)$", style_name, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def classify_heading(text):
    """
    根据标题文本分类章节类型。

    Returns:
        str: body | review | references | toc | abstract | acknowledgement | appendix
    """
    t = normalize_text(text)
    if not t:
        return "body"

    chapter_prefix_cn = r"(第[一二三四五六七八九十百千万0-9]+章)?"
    chapter_prefix_en = r"(chapter[0-9ivxlcdm]+)?"
    patterns = {
        "review": [
            rf"^{chapter_prefix_cn}综述$",
            rf"^{chapter_prefix_cn}文献综述$",
            rf"^{chapter_prefix_en}literaturereview$",
        ],
        "references": [
            rf"^{chapter_prefix_cn}参考文献$",
            rf"^{chapter_prefix_en}references$",
        ],
        "toc": [r"^目录$", r"tableofcontents", r"^contents$"],
        "abstract": [
            rf"^{chapter_prefix_cn}(中文|英文)?摘要$",
            rf"^{chapter_prefix_en}abstract$",
        ],
        "acknowledgement": [
            rf"^{chapter_prefix_cn}致谢$",
            rf"^{chapter_prefix_en}acknowledg(e)?ment$",
        ],
        "appendix": [
            rf"^{chapter_prefix_cn}附录$",
            rf"^{chapter_prefix_en}appendix$",
        ],
    }
    for section_type, regex_list in patterns.items():
        for regex in regex_list:
            if re.search(regex, t):
                return section_type
    return "body"


def infer_project_root_for_profile(docx_path):
    """
    从 docx 路径向上查找 thesis_profile.json，找到后返回其所在目录。
    找不到时返回 docx 所在目录，保持向后兼容。
    """
    current = os.path.abspath(os.path.dirname(docx_path))
    while True:
        candidate = os.path.join(current, "thesis_profile.json")
        if os.path.exists(candidate):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(os.path.dirname(docx_path))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
博士论文质量自检工具

功能：
1. 检查字数是否达标
2. 检查格式是否规范
3. 检查图表编号是否连续
4. 检查是否有列表项（应为段落）
5. 生成质量报告

作者：Sci2Doc Team
日期：2024-03-15
"""

from docx import Document
import argparse
import sys
import os
import re
import json
from datetime import datetime

try:
    from thesis_profile import load_profile
except Exception:  # pragma: no cover
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from thesis_profile import load_profile


def normalize_text(value):
    return re.sub(r"\s+", "", (value or "").lower())


def heading_level(style_name):
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


def line_spacing_pt(paragraph):
    value = paragraph.paragraph_format.line_spacing
    if value is None:
        return None
    if hasattr(value, "pt"):
        return float(value.pt)
    if isinstance(value, (int, float)):
        if value > 1000:
            return float(value) / 12700.0
        return float(value)
    return None


def check_word_count(doc, body_target_chars=80000, review_target_chars=0, review_in_scope=False):
    """检查字数是否达标"""
    issues = []
    
    total_chinese = 0
    review_chinese = 0
    current_section_type = "body"
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        lvl = heading_level(getattr(para.style, "name", ""))
        if lvl is not None:
            current_section_type = classify_heading(text)
            continue

        chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if current_section_type == "review":
            review_chinese += chars
        elif current_section_type in {"references", "toc", "abstract", "acknowledgement", "appendix"}:
            continue
        else:
            total_chinese += chars
    
    # 检查正文字数
    body_target_chars = max(1, int(body_target_chars or 80000))
    review_target_chars = max(0, int(review_target_chars or 0))

    if total_chinese < body_target_chars:
        issues.append({
            'level': 'error',
            'category': '字数',
            'message': f'正文字数不足：{total_chinese} / {body_target_chars:,} 字',
            'suggestion': f'需要扩展内容以达到 {body_target_chars:,} 字要求'
        })
    
    # 检查综述字数
    if review_in_scope and review_target_chars > 0 and review_chinese > 0 and review_chinese < review_target_chars:
        issues.append({
            'level': 'warning',
            'category': '字数',
            'message': f'综述字数不足：{review_chinese} / {review_target_chars:,} 字',
            'suggestion': f'建议扩展综述部分至 {review_target_chars:,} 字以上'
        })
    
    return issues, {
        'body_words': total_chinese,
        'review_words': review_chinese,
        'body_target_chars': body_target_chars,
        'review_target_chars': review_target_chars,
        'review_in_scope': bool(review_in_scope),
    }


def check_heading_levels(doc):
    """检查标题层级是否规范"""
    issues = []
    prev_level = 0
    
    for i, para in enumerate(doc.paragraphs):
        level = heading_level(getattr(para.style, "name", ""))
        if level is not None:
            
            # 检查是否超过三级
            if level > 3:
                issues.append({
                    'level': 'error',
                    'category': '标题层级',
                    'location': f'第 {i+1} 段',
                    'message': f'标题层级过深：{level} 级（{para.text[:30]}...）',
                    'suggestion': '中南大学要求标题最多三级'
                })
            
            # 检查是否跳级（如 1 → 3）
            if level - prev_level > 1:
                issues.append({
                    'level': 'warning',
                    'category': '标题层级',
                    'location': f'第 {i+1} 段',
                    'message': f'标题层级跳跃：从 {prev_level} 级跳到 {level} 级',
                    'suggestion': '建议按顺序设置标题层级'
                })
            
            prev_level = level
    
    return issues


def check_figure_numbering(doc):
    """检查图表编号是否连续规范"""
    issues = []
    
    # 匹配图编号：图 1-1, 图 2-3 等
    figure_pattern = re.compile(r'图\s*(\d+)-(\d+)')
    table_pattern = re.compile(r'表\s*(\d+)-(\d+)')
    
    figures = []
    tables = []
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text
        
        # 查找图编号
        for match in figure_pattern.finditer(text):
            chapter = int(match.group(1))
            number = int(match.group(2))
            figures.append({
                'chapter': chapter,
                'number': number,
                'location': i + 1,
                'text': text[:50]
            })
        
        # 查找表编号
        for match in table_pattern.finditer(text):
            chapter = int(match.group(1))
            number = int(match.group(2))
            tables.append({
                'chapter': chapter,
                'number': number,
                'location': i + 1,
                'text': text[:50]
            })
    
    # 检查图编号连续性
    figures_by_chapter = {}
    for fig in figures:
        chapter = fig['chapter']
        if chapter not in figures_by_chapter:
            figures_by_chapter[chapter] = []
        figures_by_chapter[chapter].append(fig)
    
    for chapter, figs in figures_by_chapter.items():
        figs_sorted = sorted(figs, key=lambda x: x['number'])
        for i, fig in enumerate(figs_sorted):
            expected = i + 1
            if fig['number'] != expected:
                issues.append({
                    'level': 'warning',
                    'category': '图表编号',
                    'location': f'第 {fig["location"]} 段',
                    'message': f'第 {chapter} 章图编号不连续：图 {chapter}-{fig["number"]}',
                    'suggestion': f'应为 图 {chapter}-{expected}'
                })
    
    # 检查表编号连续性（同理）
    tables_by_chapter = {}
    for tab in tables:
        chapter = tab['chapter']
        if chapter not in tables_by_chapter:
            tables_by_chapter[chapter] = []
        tables_by_chapter[chapter].append(tab)
    
    for chapter, tabs in tables_by_chapter.items():
        tabs_sorted = sorted(tabs, key=lambda x: x['number'])
        for i, tab in enumerate(tabs_sorted):
            expected = i + 1
            if tab['number'] != expected:
                issues.append({
                    'level': 'warning',
                    'category': '图表编号',
                    'location': f'第 {tab["location"]} 段',
                    'message': f'第 {chapter} 章表编号不连续：表 {chapter}-{tab["number"]}',
                    'suggestion': f'应为 表 {chapter}-{expected}'
                })
    
    return issues


def check_bullet_points(doc):
    """检查是否有列表项（应全部为段落）"""
    issues = []
    
    for i, para in enumerate(doc.paragraphs):
        # 检查是否为列表样式
        if 'List' in para.style.name:
            issues.append({
                'level': 'error',
                'category': '格式',
                'location': f'第 {i+1} 段',
                'message': f'发现列表项：{para.text[:30]}...',
                'suggestion': '论文要求段落式写作，不允许使用列表项'
            })
        
        # 检查是否有列表标记（简单检测）
        text = para.text.strip()
        if text and (
            text.startswith('• ') or
            text.startswith('- ') or
            text.startswith('* ') or
            re.match(r'^\d+\.\s', text) or
            re.match(r'^\(\d+\)\s', text)
        ):
            issues.append({
                'level': 'warning',
                'category': '格式',
                'location': f'第 {i+1} 段',
                'message': f'疑似列表项：{text[:30]}...',
                'suggestion': '请确认是否为列表项，如是请改为段落形式'
            })
    
    return issues


def check_reference_count(doc, min_reference_count=80):
    """检查参考文献数量"""
    issues = []
    
    # 查找参考文献章节
    in_references = False
    ref_count = 0
    
    for para in doc.paragraphs:
        text = para.text.strip()

        if not text:
            continue

        lvl = heading_level(getattr(para.style, "name", ""))
        if lvl is not None:
            if classify_heading(text) == "references":
                in_references = True
            elif in_references:
                # 下一标题即离开参考文献章节
                in_references = False
            continue

        if in_references:
            # 匹配 [1], [2] 等编号
            if re.match(r'^\[\d+\]', text) or re.match(r'^\d+\.\s', text):
                ref_count += 1
    
    min_reference_count = int(min_reference_count if min_reference_count is not None else 80)
    if min_reference_count <= 0:
        return issues, ref_count
    if ref_count < min_reference_count:
        issues.append({
            'level': 'error',
            'category': '参考文献',
            'message': f'参考文献数量不足：{ref_count} / {min_reference_count} 篇',
            'suggestion': f'当前配置要求参考文献不少于 {min_reference_count} 篇'
        })
    
    return issues, ref_count


def is_chapter_heading_text(text):
    t = (text or "").strip()
    return bool(re.match(r"^第[一二三四五六七八九十百千万零〇0-9]+章", t))


def check_reference_position(doc):
    """
    校验参考文献位置：
    1) 全文应只有一个参考文献标题
    2) 参考文献后不能再出现“第X章”正文章节标题
    """
    issues = []
    heading_items = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        lvl = heading_level(getattr(para.style, "name", ""))
        if lvl is None:
            continue
        heading_items.append((i, text, classify_heading(text)))

    ref_headings = [(idx, text) for idx, text, kind in heading_items if kind == "references"]
    if len(ref_headings) > 1:
        issues.append({
            'level': 'error',
            'category': '参考文献位置',
            'message': f'检测到多个参考文献标题：{len(ref_headings)} 处',
            'suggestion': '参考文献应全书统一放置，且仅保留一个参考文献章节'
        })
        return issues

    if len(ref_headings) == 1:
        ref_idx, _ = ref_headings[0]
        for idx, text, _kind in heading_items:
            if idx <= ref_idx:
                continue
            if is_chapter_heading_text(text):
                issues.append({
                    'level': 'error',
                    'category': '参考文献位置',
                    'location': f'第 {idx+1} 段',
                    'message': f'参考文献后出现章节标题：{text}',
                    'suggestion': '参考文献应位于正文章节之后，不能再进入新的“第X章”章节'
                })
                break

    return issues


# ---------------------------------------------------------------------------
# 正文内联引用格式检测
# ---------------------------------------------------------------------------

# 合法引用格式：[6] [6,7] [6-8] [6,7,9] [6-8,10] 等
_VALID_CITATION_RE = re.compile(
    r'\[(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]'
)

# 宽松匹配：任何 [ 数字... ] 形态（用于发现格式错误的引用）
_LOOSE_CITATION_RE = re.compile(
    r'\[[\d,\-–\s]+\]'
)

# 不合法的常见错误模式
_BAD_CITATION_PATTERNS = [
    # 缺少逗号：[6 7]
    (re.compile(r'\[\d+\s+\d+\]'), '引用编号之间缺少逗号，应为 [X,Y] 格式'),
    # 中文逗号：[6，7]
    (re.compile(r'\[\d+\s*，\s*\d+'), '引用中使用了中文逗号，应使用英文逗号'),
    # 中文括号：（6）或【6】
    (re.compile(r'[（【]\d+(?:\s*[,，\-–]\s*\d+)*[）】]'), '引用使用了中文括号，应使用英文方括号 [X]'),
    # 上标格式残留：^[6] 或 <sup>[6]</sup>
    (re.compile(r'\^\[\d+'), '引用不应使用 markdown 上标语法'),
]


def check_inline_citations(doc):
    """
    检测正文中内联引用格式是否规范。

    合法格式：[6] [6,7] [6-8] [6,7,9-11]
    检测问题：
    - 格式错误的引用（中文逗号、缺逗号、中文括号等）
    - 引用编号不连续或逆序（如 [8,3]）
    - 引用编号超出参考文献范围（需配合 ref_count 使用）
    """
    issues = []
    in_references = False
    in_abstract = False
    para_idx = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        lvl = heading_level(getattr(para.style, "name", ""))
        if lvl is not None:
            cls = classify_heading(text)
            if cls == "references":
                in_references = True
            elif in_references:
                in_references = False
            in_abstract = "摘要" in text or "abstract" in text.lower()
            continue

        # 跳过参考文献区域和摘要
        if in_references or in_abstract:
            continue

        para_idx += 1

        # 1) 检测错误格式
        for bad_re, msg in _BAD_CITATION_PATTERNS:
            for m in bad_re.finditer(text):
                snippet = text[max(0, m.start() - 10):m.end() + 10]
                issues.append({
                    'level': 'error',
                    'category': '引用格式',
                    'message': f'{msg}：...{snippet}...',
                    'suggestion': '正文引用应使用英文方括号+英文逗号，如 [1,2] [3-5]'
                })

        # 2) 检测合法引用中的编号问题
        for m in _VALID_CITATION_RE.finditer(text):
            inner = m.group(1)
            # 解析所有编号
            nums = []
            for part in re.split(r'\s*,\s*', inner):
                range_match = re.match(r'(\d+)\s*[-–]\s*(\d+)', part)
                if range_match:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    if start >= end:
                        issues.append({
                            'level': 'error',
                            'category': '引用格式',
                            'message': f'引用范围逆序：[{inner}]，起始编号应小于结束编号',
                            'suggestion': f'应为 [{end}-{start}] 或拆分为独立编号'
                        })
                    nums.extend(range(start, end + 1))
                else:
                    nums.append(int(part.strip()))

            # 检查是否非递增（允许相等，不允许逆序）
            if len(nums) >= 2:
                for i in range(1, len(nums)):
                    if nums[i] < nums[i - 1]:
                        issues.append({
                            'level': 'warning',
                            'category': '引用格式',
                            'message': f'引用编号未按升序排列：[{inner}]',
                            'suggestion': '多引用应按编号升序排列，如 [3,5,7] 而非 [7,3,5]'
                        })
                        break

    return issues


def check_full_thesis_structure(doc, min_chapters=5):
    """
    全文结构门禁：
    1) 章节数不少于 min_chapters
    2) 第一章应为绪论/引言
    3) 最后一章应为总结/结论/展望类独立章节
    """
    issues = []
    chapter_titles = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        lvl = heading_level(getattr(para.style, "name", ""))
        if lvl is None:
            continue
        if is_chapter_heading_text(text):
            chapter_titles.append(text)

    min_chapters = max(1, int(min_chapters or 5))
    if len(chapter_titles) < min_chapters:
        issues.append({
            'level': 'error',
            'category': '结构',
            'message': f'章节数不足：{len(chapter_titles)} / {min_chapters}',
            'suggestion': f'需满足“独立绪论 + 多个研究章 + 独立总结章”，总章节数不少于 {min_chapters}'
        })
        return issues

    first_title = chapter_titles[0]
    first_norm = normalize_text(first_title)
    if ("绪论" not in first_norm) and ("引言" not in first_norm):
        issues.append({
            'level': 'error',
            'category': '结构',
            'message': f'第一章标题不符合绪论要求：{first_title}',
            'suggestion': '第一章应设置为“绪论”或“引言”性质章节'
        })

    last_title = chapter_titles[-1]
    last_norm = normalize_text(last_title)
    if not any(k in last_norm for k in ("结论", "总结", "小结", "展望")):
        issues.append({
            'level': 'error',
            'category': '结构',
            'message': f'最后一章标题不符合独立总结章要求：{last_title}',
            'suggestion': '最后一章应为独立总结/结论/展望章节'
        })

    if len(chapter_titles) >= 2:
        research_chapter_count = len(chapter_titles) - 2
        if research_chapter_count <= 0:
            issues.append({
                'level': 'error',
                'category': '结构',
                'message': '研究章节数量不足',
                'suggestion': '应保留“独立绪论章 + 多个研究章 + 独立总结章”组织形式'
            })

    return issues


def check_paragraph_formatting(doc):
    """检查段落格式是否规范"""
    issues = []
    
    for i, para in enumerate(doc.paragraphs):
        if not para.text.strip():
            continue
        
        # 跳过标题
        if heading_level(getattr(para.style, "name", "")) is not None:
            continue
        
        # 检查首行缩进（正文应有首行缩进）
        if para.style.name == 'Normal':
            if not para.paragraph_format.first_line_indent:
                issues.append({
                    'level': 'info',
                    'category': '格式',
                    'location': f'第 {i+1} 段',
                    'message': '正文段落缺少首行缩进',
                    'suggestion': '正文段落应设置首行缩进 2 字符'
                })
        
        # 检查行距（应为 20 磅）
        spacing_pt = line_spacing_pt(para)
        if spacing_pt is not None:
            if abs(spacing_pt - 20.0) > 0.5:
                issues.append({
                    'level': 'info',
                    'category': '格式',
                    'location': f'第 {i+1} 段',
                    'message': f'行距不符合要求：{spacing_pt:.2f} 磅',
                    'suggestion': '正文行距应设置为固定值 20 磅'
                })
    
    return issues


def generate_quality_report(
    docx_path,
    verbose=True,
    body_target_chars=80000,
    review_target_chars=0,
    review_in_scope=False,
    references_min_count=80,
    min_chapters=5,
    enforce_full_structure=False,
):
    """生成完整质量报告"""
    try:
        doc = Document(docx_path)
    except Exception as e:
        return {
            'success': False,
            'error': f'无法打开文件：{str(e)}'
        }
    
    all_issues = []
    
    # 1. 检查字数
    if verbose:
        print("🔍 检查字数...")
    word_issues, word_stats = check_word_count(
        doc,
        body_target_chars=body_target_chars,
        review_target_chars=review_target_chars,
        review_in_scope=review_in_scope,
    )
    all_issues.extend(word_issues)
    
    # 2. 检查标题层级
    if verbose:
        print("🔍 检查标题层级...")
    heading_issues = check_heading_levels(doc)
    all_issues.extend(heading_issues)
    
    # 3. 检查图表编号
    if verbose:
        print("🔍 检查图表编号...")
    numbering_issues = check_figure_numbering(doc)
    all_issues.extend(numbering_issues)
    
    # 4. 检查列表项
    if verbose:
        print("🔍 检查列表项...")
    bullet_issues = check_bullet_points(doc)
    all_issues.extend(bullet_issues)
    
    # 5. 检查参考文献
    if verbose:
        print("🔍 检查参考文献...")
    ref_issues, ref_count = check_reference_count(doc, min_reference_count=references_min_count)
    all_issues.extend(ref_issues)

    # 5.1 参考文献位置校验
    reference_position_issues = check_reference_position(doc)
    all_issues.extend(reference_position_issues)

    # 5.2 正文内联引用格式检测
    if verbose:
        print("🔍 检查正文引用格式...")
    citation_issues = check_inline_citations(doc)
    all_issues.extend(citation_issues)

    # 5.2 全文结构门禁（仅在全文检查时启用）
    if enforce_full_structure:
        if verbose:
            print("🔍 检查全文结构门禁...")
        structure_issues = check_full_thesis_structure(doc, min_chapters=min_chapters)
        all_issues.extend(structure_issues)
    
    # 6. 检查段落格式
    if verbose:
        print("🔍 检查段落格式...")
    format_issues = check_paragraph_formatting(doc)
    all_issues.extend(format_issues)
    
    # 计算总分（简化评分）
    error_count = len([i for i in all_issues if i['level'] == 'error'])
    warning_count = len([i for i in all_issues if i['level'] == 'warning'])
    info_count = len([i for i in all_issues if i['level'] == 'info'])
    
    total_score = 100 - error_count * 10 - warning_count * 3 - info_count * 1
    total_score = max(0, min(100, total_score))
    
    report = {
        'success': True,
        'file_path': docx_path,
        'check_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'overall_score': total_score,
        'statistics': {
            'body_words': word_stats['body_words'],
            'review_words': word_stats['review_words'],
            'reference_count': ref_count,
            'reference_target_count': int(references_min_count),
            'total_paragraphs': len(doc.paragraphs),
            'total_tables': len(doc.tables)
        },
        'issue_summary': {
            'total': len(all_issues),
            'error': error_count,
            'warning': warning_count,
            'info': info_count
        },
        'issues': all_issues,
        'targets': {
            'body_target_chars': int(body_target_chars),
            'review_target_chars': int(review_target_chars),
            'review_in_scope': bool(review_in_scope),
            'references_min_count': int(references_min_count),
            'min_chapters': int(min_chapters),
            'enforce_full_structure': bool(enforce_full_structure),
        },
        'recommendations': generate_recommendations(all_issues, word_stats)
    }
    
    return report


def generate_recommendations(issues, word_stats):
    """根据检查结果生成建议"""
    recommendations = []
    
    # 字数建议
    body_target = int(word_stats.get('body_target_chars', 80000) or 80000)
    if word_stats['body_words'] < body_target:
        gap = body_target - word_stats['body_words']
        recommendations.append(
            f"正文字数不足 {gap} 字，建议扩展以下内容：\n"
            "  - 增加机制讨论（从分子、细胞、体内三个层面）\n"
            "  - 补充文献对比分析\n"
            "  - 增加局限性讨论和未来展望"
        )
    
    # 错误处理建议
    errors = [i for i in issues if i['level'] == 'error']
    if errors:
        recommendations.append(
            f"发现 {len(errors)} 个严重错误，必须修正：\n" +
            "\n".join(f"  - {e['message']}" for e in errors[:3])
        )

    reference_errors = [i for i in errors if i.get('category') == '参考文献']
    if reference_errors:
        recommendations.append(
            "参考文献未达配置下限，建议补充近5年高质量文献并统一格式（GB/T 7714 或学校模板）。"
        )
    
    # 格式建议
    format_issues = [i for i in issues if i['category'] == '格式']
    if len(format_issues) > 5:
        recommendations.append(
            "格式问题较多，建议：\n"
            "  - 使用样式模板统一格式\n"
            "  - 检查所有段落的首行缩进和行距"
        )
    
    if not recommendations:
        recommendations.append("论文质量良好，符合基本要求！")
    
    return recommendations


def format_report_text(report):
    """格式化报告为可读文本"""
    lines = []
    lines.append("=" * 70)
    lines.append("📋 博士论文质量检查报告")
    lines.append("=" * 70)
    lines.append(f"📄 文件：{os.path.basename(report['file_path'])}")
    lines.append(f"📅 检查时间：{report['check_date']}")
    lines.append(f"⭐ 总体评分：{report['overall_score']} / 100")
    lines.append("")
    
    # 统计信息
    stats = report['statistics']
    targets = report.get('targets', {})
    body_target = int(targets.get('body_target_chars', stats.get('body_target_chars', 80000)) or 80000)
    review_target = int(targets.get('review_target_chars', stats.get('review_target_chars', 0)) or 0)
    review_in_scope = bool(targets.get('review_in_scope', stats.get('review_in_scope', False)))
    references_min_count = int(
        targets.get('references_min_count', stats.get('reference_target_count', 80)) or 80
    )
    min_chapters = int(targets.get('min_chapters', 5) or 5)
    enforce_full_structure = bool(targets.get('enforce_full_structure', False))
    lines.append("📊 统计信息：")
    lines.append(f"   正文字数：{stats['body_words']:,} / {body_target:,}")
    if review_in_scope and review_target > 0:
        lines.append(f"   综述字数：{stats['review_words']:,} / {review_target:,}")
    else:
        lines.append(f"   综述字数：{stats['review_words']:,}（不纳入当前考核）")
    if references_min_count > 0:
        lines.append(f"   参考文献：{stats['reference_count']} / {references_min_count}")
    else:
        lines.append(f"   参考文献：{stats['reference_count']}（当前未纳入阈值检查）")
    if enforce_full_structure:
        lines.append(f"   全文结构门禁：启用（最少章节 {min_chapters}）")
    else:
        lines.append("   全文结构门禁：未启用")
    lines.append(f"   总段落数：{stats['total_paragraphs']:,}")
    lines.append(f"   总表格数：{stats['total_tables']}")
    lines.append("")
    
    # 问题汇总
    summary = report['issue_summary']
    lines.append("⚠️  问题汇总：")
    lines.append(f"   严重错误：{summary['error']} 个")
    lines.append(f"   警告：{summary['warning']} 个")
    lines.append(f"   提示：{summary['info']} 个")
    lines.append("")
    
    # 详细问题列表
    if report['issues']:
        lines.append("📝 详细问题：")
        for i, issue in enumerate(report['issues'][:20], 1):  # 只显示前 20 个
            level_icon = {
                'error': '❌',
                'warning': '⚠️ ',
                'info': 'ℹ️ '
            }.get(issue['level'], '•')
            
            location = issue.get('location', '')
            location_str = f" [{location}]" if location else ""
            
            lines.append(f"{i}. {level_icon} {issue['message']}{location_str}")
            lines.append(f"   💡 {issue['suggestion']}")
            lines.append("")
        
        if len(report['issues']) > 20:
            lines.append(f"   ... 还有 {len(report['issues']) - 20} 个问题未显示")
            lines.append("")
    
    # 建议
    lines.append("💡 改进建议：")
    for i, rec in enumerate(report['recommendations'], 1):
        lines.append(f"{i}. {rec}")
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


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


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="博士论文质量自检工具")
    parser.add_argument("docx_path", help="待检查的 docx 文件路径")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--profile", help="thesis_profile.json 路径（可选）")
    parser.add_argument("--body-target", type=int, help="覆盖正文目标字数")
    parser.add_argument("--review-target", type=int, help="覆盖综述目标字数")
    parser.add_argument("--review-in-scope", action="store_true", help="将综述纳入考核目标")
    parser.add_argument("--references-min", type=int, help="覆盖最少参考文献数量")
    parser.add_argument("--min-chapters", type=int, help="覆盖最少章节数（全文结构门禁）")
    parser.add_argument("--enforce-full-structure", action="store_true", help="启用全文结构门禁（章数/首章绪论/末章总结）")
    args = parser.parse_args()
    docx_path = args.docx_path
    output_format = args.output
    
    if not os.path.exists(docx_path):
        if output_format == 'json':
            print(json.dumps({
                "success": False,
                "error": "file_not_found",
                "file_path": docx_path,
                "message": f"文件不存在：{docx_path}",
            }, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 文件不存在：{docx_path}")
        sys.exit(1)
    
    verbose = output_format != 'json'
    if verbose:
        print("🔍 开始质量检查...\n")

    profile_project_root = infer_project_root_for_profile(docx_path)
    try:
        profile, _ = load_profile(profile_project_root, args.profile)
    except Exception as e:
        payload = {
            "success": False,
            "error": "profile_load_failed",
            "message": str(e),
            "profile_path": args.profile,
        }
        if output_format == 'json':
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 配置加载失败：{payload['message']}")
        sys.exit(1)
    targets = profile.get("targets", {}) if isinstance(profile, dict) else {}
    body_target = int(args.body_target if args.body_target is not None else targets.get("body_target_chars", 80000))
    review_in_scope = bool(args.review_in_scope or targets.get("review_in_scope", False))
    review_target = int(args.review_target if args.review_target is not None else targets.get("review_target_chars", 0))
    references_min_count = int(
        args.references_min if args.references_min is not None else targets.get("references_min_count", 80)
    )
    min_chapters = int(args.min_chapters if args.min_chapters is not None else targets.get("min_chapters", 5))
    enforce_full_structure = bool(args.enforce_full_structure or ("完整博士论文" in os.path.basename(docx_path)))
    
    # 生成报告
    report = generate_quality_report(
        docx_path,
        verbose=verbose,
        body_target_chars=body_target,
        review_target_chars=review_target,
        review_in_scope=review_in_scope,
        references_min_count=references_min_count,
        min_chapters=min_chapters,
        enforce_full_structure=enforce_full_structure,
    )
    
    if not report.get('success'):
        if output_format == 'json':
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 检查失败：{report.get('error')}")
        sys.exit(1)
    
    # 输出报告
    if output_format == 'json':
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report_text(report))
    
    # 保存报告
    report_path = docx_path.replace('.docx', '_质量报告.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if verbose:
        print(f"\n💾 报告已保存：{report_path}")
    
    # 返回退出码
    if report['overall_score'] >= 80:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

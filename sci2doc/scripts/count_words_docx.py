#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word 文档字数统计工具（中南大学博士论文专用）

功能：
1. 统计中文字符数（不含标点）
2. 统计英文单词数
3. 区分综述与正文
4. 排除参考文献、目录等部分
5. 生成 JSON 格式报告

作者：Sci2Doc Team
日期：2024-03-15
"""

from docx import Document
import argparse
import re
import sys
import json
import os

try:
    from thesis_profile import load_profile
except Exception:  # pragma: no cover
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from thesis_profile import load_profile


def is_chinese_char(char):
    """判断是否为中文字符"""
    return '\u4e00' <= char <= '\u9fff'


def is_english_char(char):
    """判断是否为英文字符"""
    return ('a' <= char.lower() <= 'z')


def count_words_in_text(text):
    """
    统计文本中的中文字符数和英文单词数
    
    Args:
        text: 待统计文本
    
    Returns:
        dict: {'chinese_chars': int, 'english_words': int}
    """
    # 统计中文字符
    chinese_chars = sum(1 for char in text if is_chinese_char(char))
    
    # 统计英文单词
    # 移除中文字符和标点，只保留英文和空格
    english_text = ''.join(char if is_english_char(char) or char.isspace() else ' ' 
                           for char in text)
    # 分割并计数非空单词
    english_words = len([word for word in english_text.split() if word])
    
    return {
        'chinese_chars': chinese_chars,
        'english_words': english_words
    }


def normalize_text(value):
    """标准化标题文本用于匹配。"""
    return re.sub(r"\s+", "", (value or "").lower())


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


def count_words_in_docx(
    docx_path,
    exclude_review=True,
    exclude_references=True,
    body_target_chars=80000,
    review_target_chars=0,
    review_in_scope=False,
):
    """
    统计 Word 文档字数
    
    Args:
        docx_path: docx 文件路径
        exclude_review: 是否排除综述章节
        exclude_references: 是否排除参考文献
    
    Returns:
        dict: 详细统计结果
    """
    try:
        doc = Document(docx_path)
    except Exception as e:
        return {
            'success': False,
            'error': f'无法打开文件：{str(e)}'
        }
    
    # 初始化计数器
    total_chinese_chars = 0
    total_english_words = 0
    review_chinese_chars = 0
    review_english_words = 0

    # 当前章节状态（基于标题切换，避免“排除状态卡住”）
    current_section_type = "body"
    current_section_title = "正文"
    section_stats = []
    current_section = {
        "title": current_section_title,
        "type": current_section_type,
        "chinese_chars": 0,
        "english_words": 0,
    }

    def flush_section():
        if current_section["chinese_chars"] > 0 or current_section["english_words"] > 0:
            section_stats.append(current_section.copy())

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        lvl = heading_level(getattr(para.style, "name", ""))
        if lvl is not None:
            flush_section()
            current_section_type = classify_heading(text)
            current_section_title = text
            current_section = {
                "title": current_section_title,
                "type": current_section_type,
                "chinese_chars": 0,
                "english_words": 0,
            }
            continue

        counts = count_words_in_text(text)
        current_section["chinese_chars"] += counts["chinese_chars"]
        current_section["english_words"] += counts["english_words"]

        if current_section_type == "review":
            if not exclude_review:
                total_chinese_chars += counts["chinese_chars"]
                total_english_words += counts["english_words"]
            review_chinese_chars += counts["chinese_chars"]
            review_english_words += counts["english_words"]
            continue

        if current_section_type == "references" and exclude_references:
            continue
        if current_section_type in {"toc", "abstract", "acknowledgement", "appendix"}:
            continue

        total_chinese_chars += counts["chinese_chars"]
        total_english_words += counts["english_words"]

    flush_section()
    
    # 生成报告
    body_total = total_chinese_chars + total_english_words
    review_total = review_chinese_chars + review_english_words
    grand_total = body_total + review_total
    body_target_chars = max(1, int(body_target_chars or 80000))
    review_target_chars = max(0, int(review_target_chars or 0))
    body_rate = round(total_chinese_chars / body_target_chars, 4)
    review_rate = (
        round(review_chinese_chars / review_target_chars, 4)
        if review_target_chars > 0 and review_chinese_chars > 0
        else None
    )

    result = {
        "schema_version": "2.1",
        "success": True,
        "file_path": docx_path,
        "file_name": os.path.basename(docx_path),
        "body_text": {
            "chinese_chars": total_chinese_chars,
            "english_words": total_english_words,
            "total_count": body_total,
        },
        "review": {
            "chinese_chars": review_chinese_chars,
            "english_words": review_english_words,
            "total_count": review_total,
        },
        "total": {
            "chinese_chars": total_chinese_chars + review_chinese_chars,
            "english_words": total_english_words + review_english_words,
            "total_count": grand_total,
        },
        "sections": section_stats,
        "targets": {
            "body_target": body_target_chars,
            "review_target": review_target_chars,
            "review_in_scope": bool(review_in_scope),
            "body_completion_rate": body_rate,
            "review_completion_rate": review_rate,
        },
        # Legacy compatibility fields for existing SKILL.md pseudo-code.
        "chinese_chars": total_chinese_chars,
        "english_words": total_english_words,
        "total_chars": body_total,
        "completion_rate": body_rate,
        "is_review": False,
    }
    
    return result


def format_report(result):
    """格式化统计报告为可读文本"""
    if not result.get('success'):
        return f"❌ 统计失败：{result.get('error')}"
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"📊 Word 文档字数统计报告")
    lines.append("=" * 60)
    lines.append(f"📄 文件：{result['file_name']}")
    lines.append("")
    
    # 正文统计
    body = result['body_text']
    lines.append("📝 正文统计：")
    lines.append(f"   中文字符：{body['chinese_chars']:,} 字")
    lines.append(f"   英文单词：{body['english_words']:,} 词")
    lines.append(f"   合计：{body['total_count']:,}")
    body_target = result.get("targets", {}).get("body_target", 80000)
    lines.append(f"   完成率：{result['targets']['body_completion_rate']*100:.1f}% "
                f"（目标 {body_target:,} 字）")
    lines.append("")
    
    # 综述统计
    review = result['review']
    review_target = result.get("targets", {}).get("review_target", 0)
    review_in_scope = bool(result.get("targets", {}).get("review_in_scope", False))
    if review['total_count'] > 0:
        lines.append("📚 综述统计：")
        lines.append(f"   中文字符：{review['chinese_chars']:,} 字")
        lines.append(f"   英文单词：{review['english_words']:,} 词")
        lines.append(f"   合计：{review['total_count']:,}")
        if review_in_scope and review_target > 0 and result["targets"]["review_completion_rate"] is not None:
            lines.append(f"   完成率：{result['targets']['review_completion_rate']*100:.1f}% "
                        f"（目标 {review_target:,} 字）")
        else:
            lines.append("   说明：综述不纳入当前正文考核范围")
        lines.append("")
    
    # 总计
    total = result['total']
    lines.append("📊 总计：")
    lines.append(f"   中文字符：{total['chinese_chars']:,} 字")
    lines.append(f"   英文单词：{total['english_words']:,} 词")
    lines.append(f"   合计：{total['total_count']:,}")
    lines.append("")
    
    # 章节详情
    if result.get('sections'):
        lines.append("📑 章节详情：")
        for i, section in enumerate(result['sections'], 1):
            section_type = section.get('type', '')
            type_tag = f" [{section_type}]" if section_type else ""
            lines.append(f"   {i}. {section['title']}{type_tag}")
            lines.append(f"      中文：{section['chinese_chars']:,}  "
                        f"英文：{section['english_words']:,}")
    
    lines.append("=" * 60)
    
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
    parser = argparse.ArgumentParser(description="Word 文档字数统计工具")
    parser.add_argument("docx_path", help="待统计的 docx 文件路径")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--profile", help="thesis_profile.json 路径（可选）")
    parser.add_argument("--body-target", type=int, help="覆盖正文目标字数")
    parser.add_argument("--review-target", type=int, help="覆盖综述目标字数")
    parser.add_argument("--review-in-scope", action="store_true", help="将综述纳入考核目标")
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
        print(json.dumps(payload, ensure_ascii=False, indent=2) if output_format == "json" else f"❌ {payload['message']}")
        sys.exit(1)
    targets = profile.get("targets", {}) if isinstance(profile, dict) else {}

    body_target = int(args.body_target if args.body_target is not None else targets.get("body_target_chars", 80000))
    review_in_scope = bool(args.review_in_scope or targets.get("review_in_scope", False))
    default_review_target = int(targets.get("review_target_chars", 0) or 0)
    review_target = int(args.review_target if args.review_target is not None else default_review_target)

    # 执行统计
    result = count_words_in_docx(
        docx_path,
        exclude_review=(not review_in_scope),
        exclude_references=True,
        body_target_chars=body_target,
        review_target_chars=review_target,
        review_in_scope=review_in_scope,
    )
    
    # 输出结果
    if output_format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
    
    # 返回退出码（用于脚本判断）
    if result.get('success'):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

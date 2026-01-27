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
import re
import sys
import json
import os


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


def is_excluded_section(text):
    """
    判断是否为需要排除的章节（综述、参考文献、目录等）
    
    Args:
        text: 段落或标题文本
    
    Returns:
        tuple: (is_excluded, section_type)
    """
    exclude_patterns = {
        'review': ['综述', 'review', 'literature review'],
        'references': ['参考文献', 'references', '引用文献'],
        'toc': ['目录', 'contents', 'table of contents'],
        'abstract': ['摘要', 'abstract'],
        'acknowledgement': ['致谢', 'acknowledgement', 'acknowledgment'],
        'appendix': ['附录', 'appendix']
    }
    
    text_lower = text.lower().strip()
    
    for section_type, patterns in exclude_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                return True, section_type
    
    return False, None


def count_words_in_docx(docx_path, exclude_review=True, exclude_references=True):
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
    
    # 状态标记
    in_excluded_section = False
    current_section_type = None
    
    # 分段统计
    section_stats = []
    current_section = {
        'title': '开始',
        'chinese_chars': 0,
        'english_words': 0
    }
    
    for para in doc.paragraphs:
        text = para.text.strip()
        
        if not text:
            continue
        
        # 检查是否进入排除章节
        is_excluded, section_type = is_excluded_section(text)
        
        if is_excluded:
            # 保存当前章节统计
            if current_section['chinese_chars'] > 0 or current_section['english_words'] > 0:
                section_stats.append(current_section.copy())
            
            # 开始新的章节
            in_excluded_section = True
            current_section_type = section_type
            current_section = {
                'title': text,
                'chinese_chars': 0,
                'english_words': 0,
                'type': section_type
            }
            continue
        
        # 统计当前段落
        counts = count_words_in_text(text)
        current_section['chinese_chars'] += counts['chinese_chars']
        current_section['english_words'] += counts['english_words']
        
        # 根据章节类型累加到不同计数器
        if in_excluded_section:
            if current_section_type == 'review':
                review_chinese_chars += counts['chinese_chars']
                review_english_words += counts['english_words']
            # 其他排除章节不计入任何统计
        else:
            total_chinese_chars += counts['chinese_chars']
            total_english_words += counts['english_words']
    
    # 保存最后一个章节
    if current_section['chinese_chars'] > 0 or current_section['english_words'] > 0:
        section_stats.append(current_section.copy())
    
    # 生成报告
    result = {
        'success': True,
        'file_path': docx_path,
        'file_name': os.path.basename(docx_path),
        'body_text': {
            'chinese_chars': total_chinese_chars,
            'english_words': total_english_words,
            'total_count': total_chinese_chars + total_english_words  # 简化计数
        },
        'review': {
            'chinese_chars': review_chinese_chars,
            'english_words': review_english_words,
            'total_count': review_chinese_chars + review_english_words
        },
        'total': {
            'chinese_chars': total_chinese_chars + review_chinese_chars,
            'english_words': total_english_words + review_english_words,
            'total_count': total_chinese_chars + review_chinese_chars + 
                          total_english_words + review_english_words
        },
        'sections': section_stats,
        'targets': {
            'body_target': 50000,
            'review_target': 5000,
            'body_completion_rate': round(total_chinese_chars / 50000, 4),
            'review_completion_rate': round(review_chinese_chars / 5000, 4) if review_chinese_chars > 0 else 0
        }
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
    lines.append(f"   完成率：{result['targets']['body_completion_rate']*100:.1f}% "
                f"（目标 50,000 字）")
    lines.append("")
    
    # 综述统计
    review = result['review']
    if review['total_count'] > 0:
        lines.append("📚 综述统计：")
        lines.append(f"   中文字符：{review['chinese_chars']:,} 字")
        lines.append(f"   英文单词：{review['english_words']:,} 词")
        lines.append(f"   合计：{review['total_count']:,}")
        lines.append(f"   完成率：{result['targets']['review_completion_rate']*100:.1f}% "
                    f"（目标 5,000 字）")
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


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python3 count_words_docx.py <文件路径> [--output json|text]")
        print("示例: python3 count_words_docx.py thesis.docx --output json")
        sys.exit(1)
    
    docx_path = sys.argv[1]
    output_format = 'text'
    
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_format = sys.argv[idx + 1]
    
    if not os.path.exists(docx_path):
        print(f"❌ 文件不存在：{docx_path}")
        sys.exit(1)
    
    # 执行统计
    result = count_words_in_docx(docx_path)
    
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

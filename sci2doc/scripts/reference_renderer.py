#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GB/T 7714-2015 参考文献著录渲染器

从 literature_index.json 读取结构化文献条目，按 GB/T 7714-2015
规则渲染成 [J] [M] [D] [C] [EB/OL] 等类型著录条目，输出 Markdown。

用法：
  python3 reference_renderer.py --index /path/to/literature_index.json
  python3 reference_renderer.py --index .../literature_index.json --output .../refs.md
  python3 reference_renderer.py --index .../literature_index.json --chapter 2
"""

import argparse
import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# GB/T 7714-2015 著录格式规则
# ---------------------------------------------------------------------------

def _fmt_authors(authors: list[str], max_authors: int = 3) -> str:
    """
    GB/T 7714: 3 名以内全列，超过 3 名列前 3 人后加 "等" / "et al."（外文）。
    作者间用 ", " 分隔，末尾不加句号（外部拼接时处理）。

    注意：GB/T 7714-2015 要求外文作者采用"姓在前+名缩写"格式（如 Zhang S 而非 Shuang Zhang）。
    本函数原样输出输入值，不做自动缩写——输入应在写入 literature_index.json 时预处理为规范格式
    （如通过 PubMed authors 字段抓取时，作者名通常已是 "Zhang S" 格式）。
    """
    if not authors:
        return "佚名"
    is_chinese = any(
        '一' <= c <= '鿿'
        for author in authors[:1]
        for c in author
    )
    if len(authors) <= max_authors:
        return ", ".join(authors)
    suffix = "等" if is_chinese else ", et al"
    return ", ".join(authors[:max_authors]) + suffix


def _fmt_title(title: str) -> str:
    """期刊/图书题名直接返回（GB/T 7714 不强制大小写）。"""
    return (title or "").strip()


def render_journal(entry: dict) -> str:
    """
    [J] 期刊论文
    格式：著者. 题名[J]. 刊名, 年, 卷(期): 起止页. DOI: xxx.
    """
    authors = _fmt_authors(entry.get("authors", []))
    title = _fmt_title(entry.get("title", ""))
    journal = entry.get("journal", "").strip()
    year = entry.get("year", "")
    volume = entry.get("volume", "").strip()
    issue = entry.get("issue", "").strip()
    pages = entry.get("pages", "").strip()
    doi = entry.get("doi", "").strip()

    vol_iss = ""
    if volume and issue:
        vol_iss = f"{volume}({issue})"
    elif volume:
        vol_iss = volume

    # GB/T 7714: 著者. 题名[J]. 刊名, 年, 卷(期): 起止页码.
    loc_str = str(year)
    if vol_iss:
        loc_str += f", {vol_iss}"
    if pages:
        loc_str += f": {pages}"

    result = f"{authors}. {title}[J]. {journal}, {loc_str}."
    if doi:
        result += f" DOI: {doi}."
    return result


def render_book(entry: dict) -> str:
    """
    [M] 专著
    格式：著者. 书名[M]. 版次. 出版地: 出版者, 年: 起止页.
    """
    authors = _fmt_authors(entry.get("authors", []))
    title = _fmt_title(entry.get("title", ""))
    edition = entry.get("edition", "").strip()
    publisher = entry.get("publisher", "").strip()
    pub_place = entry.get("pub_place", "").strip()
    year = entry.get("year", "")
    pages = entry.get("pages", "").strip()

    result = f"{authors}. {title}[M]."
    if edition:
        result += f" {edition}."
    if pub_place and publisher:
        result += f" {pub_place}: {publisher}, {year}"
    elif publisher:
        result += f" {publisher}, {year}"
    else:
        result += f" {year}"
    if pages:
        result += f": {pages}"
    result = result.rstrip(".") + "."
    return result


def render_dissertation(entry: dict) -> str:
    """
    [D] 学位论文
    格式：著者. 题名[D]. 出版地: 出版单位(学位授予单位), 年.
    """
    authors = _fmt_authors(entry.get("authors", []))
    title = _fmt_title(entry.get("title", ""))
    pub_place = entry.get("pub_place", "").strip()
    institution = entry.get("institution", "").strip()
    year = entry.get("year", "")

    result = f"{authors}. {title}[D]."
    if pub_place and institution:
        result += f" {pub_place}: {institution}, {year}."
    elif institution:
        result += f" {institution}, {year}."
    else:
        result += f" {year}."
    return result


def render_conference(entry: dict) -> str:
    """
    [C] 论文集 / 会议论文（析出文献 [C]//，整册 [C]）
    格式：著者. 题名[C]//编者. 文集名. 出版地: 出版者, 年: 起止页.
    """
    authors = _fmt_authors(entry.get("authors", []))
    title = _fmt_title(entry.get("title", ""))
    editor = entry.get("editor", "").strip()
    booktitle = entry.get("booktitle", "").strip()
    pub_place = entry.get("pub_place", "").strip()
    publisher = entry.get("publisher", "").strip()
    year = entry.get("year", "")
    pages = entry.get("pages", "").strip()

    if booktitle:
        result = f"{authors}. {title}[C]//"
        if editor:
            result += f"{editor}. "
        result += f"{booktitle}."
    else:
        result = f"{authors}. {title}[C]."
    if pub_place and publisher:
        result += f" {pub_place}: {publisher}, {year}"
    else:
        result += f" {year}"
    if pages:
        result += f": {pages}"
    result = result.rstrip(".") + "."
    return result


def render_online(entry: dict) -> str:
    """
    [EB/OL] 电子资源/网络文献
    格式：著者. 题名[EB/OL]. 出版地: 出版者, 年[引用日期]. URL.
    """
    authors = _fmt_authors(entry.get("authors", []))
    title = _fmt_title(entry.get("title", ""))
    pub_place = entry.get("pub_place", "").strip()
    publisher = entry.get("publisher", "").strip()
    year = entry.get("year", "")
    access_date = entry.get("access_date", "").strip()
    url = entry.get("url", "").strip()
    doi = entry.get("doi", "").strip()

    result = f"{authors}. {title}[EB/OL]."
    if pub_place and publisher:
        result += f" {pub_place}: {publisher}, {year}"
    else:
        result += f" {year}"
    if access_date:
        result += f"[{access_date}]"
    result = result.rstrip(".") + "."
    if url:
        result += f" {url}."
    elif doi:
        result += f" DOI: {doi}."
    return result


def render_patent(entry: dict) -> str:
    """
    [P] 专利
    格式：专利权人. 专利题名: 专利号[P]. 公告日期.
    """
    authors = _fmt_authors(entry.get("authors", []))
    title = _fmt_title(entry.get("title", ""))
    patent_number = entry.get("patent_number", "").strip()
    pub_date = entry.get("pub_date", "").strip()

    result = f"{authors}. {title}"
    if patent_number:
        result += f": {patent_number}[P]."
    else:
        result += "[P]."
    if pub_date:
        result += f" {pub_date}."
    return result


_TYPE_RENDERERS = {
    "journal":      render_journal,
    "J":            render_journal,
    "article":      render_journal,
    "book":         render_book,
    "M":            render_book,
    "dissertation": render_dissertation,
    "D":            render_dissertation,
    "thesis":       render_dissertation,
    "conference":   render_conference,
    "C":            render_conference,
    "inproceedings": render_conference,
    "online":       render_online,
    "EB/OL":        render_online,
    "patent":       render_patent,
    "P":            render_patent,
}


def _has_structured_fields(entry: dict) -> bool:
    """
    判断条目是否具备可渲染的结构化字段。
    SCI 参考库（如 PubMed 抓取）常只有完整 raw_vancouver 字符串而无 authors/journal 等
    结构化字段，此时应回退原样输出 raw_vancouver，避免渲染出"佚名 / 空刊名"。
    判据：至少有 authors，且对期刊类至少有 journal。
    """
    authors = entry.get("authors")
    if not authors:
        return False
    ref_type = (entry.get("type") or entry.get("ref_type") or "journal").strip()
    if ref_type in {"journal", "J", "article"} and not (entry.get("journal") or "").strip():
        return False
    return True


def render_entry(entry: dict, index: int | None = None) -> str:
    """
    渲染单条文献条目为 GB/T 7714 著录字符串。
    index 为正整数时前缀 [N] 编号；None 时不加编号。
    未知 type 默认按期刊处理。

    若结构化字段缺失（作者为空/期刊为空等），回退直接采用 raw_vancouver 原文。
    """
    if not _has_structured_fields(entry):
        raw = (entry.get("raw_vancouver") or "").strip()
        if raw:
            return f"[{index}] {raw}" if index is not None else raw

    ref_type = (entry.get("type") or entry.get("ref_type") or "journal").strip()
    renderer = _TYPE_RENDERERS.get(ref_type, render_journal)
    text = renderer(entry)
    if index is not None:
        return f"[{index}] {text}"
    return text


# ---------------------------------------------------------------------------
# 校验辅助（供 check_quality.py 调用）
# ---------------------------------------------------------------------------

REQUIRED_FIELDS_BY_TYPE = {
    "journal":      ["authors", "title", "journal", "year"],
    "J":            ["authors", "title", "journal", "year"],
    "article":      ["authors", "title", "journal", "year"],
    "book":         ["authors", "title", "year"],
    "M":            ["authors", "title", "year"],
    "dissertation": ["authors", "title", "year"],
    "D":            ["authors", "title", "year"],
    "thesis":       ["authors", "title", "year"],
    "conference":   ["authors", "title", "year"],
    "C":            ["authors", "title", "year"],
    "inproceedings": ["authors", "title", "year"],
    "online":       ["title", "year"],
    "EB/OL":        ["title", "year"],
    "patent":       ["authors", "title"],
    "P":            ["authors", "title"],
}

VALID_TYPE_TAGS = set(_TYPE_RENDERERS.keys())


def validate_entry(entry: dict, entry_id: str = "") -> list[dict]:
    """
    校验单条文献条目的著录格式。
    返回问题列表，每条 {"level": str, "category": str, "message": str, "id": str}。
    """
    issues = []
    ref_id = entry_id or entry.get("id", "(unknown)")
    ref_type = (entry.get("type") or entry.get("ref_type") or "").strip()

    # 1) 类型标识必须合法
    if not ref_type:
        issues.append({
            "level": "error",
            "category": "参考文献著录",
            "message": f"文献 {ref_id}：缺少 type 字段（必须为 J/M/D/C/EB/OL/P 等）",
            "id": ref_id,
        })
        return issues  # type 缺失，后续检查无意义

    if ref_type not in VALID_TYPE_TAGS:
        issues.append({
            "level": "warning",
            "category": "参考文献著录",
            "message": f"文献 {ref_id}：type='{ref_type}' 不在已知类型列表中（{', '.join(sorted(VALID_TYPE_TAGS))}）",
            "id": ref_id,
        })

    # 2) 必填字段检查
    required = REQUIRED_FIELDS_BY_TYPE.get(ref_type, ["authors", "title", "year"])
    for field in required:
        val = entry.get(field)
        if val is None or (isinstance(val, (str, list)) and len(val) == 0):
            issues.append({
                "level": "error",
                "category": "参考文献著录",
                "message": f"文献 {ref_id}（type={ref_type}）：必填字段 '{field}' 缺失或为空",
                "id": ref_id,
            })

    # 3) year 应为 4 位整数
    year = entry.get("year")
    if year is not None:
        year_str = str(year).strip()
        if not re.match(r'^\d{4}$', year_str):
            issues.append({
                "level": "warning",
                "category": "参考文献著录",
                "message": f"文献 {ref_id}：year='{year}' 不是有效 4 位年份",
                "id": ref_id,
            })

    # 4) authors 类型检查（应为 list）
    authors = entry.get("authors")
    if authors is not None and not isinstance(authors, list):
        issues.append({
            "level": "error",
            "category": "参考文献著录",
            "message": f"文献 {ref_id}：authors 字段应为数组（list），当前为 {type(authors).__name__}",
            "id": ref_id,
        })

    # 5) doi / pmid 至少一个（鼓励但非 error）
    doi = (entry.get("doi") or "").strip()
    pmid = (entry.get("pmid") or "").strip()
    if not doi and not pmid and ref_type in {"journal", "J", "article"}:
        issues.append({
            "level": "info",
            "category": "参考文献著录",
            "message": f"文献 {ref_id}：期刊论文建议提供 doi 或 pmid",
            "id": ref_id,
        })

    return issues


def validate_all(entries: list[dict]) -> list[dict]:
    """校验全部条目，汇总问题列表。"""
    all_issues = []
    for entry in entries:
        all_issues.extend(validate_entry(entry, entry.get("id", "")))
    return all_issues


# ---------------------------------------------------------------------------
# 主渲染流程
# ---------------------------------------------------------------------------

def load_index(index_path: str) -> list[dict]:
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"literature_index.json 应为 JSON 数组，实际为 {type(data).__name__}")
    return data


def render_all(
    entries: list[dict],
    chapter: int | None = None,
    numbered: bool = True,
) -> str:
    """
    渲染所有（或指定章节）文献条目为 Markdown 文本。
    按 id 字段中数字升序排列（无数字则保持原序）。
    """
    if chapter is not None:
        entries = [e for e in entries if e.get("chapter") == chapter]

    def sort_key(e):
        m = re.search(r'\d+', str(e.get("id", "")))
        return int(m.group()) if m else float("inf")

    entries = sorted(entries, key=sort_key)

    lines = []
    for i, entry in enumerate(entries, start=1):
        idx = i if numbered else None
        lines.append(render_entry(entry, index=idx))

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="GB/T 7714-2015 参考文献著录渲染器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--index", required=True,
        help="literature_index.json 路径",
    )
    parser.add_argument(
        "--output", default=None,
        help="输出 Markdown 文件路径（默认打印到 stdout）",
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="只渲染指定章节的文献（按 chapter 字段过滤）",
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help="只校验著录格式，不渲染输出",
    )
    parser.add_argument(
        "--output-format", choices=["markdown", "json"], default="markdown",
        help="validate-only 模式下的输出格式（默认 markdown）",
    )
    args = parser.parse_args()

    if not os.path.exists(args.index):
        print(f"错误：文件不存在：{args.index}", file=sys.stderr)
        sys.exit(1)

    try:
        entries = load_index(args.index)
    except Exception as e:
        print(f"错误：无法解析 literature_index.json：{e}", file=sys.stderr)
        sys.exit(1)

    if args.validate_only:
        issues = validate_all(entries)
        if args.output_format == "json":
            print(json.dumps(issues, ensure_ascii=False, indent=2))
        else:
            if not issues:
                print("著录格式校验通过，未发现问题。")
            else:
                for iss in issues:
                    lvl = iss["level"].upper()
                    print(f"[{lvl}] {iss['message']}")
        error_count = sum(1 for i in issues if i["level"] == "error")
        sys.exit(0 if error_count == 0 else 1)

    # 正常渲染
    chapter_filter = args.chapter
    result = render_all(entries, chapter=chapter_filter, numbered=True)

    header = "## 参考文献\n\n" if not chapter_filter else f"## 第 {chapter_filter} 章参考文献\n\n"
    output_text = header + result + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"已输出到：{args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()

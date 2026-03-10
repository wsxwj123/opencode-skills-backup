#!/usr/bin/env python3
"""Generate one-shot hierarchical reviewer response HTML from DOCX materials."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from docx import Document


@dataclass
class CommentItem:
    reviewer: str
    section: str
    index: str
    comment_en: str
    reply_en: str


def read_docx_text(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_reviewers(full: str) -> dict[str, str]:
    hits = list(re.finditer(r"Reviewer\s*#\d+:", full))
    if not hits:
        return {"Reviewer #1": full}

    blocks: dict[str, str] = {}
    for i, m in enumerate(hits):
        start = m.start()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(full)
        key = m.group(0).rstrip(":")
        blocks[key] = full[start:end]
    return blocks


def split_sections(reviewer_block: str) -> list[tuple[str, str]]:
    section_names = ["Major Comments", "Minor Comments", "Major changes", "Minor changes"]
    marks: list[tuple[int, str]] = []
    for name in section_names:
        idx = reviewer_block.find(name)
        if idx != -1:
            marks.append((idx, name))
    marks.sort()
    if not marks:
        return [("General", reviewer_block)]

    spans: list[tuple[str, str]] = []
    for i, (idx, name) in enumerate(marks):
        start = idx + len(name)
        end = marks[i + 1][0] if i + 1 < len(marks) else len(reviewer_block)
        spans.append((name, reviewer_block[start:end]))
    return spans


def parse_items(reviewer_name: str, reviewer_block: str) -> list[CommentItem]:
    items: list[CommentItem] = []
    for section_name, sec_text in split_sections(reviewer_block):
        pat = re.compile(r"\n\s*(\d+)\.\s+(.*?)(?=\n\s*\d+\.\s+|\Z)", re.S)
        for m in pat.finditer("\n" + sec_text):
            idx = m.group(1)
            body = re.sub(r"\s+", " ", m.group(2)).strip()
            comment, reply = body, ""
            if " Reply:" in body:
                parts = body.split(" Reply:", 1)
                comment = parts[0].strip()
                reply = parts[1].strip()
            items.append(
                CommentItem(
                    reviewer=reviewer_name,
                    section=section_name,
                    index=idx,
                    comment_en=comment,
                    reply_en=reply,
                )
            )
    return items


def zh_understanding(comment_en: str) -> str:
    s = comment_en.strip()
    if len(s) > 220:
        s = s[:220] + "..."
    return "审稿人核心关切：" + s


def draft_response(comment_en: str, section: str) -> str:
    low = comment_en.lower()
    if section.lower().startswith("minor"):
        return (
            "Thank you for this helpful suggestion. We have revised the relevant text/figure presentation accordingly, "
            "and we rechecked consistency across related sections in the revised manuscript."
        )
    if any(k in low for k in ["discrepancy", "mismatch", "inconsistent", "contradict", "clarify"]):
        return (
            "We sincerely thank the reviewer for identifying this critical issue. We have rechecked the corresponding "
            "data and updated the related text/figure presentation to ensure strict consistency between evidence and interpretation."
        )
    if any(k in low for k in ["please provide", "please add", "include", "recommended"]):
        return (
            "We appreciate this constructive recommendation. We have incorporated the requested clarification/analysis "
            "in the revised manuscript and updated the related figure or method description accordingly."
        )
    return (
        "Thank you for this valuable comment. We have revised the manuscript accordingly and clarified the corresponding "
        "scientific point in the revised version."
    )


def notes(section: str) -> tuple[str, str]:
    if section.lower().startswith("minor"):
        return (
            "围绕术语、图注、编号和版式执行规范化修订，并逐项核对对应位置。",
            "完成同类问题的全文一致性校对，降低编辑轮返风险。",
        )
    return (
        "围绕该条意见的核心科学关切进行实质修订，确保结论与证据链一致。",
        "同步优化图号引用、术语表达与段落衔接，提升可读性与可核查性。",
    )


def build_html(title: str, email_text: str, items: list[CommentItem]) -> str:
    # Group by reviewer and section for hierarchical TOC
    grouped: dict[str, dict[str, list[CommentItem]]] = {}
    for it in items:
        grouped.setdefault(it.reviewer, {}).setdefault(it.section, []).append(it)

    toc = []
    pages = []

    toc.append('<li><button class="toc-btn active" data-target="page-email">回复审稿人的邮件</button></li>')
    pages.append(
        f'''<section id="page-email" class="page active"><h2>回复审稿人的邮件</h2>
<div class="card"><h3>English Email</h3><p>{escape(email_text)}</p></div>
<div class="card"><h3>中文说明</h3><p>本页为总回复邮件。后续目录按 Reviewer -> Major/Minor -> Comment 分层组织，点击即可切换。</p></div>
</section>'''
    )

    page_count = 0
    for reviewer, sec_map in grouped.items():
        reviewer_li = [f'<li><button class="toc-btn" data-target="r-{page_count+1}">{escape(reviewer)}</button>']
        reviewer_li.append('<ul class="toc-level-2">')
        pages.append(
            f'''<section id="r-{page_count+1}" class="page"><h2>{escape(reviewer)}</h2>
<div class="card"><p>选择下级 Major/Minor 与具体 Comment 查看详细内容。</p></div></section>'''
        )
        page_count += 1

        for sec_name, sec_items in sec_map.items():
            sec_id = f"s-{page_count+1}"
            reviewer_li.append(f'<li><button class="toc-btn" data-target="{sec_id}">{escape(sec_name)}</button>')
            reviewer_li.append('<ul class="toc-level-3">')
            pages.append(
                f'''<section id="{sec_id}" class="page"><h2>{escape(reviewer)} - {escape(sec_name)}</h2>
<div class="card"><p>请选择具体 Comment 查看逐条回复详情。</p></div></section>'''
            )
            page_count += 1

            for it in sec_items:
                cid = f"c-{page_count+1}"
                reviewer_li.append(f'<li><button class="toc-btn" data-target="{cid}">Comment {escape(it.index)}</button></li>')

                resp = it.reply_en if it.reply_en else draft_response(it.comment_en, it.section)
                core, support = notes(it.section)

                pages.append(
                    f'''<section id="{cid}" class="page"><h2>{escape(reviewer)} | {escape(sec_name)} | Comment {escape(it.index)}</h2>
<div class="card"><h3>1) Reviewer Comment (Bilingual)</h3>
<h4>中文理解</h4><p>{escape(zh_understanding(it.comment_en))}</p>
<h4>English</h4><p>{escape(it.comment_en)}</p></div>
<div class="card"><h3>2) Response to Reviewer (English)</h3><p>{escape(resp)}</p></div>
<div class="card"><h3>3) Revised Manuscript Excerpt (Clean Version)</h3><p>Not provided by user. Paste the final clean revised paragraph here.</p></div>
<div class="card"><h3>4) 修改说明（中文）</h3><ul>
<li><span class="tag core">🔴 Core</span> {escape(core)}</li>
<li><span class="tag support">🟡 Support</span> {escape(support)}</li>
</ul></div>
<div class="card"><h3>5) Evidence Attachments</h3>
<p><strong>Text:</strong> Not provided by user.</p>
<figure><img src="" alt="No image provided" /><figcaption>Not provided by user.</figcaption></figure>
<div class="table-wrap"><table><thead><tr><th>Item</th><th>Before</th><th>After</th><th>Evidence</th></tr></thead>
<tbody><tr><td>Key correction</td><td>Not provided by user</td><td>Not provided by user</td><td>Not provided by user</td></tr></tbody></table></div>
</div></section>'''
                )
                page_count += 1

            reviewer_li.append('</ul></li>')
            reviewer_li.append('</li>')

        reviewer_li.append('</ul></li>')
        toc.append("".join(reviewer_li))

    today = date.today().isoformat()
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reviewer Response Full Package</title>
  <style>
    :root {{ --bg:#f4f7fb; --panel:#fff; --text:#1f2937; --line:#d9e2ec; --accent:#0f4c81; --core:#b42318; --support:#b54708; --muted:#667085; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--text); }}
    .layout {{ display:grid; grid-template-columns:340px 1fr; min-height:100vh; }}
    .sidebar {{ border-right:1px solid var(--line); background:#fff; position:sticky; top:0; height:100vh; overflow:auto; padding:14px; }}
    .sidebar h1 {{ margin:0 0 4px; font-size:1.05rem; color:var(--accent); }}
    .meta {{ font-size:.85rem; color:var(--muted); margin-bottom:10px; }}
    .toc-level-1, .toc-level-2, .toc-level-3 {{ list-style:none; margin:0; padding-left:0; }}
    .toc-level-2 {{ padding-left:12px; margin-top:4px; }}
    .toc-level-3 {{ padding-left:14px; margin-top:4px; }}
    .toc-btn {{ width:100%; text-align:left; border:1px solid var(--line); background:#fff; padding:7px 9px; border-radius:8px; cursor:pointer; font-size:.88rem; margin-bottom:6px; }}
    .toc-btn.active {{ background:#eaf3ff; border-color:#7ea3c8; color:#0b3f68; font-weight:600; }}
    .content {{ padding:18px 22px; }}
    .page {{ display:none; }}
    .page.active {{ display:block; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin:0 0 12px; }}
    h2 {{ color:var(--accent); margin:0 0 10px; }}
    h3 {{ margin:0 0 8px; }}
    h4 {{ margin:8px 0 4px; }}
    p {{ white-space:pre-wrap; line-height:1.6; }}
    .tag {{ display:inline-block; padding:1px 8px; border-radius:999px; color:#fff; font-size:.8rem; font-weight:600; margin-right:6px; }}
    .core {{ background:var(--core); }}
    .support {{ background:var(--support); }}
    figure {{ margin:8px 0; border:1px dashed var(--line); padding:10px; border-radius:8px; background:#fafcff; }}
    img {{ max-width:100%; height:auto; min-height:80px; background:#fff; border:1px solid var(--line); border-radius:6px; }}
    .table-wrap {{ overflow-x:auto; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border:1px solid var(--line); padding:7px 9px; text-align:left; vertical-align:top; }}
    th {{ background:#eff5fb; }}
    @media (max-width:980px) {{ .layout {{ grid-template-columns:1fr; }} .sidebar {{ position:relative; height:auto; border-right:none; border-bottom:1px solid var(--line); }} }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1>审稿回复目录</h1>
      <div class="meta">{escape(title)} | {today}</div>
      <ul id="toc-root" class="toc-level-1">{''.join(toc)}</ul>
    </aside>
    <main id="content-root" class="content">{''.join(pages)}</main>
  </div>
  <script>
    const btns = document.querySelectorAll('.toc-btn');
    const pages = document.querySelectorAll('.page');
    btns.forEach(btn => {{
      btn.addEventListener('click', () => {{
        btns.forEach(b => b.classList.remove('active'));
        pages.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const target = document.getElementById(btn.dataset.target);
        if (target) target.classList.add('active');
      }});
    }});
  </script>
</body>
</html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot hierarchical reviewer response HTML")
    parser.add_argument("--comments", required=True, help="Path to comments .docx")
    parser.add_argument("--manuscript", required=True, help="Path to manuscript .docx")
    parser.add_argument("--si", default="", help="Path to SI .docx (optional)")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--title", default="Reviewer Response Full Package", help="HTML title text")
    args = parser.parse_args()

    comments_text = read_docx_text(Path(args.comments))
    manuscript_text = read_docx_text(Path(args.manuscript))
    _ = read_docx_text(Path(args.si)) if args.si else ""

    intro_match = re.search(r"Response Letter\n(.*?)\n\nReviewers' comments:", comments_text, re.S)
    email_text = intro_match.group(1).strip() if intro_match else (
        "Dear Editor and Reviewers,\n\n"
        "Thank you for your constructive comments. We revised the manuscript point by point and addressed each concern below.\n\n"
        "Sincerely,\nThe Authors"
    )

    blocks = extract_reviewers(comments_text)
    items: list[CommentItem] = []
    for reviewer_name, block in blocks.items():
        items.extend(parse_items(reviewer_name, block))

    if not items:
        # fallback one placeholder page if parsing fails
        items.append(
            CommentItem(
                reviewer="Reviewer #1",
                section="General",
                index="1",
                comment_en="Not parsed from comments file. Please check comments_docx formatting.",
                reply_en="Thank you for the comment. We will revise accordingly.",
            )
        )

    title = args.title
    if title == "Reviewer Response Full Package":
        # use manuscript first line if useful
        first = re.sub(r"\s+", " ", manuscript_text[:120]).strip()
        if first:
            title = f"Reviewer Response - {first[:70]}"

    html = build_html(title=title, email_text=email_text, items=items)
    Path(args.output).write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

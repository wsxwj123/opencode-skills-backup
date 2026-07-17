#!/usr/bin/env python3
"""extract_headings.py —— 标题真值生产者（功能② · INTERFACE §1，跨家共享）.

一趟同产两文件，偏移天然一致：
  - <text-out>  正文纯文本 draft_import.md（切片/审计的字节流基准）
  - <out>       heading_manifest.json（标题真值，char_offset 索引 draft_import.md）

不变量：对每个 heading，draft_import.md[char_offset : char_offset+len(text)] == text。

来源判定按扩展名：.md/.markdown → markdown（无第三方依赖，主覆盖）；
.docx → python-docx + styles.xml 反查（basedOn 链 / outlineLvl，识别非标准样式）；
.pdf → 抽文本、headings 置空（触发无标题路）。

退出码（INTERFACE §1）：
  0  成功（含 headings:[] 的 headless 情形，必写出两文件）
  1  源损坏（docx 非 zip / pdf 打不开 / 抽出 <200 字疑扫描件）
  2  用法错 / --source 不存在 / 缺 python-docx / 无可用 PDF 抽取器
只走 CLI，单行 JSON 到 stdout。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

MIN_BODY_CHARS = 200  # <此长度的 docx/pdf 抽取视为扫描件，HALT（markdown 不受限）
ATX_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*$")
# 保守的内容启发式：仅在 docx 无任何样式标题时，作 low-confidence 兜底（编号+短行）。
NUMBERED_RE = re.compile(r"^\s*\d+(?:[.\-]\d+){0,4}[.、\s]")
CAPTION_STYLE_RE = re.compile(r"caption|题注|图注|表注", re.IGNORECASE)


def _die(code, msg):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------
def extract_markdown(src_path):
    with open(src_path, encoding="utf-8") as f:
        raw = f.read()
    out = []
    headings = []
    pos = 0
    for line in raw.splitlines(keepends=True):
        body = line.rstrip("\n")
        nl = line[len(body):]
        m = ATX_RE.match(body)
        if m:
            htext = m.group(2).strip()
            headings.append({
                "text": htext,
                "level": len(m.group(1)),
                "char_offset": pos,
                "style_id": "md:" + m.group(1),
                "is_caption": False,
                "confidence": "high",
            })
            out.append(htext)
            pos += len(htext)
        else:
            out.append(body)
            pos += len(body)
        out.append(nl)
        pos += len(nl)
    return "".join(out), headings


# ---------------------------------------------------------------------------
# docx —— styles.xml 反查（basedOn 链 + outlineLvl）
# ---------------------------------------------------------------------------
def _docx_outline_map(doc):
    """从 styles.xml 建 styleId/name -> 层级(outlineLvl+1) 的映射（非标准样式反查）。"""
    from docx.oxml.ns import qn
    out = {}
    styles_el = doc.styles.element
    for st in styles_el.findall(qn("w:style")):
        sid = st.get(qn("w:styleId"))
        name_el = st.find(qn("w:name"))
        name = name_el.get(qn("w:val")) if name_el is not None else None
        ppr = st.find(qn("w:pPr"))
        if ppr is None:
            continue
        ol = ppr.find(qn("w:outlineLvl"))
        if ol is None:
            continue
        try:
            lvl = int(ol.get(qn("w:val"))) + 1
        except (TypeError, ValueError):
            continue
        if sid:
            out[sid] = lvl
        if name:
            out[name] = lvl
    return out


def _level_from_style_chain(style):
    """跟 base_style（basedOn）链找 Heading N / Title，返回层级或 None。"""
    seen = set()
    s = style
    while s is not None and id(s) not in seen:
        seen.add(id(s))
        name = (getattr(s, "name", None) or "").strip().lower()
        if name == "title":
            return 1
        m = re.match(r"heading\s*(\d+)", name)
        if m:
            return int(m.group(1))
        s = getattr(s, "base_style", None)
    return None


def extract_docx(src_path):
    try:
        import docx  # python-docx
    except Exception:
        _die(2, "python-docx not available")
    try:
        doc = docx.Document(src_path)
    except Exception as e:  # 非 zip / 损坏包
        _die(1, "corrupt or unreadable docx: %s" % e)

    outline_map = _docx_outline_map(doc)
    out = []
    headings = []
    pos = 0
    for p in doc.paragraphs:
        text = p.text
        style = p.style
        sname = (getattr(style, "name", None) or "")
        sid = getattr(style, "style_id", None)
        level = _level_from_style_chain(style)
        if level is None:
            level = outline_map.get(sid) or outline_map.get(sname)
        is_caption = bool(CAPTION_STYLE_RE.search(sname))
        stripped = text.strip()
        if stripped:
            if is_caption:
                headings.append({"text": stripped, "level": 0, "char_offset": pos,
                                 "style_id": sname or "caption", "is_caption": True,
                                 "confidence": "high"})
            elif level is not None:
                headings.append({"text": stripped, "level": level, "char_offset": pos,
                                 "style_id": sname or ("outline:%d" % level),
                                 "is_caption": False, "confidence": "high"})
        out.append(text)
        pos += len(text)
        out.append("\n")
        pos += 1
    return "".join(out), headings


# ---------------------------------------------------------------------------
# pdf —— 抽文本，headings 置空（触发无标题路）
# ---------------------------------------------------------------------------
def extract_pdf(src_path, pdf_tool=None):
    tools = [pdf_tool] if pdf_tool else ["pymupdf", "pdfplumber", "pypdf"]
    text = None
    for t in tools:
        try:
            if t == "pymupdf":
                import fitz
                d = fitz.open(src_path)
                text = "\n".join(pg.get_text() for pg in d)
            elif t == "pdfplumber":
                import pdfplumber
                with pdfplumber.open(src_path) as pdf:
                    text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
            elif t == "pypdf":
                import pypdf
                r = pypdf.PdfReader(src_path)
                text = "\n".join((pg.extract_text() or "") for pg in r.pages)
            if text is not None:
                break
        except ImportError:
            continue
        except Exception as e:
            _die(1, "pdf open failed: %s" % e)
    if text is None:
        _die(2, "no usable PDF extractor (install pymupdf/pdfplumber/pypdf)")
    return text, []


def main(argv=None):
    ap = argparse.ArgumentParser(description="标题真值生产者（draft_import.md + heading_manifest.json）")
    ap.add_argument("--source", required=True)
    ap.add_argument("--text-out", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf-tool", choices=["pymupdf", "pdfplumber", "pypdf", "pdftotext"])
    args = ap.parse_args(argv)

    if not os.path.isfile(args.source):
        _die(2, "source not found: %s" % args.source)

    ext = os.path.splitext(args.source)[1].lower()
    if ext in (".md", ".markdown", ".txt"):
        text, headings = extract_markdown(args.source)
    elif ext == ".docx":
        text, headings = extract_docx(args.source)
        if len(text.strip()) < MIN_BODY_CHARS and not headings:
            _die(1, "extracted <%d chars from docx (scanned?)" % MIN_BODY_CHARS)
    elif ext == ".pdf":
        text, headings = extract_pdf(args.source, args.pdf_tool)
        if len(text.strip()) < MIN_BODY_CHARS:
            _die(1, "extracted <%d chars from pdf (scanned?)" % MIN_BODY_CHARS)
    else:
        _die(2, "unsupported source extension: %s" % ext)

    os.makedirs(os.path.dirname(os.path.abspath(args.text_out)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.text_out, "w", encoding="utf-8") as f:
        f.write(text)

    manifest = {
        "source_file": os.path.abspath(args.source),
        "text_file": args.text_out,
        "text_len": len(text),
        "headings": headings,
        "warning": None if headings else "no_heading_detected",
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    _emit({"ok": True, "exit": 0, "headings": len(headings),
           "headless": not headings, "text_len": len(text)})
    sys.exit(0)


if __name__ == "__main__":
    main()

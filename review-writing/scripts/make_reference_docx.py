#!/usr/bin/env python3
"""Bake the docx style template for Phase 4 export.

Takes the pandoc default reference.docx (generated via
`pandoc --print-default-data-file reference.docx > templates/reference.docx`)
and locks the typography to the English-review house style:

  - Body styles (Normal / Body Text / First Paragraph): Times New Roman 12pt.
  - Heading styles: Times New Roman, bold, with descending sizes.

Both the ASCII font and the eastAsia font are set so an occasional CJK glyph
(e.g. a species author name) cannot trigger a fallback to a different face.

Idempotent: re-running on an already-baked template produces the same result.
Run after regenerating the pandoc default to re-apply the house style.
"""

from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

# --- House-style constants (single source of truth) -------------------------
BODY_FONT = "Times New Roman"   # ASCII/Latin face for all text
EASTASIA_FONT = "Times New Roman"  # force CJK runs onto the same face (anti-fallback)
BODY_SIZE_PT = 12

# Paragraph styles that carry running body text.
BODY_STYLES = ["Normal", "Body Text", "First Paragraph"]

# Heading style -> point size. All headings are bold TNR.
HEADING_SIZES = {
    "Title": 18,
    "Heading 1": 16,
    "Heading 2": 14,
    "Heading 3": 12,
}

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "reference.docx"


def _set_font(style, *, size_pt, bold=None):
    """Apply font face + size (+ optional bold) to a paragraph style.

    Sets the ASCII run font via python-docx, then writes the eastAsia attribute
    directly on the rFonts element so CJK glyphs use the same face instead of
    silently falling back to a default CJK font.
    """
    font = style.font
    font.name = BODY_FONT
    font.size = Pt(size_pt)
    if bold is not None:
        font.bold = bold

    # rPr/rFonts may not exist on a bare style; get_or_add creates them.
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), EASTASIA_FONT)
    rfonts.set(qn("w:ascii"), BODY_FONT)
    rfonts.set(qn("w:hAnsi"), BODY_FONT)


def main():
    if not TEMPLATE.exists():
        raise SystemExit(
            f"Base template not found: {TEMPLATE}\n"
            "Generate it first:\n"
            "  pandoc --print-default-data-file reference.docx > "
            f"{TEMPLATE}"
        )

    doc = Document(str(TEMPLATE))
    style_names = {s.name for s in doc.styles}

    for name in BODY_STYLES:
        if name in style_names:
            _set_font(doc.styles[name], size_pt=BODY_SIZE_PT)

    for name, size in HEADING_SIZES.items():
        if name in style_names:
            _set_font(doc.styles[name], size_pt=size, bold=True)

    doc.save(str(TEMPLATE))
    print(f"Baked house style into {TEMPLATE}")
    print(f"  body styles  {BODY_STYLES} -> {BODY_FONT} {BODY_SIZE_PT}pt")
    for name, size in HEADING_SIZES.items():
        print(f"  {name:<10} -> {BODY_FONT} {size}pt bold")


if __name__ == "__main__":
    main()

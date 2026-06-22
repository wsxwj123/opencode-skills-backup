"""Generate / refresh the pandoc reference.docx that locks SCI manuscript fonts.

Opens templates/reference.docx (the pandoc baseline produced by
`pandoc --print-default-data-file reference.docx`) and forces key paragraph
styles to Times New Roman with explicit point sizes, so that `/merge`'s pandoc
export yields a docx whose body is TNR 12pt and whose headings are TNR bold.

The script is IDEMPOTENT: re-running it on an already-processed file produces
the same result. Run it after editing the FONT/SIZE constants below.

Usage:
    python scripts/make_reference_docx.py

Requires: python-docx. The baseline templates/reference.docx must already exist
(regenerate with: pandoc --print-default-data-file reference.docx > templates/reference.docx).
"""

from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

# ---------------------------------------------------------------------------
# TUNABLES — edit these to change the locked fonts/sizes, then re-run the script.
# ---------------------------------------------------------------------------
FONT_NAME = "Times New Roman"  # applied to Latin, complex-script AND East-Asian slots

# Body-text styles: name -> point size. Set to TNR 12pt (standard SCI manuscript).
BODY_STYLES = {
    "Normal": 12,           # base style everything inherits from
    "Body Text": 12,        # pandoc wraps most paragraphs in Body Text
    "First Paragraph": 12,  # first paragraph after a heading
    "Compact": 12,          # tight paragraphs / list items
    "Bibliography": 12,     # reference list entries (keep consistent with body)
}

# Heading / title styles: name -> (point size, bold). TNR bold, descending sizes.
HEADING_STYLES = {
    "Title": (18, True),
    "Heading 1": (16, True),
    "Heading 2": (14, True),
    "Heading 3": (12, True),
}

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "reference.docx"


def set_style_font(style, size_pt, bold=None):
    """Force a style's font name + size, including the East-Asian font slot.

    Setting font.name only writes the Latin (w:ascii/hAnsi) slot; we also write
    w:eastAsia so an occasional CJK glyph or locale fallback cannot swap the
    body to a different face mid-document.
    """
    font = style.font
    font.name = FONT_NAME
    font.size = Pt(size_pt)
    if bold is not None:
        font.bold = bold

    rfonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), FONT_NAME)
    # Also pin ascii/hAnsi/cs at the XML level so the eastAsia write can't leave
    # the other slots inconsistent across python-docx versions.
    rfonts.set(qn("w:ascii"), FONT_NAME)
    rfonts.set(qn("w:hAnsi"), FONT_NAME)
    rfonts.set(qn("w:cs"), FONT_NAME)


def main():
    if not TEMPLATE_PATH.exists():
        raise SystemExit(
            f"baseline template not found: {TEMPLATE_PATH}\n"
            "regenerate it first:\n"
            "  pandoc --print-default-data-file reference.docx > templates/reference.docx"
        )

    doc = Document(str(TEMPLATE_PATH))
    styles = {s.name: s for s in doc.styles}

    applied = []
    for name, size in BODY_STYLES.items():
        if name in styles:
            set_style_font(styles[name], size)
            applied.append(f"{name} -> {FONT_NAME} {size}pt")

    for name, (size, bold) in HEADING_STYLES.items():
        if name in styles:
            set_style_font(styles[name], size, bold=bold)
            applied.append(f"{name} -> {FONT_NAME} {size}pt bold={bold}")

    doc.save(str(TEMPLATE_PATH))

    print(f"wrote {TEMPLATE_PATH}")
    for line in applied:
        print("  " + line)


if __name__ == "__main__":
    main()

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

DEFAULT_PATTERNS = [
    "01_Abstract*.md",
    "02_Introduction*.md",
    "03_Methods*.md",
    "04_Results*.md",
    "05_Discussion*.md",
    "06_Conclusion*.md",
    "07_References*.md",
    "*.md",
]


def natural_key(text):
    return [int(tok) if tok.isdigit() else tok.lower() for tok in re.split(r"(\d+)", text)]


def leading_index(path):
    name = os.path.basename(path)
    m = re.match(r"^\s*(\d+)", name)
    return int(m.group(1)) if m else 9999


def discover_markdown_files(manuscript_dir, patterns):
    included = []
    seen = set()
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(manuscript_dir, pattern)), key=natural_key):
            name = os.path.basename(path)
            if name.lower() in {"full_manuscript.md"}:
                continue
            if path in seen:
                continue
            seen.add(path)
            included.append(path)
    included.sort(key=lambda p: (leading_index(p), natural_key(os.path.basename(p))))
    return included


def load_references(index_file):
    if not os.path.exists(index_file):
        return []
    with open(index_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("references", "items", "entries", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def format_reference_entry(entry, number, style="vancouver"):
    if not isinstance(entry, dict):
        return f"{number}. {str(entry).strip()}"
    citation = str(entry.get("citation") or "").strip()
    if citation:
        return f"{number}. {citation}"
    if style == "nature":
        authors = entry.get("authors") or entry.get("author") or "Unknown Author"
        title = entry.get("title") or "Untitled"
        journal = entry.get("journal") or "Unknown Journal"
        year = entry.get("year") or "n.d."
        volume = entry.get("volume") or ""
        pages = entry.get("pages") or ""
        vol_pages = f"{volume}, {pages}".strip(", ").strip()
        if vol_pages:
            return f"{number}. {authors}. {title}. {journal} {vol_pages} ({year})."
        return f"{number}. {authors}. {title}. {journal} ({year})."
    authors = entry.get("authors") or entry.get("author") or "Unknown Author"
    title = entry.get("title") or "Untitled"
    journal = entry.get("journal") or "Unknown Journal"
    year = entry.get("year") or "n.d."
    volume = entry.get("volume") or ""
    pages = entry.get("pages") or ""
    tail = f"{year};{volume}:{pages}".strip(":").strip(";")
    doi = entry.get("doi") or ""
    doi_part = f" doi:{doi}" if doi else ""
    if tail:
        return f"{number}. {authors}. {title}. {journal}. {tail}.{doi_part}".rstrip()
    return f"{number}. {authors}. {title}. {journal}.{doi_part}".rstrip()


def split_out_references_section(content):
    """Remove markdown References/参考文献 block and return body + extracted entries."""
    lines = content.splitlines()
    out = []
    refs = []
    in_refs = False
    current = None
    ref_heading = re.compile(r"^\s{0,3}#{1,6}\s*(references|参考文献)\s*$", re.IGNORECASE)
    next_heading = re.compile(r"^\s{0,3}#{1,6}\s+")
    numbered = re.compile(r"^\s*(\d+)\.\s+(.*)\s*$")
    for line in lines:
        if not in_refs and ref_heading.match(line):
            in_refs = True
            current = None
            continue
        if in_refs:
            if next_heading.match(line):
                in_refs = False
                current = None
                out.append(line)
                continue
            m = numbered.match(line)
            if m:
                refs.append(m.group(2).strip())
                current = len(refs) - 1
                continue
            if current is not None and line.strip():
                refs[current] = (refs[current] + " " + line.strip()).strip()
            continue
        out.append(line)
    body = "\n".join(out).strip()
    return body, refs


def merge_markdown_files(files, relocate_references=False):
    parts = []
    local_refs = []
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if relocate_references:
            content, refs = split_out_references_section(content)
            local_refs.extend(refs)
        if content:
            parts.append(content)
    merged = "\n\n---\n\n".join(parts).strip() + ("\n" if parts else "")
    return merged, local_refs


def convert_docx(output_md, output_docx, reference_doc=None):
    pandoc_bin = shutil.which("pandoc")
    if not pandoc_bin:
        return {
            "attempted": False,
            "ok": False,
            "reason": "pandoc_not_found",
            "message": "Pandoc not found in PATH. Docx generation skipped."
        }
    cmd = [pandoc_bin, output_md, "-o", output_docx]
    if reference_doc:
        cmd.extend(["--reference-doc", reference_doc])
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {"attempted": True, "ok": True, "output_docx": output_docx}
    except subprocess.CalledProcessError as e:
        return {
            "attempted": True,
            "ok": False,
            "reason": "pandoc_failed",
            "stderr": (e.stderr or "").strip()
        }


def run_merge(manuscript_dir, output_md, output_docx, patterns, generate_docx, reference_doc=None, allow_empty=False):
    if not os.path.isdir(manuscript_dir):
        return {"ok": False, "error": f"manuscript_dir not found: {manuscript_dir}"}

    files = discover_markdown_files(manuscript_dir, patterns)
    if not files and not allow_empty:
        return {"ok": False, "error": "no manuscript markdown files matched patterns", "patterns": patterns}

    merged, local_refs = merge_markdown_files(files, relocate_references=True)
    global_refs = load_references(os.path.join(os.path.dirname(output_md) or ".", "literature_index.json"))
    if not global_refs:
        global_refs = load_references("literature_index.json")

    reference_lines = []
    if global_refs:
        reference_lines = [format_reference_entry(ref, i + 1, style="vancouver") for i, ref in enumerate(global_refs)]
    elif local_refs:
        # fallback: de-duplicate local references while keeping order
        seen = set()
        for r in local_refs:
            key = r.strip().lower()
            if key and key not in seen:
                seen.add(key)
                reference_lines.append(f"{len(reference_lines) + 1}. {r.strip()}")

    if reference_lines:
        merged = merged.rstrip() + "\n\n# References\n\n" + "\n".join(reference_lines) + "\n"
    os.makedirs(os.path.dirname(output_md) or ".", exist_ok=True)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(merged)

    result = {
        "ok": True,
        "manuscript_dir": manuscript_dir,
        "output_md": output_md,
        "files_merged_count": len(files),
        "files_merged": files,
        "references_relocated": True,
        "references_count": len(reference_lines),
        "docx": {"attempted": False, "ok": False},
    }

    if generate_docx:
        docx_report = convert_docx(output_md=output_md, output_docx=output_docx, reference_doc=reference_doc)
        result["docx"] = docx_report
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Merge manuscript markdown files and optionally generate docx")
    parser.add_argument("--manuscript-dir", default="manuscripts", help="Directory containing section markdown files")
    parser.add_argument("--output-md", default=None, help="Output merged markdown path")
    parser.add_argument("--output-docx", default=None, help="Output docx path")
    parser.add_argument("--patterns", default=",".join(DEFAULT_PATTERNS), help="Comma-separated glob patterns")
    parser.add_argument("--skip-docx", action="store_true", help="Skip docx conversion")
    parser.add_argument("--reference-doc", help="Optional pandoc reference docx template")
    parser.add_argument("--allow-empty", action="store_true", help="Allow producing an empty merged file")
    return parser.parse_args()


def main():
    args = parse_args()
    output_md = args.output_md or os.path.join(args.manuscript_dir, "Full_Manuscript.md")
    output_docx = args.output_docx or os.path.join(args.manuscript_dir, "Full_Manuscript.docx")
    patterns = [p.strip() for p in args.patterns.split(",") if p.strip()]
    report = run_merge(
        manuscript_dir=args.manuscript_dir,
        output_md=output_md,
        output_docx=output_docx,
        patterns=patterns,
        generate_docx=(not args.skip_docx),
        reference_doc=args.reference_doc,
        allow_empty=args.allow_empty,
    )
    print(json.dumps(report, ensure_ascii=False))
    if not report.get("ok", False):
        sys.exit(2)


if __name__ == "__main__":
    main()

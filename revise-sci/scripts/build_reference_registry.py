#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import autodiscover_reference_source, normalize_ws, read_docx_paragraphs, read_json, write_json, write_text


HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(references|reference|参考文献)\s*$", re.IGNORECASE)
NEXT_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S+")
NUMBERED_REF_RE = re.compile(r"^\s*(\d+)[\.\)]\s+(.*)$")
INLINE_NUMERIC_CITATION_RE = re.compile(r"\[(\d+(?:\s*[-,–]\s*\d+)*)\]")
AUTHOR_YEAR_PAREN_RE = re.compile(r"\(([A-Z][A-Za-z'`-]+(?:\s+et al\.)?),\s*((?:19|20)\d{2}[a-z]?)\)")
AUTHOR_YEAR_NARRATIVE_RE = re.compile(r"\b([A-Z][A-Za-z'`-]+(?:\s+et al\.)?)\s*\(((?:19|20)\d{2}[a-z]?)\)")
AUTHOR_YEAR_IN_MULTI_PAREN_RE = re.compile(r"([A-Z][A-Za-z'`-]+(?:\s+et al\.)?),\s*((?:19|20)\d{2}[a-z]?)")


def split_reference_section(text: str) -> tuple[str, list[str], bool]:
    lines = text.splitlines()
    start = None
    end = len(lines)
    for idx, line in enumerate(lines):
        if HEADING_RE.match(line):
            start = idx
            break
    if start is None:
        return text, [], False
    for idx in range(start + 1, len(lines)):
        if NEXT_HEADING_RE.match(lines[idx]):
            end = idx
            break
    body_lines = lines[:start] + lines[end:]
    reference_lines = [line for line in lines[start + 1 : end] if normalize_ws(line)]
    return "\n".join(body_lines), reference_lines, True


def normalize_reference_key(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"doi:\s*10\.\S+", "", lowered)
    lowered = re.sub(r"pmid:\s*\d+", "", lowered)
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def build_registry(reference_lines: list[str]) -> list[dict]:
    registry: list[dict] = []
    next_number = 1
    for line in reference_lines:
        match = NUMBERED_REF_RE.match(line)
        if match:
            number = int(match.group(1))
            raw_text = normalize_ws(match.group(2))
            next_number = max(next_number, number + 1)
        else:
            number = next_number
            raw_text = normalize_ws(line)
            next_number += 1
        registry.append(
            {
                "reference_number": number,
                "raw_text": raw_text,
                "normalized_key": normalize_reference_key(raw_text),
                "provider_family": "user-provided",
                "source_tier": "manuscript-reference",
                "verified": False,
            }
        )
    return registry


def registry_to_reference_lines(registry: list[dict]) -> list[str]:
    lines = []
    for entry in sorted(registry, key=lambda item: item.get("reference_number", 0)):
        number = int(entry.get("reference_number") or 0)
        raw_text = normalize_ws(str(entry.get("raw_text") or ""))
        if not raw_text:
            continue
        lines.append(f"{number}. {raw_text}" if number else raw_text)
    return lines


def build_reference_entry_from_fields(entry: dict, fallback_number: int) -> str:
    raw = normalize_ws(str(entry.get("reference_entry") or entry.get("raw_text") or entry.get("text") or ""))
    if raw:
        return raw
    authors = entry.get("authors") or []
    if isinstance(authors, list):
        authors_text = ", ".join(normalize_ws(str(author)) for author in authors if normalize_ws(str(author)))
    else:
        authors_text = normalize_ws(str(authors))
    title = normalize_ws(str(entry.get("title") or f"Reference {fallback_number}"))
    journal = normalize_ws(str(entry.get("journal") or entry.get("venue") or ""))
    year = normalize_ws(str(entry.get("year") or ""))
    doi = normalize_ws(str(entry.get("doi") or ""))
    pmid = normalize_ws(str(entry.get("pmid") or ""))
    parts = []
    if authors_text:
        parts.append(f"{authors_text}.")
    parts.append(f"{title}.")
    if journal:
        parts.append(f"{journal}.")
    if year:
        parts.append(f"{year}.")
    if doi:
        parts.append(f"DOI: {doi}.")
    if pmid:
        parts.append(f"PMID: {pmid}.")
    return " ".join(part for part in parts if part).strip()


def parse_seed_json(path: Path) -> list[str]:
    payload = read_json(path, {})
    if isinstance(payload, dict):
        entries = payload.get("entries") or payload.get("results") or payload.get("references") or []
    elif isinstance(payload, list):
        entries = payload
    else:
        entries = []
    lines = []
    for idx, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            lines.append(normalize_ws(str(entry)))
            continue
        lines.append(build_reference_entry_from_fields(entry, idx))
    return [line for line in lines if normalize_ws(line)]


def parse_seed_docx(path: Path) -> list[str]:
    rows = read_docx_paragraphs(path)
    texts = [row["text"] for row in rows if normalize_ws(row["text"])]
    _, reference_lines, found = split_reference_section("\n".join(texts))
    if found and reference_lines:
        return reference_lines
    return [text for text in texts if NUMBERED_REF_RE.match(text)]


def parse_seed_bib(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    entries = re.split(r"(?=@\w+\s*\{)", text)
    lines = []
    for idx, block in enumerate(entries, start=1):
        if "title" not in block.lower():
            continue
        def grab(field: str) -> str:
            match = re.search(rf"{field}\s*=\s*[\{{\"](.+?)[\}}\"],?\s*$", block, flags=re.IGNORECASE | re.MULTILINE)
            return normalize_ws(match.group(1)) if match else ""
        entry = {
            "authors": grab("author"),
            "title": grab("title"),
            "journal": grab("journal") or grab("booktitle"),
            "year": grab("year"),
            "doi": grab("doi"),
            "pmid": grab("pmid"),
        }
        lines.append(build_reference_entry_from_fields(entry, idx))
    return [line for line in lines if normalize_ws(line)]


def parse_seed_ris(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    records = re.split(r"(?m)^ER\s*-\s*$", text)
    lines = []
    for idx, block in enumerate(records, start=1):
        tags: dict[str, list[str]] = {}
        for raw_line in block.splitlines():
            match = re.match(r"^([A-Z0-9]{2})\s*-\s*(.*)$", raw_line.strip())
            if not match:
                continue
            tags.setdefault(match.group(1), []).append(normalize_ws(match.group(2)))
        if not tags:
            continue
        year_field = next((key for key in ("PY", "Y1", "DA") if tags.get(key)), "")
        year_text = tags.get(year_field, [""])[0] if year_field else ""
        year_match = re.search(r"(19|20)\d{2}", year_text)
        entry = {
            "authors": tags.get("AU", []) or tags.get("A1", []),
            "title": (tags.get("TI", []) or tags.get("T1", []) or tags.get("CT", [""]))[0],
            "journal": (tags.get("JO", []) or tags.get("JF", []) or tags.get("T2", [""]))[0],
            "year": year_match.group(0) if year_match else "",
            "doi": (tags.get("DO", [""]))[0],
            "pmid": (tags.get("AN", [""]))[0],
        }
        lines.append(build_reference_entry_from_fields(entry, idx))
    return [line for line in lines if normalize_ws(line)]


def load_reference_source_lines(path: Path | None) -> tuple[list[str], str]:
    if path is None or not path.exists():
        return [], ""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_seed_json(path), str(path.resolve())
    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        _, reference_lines, found = split_reference_section(text)
        if found and reference_lines:
            return reference_lines, str(path.resolve())
        return [line for line in text.splitlines() if normalize_ws(line)], str(path.resolve())
    if suffix == ".docx":
        return parse_seed_docx(path), str(path.resolve())
    if suffix == ".bib":
        return parse_seed_bib(path), str(path.resolve())
    if suffix == ".ris":
        return parse_seed_ris(path), str(path.resolve())
    return [], str(path.resolve())


def rewrite_references_section(output_md: Path, body_text: str, reference_lines: list[str], references_found: bool) -> None:
    body = body_text.rstrip()
    lines = body.splitlines() if body else []
    if lines and normalize_ws(lines[-1]):
        lines.append("")
    lines.append("## References")
    lines.append("")
    lines.extend(reference_lines)
    write_text(output_md, "\n".join(lines).rstrip() + "\n")


def expand_citation_numbers(payload: str) -> list[int]:
    numbers: list[int] = []
    for chunk in re.split(r"\s*,\s*", payload.replace("–", "-").strip()):
        if not chunk:
            continue
        if "-" in chunk:
            start_str, end_str = [part.strip() for part in chunk.split("-", 1)]
            if start_str.isdigit() and end_str.isdigit():
                start = int(start_str)
                end = int(end_str)
                if start <= end:
                    numbers.extend(range(start, end + 1))
                else:
                    numbers.extend([start, end])
            continue
        if chunk.isdigit():
            numbers.append(int(chunk))
    return numbers


def detect_cited_numbers(body_text: str) -> list[int]:
    cited = set()
    for match in INLINE_NUMERIC_CITATION_RE.finditer(body_text):
        cited.update(expand_citation_numbers(match.group(1)))
    return sorted(cited)


def normalize_author_year_key(author: str, year: str) -> str:
    surname = normalize_ws(author).lower().replace(" et al.", "")
    surname = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", surname)
    return f"{surname}|{normalize_ws(year)}"


def detect_author_year_citations(body_text: str) -> list[str]:
    citations: set[str] = set()
    for match in AUTHOR_YEAR_PAREN_RE.finditer(body_text):
        citations.add(normalize_author_year_key(match.group(1), match.group(2)))
    for match in AUTHOR_YEAR_NARRATIVE_RE.finditer(body_text):
        citations.add(normalize_author_year_key(match.group(1), match.group(2)))
    for parenthetical in re.findall(r"\(([^)]*;\s*[^)]*)\)", body_text):
        for match in AUTHOR_YEAR_IN_MULTI_PAREN_RE.finditer(parenthetical):
            citations.add(normalize_author_year_key(match.group(1), match.group(2)))
    return sorted(citations)


def reference_author_year_keys(registry: list[dict]) -> list[str]:
    keys: set[str] = set()
    for entry in registry:
        raw_text = normalize_ws(str(entry.get("raw_text") or ""))
        if not raw_text:
            continue
        year_match = re.search(r"\b((?:19|20)\d{2}[a-z]?)\b", raw_text)
        author_match = re.match(r"^[\[\]\d\.\)\s]*([A-Z][A-Za-z'`-]+)", raw_text)
        if year_match and author_match:
            keys.add(normalize_author_year_key(author_match.group(1), year_match.group(1)))
    return sorted(keys)


def merge_missing_numeric_references(current_registry: list[dict], source_registry: list[dict], missing_numbers: list[int]) -> tuple[list[dict], list[int]]:
    if not missing_numbers:
        return current_registry, []
    current_by_number = {int(entry.get("reference_number") or 0): dict(entry) for entry in current_registry}
    source_by_number = {int(entry.get("reference_number") or 0): dict(entry) for entry in source_registry}
    imported_numbers: list[int] = []
    for number in missing_numbers:
        if number in current_by_number or number not in source_by_number:
            continue
        current_by_number[number] = dict(source_by_number[number])
        imported_numbers.append(number)
    merged = [current_by_number[number] for number in sorted(current_by_number)]
    return merged, imported_numbers


def write_reference_recovery_request(project_root: Path, report: dict) -> None:
    request_path = project_root / "reference_recovery_request.md"
    missing_numbers = report.get("missing_reference_numbers", [])
    missing_author_year = report.get("missing_author_year_citations", [])
    if not missing_numbers and not missing_author_year:
        if request_path.exists():
            request_path.unlink()
        return
    lines = [
        "# Reference Recovery Request",
        "",
        "当前主稿中的正文引文尚未被现有参考文献源完整覆盖，因此该项目不能被视为可直接投稿版本。",
        "",
        "## 缺失概览",
        "",
        f"- citation_style: {report.get('citation_style', 'unknown')}",
        f"- missing_reference_numbers: {', '.join(str(number) for number in missing_numbers) if missing_numbers else '无'}",
        f"- missing_author_year_citations: {', '.join(missing_author_year) if missing_author_year else '无'}",
        f"- current_reference_source: {report.get('reference_source') or 'Not provided by user'}",
        "",
        "## 需作者补充的材料",
        "",
        "- 请提供同一篇稿件的完整旧版参考文献源，推荐格式：.docx/.bib/.ris/.json/.md/.txt",
        "- 如果当前稿件采用数字引文，请优先提供带完整编号的旧稿或 Bib/RIS 文件。",
        "- 如果当前稿件采用 author-year 引文，请优先提供完整参考文献列表，并确保作者-年份信息可唯一对应。",
        "",
        "## 处理原则",
        "",
        "- 系统不会凭空生成或猜测缺失的历史参考文献条目。",
        "- 在未获得可追溯的参考文献源之前，相关缺口会持续阻断 strict gate。",
        "",
    ]
    write_text(request_path, "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical reference registry and coverage audit from merged manuscript markdown")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--references-source", default="")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    output_md = Path(args.output_md)
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    state = read_json(project_root / "project_state.json", {})
    inputs = state.get("inputs", {}) if isinstance(state, dict) else {}
    references_source = (
        Path(args.references_source).resolve()
        if args.references_source
        else autodiscover_reference_source(
            Path(inputs["comments_path"]) if inputs.get("comments_path") else None,
            Path(inputs["attachments_dir_path"]) if inputs.get("attachments_dir_path") else None,
            project_root,
            Path(inputs["manuscript_docx_path"]) if inputs.get("manuscript_docx_path") else None,
        )
    )

    if not output_md.exists():
        write_json(data_dir / "reference_registry.json", [])
        report = {
            "ok": True,
            "citation_style": "none",
            "references_section_found": False,
            "reference_entries": 0,
            "cited_numbers": [],
            "available_reference_numbers": [],
            "missing_reference_numbers": [],
            "reference_source": str(references_source) if references_source else "",
        }
        write_json(data_dir / "reference_coverage_audit.json", report)
        write_reference_recovery_request(project_root, report)
        print(json.dumps({"ok": True, "reference_entries": 0, "cited_numbers": 0}, ensure_ascii=False))
        return 0

    text = output_md.read_text(encoding="utf-8")
    body_text, reference_lines, references_found = split_reference_section(text)
    imported_lines: list[str] = []
    imported_source = ""
    cited_numbers = detect_cited_numbers(body_text)
    author_year_citations = detect_author_year_citations(body_text)

    if not reference_lines:
        imported_lines, imported_source = load_reference_source_lines(references_source)
        if imported_lines:
            reference_lines = imported_lines
            rewrite_references_section(output_md, body_text, reference_lines, references_found)
            text = output_md.read_text(encoding="utf-8")
            body_text, reference_lines, references_found = split_reference_section(text)

    registry = build_registry(reference_lines)
    missing_numbers: list[int] = []
    imported_reference_numbers: list[int] = []
    if cited_numbers:
        available_numbers = sorted({entry["reference_number"] for entry in registry})
        missing_numbers = [number for number in cited_numbers if number not in set(available_numbers)]
        if missing_numbers and references_source is not None:
            imported_lines, imported_source = load_reference_source_lines(references_source)
            if imported_lines:
                source_registry = build_registry(imported_lines)
                registry, imported_reference_numbers = merge_missing_numeric_references(registry, source_registry, missing_numbers)
                if imported_reference_numbers:
                    reference_lines = registry_to_reference_lines(registry)
                    rewrite_references_section(output_md, body_text, reference_lines, references_found)
                    text = output_md.read_text(encoding="utf-8")
                    body_text, reference_lines, references_found = split_reference_section(text)
                    registry = build_registry(reference_lines)

    write_json(data_dir / "reference_registry.json", registry)

    available_numbers = sorted({entry["reference_number"] for entry in registry})
    missing_numbers = [number for number in cited_numbers if number not in set(available_numbers)]
    available_author_year_keys = reference_author_year_keys(registry)
    missing_author_year_citations = [key for key in author_year_citations if key not in set(available_author_year_keys)]
    if cited_numbers and author_year_citations:
        citation_style = "mixed"
    elif cited_numbers:
        citation_style = "numeric"
    elif author_year_citations:
        citation_style = "author-year"
    else:
        citation_style = "none"
    report = {
        "ok": not missing_numbers and not missing_author_year_citations,
        "citation_style": citation_style,
        "references_section_found": references_found,
        "reference_entries": len(registry),
        "cited_numbers": cited_numbers,
        "available_reference_numbers": available_numbers,
        "missing_reference_numbers": missing_numbers,
        "author_year_citations": author_year_citations,
        "available_author_year_keys": available_author_year_keys,
        "missing_author_year_citations": missing_author_year_citations,
        "max_cited_number": max(cited_numbers) if cited_numbers else 0,
        "reference_source": imported_source,
        "imported_reference_numbers": imported_reference_numbers,
    }
    write_json(data_dir / "reference_coverage_audit.json", report)
    write_reference_recovery_request(project_root, report)
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "reference_entries": len(registry),
                "cited_numbers": len(cited_numbers),
                "missing_reference_numbers": missing_numbers,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

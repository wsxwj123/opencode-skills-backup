from __future__ import annotations

import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from docx import Document


BANNED_PLACEHOLDER_MARKERS = ("{{", "待ai", "ai_fill_required")
ALLOWED_PROVIDER_FAMILIES = {"paper-search", "user-provided"}


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").lower()
    return cleaned or "section"


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def path_signature(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": "", "exists": False}
    resolved = path.resolve()
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    stat = resolved.stat()
    return {
        "path": str(resolved),
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def directory_signature(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": "", "exists": False, "files": []}
    resolved = path.resolve()
    if not resolved.exists() or not resolved.is_dir():
        return {"path": str(resolved), "exists": False, "files": []}
    files = []
    for item in sorted(resolved.iterdir()):
        if not item.is_file():
            continue
        stat = item.stat()
        files.append({"name": item.name, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return {"path": str(resolved), "exists": True, "files": files}


def read_docx_paragraphs(path: Path) -> list[dict[str, Any]]:
    doc = Document(str(path))
    rows: list[dict[str, Any]] = []
    for i, paragraph in enumerate(doc.paragraphs):
        text = normalize_ws(paragraph.text)
        if not text:
            continue
        style_name = normalize_ws(getattr(getattr(paragraph, "style", None), "name", "") or "")
        rows.append({"paragraph_index": i, "text": text, "style_name": style_name})
    return rows


def is_heading(row: dict[str, Any]) -> bool:
    style_name = row.get("style_name", "").lower()
    text = row.get("text", "")
    if style_name.startswith("heading"):
        return True
    if len(text.split()) <= 8 and text.lower() in {
        "abstract",
        "introduction",
        "background",
        "methods",
        "materials and methods",
        "results",
        "discussion",
        "conclusion",
        "supplementary methods",
        "supplementary results",
    }:
        return True
    return False


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?;])\s+", normalize_ws(text))
    return [p for p in parts if p]


def tokenize(text: str) -> set[str]:
    return {tok.lower() for tok in re.findall(r"[A-Za-z0-9]+", text or "")}


def choose_sentence(comment_text: str, paragraph_text: str) -> tuple[int, str]:
    sentences = split_sentences(paragraph_text)
    if not sentences:
        return 0, ""
    query = tokenize(comment_text)
    best_index = 0
    best_score = -1
    for idx, sentence in enumerate(sentences):
        score = len(query.intersection(tokenize(sentence)))
        if score > best_score:
            best_score = score
            best_index = idx
    return best_index, sentences[best_index]


def detect_comment_requirements(comment_text: str) -> dict[str, bool]:
    lowered = comment_text.lower()
    return {
        "needs_experiment": bool(re.search(r"\b(experiment|assay|animal|western blot|validate|replicate)\b", lowered)),
        "needs_citation": bool(re.search(r"\b(reference|references|citation|citations|literature|pubmed)\b", lowered)),
        "needs_figure": bool(re.search(r"\b(figure|fig\.?|table|legend|panel|supplementary)\b", lowered)),
    }


def comment_nature(comment_text: str) -> str:
    requirements = detect_comment_requirements(comment_text)
    if requirements["needs_experiment"]:
        return "需要新增实验或结果支持"
    if requirements["needs_citation"]:
        return "需要新增或核验文献支持"
    if requirements["needs_figure"]:
        return "需要核对图表、图注或补充材料"
    return "需要对现有表述进行澄清或收束"


def build_section_markdown(section: dict[str, Any]) -> str:
    parts = [f"# {section['heading']}"]
    for paragraph in section.get("paragraphs", []):
        parts.append("")
        parts.append(paragraph.get("current_text") or paragraph["text"])
    return "\n".join(parts).strip() + "\n"


def blocked_placeholder_found(value: object) -> bool:
    text = normalize_ws(str(value or "")).lower()
    if not text:
        return True
    return any(marker in text for marker in BANNED_PLACEHOLDER_MARKERS)


class AtomicCommentHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.units: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._chunks: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "") or ""
        if tag == "div" and "comment-unit" in class_name:
            self._current = {
                "comment_id": attrs_dict.get("data-comment-id", "") or "",
                "reviewer": attrs_dict.get("data-reviewer", "") or "Reviewer #1",
                "severity": (attrs_dict.get("data-severity", "") or "major").lower(),
            }
            self._chunks = []
            self._depth = 1
            return
        if self._current is not None:
            self._depth += 1

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            text = normalize_ws(data)
            if text:
                self._chunks.append(text)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        self._depth -= 1
        if self._depth <= 0:
            payload = dict(self._current)
            payload["comment_text"] = normalize_ws(" ".join(self._chunks))
            self.units.append(payload)
            self._current = None
            self._chunks = []
            self._depth = 0

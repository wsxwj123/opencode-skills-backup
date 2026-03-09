from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from docx import Document
from docx.opc.exceptions import PackageNotFoundError


BANNED_PLACEHOLDER_MARKERS = ("{{", "待ai", "ai_fill_required")
ALLOWED_PROVIDER_FAMILIES = {"paper-search", "user-provided"}
REFERENCE_SOURCE_NAME_RE = re.compile(r"(reference|references|bibliography|literature_index|refs?)", re.IGNORECASE)
REFERENCE_SOURCE_EXTS = {".json", ".md", ".txt", ".docx", ".bib", ".ris"}
MANUSCRIPT_VERSION_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")
NON_MEANINGFUL_TEXT_VALUES = {
    "",
    "无",
    "none",
    "n/a",
    "na",
    "not provided by user",
    "not provided",
    "not available",
    "ai_fill_required",
    "待ai",
}
AI_STYLE_BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    ("delve into", r"\bdelve into\b"),
    ("comprehensive landscape", r"\bcomprehensive landscape\b"),
    ("pivotal role", r"\bpivotal role\b"),
    ("realm", r"\brealm\b"),
    ("tapestry", r"\btapestry\b"),
    ("underscore", r"\bunderscore(?:s|d)?\b"),
    ("testament", r"\btestament\b"),
    ("Moreover", r"\bMoreover\b"),
    ("Crucial", r"\bCrucial\b"),
    ("Landscape", r"\bLandscape\b"),
    ("Pivot", r"\bPivot(?:s|ed|ing)?\b"),
    ("Foster", r"\bFoster(?:s|ed|ing)?\b"),
    ("Spearhead", r"\bSpearhead(?:s|ed|ing)?\b"),
    ("It is worth noting", r"\bIt is worth noting\b"),
    ("As mentioned above", r"\bAs mentioned above\b"),
    ("serves as", r"\bserves as\b"),
    ("acts as", r"\bacts as\b"),
)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def is_meaningful_text(text: str) -> bool:
    normalized = normalize_ws(text).lower()
    return normalized not in NON_MEANINGFUL_TEXT_VALUES


def find_ai_style_markers(text: str) -> list[str]:
    normalized = normalize_ws(text)
    if not normalized:
        return []
    markers: list[str] = []
    for label, pattern in AI_STYLE_BANNED_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            markers.append(label)
    if "—" in normalized:
        markers.append("em dash")
    if re.search(r"\bnot only\b.*\bbut also\b", normalized, flags=re.IGNORECASE):
        markers.append("not only...but also")
    if re.search(r"\bfrom\s+[A-Za-z0-9].+?\s+to\s+[A-Za-z0-9]", normalized, flags=re.IGNORECASE):
        markers.append("from A to B")
    if "?" in normalized:
        markers.append("rhetorical question")
    if re.search(r",\s*(?:thus|thereby|therefore)\s+[A-Za-z-]+ing\b", normalized, flags=re.IGNORECASE):
        markers.append("trailing -ing clause")
    return markers


def polish_changed_text_locally(text: str) -> str:
    cleaned = normalize_ws(text)
    if not cleaned:
        return cleaned
    replacements = (
        (r"\bMoreover,\s*", ""),
        (r"\bCrucial\b", "Important"),
        (r"\bdelve into\b", "examine"),
        (r"\bcomprehensive landscape\b", "current evidence base"),
        (r"\bpivotal role\b", "key role"),
        (r"\brealm\b", "field"),
        (r"\btapestry\b", "pattern"),
        (r"\bunderscore(?:s|d)?\b", "show"),
        (r"\btestament\b", "evidence"),
        (r"\bIt is worth noting that\s*", ""),
        (r"\bAs mentioned above,\s*", ""),
        (r"\bserves as\b", "is"),
        (r"\bacts as\b", "is"),
        (r"\bFoster(?:s|ed|ing)?\b", "support"),
        (r"\bSpearhead(?:s|ed|ing)?\b", "lead"),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("—", ", ")
    cleaned = re.sub(r"\bnot only\s+(.+?)\s+but also\s+(.+?)([.;!?]|$)", r"\1 and \2\3", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bfrom\s+([A-Za-z0-9][^,.;]{0,40})\s+to\s+([A-Za-z0-9][^,.;]{0,40})", r"across \1 and \2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r",\s*(?:thus|thereby|therefore)\s+([A-Za-z-]+ing\b[^.;!?]*)", r".", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("?", ".")
    cleaned = re.sub(r"\s+([,.;!?])", r"\1", cleaned)
    cleaned = re.sub(r"\.\.+", ".", cleaned)
    cleaned = normalize_ws(cleaned)
    return cleaned


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


def compute_tree_signature(root: Path, patterns: tuple[str, ...] = ("*.py", "*.md", "*.json")) -> str:
    digest = hashlib.sha256()
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


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


def detect_comments_input_mode(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return "docx-review-comments"
    if suffix != ".html":
        return "unsupported"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "html-unknown"
    lowered = text.lower()
    if "class=\"comment-unit\"" in lowered or "data-comment-id=" in lowered:
        return "atomic-comment-html"
    if "critique-section" in lowered and "critique-list" in lowered:
        return "reviewer-simulator-html"
    if (
        "response to reviewer" in lowered
        and "evidence attachments" in lowered
        and ("page-u-" in lowered or "reviewer #1 |" in lowered or "reviewer #1 -" in lowered)
    ):
        return "reviewer-response-sci-html"
    return "html-unknown"


def docx_title_hint(path: Path) -> str:
    try:
        rows = read_docx_paragraphs(path)
    except (PackageNotFoundError, KeyError, ValueError):
        return ""
    for row in rows[:12]:
        text = normalize_ws(row.get("text", ""))
        if not text:
            continue
        lowered = text.lower()
        if lowered in {"highlights", "abstract", "keywords", "references"}:
            continue
        if re.match(r"^(fig|figure|table)\b", text, flags=re.IGNORECASE):
            continue
        return text
    return ""


def looks_like_reference_entry(text: str) -> bool:
    candidate = normalize_ws(text)
    lowered = candidate.lower()
    if re.search(r"\bdoi:\s*10\.", lowered) or re.search(r"\bpmid:\s*\d+", lowered):
        return True
    if re.match(r"^\[?\d+\]?[.)]?\s+", candidate):
        has_year = re.search(r"\b(19|20)\d{2}\b", candidate) is not None
        author_like = re.search(r"^\[?\d+\]?[.)]?\s+[A-Z][A-Za-z-]+(?:\s+[A-Z]\.)?", candidate) is not None
        if has_year and author_like:
            return True
    return False


def docx_reference_entry_count(path: Path) -> int:
    try:
        rows = read_docx_paragraphs(path)
    except (PackageNotFoundError, KeyError, ValueError):
        return 0
    in_references = False
    count = 0
    for row in rows:
        text = normalize_ws(row.get("text", ""))
        if not text:
            continue
        lowered = text.lower()
        style_name = row.get("style_name", "").lower()
        if lowered in {"references", "reference", "参考文献"}:
            in_references = True
            continue
        if in_references and is_heading(row):
            break
        if "bibliography" in style_name and looks_like_reference_entry(text):
            count += 1
            continue
        if in_references and looks_like_reference_entry(text):
            count += 1
    return count


def normalize_title_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_ws(text).lower()).strip()


def normalize_stem_key(text: str) -> str:
    lowered = MANUSCRIPT_VERSION_SUFFIX_RE.sub("", normalize_ws(text).lower())
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def iter_nearby_docx_candidates(manuscript_path: Path) -> list[Path]:
    root = manuscript_path.parent
    candidates: list[Path] = []
    for candidate in sorted(root.rglob("*.docx")):
        if candidate.resolve() == manuscript_path.resolve():
            continue
        if candidate.name.startswith("~$"):
            continue
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            continue
        if len(relative.parts) > 3:
            continue
        candidates.append(candidate)
    return candidates


def find_same_title_reference_docx(manuscript_path: Path | None) -> Path | None:
    if manuscript_path is None or not manuscript_path.exists() or manuscript_path.suffix.lower() != ".docx":
        return None
    manuscript_title = normalize_title_key(docx_title_hint(manuscript_path))
    manuscript_stem = normalize_stem_key(manuscript_path.stem)
    siblings: list[tuple[int, Path]] = []
    for candidate in iter_nearby_docx_candidates(manuscript_path):
        reference_count = docx_reference_entry_count(candidate)
        if reference_count < 3:
            continue
        candidate_title = normalize_title_key(docx_title_hint(candidate))
        candidate_stem = normalize_stem_key(candidate.stem)
        title_match = bool(manuscript_title and candidate_title and manuscript_title == candidate_title)
        stem_match = bool(manuscript_stem and candidate_stem and manuscript_stem == candidate_stem)
        title_overlap = 0
        if manuscript_title and candidate_title:
            manuscript_tokens = set(manuscript_title.split())
            candidate_tokens = set(candidate_title.split())
            title_overlap = len(manuscript_tokens.intersection(candidate_tokens))
        near_title_match = title_overlap >= 6
        if not title_match and not stem_match and not near_title_match:
            continue
        score = 0
        if title_match:
            score += 100
        elif near_title_match:
            score += 70
        if stem_match:
            score += 20
        if candidate.parent != manuscript_path.parent:
            score -= 5
        score += min(reference_count, 50)
        siblings.append((score, candidate.resolve()))
    if not siblings:
        return None
    siblings.sort(key=lambda item: (-item[0], str(item[1])))
    return siblings[0][1]


def is_heading(row: dict[str, Any]) -> bool:
    style_name = row.get("style_name", "").lower()
    text = row.get("text", "")
    if style_name.startswith("heading"):
        return True
    if re.match(r"^\d+(?:\.\d+)*\.?\s+\S+", text) and not re.match(r"^(fig|figure|table)\b", text, flags=re.IGNORECASE) and not looks_like_reference_entry(text):
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
        "references",
        "reference",
        "acknowledgement",
        "acknowledgment",
        "data availability",
        "declaration of competing interest",
        "credit authorship contribution statement",
        "author contributions",
        "funding",
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
    needs_methodology = bool(
        re.search(
            r"\b(methodology|methodologies|search strategy|search strategies|database|databases|keyword|keywords|"
            r"inclusion|exclusion|criteria|review method|review methods|evidence level|evidence levels|"
            r"novelty|scope|boundary|boundaries|logic|framework|restructure|reorganization|organization)\b",
            lowered,
        )
    ) or any(
        token in comment_text
        for token in (
            "方法学",
            "检索",
            "数据库",
            "关键词",
            "纳入",
            "排除",
            "证据等级",
            "综述方法",
            "创新性",
            "新颖性",
            "边界",
            "逻辑",
            "框架",
            "重构",
            "结构",
        )
    )
    return {
        "needs_experiment": bool(re.search(r"\b(experiment|assay|animal|western blot|validate|replicate)\b", lowered)),
        "needs_citation": bool(re.search(r"\b(reference|references|citation|citations|literature|pubmed)\b", lowered)),
        "needs_figure": bool(
            re.search(r"\b(figure|fig\.?|table|legend|panel|supplementary|caption|captions|copyright|redraw|graphic)\b", lowered)
        )
        and not needs_methodology,
        "needs_methodology": needs_methodology,
    }


def comment_nature(comment_text: str) -> str:
    requirements = detect_comment_requirements(comment_text)
    if requirements["needs_experiment"]:
        return "需要新增实验或结果支持"
    if requirements.get("needs_methodology"):
        return "需要实质性解释、结构重构或方法学澄清"
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


def autodiscover_reference_source(
    comments_path: Path | None,
    attachments_dir: Path | None,
    project_root: Path | None,
    manuscript_path: Path | None = None,
) -> Path | None:
    candidates: list[Path] = []
    sibling_docx = find_same_title_reference_docx(manuscript_path)
    if sibling_docx is not None:
        candidates.append(sibling_docx)
    if comments_path is not None:
        candidates.append(comments_path.parent / "data" / "literature_index.json")
    if attachments_dir is not None and attachments_dir.exists():
        for item in sorted(attachments_dir.iterdir()):
            if not item.is_file():
                continue
            if item.suffix.lower() not in REFERENCE_SOURCE_EXTS:
                continue
            if REFERENCE_SOURCE_NAME_RE.search(item.name):
                candidates.append(item)
    if project_root is not None:
        for name in (
            "reference_seed.json",
            "references_source.json",
            "legacy_references.json",
            "legacy_references.docx",
            "legacy_references.ris",
            "legacy_references.md",
            "legacy_references.txt",
            "references.bib",
            "references.ris",
        ):
            candidates.append(project_root / name)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


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

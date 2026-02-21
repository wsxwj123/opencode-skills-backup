import argparse
import json
import os
import sys
import shutil
import glob
import re
import zipfile
import tempfile
import hashlib
import difflib
from collections import OrderedDict
from datetime import datetime

# Define state files map
STATE_FILES = {
    "project_config": "project_config.json",
    "storyline": "storyline.json",
    "writing_progress": "writing_progress.json",
    "context_memory": "context_memory.md",
    "literature_index": "literature_index.json",
    "figures_database": "figures_database.json",
    "reviewer_concerns": "reviewer_concerns.json",
    "version_history": "version_history.json",
    "si_database": "si_database.json"
}

TOKEN_CHAR_RATIO = 4
DEFAULT_TOKEN_BUDGET = 6000
DEFAULT_TAIL_LINES = 80
GLOBAL_HISTORY_KEYS = (
    "project_config",
    "writing_progress",
    "context_memory",
    "figures_database",
    "version_history",
)

DEFAULT_MANUSCRIPT_DIR = "manuscripts"
GATE_STATE_DIR = ".state"
GATE_STATE_FILE = os.path.join(GATE_STATE_DIR, "write_gate.json")
LOAD_CACHE_FILE = os.path.join(GATE_STATE_DIR, "load_cache.json")
SYNC_REPORT_DIR = os.path.join(GATE_STATE_DIR, "reports")
TRANSACTION_DIR = os.path.join(GATE_STATE_DIR, "transactions")
LOCK_DIR = os.path.join(GATE_STATE_DIR, "locks")
DEFAULT_BACKUP_KEEP = 20
DEFAULT_DEDUP_SIMILARITY = 0.93
DEFAULT_DEDUP_CONFLICT = 0.85
DEFAULT_REFERENCE_STYLE = "vancouver"
DEFAULT_REPORT_KEEP = 40
DEFAULT_CACHE_KEEP = 200
DEFAULT_LITERATURE_MATRIX_FILE = "literature_matrix.json"


def ensure_state_dir():
    os.makedirs(GATE_STATE_DIR, exist_ok=True)


def ensure_report_dir():
    ensure_state_dir()
    os.makedirs(SYNC_REPORT_DIR, exist_ok=True)


def ensure_transaction_dir():
    ensure_state_dir()
    os.makedirs(TRANSACTION_DIR, exist_ok=True)


def ensure_lock_dir():
    ensure_state_dir()
    os.makedirs(LOCK_DIR, exist_ok=True)


def process_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def read_lock_payload(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class FileLock:
    def __init__(self, name):
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(name))
        self.name = safe_name
        self.path = os.path.join(LOCK_DIR, f"{safe_name}.lock")
        self.acquired = False

    def acquire(self):
        ensure_lock_dir()
        payload = {
            "name": self.name,
            "pid": os.getpid(),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }
        lock_text = json.dumps(payload, ensure_ascii=False)
        attempts = 0
        while attempts < 2:
            attempts += 1
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(lock_text)
                self.acquired = True
                return
            except FileExistsError:
                existing = read_lock_payload(self.path)
                existing_pid = existing.get("pid")
                if isinstance(existing_pid, int) and not process_alive(existing_pid):
                    try:
                        os.remove(self.path)
                        continue
                    except Exception:
                        pass
                raise RuntimeError(
                    f"lock '{self.name}' is held by pid={existing_pid} "
                    f"since {existing.get('created_at')}"
                )

    def release(self):
        if not self.acquired:
            return
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        finally:
            self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


def write_transaction_log(kind, payload):
    ensure_transaction_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()
    path = os.path.join(TRANSACTION_DIR, f"{kind}_{ts}_{pid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    files = sorted(
        glob.glob(os.path.join(TRANSACTION_DIR, f"{kind}_*.json")),
        key=lambda p: os.path.getmtime(p),
        reverse=True,
    )
    for stale in files[DEFAULT_REPORT_KEEP:]:
        try:
            os.remove(stale)
        except Exception:
            pass
    return path


def summarize_bundle_for_log(bundle):
    if not isinstance(bundle, dict):
        return {}
    return {
        "scope": bundle.get("scope"),
        "section": bundle.get("section"),
        "loaded_files_count": len(bundle.get("loaded_files", []) or []),
        "loaded_files": list(bundle.get("loaded_files", []) or []),
        "budget_report": bundle.get("budget_report"),
        "word_count_total": ((bundle.get("live_word_counts") or {}).get("total")),
    }


def file_signature(path):
    if not os.path.exists(path):
        return None
    st = os.stat(path)
    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return f"{mtime_ns}:{st.st_size}"


def read_load_cache():
    if not os.path.exists(LOAD_CACHE_FILE):
        return {}
    try:
        data = safe_json_load(LOAD_CACHE_FILE)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_load_cache(cache):
    ensure_state_dir()
    # Keep cache bounded to avoid unbounded growth.
    if isinstance(cache, dict) and len(cache) > DEFAULT_CACHE_KEEP:
        sortable = []
        for k, v in cache.items():
            if isinstance(v, dict):
                ts = v.get("ts")
            else:
                ts = None
            sortable.append((ts or "", k))
        sortable.sort(reverse=True)
        keep_keys = {k for _, k in sortable[:DEFAULT_CACHE_KEEP]}
        cache = {k: v for k, v in cache.items() if k in keep_keys}
    with open(LOAD_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def cache_key(*parts):
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def write_sync_report(mode, payload):
    ensure_report_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SYNC_REPORT_DIR, f"lit_sync_{mode}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    # Keep report directory bounded.
    files = sorted(
        glob.glob(os.path.join(SYNC_REPORT_DIR, "lit_sync_*.json")),
        key=lambda p: os.path.getmtime(p),
        reverse=True,
    )
    for stale in files[DEFAULT_REPORT_KEEP:]:
        try:
            os.remove(stale)
        except Exception:
            pass
    return path


def read_gate_state():
    if not os.path.exists(GATE_STATE_FILE):
        return {}
    try:
        return safe_json_load(GATE_STATE_FILE)
    except Exception:
        return {}


def write_gate_state(payload):
    ensure_state_dir()
    with open(GATE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def update_gate_state(**updates):
    state = read_gate_state()
    state.update(updates)
    write_gate_state(state)
    return state


def validate_gate(section, phase):
    state = read_gate_state()
    if state.get("section") != section:
        return False, f"gate section mismatch: expected={section}, got={state.get('section')}"

    if phase == "prewrite":
        if not state.get("prewrite_ready", False):
            return False, "prewrite gate not ready: preflight + load are required"
        if state.get("require_cycle", True):
            if state.get("last_preflight_origin") != "write-cycle" or state.get("last_load_origin") != "write-cycle":
                return False, "prewrite gate requires write-cycle origin"
        return True, "ok"

    if phase == "complete":
        if not state.get("prewrite_ready", False):
            return False, "prewrite gate not ready: cannot complete"
        if not state.get("completion_ready", False):
            return False, "completion gate not ready: run postwrite --sync-literature --sync-apply"
        return True, "ok"

    return False, f"unknown phase: {phase}"


def start_cycle(section):
    return update_gate_state(
        section=section,
        cycle_started_ts=datetime.now().isoformat(timespec="seconds"),
        require_cycle=True,
        last_preflight_origin=None,
        last_load_origin=None,
        preflight_ok=False,
        prewrite_ready=False,
        completion_ready=False,
    )

def safe_json_load(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return {}
    return json.loads(raw)

def strip_references_markdown(content):
    """Remove References/参考文献 section from markdown body for word counting."""
    heading_re = re.compile(r"^\s{0,3}#{1,6}\s*(references|参考文献)\s*$", re.IGNORECASE | re.MULTILINE)
    match = heading_re.search(content or "")
    if not match:
        return content or ""
    return (content or "")[:match.start()]


def calculate_word_counts(exclude_references=True, section=None):
    """Calculates word counts for markdown files in manuscripts/ directory."""
    word_counts = {
        "total": 0,
        "sections": {},
        "exclude_references": bool(exclude_references),
    }
    
    manuscript_dir = "manuscripts"
    if not os.path.exists(manuscript_dir):
        return word_counts
        
    files = glob.glob(os.path.join(manuscript_dir, "*.md"))

    for file_path in files:
        filename = os.path.basename(file_path)
        if section and not filename_matches_section(filename, section):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if exclude_references:
                    content = strip_references_markdown(content)
                words = len(content.split())
                word_counts["sections"][filename] = words
                word_counts["total"] += words
        except Exception:
            word_counts["sections"][filename] = 0
            
    return word_counts

def approx_tokens(value):
    """Best-effort token estimator to prevent context explosion."""
    if value is None:
        return 0
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)
    return max(1, len(text) // TOKEN_CHAR_RATIO)

def read_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return json.loads(content) if content else {}

def sanitize_section_id(section):
    return "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in section.strip())

def section_terms(section):
    raw = section.strip().lower()
    variants = {
        raw,
        raw.replace("_", "."),
        raw.replace(".", "_"),
        raw.replace("-", "_"),
        raw.replace("-", "."),
    }
    variants.discard("")
    return variants

def extract_numeric_section(section):
    # Examples:
    # - results_3.1 -> 3.1
    # - intro_2 -> 2
    # - 04_results_3.2 -> 3.2
    match = re.search(r"(\d+(?:\.\d+)*)", section)
    return match.group(1) if match else None

def filename_matches_section(filename, section):
    # Prefer strict-ish boundary matches to avoid false positives.
    # Accept separators around section token: _, -, ., start/end.
    base = filename.lower()
    terms = sorted(section_terms(section), key=len, reverse=True)
    for term in terms:
        escaped = re.escape(term)
        pattern = rf"(^|[_\-.]){escaped}([_\-.]|$)"
        if re.search(pattern, base):
            return True
    return False

def contains_term(payload, terms):
    try:
        text = json.dumps(payload, ensure_ascii=False).lower()
    except Exception:
        text = str(payload).lower()
    return any(t and t in text for t in terms)

def compact_literature_item(item):
    if not isinstance(item, dict):
        return item
    keep_keys = {"ref_id", "title", "year", "author", "authors", "journal", "doi", "citation_key"}
    return {k: v for k, v in item.items() if k in keep_keys}

def compact_figure_item(item):
    if not isinstance(item, dict):
        return item
    keep_keys = {
        "figure_id", "id", "title", "caption", "section", "data_status",
        "n", "p_value", "statistical_test", "notes"
    }
    return {k: v for k, v in item.items() if k in keep_keys}

def tail_text(content, lines=DEFAULT_TAIL_LINES):
    split_lines = content.splitlines()
    if len(split_lines) <= lines:
        return content
    return "\n".join(split_lines[-lines:])

def normalize_doi(doi):
    if not doi:
        return ""
    return re.sub(r"\s+", "", str(doi).strip().lower())

def normalize_title(title):
    if not title:
        return ""
    text = str(title).strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_author(author):
    if not author:
        return ""
    text = str(author).strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_journal(journal):
    if not journal:
        return ""
    text = str(journal).strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def normalize_pmid(pmid):
    if not pmid:
        return ""
    return str(pmid).strip()


def _is_present(value):
    return value not in (None, "", [])


def _merge_canonical_item(target, source):
    """Merge metadata from a duplicate entry into the canonical record."""
    for key, value in source.items():
        if key in ("citation_number", "global_id"):
            continue
        if key not in target or not _is_present(target.get(key)):
            target[key] = value
            continue
        if key in ("related_sections", "sections") and isinstance(target.get(key), list) and isinstance(value, list):
            merged = []
            seen = set()
            for item in target[key] + value:
                marker = normalize_title(str(item))
                if not marker or marker in seen:
                    continue
                seen.add(marker)
                merged.append(item)
            target[key] = merged


def expand_citation_numbers(text):
    numbers = []
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                start, end = int(a.strip()), int(b.strip())
                if start <= end:
                    numbers.extend(list(range(start, end + 1)))
                else:
                    numbers.extend([start, end])
                continue
        if token.isdigit():
            numbers.append(int(token))
    return numbers

def compress_citation_numbers(numbers):
    if not numbers:
        return ""
    uniq = sorted(OrderedDict.fromkeys(numbers))
    ranges = []
    start = uniq[0]
    prev = uniq[0]
    for n in uniq[1:]:
        if n == prev + 1:
            prev = n
            continue
        ranges.append((start, prev))
        start = n
        prev = n
    ranges.append((start, prev))

    out = []
    for a, b in ranges:
        out.append(str(a) if a == b else f"{a}-{b}")
    return ",".join(out)


def format_reference_entry(entry, number, style=DEFAULT_REFERENCE_STYLE):
    if isinstance(entry, str):
        text = entry.strip()
        return f"{number}. {text}" if text else f"{number}."

    if not isinstance(entry, dict):
        return f"{number}. {str(entry).strip()}"

    authors = entry.get("authors") or entry.get("author") or ""
    title = entry.get("title") or ""
    journal = entry.get("journal") or ""
    year = entry.get("year") or ""
    volume = entry.get("volume") or ""
    pages = entry.get("pages") or entry.get("page") or ""
    doi = entry.get("doi") or ""

    if style == "nature":
        chunks = []
        if authors:
            chunks.append(str(authors).strip())
        if title:
            chunks.append(str(title).strip())
        body = ". ".join([c for c in chunks if c]).strip()
        journal_tail = ""
        if journal:
            journal_tail += str(journal).strip()
        if volume:
            journal_tail += f" {str(volume).strip()}"
        if pages:
            journal_tail += f", {str(pages).strip()}"
        if year:
            journal_tail += f" ({str(year).strip()})"
        if journal_tail:
            body = f"{body}. {journal_tail}" if body else journal_tail
        if doi:
            body = f"{body}. doi:{str(doi).strip()}" if body else f"doi:{str(doi).strip()}"
    else:
        chunks = []
        if authors:
            chunks.append(str(authors).strip())
        if title:
            chunks.append(str(title).strip())
        if journal:
            chunks.append(str(journal).strip())

        tail = ""
        if year:
            tail += str(year).strip()
        if volume:
            tail += f";{str(volume).strip()}"
        if pages:
            tail += f":{str(pages).strip()}"
        if tail:
            chunks.append(tail)
        if doi:
            chunks.append(f"doi:{str(doi).strip()}")
        body = ". ".join([c for c in chunks if c]).strip()

    if body and not body.endswith("."):
        body += "."
    return f"{number}. {body}" if body else f"{number}."


def load_storyline_section_order(storyline_file):
    if not storyline_file or not os.path.exists(storyline_file):
        return []
    try:
        payload = read_json_file(storyline_file)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    sections = payload.get("sections")
    out = []
    if isinstance(sections, list):
        for item in sections:
            if not isinstance(item, dict):
                continue
            sid = item.get("id") or item.get("section_id") or item.get("section")
            if sid:
                out.append(sanitize_section_id(str(sid)))
    return out


def parse_literature_matrix(payload):
    """Best-effort parser for section->references matrix payload."""
    matrix = OrderedDict()
    reserved = {
        "sections", "items", "matrix", "section_map", "section_matrix",
        "literature_matrix", "citation_matrix", "reference_matrix",
        "section_literature_map", "meta", "metadata", "version"
    }

    def add(section_id, refs):
        if not section_id:
            return
        sid = sanitize_section_id(str(section_id))
        if sid not in matrix:
            matrix[sid] = []
        if isinstance(refs, list):
            matrix[sid].extend(refs)
        elif refs is not None:
            matrix[sid].append(refs)

    def walk(node):
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    sid = item.get("section_id") or item.get("section") or item.get("id")
                    refs = (
                        item.get("references") or item.get("refs") or item.get("literature")
                        or item.get("citations") or item.get("items") or item.get("ref_ids")
                    )
                    if sid is not None and refs is not None:
                        add(sid, refs)
                    else:
                        walk(item)
            return

        if not isinstance(node, dict):
            return

        for key in (
            "matrix", "section_map", "section_matrix",
            "literature_matrix", "citation_matrix", "reference_matrix",
            "section_literature_map", "items"
        ):
            if key in node:
                walk(node.get(key))

        sections = node.get("sections")
        if isinstance(sections, dict):
            for sid, refs in sections.items():
                add(sid, refs)
        elif isinstance(sections, list):
            walk(sections)

        for k, v in node.items():
            lk = str(k).strip().lower()
            if lk in reserved:
                continue
            if isinstance(v, list):
                add(k, v)

    walk(payload)
    return dict(matrix)


def load_literature_matrix(matrix_file=DEFAULT_LITERATURE_MATRIX_FILE, storyline_file=STATE_FILES["storyline"]):
    combined = OrderedDict()
    sources = {"matrix_file": False, "storyline_embedded": False}

    if matrix_file and os.path.exists(matrix_file):
        try:
            payload = read_json_file(matrix_file)
            parsed = parse_literature_matrix(payload)
            for sid, refs in parsed.items():
                combined[sid] = list(refs)
            sources["matrix_file"] = bool(parsed)
        except Exception:
            sources["matrix_file"] = False

    if storyline_file and os.path.exists(storyline_file):
        try:
            payload = read_json_file(storyline_file)
            parsed = parse_literature_matrix(payload)
            for sid, refs in parsed.items():
                if sid not in combined:
                    combined[sid] = []
                combined[sid].extend(refs)
            sources["storyline_embedded"] = bool(parsed)
        except Exception:
            sources["storyline_embedded"] = False

    return dict(combined), sources


def as_index_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("references", "items", "entries", "data", "figures", "records", "si", "supplementary"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return None


def validate_index_schema(name, path, required_any_keys):
    check = {
        "name": name,
        "file": path,
        "exists": os.path.exists(path),
        "ok": True,
        "count": 0,
        "errors": [],
    }
    if not check["exists"]:
        check["ok"] = False
        check["errors"].append("missing file")
        return check
    try:
        payload = read_json_file(path)
    except Exception as e:
        check["ok"] = False
        check["errors"].append(f"invalid json: {e}")
        return check

    items = as_index_list(payload)
    if items is None:
        check["ok"] = False
        check["errors"].append("must be a list or dict containing a list field")
        return check

    check["count"] = len(items)
    for idx, entry in enumerate(items, start=1):
        if not isinstance(entry, dict):
            check["ok"] = False
            check["errors"].append(f"item[{idx}] is not an object")
            if len(check["errors"]) >= 20:
                break
            continue
        if required_any_keys:
            found = False
            for k in required_any_keys:
                val = entry.get(k)
                if isinstance(val, str):
                    if val.strip():
                        found = True
                        break
                elif val is not None:
                    found = True
                    break
            if not found:
                check["ok"] = False
                check["errors"].append(f"item[{idx}] missing required identity fields: any of {required_any_keys}")
                if len(check["errors"]) >= 20:
                    break
    return check


def validate_storyline_schema(storyline_file=STATE_FILES["storyline"]):
    check = {
        "name": "storyline",
        "file": storyline_file,
        "exists": os.path.exists(storyline_file),
        "ok": True,
        "section_count": 0,
        "errors": [],
    }
    if not check["exists"]:
        check["ok"] = False
        check["errors"].append("missing file")
        return check
    try:
        payload = read_json_file(storyline_file)
    except Exception as e:
        check["ok"] = False
        check["errors"].append(f"invalid json: {e}")
        return check

    sections = []
    if isinstance(payload, dict):
        sections = payload.get("sections", [])
    if not isinstance(sections, list):
        check["ok"] = False
        check["errors"].append("sections must be a list")
        return check

    seen = set()
    for idx, sec in enumerate(sections, start=1):
        if not isinstance(sec, dict):
            check["ok"] = False
            check["errors"].append(f"sections[{idx}] is not an object")
            continue
        sid = str(sec.get("id") or "").strip()
        if not sid:
            check["ok"] = False
            check["errors"].append(f"sections[{idx}] missing id")
            continue
        if sid in seen:
            check["ok"] = False
            check["errors"].append(f"duplicate section id: {sid}")
            continue
        seen.add(sid)
    check["section_count"] = len(seen)
    return check


def validate_matrix_schema(
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True,
):
    check = {
        "name": "literature_matrix",
        "matrix_file": matrix_file,
        "storyline_file": storyline_file,
        "ok": True,
        "errors": [],
        "warnings": [],
        "sections_in_matrix": 0,
    }
    matrix_map, sources = load_literature_matrix(matrix_file=matrix_file, storyline_file=storyline_file)
    check["sources"] = sources
    check["sections_in_matrix"] = len(matrix_map)
    if require_matrix_reindex and not matrix_map:
        check["ok"] = False
        check["errors"].append("matrix is required but no section-literature mapping was found")
        return check

    section_order = load_storyline_section_order(storyline_file)
    section_set = set(section_order)
    unknown = [sid for sid in matrix_map.keys() if section_set and sid not in section_set]
    if unknown:
        check["ok"] = False
        check["errors"].append(f"unknown section ids: {unknown[:10]}")

    bad_rows = []
    for sid, refs in matrix_map.items():
        if not isinstance(refs, list):
            bad_rows.append({"section_id": sid, "reason": "refs must be a list"})
            continue
        if not refs:
            check["warnings"].append(f"section '{sid}' has empty references list")
        for raw in refs:
            tokens = expand_matrix_ref_tokens(raw)
            if not tokens:
                bad_rows.append({"section_id": sid, "reason": f"invalid ref token: {raw}"})
    if bad_rows:
        check["ok"] = False
        check["errors"].append(f"invalid matrix rows: {bad_rows[:10]}")
    return check


def validate_state_schemas(
    require_matrix_reindex=True,
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
):
    literature = validate_index_schema(
        "literature_index",
        STATE_FILES["literature_index"],
        required_any_keys=("title", "citation", "doi", "ref_id", "source_id", "citation_key"),
    )
    figures = validate_index_schema(
        "figures_database",
        STATE_FILES["figures_database"],
        required_any_keys=("figure_id", "id", "title", "caption", "section_id"),
    )
    si = validate_index_schema(
        "si_database",
        STATE_FILES["si_database"],
        required_any_keys=("si_id", "id", "title", "caption", "content", "section_id"),
    )
    storyline = validate_storyline_schema(storyline_file=storyline_file)
    matrix = validate_matrix_schema(
        matrix_file=matrix_file,
        storyline_file=storyline_file,
        require_matrix_reindex=require_matrix_reindex,
    )

    checks = [literature, figures, si, storyline, matrix]
    errors = []
    warnings = []
    for check in checks:
        if not check.get("ok", True):
            errors.append({"name": check.get("name"), "errors": check.get("errors", [])})
        ws = check.get("warnings", [])
        if ws:
            warnings.extend([{"name": check.get("name"), "warning": w} for w in ws])

    return {
        "ok": len(errors) == 0,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def build_canonical_lookup_maps(canonical_entries):
    by_ref_id = {}
    by_source_id = {}
    by_citation_key = {}
    by_doi = {}
    by_title = {}
    for idx, entry in enumerate(canonical_entries, start=1):
        if not isinstance(entry, dict):
            continue
        ref_id = str(entry.get("ref_id") or "").strip().lower()
        source_id = str(entry.get("source_id") or "").strip().lower()
        citation_key = str(entry.get("citation_key") or "").strip().lower()
        doi = normalize_doi(entry.get("doi"))
        title = normalize_title(entry.get("title"))
        if ref_id:
            by_ref_id.setdefault(ref_id, idx)
        if source_id:
            by_source_id.setdefault(source_id, idx)
        if citation_key:
            by_citation_key.setdefault(citation_key, idx)
        if doi:
            by_doi.setdefault(doi, idx)
        if title:
            by_title.setdefault(title, idx)
    return {
        "ref_id": by_ref_id,
        "source_id": by_source_id,
        "citation_key": by_citation_key,
        "doi": by_doi,
        "title": by_title,
    }


def expand_matrix_ref_tokens(raw):
    if raw is None:
        return []
    if isinstance(raw, int):
        return [raw]
    if isinstance(raw, str):
        s = raw.strip()
        m = re.match(r"^\[(.+)\]$", s)
        payload = m.group(1) if m else s
        nums = expand_citation_numbers(payload)
        if nums:
            return nums
        return [s]
    if isinstance(raw, dict):
        out = []
        for key in ("number", "citation_number", "index"):
            val = raw.get(key)
            if isinstance(val, int):
                out.append(val)
        if out:
            return out
        return [raw]
    return [raw]


def resolve_matrix_token_to_canonical(token, old_to_new, lookup_maps):
    if isinstance(token, int):
        return old_to_new.get(token)

    if isinstance(token, dict):
        for key in ("ref_id", "source_id", "citation_key"):
            val = str(token.get(key) or "").strip().lower()
            if val and val in lookup_maps[key]:
                return lookup_maps[key][val]
        doi = normalize_doi(token.get("doi"))
        if doi and doi in lookup_maps["doi"]:
            return lookup_maps["doi"][doi]
        title = normalize_title(token.get("title"))
        if title and title in lookup_maps["title"]:
            return lookup_maps["title"][title]
        return None

    if isinstance(token, str):
        s = token.strip()
        if not s:
            return None
        if s.isdigit():
            return old_to_new.get(int(s))
        low = s.lower()
        if low in lookup_maps["ref_id"]:
            return lookup_maps["ref_id"][low]
        if low in lookup_maps["source_id"]:
            return lookup_maps["source_id"][low]
        if low in lookup_maps["citation_key"]:
            return lookup_maps["citation_key"][low]
        doi = normalize_doi(s)
        if doi in lookup_maps["doi"]:
            return lookup_maps["doi"][doi]
        title = normalize_title(s)
        if title in lookup_maps["title"]:
            return lookup_maps["title"][title]
    return None


def apply_matrix_reindex(
    dedup_result,
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True
):
    canonical = dedup_result.get("canonical_entries", [])
    old_to_new = dedup_result.get("old_to_new", {})
    if not isinstance(canonical, list) or not isinstance(old_to_new, dict):
        return dedup_result, {"applied": False, "reason": "invalid_dedup_result"}

    matrix_map, sources = load_literature_matrix(matrix_file=matrix_file, storyline_file=storyline_file)
    section_order = load_storyline_section_order(storyline_file)
    section_keys = list(matrix_map.keys())
    unknown_sections = []
    if section_order:
        order_set = set(section_order)
        unknown_sections = [s for s in section_keys if s not in order_set]
    if section_order:
        ordered_sections = [s for s in section_order if s in matrix_map]
        ordered_sections.extend([s for s in section_keys if s not in ordered_sections])
    else:
        ordered_sections = section_keys

    if require_matrix_reindex and len(canonical) > 0 and not ordered_sections:
        raise RuntimeError(
            f"Matrix reindex required but no section-literature matrix found "
            f"(expected {matrix_file} or embedded matrix in {storyline_file})."
        )
    if require_matrix_reindex and unknown_sections:
        raise RuntimeError(
            f"Matrix reindex unknown section ids (not found in storyline sections): {unknown_sections[:10]}"
        )

    lookup_maps = build_canonical_lookup_maps(canonical)
    ordered_canonical = []
    seen = set()
    unresolved = []

    for sid in ordered_sections:
        refs = matrix_map.get(sid, [])
        for raw in refs:
            for token in expand_matrix_ref_tokens(raw):
                cidx = resolve_matrix_token_to_canonical(token, old_to_new, lookup_maps)
                if cidx is None:
                    unresolved.append({"section_id": sid, "token": token})
                    continue
                if cidx not in seen:
                    seen.add(cidx)
                    ordered_canonical.append(cidx)

    all_canonical = list(range(1, len(canonical) + 1))
    unmatched = [idx for idx in all_canonical if idx not in seen]

    if require_matrix_reindex and len(canonical) > 0:
        if unresolved:
            sample = unresolved[:5]
            raise RuntimeError(f"Matrix reindex unresolved references: {sample}")
        if unmatched:
            raise RuntimeError(f"Matrix reindex missing section assignment for canonical refs: {unmatched[:10]}")

    if not ordered_canonical:
        ordered_canonical = all_canonical
    elif unmatched:
        ordered_canonical.extend(unmatched)

    canonical_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(ordered_canonical, start=1)}
    reordered = [canonical[old_idx - 1] for old_idx in ordered_canonical]
    for i, entry in enumerate(reordered, start=1):
        if isinstance(entry, dict):
            entry["citation_number"] = i

    remapped_old_to_new = {}
    for old_num, canonical_idx in old_to_new.items():
        try:
            old_key = int(old_num)
            can_key = int(canonical_idx)
        except Exception:
            continue
        remapped_old_to_new[old_key] = canonical_to_new.get(can_key, can_key)

    updated = dict(dedup_result)
    updated["canonical_entries"] = reordered
    updated["old_to_new"] = remapped_old_to_new
    report = {
        "applied": True,
        "matrix_sources": sources,
        "ordered_sections": ordered_sections,
        "unknown_sections": unknown_sections,
        "unresolved_count": len(unresolved),
        "unmatched_count": len(unmatched),
        "total_canonical": len(canonical),
    }
    return updated, report

def summarize_dict_hits(data, terms, max_hits=40):
    hits = []

    def walk(node, path):
        if len(hits) >= max_hits:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [str(k)])
            return
        if isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [f"[{i}]"])
            return
        text = str(node).lower()
        if any(t in text for t in terms):
            hits.append({
                "path": ".".join(path),
                "value_preview": str(node)[:200]
            })

    walk(data, [])
    return {
        "_section_filtered": True,
        "_matched_leaf_count": len(hits),
        "_matched_leaves": hits
    }

def filter_for_section(data, terms, compact=False, data_type=None):
    if data is None:
        return None

    if isinstance(data, list):
        matched = [item for item in data if contains_term(item, terms)]
        if compact:
            if data_type == "literature":
                matched = [compact_literature_item(x) for x in matched]
            elif data_type == "figures":
                matched = [compact_figure_item(x) for x in matched]
        return matched

    if isinstance(data, dict):
        if not contains_term(data, terms):
            return {}
        if approx_tokens(data) <= 1200:
            return data
        return summarize_dict_hits(data, terms)

    return data if contains_term(data, terms) else None


def cached_filtered_section_json(path, section, compact=False, data_type=None):
    sig = file_signature(path)
    if not sig:
        return None
    key = cache_key("filtered", path, section, compact, data_type)
    cache = read_load_cache()
    item = cache.get(key)
    if isinstance(item, dict) and item.get("sig") == sig:
        return item.get("payload")

    data = read_json_file(path)
    payload = filter_for_section(data, section_terms(section), compact=compact, data_type=data_type)
    cache[key] = {"sig": sig, "payload": payload, "ts": datetime.now().isoformat(timespec="seconds")}
    write_load_cache(cache)
    return payload


def cached_global_value(path, compact=False, key_name=None):
    sig = file_signature(path)
    if not sig:
        return None
    key = cache_key("global", path, compact, key_name)
    cache = read_load_cache()
    item = cache.get(key)
    if isinstance(item, dict) and item.get("sig") == sig:
        return item.get("payload")

    if path.endswith(".json"):
        payload = read_json_file(path)
        if compact and key_name == "figures_database" and isinstance(payload, list):
            payload = [compact_figure_item(x) for x in payload[:30]]
        if compact and key_name == "version_history" and isinstance(payload, list):
            payload = payload[-30:]
    else:
        with open(path, "r", encoding="utf-8") as f:
            payload = f.read()
        if compact and key_name == "context_memory":
            payload = tail_text(payload, lines=80)

    cache[key] = {"sig": sig, "payload": payload, "ts": datetime.now().isoformat(timespec="seconds")}
    write_load_cache(cache)
    return payload

def find_section_manuscripts(section):
    manuscript_dir = "manuscripts"
    if not os.path.exists(manuscript_dir):
        return []

    all_files = sorted(glob.glob(os.path.join(manuscript_dir, "*.md")))
    strict_matched = []
    for path in all_files:
        name = os.path.basename(path).lower()
        if filename_matches_section(name, section):
            strict_matched.append(path)

    if strict_matched:
        return strict_matched

    # Fallback for non-standard filenames:
    # inspect file content for section id / numeric subsection markers.
    terms = section_terms(section)
    numeric = extract_numeric_section(section)
    content_matched = []
    for path in all_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().lower()
            if any(term in content for term in terms):
                content_matched.append(path)
                continue
            if numeric and re.search(rf"\b{re.escape(numeric)}\b", content):
                content_matched.append(path)
        except Exception:
            continue
    return content_matched

def trim_section_bundle_to_budget(bundle, token_budget, tail_lines):
    report = {
        "token_budget": token_budget,
        "initial_estimated_tokens": approx_tokens(bundle),
        "actions": []
    }

    if report["initial_estimated_tokens"] <= token_budget:
        report["final_estimated_tokens"] = report["initial_estimated_tokens"]
        report["over_budget"] = False
        bundle["budget_report"] = report
        return bundle

    draft = bundle.get("current_section_draft")
    if isinstance(draft, str) and draft:
        bundle["current_section_draft"] = tail_text(draft, lines=tail_lines)
        report["actions"].append(f"Trimmed current_section_draft to last {tail_lines} lines")

    section_memory = bundle.get("section_memory")
    if isinstance(section_memory, str) and section_memory:
        bundle["section_memory"] = tail_text(section_memory, lines=min(40, tail_lines))
        report["actions"].append("Trimmed section_memory to recent tail")

    literature = bundle.get("literature_section")
    if isinstance(literature, list) and len(literature) > 10:
        bundle["literature_section"] = [compact_literature_item(x) for x in literature[:10]]
        report["actions"].append("Compacted literature_section to first 10 compact items")

    figures = bundle.get("figures_section")
    if isinstance(figures, list) and len(figures) > 10:
        bundle["figures_section"] = [compact_figure_item(x) for x in figures[:10]]
        report["actions"].append("Compacted figures_section to first 10 compact items")

    storyline = bundle.get("storyline_section")
    if approx_tokens(storyline) > 1200:
        terms = section_terms(bundle.get("section", ""))
        bundle["storyline_section"] = summarize_dict_hits(storyline, terms, max_hits=20) if isinstance(storyline, dict) else storyline
        report["actions"].append("Reduced storyline_section to matched leaf summary")

    global_history = bundle.get("global_history")
    if isinstance(global_history, dict):
        for key in ("context_memory", "context_memory_v-1", "context_memory_v-2"):
            value = global_history.get(key)
            if isinstance(value, str) and len(value.splitlines()) > tail_lines:
                global_history[key] = tail_text(value, lines=tail_lines)
                report["actions"].append(f"Trimmed global_history.{key} to last {tail_lines} lines")

        if approx_tokens(bundle) > token_budget and isinstance(global_history.get("project_config"), dict):
            slim_project = {k: global_history["project_config"].get(k) for k in ("project_name", "target_journal", "manuscript_type")}
            global_history["project_config"] = {k: v for k, v in slim_project.items() if v is not None}
            report["actions"].append("Compacted global_history.project_config to core fields")

        if approx_tokens(bundle) > token_budget and isinstance(global_history.get("writing_progress"), dict):
            slim_progress = {
                "last_section": global_history["writing_progress"].get("last_section"),
                "last_updated": global_history["writing_progress"].get("last_updated"),
                "status": global_history["writing_progress"].get("status"),
                "pending_issues": global_history["writing_progress"].get("pending_issues", [])[:5]
            }
            global_history["writing_progress"] = {k: v for k, v in slim_progress.items() if v not in (None, [], "")}
            report["actions"].append("Compacted global_history.writing_progress to core fields")

    report["final_estimated_tokens"] = approx_tokens(bundle)
    report["over_budget"] = report["final_estimated_tokens"] > token_budget
    bundle["budget_report"] = report
    return bundle

def build_global_history_bundle(compact=False):
    bundle = {
        "loaded_files": []
    }

    for key in GLOBAL_HISTORY_KEYS:
        filename = STATE_FILES[key]
        if os.path.exists(filename):
            try:
                bundle[key] = cached_global_value(filename, compact=compact, key_name=key)
                bundle["loaded_files"].append(filename)
            except Exception as e:
                bundle[key] = f"<Error loading {filename}: {str(e)}>"
        else:
            bundle[key] = None

    for history_file in ("context_memory_v-1.md", "context_memory_v-2.md"):
        key = history_file.replace(".md", "")
        if os.path.exists(history_file):
            try:
                bundle[key] = cached_global_value(history_file, compact=compact, key_name=key)
                bundle["loaded_files"].append(history_file)
            except Exception as e:
                bundle[key] = f"<Error loading {history_file}: {str(e)}>"
        else:
            bundle[key] = None

    return bundle

def build_section_bundle(
    section,
    compact=False,
    token_budget=DEFAULT_TOKEN_BUDGET,
    tail_lines=DEFAULT_TAIL_LINES,
    with_global_history=True,
    include_draft=False
):
    terms = section_terms(section)
    bundle = {
        "scope": "section-local",
        "section": section,
        "loaded_files": []
    }

    if os.path.exists("project_config.json"):
        bundle["project_config"] = read_json_file("project_config.json")
        bundle["loaded_files"].append("project_config.json")
    else:
        bundle["project_config"] = None

    if os.path.exists("storyline.json"):
        bundle["storyline_section"] = cached_filtered_section_json("storyline.json", section, compact=compact, data_type="storyline")
        bundle["loaded_files"].append("storyline.json (filtered)")
    else:
        bundle["storyline_section"] = None

    if os.path.exists("figures_database.json"):
        bundle["figures_section"] = cached_filtered_section_json("figures_database.json", section, compact=True, data_type="figures")
        bundle["loaded_files"].append("figures_database.json (filtered)")
    else:
        bundle["figures_section"] = None

    if os.path.exists("literature_index.json"):
        bundle["literature_section"] = cached_filtered_section_json("literature_index.json", section, compact=True, data_type="literature")
        bundle["loaded_files"].append("literature_index.json (filtered)")
    else:
        bundle["literature_section"] = None

    if os.path.exists("si_database.json"):
        bundle["si_section"] = cached_filtered_section_json("si_database.json", section, compact=True, data_type="si")
        bundle["loaded_files"].append("si_database.json (filtered)")
    else:
        bundle["si_section"] = None

    memory_dir = "section_memory"
    section_memory_file = os.path.join(memory_dir, f"{sanitize_section_id(section)}.md")
    if os.path.exists(section_memory_file):
        with open(section_memory_file, "r", encoding="utf-8") as f:
            bundle["section_memory"] = f.read()
        bundle["loaded_files"].append(section_memory_file)
    else:
        bundle["section_memory"] = None

    if include_draft:
        matched_files = find_section_manuscripts(section)
        draft_blocks = []
        for file_path in matched_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                draft_blocks.append(f"## FILE: {os.path.basename(file_path)}\n{content}")
                bundle["loaded_files"].append(file_path)
            except Exception as e:
                draft_blocks.append(f"## FILE: {os.path.basename(file_path)}\n<Error: {str(e)}>")
                bundle["loaded_files"].append(file_path)
        bundle["current_section_draft"] = "\n\n".join(draft_blocks) if draft_blocks else None
    else:
        bundle["current_section_draft"] = None

    bundle["live_word_counts"] = calculate_word_counts()
    if with_global_history:
        bundle["global_history"] = build_global_history_bundle(compact=compact)
    return trim_section_bundle_to_budget(bundle, token_budget=token_budget, tail_lines=tail_lines)

def load_state(
    target_files=None,
    compact=False,
    section=None,
    token_budget=DEFAULT_TOKEN_BUDGET,
    tail_lines=DEFAULT_TAIL_LINES,
    with_global_history=False,
    include_draft=False,
    origin="manual"
):
    """Reads state files.
    Args:
        target_files (list): Optional list of specific keys to load (e.g. ['storyline', 'literature_index']).
        compact (bool): If True, removes bulky fields like 'abstract' to save tokens.
        section (str): If provided, perform section-local loading only.
    """
    if section:
        scoped_bundle = build_section_bundle(
            section=section,
            compact=compact,
            token_budget=token_budget,
            tail_lines=tail_lines,
            with_global_history=with_global_history,
            include_draft=include_draft
        )
        # hard-gate: load of scoped context marks prewrite-ready when a matching preflight already exists
        gate = read_gate_state()
        if gate.get("section") == section and gate.get("preflight_ok", False):
            update_gate_state(
                load_ts=datetime.now().isoformat(timespec="seconds"),
                last_load_origin=origin,
                prewrite_ready=True,
                completion_ready=False,
                include_draft=bool(include_draft),
                with_global_history=bool(with_global_history)
            )
        print(json.dumps(scoped_bundle, indent=2, ensure_ascii=False))
        return scoped_bundle

    combined_state = {}
    
    # Determine which files to load
    keys_to_load = target_files if target_files else STATE_FILES.keys()
    
    # 1. Load standard state files
    for key in keys_to_load:
        if key not in STATE_FILES:
            continue
            
        filename = STATE_FILES[key]
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        data = json.loads(content) if content else {}
                        
                        # Apply compaction logic
                        if compact:
                            if key == "literature_index" and isinstance(data, list):
                                for item in data:
                                    # Keep only critical info for citation
                                    keep_keys = {"ref_id", "title", "year", "author", "journal", "citation_key"}
                                    for k in list(item.keys()):
                                        if k not in keep_keys:
                                            item.pop(k, None)
                            elif key == "storyline":
                                # Maybe just keep section titles? For now keep full structure as it's logic
                                pass
                                
                        combined_state[key] = data
                else:
                    with open(filename, 'r', encoding='utf-8') as f:
                        # For context_memory.md, maybe just read last 50 lines?
                        content = f.read()
                        if compact and key == "context_memory":
                            lines = content.split('\n')
                            if len(lines) > 50:
                                combined_state[key] = "...(truncated)...\n" + "\n".join(lines[-50:])
                            else:
                                combined_state[key] = content
                        else:
                            combined_state[key] = content
            except Exception as e:
                combined_state[key] = f"<Error loading {filename}: {str(e)}>"
        else:
            combined_state[key] = None
            
    # 2. Inject Real-time Word Counts (Only if loading progress or generic load)
    if not target_files or "writing_progress" in target_files:
        combined_state["live_word_counts"] = calculate_word_counts()
            
    print(json.dumps(combined_state, indent=2, ensure_ascii=False))
    return combined_state

def preflight_validate_state(
    section=None,
    strict=False,
    origin="manual",
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True,
):
    """Lightweight full-state validation without loading heavy content into context."""
    checks = []
    warnings = []
    ok = True

    # 1) Validate all declared state files
    for key, path in STATE_FILES.items():
        item = {
            "key": key,
            "file": path,
            "exists": os.path.exists(path),
            "parse_ok": None,
            "error": None
        }
        if not item["exists"]:
            item["parse_ok"] = False
            item["error"] = "missing"
            if strict:
                ok = False
            else:
                warnings.append(f"missing:{path}")
        else:
            try:
                if path.endswith(".json"):
                    safe_json_load(path)
                else:
                    with open(path, "r", encoding="utf-8") as f:
                        _ = f.read(1024)
                item["parse_ok"] = True
            except Exception as e:
                item["parse_ok"] = False
                item["error"] = str(e)
                ok = False
        checks.append(item)

    # 2) Validate context memory history files (optional but checked)
    for hist in ("context_memory_v-1.md", "context_memory_v-2.md"):
        item = {
            "key": hist.replace(".md", ""),
            "file": hist,
            "exists": os.path.exists(hist),
            "parse_ok": True,
            "error": None
        }
        if item["exists"]:
            try:
                with open(hist, "r", encoding="utf-8") as f:
                    _ = f.read(1024)
            except Exception as e:
                item["parse_ok"] = False
                item["error"] = str(e)
                ok = False
        checks.append(item)

    # 3) Section-local file sanity (lightweight)
    section_check = None
    if section:
        section_file = os.path.join("section_memory", f"{sanitize_section_id(section)}.md")
        section_check = {
            "section": section,
            "section_memory_file": section_file,
            "section_memory_exists": os.path.exists(section_file),
            "matched_manuscript_files": len(find_section_manuscripts(section))
        }

    schema_report = validate_state_schemas(
        require_matrix_reindex=require_matrix_reindex,
        matrix_file=matrix_file,
        storyline_file=storyline_file,
    )
    if not schema_report.get("ok", False):
        if strict:
            ok = False
        else:
            warnings.append("schema_validation_failed_in_lenient_mode")

    result = {
        "mode": "strict" if strict else "lenient",
        "ok": ok,
        "warnings": warnings,
        "checks": checks,
        "section_check": section_check,
        "schema": schema_report,
    }
    if section:
        update_gate_state(
            section=section,
            preflight_ts=datetime.now().isoformat(timespec="seconds"),
            preflight_ok=ok,
            last_preflight_origin=origin,
            prewrite_ready=False,
            completion_ready=False
        )
    print(json.dumps(result, ensure_ascii=False))
    return result

def rotate_context_memory_versions():
    """Handles versioning for context_memory.md (v-1, v-2)."""
    base_file = "context_memory.md"
    v1_file = "context_memory_v-1.md"
    v2_file = "context_memory_v-2.md"

    if os.path.exists(v1_file):
        shutil.copy2(v1_file, v2_file)
    
    if os.path.exists(base_file):
        shutil.copy2(base_file, v1_file)

def dedup_literature_index(
    index_file="literature_index.json",
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT
):
    """Deduplicate literature index by DOI -> metadata key -> title/fuzzy fallback.
    Returns:
      dict with canonical_entries, old_to_new map (1-based), duplicate_count.
    """
    if not os.path.exists(index_file):
        return {
            "canonical_entries": [],
            "old_to_new": {},
            "duplicate_count": 0,
            "total_before": 0,
            "total_after": 0
        }

    data = read_json_file(index_file)
    if not isinstance(data, list):
        return {
            "canonical_entries": data,
            "old_to_new": {},
            "duplicate_count": 0,
            "total_before": 0,
            "total_after": 0
        }

    seen_doi = {}
    seen_pmid = {}
    seen_title = {}
    seen_meta = {}
    canonical_title_by_idx = {}
    canonical = []
    old_to_new = {}
    duplicates = 0
    conflicts = []
    strategy_counts = {
        "doi": 0,
        "pmid": 0,
        "meta": 0,
        "exact_title": 0,
        "fuzzy_title": 0
    }

    for i, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            entry = {"title": str(entry)}
        doi_key = normalize_doi(entry.get("doi"))
        pmid_key = normalize_pmid(entry.get("pmid"))
        title_key = normalize_title(entry.get("title"))
        author_key = normalize_author(entry.get("authors") or entry.get("author"))
        year_key = str(entry.get("year") or "").strip()
        journal_key = normalize_journal(entry.get("journal"))
        meta_key = f"{author_key}|{year_key}|{journal_key}" if (author_key and year_key and journal_key) else ""

        canonical_idx = None
        if doi_key and doi_key in seen_doi:
            canonical_idx = seen_doi[doi_key]
            strategy_counts["doi"] += 1
        elif pmid_key and pmid_key in seen_pmid:
            canonical_idx = seen_pmid[pmid_key]
            strategy_counts["pmid"] += 1
        elif meta_key and meta_key in seen_meta:
            canonical_idx = seen_meta[meta_key]
            strategy_counts["meta"] += 1
        elif title_key and title_key in seen_title:
            canonical_idx = seen_title[title_key]
            strategy_counts["exact_title"] += 1
        elif title_key:
            best_idx = None
            best_score = 0.0
            for cidx, ctitle in canonical_title_by_idx.items():
                score = title_similarity(title_key, ctitle)
                if score > best_score:
                    best_score = score
                    best_idx = cidx
            if best_idx is not None and best_score >= similarity_threshold:
                canonical_idx = best_idx
                strategy_counts["fuzzy_title"] += 1
            elif best_idx is not None and best_score >= conflict_threshold:
                conflicts.append({
                    "old_number": i,
                    "candidate_number": best_idx,
                    "similarity": round(best_score, 4),
                    "title": entry.get("title", "")
                })

        if canonical_idx is not None:
            _merge_canonical_item(canonical[canonical_idx - 1], entry)
            old_to_new[i] = canonical_idx
            duplicates += 1
            continue

        canonical.append(entry)
        new_idx = len(canonical)
        old_to_new[i] = new_idx
        if doi_key:
            seen_doi[doi_key] = new_idx
        if pmid_key:
            seen_pmid[pmid_key] = new_idx
        if title_key:
            seen_title[title_key] = new_idx
            canonical_title_by_idx[new_idx] = title_key
        if meta_key:
            seen_meta[meta_key] = new_idx

    for idx, entry in enumerate(canonical, start=1):
        if isinstance(entry, dict):
            entry["citation_number"] = idx

    return {
        "canonical_entries": canonical,
        "old_to_new": old_to_new,
        "duplicate_count": duplicates,
        "conflicts": conflicts,
        "strategy_counts": strategy_counts,
        "total_before": len(data),
        "total_after": len(canonical)
    }

def rewrite_citations_in_text(text, old_to_new):
    """Rewrite [n], [n,m], [n-m] citations according to mapping."""
    pattern = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
    changed = False

    def repl(match):
        nonlocal changed
        payload = match.group(1)
        numbers = expand_citation_numbers(payload)
        if not numbers:
            return match.group(0)
        mapped = [old_to_new.get(n, n) for n in numbers]
        compressed = compress_citation_numbers(mapped)
        new_token = f"[{compressed}]" if compressed else match.group(0)
        if new_token != match.group(0):
            changed = True
        return new_token

    new_text = pattern.sub(repl, text)
    return new_text, changed

def rewrite_reference_sections(
    text,
    old_to_new,
    canonical_entries=None,
    strict_rebuild=False,
    reference_style=DEFAULT_REFERENCE_STYLE
):
    """Rewrite numbered entries inside References sections.

    strict_rebuild=True: rebuild references block to continuous 1..N from canonical entries.
    """
    lines = text.splitlines()
    out = []
    changed = False
    i = 0

    heading_re = re.compile(r"^\s{0,3}#{1,6}\s*(references|参考文献)\s*$", re.IGNORECASE)
    next_heading_re = re.compile(r"^\s{0,3}#{1,6}\s+\S+")
    ref_item_re = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")

    while i < len(lines):
        line = lines[i]
        if not heading_re.match(line):
            out.append(line)
            i += 1
            continue

        # Keep heading line
        out.append(line)
        i += 1

        # Collect section block until next heading or EOF
        block = []
        while i < len(lines) and not next_heading_re.match(lines[i]):
            block.append(lines[i])
            i += 1

        # Strict mode: rebuild entire block from canonical index.
        if strict_rebuild and isinstance(canonical_entries, list):
            rebuilt = [
                format_reference_entry(entry, idx, style=reference_style)
                for idx, entry in enumerate(canonical_entries, start=1)
            ]
            if block != rebuilt:
                changed = True
            out.extend(rebuilt)
            continue

        # Legacy mode: remap existing numbered entries in this block.
        mapped_block = []
        seen_numbers = set()
        for bline in block:
            m = ref_item_re.match(bline)
            if not m:
                mapped_block.append(bline)
                continue
            indent, old_num_text, content = m.groups()
            old_num = int(old_num_text)
            new_num = old_to_new.get(old_num, old_num)
            if new_num in seen_numbers:
                changed = True
                continue
            seen_numbers.add(new_num)
            mapped_block.append(f"{indent}{new_num}. {content}")
            if new_num != old_num:
                changed = True

        out.extend(mapped_block)

    new_text = "\n".join(out)
    if text.endswith("\n"):
        new_text += "\n"
    return new_text, changed

def rewrite_docx_citations(old_to_new, manuscript_dir=DEFAULT_MANUSCRIPT_DIR):
    """Best-effort citation rewrite for .docx by editing XML text payloads."""
    if not os.path.exists(manuscript_dir):
        return {"files_changed": 0, "files_scanned": 0}

    docx_files = sorted(glob.glob(os.path.join(manuscript_dir, "*.docx")))
    changed_count = 0
    xml_targets = (
        "word/document.xml",
        "word/footnotes.xml",
        "word/endnotes.xml",
        "word/comments.xml",
    )

    for docx_path in docx_files:
        docx_changed = False
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(docx_path, "r") as zin:
                zin.extractall(tmpdir)

            for rel_path in xml_targets:
                xml_path = os.path.join(tmpdir, rel_path)
                if not os.path.exists(xml_path):
                    continue
                try:
                    with open(xml_path, "r", encoding="utf-8") as f:
                        xml_text = f.read()
                    rewritten, changed = rewrite_citations_in_text(xml_text, old_to_new)
                    if changed:
                        with open(xml_path, "w", encoding="utf-8") as f:
                            f.write(rewritten)
                        docx_changed = True
                except Exception:
                    continue

            if docx_changed:
                tmp_output = os.path.join(tmpdir, "rewritten.docx")
                with zipfile.ZipFile(tmp_output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                    for root, _, files in os.walk(tmpdir):
                        for name in files:
                            src = os.path.join(root, name)
                            if src == tmp_output:
                                continue
                            rel = os.path.relpath(src, tmpdir)
                            zout.write(src, rel)
                shutil.copy2(tmp_output, docx_path)
                changed_count += 1

    return {"files_changed": changed_count, "files_scanned": len(docx_files)}

def rewrite_manuscript_citations(old_to_new, manuscript_dir=DEFAULT_MANUSCRIPT_DIR, rewrite_docx=True):
    """Apply citation remap to manuscript markdown/docx files."""
    if not os.path.exists(manuscript_dir):
        return {"files_changed": 0, "files_scanned": 0, "docx": {"files_changed": 0, "files_scanned": 0}}

    md_changed_count = 0
    md_files = sorted(glob.glob(os.path.join(manuscript_dir, "*.md")))
    for path in md_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                original = f.read()
            rewritten, changed_cites = rewrite_citations_in_text(original, old_to_new)
            rewritten, changed_refs = rewrite_reference_sections(rewritten, old_to_new)
            if changed_cites or changed_refs:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rewritten)
                md_changed_count += 1
        except Exception:
            continue

    docx_report = {"files_changed": 0, "files_scanned": 0}
    if rewrite_docx:
        docx_report = rewrite_docx_citations(old_to_new, manuscript_dir=manuscript_dir)

    return {
        "files_changed": md_changed_count + docx_report["files_changed"],
        "files_scanned": len(md_files) + docx_report["files_scanned"],
        "md": {"files_changed": md_changed_count, "files_scanned": len(md_files)},
        "docx": docx_report
    }


def rewrite_manuscript_citations_strict(
    old_to_new,
    canonical_entries,
    manuscript_dir=DEFAULT_MANUSCRIPT_DIR,
    rewrite_docx=False,
    reference_style=DEFAULT_REFERENCE_STYLE
):
    """Rewrite in-text citations and strictly rebuild References/参考文献 blocks."""
    if not os.path.exists(manuscript_dir):
        return {"files_changed": 0, "files_scanned": 0, "docx": {"files_changed": 0, "files_scanned": 0}}

    md_changed_count = 0
    md_files = sorted(glob.glob(os.path.join(manuscript_dir, "*.md")))
    for path in md_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                original = f.read()
            rewritten, changed_cites = rewrite_citations_in_text(original, old_to_new)
            rewritten, changed_refs = rewrite_reference_sections(
                rewritten,
                old_to_new,
                canonical_entries=canonical_entries,
                strict_rebuild=True,
                reference_style=reference_style
            )
            if changed_cites or changed_refs:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rewritten)
                md_changed_count += 1
        except Exception:
            continue

    docx_report = {"files_changed": 0, "files_scanned": 0}
    if rewrite_docx:
        docx_report = rewrite_docx_citations(old_to_new, manuscript_dir=manuscript_dir)

    return {
        "files_changed": md_changed_count + docx_report["files_changed"],
        "files_scanned": len(md_files) + docx_report["files_scanned"],
        "md": {"files_changed": md_changed_count, "files_scanned": len(md_files)},
        "docx": docx_report
    }


def prune_old_literature_backups(backup_root="backups", keep=DEFAULT_BACKUP_KEEP, max_age_days=None):
    target_root = os.path.join(backup_root, "literature_sync")
    if not os.path.exists(target_root):
        return {"removed": [], "kept": 0}

    dirs = [d for d in glob.glob(os.path.join(target_root, "lit_sync_*")) if os.path.isdir(d)]
    dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    removed = []

    now_ts = datetime.now().timestamp()
    for idx, d in enumerate(dirs):
        remove_by_count = idx >= max(1, int(keep))
        remove_by_age = False
        if max_age_days is not None:
            age_days = (now_ts - os.path.getmtime(d)) / 86400.0
            remove_by_age = age_days > float(max_age_days)
        if remove_by_count or remove_by_age:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d)

    return {"removed": removed, "kept": max(0, len(dirs) - len(removed))}

def backup_literature_sync_assets(
    index_file="literature_index.json",
    manuscript_dir=DEFAULT_MANUSCRIPT_DIR,
    backup_root="backups",
    backup_keep=DEFAULT_BACKUP_KEEP,
    backup_max_days=None
):
    """Backup literature index + manuscript md/docx into dedicated subfolder before sync."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(backup_root, "literature_sync", f"lit_sync_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)

    copied_files = []
    if os.path.exists(index_file):
        target = os.path.join(backup_dir, os.path.basename(index_file))
        shutil.copy2(index_file, target)
        copied_files.append(target)

    if os.path.exists(manuscript_dir):
        target_dir = os.path.join(backup_dir, "manuscripts")
        os.makedirs(target_dir, exist_ok=True)
        for ext in ("*.md", "*.docx"):
            for src in sorted(glob.glob(os.path.join(manuscript_dir, ext))):
                dst = os.path.join(target_dir, os.path.basename(src))
                shutil.copy2(src, dst)
                copied_files.append(dst)

    manifest = {
        "backup_created_at": timestamp,
        "index_file": index_file,
        "manuscript_dir": manuscript_dir,
        "copied_files_count": len(copied_files),
        "copied_files": copied_files
    }
    with open(os.path.join(backup_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    prune = prune_old_literature_backups(
        backup_root=backup_root,
        keep=backup_keep,
        max_age_days=backup_max_days
    )
    with open(os.path.join(backup_dir, "prune_report.json"), "w", encoding="utf-8") as f:
        json.dump(prune, f, indent=2, ensure_ascii=False)

    return backup_dir

def restore_literature_sync_backup(backup_dir, index_file="literature_index.json", manuscript_dir=DEFAULT_MANUSCRIPT_DIR):
    if not backup_dir or not os.path.exists(backup_dir):
        return False

    backup_index = os.path.join(backup_dir, os.path.basename(index_file))
    if os.path.exists(backup_index):
        shutil.copy2(backup_index, index_file)

    backup_manuscripts = os.path.join(backup_dir, "manuscripts")
    if os.path.exists(backup_manuscripts):
        os.makedirs(manuscript_dir, exist_ok=True)
        for src in glob.glob(os.path.join(backup_manuscripts, "*")):
            shutil.copy2(src, os.path.join(manuscript_dir, os.path.basename(src)))
    return True

def collect_citation_numbers(text):
    pattern = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
    found = []
    for m in pattern.finditer(text):
        found.extend(expand_citation_numbers(m.group(1)))
    return sorted(OrderedDict.fromkeys(found))

def validate_number_integrity(index_file="literature_index.json", manuscript_dir=DEFAULT_MANUSCRIPT_DIR):
    """Validate that all in-text citations map to existing literature entries."""
    if not os.path.exists(index_file):
        return {"ok": False, "reason": "literature_index.json missing"}

    data = read_json_file(index_file)
    if not isinstance(data, list):
        return {"ok": False, "reason": "literature_index.json is not a list"}

    max_ref = len(data)
    citations = []

    # Scan markdown
    for md_path in sorted(glob.glob(os.path.join(manuscript_dir, "*.md"))):
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                citations.extend(collect_citation_numbers(f.read()))
        except Exception:
            continue

    # Scan docx XML payloads for bracket citations
    for docx_path in sorted(glob.glob(os.path.join(manuscript_dir, "*.docx"))):
        try:
            with zipfile.ZipFile(docx_path, "r") as zin:
                for rel in ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml"):
                    if rel not in zin.namelist():
                        continue
                    payload = zin.read(rel).decode("utf-8", errors="ignore")
                    citations.extend(collect_citation_numbers(payload))
        except Exception:
            continue

    citations = sorted(OrderedDict.fromkeys(citations))
    out_of_range = [n for n in citations if n < 1 or n > max_ref]
    return {
        "ok": len(out_of_range) == 0,
        "max_reference_number": max_ref,
        "used_citations": citations,
        "out_of_range": out_of_range
    }

def build_literature_sync_preview(
    index_file="literature_index.json",
    manuscript_dir=DEFAULT_MANUSCRIPT_DIR,
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT,
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True
):
    result = dedup_literature_index(
        index_file=index_file,
        similarity_threshold=similarity_threshold,
        conflict_threshold=conflict_threshold
    )
    result, matrix_report = apply_matrix_reindex(
        result,
        matrix_file=matrix_file,
        storyline_file=storyline_file,
        require_matrix_reindex=require_matrix_reindex
    )
    old_to_new = result.get("old_to_new", {})
    changed_pairs = [
        {"old": int(k), "new": int(v)}
        for k, v in old_to_new.items()
        if int(k) != int(v)
    ]

    md_preview = []
    for path in sorted(glob.glob(os.path.join(manuscript_dir, "*.md"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            cnums = collect_citation_numbers(content)
            impacted = [n for n in cnums if old_to_new.get(n, n) != n]
            if impacted:
                md_preview.append({
                    "file": path,
                    "impacted_old_numbers": sorted(OrderedDict.fromkeys(impacted))
                })
        except Exception:
            continue

    return {
        "index_file": index_file,
        "total_before": result.get("total_before", 0),
        "total_after": result.get("total_after", 0),
        "duplicates_removed": result.get("duplicate_count", 0),
        "number_changes": len(changed_pairs),
        "changed_pairs_preview": changed_pairs[:30],
        "dedup_conflicts": result.get("conflicts", []),
        "dedup_strategy_counts": result.get("strategy_counts", {}),
        "matrix_reindex": matrix_report,
        "affected_markdown_files": md_preview,
        "affected_markdown_files_count": len(md_preview),
        "strict_references_rebuild": True,
        "rewrite_docx_default": False
    }


def sync_global_literature(
    index_file="literature_index.json",
    rewrite_manuscripts=True,
    backup_first=True,
    rewrite_docx=False,
    dry_run=False,
    apply_changes=False,
    strict_references=True,
    reference_style=DEFAULT_REFERENCE_STYLE,
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT,
    allow_conflicts=False,
    backup_keep=DEFAULT_BACKUP_KEEP,
    backup_max_days=None,
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True
):
    """Deduplicate literature index + remap citations.

    Safety model:
    - dry_run=True returns preview only.
    - apply_changes=True writes files.
    - if both False, defaults to preview-only.
    """
    mode = "dry-run" if (dry_run or not apply_changes) else "apply"
    schema = validate_state_schemas(
        require_matrix_reindex=require_matrix_reindex,
        matrix_file=matrix_file,
        storyline_file=storyline_file,
    )
    if not schema.get("ok", False):
        out = {
            "mode": mode,
            "applied": False,
            "error": "schema_validation_failed",
            "schema": schema,
        }
        out["report_file"] = write_sync_report("error", out)
        out["transaction_log"] = write_transaction_log("sync_literature", {
            "command": "sync-literature",
            "mode": mode,
            "ok": False,
            "error": out["error"],
            "schema_error_count": len(schema.get("errors", [])),
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        return out

    try:
        preview = build_literature_sync_preview(
            index_file=index_file,
            similarity_threshold=similarity_threshold,
            conflict_threshold=conflict_threshold,
            matrix_file=matrix_file,
            storyline_file=storyline_file,
            require_matrix_reindex=require_matrix_reindex
        )
    except Exception as e:
        out = {
            "mode": mode,
            "applied": False,
            "error": f"matrix_reindex_gate_failed: {e}"
        }
        out["report_file"] = write_sync_report("error", out)
        out["transaction_log"] = write_transaction_log("sync_literature", {
            "command": "sync-literature",
            "mode": mode,
            "ok": False,
            "error": out["error"],
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        return out
    ensure_state_dir()
    with open(os.path.join(GATE_STATE_DIR, "lit_sync_preview.json"), "w", encoding="utf-8") as f:
        json.dump(preview, f, indent=2, ensure_ascii=False)

    if dry_run or not apply_changes:
        out = {
            "mode": "dry-run",
            "preview": preview,
            "applied": False
        }
        out["report_file"] = write_sync_report("dry_run", out)
        out["transaction_log"] = write_transaction_log("sync_literature", {
            "command": "sync-literature",
            "mode": "dry-run",
            "ok": True,
            "applied": False,
            "duplicates_removed_preview": preview.get("duplicates_removed"),
            "number_changes_preview": preview.get("number_changes"),
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        return out

    backup_dir = None
    try:
        with FileLock("literature_sync_apply"):
            if backup_first:
                backup_dir = backup_literature_sync_assets(
                    index_file=index_file,
                    backup_keep=backup_keep,
                    backup_max_days=backup_max_days
                )

            result = dedup_literature_index(
                index_file=index_file,
                similarity_threshold=similarity_threshold,
                conflict_threshold=conflict_threshold
            )
            result, matrix_report = apply_matrix_reindex(
                result,
                matrix_file=matrix_file,
                storyline_file=storyline_file,
                require_matrix_reindex=require_matrix_reindex
            )
            if result.get("conflicts") and not allow_conflicts:
                raise RuntimeError(
                    "Dedup conflicts detected; aborting apply. "
                    "Use --allow-conflicts only after reviewing dry-run report."
                )
            canonical = result["canonical_entries"]

            if isinstance(canonical, list):
                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(canonical, f, indent=2, ensure_ascii=False)

            rewrite_report = {"files_changed": 0, "files_scanned": 0}
            if rewrite_manuscripts and isinstance(result["old_to_new"], dict):
                if strict_references:
                    rewrite_report = rewrite_manuscript_citations_strict(
                        result["old_to_new"],
                        result.get("canonical_entries", []),
                        rewrite_docx=rewrite_docx,
                        reference_style=reference_style
                    )
                else:
                    rewrite_report = rewrite_manuscript_citations(
                        result["old_to_new"],
                        rewrite_docx=rewrite_docx
                    )

            validation = validate_number_integrity(index_file=index_file)
            if not validation.get("ok", False):
                raise RuntimeError(f"Citation validation failed: out_of_range={validation.get('out_of_range')}")

            summary = {
                "mode": "apply",
                "index_file": index_file,
                "backup_dir": backup_dir,
                "total_before": result["total_before"],
                "total_after": result["total_after"],
                "duplicates_removed": result["duplicate_count"],
                "dedup_conflicts": result.get("conflicts", []),
                "dedup_strategy_counts": result.get("strategy_counts", {}),
                "matrix_reindex": matrix_report,
                "allow_conflicts": bool(allow_conflicts),
                "manuscripts": rewrite_report,
                "validation": validation,
                "rolled_back": False,
                "applied": True,
                "strict_references_rebuild": strict_references
            }
            summary["report_file"] = write_sync_report("apply", summary)
            summary["transaction_log"] = write_transaction_log("sync_literature", {
                "command": "sync-literature",
                "mode": "apply",
                "ok": True,
                "applied": True,
                "backup_dir": backup_dir,
                "duplicates_removed": summary.get("duplicates_removed"),
                "number_changes": ((preview or {}).get("number_changes")),
                "files_changed": (rewrite_report or {}).get("files_changed"),
                "strict_references_rebuild": bool(strict_references),
                "ts": datetime.now().isoformat(timespec="seconds"),
            })
            return summary
    except Exception as e:
        restored = False
        if backup_dir:
            restored = restore_literature_sync_backup(backup_dir, index_file=index_file)
        err = str(e)
        error_type = "lock_acquire_failed" if "lock '" in err else "sync_apply_failed"
        out = {
            "index_file": index_file,
            "backup_dir": backup_dir,
            "error": err,
            "error_type": error_type,
            "rolled_back": restored
        }
        out["report_file"] = write_sync_report("error", out)
        out["transaction_log"] = write_transaction_log("sync_literature", {
            "command": "sync-literature",
            "mode": "apply",
            "ok": False,
            "applied": False,
            "error": err,
            "error_type": error_type,
            "rolled_back": restored,
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        return out

def postwrite_state(
    section,
    status="updated",
    summary="",
    create_snapshot=False,
    sync_literature=False,
    rewrite_manuscripts=True,
    backup_first=True,
    rewrite_docx=False,
    sync_apply=False,
    strict_references=True,
    reference_style=DEFAULT_REFERENCE_STYLE,
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT,
    allow_conflicts=False,
    backup_keep=DEFAULT_BACKUP_KEEP,
    backup_max_days=None,
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True
):
    """Auto-sync global progress after each writing turn."""
    ok, reason = validate_gate(section, "prewrite")
    if not ok:
        payload = {
            "error": "prewrite_gate_failed",
            "reason": reason,
            "hint": "Run write-cycle --section <id> before postwrite"
        }
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(2)

    try:
        with FileLock("state_update"):
            timestamp = datetime.now().isoformat(timespec="seconds")
            updated_files = []

            # 1) Update global writing progress
            progress_file = STATE_FILES["writing_progress"]
            progress_data = {}
            if os.path.exists(progress_file):
                try:
                    current = read_json_file(progress_file)
                    if isinstance(current, dict):
                        progress_data = current
                except Exception:
                    progress_data = {}

            progress_data["last_section"] = section
            progress_data["last_updated"] = timestamp
            progress_data["status"] = status
            if summary:
                progress_data["last_summary"] = summary

            history = progress_data.get("update_history", [])
            if not isinstance(history, list):
                history = []
            history.append({
                "ts": timestamp,
                "section": section,
                "status": status,
                "summary": summary[:200]
            })
            progress_data["update_history"] = history[-50:]

            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            updated_files.append(progress_file)

            # 2) Update global context memory with version rotation
            context_file = STATE_FILES["context_memory"]
            existing = ""
            if os.path.exists(context_file):
                with open(context_file, "r", encoding="utf-8") as f:
                    existing = f.read().rstrip()
                rotate_context_memory_versions()

            note = f"[{timestamp}] section={section}; status={status}"
            if summary:
                note += f"; summary={summary}"

            new_content = f"{existing}\n{note}".strip() + "\n"
            with open(context_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated_files.append(context_file)

            literature_report = None
            if sync_literature:
                literature_report = sync_global_literature(
                    index_file=STATE_FILES["literature_index"],
                    rewrite_manuscripts=rewrite_manuscripts,
                    backup_first=backup_first,
                    rewrite_docx=rewrite_docx,
                    dry_run=not sync_apply,
                    apply_changes=sync_apply,
                    strict_references=strict_references,
                    reference_style=reference_style,
                    similarity_threshold=similarity_threshold,
                    conflict_threshold=conflict_threshold,
                    allow_conflicts=allow_conflicts,
                    backup_keep=backup_keep,
                    backup_max_days=backup_max_days,
                    matrix_file=matrix_file,
                    storyline_file=storyline_file,
                    require_matrix_reindex=require_matrix_reindex
                )

            completion_ready = bool(
                sync_literature
                and sync_apply
                and isinstance(literature_report, dict)
                and literature_report.get("applied", False)
                and not literature_report.get("error")
            )
            update_gate_state(
                section=section,
                last_postwrite_ts=timestamp,
                postwrite_sync_literature=bool(sync_literature),
                postwrite_sync_apply=bool(sync_apply),
                completion_ready=completion_ready
            )

            if create_snapshot:
                backup_project_state()

            result = {
                "updated_files": updated_files,
                "literature_sync": literature_report,
                "gate": {
                    "section": section,
                    "completion_ready": completion_ready,
                    "requires": "postwrite --sync-literature --sync-apply"
                }
            }
            print(json.dumps(result, ensure_ascii=False))
            return result
    except RuntimeError as e:
        payload = {"error": "lock_acquire_failed", "reason": str(e), "lock": "state_update"}
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(2)


def gate_check(section, phase):
    ok, reason = validate_gate(section, phase)
    payload = {
        "section": section,
        "phase": phase,
        "ok": ok,
        "reason": reason,
        "gate_file": GATE_STATE_FILE,
        "state": read_gate_state()
    }
    print(json.dumps(payload, ensure_ascii=False))
    if not ok:
        sys.exit(2)
    return payload


def write_cycle(
    section,
    compact=True,
    token_budget=DEFAULT_TOKEN_BUDGET,
    tail_lines=DEFAULT_TAIL_LINES,
    include_draft=False,
    finalize=False,
    status="updated",
    summary="",
    sync_literature=False,
    sync_apply=False,
    strict_references=True,
    rewrite_docx=False,
    no_backup=False,
    reference_style=DEFAULT_REFERENCE_STYLE,
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT,
    allow_conflicts=False,
    backup_keep=DEFAULT_BACKUP_KEEP,
    backup_max_days=None,
    preflight_strict=True,
    matrix_file=DEFAULT_LITERATURE_MATRIX_FILE,
    storyline_file=STATE_FILES["storyline"],
    require_matrix_reindex=True
):
    tx = {
        "command": "write-cycle",
        "section": section,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "params": {
            "compact": bool(compact),
            "token_budget": token_budget,
            "tail_lines": tail_lines,
            "include_draft": bool(include_draft),
            "finalize": bool(finalize),
            "sync_literature": bool(sync_literature),
            "sync_apply": bool(sync_apply),
            "strict_references": bool(strict_references),
            "preflight_strict": bool(preflight_strict),
            "matrix_file": matrix_file,
            "storyline_file": storyline_file,
            "require_matrix_reindex": bool(require_matrix_reindex),
        },
        "ok": False,
    }
    try:
        start_cycle(section)

        # 1) hard gate preflight
        preflight = preflight_validate_state(
            section=section,
            strict=preflight_strict,
            origin="write-cycle",
            matrix_file=matrix_file,
            storyline_file=storyline_file,
            require_matrix_reindex=require_matrix_reindex,
        )
        tx["preflight"] = {
            "ok": bool((preflight or {}).get("ok")),
            "mode": (preflight or {}).get("mode"),
            "schema_ok": bool(((preflight or {}).get("schema") or {}).get("ok")),
            "schema_error_count": len((((preflight or {}).get("schema") or {}).get("errors") or [])),
        }

        # 2) scoped load (global history + section indexes)
        loaded = load_state(
            compact=compact,
            section=section,
            token_budget=token_budget,
            tail_lines=tail_lines,
            with_global_history=True,
            include_draft=include_draft,
            origin="write-cycle"
        )
        tx["load"] = summarize_bundle_for_log(loaded)

        prewrite_gate = gate_check(section=section, phase="prewrite")
        tx["prewrite_gate"] = {
            "ok": bool((prewrite_gate or {}).get("ok")),
            "reason": (prewrite_gate or {}).get("reason"),
        }

        # 3) Optional finalize step after writing content externally
        if finalize:
            post = postwrite_state(
                section=section,
                status=status,
                summary=summary,
                create_snapshot=False,
                sync_literature=sync_literature,
                rewrite_manuscripts=True,
                backup_first=not no_backup,
                rewrite_docx=rewrite_docx,
                sync_apply=sync_apply,
                strict_references=strict_references,
                reference_style=reference_style,
                similarity_threshold=similarity_threshold,
                conflict_threshold=conflict_threshold,
                allow_conflicts=allow_conflicts,
                backup_keep=backup_keep,
                backup_max_days=backup_max_days,
                matrix_file=matrix_file,
                storyline_file=storyline_file,
                require_matrix_reindex=require_matrix_reindex
            )
            tx["postwrite"] = {
                "updated_files_count": len((post or {}).get("updated_files", []) or []),
                "completion_ready": ((post or {}).get("gate") or {}).get("completion_ready"),
                "literature_sync_applied": ((post or {}).get("literature_sync") or {}).get("applied"),
                "literature_sync_error": ((post or {}).get("literature_sync") or {}).get("error"),
            }

        tx["ok"] = True
    except SystemExit as e:
        tx["ok"] = False
        tx["error"] = f"SystemExit:{e.code}"
        raise
    except Exception as e:
        tx["ok"] = False
        tx["error"] = str(e)
        raise
    finally:
        tx["finished_at"] = datetime.now().isoformat(timespec="seconds")
        tx_path = write_transaction_log("write_cycle", tx)
        update_gate_state(last_write_cycle_log=tx_path)

def update_state(payload_path):
    """Updates state files based on a JSON payload file."""
    if not os.path.exists(payload_path):
        print(f"Error: Payload file '{payload_path}' not found.")
        sys.exit(1)

    try:
        with open(payload_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in payload file: {e}")
        sys.exit(1)

    updated_files = []

    for key, content in payload.items():
        if key == "section_memory":
            if not isinstance(content, dict) or "section" not in content:
                print("Warning: section_memory payload must be {'section': 'results_3.1', 'content': '...'}")
                continue
            section = sanitize_section_id(str(content.get("section", "")).strip())
            section_text = str(content.get("content", ""))
            if not section:
                print("Warning: section_memory.section is empty. Skipping.")
                continue
            memory_dir = "section_memory"
            os.makedirs(memory_dir, exist_ok=True)
            section_file = os.path.join(memory_dir, f"{section}.md")
            try:
                with open(section_file, "w", encoding="utf-8") as f:
                    f.write(section_text)
                updated_files.append(section_file)
            except Exception as e:
                print(f"Error writing section memory {section_file}: {e}")
            continue

        if key not in STATE_FILES:
            print(f"Warning: Unknown key '{key}' in payload. Skipping.")
            continue
        
        filename = STATE_FILES[key]
        
        try:
            # Special handling for context_memory versioning
            if key == "context_memory":
                # Only rotate if content actually changed or if file exists
                if os.path.exists(filename):
                     rotate_context_memory_versions()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            # JSON files
            elif filename.endswith(".json"):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
            
            # Text/Markdown files
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            updated_files.append(filename)
            
        except Exception as e:
            print(f"Error writing to {filename}: {e}")

    print(f"Successfully updated: {', '.join(updated_files)}")
    
    # Auto-delete payload file to keep directory clean
    try:
        os.remove(payload_path)
    except:
        pass

def backup_project_state(backup_dir="backups"):
    """Creates a full project snapshot including all state files and manuscripts."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = os.path.join(backup_dir, f"snapshot_{timestamp}")
    
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)
        
    # 1. Backup State Files
    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            shutil.copy2(filename, snapshot_dir)
            
    # 2. Backup Manuscripts
    manuscript_dir = "manuscripts"
    if os.path.exists(manuscript_dir):
        target_manuscript_dir = os.path.join(snapshot_dir, "manuscripts")
        shutil.copytree(manuscript_dir, target_manuscript_dir)

    # 3. Backup section-level memory (if available)
    if os.path.exists("section_memory"):
        shutil.copytree("section_memory", os.path.join(snapshot_dir, "section_memory"))
        
    print(f"✅ Full project snapshot created at: {snapshot_dir}")
    return snapshot_dir


def list_snapshot_backups(backup_dir="backups"):
    root = backup_dir
    if not os.path.exists(root):
        return []
    dirs = [d for d in glob.glob(os.path.join(root, "snapshot_*")) if os.path.isdir(d)]
    dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return dirs


def restore_project_snapshot(snapshot_dir):
    if not snapshot_dir or not os.path.exists(snapshot_dir):
        return {"restored": False, "reason": "snapshot_not_found", "snapshot_dir": snapshot_dir}

    restored_files = []

    # Restore state files.
    for _, filename in STATE_FILES.items():
        src = os.path.join(snapshot_dir, filename)
        if os.path.exists(src):
            shutil.copy2(src, filename)
            restored_files.append(filename)

    # Restore manuscripts.
    src_manuscripts = os.path.join(snapshot_dir, "manuscripts")
    if os.path.exists(src_manuscripts):
        os.makedirs(DEFAULT_MANUSCRIPT_DIR, exist_ok=True)
        for src in glob.glob(os.path.join(src_manuscripts, "*")):
            dst = os.path.join(DEFAULT_MANUSCRIPT_DIR, os.path.basename(src))
            shutil.copy2(src, dst)
            restored_files.append(dst)

    # Restore section memory.
    src_memory = os.path.join(snapshot_dir, "section_memory")
    if os.path.exists(src_memory):
        os.makedirs("section_memory", exist_ok=True)
        for src in glob.glob(os.path.join(src_memory, "*")):
            dst = os.path.join("section_memory", os.path.basename(src))
            shutil.copy2(src, dst)
            restored_files.append(dst)

    return {
        "restored": True,
        "snapshot_dir": snapshot_dir,
        "restored_files_count": len(restored_files),
        "restored_files": restored_files,
    }


def rollback_state(target="snapshot", backup_dir="backups", snapshot_dir=None):
    """Rollback project state from latest snapshot or literature sync backup."""
    if target == "snapshot":
        chosen = snapshot_dir
        if not chosen:
            snapshots = list_snapshot_backups(backup_dir=backup_dir)
            chosen = snapshots[0] if snapshots else None
        result = restore_project_snapshot(chosen)
        result["target"] = "snapshot"
        return result

    if target == "literature_sync":
        lit_root = os.path.join(backup_dir, "literature_sync")
        candidates = [d for d in glob.glob(os.path.join(lit_root, "lit_sync_*")) if os.path.isdir(d)]
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        chosen = snapshot_dir or (candidates[0] if candidates else None)
        ok = restore_literature_sync_backup(chosen, index_file=STATE_FILES["literature_index"])
        return {
            "target": "literature_sync",
            "restored": bool(ok),
            "backup_dir": chosen,
        }

    return {"restored": False, "reason": f"unknown rollback target: {target}"}


def word_count(section=None, include_references=False):
    payload = calculate_word_counts(exclude_references=(not include_references), section=section)
    if section:
        payload["section_filter"] = section
    print(json.dumps(payload, ensure_ascii=False))


def count_index_entries(payload):
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("references", "items", "entries", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return len(payload)
    return 0


def stats(section=None, include_history=False, backup_dir="backups"):
    """Project dashboard stats for /stats command."""
    now = datetime.now().isoformat(timespec="seconds")

    wp = {}
    if os.path.exists(STATE_FILES["writing_progress"]):
        try:
            data = read_json_file(STATE_FILES["writing_progress"])
            if isinstance(data, dict):
                wp = data
        except Exception:
            wp = {}

    gate = read_gate_state()

    lit_count = 0
    if os.path.exists(STATE_FILES["literature_index"]):
        try:
            lit_count = count_index_entries(read_json_file(STATE_FILES["literature_index"]))
        except Exception:
            lit_count = 0

    fig_count = 0
    if os.path.exists(STATE_FILES["figures_database"]):
        try:
            fig_count = count_index_entries(read_json_file(STATE_FILES["figures_database"]))
        except Exception:
            fig_count = 0

    si_count = 0
    if os.path.exists(STATE_FILES["si_database"]):
        try:
            si_count = count_index_entries(read_json_file(STATE_FILES["si_database"]))
        except Exception:
            si_count = 0

    md_files = sorted(glob.glob(os.path.join(DEFAULT_MANUSCRIPT_DIR, "*.md")))
    docx_files = sorted(glob.glob(os.path.join(DEFAULT_MANUSCRIPT_DIR, "*.docx")))
    wc = calculate_word_counts(exclude_references=True, section=section)

    snapshots = list_snapshot_backups(backup_dir=backup_dir)
    lit_sync_dirs = [d for d in glob.glob(os.path.join(backup_dir, "literature_sync", "lit_sync_*")) if os.path.isdir(d)]

    payload = {
        "timestamp": now,
        "section_filter": section,
        "writing_progress": {
            "last_section": wp.get("last_section"),
            "last_updated": wp.get("last_updated"),
            "status": wp.get("status"),
        },
        "word_count": wc,
        "literature_index_count": lit_count,
        "figures_index_count": fig_count,
        "si_index_count": si_count,
        "manuscripts": {
            "md_files": len(md_files),
            "docx_files": len(docx_files),
        },
        "gate": {
            "section": gate.get("section"),
            "prewrite_ready": gate.get("prewrite_ready"),
            "completion_ready": gate.get("completion_ready"),
            "preflight_ok": gate.get("preflight_ok"),
            "last_preflight_origin": gate.get("last_preflight_origin"),
            "last_load_origin": gate.get("last_load_origin"),
            "last_postwrite_ts": gate.get("last_postwrite_ts"),
            "last_write_cycle_log": gate.get("last_write_cycle_log"),
        },
        "backups": {
            "snapshot_count": len(snapshots),
            "latest_snapshot": snapshots[0] if snapshots else None,
            "literature_sync_count": len(lit_sync_dirs),
        },
    }
    if include_history:
        history = wp.get("update_history", [])
        if not isinstance(history, list):
            history = []
        payload["writing_progress"]["recent_history"] = history[-10:]

    print(json.dumps(payload, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Manage state files for Article Writing Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Load command
    load_parser = subparsers.add_parser("load", help="Load state files")
    load_parser.add_argument("--files", help="Comma-separated list of files to load (e.g. 'storyline,progress')")
    load_parser.add_argument("--compact", action="store_true", help="Remove bulky fields like abstracts")
    load_parser.add_argument("--section", help="Section-local scope, e.g. 'results_3.1'")
    load_parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET, help="Approx token budget for section-local load")
    load_parser.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES, help="Tail lines kept when auto-trimming text")
    load_parser.add_argument("--with-global-history", action="store_true", help="When used with --section, also load full global history/state bundle")
    load_parser.add_argument("--include-draft", action="store_true", help="When used with --section, include current section manuscript draft files")

    # Preflight command
    preflight_parser = subparsers.add_parser("preflight", help="Lightweight validation of all state/history files")
    preflight_parser.add_argument("--section", help="Optional section id for section-local sanity check")
    preflight_parser.add_argument("--strict", action="store_true", help="Strict mode: missing required files fails preflight")
    preflight_parser.add_argument("--matrix-file", default=DEFAULT_LITERATURE_MATRIX_FILE, help="Section-literature matrix file path")
    preflight_parser.add_argument("--storyline-file", default=STATE_FILES["storyline"], help="Storyline JSON used for schema checks")
    preflight_parser.add_argument("--no-require-matrix-reindex", action="store_true", help="Do not require matrix mapping during schema check")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update state files from a payload")
    update_parser.add_argument("payload_file", help="Path to the JSON file containing updates")

    # Postwrite command
    postwrite_parser = subparsers.add_parser("postwrite", help="Auto-sync global progress/context after a writing turn")
    postwrite_parser.add_argument("--section", required=True, help="Current section id, e.g. 'results_3.1'")
    postwrite_parser.add_argument("--status", default="updated", help="Progress status, e.g. updated/draft/reviewed")
    postwrite_parser.add_argument("--summary", default="", help="Short summary of this turn")
    postwrite_parser.add_argument("--sync-literature", action="store_true", help="Deduplicate global literature index during postwrite")
    postwrite_parser.add_argument("--sync-apply", action="store_true", help="Apply literature sync changes (default is dry-run preview)")
    postwrite_parser.add_argument("--strict-references", action="store_true", help="Strictly rebuild References/参考文献 to continuous 1..N")
    postwrite_parser.add_argument("--reference-style", choices=["vancouver", "nature"], default=DEFAULT_REFERENCE_STYLE, help="References rebuild style")
    postwrite_parser.add_argument("--similarity-threshold", type=float, default=DEFAULT_DEDUP_SIMILARITY, help="Dedup fuzzy-title similarity threshold")
    postwrite_parser.add_argument("--conflict-threshold", type=float, default=DEFAULT_DEDUP_CONFLICT, help="Dedup conflict warning threshold")
    postwrite_parser.add_argument("--allow-conflicts", action="store_true", help="Allow apply even when dedup conflicts are detected")
    postwrite_parser.add_argument("--backup-keep", type=int, default=DEFAULT_BACKUP_KEEP, help="How many literature_sync backups to keep")
    postwrite_parser.add_argument("--backup-max-days", type=int, help="Optional backup retention in days")
    postwrite_parser.add_argument("--matrix-file", default=DEFAULT_LITERATURE_MATRIX_FILE, help="Section-literature matrix file path")
    postwrite_parser.add_argument("--storyline-file", default=STATE_FILES["storyline"], help="Storyline JSON used for section ordering")
    postwrite_parser.add_argument("--no-require-matrix-reindex", action="store_true", help="Allow sync apply without strict matrix reindex gate")
    postwrite_parser.add_argument("--no-rewrite-manuscripts", action="store_true", help="Do not rewrite manuscript [n] citations when syncing literature")
    postwrite_parser.add_argument("--rewrite-docx", action="store_true", help="Also rewrite docx citation markers (md-only by default)")
    postwrite_parser.add_argument("--no-backup", action="store_true", help="Skip literature sync backup (not recommended)")
    postwrite_parser.add_argument("--snapshot", action="store_true", help="Also create a full snapshot")

    # Literature sync command
    sync_lit_parser = subparsers.add_parser("sync-literature", help="Deduplicate literature index and rewrite manuscript citations")
    sync_lit_parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    sync_lit_parser.add_argument("--apply", action="store_true", help="Apply changes to files")
    sync_lit_parser.add_argument("--strict-references", action="store_true", help="Strictly rebuild References/参考文献 to continuous 1..N")
    sync_lit_parser.add_argument("--reference-style", choices=["vancouver", "nature"], default=DEFAULT_REFERENCE_STYLE, help="References rebuild style")
    sync_lit_parser.add_argument("--similarity-threshold", type=float, default=DEFAULT_DEDUP_SIMILARITY, help="Dedup fuzzy-title similarity threshold")
    sync_lit_parser.add_argument("--conflict-threshold", type=float, default=DEFAULT_DEDUP_CONFLICT, help="Dedup conflict warning threshold")
    sync_lit_parser.add_argument("--allow-conflicts", action="store_true", help="Allow apply even when dedup conflicts are detected")
    sync_lit_parser.add_argument("--backup-keep", type=int, default=DEFAULT_BACKUP_KEEP, help="How many literature_sync backups to keep")
    sync_lit_parser.add_argument("--backup-max-days", type=int, help="Optional backup retention in days")
    sync_lit_parser.add_argument("--matrix-file", default=DEFAULT_LITERATURE_MATRIX_FILE, help="Section-literature matrix file path")
    sync_lit_parser.add_argument("--storyline-file", default=STATE_FILES["storyline"], help="Storyline JSON used for section ordering")
    sync_lit_parser.add_argument("--no-require-matrix-reindex", action="store_true", help="Allow sync apply without strict matrix reindex gate")
    sync_lit_parser.add_argument("--no-rewrite-manuscripts", action="store_true", help="Do not rewrite manuscript [n] citations")
    sync_lit_parser.add_argument("--rewrite-docx", action="store_true", help="Also rewrite docx citation markers (md-only by default)")
    sync_lit_parser.add_argument("--no-backup", action="store_true", help="Skip pre-sync backup (not recommended)")

    # Gate check command
    gate_parser = subparsers.add_parser("gate-check", help="Hard gate check before writing/completing")
    gate_parser.add_argument("--section", required=True, help="Section id")
    gate_parser.add_argument("--phase", choices=["prewrite", "complete"], required=True, help="Gate phase")

    # Single-command orchestrator
    cycle_parser = subparsers.add_parser("write-cycle", help="Orchestrate preflight -> load -> (optional) postwrite")
    cycle_parser.add_argument("--section", required=True, help="Section id")
    cycle_parser.add_argument("--include-draft", action="store_true", help="Include current section draft during load")
    cycle_parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET, help="Approx token budget for section-local load")
    cycle_parser.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES, help="Tail lines kept when auto-trimming text")
    cycle_parser.add_argument("--finalize", action="store_true", help="Also execute postwrite at the end")
    cycle_parser.add_argument("--status", default="updated", help="Postwrite status when --finalize is used")
    cycle_parser.add_argument("--summary", default="", help="Postwrite summary when --finalize is used")
    cycle_parser.add_argument("--sync-literature", action="store_true", help="Run postwrite sync-literature when --finalize")
    cycle_parser.add_argument("--sync-apply", action="store_true", help="Apply sync changes when --finalize --sync-literature")
    cycle_parser.add_argument("--strict-references", action="store_true", help="Strictly rebuild References/参考文献")
    cycle_parser.add_argument("--preflight-strict", action="store_true", help="Run preflight in strict mode (default true)")
    cycle_parser.add_argument("--preflight-lenient", action="store_true", help="Override default strict preflight")
    cycle_parser.add_argument("--reference-style", choices=["vancouver", "nature"], default=DEFAULT_REFERENCE_STYLE, help="References rebuild style")
    cycle_parser.add_argument("--similarity-threshold", type=float, default=DEFAULT_DEDUP_SIMILARITY, help="Dedup fuzzy-title similarity threshold")
    cycle_parser.add_argument("--conflict-threshold", type=float, default=DEFAULT_DEDUP_CONFLICT, help="Dedup conflict warning threshold")
    cycle_parser.add_argument("--allow-conflicts", action="store_true", help="Allow apply even when dedup conflicts are detected")
    cycle_parser.add_argument("--backup-keep", type=int, default=DEFAULT_BACKUP_KEEP, help="How many literature_sync backups to keep")
    cycle_parser.add_argument("--backup-max-days", type=int, help="Optional backup retention in days")
    cycle_parser.add_argument("--matrix-file", default=DEFAULT_LITERATURE_MATRIX_FILE, help="Section-literature matrix file path")
    cycle_parser.add_argument("--storyline-file", default=STATE_FILES["storyline"], help="Storyline JSON used for section ordering")
    cycle_parser.add_argument("--no-require-matrix-reindex", action="store_true", help="Allow finalize sync-apply without strict matrix reindex gate")
    cycle_parser.add_argument("--rewrite-docx", action="store_true", help="Also rewrite docx citation markers")
    cycle_parser.add_argument("--no-backup", action="store_true", help="Skip pre-sync backup")

    # Snapshot command
    subparsers.add_parser("snapshot", help="Create a full project backup")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback from snapshot or literature-sync backup")
    rollback_parser.add_argument("--target", choices=["snapshot", "literature_sync"], default="snapshot", help="Rollback target")
    rollback_parser.add_argument("--backup-dir", default="backups", help="Backup root directory")
    rollback_parser.add_argument("--snapshot-dir", help="Specific backup directory to restore")

    # Word count command
    word_count_parser = subparsers.add_parser("word-count", help="Count manuscript words")
    word_count_parser.add_argument("--section", help="Optional section id filter, e.g. 'results_3.1'")
    word_count_parser.add_argument("--include-references", action="store_true", help="Count references section too")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show project writing dashboard")
    stats_parser.add_argument("--section", help="Optional section id filter for word count")
    stats_parser.add_argument("--include-history", action="store_true", help="Include last 10 history records")
    stats_parser.add_argument("--backup-dir", default="backups", help="Backup root directory")

    args = parser.parse_args()

    if args.command == "load":
        files = args.files.split(",") if args.files else None
        load_state(
            target_files=files,
            compact=args.compact,
            section=args.section,
            token_budget=max(1000, args.token_budget),
            tail_lines=max(20, args.tail_lines),
            with_global_history=(args.with_global_history or bool(args.section)),
            include_draft=args.include_draft,
            origin="manual"
        )
    elif args.command == "preflight":
        preflight_validate_state(
            section=args.section,
            strict=args.strict,
            origin="manual",
            matrix_file=args.matrix_file,
            storyline_file=args.storyline_file,
            require_matrix_reindex=(not args.no_require_matrix_reindex)
        )
    elif args.command == "update":
        update_state(args.payload_file)
    elif args.command == "postwrite":
        postwrite_state(
            section=args.section,
            status=args.status,
            summary=args.summary,
            create_snapshot=args.snapshot,
            sync_literature=args.sync_literature,
            rewrite_manuscripts=not args.no_rewrite_manuscripts,
            backup_first=not args.no_backup,
            rewrite_docx=args.rewrite_docx,
            sync_apply=args.sync_apply,
            strict_references=args.strict_references,
            reference_style=args.reference_style,
            similarity_threshold=args.similarity_threshold,
            conflict_threshold=args.conflict_threshold,
            allow_conflicts=args.allow_conflicts,
            backup_keep=max(1, args.backup_keep),
            backup_max_days=args.backup_max_days,
            matrix_file=args.matrix_file,
            storyline_file=args.storyline_file,
            require_matrix_reindex=(not args.no_require_matrix_reindex)
        )
    elif args.command == "sync-literature":
        report = sync_global_literature(
            index_file=STATE_FILES["literature_index"],
            rewrite_manuscripts=not args.no_rewrite_manuscripts,
            backup_first=not args.no_backup,
            rewrite_docx=args.rewrite_docx,
            dry_run=(args.dry_run or not args.apply),
            apply_changes=args.apply,
            strict_references=args.strict_references,
            reference_style=args.reference_style,
            similarity_threshold=args.similarity_threshold,
            conflict_threshold=args.conflict_threshold,
            allow_conflicts=args.allow_conflicts,
            backup_keep=max(1, args.backup_keep),
            backup_max_days=args.backup_max_days,
            matrix_file=args.matrix_file,
            storyline_file=args.storyline_file,
            require_matrix_reindex=(not args.no_require_matrix_reindex)
        )
        print(json.dumps(report, ensure_ascii=False))
    elif args.command == "gate-check":
        gate_check(section=args.section, phase=args.phase)
    elif args.command == "write-cycle":
        write_cycle(
            section=args.section,
            compact=True,
            token_budget=max(1000, args.token_budget),
            tail_lines=max(20, args.tail_lines),
            include_draft=args.include_draft,
            finalize=args.finalize,
            status=args.status,
            summary=args.summary,
            sync_literature=args.sync_literature,
            sync_apply=args.sync_apply,
            strict_references=args.strict_references,
            reference_style=args.reference_style,
            similarity_threshold=args.similarity_threshold,
            conflict_threshold=args.conflict_threshold,
            allow_conflicts=args.allow_conflicts,
            backup_keep=max(1, args.backup_keep),
            backup_max_days=args.backup_max_days,
            preflight_strict=(not args.preflight_lenient),
            rewrite_docx=args.rewrite_docx,
            no_backup=args.no_backup,
            matrix_file=args.matrix_file,
            storyline_file=args.storyline_file,
            require_matrix_reindex=(not args.no_require_matrix_reindex)
        )
    elif args.command == "snapshot":
        backup_project_state()
    elif args.command == "rollback":
        result = rollback_state(
            target=args.target,
            backup_dir=args.backup_dir,
            snapshot_dir=args.snapshot_dir
        )
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "word-count":
        word_count(section=args.section, include_references=args.include_references)
    elif args.command == "stats":
        stats(section=args.section, include_history=args.include_history, backup_dir=args.backup_dir)

if __name__ == "__main__":
    main()

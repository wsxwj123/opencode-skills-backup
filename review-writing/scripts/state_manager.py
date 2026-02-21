import argparse
import difflib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None

# Define state files map for Review Writing Project
STATE_FILES = {
    "project_info": "project_info.md",          # Basic project info (RQ, PICO)
    "storyline": "storyline.md",                # Outline and status
    "progress": "progress.json",                # Quantitative progress (citations count, stage)
    "literature_index": "data/literature_index.json",  # The core database of papers
    "synthesis_matrix": "data/synthesis_matrix.json",  # Matrix for synthesis
    "figure_index": "figures/figure_index.md",  # Figure planning
    "context_memory": "logs/context_memory.md",  # Conversation history snapshot
    "si_database": "data/si_database.json",      # Supplementary info tracking
}


def _normalize_text(text):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(text).lower())


def _section_matches(section, section_list):
    target_raw = str(section).strip()
    target_norm = _normalize_text(section)
    if not target_raw or not isinstance(section_list, list):
        return False
    for item in section_list:
        if not isinstance(item, str):
            continue
        item_s = item.strip()
        # 1. 精确前缀匹配（"2.1" 匹配 "2.1 Title"，但不匹配 "2.10 ..."）
        if item_s.startswith(target_raw + " ") or item_s == target_raw:
            return True
        # 2. 归一化全等匹配（向后兼容）
        if _normalize_text(item_s) == target_norm:
            return True
    return False


def _read_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else {}


def _load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        data = _read_json_file(path)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _extract_storyline_sections(storyline_path):
    p = Path(storyline_path)
    if not p.exists():
        return []
    sections = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(##+)\s+(.*)$", line)
        if not m:
            continue
        title = m.group(2).strip()
        if title:
            sections.append(title)
    return sections


def _coerce_section_id(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("section_id", "id", "name", "title"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _load_storyline_json_sections(path):
    if not path.exists() or path.suffix.lower() != ".json":
        return []
    try:
        data = _read_json_file(path)
    except Exception:
        return []

    sections = data.get("sections") if isinstance(data, dict) else None
    if not isinstance(sections, list):
        return []

    out = []
    for section in sections:
        sid = _coerce_section_id(section)
        if sid:
            out.append(sid)
    return out


def _load_section_order(storyline_path):
    direct = Path(storyline_path)
    candidates = [direct]
    if direct.suffix.lower() == ".md":
        candidates.append(direct.with_suffix(".json"))
    elif direct.suffix.lower() == ".json":
        candidates.append(direct.with_suffix(".md"))

    for candidate in candidates:
        if candidate.suffix.lower() == ".json":
            sections = _load_storyline_json_sections(candidate)
        else:
            sections = _extract_storyline_sections(str(candidate))
        if sections:
            return sections
    return []


def _is_present(value):
    return value not in (None, "", [])


DEFAULT_DEDUP_SIMILARITY = 0.93
DEFAULT_DEDUP_CONFLICT = 0.85


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


def normalize_pmid(pmid):
    if not pmid:
        return ""
    return str(pmid).strip()


def title_similarity(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _resolve_matrix_sources(matrix_path, storyline_path):
    explicit = Path(matrix_path) if matrix_path else None
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    else:
        candidates.extend(
            [
                Path("data/synthesis_matrix.json"),
                Path("data/literature_matrix.json"),
            ]
        )

    writable_path = None
    matrix_rows = None
    matrix_source = None

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = _read_json_file(candidate)
        except Exception:
            continue
        if isinstance(payload, list):
            matrix_rows = payload
            matrix_source = str(candidate)
            if explicit is not None:
                writable_path = candidate
            else:
                # Use synthesis_matrix.json as the canonical writable source.
                writable_path = Path("data/synthesis_matrix.json")
            break

    storyline_json = None
    p = Path(storyline_path)
    if p.suffix.lower() == ".json":
        storyline_json = p
    else:
        alt = p.with_suffix(".json")
        if alt.exists():
            storyline_json = alt

    if storyline_json is not None and storyline_json.exists():
        try:
            payload = _read_json_file(storyline_json)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            for key in ("literature_matrix", "synthesis_matrix", "matrix"):
                embedded = payload.get(key)
                if isinstance(embedded, list):
                    if matrix_rows is None:
                        matrix_rows = embedded
                        matrix_source = f"{storyline_json}#{key}"
                    break

    return matrix_rows, writable_path, matrix_source


def _merge_canonical_item(target, source):
    for key, value in source.items():
        if key in ("global_id", "citation_number"):
            continue
        if key not in target or not _is_present(target.get(key)):
            target[key] = value
            continue
        if key in ("related_sections", "sections") and isinstance(target.get(key), list) and isinstance(value, list):
            merged = []
            seen = set()
            for item in target[key] + value:
                marker = _normalize_text(item)
                if not marker or marker in seen:
                    continue
                seen.add(marker)
                merged.append(item)
            target[key] = merged


def _build_canonical_records(
    index_rows,
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT,
):
    canonical = []
    old_to_canonical = {}
    next_virtual_id = 10**9

    seen_doi = {}
    seen_pmid = {}
    seen_meta = {}
    seen_title = {}
    canonical_title_by_idx = {}
    duplicates = 0
    conflicts = []
    strategy_counts = {
        "doi": 0,
        "pmid": 0,
        "meta": 0,
        "exact_title": 0,
        "fuzzy_title": 0,
    }

    for pos, item in enumerate(index_rows):
        if not isinstance(item, dict):
            continue

        gid = item.get("global_id")
        old_gid = gid if isinstance(gid, int) and gid > 0 else None
        if old_gid is None:
            old_gid = next_virtual_id + pos

        doi_key = normalize_doi(item.get("doi"))
        pmid_key = normalize_pmid(item.get("pmid"))
        title_key = normalize_title(item.get("title"))
        author_key = normalize_author(item.get("authors") or item.get("author"))
        year_key = str(item.get("year") or "").strip()
        journal_key = normalize_journal(item.get("journal"))
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
                    "old_gid": old_gid,
                    "candidate_idx": best_idx,
                    "similarity": round(best_score, 4),
                    "title": item.get("title", ""),
                })

        if canonical_idx is not None:
            _merge_canonical_item(canonical[canonical_idx], item)
            old_to_canonical[old_gid] = canonical_idx
            duplicates += 1
            continue

        new_item = dict(item)
        canonical.append(new_item)
        idx = len(canonical) - 1
        old_to_canonical[old_gid] = idx
        if doi_key:
            seen_doi[doi_key] = idx
        if pmid_key:
            seen_pmid[pmid_key] = idx
        if title_key:
            seen_title[title_key] = idx
            canonical_title_by_idx[idx] = title_key
        if meta_key:
            seen_meta[meta_key] = idx

    return canonical, old_to_canonical, {
        "duplicate_count": duplicates,
        "conflicts": conflicts,
        "strategy_counts": strategy_counts,
        "total_before": len(index_rows),
        "total_after": len(canonical),
    }


def _split_citation_items(body):
    return [token.strip() for token in re.split(r"\s*[,;]\s*", body.strip()) if token.strip()]


def _expand_citation_token(token):
    if re.fullmatch(r"\d+", token):
        return [int(token)]
    m = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", token)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2))
    step = 1 if start <= end else -1
    return list(range(start, end + step, step))


def _compress_citation_numbers(numbers):
    if not numbers:
        return ""
    ordered = sorted(set(numbers))
    spans = []
    s = ordered[0]
    e = ordered[0]
    for num in ordered[1:]:
        if num == e + 1:
            e = num
            continue
        spans.append((s, e))
        s = num
        e = num
    spans.append((s, e))

    parts = []
    for start, end in spans:
        if start == end:
            parts.append(str(start))
        else:
            parts.append(f"{start}-{end}")
    return ",".join(parts)


def _remap_citation_brackets(text, old_to_new, strict, unresolved):
    pattern = re.compile(r"\[((?:\s*\d+(?:\s*[-–]\s*\d+)?\s*)(?:[,;]\s*\d+(?:\s*[-–]\s*\d+)?\s*)*)\]")
    changed = 0

    def repl(match):
        nonlocal changed
        body = match.group(1)
        tokens = _split_citation_items(body)
        nums = []
        for token in tokens:
            expanded = _expand_citation_token(token)
            if expanded is None:
                return match.group(0)
            nums.extend(expanded)

        mapped = []
        for number in nums:
            if number not in old_to_new:
                unresolved.add(number)
                if strict:
                    return match.group(0)
                mapped.append(number)
            else:
                mapped.append(old_to_new[number])

        normalized = _compress_citation_numbers(mapped)
        replacement = f"[{normalized}]"
        if replacement != match.group(0):
            changed += 1
        return replacement

    return pattern.sub(repl, text), changed


def _remap_reference_section(text, old_to_new, strict, unresolved):
    lines = text.splitlines(keepends=True)
    in_refs = False
    changed = 0
    head_re = re.compile(r"^\s*##\s+references\b", re.IGNORECASE)
    next_head_re = re.compile(r"^\s*##\s+")
    ref_num_re = re.compile(r"^(\s*)(\d+)([.)])(\s+.*)$")

    out = []
    for line in lines:
        if head_re.match(line):
            in_refs = True
            out.append(line)
            continue
        if in_refs and next_head_re.match(line):
            in_refs = False

        if in_refs:
            m = ref_num_re.match(line)
            if m:
                old = int(m.group(2))
                if old not in old_to_new:
                    unresolved.add(old)
                    if strict:
                        out.append(line)
                        continue
                    new_num = old
                else:
                    new_num = old_to_new[old]
                new_line = f"{m.group(1)}{new_num}{m.group(3)}{m.group(4)}"
                if new_line != line:
                    changed += 1
                out.append(new_line)
                continue

        out.append(line)

    return "".join(out), changed


def _atomic_write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _find_section_draft(section):
    if not section:
        return None
    drafts_dir = Path("drafts")
    if not drafts_dir.exists():
        return None

    section_norm = _normalize_text(section)
    for path in drafts_dir.glob("**/*.md"):
        if section_norm and section_norm in _normalize_text(path.stem):
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as e:
                content = f"<Error reading {path}: {e}>"
            return {"file": str(path), "content": content}
    return None


def load_state(section=None, fallback_recent=False, minimal=False):
    """Reads state files and returns a consolidated JSON object to stdout."""
    combined_state = {}

    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    combined_state[key] = _read_json_file(filename)
                else:
                    with open(filename, "r", encoding="utf-8") as f:
                        combined_state[key] = f.read()
            except Exception as e:
                combined_state[key] = f"<Error loading {filename}: {e}>"
        else:
            combined_state[key] = None

    # Backward compatibility: if canonical synthesis matrix is missing, use legacy literature_matrix.
    if combined_state.get("synthesis_matrix") is None and os.path.exists("data/literature_matrix.json"):
        try:
            legacy = _read_json_file("data/literature_matrix.json")
            if isinstance(legacy, list):
                combined_state["synthesis_matrix"] = legacy
        except Exception:
            pass

    if section:
        lit_data = combined_state.get("literature_index")
        if isinstance(lit_data, list):
            filtered_lit = []
            for item in lit_data:
                if "global_id" not in item:
                    item["global_id"] = None

                related_sections = item.get("related_sections")
                legacy_sections = item.get("sections")

                if _section_matches(section, related_sections):
                    filtered_lit.append(item)
                elif _section_matches(section, legacy_sections):
                    filtered_lit.append(item)

            if fallback_recent and not filtered_lit and lit_data:
                filtered_lit = lit_data[-20:]

            combined_state["literature_index"] = filtered_lit

            relevant_ids = {
                item.get("global_id")
                for item in filtered_lit
                if item.get("global_id") is not None
            }
            matrix_data = combined_state.get("synthesis_matrix")
            if isinstance(matrix_data, list):
                filtered_rows = []
                for row in matrix_data:
                    if row.get("global_id") not in relevant_ids:
                        continue
                    row_section = row.get("section_id")
                    # If section_id exists in row, enforce section match after normalization.
                    if row_section is not None and _normalize_text(row_section) != _normalize_text(section):
                        continue
                    filtered_rows.append(row)
                combined_state["synthesis_matrix"] = filtered_rows

    if minimal:
        minimal_state = {
            "progress": combined_state.get("progress"),
            "literature_index": combined_state.get("literature_index"),
            "synthesis_matrix": combined_state.get("synthesis_matrix"),
            "section_draft": _find_section_draft(section),
        }
        print(json.dumps(minimal_state, indent=2, ensure_ascii=False))
        return

    print(json.dumps(combined_state, indent=2, ensure_ascii=False))


def rotate_context_memory_versions():
    """Handles versioning for context_memory.md (v-1, v-2)."""
    base_file = "logs/context_memory.md"
    v1_file = "logs/context_memory_v-1.md"
    v2_file = "logs/context_memory_v-2.md"

    os.makedirs(os.path.dirname(base_file), exist_ok=True)

    if os.path.exists(v1_file):
        shutil.copy2(v1_file, v2_file)
    if os.path.exists(base_file):
        shutil.copy2(base_file, v1_file)


def _extract_memory_markers(lines):
    markers = {
        "decisions": [],
        "open_questions": [],
        "next_actions": [],
        "risks": [],
    }
    patterns = {
        "decisions": re.compile(r"\b(decision|decided|结论)\b", re.IGNORECASE),
        "open_questions": re.compile(r"\b(question|unknown|待确认|待定)\b", re.IGNORECASE),
        "next_actions": re.compile(r"\b(todo|next|action|下一步)\b", re.IGNORECASE),
        "risks": re.compile(r"\b(risk|blocker|阻塞|风险)\b", re.IGNORECASE),
    }

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        for key, pattern in patterns.items():
            if pattern.search(line):
                markers[key].append(line)

    for key in markers:
        markers[key] = markers[key][-20:]
    return markers


def compact_memory():
    """Compacts context_memory.md and writes a structured memory summary."""
    memory_file = STATE_FILES["context_memory"]

    if not os.path.exists(memory_file):
        print("Context memory file not found.")
        return

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        max_lines = 100
        keep_recent = 20

        if len(lines) <= max_lines:
            print("Memory is within limits. No compaction needed.")
            return

        header = lines[:5]
        recent = lines[-keep_recent:]

        rotate_context_memory_versions()

        with open(memory_file, "w", encoding="utf-8") as f:
            f.writelines(header)
            f.write(f"\nArchived Context: [{len(lines) - 5 - keep_recent} lines hidden]\n\n")
            f.writelines(recent)

        summary = {
            "updated_at": datetime.now().isoformat(),
            "line_count_before": len(lines),
            "line_count_after": len(header) + 1 + len(recent),
            "markers": _extract_memory_markers(lines),
        }
        os.makedirs("logs", exist_ok=True)
        with open("logs/context_memory_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(
            f"Compacted memory from {len(lines)} lines to {len(header) + 1 + len(recent)} lines."
        )

    except Exception as e:
        print(f"Error compacting memory: {e}")


def _paper_identity(item):
    doi = str(item.get("doi", "")).strip().lower()
    pmid = str(item.get("pmid", "")).strip()
    title = str(item.get("title", "")).strip().lower()
    if doi:
        return f"doi:{doi}"
    if pmid:
        return f"pmid:{pmid}"
    if title:
        return f"title:{title}"
    return None


def _merge_literature(existing, incoming):
    existing = [x for x in existing if isinstance(x, dict)]
    incoming = [x for x in incoming if isinstance(x, dict)]

    by_id = {}
    by_identity = {}
    max_id = 0

    for item in existing:
        gid = item.get("global_id")
        if isinstance(gid, int) and gid > 0:
            by_id[gid] = item
            max_id = max(max_id, gid)
        ident = _paper_identity(item)
        if ident:
            by_identity[ident] = item

    for item in incoming:
        gid = item.get("global_id")
        ident = _paper_identity(item)

        target = None
        if isinstance(gid, int) and gid > 0 and gid in by_id:
            target = by_id[gid]
        elif ident and ident in by_identity:
            target = by_identity[ident]

        if target is not None:
            target.update(item)
            continue

        if not (isinstance(gid, int) and gid > 0 and gid not in by_id):
            max_id += 1
            item["global_id"] = max_id
        else:
            max_id = max(max_id, gid)

        by_id[item["global_id"]] = item
        ident = _paper_identity(item)
        if ident:
            by_identity[ident] = item

    return [by_id[k] for k in sorted(by_id.keys())]


def _merge_matrix(existing, incoming):
    existing = [x for x in existing if isinstance(x, dict)]
    incoming = [x for x in incoming if isinstance(x, dict)]

    by_key = {}
    no_id = []

    for row in existing:
        gid = row.get("global_id")
        section = row.get("section_id")
        if isinstance(gid, int) and gid > 0:
            by_key[(gid, section)] = row
        else:
            no_id.append(row)

    for row in incoming:
        gid = row.get("global_id")
        section = row.get("section_id")
        if isinstance(gid, int) and gid > 0:
            key = (gid, section)
            if key in by_key:
                by_key[key].update(row)
            else:
                by_key[key] = row
        else:
            no_id.append(row)

    ordered = sorted(by_key.keys(), key=lambda x: (x[1] if x[1] is not None else "", x[0]))
    return [by_key[k] for k in ordered] + no_id


def reindex_literature_by_section(
    storyline_path="storyline.md",
    index_path="data/literature_index.json",
    matrix_path=None,
    drafts_dir="drafts",
    sync_apply=False,
    similarity_threshold=DEFAULT_DEDUP_SIMILARITY,
    conflict_threshold=DEFAULT_DEDUP_CONFLICT,
    allow_conflicts=False,
):
    if not os.path.exists(index_path):
        raise SystemExit(f"Error: Index file not found: {index_path}")

    sections = _load_section_order(storyline_path)
    section_rank = {_normalize_text(name): i for i, name in enumerate(sections)}

    with _state_lock():
        index_rows = _read_json_file(index_path)
        if not isinstance(index_rows, list):
            raise SystemExit("literature_index must be a list")

        canonical_rows, old_to_canonical, dedup_stats = _build_canonical_records(
            index_rows,
            similarity_threshold=similarity_threshold,
            conflict_threshold=conflict_threshold,
        )
        matrix_rows, writable_matrix_path, matrix_source = _resolve_matrix_sources(matrix_path, storyline_path)

        if dedup_stats["conflicts"] and sync_apply and not allow_conflicts:
            for c in dedup_stats["conflicts"]:
                print(f"  [CONFLICT] gid={c['old_gid']} ~{c['similarity']} vs idx={c['candidate_idx']}: {c['title']}")
            print(f"[GATE] --sync-apply blocked: {len(dedup_stats['conflicts'])} dedup conflicts. Use --allow-conflicts to override.")
            raise SystemExit(2)

        if sync_apply and matrix_rows is None:
            print("[GATE] --sync-apply requires a matrix source (data/literature_matrix.json or data/synthesis_matrix.json).")
            raise SystemExit(2)
        if sync_apply and writable_matrix_path is None:
            print("[GATE] --sync-apply requires a writable matrix file path.")
            raise SystemExit(2)

        ordered_canonical = []
        seen_canonical = set()
        section_first_seen = {}
        mapping_failures = []
        remapped_rows = 0
        remapped_matrix = None

        matrix_order_ids = []
        if isinstance(matrix_rows, list):
            remapped_matrix = []
            for idx, row in enumerate(matrix_rows):
                if not isinstance(row, dict):
                    remapped_matrix.append(row)
                    continue
                new_row = dict(row)
                remapped_matrix.append(new_row)

                section_id = str(new_row.get("section_id", "unassigned"))
                section_key = _normalize_text(section_id)
                if section_key not in section_first_seen:
                    section_first_seen[section_key] = len(section_first_seen)

                gid = new_row.get("global_id")
                if not (isinstance(gid, int) and gid > 0):
                    continue
                if gid not in old_to_canonical:
                    mapping_failures.append({"source": "matrix", "global_id": gid, "row_index": idx, "section_id": section_id})
                    continue

                canonical_idx = old_to_canonical[gid]
                if canonical_idx not in seen_canonical:
                    seen_canonical.add(canonical_idx)
                    ordered_canonical.append(
                        (
                            section_rank.get(section_key, len(section_rank) + section_first_seen[section_key]),
                            idx,
                            canonical_idx,
                        )
                    )

            ordered_canonical.sort(key=lambda x: (x[0], x[1]))
            matrix_order_ids = [x[2] for x in ordered_canonical]
        else:
            matrix_order_ids = []

        fallback_order = []
        for idx, item in enumerate(canonical_rows):
            if idx in seen_canonical:
                continue
            related = item.get("related_sections")
            related = related if isinstance(related, list) else []
            hits = []
            for sec in related:
                sec_key = _normalize_text(sec)
                if sec_key in section_rank:
                    hits.append(section_rank[sec_key])
            fallback_rank = min(hits) if hits else len(section_rank) + idx
            fallback_order.append((fallback_rank, idx))

        fallback_order.sort(key=lambda x: (x[0], x[1]))
        final_canonical_order = matrix_order_ids + [idx for _, idx in fallback_order]

        canonical_to_new = {cid: i for i, cid in enumerate(final_canonical_order, start=1)}
        old_to_new = {}
        for old_gid, cid in old_to_canonical.items():
            if old_gid >= 10**9:
                continue
            old_to_new[old_gid] = canonical_to_new[cid]

        if remapped_matrix is not None:
            for row in remapped_matrix:
                if not isinstance(row, dict):
                    continue
                gid = row.get("global_id")
                if isinstance(gid, int) and gid > 0 and gid in old_to_new:
                    new_gid = old_to_new[gid]
                    if new_gid != gid:
                        remapped_rows += 1
                    row["global_id"] = new_gid

        reindexed = []
        for cid in final_canonical_order:
            entry = dict(canonical_rows[cid])
            entry["global_id"] = canonical_to_new[cid]
            reindexed.append(entry)

        draft_updates = {}
        unresolved_ids = set()
        remapped_citations = 0
        remapped_ref_lines = 0
        ddir = Path(drafts_dir)
        if ddir.exists():
            for md in sorted(ddir.glob("**/*.md")):
                try:
                    text = md.read_text(encoding="utf-8")
                except Exception:
                    continue
                text1, changed_c = _remap_citation_brackets(text, old_to_new, sync_apply, unresolved_ids)
                text2, changed_r = _remap_reference_section(text1, old_to_new, sync_apply, unresolved_ids)
                if text2 != text:
                    draft_updates[md] = text2
                remapped_citations += changed_c
                remapped_ref_lines += changed_r

        if mapping_failures and sync_apply:
            print(f"[GATE] --sync-apply blocked: {len(mapping_failures)} matrix rows reference unknown global_id.")
            raise SystemExit(2)
        if unresolved_ids and sync_apply:
            unresolved_text = ", ".join(str(x) for x in sorted(unresolved_ids)[:20])
            print(f"[GATE] --sync-apply blocked: unresolved citation IDs in drafts: {unresolved_text}")
            raise SystemExit(2)

        _atomic_write_text(index_path, json.dumps(reindexed, indent=2, ensure_ascii=False))
        if writable_matrix_path is not None and remapped_matrix is not None:
            _atomic_write_text(writable_matrix_path, json.dumps(remapped_matrix, indent=2, ensure_ascii=False))
        for md, content in draft_updates.items():
            _atomic_write_text(md, content)

    dedup_count = dedup_stats["duplicate_count"]
    matrix_label = matrix_source if matrix_source else "none"
    strategy_info = ", ".join(f"{k}={v}" for k, v in dedup_stats["strategy_counts"].items() if v > 0)
    print(
        f"Reindex complete: index={len(reindexed)} (dedup_removed={dedup_count}{', ' + strategy_info if strategy_info else ''}), "
        f"matrix_source={matrix_label}, matrix_rows_remapped={remapped_rows}, "
        f"draft_citation_groups_remapped={remapped_citations}, references_lines_remapped={remapped_ref_lines}"
    )


@contextmanager
def _state_lock(timeout=20):
    lock_path = Path("logs") / ".state_manager.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    start = time.time()
    acquired = False
    try:
        while True:
            try:
                if fcntl is None:
                    acquired = True
                    break
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.time() - start > timeout:
                    raise TimeoutError(f"state lock timeout after {timeout}s: {lock_path}")
                time.sleep(0.05)
        yield
    finally:
        if acquired and fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
        os.close(fd)


def update_state(payload_path, merge=True):
    """Updates state files based on a JSON payload file."""
    if not os.path.exists(payload_path):
        print(f"Error: Payload file '{payload_path}' not found.")
        sys.exit(1)

    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in payload file: {e}")
        sys.exit(1)

    updated_files = []

    with _state_lock():
        for key, content in payload.items():
            if key not in STATE_FILES:
                print(f"Warning: Unknown key '{key}' in payload. Skipping.")
                continue

            filename = STATE_FILES[key]

            if merge and key == "literature_index" and isinstance(content, list):
                content = _merge_literature(_load_json_list(filename), content)
            elif merge and key == "synthesis_matrix" and isinstance(content, list):
                content = _merge_matrix(_load_json_list(filename), content)
            elif key == "literature_index" and isinstance(content, list):
                current_max_id = 0
                if os.path.exists(filename):
                    try:
                        existing_data = _read_json_file(filename)
                        if isinstance(existing_data, list):
                            for item in existing_data:
                                gid = item.get("global_id")
                                if isinstance(gid, int) and gid > current_max_id:
                                    current_max_id = gid
                    except Exception as e:
                        print(f"Warning reading existing literature index for max_id: {e}")

                for item in content:
                    gid = item.get("global_id")
                    if (
                        ("global_id" not in item)
                        or (gid is None)
                        or (not isinstance(gid, int))
                        or (gid <= 0)
                    ):
                        current_max_id += 1
                        item["global_id"] = current_max_id
                    elif gid > current_max_id:
                        current_max_id = gid

            try:
                os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)

                if key == "context_memory":
                    if os.path.exists(filename):
                        rotate_context_memory_versions()
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(str(content))
                elif filename.endswith(".json"):
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2, ensure_ascii=False)
                else:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(str(content))

                updated_files.append(filename)

            except Exception as e:
                print(f"Error writing to {filename}: {e}")

    print(f"Successfully updated: {', '.join(updated_files)}")

    try:
        os.remove(payload_path)
    except Exception:
        pass


def snapshot_state(output_path=None):
    """Write a point-in-time snapshot of all state files to JSON."""
    snapshot = {}
    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    snapshot[key] = _read_json_file(filename)
                else:
                    with open(filename, "r", encoding="utf-8") as f:
                        snapshot[key] = f.read()
            except Exception as e:
                snapshot[key] = f"<Error loading {filename}: {e}>"
        else:
            snapshot[key] = None

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("logs", "snapshots", f"state_snapshot_{ts}.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"Snapshot written: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Manage state files for Review Writing Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser("load", help="Load and print all state files as JSON")
    load_parser.add_argument("--section", help="Optional: Section name to filter relevant literature", default=None)
    load_parser.add_argument(
        "--fallback-recent",
        action="store_true",
        help="Fallback to last 20 literature entries if section filter is empty (legacy behavior)",
    )
    load_parser.add_argument(
        "--minimal",
        action="store_true",
        help="Return only progress, section-filtered literature/matrix, and matching section draft",
    )
    load_parser.add_argument(
        "--allow-unscoped-minimal",
        action="store_true",
        help="Allow --minimal without --section (disabled by default to prevent oversized context loads).",
    )

    update_parser = subparsers.add_parser("update", help="Update state files from a payload")
    update_parser.add_argument(
        "payload_file",
        nargs="?",
        default="state_update_payload.json",
        help="Path to the JSON file containing updates (default: state_update_payload.json)",
    )
    update_parser.add_argument(
        "--replace",
        action="store_true",
        help="Disable merge mode and replace file content from payload.",
    )

    subparsers.add_parser("compact", help="Compact the context memory file if too large")

    snapshot_parser = subparsers.add_parser("snapshot", help="Write a full state snapshot JSON")
    snapshot_parser.add_argument(
        "--out",
        default=None,
        help="Optional snapshot output path (default: logs/snapshots/state_snapshot_<timestamp>.json)",
    )

    reindex_parser = subparsers.add_parser(
        "reindex",
        help="Canonical-deduplicate and reindex literature by section/matrix order, then remap matrix+draft citations",
    )
    reindex_parser.add_argument("--storyline", default="storyline.md", help="Storyline markdown path")
    reindex_parser.add_argument("--index", default="data/literature_index.json", help="Literature index path")
    reindex_parser.add_argument(
        "--matrix",
        default=None,
        help="Optional matrix path (auto-detects data/synthesis_matrix.json then legacy data/literature_matrix.json)",
    )
    reindex_parser.add_argument("--drafts-dir", default="drafts", help="Draft directory for citation remap")
    reindex_parser.add_argument(
        "--sync-apply",
        action="store_true",
        help="Hard gate mode: block on missing matrix or unresolved mappings (exit 2).",
    )
    reindex_parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_DEDUP_SIMILARITY,
        help=f"Fuzzy title match threshold (default: {DEFAULT_DEDUP_SIMILARITY})",
    )
    reindex_parser.add_argument(
        "--conflict-threshold",
        type=float,
        default=DEFAULT_DEDUP_CONFLICT,
        help=f"Conflict detection threshold (default: {DEFAULT_DEDUP_CONFLICT})",
    )
    reindex_parser.add_argument(
        "--allow-conflicts",
        action="store_true",
        help="Allow apply even when dedup conflicts are detected",
    )

    args = parser.parse_args()

    if args.command == "load":
        if args.minimal and not args.section and not args.allow_unscoped_minimal:
            print("[GATE] --minimal requires --section to avoid oversized context loads.")
            sys.exit(2)
        load_state(section=args.section, fallback_recent=args.fallback_recent, minimal=args.minimal)
    elif args.command == "update":
        if not os.path.exists(args.payload_file):
            print(
                f"Error: Payload file '{args.payload_file}' not found. "
                "Create this file or pass an explicit path."
            )
            sys.exit(1)
        update_state(args.payload_file, merge=not args.replace)
    elif args.command == "compact":
        compact_memory()
    elif args.command == "snapshot":
        snapshot_state(output_path=args.out)
    elif args.command == "reindex":
        reindex_literature_by_section(
            storyline_path=args.storyline,
            index_path=args.index,
            matrix_path=args.matrix,
            drafts_dir=args.drafts_dir,
            sync_apply=args.sync_apply,
            similarity_threshold=args.similarity_threshold,
            conflict_threshold=args.conflict_threshold,
            allow_conflicts=args.allow_conflicts,
        )


if __name__ == "__main__":
    main()

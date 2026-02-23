#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci2Doc 状态管理器

目标：
1) 防失忆：统一读写全局状态与章节记忆
2) 防爆 token：章节级加载 + 预算裁剪
3) 防误完成：prewrite/complete 双门禁
4) 可回滚：快照与恢复
"""

import argparse
import copy
import glob
import hashlib
import io
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager, redirect_stdout
from datetime import datetime

try:
    from thesis_profile import load_profile, save_profile, parse_chapter_target_spec
except Exception:  # pragma: no cover
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from thesis_profile import load_profile, save_profile, parse_chapter_target_spec

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

LOCK_BACKEND = "fcntl" if fcntl is not None else "lockfile_fallback"

TOKEN_CHAR_RATIO = 4
DEFAULT_TOKEN_BUDGET = 6000
DEFAULT_TAIL_LINES = 80
DEFAULT_BACKUP_KEEP = 20

REQUIRED_STATE_FILES = {
    "project_state": "project_state.json",
    "thesis_profile": "thesis_profile.json",
}

OPTIONAL_STATE_FILES = {
    "context_memory": "context_memory.md",
    "chapter_index": "chapter_index.json",
    "history_log": "history_log.json",
    "literature_index": "literature_index.json",
    "figures_index": "figures_index.json",
}

RESTORE_MANAGED_FILES = tuple(
    list(REQUIRED_STATE_FILES.values())
    + list(OPTIONAL_STATE_FILES.values())
    + ["context_memory_v-1.md", "context_memory_v-2.md"]
)
RESTORE_MANAGED_DIRS = (".state", "02_分章节文档", "03_合并文档", "04_图表文件", "chapter_memory")

GATE_STATE_DIR = ".state"
GATE_STATE_FILE = os.path.join(GATE_STATE_DIR, "write_gate.json")
LOAD_CACHE_FILE = os.path.join(GATE_STATE_DIR, "load_cache.json")


# ---------------------------------------------------------------------------
# Lazy-loaded abbreviation processing (avoids circular import)
# ---------------------------------------------------------------------------

def _get_abbr_process():
    """Lazily import abbreviation_registry to avoid circular dependency."""
    try:
        from abbreviation_registry import process_section_markdown
        return process_section_markdown
    except ImportError:
        _sd = os.path.dirname(os.path.abspath(__file__))
        if _sd not in sys.path:
            sys.path.insert(0, _sd)
        try:
            from abbreviation_registry import process_section_markdown
            return process_section_markdown
        except ImportError:
            return None


def _postwrite_abbreviation_process(project_root, chapter):
    """
    Post-write hook: extract, register, and strip redundant abbreviation
    expansions from all markdown files in the given chapter directory.

    Returns a report dict or None if abbreviation_registry is unavailable.
    """
    process_fn = _get_abbr_process()
    if process_fn is None:
        return None

    # Find chapter directory (support both layouts)
    chapter_str = str(int(chapter)) if str(chapter).isdigit() else str(chapter)
    candidates = [
        os.path.join(project_root, "atomic_md", f"第{chapter_str}章"),
        os.path.join(project_root, "02_分章节文档", f"第{chapter_str}章"),
    ]
    chapter_dir = None
    for c in candidates:
        if os.path.isdir(c):
            chapter_dir = c
            break

    if chapter_dir is None:
        return {"skipped": True, "reason": "chapter_dir_not_found"}

    report = {"processed_files": [], "new_abbreviations": 0, "stripped_count": 0}
    md_files = sorted(glob.glob(os.path.join(chapter_dir, "*.md")))
    for md_path in md_files:
        basename = os.path.basename(md_path)
        # Extract section number from filename like "2.1_引言.md"
        sec_match = re.match(r"(\d+\.\d+)", basename)
        section = sec_match.group(1) if sec_match else basename

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            cleaned, result = process_fn(
                project_root=project_root,
                md_content=md_content,
                chapter=chapter_str,
                section=section,
            )

            # Write back only if content changed
            if cleaned != md_content:
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)

            report["processed_files"].append(basename)
            reg = result.get("registration", {})
            strip = result.get("stripping", {})
            report["new_abbreviations"] += reg.get("registered_count", 0)
            report["stripped_count"] += strip.get("stripped_count", 0)
        except Exception:
            pass  # Non-fatal: abbreviation processing should not block postwrite

    return report


class StateFileError(Exception):
    def __init__(self, path, reason, detail):
        super().__init__(f"{reason}: {path}")
        self.path = path
        self.reason = reason
        self.detail = detail


def ensure_state_dir(project_root):
    os.makedirs(os.path.join(project_root, GATE_STATE_DIR), exist_ok=True)


def resolve_path(project_root, rel_path):
    if os.path.isabs(rel_path):
        return rel_path
    return os.path.join(project_root, rel_path)


def lock_path(path):
    return f"{path}.lock"


@contextmanager
def file_lock(path, exclusive=True):
    lock_file = lock_path(path)
    os.makedirs(os.path.dirname(lock_file) or ".", exist_ok=True)
    if fcntl is not None:
        with open(lock_file, "a+", encoding="utf-8") as handle:
            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(handle.fileno(), mode)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return

    # Cross-platform fallback when fcntl is unavailable.
    fd = None
    start = time.monotonic()
    timeout_sec = 10.0
    poll_sec = 0.05
    while True:
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.monotonic() - start >= timeout_sec:
                raise StateFileError(
                    path=lock_file,
                    reason="lock_timeout",
                    detail=f"timed out waiting for lock after {timeout_sec:.1f}s",
                )
            time.sleep(poll_sec)
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.remove(lock_file)
        except OSError:
            pass


def safe_json_load(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return copy.deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except OSError as e:
        raise StateFileError(path=path, reason="read_failed", detail=str(e)) from e
    if not raw:
        return copy.deepcopy(default)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise StateFileError(path=path, reason="invalid_json", detail=str(e)) from e


def safe_json_dump(path, payload):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_state_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def safe_text_dump(path, text):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_state_", suffix=".txt", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def update_json_locked(path, default, mutate_fn):
    with file_lock(path, exclusive=True):
        current = safe_json_load(path, default=default)
        updated = mutate_fn(current)
        if updated is None:
            updated = current
        safe_json_dump(path, updated)
        return updated


def count_index_entries(payload):
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return len(payload.keys())
    return 0


def extract_word_stats(result):
    body = 0
    review = 0
    total = 0
    if isinstance(result, dict):
        body = (
            result.get("body_text", {}).get("chinese_chars")
            if isinstance(result.get("body_text"), dict)
            else result.get("chinese_chars", 0)
        )
        review = (
            result.get("review", {}).get("chinese_chars")
            if isinstance(result.get("review"), dict)
            else result.get("review_chinese_chars", 0)
        )
        total = (
            result.get("total", {}).get("chinese_chars")
            if isinstance(result.get("total"), dict)
            else result.get("total_chinese_chars", 0)
        )
    return int(body or 0), int(review or 0), int(total or 0)


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


def approx_tokens(value):
    if value is None:
        return 0
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False)
    return max(1, len(text) // TOKEN_CHAR_RATIO)


def tail_text(value, lines=80):
    if not isinstance(value, str):
        return value
    parts = value.splitlines()
    if len(parts) <= lines:
        return value
    return "\n".join(parts[-lines:])


def chapter_terms(chapter):
    chapter = str(chapter).strip().lower()
    out = {chapter}
    if chapter.isdigit():
        out.add(f"第{chapter}章")
        out.add(f"chapter{chapter}")
        out.add(f"chapter {chapter}")
    return {x for x in out if x}


def contains_term(node, terms):
    if node is None:
        return False
    if isinstance(node, str):
        text = node.lower()
        return any(term in text for term in terms)
    if isinstance(node, dict):
        return any(contains_term(v, terms) for v in node.values())
    if isinstance(node, list):
        return any(contains_term(v, terms) for v in node)
    return contains_term(str(node), terms)


def read_gate_state(project_root):
    gate_file = resolve_path(project_root, GATE_STATE_FILE)
    return safe_json_load(gate_file, default={})


def update_gate_state(project_root, **updates):
    ensure_state_dir(project_root)
    gate_file = resolve_path(project_root, GATE_STATE_FILE)

    def mutate(state):
        if not isinstance(state, dict):
            state = {}
        state.update(updates)
        return state

    return update_json_locked(gate_file, {}, mutate)


def start_cycle(project_root, chapter):
    return update_gate_state(
        project_root,
        chapter=str(chapter),
        cycle_started_ts=now_ts(),
        require_cycle=True,
        preflight_ok=False,
        prewrite_ready=False,
        completion_ready=False,
        last_preflight_origin=None,
        last_load_origin=None,
    )


def validate_gate(project_root, chapter, phase):
    state = read_gate_state(project_root)
    chapter = str(chapter)
    if not isinstance(state, dict) or not state:
        return (
            False,
            "gate state missing: run 'init' then 'write-cycle --chapter <n>' before gate-check",
        )
    if state.get("chapter") != chapter:
        got = state.get("chapter")
        if got is None:
            return (
                False,
                "gate chapter not set: run 'write-cycle --chapter <n>' to initialize gate state",
            )
        return False, f"gate chapter mismatch: expected={chapter}, got={got}"

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
            return False, "completion gate not ready: run postwrite/finalize first"
        return True, "ok"

    return False, f"unknown phase: {phase}"


def gate_check(project_root, chapter, phase):
    ok, reason = validate_gate(project_root, chapter, phase)
    payload = {
        "chapter": str(chapter),
        "phase": phase,
        "ok": ok,
        "reason": reason,
        "gate_file": resolve_path(project_root, GATE_STATE_FILE),
        "state": read_gate_state(project_root),
    }
    print(json.dumps(payload, ensure_ascii=False))
    if not ok:
        sys.exit(2)


def parse_json_lines(stdout_text):
    payloads = []
    for line in (stdout_text or "").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payloads.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return payloads


def run_step_silently(step_name, fn, *args, **kwargs):
    buf = io.StringIO()
    exit_code = 0
    with redirect_stdout(buf):
        try:
            fn(*args, **kwargs)
        except SystemExit as e:
            if isinstance(e.code, int):
                exit_code = e.code
            elif e.code is None:
                exit_code = 0
            else:
                exit_code = 1
    stdout_text = buf.getvalue().strip()
    payloads = parse_json_lines(stdout_text)
    step = {
        "step": step_name,
        "exit_code": exit_code,
    }
    if payloads:
        step["payload"] = payloads[-1]
    elif stdout_text:
        step["stdout"] = stdout_text
    return step, exit_code


def file_signature(path):
    if not os.path.exists(path):
        return None
    st = os.stat(path)
    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return f"{mtime_ns}:{st.st_size}"


def cache_key(*parts):
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def read_load_cache(project_root):
    cache_path = resolve_path(project_root, LOAD_CACHE_FILE)
    return safe_json_load(cache_path, default={})


def read_json_cached(project_root, rel_path, cache_hint):
    path = resolve_path(project_root, rel_path)
    sig = file_signature(path)
    if not sig:
        return None
    cache = read_load_cache(project_root)
    key = cache_key("json", rel_path, cache_hint)
    item = cache.get(key)
    if isinstance(item, dict) and item.get("sig") == sig:
        return item.get("payload")
    payload = safe_json_load(path, default={})
    cache_path = resolve_path(project_root, LOAD_CACHE_FILE)

    def mutate(existing):
        if not isinstance(existing, dict):
            existing = {}
        existing[key] = {"sig": sig, "payload": payload, "ts": now_ts()}
        return existing

    update_json_locked(cache_path, {}, mutate)
    return payload


def compact_list(items, limit=20):
    if not isinstance(items, list):
        return items
    out = []
    for item in items[:limit]:
        if isinstance(item, dict):
            slim = {}
            for key in ("id", "chapter", "title", "name", "status", "source", "updated_at", "date"):
                if key in item:
                    slim[key] = item[key]
            if not slim:
                slim = {"preview": json.dumps(item, ensure_ascii=False)[:200]}
            out.append(slim)
        else:
            out.append(str(item)[:200])
    return out


def trim_bundle_to_budget(bundle, token_budget, tail_lines):
    report = {
        "token_budget": token_budget,
        "initial_estimated_tokens": approx_tokens(bundle),
        "actions": [],
    }
    if report["initial_estimated_tokens"] <= token_budget:
        report["final_estimated_tokens"] = report["initial_estimated_tokens"]
        report["over_budget"] = False
        bundle["budget_report"] = report
        return bundle

    if isinstance(bundle.get("context_memory"), str):
        bundle["context_memory"] = tail_text(bundle["context_memory"], lines=tail_lines)
        report["actions"].append(f"Trimmed context_memory to last {tail_lines} lines")

    history = bundle.get("history_log")
    if isinstance(history, list) and len(history) > 20:
        bundle["history_log"] = history[-20:]
        report["actions"].append("Trimmed history_log to last 20 items")

    for key in ("chapter_index", "literature_index", "figures_index"):
        value = bundle.get(key)
        if isinstance(value, list) and len(value) > 20:
            bundle[key] = compact_list(value, limit=20)
            report["actions"].append(f"Compacted {key} to 20 items")

    if approx_tokens(bundle) > token_budget and isinstance(bundle.get("project_state"), dict):
        project_state = bundle["project_state"]
        minimal = {
            "project_info": project_state.get("project_info", {}),
            "progress": project_state.get("progress", {}),
            "stats": project_state.get("stats", {}),
        }
        bundle["project_state"] = minimal
        report["actions"].append("Compacted project_state to core fields")

    report["final_estimated_tokens"] = approx_tokens(bundle)
    report["over_budget"] = report["final_estimated_tokens"] > token_budget
    bundle["budget_report"] = report
    return bundle


def check_runtime_dependencies(require_high_fidelity=False):
    checks = []
    warnings = []
    ok = True

    lock_item = {
        "name": "file-lock-backend",
        "module": LOCK_BACKEND,
        "required": False,
        "available": True,
        "error": None if fcntl is not None else "fcntl unavailable; using lock file fallback",
        "install_hint": "For stronger cross-process semantics on Windows, consider portalocker",
    }
    checks.append(lock_item)
    if fcntl is None:
        warnings.append("lock-backend-fallback:lockfile")

    requirements = [
        {
            "name": "python-docx",
            "module": "docx",
            "required": True,
            "install_hint": "pip3 install python-docx",
        },
        {
            "name": "docxcompose",
            "module": "docxcompose",
            "required": bool(require_high_fidelity),
            "install_hint": "pip3 install docxcompose",
        },
    ]

    for req in requirements:
        item = {
            "name": req["name"],
            "module": req["module"],
            "required": req["required"],
            "available": False,
            "error": None,
            "install_hint": req["install_hint"],
        }
        try:
            importlib.import_module(req["module"])
            item["available"] = True
        except Exception as e:
            item["error"] = str(e)
            if req["required"]:
                warnings.append(f"dependency-missing:{req['name']}")
                ok = False
        checks.append(item)

    return {"ok": ok, "checks": checks, "warnings": warnings}


def preflight_validate_state(project_root, chapter=None, strict=False, origin="manual", require_high_fidelity=False):
    checks = []
    warnings = []
    ok = True

    all_files = {}
    all_files.update(REQUIRED_STATE_FILES)
    all_files.update(OPTIONAL_STATE_FILES)

    for key, rel_path in all_files.items():
        path = resolve_path(project_root, rel_path)
        item = {
            "key": key,
            "file": path,
            "exists": os.path.exists(path),
            "parse_ok": None,
            "error": None,
        }
        if not item["exists"]:
            item["parse_ok"] = False
            item["error"] = "missing"
            if key in REQUIRED_STATE_FILES or strict:
                ok = False
            else:
                warnings.append(f"missing:{rel_path}")
        else:
            try:
                if path.endswith(".json"):
                    safe_json_load(path, default={})
                else:
                    with open(path, "r", encoding="utf-8") as f:
                        f.read(1024)
                item["parse_ok"] = True
            except Exception as e:
                item["parse_ok"] = False
                item["error"] = str(e)
                if key in REQUIRED_STATE_FILES or strict:
                    ok = False
                else:
                    warnings.append(f"parse-error:{rel_path}")
        checks.append(item)

    dep_result = check_runtime_dependencies(require_high_fidelity=require_high_fidelity)
    checks.extend(dep_result["checks"])
    warnings.extend(dep_result["warnings"])
    if not dep_result["ok"]:
        ok = False

    chapter_docs = glob.glob(resolve_path(project_root, "02_分章节文档/*.docx"))
    chapter_info = {
        "chapter": str(chapter) if chapter is not None else None,
        "chapter_docs_count": len(chapter_docs),
    }

    if chapter is not None:
        update_gate_state(
            project_root,
            chapter=str(chapter),
            preflight_ts=now_ts(),
            preflight_ok=ok,
            last_preflight_origin=origin,
            prewrite_ready=False,
            completion_ready=False,
        )

    payload = {
        "mode": "strict" if strict else "lenient",
        "ok": ok,
        "warnings": warnings,
        "checks": checks,
        "dependency_require_high_fidelity": bool(require_high_fidelity),
        "chapter_check": chapter_info,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if not ok:
        sys.exit(2)


def filter_for_chapter(data, chapter):
    terms = chapter_terms(chapter)
    if isinstance(data, list):
        return [x for x in data if contains_term(x, terms)]
    if isinstance(data, dict):
        # 保守策略：匹配不到则返回空 dict，减少串章污染
        if contains_term(data, terms):
            return data
        return {}
    return data


def find_chapter_doc_files(project_root, chapter):
    pattern = resolve_path(project_root, f"02_分章节文档/第{chapter}章*.docx")
    return sorted(glob.glob(pattern))


def load_state(
    project_root,
    chapter,
    token_budget=DEFAULT_TOKEN_BUDGET,
    tail_lines=DEFAULT_TAIL_LINES,
    include_draft=False,
    with_global_history=True,
    origin="manual",
):
    bundle = {
        "scope": "chapter-local",
        "chapter": str(chapter),
        "loaded_files": [],
    }

    # Core project state
    project_state = read_json_cached(project_root, "project_state.json", cache_hint="project_state")
    bundle["project_state"] = project_state
    bundle["loaded_files"].append(resolve_path(project_root, "project_state.json"))

    # Optional files
    chapter_index = read_json_cached(project_root, "chapter_index.json", cache_hint=f"chapter_index:{chapter}")
    if chapter_index is not None:
        bundle["chapter_index"] = filter_for_chapter(chapter_index, chapter)
        bundle["loaded_files"].append(resolve_path(project_root, "chapter_index.json"))
    else:
        bundle["chapter_index"] = None

    literature_index = read_json_cached(project_root, "literature_index.json", cache_hint=f"literature:{chapter}")
    if literature_index is not None:
        bundle["literature_index"] = filter_for_chapter(literature_index, chapter)
        bundle["loaded_files"].append(resolve_path(project_root, "literature_index.json"))
    else:
        bundle["literature_index"] = None

    figures_index = read_json_cached(project_root, "figures_index.json", cache_hint=f"figures:{chapter}")
    if figures_index is not None:
        bundle["figures_index"] = filter_for_chapter(figures_index, chapter)
        bundle["loaded_files"].append(resolve_path(project_root, "figures_index.json"))
    else:
        bundle["figures_index"] = None

    if with_global_history:
        context_path = resolve_path(project_root, "context_memory.md")
        if os.path.exists(context_path):
            with open(context_path, "r", encoding="utf-8") as f:
                bundle["context_memory"] = tail_text(f.read(), lines=tail_lines)
            bundle["loaded_files"].append(context_path)
        else:
            bundle["context_memory"] = None

        history_path = resolve_path(project_root, "history_log.json")
        if os.path.exists(history_path):
            history = safe_json_load(history_path, default=[])
            if isinstance(history, list):
                history = history[-50:]
            bundle["history_log"] = history
            bundle["loaded_files"].append(history_path)
        else:
            bundle["history_log"] = []

    if include_draft:
        docs = find_chapter_doc_files(project_root, chapter)
        previews = []
        for p in docs:
            previews.append(
                {
                    "file": p,
                    "size_bytes": os.path.getsize(p),
                    "modified_at": datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="seconds"),
                }
            )
            bundle["loaded_files"].append(p)
        bundle["chapter_draft_files"] = previews
    else:
        bundle["chapter_draft_files"] = None

    bundle = trim_bundle_to_budget(bundle, token_budget=token_budget, tail_lines=tail_lines)

    gate = read_gate_state(project_root)
    if gate.get("chapter") == str(chapter) and gate.get("preflight_ok", False):
        update_gate_state(
            project_root,
            load_ts=now_ts(),
            last_load_origin=origin,
            prewrite_ready=True,
            completion_ready=False,
            include_draft=bool(include_draft),
            with_global_history=bool(with_global_history),
        )

    print(json.dumps(bundle, ensure_ascii=False))


def rotate_context_memory_versions(project_root):
    base_file = resolve_path(project_root, "context_memory.md")
    v1 = resolve_path(project_root, "context_memory_v-1.md")
    v2 = resolve_path(project_root, "context_memory_v-2.md")

    if os.path.exists(v1):
        shutil.copy2(v1, v2)
    if os.path.exists(base_file):
        shutil.copy2(base_file, v1)


def append_history_log(project_root, item):
    path = resolve_path(project_root, "history_log.json")

    def mutate(payload):
        if not isinstance(payload, list):
            payload = []
        payload.append(item)
        return payload[-200:]

    update_json_locked(path, [], mutate)


def postwrite_state(project_root, chapter, status="updated", summary="", create_snapshot=False):
    ok, reason = validate_gate(project_root, chapter, "prewrite")
    if not ok:
        print(
            json.dumps(
                {
                    "error": "prewrite_gate_failed",
                    "reason": reason,
                    "hint": "Run write-cycle --chapter <n> before postwrite",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(2)

    ts = now_ts()
    updated_files = []

    # Update project_state progress
    state_path = resolve_path(project_root, "project_state.json")

    def mutate_project_state(project_state):
        if not isinstance(project_state, dict):
            project_state = {}
        progress = project_state.setdefault("progress", {})
        progress["last_chapter"] = str(chapter)
        progress["last_updated"] = ts
        progress["status"] = status
        if summary:
            progress["last_summary"] = summary
        hist = progress.get("update_history", [])
        if not isinstance(hist, list):
            hist = []
        hist.append(
            {
                "ts": ts,
                "chapter": str(chapter),
                "status": status,
                "summary": summary[:200],
            }
        )
        progress["update_history"] = hist[-50:]
        return project_state

    update_json_locked(state_path, {}, mutate_project_state)
    updated_files.append(state_path)

    # Update context memory + versions
    context_path = resolve_path(project_root, "context_memory.md")
    with file_lock(context_path, exclusive=True):
        existing = ""
        if os.path.exists(context_path):
            with open(context_path, "r", encoding="utf-8") as f:
                existing = f.read().rstrip()
            rotate_context_memory_versions(project_root)
        note = f"[{ts}] chapter={chapter}; status={status}"
        if summary:
            note += f"; summary={summary}"
        safe_text_dump(context_path, (existing + "\n" + note).strip() + "\n")
    updated_files.append(context_path)

    append_history_log(
        project_root,
        {
            "ts": ts,
            "chapter": str(chapter),
            "status": status,
            "summary": summary,
            "event": "postwrite",
        },
    )
    updated_files.append(resolve_path(project_root, "history_log.json"))

    update_gate_state(
        project_root,
        chapter=str(chapter),
        last_postwrite_ts=ts,
        completion_ready=True,
    )

    snapshot_dir = None
    if create_snapshot:
        snapshot_dir = backup_project_state(project_root)

    # Abbreviation processing (lazy-loaded, non-fatal)
    abbr_report = _postwrite_abbreviation_process(project_root, chapter)

    print(
        json.dumps(
            {
                "updated_files": updated_files,
                "snapshot_dir": snapshot_dir,
                "gate": {
                    "chapter": str(chapter),
                    "completion_ready": True,
                },
                "abbreviation_processing": abbr_report,
            },
            ensure_ascii=False,
        )
    )


def detect_default_docx(project_root):
    state_path = resolve_path(project_root, "project_state.json")
    state = safe_json_load(state_path, default={})
    save_path = (
        state.get("project_info", {}).get("save_path")
        if isinstance(state, dict)
        else None
    )
    if not save_path:
        return None
    candidate = os.path.join(save_path, "03_合并文档", "完整博士论文.docx")
    if os.path.exists(candidate):
        return candidate
    return None


def load_count_words_module(project_root):
    script_path = resolve_path(project_root, "scripts/count_words_docx.py")
    if not os.path.exists(script_path):
        script_path = os.path.join(os.path.dirname(__file__), "count_words_docx.py")
    import importlib.util

    spec = importlib.util.spec_from_file_location("sci2doc_count_words_docx", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load count_words_docx module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def word_count(project_root, docx=None, sync_project_state=True):
    target = docx
    if target is None:
        target = detect_default_docx(project_root)
    if target is None:
        print(json.dumps({"success": False, "error": "no docx target found; pass --docx explicitly"}, ensure_ascii=False))
        sys.exit(2)
    if not os.path.isabs(target):
        target = resolve_path(project_root, target)
    if not os.path.exists(target):
        print(json.dumps({"success": False, "error": f"docx not found: {target}"}, ensure_ascii=False))
        sys.exit(2)

    module = load_count_words_module(project_root)
    profile, _ = load_profile(project_root)
    targets = profile.get("targets", {}) if isinstance(profile, dict) else {}
    body_target = int(targets.get("body_target_chars", 80000))
    review_target = int(targets.get("review_target_chars", 0))
    review_in_scope = bool(targets.get("review_in_scope", False))
    result = module.count_words_in_docx(
        target,
        exclude_references=True,
        body_target_chars=body_target,
        review_target_chars=review_target,
        review_in_scope=review_in_scope,
    )
    result["source"] = target
    body_words, review_words, total_words = extract_word_stats(result)

    if sync_project_state:
        state_path = resolve_path(project_root, "project_state.json")
        sync_ts = now_ts()

        def mutate_state(state):
            if not isinstance(state, dict):
                state = {}
            stats_data = state.setdefault("stats", {})
            stats_data["total_body_words"] = body_words
            stats_data["review_words"] = review_words
            stats_data["total_words_including_abstract"] = total_words
            stats_data["word_count_last_updated"] = sync_ts
            return state

        update_json_locked(state_path, {}, mutate_state)
        append_history_log(
            project_root,
            {
                "ts": sync_ts,
                "chapter": "all",
                "status": "word_count_synced",
                "summary": f"body={body_words}, review={review_words}, total={total_words}",
                "event": "word_count",
            },
        )
        result["synced_to_project_state"] = True
        result["project_state_path"] = state_path
    else:
        result["synced_to_project_state"] = False

    print(json.dumps(result, ensure_ascii=False))


def list_snapshot_backups(project_root, backup_dir="backups"):
    root = resolve_path(project_root, backup_dir)
    if not os.path.exists(root):
        return []
    dirs = [d for d in glob.glob(os.path.join(root, "snapshot_*")) if os.path.isdir(d)]
    dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return dirs


def prune_snapshots(project_root, backup_dir="backups", keep=DEFAULT_BACKUP_KEEP):
    snapshots = list_snapshot_backups(project_root, backup_dir=backup_dir)
    for stale in snapshots[keep:]:
        try:
            shutil.rmtree(stale)
        except Exception:
            pass


def create_unique_snapshot_dir(project_root, backup_dir="backups"):
    backup_root = resolve_path(project_root, backup_dir)
    os.makedirs(backup_root, exist_ok=True)
    base = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for idx in range(100):
        suffix = "" if idx == 0 else f"_{idx}"
        candidate = os.path.join(backup_root, f"snapshot_{base}{suffix}")
        try:
            os.makedirs(candidate)
            return candidate
        except FileExistsError:
            continue
    raise StateFileError(
        path=backup_root,
        reason="snapshot_dir_conflict",
        detail="failed to allocate unique snapshot directory",
    )


def backup_project_state(project_root, backup_dir="backups"):
    snapshot_dir = create_unique_snapshot_dir(project_root, backup_dir=backup_dir)

    # Backup state files
    all_files = {}
    all_files.update(REQUIRED_STATE_FILES)
    all_files.update(OPTIONAL_STATE_FILES)
    all_files["context_memory_v-1"] = "context_memory_v-1.md"
    all_files["context_memory_v-2"] = "context_memory_v-2.md"
    for rel_path in all_files.values():
        src = resolve_path(project_root, rel_path)
        if os.path.exists(src):
            shutil.copy2(src, resolve_path(snapshot_dir, os.path.basename(rel_path)))

    # Backup runtime state dir
    state_dir = resolve_path(project_root, ".state")
    if os.path.exists(state_dir):
        shutil.copytree(state_dir, resolve_path(snapshot_dir, ".state"))

    # Backup chapter docs dirs (if exists)
    for folder in ("02_分章节文档", "03_合并文档", "04_图表文件", "chapter_memory"):
        src = resolve_path(project_root, folder)
        if os.path.exists(src):
            shutil.copytree(src, resolve_path(snapshot_dir, folder))

    prune_snapshots(project_root, backup_dir=backup_dir, keep=DEFAULT_BACKUP_KEEP)
    return snapshot_dir


def remove_path_if_exists(path):
    if not os.path.exists(path):
        return False
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    return True


def restore_snapshot(project_root, snapshot_dir, strict_mirror=False):
    if not snapshot_dir or not os.path.exists(snapshot_dir):
        return {"restored": False, "reason": "snapshot_not_found", "snapshot_dir": snapshot_dir}

    restored_files = []
    cleaned_paths = []

    if strict_mirror:
        for rel_path in RESTORE_MANAGED_FILES:
            dst = resolve_path(project_root, rel_path)
            if remove_path_if_exists(dst):
                cleaned_paths.append(dst)
        for folder in RESTORE_MANAGED_DIRS:
            dst = resolve_path(project_root, folder)
            if remove_path_if_exists(dst):
                cleaned_paths.append(dst)

    # Restore top-level files
    for filename in os.listdir(snapshot_dir):
        src = os.path.join(snapshot_dir, filename)
        dst = resolve_path(project_root, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            restored_files.append(dst)

    # Restore dirs
    for folder in RESTORE_MANAGED_DIRS:
        src_dir = os.path.join(snapshot_dir, folder)
        if not os.path.exists(src_dir):
            continue
        dst_dir = resolve_path(project_root, folder)
        if strict_mirror:
            shutil.copytree(src_dir, dst_dir)
            restored_files.append(dst_dir)
            continue

        os.makedirs(dst_dir, exist_ok=True)
        for src in glob.glob(os.path.join(src_dir, "*")):
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_dir, os.path.basename(src)))
            elif os.path.isdir(src):
                target = os.path.join(dst_dir, os.path.basename(src))
                if os.path.exists(target):
                    shutil.rmtree(target)
                shutil.copytree(src, target)
            restored_files.append(os.path.join(dst_dir, os.path.basename(src)))

    return {
        "restored": True,
        "snapshot_dir": snapshot_dir,
        "restored_files_count": len(restored_files),
        "restored_files": restored_files,
        "strict_mirror": bool(strict_mirror),
        "cleaned_paths_count": len(cleaned_paths),
    }


def rollback_state(project_root, target="snapshot", snapshot_dir=None, backup_dir="backups", strict_mirror=False):
    if target != "snapshot":
        return {"restored": False, "reason": f"unsupported target: {target}"}
    chosen = snapshot_dir
    if not chosen:
        snapshots = list_snapshot_backups(project_root, backup_dir=backup_dir)
        chosen = snapshots[0] if snapshots else None
    return restore_snapshot(project_root, chosen, strict_mirror=strict_mirror)


def stats(project_root, chapter=None, backup_dir="backups"):
    gate = read_gate_state(project_root)
    project_state = safe_json_load(resolve_path(project_root, "project_state.json"), default={})
    profile, profile_path = load_profile(project_root)
    chapter_docs = glob.glob(resolve_path(project_root, "02_分章节文档/*.docx"))
    snapshots = list_snapshot_backups(project_root, backup_dir=backup_dir)
    history = safe_json_load(resolve_path(project_root, "history_log.json"), default=[])
    chapter_index = safe_json_load(resolve_path(project_root, "chapter_index.json"), default=[])
    literature_index = safe_json_load(resolve_path(project_root, "literature_index.json"), default=[])
    figures_index = safe_json_load(resolve_path(project_root, "figures_index.json"), default=[])
    context_path = resolve_path(project_root, "context_memory.md")
    context_lines = 0
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            context_lines = len(f.read().splitlines())

    payload = {
        "timestamp": now_ts(),
        "project_root": project_root,
        "chapter_filter": str(chapter) if chapter is not None else None,
        "progress": project_state.get("progress", {}) if isinstance(project_state, dict) else {},
        "stats": project_state.get("stats", {}) if isinstance(project_state, dict) else {},
        "chapter_docs_count": len(chapter_docs),
        "gate": {
            "chapter": gate.get("chapter"),
            "preflight_ok": gate.get("preflight_ok"),
            "prewrite_ready": gate.get("prewrite_ready"),
            "completion_ready": gate.get("completion_ready"),
            "last_preflight_origin": gate.get("last_preflight_origin"),
            "last_load_origin": gate.get("last_load_origin"),
            "last_postwrite_ts": gate.get("last_postwrite_ts"),
        },
        "indexes": {
            "history_log_count": count_index_entries(history),
            "chapter_index_count": count_index_entries(chapter_index),
            "literature_index_count": count_index_entries(literature_index),
            "figures_index_count": count_index_entries(figures_index),
            "context_memory_lines": context_lines,
        },
        "backups": {
            "snapshot_count": len(snapshots),
            "latest_snapshot": snapshots[0] if snapshots else None,
        },
        "thesis_profile": {
            "path": profile_path,
            "body_target_chars": profile.get("targets", {}).get("body_target_chars"),
            "abstract_min_chars": profile.get("targets", {}).get("abstract_min_chars"),
            "abstract_max_chars": profile.get("targets", {}).get("abstract_max_chars"),
            "review_in_scope": profile.get("targets", {}).get("review_in_scope"),
            "chapter_targets_count": len(profile.get("chapter_targets", {}))
            if isinstance(profile.get("chapter_targets"), dict)
            else 0,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


def init_project(
    project_root,
    save_path=None,
    title="",
    title_en="",
    author="",
    student_id="",
    supervisor="",
    major="",
    source_paper="",
    copy_local_scripts=False,
):
    if save_path is None:
        effective_root = os.path.abspath(project_root)
    elif os.path.isabs(save_path):
        effective_root = save_path
    else:
        effective_root = resolve_path(project_root, save_path)
    effective_root = os.path.abspath(effective_root)

    # Core folders
    folders = [
        "01_文献分析",
        "02_分章节文档",
        "03_合并文档",
        "04_图表文件",
        "05_参考文献",
        "chapter_memory",
        ".state",
    ]
    for folder in folders:
        os.makedirs(resolve_path(effective_root, folder), exist_ok=True)

    # Base files
    state_path = resolve_path(effective_root, "project_state.json")

    def mutate_project_state(state):
        if not isinstance(state, dict) or not state:
            return {
                "project_info": {
                    "title": title,
                    "title_en": title_en,
                    "author": author,
                    "student_id": student_id,
                    "supervisor": supervisor,
                    "major": major,
                    "save_path": effective_root,
                    "source_paper": source_paper,
                },
                "progress": {
                    "status": "idle",
                    "current_chapter_index": 0,
                    "total_chapters": 0,
                    "completed_files": [],
                },
                "outline": [],
                "stats": {
                    "total_body_words": 0,
                    "review_words": 0,
                    "last_updated": "",
                },
            }

        info = state.setdefault("project_info", {})
        info["save_path"] = effective_root
        if title:
            info["title"] = title
        if title_en:
            info["title_en"] = title_en
        if author:
            info["author"] = author
        if student_id:
            info["student_id"] = student_id
        if supervisor:
            info["supervisor"] = supervisor
        if major:
            info["major"] = major
        if source_paper:
            info["source_paper"] = source_paper
        return state

    update_json_locked(state_path, {}, mutate_project_state)

    for rel_path, default_value in [
        ("context_memory.md", ""),
        ("history_log.json", []),
        ("chapter_index.json", []),
        ("literature_index.json", []),
        ("figures_index.json", []),
    ]:
        path = resolve_path(effective_root, rel_path)
        if os.path.exists(path):
            continue
        if rel_path.endswith(".json"):
            safe_json_dump(path, default_value)
        else:
            safe_text_dump(path, default_value)

    profile, profile_path = load_profile(effective_root)
    save_profile(profile_path, profile)

    copied_scripts = []
    if copy_local_scripts:
        src_dir = os.path.dirname(os.path.abspath(__file__))
        dst_dir = resolve_path(effective_root, "scripts")
        os.makedirs(dst_dir, exist_ok=True)
        for src in glob.glob(os.path.join(src_dir, "*.py")):
            dst = os.path.join(dst_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            copied_scripts.append(dst)

    print(
        json.dumps(
            {
                "ok": True,
                "project_root": effective_root,
                "save_path": effective_root,
                "initialized_files": [
                    "project_state.json",
                    "thesis_profile.json",
                    "context_memory.md",
                    "history_log.json",
                    "chapter_index.json",
                    "literature_index.json",
                    "figures_index.json",
                ],
                "copied_scripts_count": len(copied_scripts),
                "copied_scripts": copied_scripts,
            },
            ensure_ascii=False,
        )
    )


def write_cycle(
    project_root,
    chapter,
    token_budget=DEFAULT_TOKEN_BUDGET,
    tail_lines=DEFAULT_TAIL_LINES,
    include_draft=False,
    finalize=False,
    summary="",
    status="updated",
    preflight_strict=True,
    snapshot=False,
    require_high_fidelity=False,
    json_summary=False,
):
    if not json_summary:
        start_cycle(project_root, chapter)
        preflight_validate_state(
            project_root=project_root,
            chapter=chapter,
            strict=preflight_strict,
            origin="write-cycle",
            require_high_fidelity=require_high_fidelity,
        )
        load_state(
            project_root=project_root,
            chapter=chapter,
            token_budget=token_budget,
            tail_lines=tail_lines,
            include_draft=include_draft,
            with_global_history=True,
            origin="write-cycle",
        )
        gate_check(project_root=project_root, chapter=chapter, phase="prewrite")
        if finalize:
            postwrite_state(
                project_root=project_root,
                chapter=chapter,
                status=status,
                summary=summary,
                create_snapshot=snapshot,
            )
            gate_check(project_root=project_root, chapter=chapter, phase="complete")
        return

    start_cycle(project_root, chapter)
    steps = []
    exit_code = 0

    step, step_code = run_step_silently(
        "preflight",
        preflight_validate_state,
        project_root=project_root,
        chapter=chapter,
        strict=preflight_strict,
        origin="write-cycle",
        require_high_fidelity=require_high_fidelity,
    )
    steps.append(step)
    if step_code != 0:
        exit_code = step_code

    if exit_code == 0:
        step, step_code = run_step_silently(
            "load",
            load_state,
            project_root=project_root,
            chapter=chapter,
            token_budget=token_budget,
            tail_lines=tail_lines,
            include_draft=include_draft,
            with_global_history=True,
            origin="write-cycle",
        )
        steps.append(step)
        if step_code != 0:
            exit_code = step_code

    if exit_code == 0:
        step, step_code = run_step_silently(
            "gate-prewrite",
            gate_check,
            project_root=project_root,
            chapter=chapter,
            phase="prewrite",
        )
        steps.append(step)
        if step_code != 0:
            exit_code = step_code

    if finalize and exit_code == 0:
        step, step_code = run_step_silently(
            "postwrite",
            postwrite_state,
            project_root=project_root,
            chapter=chapter,
            status=status,
            summary=summary,
            create_snapshot=snapshot,
        )
        steps.append(step)
        if step_code != 0:
            exit_code = step_code

    if finalize and exit_code == 0:
        step, step_code = run_step_silently(
            "gate-complete",
            gate_check,
            project_root=project_root,
            chapter=chapter,
            phase="complete",
        )
        steps.append(step)
        if step_code != 0:
            exit_code = step_code

    payload = {
        "command": "write-cycle",
        "project_root": project_root,
        "chapter": str(chapter),
        "finalize": bool(finalize),
        "ok": exit_code == 0,
        "exit_code": exit_code,
        "steps": steps,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if exit_code != 0:
        sys.exit(exit_code)


def profile_manage(
    project_root,
    body_target=None,
    abstract_min=None,
    abstract_max=None,
    references_min=None,
    min_chapters=None,
    chapter_target_specs=None,
    show_only=False,
):
    profile, path = load_profile(project_root)
    targets = profile.setdefault("targets", {})
    chapter_targets = profile.setdefault("chapter_targets", {})
    if not isinstance(chapter_targets, dict):
        chapter_targets = {}
        profile["chapter_targets"] = chapter_targets

    updated = False
    if body_target is not None:
        targets["body_target_chars"] = int(body_target)
        updated = True
    if abstract_min is not None:
        targets["abstract_min_chars"] = int(abstract_min)
        updated = True
    if abstract_max is not None:
        targets["abstract_max_chars"] = int(abstract_max)
        updated = True
    if references_min is not None:
        targets["references_min_count"] = int(references_min)
        updated = True
    if min_chapters is not None:
        targets["min_chapters"] = int(min_chapters)
        updated = True
    if chapter_target_specs:
        for spec in chapter_target_specs:
            chapter, chars = parse_chapter_target_spec(spec)
            chapter_targets[str(chapter)] = int(chars)
            updated = True

    min_chars = targets.get("abstract_min_chars")
    max_chars = targets.get("abstract_max_chars")
    body_chars = targets.get("body_target_chars")
    references_min_count = targets.get("references_min_count")
    min_chapter_count = targets.get("min_chapters")

    if body_chars is not None and int(body_chars) < 80000:
        raise StateFileError(
            path=path,
            reason="invalid_profile",
            detail=f"body_target_chars ({body_chars}) must be >= 80000",
        )

    if min_chars is not None and int(min_chars) < 1500:
        raise StateFileError(
            path=path,
            reason="invalid_profile",
            detail=f"abstract_min_chars ({min_chars}) must be >= 1500",
        )
    if max_chars is not None and int(max_chars) > 2500:
        raise StateFileError(
            path=path,
            reason="invalid_profile",
            detail=f"abstract_max_chars ({max_chars}) must be <= 2500",
        )
    if min_chars is not None and max_chars is not None and int(min_chars) > int(max_chars):
        raise StateFileError(
            path=path,
            reason="invalid_profile",
            detail=f"abstract_min_chars ({min_chars}) > abstract_max_chars ({max_chars})",
        )

    if references_min_count is not None and int(references_min_count) <= 0:
        raise StateFileError(
            path=path,
            reason="invalid_profile",
            detail=f"references_min_count ({references_min_count}) must be > 0",
        )
    if min_chapter_count is not None and int(min_chapter_count) < 5:
        raise StateFileError(
            path=path,
            reason="invalid_profile",
            detail=f"min_chapters ({min_chapter_count}) must be >= 5",
        )

    if updated and not show_only:
        save_profile(path, profile)

    payload = {
        "ok": True,
        "profile_path": path,
        "updated": bool(updated and not show_only),
        "profile": profile,
    }
    print(json.dumps(payload, ensure_ascii=False))


def parse_args():
    parser = argparse.ArgumentParser(description="Manage state for Sci2Doc projects")
    parser.add_argument("--project-root", default=".", help="Sci2Doc project root path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_p = subparsers.add_parser("preflight", help="Lightweight validation")
    preflight_p.add_argument("--chapter", help="Chapter id/number")
    preflight_p.add_argument("--strict", action="store_true", help="Fail if optional files are missing")
    preflight_p.add_argument(
        "--require-high-fidelity",
        action="store_true",
        help="Treat docxcompose as required dependency",
    )

    load_p = subparsers.add_parser("load", help="Load project/chapter context")
    load_p.add_argument("--chapter", required=True, help="Chapter id/number")
    load_p.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET)
    load_p.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES)
    load_p.add_argument("--include-draft", action="store_true")

    gate_p = subparsers.add_parser("gate-check", help="Gate check")
    gate_p.add_argument("--chapter", required=True)
    gate_p.add_argument("--phase", choices=["prewrite", "complete"], required=True)

    postwrite_p = subparsers.add_parser("postwrite", help="Finalize one writing turn")
    postwrite_p.add_argument("--chapter", required=True)
    postwrite_p.add_argument("--status", default="updated")
    postwrite_p.add_argument("--summary", default="")
    postwrite_p.add_argument("--snapshot", action="store_true")

    cycle_p = subparsers.add_parser("write-cycle", help="Single required entry for write turns")
    cycle_p.add_argument("--chapter", required=True)
    cycle_p.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET)
    cycle_p.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES)
    cycle_p.add_argument("--include-draft", action="store_true")
    cycle_p.add_argument("--finalize", action="store_true")
    cycle_p.add_argument("--summary", default="")
    cycle_p.add_argument("--status", default="updated")
    cycle_p.add_argument("--snapshot", action="store_true")
    cycle_p.add_argument("--preflight-lenient", action="store_true")
    cycle_p.add_argument(
        "--require-high-fidelity",
        action="store_true",
        help="Preflight checks docxcompose as required",
    )
    cycle_p.add_argument(
        "--json-summary",
        action="store_true",
        help="Emit single aggregated JSON payload for the full write-cycle",
    )

    init_p = subparsers.add_parser("init", help="Initialize Sci2Doc project state/files")
    init_p.add_argument("--save-path", help="Target project root (default: --project-root)")
    init_p.add_argument("--title", default="")
    init_p.add_argument("--title-en", default="")
    init_p.add_argument("--author", default="")
    init_p.add_argument("--student-id", default="")
    init_p.add_argument("--supervisor", default="")
    init_p.add_argument("--major", default="")
    init_p.add_argument("--source-paper", default="")
    init_p.add_argument("--copy-local-scripts", action="store_true")

    wc_p = subparsers.add_parser("word-count", help="Count words from merged docx")
    wc_p.add_argument("--docx", help="docx path; default auto-detect from project_state.save_path")
    wc_p.add_argument("--no-sync", action="store_true", help="Do not sync count result into project_state.json")

    stats_p = subparsers.add_parser("stats", help="Project dashboard")
    stats_p.add_argument("--chapter", help="Optional chapter filter marker")
    stats_p.add_argument("--backup-dir", default="backups")

    subparsers.add_parser("snapshot", help="Create full snapshot")

    rollback_p = subparsers.add_parser("rollback", help="Rollback from latest snapshot")
    rollback_p.add_argument("--target", choices=["snapshot"], default="snapshot")
    rollback_p.add_argument("--snapshot-dir", help="Specific snapshot dir")
    rollback_p.add_argument("--backup-dir", default="backups")
    rollback_p.add_argument(
        "--strict-mirror",
        action="store_true",
        help="Remove managed current files/dirs before restore for strict mirror rollback",
    )

    profile_p = subparsers.add_parser("profile", help="Show or update thesis profile")
    profile_p.add_argument("--show", action="store_true", help="Show profile only")
    profile_p.add_argument("--body-target", type=int, help="Set body target chars, e.g. 80000")
    profile_p.add_argument("--abstract-min", type=int, help="Set abstract min chars")
    profile_p.add_argument("--abstract-max", type=int, help="Set abstract max chars")
    profile_p.add_argument("--references-min", type=int, help="Set min references count")
    profile_p.add_argument("--min-chapters", type=int, help="Set minimum chapter count")
    profile_p.add_argument(
        "--chapter-target",
        action="append",
        default=[],
        help="Set chapter target using '<chapter>:<chars>', repeatable",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    project_root = os.path.abspath(args.project_root)
    try:
        if args.command == "init":
            init_project(
                project_root=project_root,
                save_path=args.save_path,
                title=args.title,
                title_en=args.title_en,
                author=args.author,
                student_id=args.student_id,
                supervisor=args.supervisor,
                major=args.major,
                source_paper=args.source_paper,
                copy_local_scripts=args.copy_local_scripts,
            )
        elif args.command == "preflight":
            preflight_validate_state(
                project_root=project_root,
                chapter=args.chapter,
                strict=args.strict,
                origin="manual",
                require_high_fidelity=args.require_high_fidelity,
            )
        elif args.command == "load":
            load_state(
                project_root=project_root,
                chapter=args.chapter,
                token_budget=max(1000, args.token_budget),
                tail_lines=max(20, args.tail_lines),
                include_draft=args.include_draft,
                with_global_history=True,
                origin="manual",
            )
        elif args.command == "gate-check":
            gate_check(project_root=project_root, chapter=args.chapter, phase=args.phase)
        elif args.command == "postwrite":
            postwrite_state(
                project_root=project_root,
                chapter=args.chapter,
                status=args.status,
                summary=args.summary,
                create_snapshot=args.snapshot,
            )
        elif args.command == "write-cycle":
            write_cycle(
                project_root=project_root,
                chapter=args.chapter,
                token_budget=max(1000, args.token_budget),
                tail_lines=max(20, args.tail_lines),
                include_draft=args.include_draft,
                finalize=args.finalize,
                summary=args.summary,
                status=args.status,
                preflight_strict=(not args.preflight_lenient),
                snapshot=args.snapshot,
                require_high_fidelity=args.require_high_fidelity,
                json_summary=args.json_summary,
            )
        elif args.command == "word-count":
            word_count(project_root=project_root, docx=args.docx, sync_project_state=(not args.no_sync))
        elif args.command == "stats":
            stats(project_root=project_root, chapter=args.chapter, backup_dir=args.backup_dir)
        elif args.command == "snapshot":
            payload = {"snapshot_dir": backup_project_state(project_root)}
            print(json.dumps(payload, ensure_ascii=False))
        elif args.command == "rollback":
            payload = rollback_state(
                project_root=project_root,
                target=args.target,
                snapshot_dir=args.snapshot_dir,
                backup_dir=args.backup_dir,
                strict_mirror=args.strict_mirror,
            )
            print(json.dumps(payload, ensure_ascii=False))
        elif args.command == "profile":
            profile_manage(
                project_root=project_root,
                body_target=args.body_target,
                abstract_min=args.abstract_min,
                abstract_max=args.abstract_max,
                references_min=args.references_min,
                min_chapters=args.min_chapters,
                chapter_target_specs=args.chapter_target,
                show_only=args.show,
            )
    except StateFileError as e:
        payload = {
            "success": False,
            "error": "state_file_error",
            "reason": e.reason,
            "file": os.path.abspath(e.path),
            "detail": e.detail,
            "hint": f"Fix the file or run: python3 scripts/state_manager.py --project-root '{project_root}' rollback --target snapshot",
        }
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(2)


if __name__ == "__main__":
    main()

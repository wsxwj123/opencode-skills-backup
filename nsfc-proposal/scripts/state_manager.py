#!/usr/bin/env python3
"""Project state manager for nsfc-proposal skill."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import consistency_mapper
import diagnosis_engine
import word_counter


DEFAULT_PROFILE = {
    "project_type": "面上项目",
    "research_attribute": "自由探索类",
    "duration_years": 4,
    "budget_total": 500000,
    "page_limit": 30,
    "word_targets": {
        "p1_rationale": {"recommended_max": 8000, "user_agreed": None},
        "p2_content": {"recommended_max": 8000, "user_agreed": None},
        "p3_foundation": {"recommended_max": 6000, "user_agreed": None},
        "p4_other": {"recommended_max": 500, "user_agreed": None},
        "total_body": {"min": 18000, "max": 25000},
    },
    "citation_targets": {"min_total": 30, "min_recent_5yr": 20, "min_cn_journals": 5},
    "mode": "write",
}

SECTION_ALIASES = {
    "P1": "P1_立项依据.md",
    "P2": "P2_研究内容.md",
    "P3_1": "P3_1_研究基础与可行性分析.md",
    "P3_2": "P3_2_工作条件.md",
    "P3_3": "P3_3_正在承担的相关项目.md",
    "P3_4": "P3_4_完成基金项目情况.md",
    "P4": "P4_其他需要说明的情况.md",
    "REF": "REF_参考文献.md",
}


AUTO_FIX_STUBS = {
    "sections/P1_立项依据.md": "# P1_立项依据\n\n待补充。\n",
    "sections/REF_参考文献.md": "# REF_参考文献\n\n待补充。\n",
}


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_history(root: Path, event: str, payload: dict[str, Any] | None = None) -> None:
    history = load_json(root / "history_log.json", {"events": []})
    history.setdefault("events", []).append({"at": utc_now(), "event": event, "payload": payload or {}})
    save_json(root / "history_log.json", history)


def append_context(root: Path, content: str) -> None:
    path = root / "context_memory.md"
    if not path.exists():
        path.write_text("# Context Memory\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"## {utc_now()}\n")
        f.write(content.strip() + "\n\n")


def init_project(root: Path) -> None:
    for d in ["sections", "output", "data", ".state", "snapshots"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    save_json(root / "proposal_profile.json", DEFAULT_PROFILE)
    save_json(root / "data/literature_index.json", {"metadata": {"verification_status": "pending"}, "entries": []})
    save_json(root / "data/consistency_map.json", consistency_mapper.load_map(Path("__missing__")))
    save_json(root / "project_state.json", {"phase": "phase0", "gate": "init", "updated_at": utc_now()})
    save_json(root / "history_log.json", {"events": []})

    (root / "context_memory.md").write_text("# Context Memory\n\n", encoding="utf-8")
    append_history(root, "init")
    append_context(root, "Project initialized.")


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def do_snapshot(root: Path, name: str) -> Path:
    snap = root / "snapshots" / f"{ts()}_{name}"
    snap.mkdir(parents=True, exist_ok=True)

    for d in ["sections", "data", "output", ".state"]:
        src = root / d
        if src.exists():
            shutil.copytree(src, snap / d)

    for f in ["project_state.json", "proposal_profile.json", "history_log.json", "context_memory.md"]:
        src = root / f
        if src.exists():
            shutil.copy2(src, snap / f)

    append_history(root, "snapshot", {"name": name, "path": str(snap)})
    return snap


def rollback(root: Path, snapshot_dir: Path) -> None:
    do_snapshot(root, "pre_rollback")

    for d in ["sections", "data", "output", ".state"]:
        target = root / d
        if target.exists():
            shutil.rmtree(target)
        src = snapshot_dir / d
        if src.exists():
            shutil.copytree(src, target)

    for f in ["project_state.json", "proposal_profile.json", "history_log.json", "context_memory.md"]:
        src = snapshot_dir / f
        if src.exists():
            shutil.copy2(src, root / f)

    append_history(root, "rollback", {"snapshot": str(snapshot_dir)})
    append_context(root, f"Rolled back to snapshot: {snapshot_dir}")


def _phase_number(state: dict[str, Any]) -> int:
    phase = str(state.get("phase", ""))
    m = re.match(r"phase(\d+)", phase)
    return int(m.group(1)) if m else -1


def _semantic_sync_checks(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    cm = consistency_mapper.load_map(root / "data/consistency_map.json")
    cm_validation = consistency_mapper.validate(cm)
    cm_error = any((not x["pass"] and x["severity"] == "ERROR") for x in cm_validation.values())

    lit = load_json(root / "data/literature_index.json", {"metadata": {}, "entries": []})
    p1_entries = [e for e in lit.get("entries", []) if "P1_立项依据" in (e.get("used_in_sections") or [])]
    p1_verified = all(bool(e.get("verified")) for e in p1_entries) if p1_entries else False

    context_text = (root / "context_memory.md").read_text(encoding="utf-8") if (root / "context_memory.md").exists() else ""
    has_context_blocks = "## " in context_text

    history = load_json(root / "history_log.json", {"events": []})
    has_history = bool(history.get("events"))

    phase_no = _phase_number(state)
    require_strict = phase_no >= 2

    return {
        "cm_has_error": cm_error,
        "cm_validation": cm_validation,
        "p1_entries_count": len(p1_entries),
        "p1_verified": p1_verified,
        "has_context_blocks": has_context_blocks,
        "has_history": has_history,
        "strict_mode": require_strict,
    }


def sync_all(root: Path) -> dict[str, Any]:
    required = [
        root / "data/consistency_map.json",
        root / "data/literature_index.json",
        root / "context_memory.md",
        root / "project_state.json",
        root / "history_log.json",
    ]
    exists = {str(p.relative_to(root)): p.exists() for p in required}

    state = load_json(root / "project_state.json", {})
    phase = state.get("phase", "")
    gate = state.get("gate", "")
    if phase == "phase0" and gate == "init":
        fresh = {str(p.relative_to(root)): True for p in required if p.name != "project_state.json"}
    else:
        state_mtime = (root / "project_state.json").stat().st_mtime if (root / "project_state.json").exists() else 0.0
        grace_seconds = 2.0
        fresh = {
            str(p.relative_to(root)): (p.exists() and (p.stat().st_mtime + grace_seconds) >= state_mtime)
            for p in required
            if p.name != "project_state.json"
        }

    semantic = _semantic_sync_checks(root, state)

    return {
        "exists": exists,
        "fresh": fresh,
        "semantic": semantic,
    }


def _auto_fix_project(root: Path) -> dict[str, Any]:
    fixed: list[str] = []

    for d in ["sections", "output", "data", ".state", "snapshots"]:
        p = root / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            fixed.append(f"mkdir:{d}")

    profile_path = root / "proposal_profile.json"
    profile = load_json(profile_path, DEFAULT_PROFILE)
    if not isinstance(profile, dict):
        profile = DEFAULT_PROFILE
        fixed.append("reset:proposal_profile.json")
    save_json(profile_path, deep_merge(DEFAULT_PROFILE, profile))

    lit_path = root / "data/literature_index.json"
    lit = load_json(lit_path, {"metadata": {"verification_status": "pending"}, "entries": []})
    if isinstance(lit, list):
        lit = {"metadata": {"verification_status": "pending"}, "entries": lit}
        fixed.append("normalize:data/literature_index.json:list->dict")
    elif not isinstance(lit, dict):
        lit = {"metadata": {"verification_status": "pending"}, "entries": []}
        fixed.append("reset:data/literature_index.json")
    lit.setdefault("metadata", {})
    if not isinstance(lit.get("entries"), list):
        lit["entries"] = []
        fixed.append("normalize:data/literature_index.json:entries")
    save_json(lit_path, lit)

    cm_path = root / "data/consistency_map.json"
    cm = consistency_mapper.load_map(cm_path)
    save_json(cm_path, cm)

    ps_path = root / "project_state.json"
    ps = load_json(ps_path, {"phase": "phase0", "gate": "init", "updated_at": utc_now()})
    if not isinstance(ps, dict):
        ps = {"phase": "phase0", "gate": "init", "updated_at": utc_now()}
        fixed.append("reset:project_state.json")
    ps.setdefault("phase", "phase0")
    ps.setdefault("gate", "init")
    ps["updated_at"] = utc_now()
    save_json(ps_path, ps)

    hist_path = root / "history_log.json"
    hist = load_json(hist_path, {"events": []})
    if not isinstance(hist, dict):
        hist = {"events": []}
        fixed.append("reset:history_log.json")
    if not isinstance(hist.get("events"), list):
        hist["events"] = []
        fixed.append("normalize:history_log.json:events")
    save_json(hist_path, hist)

    context_path = root / "context_memory.md"
    if not context_path.exists():
        context_path.write_text("# Context Memory\n\n", encoding="utf-8")
        fixed.append("create:context_memory.md")

    for rel, content in AUTO_FIX_STUBS.items():
        target = root / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            fixed.append(f"create:{rel}")

    append_history(root, "auto_fix", {"fixed": fixed})
    append_context(root, "Auto-fix applied.")
    return {"fixed_count": len(fixed), "fixed": fixed}


def _normalize_section_name(section: str) -> str:
    s = section.strip()
    if s in SECTION_ALIASES:
        return SECTION_ALIASES[s]
    if s.endswith(".md"):
        return s
    return s + ".md"


def _section_file(root: Path, section: str) -> Path:
    return root / "sections" / _normalize_section_name(section)


def _section_key_facts(text: str, max_facts: int = 10, max_chars: int = 80) -> list[str]:
    if not text.strip():
        return []
    parts = re.split(r"[\n。！？!?；;]", text)
    facts = []
    for raw in parts:
        x = raw.strip()
        if not x:
            continue
        if len(x) > max_chars:
            x = x[: max_chars - 3] + "..."
        facts.append(x)
        if len(facts) >= max_facts:
            break
    return facts


def _compact_consistency_for_section(cm: dict[str, Any], section_stem: str) -> dict[str, Any]:
    q = consistency_mapper.query_by_section(cm, section_stem)
    out: dict[str, Any] = {}
    for k, items in q.items():
        out[k] = [{"id": i.get("id"), "statement": i.get("statement", "")} for i in items]
    return out


def _section_excerpt(text: str, limit_chars: int = 1200) -> str:
    if len(text) <= limit_chars:
        return text
    half = limit_chars // 2
    return text[:half] + "\n...\n" + text[-half:]


def build_write_cycle(root: Path, section: str, token_budget: int | None = None) -> dict[str, Any]:
    profile = load_json(root / "proposal_profile.json", DEFAULT_PROFILE)
    cm = consistency_mapper.load_map(root / "data/consistency_map.json")
    lit = load_json(root / "data/literature_index.json", {"metadata": {}, "entries": []})

    sec_path = _section_file(root, section)
    section_text = sec_path.read_text(encoding="utf-8") if sec_path.exists() else ""

    related_entities = _compact_consistency_for_section(cm, sec_path.stem)
    token_budget = token_budget or 4000

    literature_ctx = []
    if sec_path.stem.startswith("P1"):
        for e in lit.get("entries", [])[:20]:
            literature_ctx.append(
                {
                    "ref_number": e.get("ref_number"),
                    "title": e.get("title"),
                    "year": e.get("year"),
                    "role": e.get("role"),
                    "verified": e.get("verified"),
                }
            )

    return {
        "section": sec_path.name,
        "token_budget": token_budget,
        "token_plan": {
            "section_summary": int(token_budget * 0.4),
            "consistency": int(token_budget * 0.2),
            "literature": int(token_budget * 0.25) if sec_path.stem.startswith("P1") else 0,
            "system": token_budget
            - int(token_budget * 0.4)
            - int(token_budget * 0.2)
            - (int(token_budget * 0.25) if sec_path.stem.startswith("P1") else 0),
        },
        "section_excerpt": _section_excerpt(section_text),
        "section_key_facts": _section_key_facts(section_text),
        "related_consistency": related_entities,
        "literature_context": literature_ctx,
        "profile": {
            "mode": profile.get("mode"),
            "page_limit": profile.get("page_limit"),
            "word_targets": profile.get("word_targets", {}),
        },
    }


def load_view(root: Path, section: str | None, minimal: bool, global_load: bool) -> dict[str, Any]:
    state = load_json(root / "project_state.json", {})
    out: dict[str, Any] = {"state": state}

    if section:
        path = _section_file(root, section)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        out["section_name"] = path.name
        if minimal:
            cm = consistency_mapper.load_map(root / "data/consistency_map.json")
            out["section_key_facts"] = _section_key_facts(text)
            out["related_consistency"] = _compact_consistency_for_section(cm, path.stem)
        else:
            out["section"] = text

    if global_load:
        out["consistency"] = consistency_mapper.load_map(root / "data/consistency_map.json")
        out["literature_meta"] = load_json(root / "data/literature_index.json", {"metadata": {}}).get("metadata", {})
        out["profile"] = load_json(root / "proposal_profile.json", DEFAULT_PROFILE)

    if minimal:
        out["mode"] = "minimal"

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p_profile = sub.add_parser("profile")
    p_profile.add_argument("--json", required=True)

    p_load = sub.add_parser("load")
    p_load.add_argument("--section")
    p_load.add_argument("--minimal", action="store_true")
    p_load.add_argument("--global", dest="global_load", action="store_true")

    p_update = sub.add_parser("update")
    p_update.add_argument("--json", required=True)

    p_snap = sub.add_parser("snapshot")
    p_snap.add_argument("--name", required=True)

    p_roll = sub.add_parser("rollback")
    p_roll.add_argument("--snapshot", required=True)

    p_wc = sub.add_parser("word-count")
    p_wc.add_argument("--sections-dir", default="sections")

    p_pe = sub.add_parser("page-estimate")
    p_pe.add_argument("--sections-dir", default="sections")

    p_write = sub.add_parser("write-cycle")
    p_write.add_argument("--section", required=True)
    p_write.add_argument("--token-budget", type=int, default=4000)

    sub.add_parser("sync-all")

    p_review = sub.add_parser("self-review")
    p_review.add_argument("--sections-dir", default="sections")
    p_review.add_argument("--output", default="data/diagnosis_report.json")

    p_sync = sub.choices["sync-all"]
    p_sync.add_argument("--auto-fix", action="store_true")

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.cmd == "init":
        init_project(root)
        print(json.dumps({"ok": True, "root": str(root)}, ensure_ascii=False))
        return 0

    if args.cmd == "profile":
        patch = json.loads(args.json)
        current = load_json(root / "proposal_profile.json", DEFAULT_PROFILE)
        merged = deep_merge(current, patch)
        save_json(root / "proposal_profile.json", merged)
        append_history(root, "profile_update", patch)
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return 0

    if args.cmd == "load":
        print(json.dumps(load_view(root, args.section, args.minimal, args.global_load), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "update":
        patch = json.loads(args.json)
        state = load_json(root / "project_state.json", {})
        state = deep_merge(state, patch)
        state["updated_at"] = utc_now()
        save_json(root / "project_state.json", state)
        append_history(root, "state_update", patch)
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return 0

    if args.cmd == "snapshot":
        snap = do_snapshot(root, args.name)
        print(json.dumps({"ok": True, "snapshot": str(snap)}, ensure_ascii=False))
        return 0

    if args.cmd == "rollback":
        rollback(root, Path(args.snapshot))
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return 0

    if args.cmd == "word-count":
        data = word_counter.count_all(root / args.sections_dir)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "page-estimate":
        data = word_counter.count_all(root / args.sections_dir)
        print(word_counter.estimate_pages(data.get("__total__", 0)))
        return 0

    if args.cmd == "write-cycle":
        payload = build_write_cycle(root, args.section, token_budget=args.token_budget)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "sync-all":
        if getattr(args, "auto_fix", False):
            fix = _auto_fix_project(root)
        else:
            fix = {"fixed_count": 0, "fixed": []}
        status = sync_all(root)
        exists_ok = all(status["exists"].values())
        fresh_ok = all(status["fresh"].values()) if status["fresh"] else True

        semantic = status["semantic"]
        if semantic["strict_mode"]:
            semantic_ok = (
                (not semantic["cm_has_error"])
                and semantic["has_context_blocks"]
                and semantic["has_history"]
                and semantic["p1_verified"]
            )
        else:
            semantic_ok = semantic["has_context_blocks"] and semantic["has_history"]

        ok = exists_ok and fresh_ok and semantic_ok
        print(json.dumps({"ok": ok, **status, "semantic_ok": semantic_ok, "auto_fix": fix}, ensure_ascii=False, indent=2))
        return 0 if ok else 2

    if args.cmd == "self-review":
        profile = load_json(root / "proposal_profile.json", DEFAULT_PROFILE)
        report = diagnosis_engine.full_review(
            sections_dir=root / args.sections_dir,
            consistency_path=root / "data/consistency_map.json",
            index_path=root / "data/literature_index.json",
            p1_path=root / "sections/P1_立项依据.md",
            ref_path=root / "sections/REF_参考文献.md",
            page_limit=int(profile.get("page_limit", 30)),
        )
        out = root / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        append_history(root, "self_review", {"overall_grade": report["overall_grade"]})
        print(json.dumps({"ok": True, "output": str(out), "overall": report["overall_grade"]}, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

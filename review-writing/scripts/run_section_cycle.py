#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

WORKFLOW_VERSION = 2

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _gates_path():
    return Path("logs") / "workflow_gates.json"


def _manifest_path():
    return Path("logs") / "search_manifest.json"


def _checkpoint_path(section):
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in section)
    return Path("logs") / f"cycle_checkpoint_{safe}.json"


def _load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_gates():
    return _load_json(_gates_path(), {"round1_complete": False, "sections": {}})


def _save_gates(gates):
    _save_json(_gates_path(), gates)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_strategy_payload(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[GATE] Invalid search strategy JSON: {path} ({e})")
        raise SystemExit(2)
    return data


def _record_search_manifest(section, round_id, strategy_file, claims_file, resume):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow_version": WORKFLOW_VERSION,
        "section": section,
        "round": round_id,
        "resume": resume,
        "search_order": ["PubMed", "Semantic Scholar", "Google Scholar"],
        "strategy_file": strategy_file,
        "strategy_sha256": _sha256_file(strategy_file),
        "strategy": _load_strategy_payload(strategy_file),
    }
    if claims_file and os.path.exists(claims_file):
        entry["claims_file"] = claims_file
        entry["claims_sha256"] = _sha256_file(claims_file)

    with _workflow_lock():
        manifest = _load_json(_manifest_path(), [])
        if not isinstance(manifest, list):
            manifest = []
        manifest.append(entry)
        _save_json(_manifest_path(), manifest)


@contextmanager
def _workflow_lock(timeout=20):
    lock_path = Path("logs") / ".workflow.lock"
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
                    raise TimeoutError(f"workflow lock timeout after {timeout}s: {lock_path}")
                time.sleep(0.05)
        yield
    finally:
        if acquired and fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
        os.close(fd)


def _enforce_gate(round_id, section):
    gates = _load_gates()
    if round_id == 2 and not gates.get("round1_complete", False):
        print("[GATE] Round 2 blocked: Round 1 must be completed first.")
        raise SystemExit(2)
    if round_id == 3:
        section_state = gates.get("sections", {}).get(section, {})
        if not section_state.get("round2_complete", False):
            print(f"[GATE] Round 3 blocked for '{section}': Round 2 must be completed for this section.")
            raise SystemExit(2)


def _mark_gate_completed(round_id, section):
    with _workflow_lock():
        gates = _load_gates()
        if round_id == 1:
            gates["round1_complete"] = True
        elif round_id == 2:
            gates.setdefault("sections", {}).setdefault(section, {})["round2_complete"] = True
        elif round_id == 3:
            gates.setdefault("sections", {}).setdefault(section, {})["round3_complete"] = True
        _save_gates(gates)


def _load_resume_steps(section, round_id, resume):
    if not resume:
        return set(), None
    cp = _load_json(_checkpoint_path(section), {})
    if cp.get("status") not in ("failed", "running"):
        return set(), "[RESUME] No resumable checkpoint (status must be 'failed' or 'running'). Starting fresh."
    if cp.get("workflow_version") != WORKFLOW_VERSION:
        return (
            set(),
            f"[RESUME] Checkpoint workflow_version={cp.get('workflow_version')} "
            f"!= current={WORKFLOW_VERSION}. Starting fresh.",
        )
    if cp.get("section") != section or cp.get("round") != round_id:
        return (
            set(),
            f"[RESUME] Checkpoint target mismatch (section={cp.get('section')}, round={cp.get('round')}). "
            "Starting fresh.",
        )
    completed = cp.get("completed_steps", [])
    return set(completed if isinstance(completed, list) else []), None


def _prune_log_files(keep_snapshots=100, keep_checkpoints=20):
    logs_dir = Path("logs")
    removed = {"snapshots": 0, "checkpoints": 0}
    if not logs_dir.exists():
        return removed

    snap_dir = logs_dir / "snapshots"
    if snap_dir.exists():
        snaps = sorted(snap_dir.glob("state_snapshot_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in snaps[keep_snapshots:]:
            try:
                stale.unlink()
                removed["snapshots"] += 1
            except OSError:
                pass

    checkpoints = sorted(logs_dir.glob("cycle_checkpoint_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in checkpoints[keep_checkpoints:]:
        try:
            stale.unlink()
            removed["checkpoints"] += 1
        except OSError:
            pass

    return removed


def _write_checkpoint(section, round_id, status, current_step, completed_steps, payload_exists_before):
    payload = {
        "workflow_version": WORKFLOW_VERSION,
        "section": section,
        "round": round_id,
        "status": status,
        "current_step": current_step,
        "completed_steps": list(completed_steps),
        "payload_exists_before": payload_exists_before,
    }
    _save_json(_checkpoint_path(section), payload)


def main():
    parser = argparse.ArgumentParser(description="Run a token-safe section cycle for review-writing")
    parser.add_argument("section", help="Section identifier, e.g., intro or methods")
    parser.add_argument("--payload", default="state_update_payload.json", help="State update payload file")
    parser.add_argument("--skip-live", action="store_true", help="Skip online DOI/PMID checks")
    parser.add_argument("--round", type=int, choices=[1, 2, 3], default=2, help="Evidence round for matrix operations")
    parser.add_argument("--claims", default=None, help="Claims JSON file for round-2 claim binding")
    parser.add_argument(
        "--search-strategy",
        default=None,
        help="Path to section retrieval strategy JSON (queries, filters, time window); required for round-2 reproducibility.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from failed checkpoint for this section/round")
    parser.add_argument("--keep-snapshots", type=int, default=100, help="Retention count for snapshot files")
    parser.add_argument("--keep-checkpoints", type=int, default=20, help="Retention count for checkpoint files")
    args = parser.parse_args()

    section = args.section
    if args.round == 2 and not args.claims:
        print("[GATE] Round 2 requires --claims to bind section claims before completion.")
        raise SystemExit(2)
    if args.round == 2 and not args.search_strategy:
        print("[GATE] Round 2 requires --search-strategy for reproducible section retrieval.")
        raise SystemExit(2)
    if args.search_strategy and not os.path.exists(args.search_strategy):
        print(f"[GATE] Search strategy file not found: {args.search_strategy}")
        raise SystemExit(2)
    payload_exists_before = os.path.exists(args.payload)
    _enforce_gate(args.round, section)
    completed_steps, resume_msg = _load_resume_steps(section, args.round, args.resume)
    if resume_msg:
        print(resume_msg)
    if args.search_strategy:
        _record_search_manifest(section, args.round, args.search_strategy, args.claims, args.resume)

    steps = [
        ("load_state", ["python3", "scripts/state_manager.py", "load", "--section", section, "--minimal"]),
    ]
    if args.round == 1:
        steps.append(("matrix_round1_bootstrap", ["python3", "scripts/matrix_manager.py", "bootstrap", "--round", "1"]))
    elif args.round == 2 and args.claims:
        steps.append(
            (
                "matrix_round2_bind_claims",
                [
                    "python3",
                    "scripts/matrix_manager.py",
                    "bind-claims",
                    "--section",
                    section,
                    "--claims",
                    args.claims,
                    "--fail-on-no-update",
                ],
            )
        )
    elif args.round == 3:
        steps.append(("matrix_round3_mark", ["python3", "scripts/matrix_manager.py", "mark-round3", "--section", section]))

    audit_cmd = ["python3", "scripts/matrix_manager.py", "audit", "--section", section]
    if args.round in (2, 3):
        audit_cmd.append("--fail-on-gap")
    steps.append(("matrix_audit", audit_cmd))
    if payload_exists_before:
        steps.append(("state_update", ["python3", "scripts/state_manager.py", "update", args.payload]))
    steps.append(("state_compact", ["python3", "scripts/state_manager.py", "compact"]))
    steps.append(("state_snapshot", ["python3", "scripts/state_manager.py", "snapshot"]))

    validate_cmd = ["python3", "scripts/validate_citations.py", "--fail-on-orphan"]
    if not args.skip_live:
        validate_cmd += ["--live", "--live-used-only", "--fail-on-live"]
    steps.append(("validate_citations", validate_cmd))
    steps.append(("check_citation_sequence", ["python3", "scripts/check_global_citation_sequence.py"]))
    if args.round == 3:
        steps.append(("final_consistency_check", ["python3", "scripts/final_consistency_check.py", "--fail-on-gap"]))

    if not payload_exists_before:
        print(f"[INFO] No payload found at {args.payload}; skipping state update")

    try:
        for step_name, cmd in steps:
            if step_name in completed_steps:
                print(f"[RESUME] skipping completed step: {step_name}")
                continue
            _write_checkpoint(section, args.round, "running", step_name, completed_steps, payload_exists_before)
            run(cmd)
            completed_steps.add(step_name)
        _write_checkpoint(section, args.round, "completed", "done", completed_steps, payload_exists_before)
    except Exception:
        _write_checkpoint(section, args.round, "failed", step_name, completed_steps, payload_exists_before)
        raise

    _mark_gate_completed(args.round, section)
    pruned = _prune_log_files(args.keep_snapshots, args.keep_checkpoints)

    summary = {
        "section": section,
        "payload_used": payload_exists_before,
        "live_validation": not args.skip_live,
        "round": args.round,
        "resume": args.resume,
        "checkpoint": str(_checkpoint_path(section)),
        "gates_file": str(_gates_path()),
        "log_pruned": pruned,
        "status": "ok",
    }
    print("Cycle Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

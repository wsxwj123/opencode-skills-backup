#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _gates_path():
    return Path("logs") / "workflow_gates.json"


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
        return set()
    cp = _load_json(_checkpoint_path(section), {})
    if cp.get("status") not in ("failed", "running"):
        return set()
    if cp.get("section") != section or cp.get("round") != round_id:
        return set()
    completed = cp.get("completed_steps", [])
    return set(completed if isinstance(completed, list) else [])


def _write_checkpoint(section, round_id, status, current_step, completed_steps, payload_exists_before):
    payload = {
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
    parser.add_argument("--resume", action="store_true", help="Resume from failed checkpoint for this section/round")
    args = parser.parse_args()

    section = args.section
    payload_exists_before = os.path.exists(args.payload)
    _enforce_gate(args.round, section)
    completed_steps = _load_resume_steps(section, args.round, args.resume)

    steps = [
        ("load_state", ["python3", "scripts/state_manager.py", "load", "--section", section, "--minimal"]),
    ]
    if args.round == 1:
        steps.append(("matrix_round1_bootstrap", ["python3", "scripts/matrix_manager.py", "bootstrap", "--round", "1"]))
    elif args.round == 2 and args.claims:
        steps.append(
            (
                "matrix_round2_bind_claims",
                ["python3", "scripts/matrix_manager.py", "bind-claims", "--section", section, "--claims", args.claims],
            )
        )
    elif args.round == 3:
        steps.append(("matrix_round3_mark", ["python3", "scripts/matrix_manager.py", "mark-round3", "--section", section]))

    steps.append(("matrix_audit", ["python3", "scripts/matrix_manager.py", "audit", "--section", section]))
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

    summary = {
        "section": section,
        "payload_used": payload_exists_before,
        "live_validation": not args.skip_live,
        "round": args.round,
        "resume": args.resume,
        "checkpoint": str(_checkpoint_path(section)),
        "gates_file": str(_gates_path()),
        "status": "ok",
    }
    print("Cycle Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

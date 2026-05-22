#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _add_issue(report, level, code, message):
    report["issues"].append({"level": level, "code": code, "message": message})


def run_preflight(project_root):
    root = Path(project_root)
    report = {
        "project_root": str(root.resolve()),
        "issues": [],
    }

    required_dirs = ["drafts", "data", "logs", "figures"]
    for rel in required_dirs:
        p = root / rel
        if not p.exists() or not p.is_dir():
            _add_issue(report, "error", "missing_dir", f"Missing directory: {rel}")

    storyline_md = root / "storyline.md"
    storyline_json = root / "storyline.json"
    if not storyline_md.exists() and not storyline_json.exists():
        _add_issue(report, "error", "missing_storyline", "Need storyline.md or storyline.json")

    index_path = root / "data" / "literature_index.json"
    if not index_path.exists():
        _add_issue(report, "error", "missing_index", "Missing data/literature_index.json")
    else:
        payload, err = _read_json(index_path)
        if err:
            _add_issue(report, "error", "invalid_index_json", f"Invalid literature_index.json: {err}")
        elif not isinstance(payload, list):
            _add_issue(report, "error", "invalid_index_type", "literature_index.json must be a list")

    matrix_canonical = root / "data" / "synthesis_matrix.json"
    matrix_legacy = root / "data" / "literature_matrix.json"

    if not matrix_canonical.exists() and not matrix_legacy.exists():
        _add_issue(report, "error", "missing_matrix", "Need data/synthesis_matrix.json (canonical matrix)")
    elif matrix_canonical.exists() and matrix_legacy.exists():
        c_text = matrix_canonical.read_text(encoding="utf-8")
        l_text = matrix_legacy.read_text(encoding="utf-8")
        if c_text != l_text:
            _add_issue(
                report,
                "error",
                "matrix_split_brain",
                "Both synthesis_matrix.json and literature_matrix.json exist with different content",
            )
        else:
            _add_issue(
                report,
                "warning",
                "matrix_duplicate",
                "Both matrix files exist with identical content; keep only synthesis_matrix.json",
            )
    elif matrix_legacy.exists() and not matrix_canonical.exists():
        _add_issue(
            report,
            "warning",
            "legacy_matrix_only",
            "Only data/literature_matrix.json exists; migrate to data/synthesis_matrix.json",
        )

    logs_dir = root / "logs"
    if logs_dir.exists():
        probe = logs_dir / ".preflight_write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except Exception as e:  # noqa: BLE001
            _add_issue(report, "error", "logs_not_writable", f"logs/ not writable: {e}")

    for lock_name in (".state_manager.lock", ".matrix.lock", ".workflow.lock"):
        lock_path = logs_dir / lock_name
        if lock_path.exists():
            _add_issue(report, "warning", "lock_present", f"Lock file present: logs/{lock_name}")

    errors = [x for x in report["issues"] if x["level"] == "error"]
    warnings = [x for x in report["issues"] if x["level"] == "warning"]
    report["summary"] = {
        "error_count": len(errors),
        "warning_count": len(warnings),
        "status": "ok" if not errors else "failed",
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Preflight checks for review-writing project structure and consistency")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    report = run_preflight(args.project_root)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    errors = report["summary"]["error_count"]
    warnings = report["summary"]["warning_count"]
    should_fail = (args.fail_on_error and errors > 0) or (args.fail_on_warning and warnings > 0)
    if should_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

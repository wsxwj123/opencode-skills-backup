#!/usr/bin/env python3
"""vendored 副本一致性门:跑 sync_vendored.py --check,任何缺失/漂移即 fail。

进 run_all_tests 后,谁改了 _shared 真源忘了铺、或手改了某技能副本,这里立刻红。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SYNC = Path(__file__).resolve().parent / "sync_vendored.py"


def _check_registry_full_table() -> list[str]:
    """裁决7:每份 gate_registry.json 必须是完整 8 技能全表。裁剪过的 registry
    会让后装技能把先装技能的条目覆没(部署是整表覆盖)。真源与全部副本都查。"""
    import json
    shared = Path(__file__).resolve().parent
    skills_root = shared.parent
    expected = {
        "general-sci-writing", "review-writing", "nsfc-proposal", "sci2doc",
        "revise-sci", "reviewer-response-sci", "reviewer-simulator", "polish-sci",
    }
    problems = []
    candidates = [shared / "gate_registry.json"] + [
        skills_root / s / "scripts" / "gate_registry.json" for s in sorted(expected)]
    for p in candidates:
        if not p.is_file():
            continue  # 缺失由 md5 check 报
        try:
            keys = set(json.loads(p.read_text(encoding="utf-8")).get("skills", {}))
        except Exception:
            problems.append(f"registry 损坏: {p}")
            continue
        if keys != expected:
            problems.append(f"registry 非全表: {p} 缺 {sorted(expected - keys)}")
    return problems


def main() -> int:
    proc = subprocess.run(
        [sys.executable or "python3", str(SYNC), "--check"],
        capture_output=True, text=True, timeout=60,
    )
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print("FAIL: vendored 副本与 _shared 真源不一致(见上方明细)", file=sys.stderr)
        return 1
    reg_problems = _check_registry_full_table()
    if reg_problems:
        for p in reg_problems:
            print(f"  - {p}")
        print("FAIL: gate_registry 全表断言未过", file=sys.stderr)
        return 1
    print("OK: vendored consistency + registry 全表")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

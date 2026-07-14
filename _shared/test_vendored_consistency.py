#!/usr/bin/env python3
"""vendored 副本一致性门:跑 sync_vendored.py --check,任何缺失/漂移即 fail。

进 run_all_tests 后,谁改了 _shared 真源忘了铺、或手改了某技能副本,这里立刻红。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SYNC = Path(__file__).resolve().parent / "sync_vendored.py"


def main() -> int:
    proc = subprocess.run(
        [sys.executable or "python3", str(SYNC), "--check"],
        capture_output=True, text=True, timeout=60,
    )
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print("FAIL: vendored 副本与 _shared 真源不一致(见上方明细)", file=sys.stderr)
        return 1
    print("OK: vendored consistency")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""学术技能测试 suite 运行器(stdlib-only,跨平台)。

背景:8 个学术技能各自的 `test_*.py` 是自包含 assert 脚本(靠 `python3 <file>` 跑),
从未接入统一 suite;且有 7 个同名 `test_format_contract.py`,`pytest` 整体收集会因
basename 冲突失败。本 runner 绕开 pytest:发现所有 `test_*.py`,逐个用独立
subprocess 跑(一次一个,无 basename 冲突),汇总 pass/fail,任一失败 → exit 1。

用法:
  python3 _shared/run_all_tests.py            # 跑全部技能 + _shared 的 test_*.py
  python3 _shared/run_all_tests.py --skill nsfc-proposal   # 只跑某技能
  python3 _shared/run_all_tests.py -q         # 只打摘要与失败项

判定:子进程退出码 0 = pass,非 0 = fail。断言式脚本 assert 失败会抛 AssertionError
→ 非 0 退出,被正确记为 fail。空文件/无断言脚本退出 0,记 pass(runner 不臆测其是否
真跑了断言,仅忠实反映退出码)。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _skills_root() -> Path:
    # 本文件在 skills/_shared/ → parent.parent = skills/
    return Path(__file__).resolve().parent.parent


def discover_tests(root: Path, skill: str | None) -> list[Path]:
    tests: list[Path] = []
    # _shared 自身的 test_*.py
    if skill is None:
        tests += sorted((root / "_shared").glob("test_*.py"))
    # 各技能 scripts/ 下的 test_*.py
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
            continue
        if skill and skill_dir.name != skill:
            continue
        scripts = skill_dir / "scripts"
        if scripts.is_dir():
            tests += sorted(scripts.glob("test_*.py"))
    # 去重(保序)
    seen: set[str] = set()
    uniq: list[Path] = []
    for t in tests:
        rp = str(t.resolve())
        if rp not in seen:
            seen.add(rp)
            uniq.append(t)
    return uniq


def run_one(test: Path, timeout: int = 120) -> tuple[bool, str]:
    """跑单个测试,返回 (passed, tail_output)。"""
    try:
        proc = subprocess.run(
            [sys.executable or "python3", str(test)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(test.parent),
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT (>{timeout}s)"
    except Exception as e:  # noqa: BLE001
        return False, f"RUN-ERROR: {e}"
    if proc.returncode == 0:
        return True, ""
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return False, "\n    ".join(tail)


def main() -> int:
    ap = argparse.ArgumentParser(description="学术技能测试 suite 运行器")
    ap.add_argument("--skill", default=None, help="只跑某技能(目录名)")
    ap.add_argument("-q", "--quiet", action="store_true", help="只打摘要与失败项")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    root = _skills_root()
    tests = discover_tests(root, args.skill)
    if not tests:
        print("未发现任何 test_*.py")
        return 0

    passed, failed = [], []
    for t in tests:
        ok, tail = run_one(t, args.timeout)
        rel = t.relative_to(root)
        if ok:
            passed.append(rel)
            if not args.quiet:
                print(f"  PASS  {rel}")
        else:
            failed.append((rel, tail))
            print(f"  FAIL  {rel}")
            if tail:
                print(f"    {tail}")

    print("\n" + "=" * 60)
    print(f"测试 suite: {len(passed)}/{len(tests)} 通过, {len(failed)} 失败")
    if failed:
        print("失败项:")
        for rel, _ in failed:
            print(f"  - {rel}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

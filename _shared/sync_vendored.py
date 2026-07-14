#!/usr/bin/env python3
"""vendored 纯库同步器:_shared/ 为唯一真源,按 MANIFEST 铺进各技能 scripts/。

背景:8 个学术技能要能被单独分发(GUI/ZIP 只拉单个技能目录,不带同级 _shared/),
故纯库(stdlib-only、零互 import)vendored 进各技能 scripts/ 同目录使用;_shared/
仍是开发真源。多份拷贝的漂移由本脚本 --check 兜住(进 run_all_tests,漂移即测试红)。

用法:
  python3 _shared/sync_vendored.py --check   # md5 比对,缺失/不一致列明细 exit 1
  python3 _shared/sync_vendored.py --sync    # 从 _shared 铺开覆盖各技能副本

规矩:
- MANIFEST 是唯一分发清单;新增共享库/新增消费技能,只改这里。
- 只 vendor 纯库(.py 单文件、stdlib-only);测试文件(test_*.py)绝不 vendor
  (run_all_tests 会重复发现并二次执行)。
- 运行时产物(hook_heartbeat.json 等)绝不 vendor。
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent.parent
SHARED = Path(__file__).resolve().parent

ALL8 = [
    "general-sci-writing", "review-writing", "nsfc-proposal", "sci2doc",
    "revise-sci", "reviewer-response-sci", "reviewer-simulator", "polish-sci",
]

# 源文件(_shared/ 下) → 消费技能列表(拷到 <skill>/scripts/ 同名)
MANIFEST: dict[str, list[str]] = {
    # 跨会话接续:全部 8 家(env_preflight 打印 RESUME/LOG_CMD)
    "session_journal.py": ALL8,
    # 引文核证:6 家(polish/reviewer-simulator 不用)
    "citation_claim_check.py": [
        "general-sci-writing", "nsfc-proposal", "sci2doc",
        "review-writing", "revise-sci", "reviewer-response-sci",
    ],
    # 结构签字:Phase A 时仅 4 家 confirm 侧;Phase B 起它是门禁四件套部署源成员,
    # 8 家全铺(installer 从自身同目录取四件套部署到 ~/.claude/academic-gate/)
    "structure_signoff_gate.py": ALL8,
    # 门禁四件套其余三件(Phase B):每技能自带安装能力,装出全局唯一钩子。
    # 心跳 hook_heartbeat.json 是运行时产物,绝不入 MANIFEST。
    "academic_gate_hook.py": ALL8,
    "install_gate_hook.py": ALL8,
    "gate_registry.json": ALL8,
    # 既有 vendored,纳管防漂
    "md_runs.py": ["revise-sci", "polish-sci", "sci2doc"],
    "citation_guard_core.py": [
        "general-sci-writing", "nsfc-proposal", "review-writing", "sci2doc",
        "revise-sci", "reviewer-response-sci", "reviewer-simulator",
    ],
}


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def iter_targets():
    """生成 (源Path, 目标Path, 技能名)。"""
    for src_name, skills in MANIFEST.items():
        src = SHARED / src_name
        for skill in skills:
            yield src, SKILLS_ROOT / skill / "scripts" / src_name, skill


def do_check() -> int:
    problems: list[str] = []
    missing_src: set[str] = set()
    for src, dst, skill in iter_targets():
        if not src.is_file():
            if src.name not in missing_src:
                missing_src.add(src.name)
                problems.append(f"真源缺失: _shared/{src.name}")
            continue
        if not dst.is_file():
            problems.append(f"缺失: {skill}/scripts/{src.name}")
        elif _md5(src) != _md5(dst):
            problems.append(f"漂移: {skill}/scripts/{src.name} (md5 != _shared)")
    if problems:
        print(f"vendored 一致性检查 FAIL,{len(problems)} 项:")
        for p in problems:
            print(f"  - {p}")
        print("修复: python3 _shared/sync_vendored.py --sync")
        return 1
    n = sum(len(v) for v in MANIFEST.values())
    print(f"vendored 一致性检查 OK({len(MANIFEST)} 库 × 共 {n} 份副本,全部与 _shared 真源一致)")
    return 0


def do_sync() -> int:
    copied = 0
    for src, dst, skill in iter_targets():
        if not src.is_file():
            print(f"跳过(真源缺失): _shared/{src.name}", file=sys.stderr)
            continue
        if dst.is_file() and _md5(src) == _md5(dst):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"铺: {skill}/scripts/{src.name}")
        copied += 1
    print(f"同步完成,更新 {copied} 份")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="vendored 纯库同步/校验(_shared 为真源)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="md5 校验,不一致 exit 1")
    g.add_argument("--sync", action="store_true", help="从 _shared 铺开覆盖")
    args = ap.parse_args()
    return do_check() if args.check else do_sync()


if __name__ == "__main__":
    raise SystemExit(main())

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
    # 8 家全铺(installer 从自身同目录取四件套部署到 ~/.claude/academic-gate/)。
    # 2026-07-28 起 academic-gate 插件目录也是消费方(@skills-dir 插件,钩子由
    # Claude Code 启动时自动加载,不依赖 AI 自觉);它不带 install_gate_hook.py。
    "structure_signoff_gate.py": ALL8 + ["academic-gate"],
    # 门禁四件套其余三件(Phase B):每技能自带安装能力,装出全局唯一钩子。
    # 心跳 hook_heartbeat.json 是运行时产物,绝不入 MANIFEST。
    "academic_gate_hook.py": ALL8 + ["academic-gate"],
    "install_gate_hook.py": ALL8,
    "gate_registry.json": ALL8 + ["academic-gate"],
    # context-guard 判定库:三个钩子(喂/拦/Bash)唯一共用的判定实现,也是
    # academic_gate_hook.py 的 import 依赖 → 后者铺到哪它就必须铺到哪(含 legacy
    # 装法的部署源,见 install_gate_hook.BUNDLE),否则拦层一 import 就炸。
    "context_guard_core.py": ALL8 + ["academic-gate"],
    # 喂层与 Bash 守卫只由插件执行(legacy settings.json 装法不挂它们),故单成员分区。
    "context_feed_hook.py": ["academic-gate"],
    "bash_guard_hook.py": ["academic-gate"],
    # 既有 vendored,纳管防漂
    # 2026-07-28 补：这三个此前**三道守卫全无**（MANIFEST/L4/CI 都没有），
    # 改了漂了不会有人发现。实测各家 md5 全一致，登记只冻结现状、不改行为。
    # proofread.py 是其中最大的（30.8KB×6家），也是最该守的。
    "proofread.py": ["general-sci-writing", "polish-sci", "review-writing",
                     "reviewer-response-sci", "reviewer-simulator", "revise-sci"],
    "git_checkpoint.py": ["general-sci-writing", "nsfc-proposal", "sci2doc"],
    "extract_docx_images.py": ["polish-sci", "revise-sci", "sci2doc"],
    "md_runs.py": ["revise-sci", "polish-sci", "sci2doc"],
    "citation_guard_core.py": [
        "general-sci-writing", "nsfc-proposal", "review-writing", "sci2doc",
        "revise-sci", "reviewer-response-sci", "reviewer-simulator",
    ],
    # 撰写编排核心:撰写四家
    "delegate_write_core.py": [
        "general-sci-writing", "review-writing", "nsfc-proposal", "sci2doc",
    ],
    # 原子化拆分三件:review + nsfc 两家
    "extract_headings.py": ["review-writing", "nsfc-proposal"],
    "split_headings.py": ["review-writing", "nsfc-proposal"],
    "split_audit.py": ["review-writing", "nsfc-proposal"],
    # 审稿一致性(数值 / xref+M):reviewer-sim + 撰写三家;
    # manuscript_index 多一家 polish-sci,且是 structure_outline/methods_terms 的
    # import 依赖,必须同版本,否则另三家跟着错。
    "numeric_candidates.py": [
        "general-sci-writing", "sci2doc", "revise-sci", "reviewer-simulator",
    ],
    # structure_outline 多两家 review-writing / nsfc-proposal(xref 推广第四、五家,
    # 只挂 xref、不挂 M,故 methods_terms 不铺);manuscript_index 是它的 import 依赖,
    # 跟着扩——只搬主文件会 ModuleNotFoundError。
    "structure_outline.py": [
        "general-sci-writing", "sci2doc", "revise-sci", "reviewer-simulator",
        "review-writing", "nsfc-proposal",
    ],
    "methods_terms.py": [
        "general-sci-writing", "sci2doc", "revise-sci", "reviewer-simulator",
    ],
    "manuscript_index.py": [
        "general-sci-writing", "sci2doc", "revise-sci", "reviewer-simulator",
        "polish-sci", "review-writing", "nsfc-proposal",
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
    # 漏登记:文件已 vendored 进某技能、_shared 里也有真源,却不在 MANIFEST。
    # 这类副本无人守漂——本检查存在的意义就是不让清单落后于现实。
    for skill in ALL8:
        for dst in sorted((SKILLS_ROOT / skill / "scripts").glob("*.py")):
            if (SHARED / dst.name).is_file() and skill not in MANIFEST.get(dst.name, []):
                problems.append(f"漏登记: {skill}/scripts/{dst.name} 未列入 MANIFEST")
    if problems:
        print(f"vendored 一致性检查 FAIL,{len(problems)} 项:")
        for p in problems:
            print(f"  - {p}")
        print("修复: 漂移/缺失 → python3 _shared/sync_vendored.py --sync;"
              "漏登记 → 把该技能补进本文件 MANIFEST")
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

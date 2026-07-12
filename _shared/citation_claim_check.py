#!/usr/bin/env python3
"""引文核证（共享，8 技能通用）——判"引用是否真支持它挂的论点"，而非只验真实性。

定位：矩阵驱动写作的一环。写某节前建"观点↔引文"矩阵时，对每个观点↔引用，拿该引文
**检索到的真实 abstract**（不看可编的 key_finding）判支撑度。承重论点句 contradict/无法判定
→ fail-closed，逼人工处理；承重句还须逐条人工确认(user_confirmed)。背景陈述句只在表里
批量呈现、不逐条阻断。**不含 MCP、不碰 hook**——取 abstract 那半走各技能工作流子代理。

CLI:
  python citation_claim_check.py --root <project_root> [--evidence claim_evidence.json]
  python citation_claim_check.py --evidence <path>            # 直接指定

输入 claim_evidence.json：list，每条
  {section, claim_sentence, is_load_bearing(bool), ref_id,
   retrieved_abstract, verdict∈support/weak/contradict/unknown,
   evidence_quote, user_confirmed(bool)}

行为：
  - 渲染面向用户的矩阵表（stdout 上半）。
  - fail-closed(exit 2) 若任一**承重句**：verdict∈{contradict,unknown} / 缺 retrieved_abstract
    / verdict∈{support,weak} 但 user_confirmed!=true（承重句必须人工逐条确认）。
  - 背景句的 contradict/weak：表里标红提示，不阻断（走批量确认）。
  - stdout 末行输出机器可读 JSON 摘要 {ok, blockers:[...], counts:{...}}。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_VERDICTS = {"support", "weak", "contradict", "unknown"}


def _load_evidence(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    raise ValueError("claim_evidence 必须是 list 或 {rows:[...]}")


def _row_blockers(row: dict) -> list[str]:
    """返回该行的阻断原因（空=不阻断）。只有承重句会产生阻断。"""
    if not row.get("is_load_bearing"):
        return []
    problems: list[str] = []
    ref = row.get("ref_id") or "?"
    verdict = row.get("verdict")
    if not (row.get("retrieved_abstract") or "").strip():
        problems.append(f"[{ref}] 承重句但未取到被引文献摘要，无法核证（需人工或重取摘要）")
        return problems  # 没摘要就没法谈 verdict
    if verdict not in VALID_VERDICTS:
        problems.append(f"[{ref}] verdict 非法/缺失：{verdict!r}")
    elif verdict in {"contradict", "unknown"}:
        problems.append(f"[{ref}] 承重论点被判 {verdict}——引文不支持/无法判定该论点，禁止照此下笔")
    if verdict in {"support", "weak"} and row.get("user_confirmed") is not True:
        problems.append(f"[{ref}] 承重句须逐条人工确认（user_confirmed 尚未为 true）")
    return problems


VERDICT_CN = {"support": "✅支持", "weak": "🟡弱相关", "contradict": "❌不支持", "unknown": "❔无法判定"}


def _render_table(rows: list[dict]) -> str:
    lines = ["## 引文核证矩阵（观点 ↔ 引文 ↔ 是否真支持）", "",
             "| 承重 | 章节 | 论点句 | 引文 | 判定 | 摘要证据句 | 已确认 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lb = "🔴承重" if r.get("is_load_bearing") else "背景"
        claim = (r.get("claim_sentence") or "").replace("|", "\\|")[:60]
        ref = str(r.get("ref_id") or "?")
        verdict = VERDICT_CN.get(r.get("verdict"), str(r.get("verdict")))
        ev = (r.get("evidence_quote") or "").replace("|", "\\|")[:60]
        conf = "是" if r.get("user_confirmed") is True else "—"
        sec = str(r.get("section") or "").replace("|", "\\|")[:16]
        lines.append(f"| {lb} | {sec} | {claim} | {ref} | {verdict} | {ev} | {conf} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="引文核证：判引文是否真支持论点")
    ap.add_argument("--root", default=None)
    ap.add_argument("--evidence", default=None)
    args = ap.parse_args()

    if args.evidence:
        ev_path = Path(args.evidence)
    elif args.root:
        ev_path = Path(args.root) / "claim_evidence.json"
    else:
        print("需 --root 或 --evidence")
        return 2

    if not ev_path.is_file():
        print(json.dumps({"ok": False, "error": "claim_evidence_missing",
                          "message": f"未找到 {ev_path}——先建本节观点↔引文矩阵并取真摘要核证"},
                         ensure_ascii=False))
        return 2

    try:
        rows = _load_evidence(ev_path)
    except Exception as e:
        print(json.dumps({"ok": False, "error": "bad_evidence", "message": str(e)}, ensure_ascii=False))
        return 2

    print(_render_table(rows))
    print("")

    blockers: list[str] = []
    for r in rows:
        blockers.extend(_row_blockers(r))

    load_bearing = sum(1 for r in rows if r.get("is_load_bearing"))
    contradict = sum(1 for r in rows if r.get("verdict") == "contradict")
    summary = {
        "ok": not blockers,
        "blockers": blockers,
        "counts": {"total": len(rows), "load_bearing": load_bearing, "contradict": contradict},
    }
    if blockers:
        print("🔴 引文核证未过——承重论点存在下列问题，禁止照此下笔（改引文/改论点/补人工确认后重跑）：")
        for b in blockers:
            print(f"  - {b}")
        print("")
    else:
        print("✅ 引文核证通过：承重论点均有真摘要支撑且已人工确认（背景句请在上表批量核对）。")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())

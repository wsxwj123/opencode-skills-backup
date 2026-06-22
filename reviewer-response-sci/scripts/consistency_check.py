#!/usr/bin/env python3
"""Consistency checks across atomic response units."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_unit_text(unit: dict) -> str:
    c = unit.get("content", {})
    parts = [
        c.get("response_en", ""),
        c.get("revised_excerpt_en", ""),
        " ".join(c.get("notes_core_zh", [])),
        " ".join(c.get("notes_support_zh", [])),
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Consistency checker for reviewer-response units")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--rules", default="")
    parser.add_argument("--fail-on-conflict", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root)
    rules_path = Path(args.rules) if args.rules else Path(__file__).resolve().parents[1] / "references" / "consistency-rules.json"
    rules = read_json(rules_path)

    units = [read_json(p) for p in sorted((root / "units").glob("*.json"))]
    text_by_unit = {u.get("unit_id", ""): collect_unit_text(u) for u in units}
    merged_text = "\n".join(text_by_unit.values())

    warnings: list[str] = []
    conflicts: list[str] = []

    for pat in rules.get("forbidden_phrase_patterns", []):
        if re.search(re.escape(pat), merged_text, flags=re.IGNORECASE):
            conflicts.append(f"Forbidden phrase detected: {pat}")

    for term_set in rules.get("conflict_term_sets", []):
        present = [t for t in term_set if re.search(re.escape(t), merged_text, flags=re.IGNORECASE)]
        if len(present) >= 2:
            conflicts.append(f"Conflicting terms co-exist: {', '.join(present)}")

    for marker in rules.get("required_markers", []):
        if marker not in merged_text:
            warnings.append(f"Required marker not found globally: {marker}")

    # --- Commitment ↔ Landing-point consistency check (WARN level) ---
    # Verify that action verbs promised in response_en (added/clarified/revised + object)
    # can be found as corresponding entries in modification_actions or revised_excerpt_en
    # of the same unit. Mismatch → WARN (non-blocking).
    ACTION_VERB_RE = re.compile(
        r"\b(we (?:added|clarified|revised|corrected|updated|included|removed|expanded|moved|replaced)"
        r"(?: [\w]+){0,5})",
        re.IGNORECASE,
    )
    # Signal that the promise claims newly added substantive content (a new
    # experiment / dataset / figure / analysis), not a mere wording tweak.
    # Only these promises get the stricter landing-evidence requirement below.
    SUBSTANTIVE_ADD_RE = re.compile(
        r"\b(?:added|new|newly|additional|included|incorporated|expanded|performed|conducted|carried out)\b"
        r".{0,40}?"
        r"\b(?:experiment|experiments|assay|assays|analysis|analyses|dataset|datasets|data|"
        r"figure|figures|panel|panels|table|tables|cohort|sample|samples|replicate|replicates|"
        r"measurement|measurements|test|tests|model|models|group|groups|control|controls)\b",
        re.IGNORECASE,
    )
    for u in units:
        if u.get("section") == "email":
            continue
        uid = u.get("unit_id", "?")
        c = u.get("content", {})
        response_en = c.get("response_en", "")
        mod_actions = c.get("modification_actions", [])
        revised = c.get("revised_excerpt_en", "")

        # Skip if unit is still a placeholder (not yet filled by AI)
        if "AI_FILL_REQUIRED" in response_en or "【待AI" in response_en:
            continue

        promises = ACTION_VERB_RE.findall(response_en)
        for promise in promises:
            promise_lower = promise.lower()
            kws = [kw for kw in promise_lower.split()[1:3] if len(kw) > 3]

            # 1) English keyword match in action reason/target or revised excerpt
            found_in_actions_en = bool(kws) and any(
                any(kw in (a.get("reason", "") + a.get("target", "")).lower() for kw in kws)
                for a in mod_actions
            )
            found_in_revised_en = bool(kws) and any(kw in revised.lower() for kw in kws)

            # 2) Chinese fields: if modification_actions has a non-placeholder action_type
            #    and response_zh / notes are filled, treat the unit as consistent.
            #    This handles bilingual units where reason/target are written in Chinese.
            response_zh = c.get("response_zh", "")
            notes_core = c.get("notes_core_zh", [])
            zh_fields_filled = (
                response_zh
                and "【待AI" not in response_zh
                and "AI_FILL_REQUIRED" not in response_zh
            )
            actions_have_type = any(
                a.get("action_type", "").strip() not in {"", "修改"}
                or a.get("reason", "").strip() not in {"", "【待AI填写：添加/删除/修改及原因】"}
                for a in mod_actions
            )
            zh_fallback_ok = zh_fields_filled and actions_have_type

            # 3) Tighten the Chinese fallback for "newly added substantive content"
            #    promises. Filled-and-non-placeholder is too weak: a promise to add
            #    a new experiment must leave an add-landing somewhere, not just a
            #    non-empty Chinese field on an unrelated caption tweak. We require
            #    the landing point (action_type / target / reason / revised excerpt,
            #    EN or ZH) to carry an addition signal; a landing that is purely a
            #    wording / unit / typo fix carries none and is downgraded to WARN.
            #    Non-substantive promises (clarified/corrected/updated wording) keep
            #    the original lenient fallback so genuine bilingual matches do not
            #    become false positives.
            if zh_fallback_ok and SUBSTANTIVE_ADD_RE.search(promise):
                revised_zh = c.get("revised_excerpt_zh", "")
                landing_text = " ".join(
                    [a.get("action_type", "") + a.get("target", "") + a.get("reason", "") for a in mod_actions]
                    + [revised, revised_zh]
                ).lower()
                has_add_action = any(a.get("action_type", "").strip() == "添加" for a in mod_actions)
                landing_has_add_signal = bool(
                    re.search(
                        r"添加|新增|新加|增设|补充|加入|纳入|added|new\b|newly|additional|"
                        r"included|incorporated|expanded|extra",
                        landing_text,
                    )
                )
                zh_fallback_ok = has_add_action or landing_has_add_signal

            found = (
                found_in_actions_en
                or found_in_revised_en
                or zh_fallback_ok
            )

            # A promise lives in response_en independent of whether revised_excerpt_en
            # is "无": a unit often promises (e.g.) "added a new control" while landing
            # the change in SI/main text outside the excerpt and leaving revised="无".
            # The landing point is therefore sought in modification_actions / Chinese
            # fields (all folded into `found`), NOT gated on revised being non-empty.
            # revised="无" no longer exempts the promise from the check.
            if not found:
                warnings.append(
                    f"[{uid}] response_en promises '{promise}' but no matching entry found "
                    f"in modification_actions, revised_excerpt_en, or Chinese fields"
                )

    if conflicts:
        print("CONSISTENCY_CHECK: FAIL")
        for c in conflicts:
            print(f"- {c}")
        if warnings:
            for w in warnings:
                print(f"- WARN: {w}")
        return 2 if args.fail_on_conflict else 1

    print("CONSISTENCY_CHECK: PASS")
    if warnings:
        for w in warnings:
            print(f"- WARN: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

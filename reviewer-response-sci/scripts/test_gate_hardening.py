#!/usr/bin/env python3
"""Self-checks for the漏回/绕过 gate hardening.

Covers:
- consistency_check.py: substantive-addition promise with no landing → FAIL;
  the widened verb table catches `we have added` / `we performed`;
  a wording-only promise with no landing stays a non-blocking WARN.
- delegate_review.py pack --comments: original reviewer letter is embedded
  verbatim into the blind-review task package.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def _unit(uid: str, response_en: str, actions=None, revised="无"):
    return {
        "unit_id": uid,
        "section": "major",
        "content": {
            "response_en": response_en,
            "response_zh": "已处理。",
            "revised_excerpt_en": revised,
            "revised_excerpt_zh": "无",
            "modification_actions": actions or [],
        },
    }


def _run_consistency(tmp_path: Path, unit: dict):
    (tmp_path / "units").mkdir(parents=True, exist_ok=True)
    (tmp_path / "units" / f"{unit['unit_id']}.json").write_text(
        json.dumps(unit, ensure_ascii=False), encoding="utf-8"
    )
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "consistency_check.py"), "--project-root", str(tmp_path)],
        capture_output=True, text=True,
    )


def test_substantive_add_no_landing_fails(tmp_path):
    # "we have added a new control experiment" with an empty landing must FAIL.
    r = _run_consistency(tmp_path, _unit("u1", "We thank the reviewer. We have added a new control experiment to the study."))
    assert r.returncode != 0, r.stdout
    assert "CONSISTENCY_CHECK: FAIL" in r.stdout
    assert "SUBSTANTIVE ADDITION" in r.stdout


def test_we_performed_detected(tmp_path):
    r = _run_consistency(tmp_path, _unit("u2", "We performed an additional sensitivity analysis. It confirms the result."))
    assert r.returncode != 0, r.stdout
    assert "CONSISTENCY_CHECK: FAIL" in r.stdout


def test_wording_promise_no_landing_is_warn_only(tmp_path):
    # A pure wording tweak promise with no landing stays WARN → exit 0.
    r = _run_consistency(tmp_path, _unit("u3", "We clarified the wording of this sentence. It now reads more clearly."))
    assert r.returncode == 0, r.stdout
    assert "CONSISTENCY_CHECK: PASS" in r.stdout
    assert "WARN" in r.stdout


def test_substantive_add_with_landing_passes(tmp_path):
    actions = [{"action_type": "添加", "target": "new control experiment", "reason": "added a new control per reviewer"}]
    r = _run_consistency(tmp_path, _unit("u4", "We have added a new control experiment to address this.", actions=actions))
    assert r.returncode == 0, r.stdout
    assert "CONSISTENCY_CHECK: PASS" in r.stdout


def test_pack_embeds_comments(tmp_path):
    units_dir = tmp_path / "units"
    units_dir.mkdir()
    (units_dir / "001.json").write_text("{}", encoding="utf-8")
    letter = tmp_path / "letter.txt"
    letter.write_text(
        "Reviewer 1. The authors should address several points: (i) the sample size, "
        "(ii) the statistical model, (iii) the control group.",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "delegate_review.py"), "pack",
         "--checklist", str(ROOT / "references" / "dod_checklist.json"),
         "--gate", "response-dod",
         "--files", str(units_dir / "001.json"),
         "--comments", str(letter),
         "--workdir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "审稿信原文" in r.stdout
    assert "(i) the sample size" in r.stdout
    assert "(iii) the control group" in r.stdout


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))

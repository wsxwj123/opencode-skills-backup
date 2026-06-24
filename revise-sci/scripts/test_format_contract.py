#!/usr/bin/env python3
"""Regression tests for two format-contract fixes (self-contained, no pytest).

Run directly:  python3 test_format_contract.py
Pass => prints OK. Fail => raises AssertionError.

Covers two contracts that regressed and were fixed in the closing pass:

1. polish_revisions.py must NOT list "from A to B" as a forbidden structure.
   The detection side already treats "from-X-to-Y" as legitimate academic
   phrasing; the cleaning side (this prompt config) must stay aligned and not
   strip it. Bug: cleaning end forbade a structure the detection end allows.

2. intake_router.py must reject a non-.docx main manuscript AT THE INTAKE
   STAGE (detected_mode=unsupported + manuscript_format_error set), not pass it
   through to the pipeline and crash later. A valid .docx must still pass.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
POLISH = SCRIPTS_DIR / "polish_revisions.py"
INTAKE = SCRIPTS_DIR / "intake_router.py"
CITATION_GUARD = SCRIPTS_DIR / "citation_guard.py"
REFERENCE_SYNC = SCRIPTS_DIR / "reference_sync.py"
XSEC_SCRIPT = SCRIPTS_DIR / "cross_section_consistency.py"


def test_polish_no_from_a_to_b_forbidden() -> None:
    # BUG: "from A to B" was listed in forbidden_structures, contradicting the
    # detection side which accepts from-X-to-Y as valid academic phrasing.
    src = POLISH.read_text(encoding="utf-8")

    assert "from A to B" not in src, (
        'polish_revisions.py still contains "from A to B" as a forbidden item; '
        "cleaning end must align with detection end (from-X-to-Y is legitimate)."
    )

    # The list structure must remain syntactically intact (not broken by the edit).
    tree = ast.parse(src)
    assert tree is not None, "polish_revisions.py failed to ast.parse after edit"


def _run_intake(manuscript_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(INTAKE), "--manuscript", str(manuscript_path)],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"intake_router exited non-zero: {result.returncode}\nstderr:\n{result.stderr}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_intake_rejects_non_docx_manuscript() -> None:
    # BUG: a non-.docx main manuscript was passed through to the pipeline and
    # crashed there instead of being caught at intake.
    with tempfile.TemporaryDirectory() as tmp:
        md_path = Path(tmp) / "main.md"
        md_path.write_text("# Title\n\nSome manuscript body.\n", encoding="utf-8")
        payload = _run_intake(md_path)

    assert payload["detected_mode"] == "unsupported", (
        f"non-.docx manuscript should route to 'unsupported', got "
        f"{payload['detected_mode']!r}"
    )
    assert payload["manuscript_format_error"], (
        "manuscript_format_error must be non-empty for a non-.docx manuscript"
    )
    prompt = payload.get("assistant_prompt", "")
    assert ".docx" in prompt, (
        "intake prompt must tell the user a .docx manuscript is required; "
        f"got prompt:\n{prompt}"
    )


def test_intake_accepts_docx_manuscript() -> None:
    # A valid .docx must NOT regress into the format-error branch. The intake
    # extension check is by suffix only and does not parse the docx package, so
    # a .docx-suffixed file is enough to assert the accept path.
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = Path(tmp) / "main.docx"
        docx_path.write_bytes(b"PK\x03\x04 placeholder docx bytes")
        payload = _run_intake(docx_path)

    assert not payload["manuscript_format_error"], (
        "a .docx manuscript must not trigger manuscript_format_error; got "
        f"{payload['manuscript_format_error']!r}"
    )
    assert payload["detected_mode"] != "unsupported", (
        "a .docx-only manuscript should route to a supported mode "
        "(no-comments-manuscript-only), not 'unsupported'"
    )
    assert payload["detected_mode"] == "no-comments-manuscript-only", (
        f"expected 'no-comments-manuscript-only' for docx-only intake, got "
        f"{payload['detected_mode']!r}"
    )


def _run_guard(tmp: Path, extra_args: list[str]) -> int:
    """Run citation_guard against one unverified row; return its exit code."""
    results = {
        "results": [
            {
                "comment_id": "c1",
                "confirmed": False,  # unverified row -> all_rows_guard_verified False
                "citations": [{"title": "Some unverifiable paper", "source": "no identifier"}],
            }
        ]
    }
    rf = tmp / "psr.json"
    rf.write_text(json.dumps(results), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(CITATION_GUARD),
            "--paper-search-results",
            str(rf),
            "--project-root",
            str(tmp),
            "--offline",
        ]
        + extra_args,
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode


def test_guard_allow_unverified_is_lenient_by_default() -> None:
    # Default pipeline behaviour must stay lenient: --allow-unverified -> exit 0.
    with tempfile.TemporaryDirectory() as tmp:
        rc = _run_guard(Path(tmp), ["--allow-unverified"])
    assert rc == 0, f"--allow-unverified must stay lenient (exit 0), got {rc}"


def test_guard_fail_on_unverified_overrides_allow() -> None:
    # Opt-in hard gate: --fail-on-unverified must override --allow-unverified
    # and turn an unverified row back into fail-closed (exit 2).
    with tempfile.TemporaryDirectory() as tmp:
        rc = _run_guard(Path(tmp), ["--allow-unverified", "--fail-on-unverified"])
    assert rc == 2, f"--fail-on-unverified must force exit 2 on unverified row, got {rc}"


def _run_sync(tmp: Path, refs_block: str, extra_args: list[str]) -> tuple[int, dict]:
    (tmp / "units").mkdir(exist_ok=True)  # empty units -> only existing refs evaluated
    md = tmp / "out.md"
    md.write_text(f"# Title\n\nbody\n\n## References\n\n{refs_block}", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(REFERENCE_SYNC),
            "--project-root",
            str(tmp),
            "--output-md",
            str(md),
        ]
        + extra_args,
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    return result.returncode, payload


def test_reference_sync_fail_on_gap_lenient_by_default() -> None:
    # Default behaviour unchanged: a numbering gap is reported but does NOT fail.
    gapped = "1. A.\n2. B.\n4. D.\n"
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload = _run_sync(Path(tmp), gapped, [])
    assert rc == 0, f"reference_sync must stay lenient without --fail-on-gap, got {rc}"
    assert payload["numbering_gaps"] == [3], (
        f"gap 3 must be detected and reported, got {payload['numbering_gaps']}"
    )


def test_reference_sync_fail_on_gap_blocks() -> None:
    gapped = "1. A.\n2. B.\n4. D.\n"
    with tempfile.TemporaryDirectory() as tmp:
        rc, _ = _run_sync(Path(tmp), gapped, ["--fail-on-gap"])
    assert rc != 0, f"--fail-on-gap must block on a numbering gap, got {rc}"


def test_reference_sync_fail_on_gap_no_false_positive() -> None:
    clean = "1. A.\n2. B.\n3. C.\n"
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload = _run_sync(Path(tmp), clean, ["--fail-on-gap"])
    assert rc == 0, f"--fail-on-gap must not fire on contiguous refs, got {rc}"
    assert payload["numbering_gaps"] == [], (
        f"contiguous refs must report no gaps, got {payload['numbering_gaps']}"
    )


# ---------------------------------------------------------------------------
# B1/B2: cross_section_consistency — cross-section numeric drift (WARN, semi-auto).
# Bidirectional: same label + different value -> suspicion; consistent / different
# label -> nothing. Scans the revise-sci drafts/section_*.md chapter layout.
# ---------------------------------------------------------------------------
def _run_xsec(root: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(XSEC_SCRIPT), "--project-root", str(root)],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"xsec must be WARN-level (rc=0), got {result.returncode}\n{result.stderr}"
    )
    return json.loads(result.stdout)


def _xsec_drafts(tmp: str, sec1: str, sec2: str) -> Path:
    root = Path(tmp)
    drafts = root / "drafts"
    drafts.mkdir()
    (drafts / "section_01_abstract.md").write_text(sec1, encoding="utf-8")
    (drafts / "section_03_results.md").write_text(sec2, encoding="utf-8")
    return root


def test_xsec_flags_same_label_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_drafts(
            tmp,
            "The survival rate was 45% in the treated cohort.\n",
            "# Results\n\nUltimately the survival rate reached 47% overall.\n",
        )
        res = _run_xsec(root)
    labels = {s["label"] for s in res["suspicions"]}
    assert "survival rate" in labels, (
        f"45% vs 47% under same label must be flagged; got {res['suspicions']}"
    )
    susp = next(s for s in res["suspicions"] if s["label"] == "survival rate")
    assert {v["value"] for v in susp["values"]} == {"45", "47"}, (
        "both drifting values must appear"
    )


def test_xsec_no_flag_when_consistent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_drafts(
            tmp,
            "The survival rate was 45% in the treated cohort.\n",
            "# Results\n\nThe survival rate remained 45% at follow-up.\n",
        )
        res = _run_xsec(root)
    assert res["suspicions"] == [], (
        f"consistent 45%/45% must NOT be flagged; got {res['suspicions']}"
    )


def test_xsec_no_flag_for_different_labels() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_drafts(
            tmp,
            "The survival rate was 45% in the treated cohort.\n",
            "# Results\n\nThe response rate reached 47% overall.\n",
        )
        res = _run_xsec(root)
    assert res["suspicions"] == [], (
        f"different labels must NOT be flagged; got {res['suspicions']}"
    )


def test_xsec_ignores_reference_block_pmids() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_drafts(
            tmp,
            "Efficacy of 45% was observed.\n",
            "# Results\n\nNo numeric claim here.\n\n"
            "## References\n\n"
            "- [1] Some paper reporting 45% something. 2020. PMID 12345678.\n"
            "- [2] Another reporting 99% else. 2021. PMID 87654321.\n",
        )
        res = _run_xsec(root)
    assert res["suspicions"] == [], (
        f"reference-block numerics must be excluded; got {res['suspicions']}"
    )


def main() -> int:
    test_polish_no_from_a_to_b_forbidden()
    test_intake_rejects_non_docx_manuscript()
    test_intake_accepts_docx_manuscript()
    test_guard_allow_unverified_is_lenient_by_default()
    test_guard_fail_on_unverified_overrides_allow()
    test_reference_sync_fail_on_gap_lenient_by_default()
    test_reference_sync_fail_on_gap_blocks()
    test_reference_sync_fail_on_gap_no_false_positive()
    test_xsec_flags_same_label_drift()
    test_xsec_no_flag_when_consistent()
    test_xsec_no_flag_for_different_labels()
    test_xsec_ignores_reference_block_pmids()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
DOD_CHECKLIST = SCRIPTS_DIR.parent / "references" / "dod_checklist.json"
MANUSCRIPT_INDEX = SCRIPTS_DIR / "manuscript_index.py"
DELEGATE_REVIEW = SCRIPTS_DIR / "delegate_review.py"


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


def test_dod_checklist_valid_and_rv_r10_wired_to_xsec() -> None:
    # RV-R10 (cross-section consistency blind check) gained an auxiliary objective
    # signal: it must now carry a "script" field invoking cross_section_consistency.py.
    # The checklist must stay valid JSON and the script must resolve to an existing file.
    data = json.loads(DOD_CHECKLIST.read_text(encoding="utf-8"))
    items = data["gates"]["revision-dod"]["items"]
    rv_r10 = next((i for i in items if i["id"] == "RV-R10"), None)
    assert rv_r10 is not None, "RV-R10 item missing from dod_checklist.json"
    assert "script" in rv_r10 and rv_r10["script"].strip(), (
        f"RV-R10 must carry a non-empty 'script' field; got {rv_r10.get('script')!r}"
    )
    assert "cross_section_consistency.py" in rv_r10["script"], (
        f"RV-R10 script must invoke cross_section_consistency.py; got {rv_r10['script']!r}"
    )
    assert XSEC_SCRIPT.exists(), (
        f"cross_section_consistency.py referenced by RV-R10 must exist at {XSEC_SCRIPT}"
    )


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


# ---------------------------------------------------------------------------
# Bug 2: manuscript_index — a numbered References heading ("## 9. References")
# must still be recognised as the reference section, so reference reverse-lookup
# does not silently report references=0. Driven end-to-end through the CLI.
# ---------------------------------------------------------------------------
def _run_manuscript_index(manuscript_md: str, tmp: Path) -> dict:
    md = tmp / "main.md"
    md.write_text(manuscript_md, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(MANUSCRIPT_INDEX),
            "--manuscript",
            str(md),
            "--project-root",
            str(tmp),
        ],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"manuscript_index exited non-zero: {result.returncode}\nstderr:\n{result.stderr}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


# A body that cites [1] and [2] plus a reference list under the given heading.
_MS_BODY = (
    "# Title\n\n"
    "## Introduction\n\n"
    "Prior work established the baseline [1] and the follow-up [2].\n\n"
    "{heading}\n\n"
    "1. Smith J. A foundational study. Journal A. 2019.\n"
    "2. Doe R. A follow-up study. Journal B. 2021.\n"
)


def test_manuscript_index_numbered_references_heading() -> None:
    # BUG: "## 9. References" normalised to "9. references", which was not in the
    # exact REFERENCE_HEADINGS set, so references parsed as 0 and orphan detection
    # was meaningless.
    with tempfile.TemporaryDirectory() as tmp:
        payload = _run_manuscript_index(
            _MS_BODY.format(heading="## 9. References"), Path(tmp)
        )
    assert payload["references"] == 2, (
        f"numbered 'References' heading must yield references>0, got {payload['references']}"
    )
    # Both refs are cited -> no entry_not_cited orphans for them.
    assert payload["reference_orphans"] == 0, (
        f"both refs are cited, expected 0 reference orphans, got {payload['reference_orphans']}"
    )


def test_manuscript_index_plain_references_heading_unchanged() -> None:
    # An un-numbered "## References" must NOT regress.
    with tempfile.TemporaryDirectory() as tmp:
        payload = _run_manuscript_index(
            _MS_BODY.format(heading="## References"), Path(tmp)
        )
    assert payload["references"] == 2, (
        f"plain 'References' heading must still parse refs, got {payload['references']}"
    )


def test_manuscript_index_numbered_chinese_references_heading() -> None:
    # "## 6 参考文献" (number + space, no dot) must also be recognised.
    with tempfile.TemporaryDirectory() as tmp:
        payload = _run_manuscript_index(
            _MS_BODY.format(heading="## 6 参考文献"), Path(tmp)
        )
    assert payload["references"] == 2, (
        f"numbered Chinese references heading must parse refs, got {payload['references']}"
    )


# ---------------------------------------------------------------------------
# Bug 7: delegate_review._get_gate — a malformed checklist whose "gates" is a
# list (not a dict) must fail with a friendly exit 2, not crash with TypeError.
# ---------------------------------------------------------------------------
def _run_delegate_pack(checklist_obj, tmp: Path) -> subprocess.CompletedProcess:
    cl = tmp / "checklist.json"
    cl.write_text(json.dumps(checklist_obj), encoding="utf-8")
    target = tmp / "target.md"
    target.write_text("placeholder\n", encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(DELEGATE_REVIEW),
            "pack",
            "--checklist",
            str(cl),
            "--gate",
            "g1",
            "--files",
            str(target),
            "--workdir",
            str(tmp),
        ],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )


def test_delegate_review_malformed_gates_list_exit2() -> None:
    # BUG: gates as a list reached sorted()+join and raised TypeError.
    with tempfile.TemporaryDirectory() as tmp:
        proc = _run_delegate_pack({"skill": "x", "gates": ["g1", "g2"]}, Path(tmp))
    assert proc.returncode == 2, (
        f"malformed list 'gates' must exit 2 (friendly), got {proc.returncode}\n"
        f"stderr:\n{proc.stderr}"
    )
    assert "TypeError" not in proc.stderr, (
        f"must not crash with TypeError; stderr:\n{proc.stderr}"
    )


def test_delegate_review_unknown_gate_still_exit2() -> None:
    # A well-formed dict 'gates' missing the requested gate must keep its
    # existing friendly exit-2 behaviour (no regression).
    with tempfile.TemporaryDirectory() as tmp:
        proc = _run_delegate_pack({"skill": "x", "gates": {"other": {}}}, Path(tmp))
    assert proc.returncode == 2, (
        f"unknown gate on a valid dict checklist must still exit 2, got {proc.returncode}\n"
        f"stderr:\n{proc.stderr}"
    )


# ---------------------------------------------------------------------------
# Bug 7 (residual): pack/verify use it["id"] over gate["items"]; a malformed
# gate (items elements not dicts / items not a list / gate not a dict) must
# fail with a friendly exit 2, never a raw TypeError. A normal dict checklist
# must keep pack->verify behaviour identical.
# ---------------------------------------------------------------------------
def _run_delegate_verify(
    checklist_obj, return_obj, tmp: Path
) -> subprocess.CompletedProcess:
    cl = tmp / "checklist.json"
    cl.write_text(json.dumps(checklist_obj), encoding="utf-8")
    ret = tmp / ".review_return_g1.json"
    ret.write_text(json.dumps(return_obj), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(DELEGATE_REVIEW),
            "verify",
            "--checklist",
            str(cl),
            "--gate",
            "g1",
            "--workdir",
            str(tmp),
        ],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )


def test_delegate_review_items_string_elements_exit2() -> None:
    # ① items is a list but elements are strings -> it["id"] would TypeError.
    bad = {"skill": "x", "gates": {"g1": {"items": ["a", "b"]}}}
    with tempfile.TemporaryDirectory() as tmp:
        proc_pack = _run_delegate_pack(bad, Path(tmp))
        proc_ver = _run_delegate_verify(bad, [], Path(tmp))
    for label, proc in (("pack", proc_pack), ("verify", proc_ver)):
        assert proc.returncode == 2, (
            f"{label}: string-element items must exit 2, got {proc.returncode}\n"
            f"stderr:\n{proc.stderr}"
        )
        assert "Traceback" not in proc.stderr, (
            f"{label}: must not crash with Traceback; stderr:\n{proc.stderr}"
        )


def test_delegate_review_items_not_list_exit2() -> None:
    # ② items is a dict (not a list) -> friendly exit 2, no TypeError.
    bad = {"skill": "x", "gates": {"g1": {"items": {"id": "X1"}}}}
    with tempfile.TemporaryDirectory() as tmp:
        proc_pack = _run_delegate_pack(bad, Path(tmp))
        proc_ver = _run_delegate_verify(bad, [], Path(tmp))
    for label, proc in (("pack", proc_pack), ("verify", proc_ver)):
        assert proc.returncode == 2, (
            f"{label}: dict (non-list) items must exit 2, got {proc.returncode}\n"
            f"stderr:\n{proc.stderr}"
        )
        assert "Traceback" not in proc.stderr, (
            f"{label}: must not crash with Traceback; stderr:\n{proc.stderr}"
        )


def test_delegate_review_gate_not_dict_exit2() -> None:
    # ③ gates[gate] is not a dict (e.g. a list) -> friendly exit 2, no TypeError.
    bad = {"skill": "x", "gates": {"g1": ["not", "a", "dict"]}}
    with tempfile.TemporaryDirectory() as tmp:
        proc_pack = _run_delegate_pack(bad, Path(tmp))
        proc_ver = _run_delegate_verify(bad, [], Path(tmp))
    for label, proc in (("pack", proc_pack), ("verify", proc_ver)):
        assert proc.returncode == 2, (
            f"{label}: non-dict gate object must exit 2, got {proc.returncode}\n"
            f"stderr:\n{proc.stderr}"
        )
        assert "Traceback" not in proc.stderr, (
            f"{label}: must not crash with Traceback; stderr:\n{proc.stderr}"
        )


def test_delegate_review_normal_checklist_pack_and_verify_ok() -> None:
    # ④ A well-formed checklist: pack must exit 0; verify with a complete,
    # evidence-bearing return must pass (exit 0). Behaviour unchanged.
    good = {
        "skill": "x",
        "gates": {
            "g1": {
                "title": "Gate One",
                "items": [
                    {"id": "X1", "name": "n1", "check": "c1"},
                    {"id": "X2", "name": "n2", "check": "c2"},
                ],
            }
        },
    }
    good_return = [
        {"id": "X1", "verdict": "pass", "evidence": "ok per file"},
        {"id": "X2", "verdict": "pass", "evidence": "ok per file"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        proc_pack = _run_delegate_pack(good, Path(tmp))
        assert proc_pack.returncode == 0, (
            f"normal pack must exit 0, got {proc_pack.returncode}\n"
            f"stderr:\n{proc_pack.stderr}"
        )
        assert "X1" in proc_pack.stdout and "X2" in proc_pack.stdout, (
            "pack output must list both item ids"
        )
        proc_ver = _run_delegate_verify(good, good_return, Path(tmp))
    assert proc_ver.returncode == 0, (
        f"normal verify with full evidence must exit 0, got {proc_ver.returncode}\n"
        f"stderr:\n{proc_ver.stderr}"
    )
    assert "Traceback" not in proc_ver.stderr


def main() -> int:
    test_polish_no_from_a_to_b_forbidden()
    test_intake_rejects_non_docx_manuscript()
    test_intake_accepts_docx_manuscript()
    test_guard_allow_unverified_is_lenient_by_default()
    test_guard_fail_on_unverified_overrides_allow()
    test_reference_sync_fail_on_gap_lenient_by_default()
    test_reference_sync_fail_on_gap_blocks()
    test_reference_sync_fail_on_gap_no_false_positive()
    test_dod_checklist_valid_and_rv_r10_wired_to_xsec()
    test_xsec_flags_same_label_drift()
    test_xsec_no_flag_when_consistent()
    test_xsec_no_flag_for_different_labels()
    test_xsec_ignores_reference_block_pmids()
    test_manuscript_index_numbered_references_heading()
    test_manuscript_index_plain_references_heading_unchanged()
    test_manuscript_index_numbered_chinese_references_heading()
    test_delegate_review_malformed_gates_list_exit2()
    test_delegate_review_unknown_gate_still_exit2()
    test_delegate_review_items_string_elements_exit2()
    test_delegate_review_items_not_list_exit2()
    test_delegate_review_gate_not_dict_exit2()
    test_delegate_review_normal_checklist_pack_and_verify_ok()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

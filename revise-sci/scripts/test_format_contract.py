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


def main() -> int:
    test_polish_no_from_a_to_b_forbidden()
    test_intake_rejects_non_docx_manuscript()
    test_intake_accepts_docx_manuscript()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

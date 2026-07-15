#!/usr/bin/env python3
"""Round-trip + fail-closed tests for anchorize_draft.py + apply_revision_patch.py.

This pair is the ONLY place revise-sci rewrites the user's draft bytes: anchorize
splits the draft into content-hashed blocks; apply_revision_patch splices patched
blocks back and promises to (a) preserve every untouched block, separator and the
trailing-newline state byte-for-byte, and (b) reject the whole patch set writing
NOTHING whenever any anchor/hash/source precondition fails (fail-closed).

Both directions are driven through the real CLIs (subprocess), self-contained via
tempfile, standalone: `python3 test_anchor_patch_roundtrip.py` (exit 0 == all pass).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ANCHORIZE = SCRIPTS / "anchorize_draft.py"
APPLY = SCRIPTS / "apply_revision_patch.py"

# Deliberately awkward source: leading text, an indented blank separator line,
# CRLF-free multi-block body, and NO trailing newline on the last block. Every one
# of these is a byte the reassembler must reproduce exactly for untouched regions.
DRAFT = "First block stays.\n\nSecond block gets patched.\n \nThird block stays too."


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _anchorize(tmp: Path, draft_text: str = DRAFT) -> tuple[Path, dict]:
    draft = tmp / "draft.md"
    draft.write_text(draft_text, encoding="utf-8")
    manifest = tmp / "manifest.json"
    r = _run(ANCHORIZE, "--draft", str(draft), "--manifest", str(manifest))
    assert r.returncode == 0, r.stdout + r.stderr
    return manifest, json.loads(manifest.read_text(encoding="utf-8"))


def _block(manifest_obj: dict, ordinal: int) -> dict:
    return next(b for b in manifest_obj["blocks"] if b["ordinal"] == ordinal)


def test_precise_replace_preserves_other_bytes():
    """Patch only block 2; blocks 1/3, both separators and the no-trailing-newline
    tail must survive byte-for-byte (only the targeted span differs)."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        manifest, obj = _anchorize(tmp)
        target = _block(obj, 2)
        new_text = "Second block is now revised."
        patch = tmp / "patch.json"
        patch.write_text(json.dumps([
            {"anchor_id": target["anchor_id"], "expected_hash": target["sha256"], "new_content": new_text}
        ]), encoding="utf-8")
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 0, r.stdout + r.stderr
        produced = out.read_text(encoding="utf-8")
        # Exactly the original with block-2's span swapped: prove by reconstructing.
        expected = DRAFT[:target["char_start"]] + new_text + DRAFT[target["char_end"]:]
        assert produced == expected, repr(produced)
        # Untouched blocks appear verbatim; trailing-newline state (none) preserved.
        assert "First block stays." in produced and "Third block stays too." in produced
        assert not produced.endswith("\n"), "trailing-newline state must be preserved (source had none)"


def test_hash_mismatch_rejects_and_writes_nothing():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        manifest, obj = _anchorize(tmp)
        target = _block(obj, 2)
        patch = tmp / "patch.json"
        patch.write_text(json.dumps([
            {"anchor_id": target["anchor_id"], "expected_hash": "deadbeef" * 8, "new_content": "X"}
        ]), encoding="utf-8")
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 1, r.stdout
        assert json.loads(r.stdout)["rejected"] is True
        assert not out.exists(), "fail-closed: output file must not be created on hash mismatch"


def test_unknown_anchor_rejects_and_writes_nothing():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        manifest, obj = _anchorize(tmp)
        real = _block(obj, 1)
        patch = tmp / "patch.json"
        patch.write_text(json.dumps([
            {"anchor_id": "block-9999-nonexist", "expected_hash": real["sha256"], "new_content": "X"}
        ]), encoding="utf-8")
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 1, r.stdout
        assert not out.exists(), "fail-closed: unknown anchor must not write output"


def test_source_drift_rejects_and_writes_nothing():
    """If the draft on disk changed after anchorize (source_sha256 no longer holds),
    even a hash-correct patch must be rejected with no output."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        draft = tmp / "draft.md"
        draft.write_text(DRAFT, encoding="utf-8")
        manifest = tmp / "manifest.json"
        assert _run(ANCHORIZE, "--draft", str(draft), "--manifest", str(manifest)).returncode == 0
        obj = json.loads(manifest.read_text(encoding="utf-8"))
        target = _block(obj, 2)
        # Mutate the draft AFTER anchorize -> source drift.
        draft.write_text(DRAFT + "\n\nAn extra block appeared.", encoding="utf-8")
        patch = tmp / "patch.json"
        patch.write_text(json.dumps([
            {"anchor_id": target["anchor_id"], "expected_hash": target["sha256"], "new_content": "X"}
        ]), encoding="utf-8")
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 1, r.stdout
        assert not out.exists(), "fail-closed: source drift must not write output"


def test_non_array_patch_rejects():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        manifest, _ = _anchorize(tmp)
        patch = tmp / "patch.json"
        patch.write_text(json.dumps({"anchor_id": "x"}), encoding="utf-8")  # object, not array
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 1, r.stdout
        assert not out.exists()


def test_missing_field_rejects():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        manifest, obj = _anchorize(tmp)
        target = _block(obj, 1)
        patch = tmp / "patch.json"
        # missing new_content
        patch.write_text(json.dumps([
            {"anchor_id": target["anchor_id"], "expected_hash": target["sha256"]}
        ]), encoding="utf-8")
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 1, r.stdout
        assert not out.exists()


def test_duplicate_anchor_rejects():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        manifest, obj = _anchorize(tmp)
        target = _block(obj, 1)
        entry = {"anchor_id": target["anchor_id"], "expected_hash": target["sha256"], "new_content": "X"}
        patch = tmp / "patch.json"
        patch.write_text(json.dumps([entry, dict(entry)]), encoding="utf-8")  # same anchor twice
        out = tmp / "out.md"
        r = _run(APPLY, "--manifest", str(manifest), "--patch", str(patch), "--output", str(out))
        assert r.returncode == 1, r.stdout
        assert not out.exists()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: anchorize+apply round-trip preserves untouched bytes and fails closed on every precondition")

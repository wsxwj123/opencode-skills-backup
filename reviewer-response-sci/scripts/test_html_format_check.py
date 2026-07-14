#!/usr/bin/env python3
"""Smoke test for html_format_check.py (HTML output-contract承重门, fail-closed).

Bidirectional:
  - violation: a bare <html></html> shell missing the required ids/classes/headings
    → exit 1, "HTML_FORMAT_CHECK: FAIL".
  - compliant: a synthetic HTML carrying every required id/class/scaffold/heading token
    → exit 0, "HTML_FORMAT_CHECK: PASS".
Self-contained: writes synthetic HTML under tempfile; no real render pipeline.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "html_format_check.py"

# Minimal HTML that satisfies every hard requirement in html_format_check.main().
_COMPLIANT = """<html><head><style>:root{--sidebar-w:320px}</style></head><body>
<div id="layout-root">
  <nav id="toc-root">
    <button class="toc-btn toc-level-1">R1</button>
    <button class="toc-btn toc-level-2">C1</button>
    <button class="toc-btn toc-level-3">C1.1</button>
  </nav>
  <div id="resizer" role="separator"></div>
  <main id="content-root">
    <section class="page">
      <h2>Response to Reviewer（中英对照）</h2>
      <button class="copy-btn" onclick="copyText('x')">copy</button>
      <h2>可能需要修改的正文/附件内容（中英对照）</h2>
      <div>原子化定位（Atomic Location）: manuscript_unit_id = m1</div>
      <div>核心 Core note</div>
      <table><thead><tr><th>col</th></tr></thead><tbody><tr><td>v</td></tr></tbody></table>
    </section>
  </main>
</div>
<script>localStorage.getItem('reviewer_sidebar_width_v1');function copyText(t){}</script>
</body></html>
"""

_VIOLATION = "<html><body><p>empty shell, no scaffolding</p></body></html>"


def _run(html: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, str(SCRIPT), path], capture_output=True, text=True
        )
    finally:
        Path(path).unlink(missing_ok=True)


def test_violation_fails() -> None:
    r = _run(_VIOLATION)
    assert r.returncode == 1, f"expected FAIL exit 1, got {r.returncode}\n{r.stdout}"
    assert "HTML_FORMAT_CHECK: FAIL" in r.stdout, r.stdout


def test_compliant_passes() -> None:
    r = _run(_COMPLIANT)
    assert r.returncode == 0, f"expected PASS exit 0, got {r.returncode}\n{r.stdout}"
    assert "HTML_FORMAT_CHECK: PASS" in r.stdout, r.stdout


if __name__ == "__main__":
    test_violation_fails()
    test_compliant_passes()
    print("OK: html_format_check — bare shell fails, full scaffold passes")

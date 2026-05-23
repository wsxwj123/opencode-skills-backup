#!/usr/bin/env python3
"""Citation verification guard for reviewer-response-sci.

Validates entries in citation_registry.json (new references added during
reviewer response) against CrossRef / PubMed APIs.  Adapted from
review-writing/scripts/citation_guard.py with simplified interface.

Usage:
    python citation_guard.py --project-root /path/to/project
    python citation_guard.py --project-root /path/to/project --offline
    python citation_guard.py --project-root /path/to/project --fail-on-unverified
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
PMID_RE = re.compile(r"^\d{4,10}$")
TITLE_TOKEN_RE = re.compile(r"[a-z0-9一-鿿]+")

FORBIDDEN_PROVIDERS = {"websearch", "web-search", "web_search", "tavily"}


def _http_get_json(url: str, timeout_sec: float = 8.0) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": "citation-guard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9一-鿿]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _title_tokens(title: str) -> set[str]:
    return set(TITLE_TOKEN_RE.findall(_normalize_title(title)))


def _title_similarity(a: str, b: str) -> float:
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = _title_tokens(a), _title_tokens(b)
    jacc = (len(ta & tb) / len(ta | tb)) if ta and tb else 0.0
    short = min(len(na), len(nb)) / max(len(na), len(nb))
    contain_bonus = 0.1 if (na in nb or nb in na) else 0.0
    return min(1.0, 0.75 * jacc + 0.25 * short + contain_bonus)


def _fetch_crossref_by_doi(doi: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(doi, safe="")
    payload = _http_get_json(f"https://api.crossref.org/works/{encoded}")
    if not payload or "message" not in payload:
        return None
    msg = payload["message"]
    title = (msg.get("title") or [""])[0] if isinstance(msg.get("title"), list) else ""
    relation = msg.get("relation") or {}
    is_retracted = isinstance(relation, dict) and any("retract" in str(k).lower() for k in relation.keys())
    return {"source": "crossref", "title": title or "", "doi": doi, "retracted": is_retracted}


def _fetch_pubmed_by_pmid(pmid: str) -> dict[str, Any] | None:
    payload = _http_get_json(
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    )
    if not payload or "result" not in payload:
        return None
    result = payload["result"].get(str(pmid))
    if not isinstance(result, dict):
        return None
    title = result.get("title") or ""
    article_ids = result.get("articleids") or []
    doi = None
    for aid in article_ids:
        if isinstance(aid, dict) and str(aid.get("idtype", "")).lower() == "doi":
            doi = aid.get("value")
            break
    pubtypes = result.get("pubtype") or []
    is_retracted = any("retract" in str(x).lower() for x in pubtypes)
    return {"source": "pubmed", "title": title, "doi": doi, "pmid": str(pmid), "retracted": is_retracted}


def validate_entry(entry: dict[str, Any], *, online: bool) -> dict[str, Any]:
    """Validate a single citation registry entry."""
    title = str(entry.get("title") or "").strip()
    doi = str(entry.get("doi") or "").strip()
    pmid = str(entry.get("pmid") or "").strip()
    provider = str(entry.get("source_provider") or "").strip().lower()

    doi_fmt_ok = DOI_RE.match(doi) is not None if doi else None
    pmid_fmt_ok = PMID_RE.match(pmid) is not None if pmid else None

    crossref = _fetch_crossref_by_doi(doi) if (online and doi and doi_fmt_ok) else None
    pubmed = _fetch_pubmed_by_pmid(pmid) if (online and pmid and pmid_fmt_ok) else None

    # Title similarity check against external sources
    source_titles = []
    for rec in (pubmed, crossref):
        if rec and rec.get("title"):
            source_titles.append(str(rec["title"]))
    title_sim = max((_title_similarity(title, st) for st in source_titles), default=0.0)
    title_match = bool(source_titles) and title_sim >= 0.72

    failures: list[str] = []

    if not title:
        failures.append("title_missing")
    if provider in FORBIDDEN_PROVIDERS:
        failures.append("forbidden_provider")
    if not doi and not pmid:
        failures.append("no_identifier")
    if doi and not doi_fmt_ok:
        failures.append("doi_format_invalid")
    if pmid and not pmid_fmt_ok:
        failures.append("pmid_format_invalid")
    if online and doi and doi_fmt_ok and crossref is None:
        failures.append("doi_unresolvable")
    if online and pmid and pmid_fmt_ok and pubmed is None:
        failures.append("pmid_unresolvable")
    if title and source_titles and not title_match:
        failures.append("title_mismatch")

    # DOI/PMID cross-match
    if doi and pmid and pubmed and pubmed.get("doi"):
        if str(pubmed["doi"]).lower() != doi.lower():
            failures.append("doi_pmid_cross_mismatch")

    # Retraction
    retracted = bool(entry.get("retracted", False))
    for rec in (pubmed, crossref):
        if rec and rec.get("retracted"):
            retracted = True
    if retracted:
        failures.append("retracted")

    # Confidence score
    score = 0.0
    score += title_sim * 35
    if doi_fmt_ok is True:
        score += 18 if (crossref is not None or not online) else -5
    if pmid_fmt_ok is True:
        score += 18 if (pubmed is not None or not online) else -5
    if doi and pmid and pubmed and pubmed.get("doi"):
        score += 10 if str(pubmed["doi"]).lower() == doi.lower() else -12
    if provider and provider not in FORBIDDEN_PROVIDERS:
        score += 6
    elif provider in FORBIDDEN_PROVIDERS:
        score -= 20
    if retracted:
        score -= 60
    confidence = int(max(0, min(100, round(score))))

    return {
        "ref_number": entry.get("ref_number"),
        "title": title,
        "doi": doi,
        "pmid": pmid,
        "verified": len(failures) == 0,
        "confidence": confidence,
        "title_similarity": round(title_sim, 4),
        "failures": failures,
        "retracted": retracted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Citation guard for reviewer-response-sci")
    parser.add_argument("--project-root", required=True, help="Project root directory")
    parser.add_argument("--offline", action="store_true", help="Skip online API checks")
    parser.add_argument("--fail-on-unverified", action="store_true", help="Exit non-zero if any entry fails")
    args = parser.parse_args()

    root = Path(args.project_root)
    registry_path = root / "citation_registry.json"

    if not registry_path.exists():
        print("CITATION_GUARD: SKIP (no citation_registry.json)")
        return 0

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"CITATION_GUARD: ERROR reading registry: {e}")
        return 1

    entries = registry.get("entries", [])
    if not entries:
        print("CITATION_GUARD: PASS (empty registry)")
        return 0

    t0 = time.perf_counter()
    now_utc = datetime.now(timezone.utc)
    online = not args.offline

    results = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        result = validate_entry(entry, online=online)
        results.append(result)
        if online:
            time.sleep(0.3)  # rate limit courtesy

    verified_count = sum(1 for r in results if r["verified"])
    failed = [r for r in results if not r["verified"]]
    retracted = [r for r in results if r.get("retracted")]
    duration_ms = int((time.perf_counter() - t0) * 1000)

    report = {
        "status": "pass" if verified_count == len(results) else "warn",
        "total": len(results),
        "verified": verified_count,
        "failed": len(failed),
        "retracted": len(retracted),
        "avg_confidence": round(sum(r["confidence"] for r in results) / len(results), 1) if results else 0,
        "duration_ms": duration_ms,
        "checked_at": now_utc.isoformat(),
        "online": online,
        "failed_entries": [
            {"ref_number": r["ref_number"], "title": r["title"][:60], "failures": r["failures"]}
            for r in failed
        ],
        "retracted_entries": [
            {"ref_number": r["ref_number"], "title": r["title"][:60]}
            for r in retracted
        ],
    }

    # Write report
    report_path = root / "logs" / "citation_guard_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    if failed:
        print("CITATION_GUARD: WARN")
        for r in failed:
            print(f"  - [ref {r['ref_number']}] {r['title'][:50]}: {', '.join(r['failures'])}")
    elif retracted:
        print("CITATION_GUARD: WARN (retracted references found)")
        for r in retracted:
            print(f"  - [ref {r['ref_number']}] {r['title'][:50]}: RETRACTED")
    else:
        print(f"CITATION_GUARD: PASS ({verified_count}/{len(results)} verified)")

    if args.fail_on_unverified and failed:
        return 1
    if retracted:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

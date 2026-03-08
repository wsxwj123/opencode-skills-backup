#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from common import normalize_ws, read_json, write_json


DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
PMID_RE = re.compile(r"^\d{4,10}$")
TITLE_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+")
ALLOWED_PROVIDER_FAMILIES = {"paper-search"}


def _http_get_json(url: str, timeout_sec: float = 8.0) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": "revise-sci-citation-guard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def _normalize_title(title: str) -> str:
    text = title.lower().strip()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_tokens(title: str) -> set[str]:
    return set(TITLE_TOKEN_RE.findall(_normalize_title(title)))


def _title_similarity(a: str, b: str) -> float:
    na = _normalize_title(a)
    nb = _normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta = _title_tokens(a)
    tb = _title_tokens(b)
    if not ta or not tb:
        return 0.0
    jacc = len(ta & tb) / len(ta | tb)
    short = min(len(na), len(nb)) / max(len(na), len(nb))
    contain_bonus = 0.1 if (na in nb or nb in na) else 0.0
    return min(1.0, 0.75 * jacc + 0.25 * short + contain_bonus)


def _fetch_crossref_by_doi(doi: str) -> dict[str, Any] | None:
    payload = _http_get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}")
    if not payload or "message" not in payload:
        return None
    msg = payload["message"]
    title = (msg.get("title") or [""])[0] if isinstance(msg.get("title"), list) else ""
    returned_doi = str(msg.get("DOI") or doi).strip()
    return {"title": title or "", "doi": returned_doi}


def _fetch_pubmed_by_pmid(pmid: str) -> dict[str, Any] | None:
    payload = _http_get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        + urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "json"})
    )
    if not payload or "result" not in payload:
        return None
    result = payload["result"].get(str(pmid))
    if not isinstance(result, dict):
        return None
    article_ids = result.get("articleids") or []
    doi = ""
    for item in article_ids:
        if isinstance(item, dict) and str(item.get("idtype", "")).lower() == "doi":
            doi = str(item.get("value") or "").strip()
            break
    return {"title": str(result.get("title") or "").strip(), "pmid": str(pmid), "doi": doi}


def _provider_family(citation: dict[str, Any]) -> str:
    provider = normalize_ws(
        str(citation.get("source_provider") or citation.get("provider_family") or citation.get("provider") or "paper-search")
    ).lower()
    return "paper-search" if provider.startswith("paper-search") else provider


def _extract_identifier(citation: dict[str, Any]) -> tuple[str, str]:
    doi = normalize_ws(str(citation.get("doi") or ""))
    pmid = normalize_ws(str(citation.get("pmid") or ""))
    source = normalize_ws(str(citation.get("source") or citation.get("source_id") or ""))
    if not doi:
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", source, flags=re.IGNORECASE)
        if match:
            doi = match.group(0)
    if not pmid:
        match = re.search(r"PMID[:\s]*(\d{4,10})", source, flags=re.IGNORECASE)
        if match:
            pmid = match.group(1)
    return doi, pmid


def build_reference_entry(citation: dict[str, Any]) -> str:
    authors = citation.get("authors") or []
    if isinstance(authors, list):
        authors_text = ", ".join(str(x).strip() for x in authors if str(x).strip())
    else:
        authors_text = normalize_ws(str(authors))
    title = normalize_ws(str(citation.get("title") or "Untitled"))
    journal = normalize_ws(str(citation.get("journal") or citation.get("venue") or ""))
    year = normalize_ws(str(citation.get("year") or ""))
    doi, pmid = _extract_identifier(citation)
    parts = []
    if authors_text:
        parts.append(f"{authors_text}.")
    parts.append(f"{title}.")
    if journal:
        parts.append(journal + ".")
    if year:
        parts.append(year + ".")
    if doi:
        parts.append(f"DOI: {doi}.")
    if pmid:
        parts.append(f"PMID: {pmid}.")
    return " ".join(parts).strip()


def validate_citation(citation: dict[str, Any], *, online_check: bool) -> dict[str, Any]:
    title = normalize_ws(str(citation.get("title") or ""))
    source_trace = normalize_ws(str(citation.get("source_id") or citation.get("source") or ""))
    doi, pmid = _extract_identifier(citation)
    provider_family = _provider_family(citation)
    failure_reasons: list[str] = []

    if provider_family not in ALLOWED_PROVIDER_FAMILIES:
        failure_reasons.append("source_provider_not_allowed")
    if not title:
        failure_reasons.append("title_missing")
    if not source_trace:
        failure_reasons.append("source_trace_missing")
    if not doi and not pmid:
        failure_reasons.append("identifier_missing")
    if doi and DOI_RE.match(doi) is None:
        failure_reasons.append("doi_format_invalid")
    if pmid and PMID_RE.match(pmid) is None:
        failure_reasons.append("pmid_format_invalid")

    secondary_titles = []
    secondary_doi = normalize_ws(str(citation.get("verified_doi") or citation.get("crossref_doi") or ""))
    secondary_pmid = normalize_ws(str(citation.get("verified_pmid") or citation.get("pubmed_pmid") or ""))
    for key in ("verified_title", "crossref_title", "pubmed_title"):
        value = normalize_ws(str(citation.get(key) or ""))
        if value:
            secondary_titles.append(value)

    if online_check:
        if doi and not secondary_titles:
            rec = _fetch_crossref_by_doi(doi)
            if rec:
                secondary_titles.append(normalize_ws(rec.get("title", "")))
                secondary_doi = secondary_doi or normalize_ws(rec.get("doi", ""))
        if pmid and not secondary_titles:
            rec = _fetch_pubmed_by_pmid(pmid)
            if rec:
                secondary_titles.append(normalize_ws(rec.get("title", "")))
                secondary_pmid = secondary_pmid or normalize_ws(rec.get("pmid", ""))
                secondary_doi = secondary_doi or normalize_ws(rec.get("doi", ""))

    if not secondary_titles:
        failure_reasons.append("secondary_verification_missing")

    title_similarity = max((_title_similarity(title, st) for st in secondary_titles), default=0.0)
    if secondary_titles and title_similarity < 0.72:
        failure_reasons.append("title_mismatch")

    if doi and secondary_doi and doi.lower() != secondary_doi.lower():
        failure_reasons.append("doi_mismatch")
    if pmid and secondary_pmid and pmid != secondary_pmid:
        failure_reasons.append("pmid_mismatch")

    verified = not failure_reasons
    payload = dict(citation)
    payload["provider_family"] = provider_family
    payload["doi"] = doi
    payload["pmid"] = pmid
    payload["guard_verified"] = verified
    payload["reference_entry"] = build_reference_entry(payload)
    payload["verification_details"] = {
        "title_similarity": round(title_similarity, 3),
        "failure_reasons": failure_reasons,
        "secondary_titles": secondary_titles,
        "secondary_doi": secondary_doi,
        "secondary_pmid": secondary_pmid,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Double-verify paper-search citation payloads for revise-sci")
    parser.add_argument("--paper-search-results", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--allow-unverified", action="store_true")
    args = parser.parse_args()

    online_check = args.live and not args.offline
    project_root = Path(args.project_root)
    project_root.mkdir(parents=True, exist_ok=True)
    payload = read_json(Path(args.paper_search_results), {"results": []})
    rows = payload.get("results", []) if isinstance(payload, dict) else payload

    validated_rows = []
    all_rows_guard_verified = True
    verified_citation_count = 0
    total_citation_count = 0

    for row in rows or []:
        citations = []
        for citation in row.get("citations", []) or []:
            checked = validate_citation(citation, online_check=online_check)
            citations.append(checked)
            total_citation_count += 1
            if checked["guard_verified"]:
                verified_citation_count += 1
        row_guard_verified = bool(row.get("confirmed")) and bool(citations) and all(c["guard_verified"] for c in citations)
        if not row_guard_verified:
            all_rows_guard_verified = False
        checked_row = dict(row)
        checked_row["citations"] = citations
        checked_row["guard_verified"] = row_guard_verified
        validated_rows.append(checked_row)

    report = {
        "summary": {
            "rows": len(validated_rows),
            "citations": total_citation_count,
            "verified_citations": verified_citation_count,
            "all_rows_guard_verified": all_rows_guard_verified,
            "online_check": online_check,
            "provider_policy": {"paper_search_only": True, "double_verification_required": True},
        },
        "results": validated_rows,
    }
    write_json(project_root / "paper_search_guard_report.json", report)
    write_json(project_root / "paper_search_validated.json", {"results": validated_rows})

    if not all_rows_guard_verified and not args.allow_unverified:
        print(json.dumps({"ok": False, "summary": report["summary"]}, ensure_ascii=False))
        return 2

    print(json.dumps({"ok": True, "summary": report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Shared citation-verification core (single source of truth).

Pure verification primitives only. No argparse, no file IO, no print. Skill
adapters (citation_guard.py) handle loading, MCP index building, CLI flags, and
report writing; they call validate_core for the actual checks.

Verification strength here is the baseline floor: provider allowlist, online
DOI/PMID resolution, by-title existence when no identifier, per-source title
cross-validation, retraction, year reasonableness, and bounded HTTP retry. To
change a threshold globally, edit this file once and re-mirror it.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
PMID_RE = re.compile(r"^\d{4,10}$")
TITLE_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+")
ALLOWED_PROVIDER_FAMILIES = {"pubmed-cli", "paper-search"}
FORBIDDEN_PROVIDER_FAMILIES = {"websearch", "openalex-cli", "tavily"}
TITLE_VERIFY_THRESHOLD = 0.8


def _http_get_json(
    url: str, timeout_sec: float = 8.0, *, retries: int = 2, backoff_sec: float = 1.5
) -> dict[str, Any] | None:
    """GET JSON with bounded retry/backoff.

    Returns None on any failure (network, HTTP error, bad JSON). Callers MUST
    treat None as "not verified" and never as a pass (fail-closed).
    """
    req = urllib.request.Request(url, headers={"User-Agent": "citation-guard/1.0"})
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            # Retry only on rate-limit / transient server errors.
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(backoff_sec * (2**attempt))
                attempt += 1
                continue
            return None
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(backoff_sec * (2**attempt))
                attempt += 1
                continue
            return None
        except json.JSONDecodeError:
            return None


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


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
    jacc = (len(ta & tb) / len(ta | tb)) if ta and tb else 0.0
    short = min(len(na), len(nb)) / max(len(na), len(nb))
    contain_bonus = 0.1 if (na in nb or nb in na) else 0.0
    return min(1.0, 0.75 * jacc + 0.25 * short + contain_bonus)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    try:
        if len(s) == 10 and s.count("-") == 2:
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _is_mcp_fresh(record: dict[str, Any], ttl_days: int, now_utc: datetime) -> tuple[bool, str | None]:
    if ttl_days <= 0:
        return True, None
    checked_at = _parse_dt(str(record.get("verified_at") or record.get("checked_at") or record.get("retrieved_at") or ""))
    if checked_at is None:
        return False, "mcp_timestamp_missing"
    if checked_at < now_utc - timedelta(days=ttl_days):
        return False, "mcp_stale"
    return True, None


def _fetch_crossref_by_doi(doi: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(doi, safe="")
    payload = _http_get_json(f"https://api.crossref.org/works/{encoded}")
    if not payload or "message" not in payload:
        return None
    msg = payload["message"]
    title = (msg.get("title") or [""])[0] if isinstance(msg.get("title"), list) else ""
    relation = msg.get("relation") or {}
    is_retracted = isinstance(relation, dict) and any("retract" in str(k).lower() for k in relation.keys())
    return {"source": "crossref", "title": title or "", "doi": doi, "pmid": None, "retracted": is_retracted}


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


def _verify_title_exists(title: str) -> dict[str, Any] | None:
    """Confirm an entry with no DOI/PMID corresponds to a real publication.

    Strategy: query Crossref by-title first; if it fails (None) or returns no
    sufficiently-similar match, fall back to Semantic Scholar by-title.
    Returns a match record {source, matched_title, similarity, doi, pmid} when a
    candidate title clears TITLE_VERIFY_THRESHOLD, else None.

    Network failures from _http_get_json are returned as None (fail-closed): the
    caller treats "no match" identically to "not verified". Semantic Scholar is
    rate-limit prone; on its failure we have already tried Crossref, so we simply
    return None rather than crashing.
    """
    if not title.strip():
        return None

    def _best_match(candidates: list[tuple[str, str | None, str | None]], source: str) -> dict[str, Any] | None:
        best: dict[str, Any] | None = None
        for cand_title, cand_doi, cand_pmid in candidates:
            if not cand_title:
                continue
            sim = _title_similarity(title, cand_title)
            if best is None or sim > best["similarity"]:
                best = {
                    "source": source,
                    "matched_title": cand_title,
                    "similarity": sim,
                    "doi": cand_doi,
                    "pmid": cand_pmid,
                }
        if best and best["similarity"] >= TITLE_VERIFY_THRESHOLD:
            return best
        return None

    # 1) Crossref by-title
    cr_url = (
        "https://api.crossref.org/works?"
        + urllib.parse.urlencode({"query.bibliographic": title, "rows": 5})
    )
    cr = _http_get_json(cr_url)
    if cr and isinstance(cr.get("message"), dict):
        items = cr["message"].get("items") or []
        cands: list[tuple[str, str | None, str | None]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            t = (it.get("title") or [""])[0] if isinstance(it.get("title"), list) else ""
            cands.append((str(t or ""), str(it.get("DOI") or "") or None, None))
        match = _best_match(cands, "crossref-bytitle")
        if match:
            return match

    # 2) Semantic Scholar by-title (fallback; rate-limit prone)
    ss_url = (
        "https://api.semanticscholar.org/graph/v1/paper/search?"
        + urllib.parse.urlencode({"query": title, "limit": 5, "fields": "title,externalIds"})
    )
    ss = _http_get_json(ss_url)
    if ss and isinstance(ss.get("data"), list):
        cands = []
        for it in ss["data"]:
            if not isinstance(it, dict):
                continue
            ext = it.get("externalIds") or {}
            doi = str(ext.get("DOI") or "") or None if isinstance(ext, dict) else None
            pmid = str(ext.get("PubMed") or "") or None if isinstance(ext, dict) else None
            cands.append((str(it.get("title") or ""), doi, pmid))
        match = _best_match(cands, "semanticscholar-bytitle")
        if match:
            return match

    return None


def _provider_family(raw: str) -> str:
    """Map a raw provider string to its family.

    Accepts a string (not a dict). Field-name differences across skills stay in
    the adapter layer, which extracts the raw provider value before calling.
    """
    p = str(raw or "").strip().lower()
    if p.startswith("paper-search"):
        return "paper-search"
    if p.startswith("pubmed"):
        return "pubmed-cli"
    if p.startswith("openalex") or p == "pyalex":
        return "openalex-cli"
    if p.startswith("tavily"):
        return "tavily"
    if "websearch" in p or "web-search" in p or "web_search" in p:
        return "websearch"
    return p


def validate_core(
    entry: dict[str, Any],
    *,
    online: bool,
    require_mcp: bool = False,
    mcp_record: dict[str, Any] | None = None,
    require_identifier: bool = False,
    prefetched: dict[str, Any] | None = None,
    mcp_ttl_days: int = 30,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Verify a single normalized citation entry.

    Input entry is the normalized schema produced by the adapter:
        {title, doi, pmid, provider_family, source_id, year}
    plus an optional ``retracted`` flag. ``provider_family`` is already mapped
    via _provider_family by the adapter.

    Switches:
      - require_mcp: when True, unresolved/stale MCP evidence is blocking.
      - require_identifier: when True, an entry with no DOI and no PMID hard-fails
        with ``identifier_missing`` regardless of by-title verification (for nsfc;
        not wired in this phase).
      - prefetched: optional pre-fetched online data to avoid re-hitting APIs.
        Recognized keys: ``crossref`` / ``pubmed`` (records shaped like the
        _fetch_* return values), ``title_verify`` (a _verify_title_exists match).
        When a key is present it is used as-is; when absent the corresponding
        online fetch runs (subject to ``online``).
      - mcp_ttl_days / now_utc: MCP freshness window and clock (adapter supplies).

    Returns a normalized result dict:
        {verified, failure_reasons[], confidence, needs_manual_review, details}
    where ``details`` carries the full per-check breakdown.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    if prefetched is None:
        prefetched = {}

    title = str(entry.get("title") or "").strip()
    doi = str(entry.get("doi") or "").strip()
    pmid = str(entry.get("pmid") or "").strip()
    provider_family = str(entry.get("provider_family") or "").strip().lower()
    source_id = str(entry.get("source_id") or "").strip()

    doi_fmt_ok = DOI_RE.match(doi) is not None if doi else None
    pmid_fmt_ok = PMID_RE.match(pmid) is not None if pmid else None

    mcp_ok = bool(mcp_record)
    mcp_fresh, mcp_fresh_reason = _is_mcp_fresh(mcp_record or {}, mcp_ttl_days, now_utc) if mcp_ok else (False, None)

    # Online fetches honor prefetched cache first (lazy / re-use), else fetch.
    if "crossref" in prefetched:
        crossref = prefetched["crossref"]
    else:
        crossref = _fetch_crossref_by_doi(doi) if (online and doi and doi_fmt_ok) else None
    if "pubmed" in prefetched:
        pubmed = prefetched["pubmed"]
    else:
        pubmed = _fetch_pubmed_by_pmid(pmid) if (online and pmid and pmid_fmt_ok) else None

    has_identifier = bool(doi or pmid)

    # By-title verification: only when the entry carries NO DOI and NO PMID.
    # Confirms the title corresponds to a real publication (Crossref/Semantic
    # Scholar). Gray zone (no match / unreachable / offline) stays FAIL.
    title_verify: dict[str, Any] | None = None
    if not has_identifier and title:
        if "title_verify" in prefetched:
            title_verify = prefetched["title_verify"]
        elif online:
            title_verify = _verify_title_exists(title)
    title_verified = title_verify is not None

    source_titles = []
    for rec in (mcp_record, pubmed, crossref):
        if rec and rec.get("title"):
            source_titles.append(str(rec["title"]))

    title_similarity = max((_title_similarity(title, st) for st in source_titles), default=0.0)
    title_match = bool(source_titles) and title_similarity >= 0.72

    # Per-source title cross-validation: detect spliced/fabricated entries
    crossref_title_sim = _title_similarity(title, crossref["title"]) if (crossref and crossref.get("title") and title) else None
    pubmed_title_sim = _title_similarity(title, pubmed["title"]) if (pubmed and pubmed.get("title") and title) else None
    crossref_title_ok = crossref_title_sim is None or crossref_title_sim >= 0.72
    pubmed_title_ok = pubmed_title_sim is None or pubmed_title_sim >= 0.72

    # Year reasonableness check
    entry_year = entry.get("year")
    year_reasonable = True
    if entry_year is not None:
        try:
            yr = int(entry_year)
            year_reasonable = 1900 <= yr <= now_utc.year + 1
        except (ValueError, TypeError):
            year_reasonable = False

    doi_valid: bool | None
    if doi:
        if not doi_fmt_ok:
            doi_valid = False
        else:
            http_ok = crossref is not None if online else True
            mcp_doi = str((mcp_record or {}).get("doi") or "").strip().lower()
            mcp_ok_doi = (mcp_doi == doi.lower()) if mcp_doi else True
            doi_valid = http_ok and mcp_ok_doi
    else:
        doi_valid = None

    pmid_match: bool | None
    if pmid:
        if not pmid_fmt_ok:
            pmid_match = False
        else:
            http_ok = pubmed is not None if online else True
            mcp_pmid = str((mcp_record or {}).get("pmid") or "").strip()
            mcp_ok_pmid = (mcp_pmid == pmid) if mcp_pmid else True
            pmid_match = http_ok and mcp_ok_pmid
    else:
        pmid_match = None

    id_cross_match = True
    if doi and pmid and pubmed and pubmed.get("doi"):
        id_cross_match = str(pubmed["doi"]).lower() == doi.lower()

    retracted = bool(entry.get("retracted", False))
    for rec in (mcp_record, pubmed, crossref):
        if rec and rec.get("retracted"):
            retracted = True

    has_traceability = bool(provider_family and source_id)

    failure_reasons: list[str] = []
    if not title:
        failure_reasons.append("title_missing")
    if provider_family in FORBIDDEN_PROVIDER_FAMILIES:
        failure_reasons.append("source_provider_forbidden")
    elif provider_family and provider_family not in ALLOWED_PROVIDER_FAMILIES:
        failure_reasons.append("source_provider_not_allowed")
    if not has_identifier:
        # No DOI/PMID. require_identifier makes this an unconditional hard fail;
        # otherwise only acceptable if by-title verification found a real,
        # high-similarity match (else blocking + manual review below).
        if require_identifier:
            failure_reasons.append("identifier_missing")
        elif not title_verified:
            failure_reasons.append("identifier_missing")
            if online and title:
                failure_reasons.append("title_not_found_online")
    if title and source_titles and not title_match:
        failure_reasons.append("title_mismatch")
    if not crossref_title_ok:
        failure_reasons.append("crossref_title_mismatch")
    if not pubmed_title_ok:
        failure_reasons.append("pubmed_title_mismatch")
    if not year_reasonable:
        failure_reasons.append("year_unreasonable")
    if doi_valid is False:
        failure_reasons.append("doi_invalid_or_unresolved")
    if pmid_match is False:
        failure_reasons.append("pmid_invalid_or_unresolved")
    if not id_cross_match:
        failure_reasons.append("id_mismatch")
    if retracted:
        failure_reasons.append("retracted")
    if not has_traceability:
        failure_reasons.append("source_trace_missing")
    if require_mcp:
        if not mcp_ok:
            failure_reasons.append("mcp_unresolved")
        elif not mcp_fresh:
            failure_reasons.append(mcp_fresh_reason or "mcp_stale")
    elif mcp_ok and (not mcp_fresh):
        failure_reasons.append("mcp_stale_warning")
    if online and has_identifier and not (crossref or pubmed):
        failure_reasons.append("source_unreachable")

    bidirectional_verification_failed = any(
        r in {"title_mismatch", "crossref_title_mismatch", "pubmed_title_mismatch",
              "doi_invalid_or_unresolved", "pmid_invalid_or_unresolved", "id_mismatch"}
        for r in failure_reasons
    )
    if bidirectional_verification_failed:
        failure_reasons.append("manual_confirmation_required_bidirectional_failure")

    needs_manual_review = any(
        r in {"title_mismatch", "id_mismatch", "mcp_stale", "mcp_timestamp_missing",
              "source_unreachable", "identifier_missing", "title_not_found_online"}
        for r in failure_reasons
    ) or bidirectional_verification_failed

    score = 0.0
    score += (title_similarity * 35) if source_titles else 15  # neutral when no sources to compare
    if doi_valid is True:
        score += 18
    elif doi_valid is False:
        score -= 8
    if pmid_match is True:
        score += 18
    elif pmid_match is False:
        score -= 8
    score += 10 if id_cross_match else -12
    score += 8 if has_traceability else -15
    if provider_family in ALLOWED_PROVIDER_FAMILIES:
        score += 6
    elif provider_family in FORBIDDEN_PROVIDER_FAMILIES:
        score -= 20
    elif provider_family:
        score -= 10
    score += (8 if mcp_ok else (-10 if require_mcp else 0))
    if mcp_ok:
        score += 6 if mcp_fresh else -8
    score += (8 if (crossref or pubmed) else -8) if online else 4
    if not has_identifier:
        score += 12 if title_verified else -12
    if not crossref_title_ok:
        score -= 15
    if not pubmed_title_ok:
        score -= 15
    if not year_reasonable:
        score -= 10
    if retracted:
        score -= 60
    confidence = int(max(0, min(100, round(score))))

    verified = (len(failure_reasons) == 0) and (not bidirectional_verification_failed)

    details = {
        "checked_at": now_utc.isoformat(),
        "title_match": title_match,
        "title_similarity": round(title_similarity, 4),
        "title_verified": title_verified,
        "title_verify_source": (title_verify.get("source") if title_verify else None),
        "title_verify_similarity": (round(title_verify["similarity"], 4) if title_verify else None),
        "title_verify_matched_title": (title_verify.get("matched_title") if title_verify else None),
        "crossref_title_similarity": round(crossref_title_sim, 4) if crossref_title_sim is not None else None,
        "pubmed_title_similarity": round(pubmed_title_sim, 4) if pubmed_title_sim is not None else None,
        "crossref_fetched_title": (crossref["title"] if crossref and crossref.get("title") else None),
        "pubmed_fetched_title": (pubmed["title"] if pubmed and pubmed.get("title") else None),
        "year_reasonable": year_reasonable,
        "doi_valid": doi_valid,
        "pmid_match": pmid_match,
        "id_cross_match": id_cross_match,
        "bidirectional_verification_failed": bidirectional_verification_failed,
        "retracted": retracted,
        "has_traceability": has_traceability,
        "failure_reasons": failure_reasons,
        "confidence_score": confidence,
        "needs_manual_review": needs_manual_review,
        "sources": {
            "mcp": bool(mcp_record),
            "pubmed": bool(pubmed),
            "crossref": bool(crossref),
            "online_check": online,
            "mcp_ttl_days": mcp_ttl_days,
            "require_mcp": require_mcp,
            "provider_family": provider_family,
        },
    }

    return {
        "verified": verified,
        "failure_reasons": failure_reasons,
        "confidence": confidence,
        "needs_manual_review": needs_manual_review,
        "details": details,
    }

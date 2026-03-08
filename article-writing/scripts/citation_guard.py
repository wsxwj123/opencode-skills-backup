#!/usr/bin/env python3
"""Unified citation hallucination guard for multiple writing skills.

Goals:
- Prevent fabricated references
- Prevent citation-index mismatch
- Enforce DOI/PMID/title/source traceability checks
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
PMID_RE = re.compile(r"^\d{4,10}$")
TITLE_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+")
ALLOWED_PROVIDER_FAMILIES = {"paper-search", "tavily"}
FORBIDDEN_PROVIDER_FAMILIES = {"websearch"}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    checked_at = _parse_dt(str(record.get("verified_at") or record.get("checked_at") or ""))
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


def _normalize_index(raw: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)], "list"
    if isinstance(raw, dict):
        for key in ("entries", "papers", "items", "references", "data"):
            val = raw.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)], key
        vals = [v for v in raw.values() if isinstance(v, dict)]
        if vals:
            return vals, "dict_values"
    return [], "empty"


def _build_mcp_index(mcp_cache: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not mcp_cache:
        return out

    entries: list[dict[str, Any]] = []
    if isinstance(mcp_cache, list):
        entries.extend(x for x in mcp_cache if isinstance(x, dict))
    elif isinstance(mcp_cache, dict):
        for key in ("entries", "papers", "items", "references", "data"):
            val = mcp_cache.get(key)
            if isinstance(val, list):
                entries.extend(x for x in val if isinstance(x, dict))
        for k, v in mcp_cache.items():
            if k in {"entries", "papers", "items", "references", "data"}:
                continue
            if isinstance(v, dict):
                entries.append(v)

    for e in entries:
        doi = str(e.get("doi") or "").strip().lower()
        pmid = str(e.get("pmid") or "").strip()
        if doi:
            out[f"doi:{doi}"] = e
        if pmid:
            out[f"pmid:{pmid}"] = e
    return out


def _resolve_mcp_record(entry: dict[str, Any], mcp_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    doi = str(entry.get("doi") or "").strip().lower()
    pmid = str(entry.get("pmid") or "").strip()
    if doi and f"doi:{doi}" in mcp_index:
        return mcp_index[f"doi:{doi}"]
    if pmid and f"pmid:{pmid}" in mcp_index:
        return mcp_index[f"pmid:{pmid}"]
    return None


def _entry_ref_id(entry: dict[str, Any], fallback_idx: int) -> str:
    for k in ("ref_number", "global_id", "id"):
        v = entry.get(k)
        if v is not None:
            return str(v)
    return f"idx:{fallback_idx}"


def _provider_family(provider: str) -> str:
    p = str(provider or "").strip().lower()
    if p.startswith("paper-search"):
        return "paper-search"
    if p.startswith("tavily"):
        return "tavily"
    if "websearch" in p or "web-search" in p or "web_search" in p:
        return "websearch"
    return p


def _extract_tavily_title(entry: dict[str, Any]) -> str:
    for k in ("tavily_title", "tavily_verified_title", "reverse_verified_title", "web_title"):
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def validate_entry(
    entry: dict[str, Any],
    *,
    online_check: bool,
    mcp_index: dict[str, dict[str, Any]],
    require_mcp: bool,
    mcp_ttl_days: int,
    now_utc: datetime,
) -> dict[str, Any]:
    title = str(entry.get("title") or "").strip()
    doi = str(entry.get("doi") or "").strip()
    pmid = str(entry.get("pmid") or "").strip()

    source_provider = str(entry.get("source_provider") or "").strip()
    source_id = str(entry.get("source_id") or "").strip()
    provider_family = _provider_family(source_provider)

    doi_fmt_ok = DOI_RE.match(doi) is not None if doi else None
    pmid_fmt_ok = PMID_RE.match(pmid) is not None if pmid else None

    mcp_record = _resolve_mcp_record(entry, mcp_index)
    mcp_ok = bool(mcp_record)
    mcp_fresh, mcp_fresh_reason = _is_mcp_fresh(mcp_record or {}, mcp_ttl_days, now_utc) if mcp_ok else (False, None)

    crossref = _fetch_crossref_by_doi(doi) if (online_check and doi and doi_fmt_ok) else None
    pubmed = _fetch_pubmed_by_pmid(pmid) if (online_check and pmid and pmid_fmt_ok) else None

    source_titles = []
    for rec in (mcp_record, pubmed, crossref):
        if rec and rec.get("title"):
            source_titles.append(str(rec["title"]))
    if provider_family == "tavily":
        tavily_title = _extract_tavily_title(entry)
        if tavily_title:
            source_titles.append(tavily_title)

    title_similarity = max((_title_similarity(title, st) for st in source_titles), default=0.0)
    title_match = bool(source_titles) and title_similarity >= 0.72

    doi_valid: bool | None
    if doi:
        if not doi_fmt_ok:
            doi_valid = False
        else:
            http_ok = crossref is not None if online_check else True
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
            http_ok = pubmed is not None if online_check else True
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

    has_traceability = bool(source_provider and source_id)
    has_identifier = bool(doi or pmid)
    tavily_no_identifier = (provider_family == "tavily" and not has_identifier)

    failure_reasons: list[str] = []
    if not title:
        failure_reasons.append("title_missing")
    if provider_family in FORBIDDEN_PROVIDER_FAMILIES:
        failure_reasons.append("source_provider_forbidden")
    elif provider_family and provider_family not in ALLOWED_PROVIDER_FAMILIES:
        failure_reasons.append("source_provider_not_allowed")
    if not has_identifier and not tavily_no_identifier:
        failure_reasons.append("identifier_missing")
    if provider_family == "tavily" and has_identifier:
        failure_reasons.append("tavily_not_for_identifier_entries")
    if tavily_no_identifier:
        failure_reasons.append("tavily_manual_review_required")
    if title and not title_match:
        failure_reasons.append("title_mismatch")
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
    if online_check and not (crossref or pubmed) and not tavily_no_identifier:
        failure_reasons.append("source_unreachable")

    bidirectional_verification_failed = any(
        r in {"title_mismatch", "doi_invalid_or_unresolved", "pmid_invalid_or_unresolved", "id_mismatch"}
        for r in failure_reasons
    )
    if bidirectional_verification_failed:
        failure_reasons.append("manual_confirmation_required_bidirectional_failure")

    needs_manual_review = any(
        r in {"title_mismatch", "id_mismatch", "mcp_stale", "mcp_timestamp_missing", "source_unreachable"}
        for r in failure_reasons
    ) or tavily_no_identifier or bidirectional_verification_failed

    score = 0.0
    score += title_similarity * 35
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
    score += (8 if (crossref or pubmed) else -8) if online_check else 4
    if retracted:
        score -= 60
    confidence = int(max(0, min(100, round(score))))

    verified = (len(failure_reasons) == 0) and (not bidirectional_verification_failed)

    return {
        **entry,
        "verified": verified,
        "needs_manual_review": needs_manual_review,
        "verification_confidence": confidence,
        "verification_details": {
            "checked_at": now_utc.isoformat(),
            "title_match": title_match,
            "title_similarity": round(title_similarity, 4),
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
                "online_check": online_check,
                "mcp_ttl_days": mcp_ttl_days,
                "require_mcp": require_mcp,
                "source_provider": source_provider,
                "provider_family": provider_family,
                "tavily_no_identifier": tavily_no_identifier,
            },
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Unified anti-hallucination citation guard")
    p.add_argument("--index", required=True, help="Path to literature index JSON")
    p.add_argument("--mcp-cache", default="", help="Path to MCP cache JSON")
    p.add_argument("--offline", action="store_true", help="Disable online check")
    p.add_argument("--mcp-ttl-days", type=int, default=30)
    p.add_argument("--require-mcp", action="store_true", help="Require MCP evidence; unresolved/stale MCP is blocking")
    p.add_argument("--manual-review", default="data/manual_review_queue.json")
    p.add_argument("--log", default="data/verification_run_log.json")
    p.add_argument("--report", default="data/citation_guard_report.json")
    p.add_argument("--write-back", action="store_true", help="Write verification fields back to index")
    args = p.parse_args()

    index_path = Path(args.index)
    raw = load_json(index_path, {})
    entries, shape = _normalize_index(raw)

    mcp_cache = load_json(Path(args.mcp_cache), {}) if args.mcp_cache else {}
    mcp_index = _build_mcp_index(mcp_cache)

    t0 = time.perf_counter()
    now_utc = datetime.now(timezone.utc)
    checked = [
        validate_entry(
            dict(e),
            online_check=not args.offline,
            mcp_index=mcp_index,
            require_mcp=args.require_mcp,
            mcp_ttl_days=max(0, int(args.mcp_ttl_days)),
            now_utc=now_utc,
        )
        for e in entries
    ]

    failure_counter: Counter[str] = Counter()
    manual = []
    for i, e in enumerate(checked, 1):
        vd = e.get("verification_details", {})
        for r in vd.get("failure_reasons", []):
            failure_counter[str(r)] += 1
        if e.get("needs_manual_review"):
            manual.append(
                {
                    "ref_id": _entry_ref_id(e, i),
                    "title": e.get("title"),
                    "doi": e.get("doi"),
                    "pmid": e.get("pmid"),
                    "failure_reasons": vd.get("failure_reasons", []),
                    "confidence_score": vd.get("confidence_score"),
                }
            )

    verified_count = sum(1 for e in checked if e.get("verified"))
    duration_ms = int((time.perf_counter() - t0) * 1000)
    status = "verified" if verified_count == len(checked) and checked else ("failed" if checked else "empty")

    report = {
        "ok": status == "verified",
        "status": status,
        "shape": shape,
        "checked_entries": len(checked),
        "verified_count": verified_count,
        "manual_review_count": len(manual),
        "avg_confidence": round(sum(int(e.get("verification_confidence", 0)) for e in checked) / len(checked), 2)
        if checked
        else 0.0,
        "failure_type_counts": dict(sorted(failure_counter.items())),
        "duration_ms": duration_ms,
        "checked_at": now_utc.isoformat(),
        "online_check": not args.offline,
        "require_mcp": bool(args.require_mcp),
        "mcp_ttl_days": max(0, int(args.mcp_ttl_days)),
        "provider_policy": {
            "allowed_provider_families": sorted(ALLOWED_PROVIDER_FAMILIES),
            "forbidden_provider_families": sorted(FORBIDDEN_PROVIDER_FAMILIES),
            "tavily_only_for_no_identifier": True,
        },
    }

    save_json(Path(args.report), {"report": report, "manual_review_queue": manual})
    save_json(Path(args.manual_review), {"generated_at": now_utc.isoformat(), "count": len(manual), "entries": manual})

    run_log_path = Path(args.log)
    logs = load_json(run_log_path, {"runs": []})
    if not isinstance(logs, dict):
        logs = {"runs": []}
    runs = logs.get("runs") if isinstance(logs.get("runs"), list) else []
    runs.append(report)
    logs["runs"] = runs[-200:]
    save_json(run_log_path, logs)

    if args.write_back:
        if isinstance(raw, list):
            save_json(index_path, checked)
        elif isinstance(raw, dict):
            out = dict(raw)
            if shape in {"entries", "papers", "items", "references", "data"}:
                out[shape] = checked
            else:
                out["entries"] = checked
            md = out.get("metadata") if isinstance(out.get("metadata"), dict) else {}
            md.update({"verification_status": status, "last_updated": now_utc.isoformat(), "verification_stats": report})
            out["metadata"] = md
            save_json(index_path, out)

    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

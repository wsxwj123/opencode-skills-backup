#!/usr/bin/env python3
"""Citation validation and matrix checks for nsfc-proposal.

Dual-track validation:
- Track A: MCP evidence cache (paper-search results)
- Track B: Official HTTP sources (PubMed/Crossref)
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
CIT_RE = re.compile(r"\[(\d+)\]")
TITLE_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_citation_numbers(text: str) -> list[int]:
    return [int(x) for x in CIT_RE.findall(text)]


def _http_get_json(url: str, timeout_sec: float = 8.0) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": "nsfc-proposal-skill/1.0"})
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

    # fallback char overlap ratio for small token sets
    short = min(len(na), len(nb)) / max(len(na), len(nb))
    contain_bonus = 0.1 if (na in nb or nb in na) else 0.0
    return min(1.0, 0.75 * jacc + 0.25 * short + contain_bonus)


def _titles_match(a: str, b: str, threshold: float = 0.72) -> tuple[bool, float]:
    score = _title_similarity(a, b)
    return score >= threshold, score


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
    is_retracted = False
    if isinstance(relation, dict):
        for k in relation.keys():
            if "retract" in str(k).lower():
                is_retracted = True
                break

    return {
        "source": "crossref",
        "title": title or "",
        "doi": doi,
        "pmid": None,
        "retracted": is_retracted,
    }


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

    return {
        "source": "pubmed",
        "title": title,
        "doi": doi,
        "pmid": str(pmid),
        "retracted": is_retracted,
    }


def _build_mcp_index(mcp_cache: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not mcp_cache:
        return out

    entries: list[dict[str, Any]] = []
    if isinstance(mcp_cache, dict):
        if isinstance(mcp_cache.get("entries"), list):
            entries.extend(x for x in mcp_cache.get("entries", []) if isinstance(x, dict))
        for k, v in mcp_cache.items():
            if k == "entries":
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


def _context_check(entry: dict[str, Any], p1_text: str | None) -> bool | None:
    if "P1_立项依据" not in (entry.get("used_in_sections") or []):
        return None
    if p1_text is None:
        return None

    ref = entry.get("ref_number")
    if ref is None:
        return False

    cited = f"[{ref}]" in p1_text
    key_finding = (entry.get("key_finding") or "").strip()
    if not key_finding:
        return False

    return cited


def _confidence_score(
    *,
    title_similarity: float,
    doi_valid: bool | None,
    pmid_match: bool | None,
    id_cross_match: bool,
    mcp_ok: bool,
    mcp_fresh: bool,
    http_ok: bool,
    online_check: bool,
    retracted: bool,
    context_check: bool | None,
) -> int:
    score = 0.0
    score += max(0.0, min(1.0, title_similarity)) * 35.0

    if doi_valid is True:
        score += 18
    elif doi_valid is False:
        score -= 8

    if pmid_match is True:
        score += 18
    elif pmid_match is False:
        score -= 8

    score += 10 if id_cross_match else -12

    if mcp_ok:
        score += 8
    if mcp_ok and not mcp_fresh:
        score -= 10

    if online_check:
        score += 8 if http_ok else -8
    else:
        score += 4

    if context_check is True:
        score += 3
    elif context_check is False:
        score -= 6

    if retracted:
        score -= 60

    return int(max(0, min(100, round(score))))


def validate_entry(
    entry: dict[str, Any],
    p1_text: str | None = None,
    online_check: bool = True,
    mcp_index: dict[str, dict[str, Any]] | None = None,
    mcp_ttl_days: int = 30,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now_utc = now_utc or datetime.now(timezone.utc)

    doi = (entry.get("doi") or "").strip()
    pmid = str(entry.get("pmid") or "").strip()
    title = (entry.get("title") or "").strip()

    doi_fmt_ok = DOI_RE.match(doi) is not None if doi else None
    pmid_fmt_ok = PMID_RE.match(pmid) is not None if pmid else None

    mcp_record = _resolve_mcp_record(entry, mcp_index or {}) if mcp_index else None
    mcp_title = str((mcp_record or {}).get("title") or "").strip()
    mcp_ok = bool(mcp_record)
    mcp_fresh, mcp_fresh_reason = _is_mcp_fresh(mcp_record or {}, mcp_ttl_days, now_utc) if mcp_ok else (False, None)

    crossref_attempted = bool(online_check and doi and doi_fmt_ok)
    pubmed_attempted = bool(online_check and pmid and pmid_fmt_ok)
    crossref = _fetch_crossref_by_doi(doi) if crossref_attempted else None
    pubmed = _fetch_pubmed_by_pmid(pmid) if pubmed_attempted else None

    source_titles = []
    if mcp_title:
        source_titles.append(("mcp", mcp_title))
    if pubmed and pubmed.get("title"):
        source_titles.append(("pubmed", str(pubmed["title"])))
    if crossref and crossref.get("title"):
        source_titles.append(("crossref", str(crossref["title"])))

    title_match = False
    title_similarity = 0.0
    if source_titles:
        sims = [(_titles_match(title, st)[1], src) for src, st in source_titles]
        title_similarity = max((s for s, _ in sims), default=0.0)
        title_match = title_similarity >= 0.72

    pmid_match: bool | None
    if pmid:
        if not pmid_fmt_ok:
            pmid_match = False
        else:
            mcp_pmid = str((mcp_record or {}).get("pmid") or "").strip()
            http_ok_for_pmid = pubmed is not None if online_check else True
            mcp_ok_for_pmid = (mcp_pmid == pmid) if mcp_record and mcp_pmid else True
            pmid_match = http_ok_for_pmid and mcp_ok_for_pmid
    else:
        pmid_match = None

    doi_valid: bool | None
    if doi:
        if not doi_fmt_ok:
            doi_valid = False
        else:
            mcp_doi = str((mcp_record or {}).get("doi") or "").strip().lower()
            http_ok_for_doi = crossref is not None if online_check else True
            mcp_ok_for_doi = (mcp_doi == doi.lower()) if mcp_record and mcp_doi else True
            doi_valid = http_ok_for_doi and mcp_ok_for_doi
    else:
        doi_valid = None

    id_cross_match = True
    if doi and pmid and pubmed and pubmed.get("doi"):
        id_cross_match = str(pubmed.get("doi")).lower() == doi.lower()

    retracted = bool(entry.get("retracted", False))
    if mcp_record and bool(mcp_record.get("retracted", False)):
        retracted = True
    if crossref and crossref.get("retracted"):
        retracted = True
    if pubmed and pubmed.get("retracted"):
        retracted = True

    context_check = _context_check(entry, p1_text)

    http_ok = bool(crossref or pubmed) if online_check else True
    sources = {
        "mcp": bool(mcp_record),
        "crossref": bool(crossref),
        "pubmed": bool(pubmed),
        "crossref_attempted": crossref_attempted,
        "pubmed_attempted": pubmed_attempted,
        "online_check": online_check,
        "mcp_ttl_days": mcp_ttl_days,
    }

    failure_reasons = []
    if not title:
        failure_reasons.append("title_missing")
    if title_match is False:
        failure_reasons.append("title_mismatch")
    if doi_valid is False:
        failure_reasons.append("doi_invalid_or_unresolved")
    if pmid_match is False:
        failure_reasons.append("pmid_invalid_or_unresolved")
    if not id_cross_match:
        failure_reasons.append("id_mismatch")
    if retracted is True:
        failure_reasons.append("retracted")
    if not doi and not pmid:
        failure_reasons.append("identifier_missing")
    if context_check is False:
        failure_reasons.append("context_mismatch")

    if not mcp_ok:
        failure_reasons.append("mcp_unresolved")
    elif not mcp_fresh:
        failure_reasons.append(mcp_fresh_reason or "mcp_stale")

    if online_check and not http_ok:
        failure_reasons.append("source_unreachable")

    conflict_reasons = {"title_mismatch", "id_mismatch", "mcp_stale", "mcp_timestamp_missing", "source_unreachable"}
    needs_manual_review = any(r in conflict_reasons for r in failure_reasons)

    confidence_score = _confidence_score(
        title_similarity=title_similarity,
        doi_valid=doi_valid,
        pmid_match=pmid_match,
        id_cross_match=id_cross_match,
        mcp_ok=mcp_ok,
        mcp_fresh=mcp_fresh,
        http_ok=http_ok,
        online_check=online_check,
        retracted=retracted,
        context_check=context_check,
    )

    verified = len(failure_reasons) == 0

    details = {
        "title_match": title_match,
        "title_similarity": round(title_similarity, 4),
        "doi_valid": doi_valid,
        "pmid_match": pmid_match,
        "id_cross_match": id_cross_match,
        "retracted": retracted,
        "context_check": context_check,
        "checked_at": now_utc.isoformat(),
        "sources": sources,
        "failure_reasons": failure_reasons,
        "needs_manual_review": needs_manual_review,
        "confidence_score": confidence_score,
    }

    entry["verification_details"] = details
    entry["verified"] = verified
    entry["verification_confidence"] = confidence_score
    entry["needs_manual_review"] = needs_manual_review
    return entry


def _normalize_index(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = dict(raw)
        entries = data.get("entries")
        if not isinstance(entries, list):
            data["entries"] = []
        data.setdefault("metadata", {})
        return data
    if isinstance(raw, list):
        return {"metadata": {}, "entries": raw}
    return {"metadata": {}, "entries": []}


def verify_all(
    index: dict[str, Any] | list[dict[str, Any]],
    p1_text: str | None = None,
    online_check: bool = True,
    mcp_index: dict[str, dict[str, Any]] | None = None,
    mcp_ttl_days: int = 30,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    idx = _normalize_index(index)
    entries = idx.get("entries", [])

    t0 = time.perf_counter()
    now_utc = datetime.now(timezone.utc)

    out = [
        validate_entry(
            dict(e),
            p1_text=p1_text,
            online_check=online_check,
            mcp_index=mcp_index,
            mcp_ttl_days=mcp_ttl_days,
            now_utc=now_utc,
        )
        for e in entries
    ]

    all_ok = all(e.get("verified") for e in out) if out else False
    any_ok = any(e.get("verified") for e in out)
    status = "verified" if all_ok else ("partial" if any_ok else "failed")

    failure_counter: Counter[str] = Counter()
    confidence_values = []
    manual_review_queue = []
    for e in out:
        vd = e.get("verification_details", {})
        confidence_values.append(int(vd.get("confidence_score", 0)))
        for reason in vd.get("failure_reasons", []):
            failure_counter[str(reason)] += 1
        if e.get("needs_manual_review"):
            manual_review_queue.append(
                {
                    "ref_number": e.get("ref_number"),
                    "title": e.get("title"),
                    "doi": e.get("doi"),
                    "pmid": e.get("pmid"),
                    "failure_reasons": vd.get("failure_reasons", []),
                    "confidence_score": vd.get("confidence_score"),
                }
            )

    duration_ms = int((time.perf_counter() - t0) * 1000)

    stats_payload = {
        "checked_entries": len(out),
        "verified_count": sum(1 for e in out if e.get("verified")),
        "manual_review_count": len(manual_review_queue),
        "avg_confidence": round((sum(confidence_values) / len(confidence_values)), 2) if confidence_values else 0.0,
        "failure_type_counts": dict(sorted(failure_counter.items())),
        "duration_ms": duration_ms,
        "online_check": online_check,
        "mcp_ttl_days": mcp_ttl_days,
        "checked_at": now_utc.isoformat(),
    }

    idx["entries"] = out
    idx.setdefault("metadata", {})["verification_status"] = status
    idx["metadata"]["last_updated"] = now_utc.isoformat()
    idx["metadata"]["total_count"] = len(out)
    idx["metadata"]["recent_5yr_count"] = sum(1 for e in out if e.get("is_recent_5yr"))
    idx["metadata"]["cn_journal_count"] = sum(1 for e in out if e.get("is_cn_journal"))
    idx["metadata"]["mcp_entries_count"] = len(mcp_index or {})
    idx["metadata"]["verification_stats"] = stats_payload

    return idx, stats_payload, manual_review_queue


def _ordered_unique(values: list[int]) -> list[int]:
    seen = set()
    ordered = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        ordered.append(v)
    return ordered


def matrix_check(p1_text: str, index: dict[str, Any], ref_text: str) -> dict[str, Any]:
    p1_refs_all = extract_citation_numbers(p1_text)
    p1_refs = set(p1_refs_all)

    idx_refs = {
        int(e.get("ref_number"))
        for e in index.get("entries", [])
        if e.get("ref_number") is not None and "P1_立项依据" in (e.get("used_in_sections") or [])
    }

    ref_refs_all = extract_citation_numbers(ref_text)
    ref_refs = set(ref_refs_all)

    orphan_citations = sorted(p1_refs - idx_refs)
    orphan_entries = sorted(idx_refs - p1_refs)
    ref_missing = sorted(p1_refs - ref_refs)
    ref_extra = sorted(ref_refs - p1_refs)

    p1_first_order = _ordered_unique(p1_refs_all)
    ref_order = _ordered_unique(ref_refs_all)
    order_match = p1_first_order == ref_order

    three_way_match = p1_refs == idx_refs == ref_refs
    ok = not orphan_citations and not orphan_entries and not ref_missing and not ref_extra and order_match and three_way_match

    return {
        "ok": ok,
        "orphan_citations": orphan_citations,
        "orphan_entries": orphan_entries,
        "ref_missing": ref_missing,
        "ref_extra": ref_extra,
        "order_match": order_match,
        "three_way_match": three_way_match,
        "p1_first_order": p1_first_order,
        "ref_order": ref_order,
        "p1_count": len(p1_refs),
        "index_count": len(idx_refs),
        "ref_count": len(ref_refs),
    }


def find_orphans(p1_text: str, index: dict[str, Any]) -> dict[str, list[int]]:
    p1_refs = set(extract_citation_numbers(p1_text))
    idx_refs = {
        int(e.get("ref_number"))
        for e in index.get("entries", [])
        if e.get("ref_number") is not None and "P1_立项依据" in (e.get("used_in_sections") or [])
    }
    return {
        "orphan_citations": sorted(p1_refs - idx_refs),
        "orphan_entries": sorted(idx_refs - p1_refs),
    }


def reorder_entries_by_p1(index: dict[str, Any], p1_text: str) -> dict[str, Any]:
    order = _ordered_unique(extract_citation_numbers(p1_text))
    by_ref = {int(e["ref_number"]): e for e in index.get("entries", []) if e.get("ref_number") is not None}

    new_entries: list[dict[str, Any]] = []
    for n in order:
        if n in by_ref:
            new_entries.append(by_ref[n])

    for n in sorted(by_ref.keys()):
        if n not in order:
            new_entries.append(by_ref[n])

    for i, e in enumerate(new_entries, 1):
        e["ref_number"] = i

    index["entries"] = new_entries
    index.setdefault("metadata", {})["last_updated"] = datetime.now(timezone.utc).isoformat()
    return index


def stats(index: dict[str, Any]) -> dict[str, Any]:
    entries = index.get("entries", [])
    meta = index.get("metadata", {})
    return {
        "total": len(entries),
        "recent_5yr": sum(1 for e in entries if e.get("is_recent_5yr")),
        "cn_journal": sum(1 for e in entries if e.get("is_cn_journal")),
        "verified": sum(1 for e in entries if e.get("verified")),
        "unverified": sum(1 for e in entries if not e.get("verified")),
        "manual_review": sum(1 for e in entries if e.get("needs_manual_review")),
        "avg_confidence": round(
            (sum(int((e.get("verification_details") or {}).get("confidence_score", 0)) for e in entries) / len(entries)), 2
        )
        if entries
        else 0,
        "last_run_stats": meta.get("verification_stats", {}),
    }


def _save_manual_review_queue(path: Path, queue: list[dict[str, Any]]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(queue),
        "entries": queue,
    }
    save_json(path, payload)


def _append_verification_log(path: Path, record: dict[str, Any]) -> None:
    existing = load_json(path, {"runs": []})
    if not isinstance(existing, dict):
        existing = {"runs": []}
    runs = existing.get("runs")
    if not isinstance(runs, list):
        runs = []
    runs.append(record)
    existing["runs"] = runs[-200:]
    save_json(path, existing)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_verify_all = sub.add_parser("verify-all")
    p_verify_all.add_argument("--index", default="data/literature_index.json")
    p_verify_all.add_argument("--p1", default="sections/P1_立项依据.md")
    p_verify_all.add_argument("--offline", action="store_true")
    p_verify_all.add_argument("--mcp-cache", default="data/mcp_literature_cache.json")
    p_verify_all.add_argument("--mcp-ttl-days", type=int, default=30)
    p_verify_all.add_argument("--manual-review", default="data/manual_review_queue.json")
    p_verify_all.add_argument("--log", default="data/verification_run_log.json")

    p_verify_entry = sub.add_parser("verify-entry")
    p_verify_entry.add_argument("--index", default="data/literature_index.json")
    p_verify_entry.add_argument("--p1", default="sections/P1_立项依据.md")
    p_verify_entry.add_argument("--ref-number", type=int, required=True)
    p_verify_entry.add_argument("--offline", action="store_true")
    p_verify_entry.add_argument("--mcp-cache", default="data/mcp_literature_cache.json")
    p_verify_entry.add_argument("--mcp-ttl-days", type=int, default=30)

    p_matrix = sub.add_parser("matrix-check")
    p_matrix.add_argument("--p1", default="sections/P1_立项依据.md")
    p_matrix.add_argument("--index", default="data/literature_index.json")
    p_matrix.add_argument("--ref", default="sections/REF_参考文献.md")

    p_orphans = sub.add_parser("find-orphans")
    p_orphans.add_argument("--p1", default="sections/P1_立项依据.md")
    p_orphans.add_argument("--index", default="data/literature_index.json")

    p_reorder = sub.add_parser("reorder")
    p_reorder.add_argument("--p1", default="sections/P1_立项依据.md")
    p_reorder.add_argument("--index", default="data/literature_index.json")

    p_stats = sub.add_parser("stats")
    p_stats.add_argument("--index", default="data/literature_index.json")

    args = parser.parse_args()

    mcp_cache = load_json(Path(getattr(args, "mcp_cache", "")), {"entries": []}) if getattr(args, "mcp_cache", None) else {"entries": []}
    mcp_index = _build_mcp_index(mcp_cache)

    if args.cmd == "verify-all":
        index_path = Path(args.index)
        raw = load_json(index_path, {"metadata": {}, "entries": []})
        idx = _normalize_index(raw)
        p1_text = Path(args.p1).read_text(encoding="utf-8") if Path(args.p1).exists() else None

        idx, run_stats, queue = verify_all(
            idx,
            p1_text=p1_text,
            online_check=not args.offline,
            mcp_index=mcp_index,
            mcp_ttl_days=max(0, int(args.mcp_ttl_days)),
        )
        save_json(index_path, idx)
        _save_manual_review_queue(Path(args.manual_review), queue)
        _append_verification_log(Path(args.log), {
            "index": str(index_path),
            "verification_status": idx.get("metadata", {}).get("verification_status"),
            **run_stats,
        })

        print(
            json.dumps(
                {
                    "ok": True,
                    "verification_status": idx["metadata"].get("verification_status"),
                    "manual_review_count": len(queue),
                    "avg_confidence": run_stats.get("avg_confidence"),
                    "duration_ms": run_stats.get("duration_ms"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.cmd == "verify-entry":
        index_path = Path(args.index)
        raw = load_json(index_path, {"metadata": {}, "entries": []})
        idx = _normalize_index(raw)
        p1_text = Path(args.p1).read_text(encoding="utf-8") if Path(args.p1).exists() else None
        updated = False
        for i, entry in enumerate(idx.get("entries", [])):
            if int(entry.get("ref_number", -1)) == args.ref_number:
                idx["entries"][i] = validate_entry(
                    dict(entry),
                    p1_text=p1_text,
                    online_check=not args.offline,
                    mcp_index=mcp_index,
                    mcp_ttl_days=max(0, int(args.mcp_ttl_days)),
                )
                updated = True
                break
        if not updated:
            print(json.dumps({"ok": False, "error": "ref_number not found"}, ensure_ascii=False))
            return 2
        save_json(index_path, idx)
        print(json.dumps({"ok": True, "ref_number": args.ref_number}, ensure_ascii=False))
        return 0

    if args.cmd == "matrix-check":
        raw = load_json(Path(args.index), {"metadata": {}, "entries": []})
        idx = _normalize_index(raw)
        p1_text = Path(args.p1).read_text(encoding="utf-8") if Path(args.p1).exists() else ""
        ref_text = Path(args.ref).read_text(encoding="utf-8") if Path(args.ref).exists() else ""
        print(json.dumps(matrix_check(p1_text, idx, ref_text), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "find-orphans":
        raw = load_json(Path(args.index), {"metadata": {}, "entries": []})
        idx = _normalize_index(raw)
        p1_text = Path(args.p1).read_text(encoding="utf-8") if Path(args.p1).exists() else ""
        print(json.dumps(find_orphans(p1_text, idx), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "reorder":
        index_path = Path(args.index)
        raw = load_json(index_path, {"metadata": {}, "entries": []})
        idx = _normalize_index(raw)
        p1_text = Path(args.p1).read_text(encoding="utf-8") if Path(args.p1).exists() else ""
        idx = reorder_entries_by_p1(idx, p1_text)
        save_json(index_path, idx)
        print(json.dumps({"ok": True, "count": len(idx.get("entries", []))}, ensure_ascii=False))
        return 0

    if args.cmd == "stats":
        raw = load_json(Path(args.index), {"metadata": {}, "entries": []})
        idx = _normalize_index(raw)
        print(json.dumps(stats(idx), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

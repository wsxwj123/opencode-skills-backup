#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from urllib import error, parse, request

from citation_utils import extract_citation_ids


def scan_drafts(root_dir):
    used_ids = set()

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".md"):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    used_ids.update(str(x) for x in extract_citation_ids(content))
    return used_ids


def load_index(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get("papers", list(data.values()))

    if not isinstance(data, list):
        raise ValueError("literature_index.json must be a list or a dict with 'papers'.")

    entries = []
    for item in data:
        if not isinstance(item, dict):
            continue
        gid = item.get("global_id")
        if isinstance(gid, int) and gid > 0:
            entries.append(item)

    return entries


def validate_local(used_ids, index_entries):
    index_ids = {str(item["global_id"]) for item in index_entries}
    orphans = used_ids - index_ids
    unused = index_ids - used_ids
    return orphans, unused


def validate_traceability(index_entries):
    failures = []
    for item in index_entries:
        gid = item.get("global_id")
        title = str(item.get("title") or "").strip()
        src_provider = str(item.get("source_provider") or "").strip()
        src_id = str(item.get("source_id") or "").strip()
        doi = str(item.get("doi") or "").strip()
        pmid = str(item.get("pmid") or "").strip()

        if not title:
            failures.append((gid, "title_missing", "title is empty"))
        if not (doi or pmid):
            failures.append((gid, "identifier_missing", "missing DOI/PMID"))
        if not (src_provider and src_id):
            failures.append((gid, "source_trace_missing", "missing source_provider/source_id"))
    return failures


def check_doi_online(doi, timeout=8):
    url = "https://api.crossref.org/works/" + parse.quote(doi)
    req = request.Request(url, headers={"User-Agent": "review-writing-validator/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            return False, f"HTTP {resp.status}"
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
        returned = (
            data.get("message", {}).get("DOI", "")
            if isinstance(data, dict)
            else ""
        )
        if returned and returned.lower() == doi.lower():
            return True, "ok"
        return False, "DOI mismatch"


def check_pmid_online(pmid, timeout=8):
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        + parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "json"})
    )
    req = request.Request(url, headers={"User-Agent": "review-writing-validator/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            return False, f"HTTP {resp.status}"
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
        result = data.get("result", {}) if isinstance(data, dict) else {}
        item = result.get(str(pmid), {}) if isinstance(result, dict) else {}
        if isinstance(item, dict) and item.get("uid"):
            return True, "ok"
        return False, "PMID not found"


def _is_transient_error(reason):
    text = str(reason).lower()
    transient_tokens = ["urlerror", "timed out", "timeout", "temporary", "429", "500", "502", "503", "504"]
    return any(tok in text for tok in transient_tokens)


def _check_with_retry(identifier, checker, timeout=8, retries=2, backoff=0.6):
    attempts = 0
    while True:
        attempts += 1
        try:
            ok, reason = checker(identifier, timeout=timeout)
        except error.HTTPError as e:
            ok, reason = False, f"HTTPError {e.code}"
        except error.URLError as e:
            ok, reason = False, f"URLError {e.reason}"
        except Exception as e:  # noqa: BLE001
            ok, reason = False, f"Error {e}"

        if ok:
            return True, reason, attempts
        if attempts > retries or not _is_transient_error(reason):
            return False, reason, attempts
        time.sleep(backoff * (2 ** (attempts - 1)))


def validate_live(index_entries, timeout=8, retries=2, backoff=0.6):
    checked = 0
    passed = 0
    failures = []

    for item in index_entries:
        gid = item["global_id"]
        doi = str(item.get("doi", "")).strip()
        pmid = str(item.get("pmid", "")).strip()

        if not doi and not pmid:
            failures.append((gid, "missing_identifier", "Need DOI or PMID for live validation"))
            continue

        checked += 1

        if doi:
            ok, reason, attempts = _check_with_retry(
                doi,
                check_doi_online,
                timeout=timeout,
                retries=retries,
                backoff=backoff,
            )
        else:
            ok, reason, attempts = _check_with_retry(
                pmid,
                check_pmid_online,
                timeout=timeout,
                retries=retries,
                backoff=backoff,
            )

        if ok:
            passed += 1
        else:
            failures.append((gid, "live_check_failed", f"{reason} (attempts={attempts})"))

    return {
        "checked": checked,
        "passed": passed,
        "failed": len(failures),
        "failures": failures,
    }


def filter_entries_by_used_ids(index_entries, used_ids):
    return [item for item in index_entries if str(item.get("global_id")) in used_ids]


def main():
    parser = argparse.ArgumentParser(description="Validate citation integrity for review-writing projects")
    parser.add_argument("--drafts-dir", default="drafts", help="Draft markdown directory")
    parser.add_argument(
        "--index-path",
        default=os.path.join("data", "literature_index.json"),
        help="Path to literature_index.json",
    )
    parser.add_argument("--live", action="store_true", help="Run online DOI/PMID validation")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP timeout seconds for live checks")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for transient live-check failures")
    parser.add_argument("--retry-backoff", type=float, default=0.6, help="Base backoff seconds for live-check retries")
    parser.add_argument(
        "--live-used-only",
        action="store_true",
        help="When used with --live, validate only citations actually referenced in drafts",
    )
    parser.add_argument("--fail-on-orphan", action="store_true", help="Exit non-zero if orphan citations exist")
    parser.add_argument("--fail-on-live", action="store_true", help="Exit non-zero if live checks fail")
    parser.add_argument("--fail-on-trace", action="store_true", help="Exit non-zero if source traceability checks fail")
    args = parser.parse_args()

    if not os.path.exists(args.drafts_dir):
        print(f"Error: Drafts directory not found at {args.drafts_dir}")
        sys.exit(1)

    if not os.path.exists(args.index_path):
        print(f"Error: Index file not found at {args.index_path}")
        sys.exit(1)

    used_ids = scan_drafts(args.drafts_dir)
    try:
        entries = load_index(args.index_path)
    except Exception as e:  # noqa: BLE001
        print(f"Error loading index: {e}")
        sys.exit(1)

    orphans, unused = validate_local(used_ids, entries)

    print("-" * 40)
    print("VALIDATION REPORT")
    print("-" * 40)
    print(f"Draft citations: {len(used_ids)}")
    print(f"Index entries (with valid global_id): {len(entries)}")

    if orphans:
        print(f"[CRITICAL] Orphan citations: {', '.join(sorted(orphans, key=int))}")
    else:
        print("[OK] No orphan citations")

    if unused:
        print(f"[WARNING] Unused index entries: {', '.join(sorted(unused, key=int))}")
    else:
        print("[OK] No unused index entries")

    trace_failures = validate_traceability(entries)
    if trace_failures:
        print("-" * 40)
        print("TRACEABILITY CHECK")
        print("-" * 40)
        for gid, code, reason in trace_failures:
            print(f"[TRACE-FAIL] global_id={gid} code={code} reason={reason}")
    else:
        print("[OK] Traceability checks passed")

    live_failures = 0
    if args.live:
        target_entries = entries
        if args.live_used_only:
            target_entries = filter_entries_by_used_ids(entries, used_ids)
        live = validate_live(
            target_entries,
            timeout=args.timeout,
            retries=max(0, args.retries),
            backoff=max(0.0, args.retry_backoff),
        )
        live_failures = live["failed"]
        print("-" * 40)
        print("LIVE DOI/PMID CHECK")
        print("-" * 40)
        print(
            f"Checked: {live['checked']}  Passed: {live['passed']}  Failed: {live['failed']}"
        )
        for gid, code, reason in live["failures"]:
            print(f"[LIVE-FAIL] global_id={gid} code={code} reason={reason}")

    should_fail = (
        (args.fail_on_orphan and bool(orphans))
        or (args.fail_on_live and live_failures > 0)
        or (args.fail_on_trace and bool(trace_failures))
    )
    if should_fail:
        sys.exit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""统一抓取执行器：多路线抓取、质量判定、轻量清洗。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
URL_ROUTER = SCRIPT_DIR / "url-converter.py"
QUALITY = SCRIPT_DIR / "assess_fetch_quality.py"
CLEANER = SCRIPT_DIR / "clean_fetched_markdown.py"

ONLINE_SERVICES = ["markdown.new", "defuddle.md", "r.jina.ai"]
SCRAPLING_COMMANDS = [
    ["scrapling", "extract", "get"],
    ["scrapling", "extract", "stealthy-fetch", "--timeout", "45000", "--network-idle"],
    ["scrapling", "extract", "fetch", "--timeout", "45000", "--network-idle"],
]


def run_cmd(cmd: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def assess_text(text: str) -> Dict:
    proc = run_cmd([sys.executable, str(QUALITY)], input_text=text)
    if proc.returncode != 0:
        return {"score": -999, "passed": False, "reasons": [proc.stderr.strip() or "quality_failed"]}
    return json.loads(proc.stdout)


def clean_text(text: str) -> str:
    proc = run_cmd([sys.executable, str(CLEANER)], input_text=text)
    if proc.returncode != 0:
        return text
    return proc.stdout


def fetch_via_online_services(url: str) -> List[Dict]:
    results: List[Dict] = []
    for service in ONLINE_SERVICES:
        conv = run_cmd([sys.executable, str(URL_ROUTER), "--url", url, "--service", service])
        if conv.returncode != 0:
            continue
        service_url = conv.stdout.strip()
        content = run_cmd([sys.executable, str(URL_ROUTER), "--url", url, "--service", service, "--get-content"])
        if content.returncode != 0:
            continue
        text = content.stdout
        results.append({
            "method": f"online:{service}",
            "service_url": service_url,
            "content": text,
        })
    return results


def fetch_via_scrapling(url: str) -> List[Dict]:
    results: List[Dict] = []
    for base_cmd in SCRAPLING_COMMANDS:
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        cmd = list(base_cmd) + [url, str(tmp_path)]
        proc = run_cmd(cmd)
        if proc.returncode != 0 or not tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            continue
        text = tmp_path.read_text(encoding="utf-8", errors="ignore")
        results.append({
            "method": " ".join(base_cmd),
            "content": text,
            "stderr": proc.stderr.strip(),
        })
        tmp_path.unlink(missing_ok=True)
    return results


def choose_best(candidates: List[Dict]) -> Optional[Dict]:
    best = None
    for item in candidates:
        cleaned = clean_text(item["content"])
        quality = assess_text(cleaned)
        item["cleaned_content"] = cleaned
        item["quality"] = quality
        if best is None or quality["score"] > best["quality"]["score"]:
            best = item
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="统一抓取执行器")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 元信息")
    args = parser.parse_args()

    candidates: List[Dict] = []
    candidates.extend(fetch_via_online_services(args.url))
    candidates.extend(fetch_via_scrapling(args.url))

    best = choose_best(candidates)
    if not best:
        print(json.dumps({"url": args.url, "status": "failed", "reason": "no_candidate"}, ensure_ascii=False, indent=2))
        sys.exit(2)

    cleaned = best.get("cleaned_content", clean_text(best["content"]))
    result = {
        "url": args.url,
        "status": "success" if best["quality"].get("passed") else "partial",
        "method": best["method"],
        "score": best["quality"]["score"],
        "reasons": best["quality"]["reasons"],
        "content": cleaned,
    }

    if args.output:
        Path(args.output).write_text(cleaned, encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(cleaned)


if __name__ == "__main__":
    main()

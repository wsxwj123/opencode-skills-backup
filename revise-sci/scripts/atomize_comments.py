#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import AtomicCommentHTMLParser, detect_comments_input_mode, is_meaningful_text, normalize_ws, read_docx_paragraphs, read_json, write_json


def reviewer_number(reviewer: str) -> int:
    match = re.search(r"(\d+)", reviewer)
    return int(match.group(1)) if match else 1


def is_editor_reviewer(reviewer: str) -> bool:
    lowered = normalize_ws(reviewer).lower()
    return lowered.startswith("editor") or lowered.startswith("associate editor") or lowered == "decision letter"


def format_comment_id(reviewer: str, severity: str, index: int) -> str:
    prefix = "E" if is_editor_reviewer(reviewer) else f"R{reviewer_number(reviewer)}"
    return f"{prefix}-{severity.capitalize()}-{index:02d}"


def detect_language(text: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", text or "") else "en"


def merge_statement(existing: str, new_text: str) -> str:
    current = normalize_ws(existing)
    incoming = normalize_ws(new_text)
    if not incoming:
        return current
    if not current:
        return incoming
    if incoming in current:
        return current
    if current in incoming:
        return incoming
    return normalize_ws(f"{current} {incoming}")


def normalize_reviewer_label(text: str) -> str:
    match = re.search(r"reviewer\s*#?\s*(\d+)", text, flags=re.IGNORECASE)
    if match:
        return f"Reviewer #{int(match.group(1))}"
    return normalize_ws(text)


def parse_reviewer_heading(text: str) -> tuple[str, str]:
    match = re.match(r"^(Reviewer\s*#?\s*\d+)\s*(?:[:：-]\s*(.+))?$", text, flags=re.IGNORECASE)
    if not match:
        return "", ""
    return normalize_reviewer_label(match.group(1)), normalize_ws(match.group(2) or "")


def parse_editor_heading(text: str) -> tuple[str, str]:
    match = re.match(
        r"^(editor(?:ial)?(?:\s+(?:comments?|email|letter|decision letter))?|associate editor(?:\s+comments?)?|decision letter)\s*(?:[:：-]\s*(.+))?$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    return "Editor", normalize_ws(match.group(2) or "")


def parse_statement_label(text: str) -> tuple[bool, str]:
    match = re.match(
        r"^(overall (?:statement|assessment)|general assessment|general comments?|reviewer statement|summary|comments to the author)\s*[:：-]?\s*(.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return True, normalize_ws(match.group(2) or "")
    return False, ""


def parse_docx_comments(path: Path) -> list[dict[str, str]]:
    rows = read_docx_paragraphs(path)
    comments: list[dict[str, str]] = []
    comment_input_mode = detect_comments_input_mode(path)
    current_reviewer = "Editor"
    current_severity = "major"
    current_text: list[str] = []
    current_comment_id = ""
    current_statement_target = ""
    current_statement_text: list[str] = []
    reviewer_statements: dict[str, str] = {}
    editor_statement = ""
    expect_prefatory_statement = True

    def flush_current() -> None:
        nonlocal current_text, current_comment_id
        if not current_text or not current_comment_id:
            return
        comments.append(
            {
                "comment_id": current_comment_id,
                "reviewer": current_reviewer,
                "severity": current_severity,
                "comment_text": normalize_ws(" ".join(current_text)),
                "comment_lang": detect_language(" ".join(current_text)),
                "comment_input_mode": comment_input_mode,
                "reviewer_statement_seed": reviewer_statements.get(current_reviewer, ""),
                "editor_statement_seed": editor_statement,
                "comment_role": "editor-comment" if is_editor_reviewer(current_reviewer) else "reviewer-comment",
            }
        )
        current_text = []
        current_comment_id = ""

    def flush_statement() -> None:
        nonlocal current_statement_target, current_statement_text, editor_statement
        statement = normalize_ws(" ".join(current_statement_text))
        if not statement or not current_statement_target:
            current_statement_target = ""
            current_statement_text = []
            return
        if current_statement_target == "editor":
            editor_statement = merge_statement(editor_statement, statement)
        else:
            reviewer_statements[current_statement_target] = merge_statement(
                reviewer_statements.get(current_statement_target, ""),
                statement,
            )
        current_statement_target = ""
        current_statement_text = []

    severity_counters: dict[tuple[str, str], int] = {}

    def start_new_comment(text: str) -> None:
        nonlocal current_text, current_comment_id
        key = (current_reviewer, current_severity)
        severity_counters[key] = severity_counters.get(key, 0) + 1
        current_comment_id = format_comment_id(current_reviewer, current_severity, severity_counters[key])
        current_text = [text]

    for row in rows:
        text = row["text"]
        reviewer, reviewer_trailing = parse_reviewer_heading(text)
        if reviewer:
            flush_current()
            flush_statement()
            current_reviewer = reviewer
            current_severity = "major"
            expect_prefatory_statement = True
            if reviewer_trailing:
                current_statement_target = current_reviewer
                current_statement_text = [reviewer_trailing]
                expect_prefatory_statement = False
            continue
        editor_reviewer, editor_trailing = parse_editor_heading(text)
        if editor_reviewer:
            flush_current()
            flush_statement()
            current_reviewer = editor_reviewer
            current_severity = "major"
            expect_prefatory_statement = True
            if editor_trailing:
                current_statement_target = "editor"
                current_statement_text = [editor_trailing]
                expect_prefatory_statement = False
            continue
        lowered = text.lower()
        if lowered in {"major", "major comments", "major comment"}:
            flush_current()
            flush_statement()
            current_severity = "major"
            expect_prefatory_statement = False
            continue
        if lowered in {"minor", "minor comments", "minor comment"}:
            flush_current()
            flush_statement()
            current_severity = "minor"
            expect_prefatory_statement = False
            continue
        is_statement, statement_trailing = parse_statement_label(text)
        if is_statement:
            flush_current()
            flush_statement()
            current_statement_target = "editor" if is_editor_reviewer(current_reviewer) else current_reviewer
            current_statement_text = [statement_trailing] if statement_trailing else []
            expect_prefatory_statement = False
            continue
        match = re.match(r"^(?:comment\s*)?(\d+)\s*[\.\)\:\-]\s*(.+)$", text, flags=re.IGNORECASE)
        if match:
            flush_current()
            flush_statement()
            start_new_comment(match.group(2))
            expect_prefatory_statement = False
            continue
        if current_statement_target:
            current_statement_text.append(text)
            continue
        if current_text:
            current_text.append(text)
            continue
        if expect_prefatory_statement or is_editor_reviewer(current_reviewer):
            current_statement_target = "editor" if is_editor_reviewer(current_reviewer) else current_reviewer
            current_statement_text = [text]
            expect_prefatory_statement = False
            continue
        start_new_comment(text)
        expect_prefatory_statement = False
    flush_current()
    flush_statement()
    return comments


def parse_html_comments(path: Path) -> list[dict[str, str]]:
    parser = AtomicCommentHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    units = []
    for item in parser.units:
        units.append(
            {
                "comment_id": item["comment_id"] or format_comment_id(item["reviewer"], item["severity"], len(units) + 1),
                "reviewer": item["reviewer"],
                "severity": item["severity"],
                "comment_text": item["comment_text"],
                "comment_lang": detect_language(item["comment_text"]),
                "comment_input_mode": "atomic-comment-html",
            }
        )
    if units:
        return units

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return units

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    response_units = parse_reviewer_response_html(soup)
    if response_units:
        return response_units

    reviewer = "Reviewer #1"
    severity_counters: dict[str, int] = {"major": 0, "minor": 0}
    for section in soup.select("section.critique-section"):
        heading = normalize_ws(section.find("h2").get_text(" ", strip=True) if section.find("h2") else "")
        if "必须解决的核心问题" in heading:
            severity = "major"
        elif "其他改进建议" in heading:
            severity = "minor"
        else:
            continue
        for item in section.select("ul.critique-list > li"):
            title = normalize_ws(item.select_one(".critique-title").get_text(" ", strip=True) if item.select_one(".critique-title") else "")
            parts = [title] if title else []
            for selector in (".critique-content", ".evidence-anchor", ".root-cause", ".response-strategy"):
                node = item.select_one(selector)
                if node:
                    parts.append(normalize_ws(node.get_text(" ", strip=True)))
            if not parts:
                continue
            severity_counters[severity] += 1
            comment_text = normalize_ws(" ".join(parts))
            units.append(
                {
                    "comment_id": format_comment_id(reviewer, severity, severity_counters[severity]),
                    "reviewer": reviewer,
                    "severity": severity,
                    "comment_text": comment_text,
                    "comment_lang": detect_language(comment_text),
                    "comment_title": title,
                    "problem_description": normalize_ws(item.select_one(".critique-content").get_text(" ", strip=True) if item.select_one(".critique-content") else ""),
                    "evidence_anchor": normalize_ws(item.select_one(".evidence-anchor").get_text(" ", strip=True) if item.select_one(".evidence-anchor") else ""),
                    "root_cause": normalize_ws(item.select_one(".root-cause").get_text(" ", strip=True) if item.select_one(".root-cause") else ""),
                    "author_strategy": normalize_ws(item.select_one(".response-strategy").get_text(" ", strip=True) if item.select_one(".response-strategy") else ""),
                    "comment_input_mode": "reviewer-simulator-html",
                }
            )
    return units


def first_meaningful_text(values: list[str]) -> str:
    for value in values:
        cleaned = normalize_ws(value)
        if is_meaningful_text(cleaned):
            return cleaned
    return ""


def strip_seed_prefixes(text: str) -> str:
    cleaned = normalize_ws(text)
    patterns = (
        r"^(?:中文对应|对应中文修订说明|审稿人核心关切|中文说明|Interpretation|How to interpret)\s*[:：]\s*",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return normalize_ws(cleaned)


def heading_text(node) -> str:
    heading = node.find(["h2", "h3", "h4"])
    return normalize_ws(heading.get_text(" ", strip=True) if heading else "")


def card_for_heading(section, keywords: tuple[str, ...]):
    cards = section.find_all(class_="card", recursive=False)
    if not cards:
        cards = section.find_all(class_="card")
    for card in cards:
        title = heading_text(card).lower()
        if any(keyword.lower() in title for keyword in keywords):
            return card
    return None


def card_value_by_label(card, labels: tuple[str, ...]) -> str:
    if not card:
        return ""
    for box in card.select(".stack-box"):
        label = heading_text(box).lower()
        if any(target.lower() in label for target in labels):
            paragraphs = [normalize_ws(p.get_text(" ", strip=True)) for p in box.find_all("p")]
            value = strip_seed_prefixes(first_meaningful_text(paragraphs))
            if value:
                return value
    paragraphs = [normalize_ws(p.get_text(" ", strip=True)) for p in card.find_all("p", recursive=False)]
    return strip_seed_prefixes(first_meaningful_text(paragraphs))


def parse_revision_location(card) -> str:
    if not card:
        return ""
    candidates = []
    for box in card.select(".stack-box"):
        label = heading_text(box).lower()
        if "定位" in label or "location" in label:
            candidates.extend(normalize_ws(p.get_text(" ", strip=True)) for p in box.find_all("p"))
    return first_meaningful_text(candidates)


def parse_evidence_anchors(card) -> str:
    if not card:
        return ""
    anchors: list[str] = []
    for paragraph in card.find_all("p"):
        text = normalize_ws(paragraph.get_text(" ", strip=True))
        if text.lower().startswith("anchors:") or text.startswith("Anchors:"):
            anchors.append(normalize_ws(text.split(":", 1)[1] if ":" in text else text))
    return first_meaningful_text(anchors)


def parse_reviewer_response_header(section, fallback_index: int) -> tuple[str, str, str]:
    header = normalize_ws(section.find("h2").get_text(" ", strip=True) if section.find("h2") else "")
    reviewer = "Reviewer #1"
    severity = "major"
    comment_number = str(fallback_index)
    match = re.search(r"Reviewer\s*#?(\d+)\s*\|\s*(MAJOR|MINOR)\s*\|\s*Comment\s*(\d+)", header, flags=re.IGNORECASE)
    if match:
        reviewer = f"Reviewer #{match.group(1)}"
        severity = match.group(2).lower()
        comment_number = match.group(3)
        return reviewer, severity, comment_number
    meta = normalize_ws(section.get_text(" ", strip=True))
    meta_match = re.search(r"Comment ID:\s*(R\d+)-(Major|Minor)-(\d+)", meta, flags=re.IGNORECASE)
    if meta_match:
        reviewer_match = re.search(r"R(\d+)", meta_match.group(1))
        reviewer = f"Reviewer #{reviewer_match.group(1)}" if reviewer_match else reviewer
        severity = meta_match.group(2).lower()
        comment_number = str(int(meta_match.group(3)))
    return reviewer, severity, comment_number


def parse_reviewer_response_html(soup) -> list[dict[str, str]]:
    sections = [
        section
        for section in soup.find_all("section")
        if re.match(r"page-u-(?!000-email)", section.get("id", ""), flags=re.IGNORECASE)
    ]
    if not sections:
        title = normalize_ws(soup.find("title").get_text(" ", strip=True) if soup.find("title") else "")
        if "reviewer response" not in title.lower():
            return []
        sections = [soup.find("body") or soup]
    units: list[dict[str, str]] = []
    severity_counters: dict[tuple[str, str], int] = {}
    for fallback_index, section in enumerate(sections, start=1):
        reviewer, severity, comment_number = parse_reviewer_response_header(section, fallback_index)
        reviewer_card = card_for_heading(section, ("reviewer comment", "审稿人意图理解", "reviewer intent"))
        response_card = card_for_heading(section, ("response to reviewer",))
        revision_card = card_for_heading(section, ("可能需要修改的正文", "revision candidate", "revised text"))
        notes_card = card_for_heading(section, ("修改说明",))
        evidence_card = card_for_heading(section, ("evidence attachments",))

        comment_original = first_meaningful_text(
            [
                card_value_by_label(reviewer_card, ("原始审稿意见", "reviewer comment", "reviewer comment (bilingual)", "english")),
                card_value_by_label(reviewer_card, ("审稿意见英文摘要", "how to interpret", "english summary")),
            ]
        )
        if not comment_original:
            continue

        key = (reviewer, severity)
        comment_index = int(comment_number) if comment_number.isdigit() else severity_counters.get(key, 0) + 1
        severity_counters[key] = max(severity_counters.get(key, 0), comment_index)
        comment_id = format_comment_id(reviewer, severity, comment_index)

        response_en = card_value_by_label(response_card, ("english response", "english"))
        response_zh = card_value_by_label(response_card, ("中文对照", "中文回应", "chinese"))
        original_excerpt = card_value_by_label(revision_card, ("original text",))
        revised_excerpt_en = card_value_by_label(revision_card, ("revised text",))
        revised_excerpt_zh = card_value_by_label(revision_card, ("修改后中文对照", "中文对照"))
        revision_location = parse_revision_location(revision_card)
        notes_summary = first_meaningful_text(
            [
                card_value_by_label(reviewer_card, ("应如何理解", "how to interpret")),
                normalize_ws(notes_card.get_text(" ", strip=True)) if notes_card else "",
            ]
        )
        evidence_anchor = parse_evidence_anchors(evidence_card)

        units.append(
            {
                "comment_id": comment_id,
                "reviewer": reviewer,
                "severity": severity,
                "comment_text": comment_original,
                "comment_lang": detect_language(comment_original),
                "comment_title": normalize_ws(section.find("h2").get_text(" ", strip=True) if section.find("h2") else ""),
                "problem_description": notes_summary,
                "evidence_anchor": evidence_anchor,
                "root_cause": "",
                "author_strategy": response_en or response_zh,
                "comment_input_mode": "reviewer-response-sci-html",
                "response_seed_en": response_en,
                "response_seed_zh": response_zh,
                "original_excerpt_seed_en": original_excerpt,
                "revised_excerpt_seed_en": revised_excerpt_en,
                "revised_excerpt_seed_zh": revised_excerpt_zh,
                "revision_location_seed": revision_location,
            }
        )
    return units


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomize review comments into comment units")
    parser.add_argument("--comments", required=True)
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    comments_path = Path(args.comments)
    project_root = Path(args.project_root)
    units_dir = project_root / "units"
    units_dir.mkdir(parents=True, exist_ok=True)

    if comments_path.suffix.lower() == ".html":
        parsed = parse_html_comments(comments_path)
    else:
        parsed = parse_docx_comments(comments_path)

    for idx, item in enumerate(parsed, start=1):
        payload = {
            "comment_id": item["comment_id"],
            "reviewer": item["reviewer"],
            "severity": item["severity"],
            "reviewer_comment_original": item["comment_text"],
            "reviewer_comment_lang": item.get("comment_lang", detect_language(item["comment_text"])),
            "reviewer_comment_en": item["comment_text"],
            "reviewer_comment_zh_literal": "",
            "reviewer_comment_en_summary": "",
            "intent_zh": "",
            "response_zh": "",
            "response_en": "",
            "atomic_location": {},
            "original_excerpt_en": "",
            "revised_excerpt_en": "",
            "revised_excerpt_zh": "",
            "modification_actions": [],
            "notes_core_zh": [],
            "notes_support_zh": [],
            "evidence_sources": [],
            "target_document": "",
            "status": "not_started",
            "author_confirmation_reason": "",
            "comment_title": item.get("comment_title", ""),
            "problem_description": item.get("problem_description", ""),
            "evidence_anchor": item.get("evidence_anchor", ""),
            "root_cause": item.get("root_cause", ""),
            "author_strategy": item.get("author_strategy", ""),
            "comment_input_mode": item.get("comment_input_mode", "raw-comments"),
            "response_seed_en": item.get("response_seed_en", ""),
            "response_seed_zh": item.get("response_seed_zh", ""),
            "original_excerpt_seed_en": item.get("original_excerpt_seed_en", ""),
            "revised_excerpt_seed_en": item.get("revised_excerpt_seed_en", ""),
            "revised_excerpt_seed_zh": item.get("revised_excerpt_seed_zh", ""),
            "revision_location_seed": item.get("revision_location_seed", ""),
            "reviewer_statement_seed": item.get("reviewer_statement_seed", ""),
            "editor_statement_seed": item.get("editor_statement_seed", ""),
            "comment_role": item.get("comment_role", "reviewer-comment"),
        }
        write_json(units_dir / f"{idx:03d}_{item['comment_id']}.json", payload)

    state = read_json(project_root / "project_state.json", {})
    state.setdefault("counts", {})
    state["counts"]["comment_units"] = len(parsed)
    write_json(project_root / "project_state.json", state)

    print(json.dumps({"ok": True, "count": len(parsed)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

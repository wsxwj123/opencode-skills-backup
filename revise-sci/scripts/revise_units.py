#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import build_section_markdown, choose_sentence, comment_nature, detect_comment_requirements, normalize_ws, read_json, tokenize, write_json, write_text


def best_location(comment_text: str, section_index: dict) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
    sections = section_index.get("sections", [])
    if not sections:
        return None, None, -1
    query = tokenize(comment_text)
    best_section = sections[0]
    best_para = sections[0]["paragraphs"][0] if sections[0]["paragraphs"] else None
    best_score = -1
    for section in sections:
        for paragraph in section.get("paragraphs", []):
            score = len(query.intersection(tokenize(paragraph["text"])))
            if section["heading"]:
                score += len(query.intersection(tokenize(section["heading"])))
            if score > best_score:
                best_score = score
                best_section = section
                best_para = paragraph
    return best_section, best_para, best_score


def infer_target_document(comment_text: str, has_si: bool) -> str:
    lowered = comment_text.lower()
    if has_si and any(token in lowered for token in ("supplementary", "figure s", "table s", "si ")):
        return "si"
    return "manuscript"


def resolve_citation_anchor(citation_payload: dict[str, Any] | None, section_index: dict) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not citation_payload:
        return None, None
    target_section_heading = normalize_ws(str(citation_payload.get("target_section_heading", "")))
    target_paragraph_index = citation_payload.get("target_paragraph_index")
    target_text = normalize_ws(str(citation_payload.get("target_text", "")))
    if not target_section_heading and target_paragraph_index is None and not target_text:
        return None, None
    for section in section_index.get("sections", []):
        heading = normalize_ws(section.get("heading", ""))
        if target_section_heading and heading != target_section_heading:
            continue
        for paragraph in section.get("paragraphs", []):
            if target_paragraph_index is not None and paragraph.get("paragraph_index") != target_paragraph_index:
                continue
            if target_text and target_text not in normalize_ws(paragraph.get("text", "")):
                continue
            return section, paragraph
        if target_section_heading and target_paragraph_index is None and not target_text and section.get("paragraphs"):
            return section, section["paragraphs"][0]
    return None, None


def literal_translate_comment(comment_text: str) -> str:
    text = normalize_ws(comment_text)
    lowered = text.lower()
    replacements = [
        (r"^please clarify ", "请澄清"),
        (r"^please explain ", "请解释"),
        (r"^please expand ", "请扩展说明"),
        (r"^please add ", "请补充"),
        (r"^add a citation for ", "请为以下内容补充参考文献："),
        (r"^correct the typo in ", "请更正以下部分的拼写错误："),
    ]
    for pattern, prefix in replacements:
        if re.search(pattern, lowered):
            remainder = re.sub(pattern, "", text, flags=re.IGNORECASE).rstrip(".")
            return f"{prefix}{remainder}。"
    return f"需作者确认的忠实翻译：{text}"


def editorial_intent(comment_text: str) -> str:
    lowered = comment_text.lower()
    if re.search(r"\b(clarify|clarification|rephrase|reword|wording|scope|overstate|tone down|temper)\b", lowered):
        return "clarify"
    if re.search(r"\b(limitation|limitations)\b", lowered):
        return "limitation"
    if re.search(r"\b(citation|citations|reference|references)\b", lowered):
        return "citation"
    return ""


def assess_status(
    comment_text: str,
    requirements: dict[str, bool],
    section: dict[str, Any] | None,
    paragraph: dict[str, Any] | None,
    best_score: int,
    citation_payload: dict[str, Any] | None,
    citation_anchor_ok: bool,
) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    intent = editorial_intent(comment_text)
    if not section or not paragraph or (best_score <= 0 and intent != "citation"):
        reasons.append("当前无法将该评论可靠定位到原稿中的具体段落。")
    if requirements["needs_experiment"]:
        reasons.append("当前材料未提供新增实验或结果。")
    if requirements["needs_citation"] and not (citation_payload and citation_payload.get("confirmed")):
        reasons.append("当前材料未提供已确认的新文献信息；如需补充检索，必须仅使用 paper-search。")
    if intent == "citation" and citation_payload and citation_payload.get("confirmed") and not citation_anchor_ok:
        reasons.append("citation 类评论缺少明确的目标章节或段落锚点，当前不能安全地自动写回正文。")
    if requirements["needs_figure"]:
        reasons.append("图表或补充材料相关修改需要作者确认具体变更内容。")
    if not intent and not reasons:
        reasons.append("该评论属于实质性解释或论证要求，当前无法在不引入新证据的情况下自动完成。")
    if intent == "citation" and citation_payload and citation_payload.get("confirmed") and not reasons:
        return "completed", intent, []
    status = "completed" if intent and not reasons else "needs_author_confirmation"
    return status, intent, reasons


def revise_paragraph(original_excerpt: str, intent: str, citation_payload: dict[str, Any] | None = None) -> str:
    sentence = normalize_ws(original_excerpt)
    if not sentence:
        return "无"
    if intent == "clarify":
        if sentence.lower().startswith("in the present dataset,"):
            return sentence
        return f"In the present dataset, {sentence}"
    if intent == "limitation":
        limitation_sentence = "This finding should be interpreted within the scope of the present study design."
        if limitation_sentence.lower() in sentence.lower():
            return sentence
        return f"{sentence} {limitation_sentence}"
    if intent == "citation" and citation_payload:
        citation_text = normalize_ws(citation_payload.get("formatted_citation_text", ""))
        if citation_text and citation_text not in sentence:
            return f"{sentence} {citation_text}".strip()
    return sentence


def response_blocks(unit: dict, status: str, needs_reason: str, intent: str) -> tuple[str, str]:
    if status == "completed":
        if intent == "clarify":
            return (
                "感谢审稿人的宝贵意见。我们已将相关表述收紧为仅基于本文当前数据的观察，避免超出证据边界的泛化结论，并同步更新了正文。",
                "We thank the reviewer for this valuable comment. We tightened the statement so that it is explicitly limited to the observation supported by the present dataset, thereby avoiding over-generalization beyond the available evidence, and revised the manuscript accordingly.",
            )
        if intent == "limitation":
            return (
                "感谢审稿人的建议。我们已在对应段落中直接补充研究局限性的说明，使讨论与当前证据边界保持一致。",
                "We thank the reviewer for this suggestion. We added an explicit limitation statement to the relevant paragraph so that the discussion remains aligned with the boundary of the current evidence.",
            )
        if intent == "citation":
            return (
                "感谢审稿人的建议。我们已根据已确认的 paper-search 检索结果补入对应参考文献信息，并在回复中保留来源追踪。",
                "We thank the reviewer for this suggestion. We incorporated the corresponding reference support based on confirmed paper-search results and preserved the source trace in the response package.",
            )
        return (
            "感谢审稿人的宝贵意见。我们已依据该意见修订相关表述，并确保回复内容与正文改动保持一致。",
            "We thank the reviewer for this valuable comment. We have revised the relevant text accordingly and aligned the response with the manuscript changes.",
        )
    reason = needs_reason or "当前材料仍需作者确认。"
    return (
        f"感谢审稿人的重要建议。根据当前用户提供材料，我们已完成定位、问题拆解和可执行修订草案，但该条仍需作者确认：{reason}",
        f"We thank the reviewer for this important comment. Based on the materials currently provided by the user, we completed the localization, issue analysis, and a draft revision path; however, this item still requires author confirmation: {reason}",
    )


def revised_excerpt_zh_summary(intent: str, status: str, citation_payload: dict[str, Any] | None = None) -> str:
    if status != "completed":
        return "需作者确认：当前材料不足以生成可直接投稿的新中文修订段落。"
    if intent == "clarify":
        return "该段已改为仅陈述当前数据范围内可以支持的观察结果。"
    if intent == "limitation":
        return "该段已补入与现有证据边界一致的局限性说明。"
    if intent == "citation":
        citation_text = normalize_ws((citation_payload or {}).get("formatted_citation_text", ""))
        if citation_text:
            return f"该段已补入经确认的参考文献支持：{citation_text}"
        return "该段已补入经确认的参考文献支持。"
    return "该段已按审稿意见完成保守的文本性修订。"


def load_paper_search_map(path: str) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    payload = read_json(Path(path), {"results": []})
    if isinstance(payload, dict):
        rows = payload.get("results", [])
    else:
        rows = payload
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        comment_id = normalize_ws(str(row.get("comment_id", "")))
        if comment_id:
            mapping[comment_id] = row
    return mapping


def render_comment_record(unit: dict) -> str:
    atomic = unit["atomic_location"]
    actions = unit["modification_actions"] or [{"action": "无", "reason": "无"}]
    lines = [
        f"# {unit['comment_id']}",
        "",
        "## 1) 审稿意见与中文理解",
        "",
        f"**原始审稿意见（English）**  \n{unit['reviewer_comment_en']}",
        "",
        f"**审稿意见中文翻译（直译）**  \n{unit['reviewer_comment_zh_literal']}",
        "",
        f"**审稿意见中文理解**  \n{unit['intent_zh']}",
        "",
        "## 2) Response to Reviewer（中英对照）",
        "",
        f"**中文回应**  \n{unit['response_zh']}",
        "",
        f"**English Translation**  \n{unit['response_en']}",
        "",
        "## 3) 可能需要修改的正文/附件内容（中英对照）",
        "",
        f"**快速定位**  \n- 章节: {atomic.get('section_heading', '无')}\n- 段落索引: {atomic.get('paragraph_index', '无')}\n- Word检索锚句: {atomic.get('matched_sentence', '无')}\n- 修改动作: {' / '.join(a['action'] for a in actions)}",
        "",
        f"**原子化定位**  \n- manuscript_section_id / si_section_id: {atomic.get('manuscript_section_id') or atomic.get('si_section_id') or '无'}\n- 原子文件路径: {atomic.get('section_file', '无')}\n- paragraph_index: {atomic.get('paragraph_index', '无')}\n- matched_sentence: {atomic.get('matched_sentence', '无')}",
        "",
        f"**Original Text**  \n{unit['original_excerpt_en'] or '无'}",
        "",
        f"**对应段落修订文本（English）**  \n{unit['revised_excerpt_en'] or '无'}",
        "",
        f"**修改后中文对照**  \n{unit['revised_excerpt_zh'] or '无'}",
        "",
        "## 4) 修改说明（中文）",
        "",
        "**细节修改**",
    ]
    for action in actions:
        lines.append(f"- {action['action']}：{action['reason']}")
    lines.extend(
        [
            "",
            "**总结**",
            f"- 🔴 Core：{'；'.join(unit['notes_core_zh'])}",
            f"- 🟡 Support：{'；'.join(unit['notes_support_zh'])}",
            "",
            "## 5) Evidence Attachments",
            "",
            "**Text**",
        ]
    )
    for source in unit["evidence_sources"]:
        lines.append(f"- {source['provider_family']}: {source['source']}")
    lines.extend(
        [
            "",
            "**Image**",
            "- Not provided by user",
            "",
            "**Table**",
            "- Not provided by user",
            "",
        ]
    )
    return "\n".join(lines)


def render_response_to_reviewers(units: list[dict]) -> str:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for unit in units:
        grouped[unit["reviewer"]][unit["severity"]].append(unit)

    lines = [
        "# 回复审稿人的邮件",
        "",
        "感谢编辑和审稿人的审阅。我们已逐条整理审稿意见、回复内容、正文修订位置及证据边界，相关需作者确认之处已明确标注。",
        "",
    ]
    for reviewer in sorted(grouped.keys()):
        lines.append(f"# {reviewer}")
        lines.append("")
        for severity in ("major", "minor"):
            items = grouped[reviewer].get(severity, [])
            if not items:
                continue
            lines.append(f"## {severity.capitalize()}")
            lines.append("")
            for idx, unit in enumerate(items, start=1):
                lines.append(f"### Comment {idx}")
                lines.append("")
                lines.append("#### 1) 审稿意见与中文理解")
                lines.append("")
                lines.append(f"**原始审稿意见（English）**  \n{unit['reviewer_comment_en']}")
                lines.append("")
                lines.append(f"**审稿意见中文翻译（直译）**  \n{unit['reviewer_comment_zh_literal']}")
                lines.append("")
                lines.append(f"**审稿意见中文理解**  \n{unit['intent_zh']}")
                lines.append("")
                lines.append("#### 2) Response to Reviewer（中英对照）")
                lines.append("")
                lines.append(f"**中文回应**  \n{unit['response_zh']}")
                lines.append("")
                lines.append(f"**English Translation**  \n{unit['response_en']}")
                lines.append("")
                lines.append("#### 3) 可能需要修改的正文/附件内容（中英对照）")
                lines.append("")
                atomic = unit["atomic_location"]
                lines.append(f"**快速定位**  \n- 章节: {atomic.get('section_heading', '无')}\n- 段落索引: {atomic.get('paragraph_index', '无')}\n- Word检索锚句: {atomic.get('matched_sentence', '无')}\n- 修改动作: {' / '.join(a['action'] for a in unit['modification_actions']) or '无'}")
                lines.append("")
                lines.append(f"**原子化定位**  \n- manuscript_section_id / si_section_id: {atomic.get('manuscript_section_id') or atomic.get('si_section_id') or '无'}\n- 原子文件路径: {atomic.get('section_file', '无')}\n- paragraph_index: {atomic.get('paragraph_index', '无')}\n- matched_sentence: {atomic.get('matched_sentence', '无')}")
                lines.append("")
                lines.append(f"**Original Text**  \n{unit['original_excerpt_en'] or '无'}")
                lines.append("")
                lines.append(f"**对应段落修订文本（English）**  \n{unit['revised_excerpt_en'] or '无'}")
                lines.append("")
                lines.append(f"**修改后中文对照**  \n{unit['revised_excerpt_zh'] or '无'}")
                lines.append("")
                lines.append("#### 4) 修改说明（中文）")
                lines.append("")
                lines.append("**细节修改**")
                for action in unit["modification_actions"]:
                    lines.append(f"- {action['action']}：{action['reason']}")
                lines.append("")
                lines.append("**总结**")
                lines.append(f"- 🔴 Core：{'；'.join(unit['notes_core_zh'])}")
                lines.append(f"- 🟡 Support：{'；'.join(unit['notes_support_zh'])}")
                lines.append("")
                lines.append("#### 5) Evidence Attachments")
                lines.append("")
                lines.append("**Text**")
                for source in unit["evidence_sources"]:
                    lines.append(f"- {source['provider_family']}: {source['source']}")
                lines.append("")
                lines.append("**Image**")
                lines.append("- Not provided by user")
                lines.append("")
                lines.append("**Table**")
                lines.append("- Not provided by user")
                lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_edit_plan(units: list[dict]) -> str:
    def sort_key(unit: dict) -> tuple[int, str]:
        atomic = unit.get("atomic_location", {})
        paragraph_index = atomic.get("paragraph_index")
        if paragraph_index is None:
            paragraph_index = 10**9
        return int(paragraph_index), unit["comment_id"]

    lines = [
        "# manuscript_edit_plan",
        "",
        "| comment_id | 目标文档 | 段落索引 | 待替换片段 | 替换后文本 | 动作类型 |",
        "|---|---|---|---|---|---|",
    ]
    for unit in sorted(units, key=sort_key):
        lines.append(
            f"| {unit['comment_id']} | {unit['target_document']} | {unit['atomic_location'].get('paragraph_index', '无')} | "
            f"{unit['original_excerpt_en'] or '无'} | {unit['revised_excerpt_en'] or '无'} | "
            f"{' / '.join(action['action'] for action in unit['modification_actions']) or '无'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate units, comment records, response markdown, and edit plan")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--paper-search-results", default="")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    manuscript_index = read_json(project_root / "manuscript_section_index.json", {"sections": []})
    si_index = read_json(project_root / "si_section_index.json", {"sections": []})
    attachments_manifest = read_json(project_root / "attachments_manifest.json", {"files": [], "count": 0})
    paper_search_path = args.paper_search_results or str(project_root / "paper_search_results.json")
    paper_search_map = load_paper_search_map(paper_search_path if Path(paper_search_path).exists() else "")
    units_paths = sorted((project_root / "units").glob("*.json"))
    comment_records_dir = project_root / "comment_records"
    comment_records_dir.mkdir(parents=True, exist_ok=True)

    processed_units = []
    for unit_path in units_paths:
        unit = read_json(unit_path, {})
        target_document = infer_target_document(unit["reviewer_comment_en"], bool(si_index.get("sections")))
        index_data = si_index if target_document == "si" else manuscript_index
        citation_payload = paper_search_map.get(unit["comment_id"])
        anchored_section, anchored_paragraph = resolve_citation_anchor(citation_payload, index_data)
        if anchored_section and anchored_paragraph:
            section, paragraph, best_score = anchored_section, anchored_paragraph, 1
        else:
            section, paragraph, best_score = best_location(unit["reviewer_comment_en"], index_data)
        original_excerpt = paragraph["text"] if paragraph else "无"
        requirements = detect_comment_requirements(unit["reviewer_comment_en"])
        status, intent, reasons = assess_status(
            unit["reviewer_comment_en"],
            requirements,
            section,
            paragraph,
            best_score,
            citation_payload,
            bool(anchored_section and anchored_paragraph),
        )
        response_zh, response_en = response_blocks(unit, status, "；".join(reasons), intent)
        revised_excerpt_en = revise_paragraph(original_excerpt, intent, citation_payload) if status == "completed" else original_excerpt
        revised_excerpt_zh = revised_excerpt_zh_summary(intent, status, citation_payload)
        notes_core = ["已逐条建立评论、回复、正文位置和证据来源的对应关系。"]
        notes_support = ["已保留 Evidence Attachments 三模块，并对缺失材料明确标注。"]
        if status == "needs_author_confirmation":
            notes_core = ["该条涉及新增证据需求，当前只能形成边界清晰的修订草案。"]
            notes_support = ["已明确记录需作者确认原因，并限制外部文献 provider 仅为 paper-search。"]
        elif intent == "clarify":
            notes_core = ["已将原句限定在当前数据范围内，避免超出证据边界的泛化表述。"]
            notes_support = ["该自动修订仅限保守措辞澄清，不引入任何新增实验、数据或参考文献。"]
        elif intent == "limitation":
            notes_core = ["已在原段中直接补入局限性提示句，保持与现有证据边界一致。"]
            notes_support = ["该自动修订不扩展机制解释，也不新增未提供的证据。"]
        elif intent == "citation":
            notes_core = ["已将经确认的 paper-search 结果接入该条评论，并补入对应的文献支持。"]
            notes_support = ["仅在提供了已确认的检索结果和格式化引文文本时，才允许自动完成该类文献补充。"]

        sent_idx, sent_text = choose_sentence(unit["reviewer_comment_en"], original_excerpt)
        atomic_location = {
            "manuscript_section_id": section["section_id"] if section and target_document == "manuscript" else "",
            "si_section_id": section["section_id"] if section and target_document == "si" else "",
            "section_file": section["file"] if section else "",
            "section_heading": section["heading"] if section else "无",
            "paragraph_index": paragraph["paragraph_index"] if paragraph else None,
            "matched_sentence": sent_text or "无",
            "matched_sentence_index": sent_idx if sent_text else None,
        }
        evidence_sources = [
            {
                "provider_family": "user-provided",
                "source": atomic_location["section_file"] or "manuscript_docx_path",
            }
        ]
        if requirements["needs_citation"]:
            if citation_payload and citation_payload.get("confirmed"):
                for citation in citation_payload.get("citations", []):
                    evidence_sources.append(
                        {
                            "provider_family": "paper-search",
                            "source": citation.get("source", "paper-search-confirmed"),
                        }
                    )
            else:
                evidence_sources.append(
                    {
                        "provider_family": "paper-search",
                        "source": "candidate-search-required",
                    }
                )

        unit.update(
            {
                "reviewer_comment_zh_literal": literal_translate_comment(unit["reviewer_comment_en"]),
                "intent_zh": f"审稿人关注点：{comment_nature(unit['reviewer_comment_en'])}。",
                "response_zh": response_zh,
                "response_en": response_en,
                "atomic_location": atomic_location,
                "original_excerpt_en": original_excerpt,
                "revised_excerpt_en": revised_excerpt_en,
                "revised_excerpt_zh": revised_excerpt_zh,
                "modification_actions": [
                    {
                        "action": "修改" if status == "completed" else "需确认",
                        "reason": "根据审稿意见完成保守的文本性修订。" if status == "completed" else "当前材料不足以直接完成可投稿改写。",
                    }
                ],
                "notes_core_zh": notes_core,
                "notes_support_zh": notes_support,
                "evidence_sources": evidence_sources,
                "target_document": target_document,
                "status": status,
                "author_confirmation_reason": "；".join(reasons),
            }
        )
        processed_units.append(unit)
        write_json(unit_path, unit)
        write_text(comment_records_dir / f"{unit['comment_id']}.md", render_comment_record(unit))

        if status == "completed" and section and paragraph:
            for sec in index_data["sections"]:
                if sec["section_id"] != section["section_id"]:
                    continue
                for para in sec["paragraphs"]:
                    if para["paragraph_index"] == paragraph["paragraph_index"]:
                        para["current_text"] = revised_excerpt_en

    for index_name, index_data, directory in (
        ("manuscript_section_index.json", manuscript_index, project_root / "manuscript_sections"),
        ("si_section_index.json", si_index, project_root / "si_sections"),
    ):
        for section in index_data.get("sections", []):
            write_text(project_root / section["file"], build_section_markdown(section))
        write_json(project_root / index_name, index_data)

    write_text(project_root / "response_to_reviewers.md", render_response_to_reviewers(processed_units))
    write_text(project_root / "manuscript_edit_plan.md", render_edit_plan(processed_units))

    state = read_json(project_root / "project_state.json", {})
    state.setdefault("counts", {})
    state["counts"]["comment_units"] = len(processed_units)
    state["counts"]["completed"] = sum(1 for unit in processed_units if unit["status"] == "completed")
    state["counts"]["needs_author_confirmation"] = sum(1 for unit in processed_units if unit["status"] == "needs_author_confirmation")
    state["delivery_status"] = "ready_to_submit" if state["counts"]["needs_author_confirmation"] == 0 else "author_confirmation_required"
    write_json(project_root / "project_state.json", state)
    print(json.dumps({"ok": True, "delivery_status": state["delivery_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

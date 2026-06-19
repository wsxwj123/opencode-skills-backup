---
name: polish-sci
description: 纯论文润色全管道。输入一份已写完的稿子(无审稿意见),逐段提升语言表达,绝不改内容/数据/结论。触发词：润色、polish、语言润色、润色论文、polish paper、language polish、proofread manuscript、母语化、润色稿子。路由说明：与revise-sci区分,revise-sci由审稿意见驱动、只改被点名片段;polish-sci无意见、全文逐段润色覆盖每一段。与general-sci-writing区分,gsw从零写新稿,polish-sci只润色现成稿。
---

# Polish-Sci

## Overview
本技能只做一件事,纯语言润色一份已写完的稿子。输入是完整稿(md 或 docx),没有审稿意见。输出是逐段润色后的稿子,加一份逐段改动报告。

核心约束,只提升语言表达,绝不改内容、数据、结论。润色覆盖全文每一段,不是只改被点名的片段。

not_for(以下情况不要用本技能):
- 从零写新稿,用 general-sci-writing。
- 审稿意见驱动改稿(收到 reviewer comments / 退稿信),用 revise-sci。
- 写综述,用 review-writing。

工作流是脚本闸门式的。脚本只负责拆分、生成润色任务包、校验红线,真正的语言改写由主 agent 按本文 prompt 逐段执行。不要跳步,不要让脚本假装自己会改写。

## Intake Gate(开工前必须确认)
拿到稿子后,先与用户确认四件事,再动工:

1. **输入稿路径**,md 还是 docx。docx 需要本机已装 python-docx。
2. **语言**,中文还是英文。决定句长上限(英文≤30词 / 中文≤50字)与去AI规则分支。
3. **润色强度**,light / standard / deep。
   - light,只去AI套话、修语法、拆超长句,保留原措辞骨架。
   - standard,默认,在 light 基础上做母语化、术语统一、被动语态向目标区间靠拢。
   - deep,在 standard 基础上做段内句序与衔接优化,但仍不改任何论点与数据。
4. **是否要 docx 导出**,默认只出 md。

确认这四项 + 目标 project_root 后再进 Pipeline。

## Red Lines(一字不改)
以下内容润色时绝对不动,脚本会做集合比对拦截:
- 引用标记 `[n]`、DOI 字符串。
- 数值、统计量、p 值、置信区间、`n=N`、百分比、单位。
- 基因、蛋白、试剂、细胞系、物种名。
- 任何改动会改变科学论断的 token。

每段 `meaning_changed` 必须为 false。语义层守卫靠脚本(数值/引用集合比对)加人工逐段对照。

## Pipeline(脚本顺序)
```bash
# 1. 原子化:把稿子按段落拆成 units/<idx>.json
python scripts/atomize_manuscript.py --manuscript <input.md|docx> --project-root <root>

# 1.5 反向抽取图/参考交叉索引(图文一致性与引用完整性的审查辅助)
python scripts/manuscript_index.py --manuscript <input> --project-root <root> --units-dir units

# 1.6 抠图落盘(支持 docx 与 pdf,把内嵌图片解到 figures/,供最终 docx 嵌回;pdf 需 PyMuPDF,缺失则优雅跳过;其他非 docx/pdf 输入会自动 no-op)
python scripts/extract_docx_images.py --manuscript <input> --project-root <root>

# 2. 生成逐段润色任务包(含 section_type 的被动目标区间 + 句长上限 + 红线)
python scripts/polish_units.py pack --project-root <root> --intensity standard

# 3. 主 agent 逐段润色:读 polish_manifest.json 的每个 task,
#    按下方 Polish Prompt 改写,把结果写回 polished/<idx>.json
#    (覆盖 polished_text、polished_by、polish_note、meaning_changed)

# 4. 校验红线(逐段写回 polish_risk_flags)
python scripts/polish_units.py verify --project-root <root>

# 5. 委托独立子代理盲检 DoD(见下方 DoD 自检清单)
# Windows 注意:PowerShell/cmd 不展开 *.json 通配符,需把 polished/ 下的 json 文件显式逐个列在 --files 后,或在 WSL/bash 里运行
python scripts/delegate_review.py pack --checklist references/dod_checklist.json \
    --gate polish-dod --files <polished/*.json polished_manuscript.md> --workdir <root>
# 子代理返回后:
python scripts/delegate_review.py verify --checklist references/dod_checklist.json \
    --gate polish-dod --workdir <root>

# 6. 交付前 fail-closed 闸门(任一红线破 -> exit 1)
python scripts/strict_gate.py --project-root <root>

# 7. 合并 + 报告
python scripts/merge_manuscript.py --project-root <root> [--docx out.docx]
python scripts/polish_report.py --project-root <root>
```

## Polish Prompt(主 agent 逐段改写时遵守)
对 `polish_manifest.json` 里的每个 task,产出 `polished_text`:
1. **去AI**,清除 AI 套话与五项装饰(见 Anti-AI 规则),改写后自检不得残留。
2. **句长**,英文单句≤30词、中文单句≤50字,长短句交替,避免连续长句。
3. **被动语态**,向该段 `passive_target` 区间靠拢。methods/results 可较高,intro/discussion 偏低。区间是软目标,不硬卡。
4. **术语一致**,同一概念全文用同一词,不要为求变化做同义替换。
5. **不确定性动词不升级**,hedge 不可改成 strong(may/suggest 不可变成 prove/demonstrate)。只可平移或下调。
6. **红线**,task 里 `red_lines.preserve_citations` 列出的引用标记、所有数值、专名一字不动。
7. 改完写回该 unit,`polished_by` 填非 PLACEHOLDER 值,`meaning_changed` 必须为 false,`polish_note` 简述改了什么或为何不改。

## Output Contract
- `units/<idx>.json`,原子化单元(原文 + section_type + 引用/数值标记)。
- `figure_index.json` / `reference_index.json`,反向抽取的图、参考交叉索引(每项含 cited_by 与 orphan_type)。
- `manuscript_index.md`,人读版图/参考索引与孤儿汇总。启发式抽取,作审查辅助而非红线核验。
- `figures/figure_NN.<ext>` + `figures/image_manifest.json`,从源 docx `word/media/` 解出的内嵌图(按 zip 出现顺序命名)。仅二进制搬运,不做 OCR/图像识别;非 docx 输入则该目录可能为空。供最终 docx 嵌图使用。
- `polish_manifest.json`,逐段润色任务包。
- `polished/<idx>.json`,逐段润色结果 + polish_risk_flags。
- `polished_manuscript.md`,合并后的润色稿。docx 为可选导出(`--docx`,需 python-docx;失败仅警告,md 仍产出)。
- `polish_change_report.md`,逐段改动 + 风险 flag + 未改原因。

## Anti-AI 规则(检测见 common.py)
去AI检测由 `find_ai_style_markers`(scripts/common.py)统一执行,润色后残留即记 flag,strict_gate 拦截。**硬拦项**:
- 修辞性破折号 `—`。
- scare quotes(普通短语裹双引号)。
- 解释性冒号(概念冒号后接句子片段)。
- `-ing` 拖尾从句(`, thereby ...ing` / `, reflecting ...`)。
- AI 套话禁词表(delve into、pivotal role、underscore、It is worth noting that 等,中英双语,见 common.py 的 AI_CLICHE 表)。
- `not only...but also`、`from A to B`(仅修辞铺陈;`from 24 to 72 h` 这类数值/时间范围不算)、修辞问句。

**软警告项(记入报告,不阻断交付)**:英文单句>30词 / 中文单句>50字。科学方法学段落常含数据列表的合法长句,strict_gate 不因句长阻断,只在 `polish_change_report.md` 列出供人工取舍。

**非散文豁免**:参考文献、作者名单、单位、资助、关键词、致谢、图表标题、纯数据清单等(atomize 标 `prose=false` 或润色器标 `polished_by=unchanged-nonprose`)保留原文不润色,**去AI/句长检测对它们不适用**(否则参考文献标题里的冒号/范围/问句会被误判);红线(数值/引用/语气/meaning)仍对全部单元核验。

> atomize 能识别**非 Word 样式的标题**(`1. Introduction` / `2.1 Foo` / 已知章节名等普通段落),据此推断 section_type 与 prose 标志。子小节按名无法归类时退回 other(只影响软性被动目标)。

本 SKILL.md 文本自身也遵守上述去AI规则。

## DoD 自检清单(润色收口)
机器可读真源,`references/dod_checklist.json` 的 `polish-dod` gate。strict_gate 运行前,必须委托独立子代理盲检。

通用 9 项(id: PL-G1 ~ PL-G9):
- **PL-G1 数值保留**,每段数值/统计量集合与原文一字不差。
- **PL-G2 无语气升级**,不确定性动词未被升级。
- **PL-G3 引用保留**,引用标记与 DOI 集合前后一致。
- **PL-G4 去AI**,散文单元 find_ai_style_markers 无硬拦残留(句长为软警告不阻断;非散文单元豁免)。
- **PL-G5 meaning 未变**,每段 meaning_changed=false,专名未动,语义层人工逐段对照。
- **PL-G6 逐段全覆盖**,无 PLACEHOLDER 残留,无遗漏段落。
- **PL-G7 被动语态合区间**,各段被动比例落在 section_type 目标区间附近。
- **PL-G8 术语一致**,全文术语用词前后一致(人工核)。
- **PL-G9 结构完整性**,合并稿段落顺序与小节结构与原稿一致,引用编号连续。

🔴 **委托盲检(强制)**,主 agent 不得自评 DoD。必须:
1. `python scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate polish-dod --files <...> --workdir <root>`,把打印的任务包交给独立子代理(默认 sonnet)。
2. 子代理只依据文件实际内容逐项裁决,返回 JSON 写到约定路径。
3. `python scripts/delegate_review.py verify ... --gate polish-dod --workdir <root>`,fail-closed 校验。任一缺项/fail/证据为空 -> exit 1,不得声明完成。

🔴 **结构完整性闸口(前置)**,合并后立即核对段落数与原稿一致、无错位、引用编号连续,再进交付。

通过条件,delegate_review verify 通过 + strict_gate.py exit 0 输出 `STRICT_GATE: PASS`。

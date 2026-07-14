---
name: polish-sci
version: 2.21.0
description: 纯论文润色全管道。输入一份已写完的稿子(无审稿意见),逐段提升语言表达,绝不改内容/数据/结论。触发词：润色、polish、语言润色、润色论文、polish paper、language polish、proofread manuscript、母语化、润色稿子。路由说明：与revise-sci区分,revise-sci由审稿意见驱动、只改被点名片段;polish-sci无意见、全文逐段润色覆盖每一段。与general-sci-writing区分,gsw从零写新稿,polish-sci只润色现成稿。
---

# Polish-Sci

> 🔁 **每次进入/续写先接续**:开工或换会话续写前,先跑 `env_preflight` 打印的 **RESUME_CMD**(`python <_shared>/session_journal.py resume --root <project_root>`),把接续报告贴给用户并打一次接续握手(确认进度到哪、之前的要求都读了、下一步做什么),等用户确认再动手。用户中途插入任何临时要求,立刻用 **LOG_CMD**(`session_journal.py log --root <project_root> --note "<原话>"`)记进 `decisions_log.md`,后续会话必读必守。

## Overview
本技能只做一件事,纯语言润色一份已写完的稿子。输入是完整稿(md 或 docx),没有审稿意见。输出是逐段润色后的稿子,加一份逐段改动报告。**默认走交互式逐段润色**(每段先贴原文/润色/逐处改动给你看、你确认或要求调整后才写回,见"交互式逐段润色协议"专节),方便你边润边对照改自己的原稿。

核心约束,只提升语言表达,绝不改内容、数据、结论。润色覆盖全文每一段,不是只改被点名的片段。

not_for(以下情况不要用本技能):
- 从零写新稿,用 general-sci-writing。
- 审稿意见驱动改稿(收到 reviewer comments / 退稿信),用 revise-sci。
- 写综述,用 review-writing。

工作流是脚本闸门式的。脚本只负责拆分、生成润色任务包、校验红线,真正的语言改写由主 agent 按本文 prompt 逐段执行。不要跳步,不要让脚本假装自己会改写。

## 🔴 Intake Gate(开工前必须确认)
🛑 STOP：拿到稿子后,先与用户确认四件事,再动工:

1. **输入稿路径**,md 还是 docx。docx 需要本机已装 python-docx。
2. **语言**,中文还是英文。决定句长上限(英文≤30词 / 中文≤50字)与去AI规则分支。
3. **目标期刊 + 美式/英式拼写(US / UK English)**。目标期刊决定语域与用词习惯(可留白,建议给出);英文稿必须定 US 还是 UK,它决定拼写(color/colour、analyze/analyse)、标点(引号与句号位置)、以及被动语态偏好,全稿一把尺子,不得混用。中文稿此项记"N/A"。
4. **润色强度**,light / standard / deep。
   - light,只去AI套话、修语法、拆超长句,保留原措辞骨架。
   - standard,默认,在 light 基础上做母语化、术语统一、被动语态向目标区间靠拢。
   - deep,在 standard 基础上做段内句序与衔接优化,但仍不改任何论点与数据。
5. **是否要 docx 导出**,默认只出 md。

确认这四项 + 目标 project_root 后,先跑**环境预检（软门禁）**:`python scripts/env_preflight.py <project_root> --py docx`,写 `env_status.json`,末行 `PRECHECK: OK|ASK|BLOCKED`。`BLOCKED`(Python 过低)→停并引导升级;`ASK`(缺 git/python-docx 等可选工具)→逐项问用户是否安装并给指引,用户答"已装/不装"后才继续;`OK`→继续。再进 Pipeline。

### 📋 开场监工卡(每次启动必须原样打印给用户)
确认完上述四项、跑完预检后,**每次开工都要把下面这张卡贴给用户**,让用户知道该盯什么:

> **这次润色你要盯的几件事:**
> 1. 我**只动语言**,绝不改你的数据、结论、引用标记、专名/单位。你若看到某处数值、结论或引用被改了,**立刻喊停**,那是越界。
> 2. 我默认**逐段停**:每段给你看「原文 → 润色后 → 改了哪几处」,请你每段核对**意思没被改**再放行。
> 3. 你可以让我"连续润完不停",但那样就**失去逐段核对**,润坏了只能等最后的合并稿兜底才发现,**慎选**。
> 4. 红线由脚本做集合比对(引用/数值/专名),但脚本只拦得住"能从文本判定"的越界;**语义有没有被悄悄改,最终要靠你逐段看**。

## Red Lines(一字不改)
以下内容润色时绝对不动,脚本会做集合比对拦截:
- 引用标记 `[n]`、DOI 字符串。
- 数值、统计量、p 值、置信区间、`n=N`、百分比、单位。
- 基因、蛋白、试剂、细胞系、物种名。
- 任何改动会改变科学论断的 token。

每段 `meaning_changed` 必须为 false,但**改写方自填的 false 不作数**(标 false 即蒙混)。语义等价的唯一权威是独立 PL-G11 盲检subagent的裁决:strict_gate 交付前会读 `<root>/.review_return_polish-dod.json`,要求 PL-G11 verdict==pass 且证据非空;缺独立裁决即视为"未核",fail-closed 拦下(见下方 ⑥/PL-G11)。脚本的数值/引用集合比对只补语义盲区的一部分,不替代盲检。

## 字符级排版契约(等同红线)
行内格式标记与上方红线**同级**,润色时逐字保留其位置与配对,不得增删、不得错配:
- **斜体** `*…*`,标注物种(`*E. coli*`)、基因(`*TP53*`)、统计符号(`*p*` 值、`*t*`、`*F*`、`*r*`、`*n*` 作变量时)。原文已斜体的,润色后仍斜体且范围不变。
- **上标** `<sup>…</sup>`,如 `10<sup>6</sup>`、`cm<sup>2</sup>`、`O<sub>2</sub>` 的对应上标场景。
- **下标** `<sub>…</sub>`,如 `H<sub>2</sub>O`、`CO<sub>2</sub>`、`Ca<sup>2+</sup>` 的对应下标。
- **加粗** `**…**`,保留原稿强调位置,不新增、不删除。

硬约束:
- 标记成对出现,改写后开闭标签数量与配对必须守恒(每个 `<sup>` 对一个 `</sup>`,每个 `*` 成对)。
- 禁止裸写需要排版的字符,如 `H2O` 必须写 `H<sub>2</sub>O`、`10^6` 必须写 `10<sup>6</sup>`、基因斜体不可退化为正体。
- 标记内的字符属红线,不可改动其中的数值/专名;只可改标记**外**的散文。

## Pipeline(脚本顺序)
**第 0 步(拆段前必做,无脚本):通读全稿一遍。** atomize 一拆段,你就只能逐段看局部,靠临场记忆润色,极易术语前后不一、指代判错。所以拆段前先把整稿从头读一遍,建立三样全局依据,写进 `decisions_log.md`(用 LOG_CMD)供逐段润色时对照:
- **术语一致表**:同一概念/缩写/基因蛋白名在全文的既定写法(哪个词、什么大小写、缩写首展在哪),逐段润色时照此表统一,不临场另起同义词。
- **作者语感基线**:摸清作者的句式偏好、语气强弱、正式度,润色是向目标期刊语域靠拢而非抹平成千篇一律的 AI 腔。
- **目标期刊语境**:结合 Intake 的目标期刊与 US/UK 拼写,定全稿统一的拼写/标点/语域基准。

通读只读不改,是逐段润色的全局基准;跳过它,就只能靠局部记忆硬润,必然出术语漂移。

```bash
# 1. 原子化:把稿子按段落拆成 units/<idx>.json
python scripts/atomize_manuscript.py --manuscript <input.md|docx> --project-root <root>

# 1.5 反向抽取图/参考/缩略语交叉索引(图文一致性、引用完整性与缩略语首展的审查辅助;产 abbreviation_index.json)
python scripts/manuscript_index.py --manuscript <input> --project-root <root> --units-dir units

# 1.6 抠图落盘(支持 docx 与 pdf,把内嵌图片解到 figures/,供最终 docx 嵌回;pdf 需 PyMuPDF,缺失则优雅跳过;其他非 docx/pdf 输入会自动 no-op)
python scripts/extract_docx_images.py --manuscript <input> --project-root <root>

# 2. 生成逐段润色任务包(含 section_type 的被动目标区间 + 句长上限 + 红线)
python scripts/polish_units.py pack --project-root <root> --intensity standard

# 3. 主 agent 逐段润色:读 polish_manifest.json 的每个 task,按下方 Polish Prompt 改写。
#    默认走「交互式逐段润色协议」(见下方专节):每段润完先贴原文/润色/逐处改动给用户,
#    用户确认或要求调整后才写回 polished/<idx>.json;不是闷头全润完再 merge。

# 4. 校验红线(逐段写回 polish_risk_flags)
python scripts/polish_units.py verify --project-root <root>

# 5. 委托独立subagent盲检 DoD(见下方 DoD 自检清单)
# Windows 注意:PowerShell/cmd 不展开 *.json 通配符,需把 polished/ 下的 json 文件显式逐个列在 --files 后,或在 WSL/bash 里运行
python scripts/delegate_review.py pack --checklist references/dod_checklist.json \
    --gate polish-dod --files <polished/*.json polished_manuscript.md> --workdir <root>
# subagent返回后:
python scripts/delegate_review.py verify --checklist references/dod_checklist.json \
    --gate polish-dod --workdir <root>

# 5b. 语法拼写与字符级自检(PL-G13,只报告不改稿;命中高置信类别 misspelling/chinese_punct/subsup_bare -> exit 1)
python scripts/proofread_polished.py --project-root <root>

# 6. 交付前 fail-closed 闸门(任一红线破 -> exit 1;
#    另⑥:还会读 .review_return_polish-dod.json,要求独立 PL-G11 语义等价盲检 verdict==pass+证据,
#    否则即便每段自填 meaning_changed=false 也判 FAIL,故本步须在第 5 步盲检 verify 之后跑)
python scripts/strict_gate.py --project-root <root>

# 7. 合并 + 报告
python scripts/merge_manuscript.py --project-root <root> [--docx out.docx] [--in-place-src <原始docx>]
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
7. **保留行内格式标记**,见"字符级排版契约"。`*斜体*`(物种/基因/统计符号)、`<sup>`/`<sub>`、`**加粗**`逐字保留位置与配对,不增删、不错配,标记内字符按红线处理。
8. 改完写回该 unit,`polished_by` 填非 PLACEHOLDER 值,`meaning_changed` 必须为 false,`polish_note` 简述改了什么或为何不改。

## 交互式逐段润色协议(默认开启)
目的:让你边润边看、能随时干预,方便对照着改自己的原稿;不是闷头全润完再 merge。

按 `polish_manifest.json` 的 task 顺序逐个处理。**散文段(prose=true)** 走下面五步,**一段一停**:

1. 按 Polish Prompt 改写,自检去AI硬拦项与红线(数值/引用/专名/行内标记)无残留、无破坏。
2. 在对话里贴出该段对照,固定格式:
   ```
   ── Unit <idx> · <section_type> ──
   原文:   <raw_text>
   润色后: <polished_text>
   改动点:
     · <原词/原表述> → <新词/新表述>(为什么:去AI套话 / 拆长句 / 母语化 / 被动调整…)
     · …(逐处列全,没改的不写)
   风险flag: <若有,列出;无则省略此行>
   ```
   改动点必须**逐处列全**,这是你对照手改原稿的依据,不能只说"优化了表达"。
3. 🛑 **停下**,等你表态:
   - 确认/默许 → 写回 `polished/<idx>.json`,进下一段。
   - 要求调整(语气/某词别动/换种改法) → 重改重贴,直到你满意再写回。
   - 跳过该段 → 标 `polished_by=unchanged-user-skip`、保留原文,进下一段。
4. 只有你确认后才写回该 unit,绝不未确认就落盘。
5. 全部段处理完 → 照常走 Pipeline 第4步起(verify / 盲检 / strict_gate / merge / report)。

### 跨段编辑(合法路径,非母语稿最需要)
unit=段落是**红线核验的边界**,不是"每段只能就地改、不准动段间"的牢笼。非母语稿最常见的毛病,恰恰是段落切分零碎、段间无过渡、话题句放错段,只在段内润色治不了。允许**跨段手术**:
- 把某段末尾的过渡句/话题句挪到下一段开头;
- 合并两个碎段;
- 在段间补一句衔接过渡。

跨段编辑仍走逐段停协议:凡涉及跨段的动作,在当轮对照里**显式说明"从 Unit X 挪了哪句到 Unit Y / 合并了 X+Y / 在 X、Y 间补了过渡句"**,让用户看得见结构性改动、能喊停。两条硬约束(否则脚本会正确地拦下你):
1. **红线 token 不跨 unit 搬家**。数值/统计量/引用标记 `[n]`/DOI/基因蛋白单位等红线 token 必须留在原 unit,它们一旦被挪到别的 unit,strict_gate 逐 unit 集合比对会判"原 unit 掉了、目标 unit 多了"而 fail(这是对的,数据/引用错位是越界)。跨段搬的只能是**不带红线 token 的散文句**(话题句、过渡句)。
2. **结构性合并/拆分只走 md 重建导出**。合并/拆分段落会改变 unit 与源 docx 段落的 1:1 映射,in-place 保格式导出(`--in-place-src`)据 `source_para_index` 精确写回,段数对不齐会 fail-closed 报错。故需要合并/拆分段落时,用 md 重建导出(`--docx`,不带 `--in-place-src`);要 in-place 保格式则保持段落 1:1、只在段内润色。

**非散文段(prose=false:参考文献、作者名单、单位、资助、关键词、致谢、图表标题、纯数据清单)**:不润色、**不逐段打扰你**。直接标 `polished_by=unchanged-nonprose` 写回,在邻近一次输出末尾汇总一句"已跳过 N 个非散文段(参考文献/图注等)"即可。

**节奏开关**:你可随时说"接下来连续润完不用停"→切到连续模式(整节或剩余段一次润完再统一贴对照);说"恢复逐段停"→切回一段一停。默认逐段停。

## Output Contract
- `units/<idx>.json`,原子化单元(原文 + section_type + 引用/数值标记)。
- `figure_index.json` / `reference_index.json`,反向抽取的图、参考交叉索引(每项含 cited_by 与 orphan_type)。
- `abbreviation_index.json`,反向抽取的缩略语交叉索引(每项含 defined_count / used_count / orphan_type)。纯润色不改缩略语定义,此索引为**软报告**,列出 undefined_use / duplicate_definition / title_abbreviation 供人工取舍,不阻断交付。
- `manuscript_index.md`,人读版图/参考/缩略语索引与孤儿汇总。启发式抽取,作审查辅助而非红线核验。
- `figures/figure_NN.<ext>` + `figures/image_manifest.json`,从源 docx `word/media/` 解出的内嵌图(按 zip 出现顺序命名)。仅二进制搬运,不做 OCR/图像识别;非 docx 输入则该目录可能为空。供最终 docx 嵌图使用。
- `polish_manifest.json`,逐段润色任务包。
- `polished/<idx>.json`,逐段润色结果 + polish_risk_flags。
- `polished_manuscript.md`,合并后的润色稿。docx 导出有两条路径:
  - **in-place 保格式导出(交付级,docx 输入首选)**:`--in-place-src <原始docx>`(可配 `--docx <输出路径>`,缺省 `polished_inplace.docx`)。直接打开**原始输入 docx**,只把每个 prose 段落的文字换成 polished 文本,按行内标记(`*斜体*`/`**加粗**`/`<sup>`/`<sub>`)重建 run,每个新 run 继承该段落原首个 run 的基础字体(`font.name`/`size`/`w:eastAsia`),再叠加 italic/sup/sub/bold。段落级格式(对齐/样式/缩进 pPr)、表格、图片、页眉页脚、参考文献等非 prose 内容**完全不动**。映射靠 `units/<idx>.json` 的 `source_para_index`;段落数与 unit 对不齐(缺索引/越界/冲突)时 **fail-closed 报错退出**,绝不错位写入。**含内嵌图片(`<w:drawing>`/`<w:object>`)的段落会跳过文字改写以保图**(清 run 重建会删图,且改写后无法确定图在新文字里的位置),改写时跳过该段、保留原 runs 不动、stderr 警告并记入 `paragraphs_skipped_images`,需人工处理该段文字(与 revise-sci 口径一致)。这是 docx 输入的**保格式交付稿**。
    > ⚠️ **已知局限:run 级颜色/下划线**:run 级颜色(`w:color`)与下划线(`w:u`)**不在**行内标记(`marked_text`)范围(只序列化斜体/加粗/上下标),润色全程不携带这两类格式。in-place 导出对此做了**分级保真**:① 某段文字**未被润色改动**时,若段内存在 run 级颜色/下划线,跳过破坏性重建、**保留原 runs 无损**(记入 `paragraphs_skipped_color_underline`);② 该段文字**被润色改动**时,原颜色/下划线锚定的词可能已不在,无可靠位置映射,**重建后丢失**。因此:**用颜色/下划线表达的强调,在被改写的段落里不保证保留**,这类强调请改用 markdown 行内标记(`*斜体*`/`**加粗**`/上下标),它们随 `marked_text` 全程保真。
  - **md 重建导出(无原始 docx 时,如 md 输入)**:`--docx out.docx`(不带 `--in-place-src`)。从 polished md 重建裸 docx,解析行内标记渲染为 run 级格式并对每个 run 设含 `w:eastAsia` 的字体(中文默认宋体)。能渲染显式标注的字符级格式,但**不携带原稿的段落排版/表格/图片**,适合 md 输入或预览。
  > ℹ️ 读取层(`read_docx_paragraphs`)已把原稿 run 级格式(斜体/上下标/加粗)序列化进 `marked_text`,atomize 用它作 prose 段落 `raw_text`,润色全程带标记(见"字符级排版契约"),因此 in-place 写回能还原原稿语义行内格式,纯润色不再把 `H₂O→H2O` 或丢斜体。
- `polish_change_report.md`,逐段改动 + 风险 flag + 未改原因。

## Anti-AI 规则(检测见 common.py,分级见 strict_gate.py)
去AI检测由 `find_ai_style_markers`(scripts/common.py)统一执行,润色后残留即记 flag。**但阻断与否分两级**(分级在 `strict_gate.is_soft_ai_marker`),学术散文里长句、-ing 分词、修辞铺陈本是正当修辞手段,一刀切硬禁会把作者文风削平,故这些降为软提示;但 AI 套话主干与**破折号**硬拦。

**硬拦项(strict_gate 阻断交付,exit 1)**:
- AI 套话禁词表(delve into、pivotal role、underscore、testament、It is worth noting that、值得注意的是、综上所述、至关重要 等,中英双语,见 common.py 的 `AI_STYLE_BANNED_PATTERNS` 与 `AI_CLICHE_TERMS_EN/ZH`)。这些是 AI 腔的硬指纹,润色后一律清零。
- **修辞性破折号 `—` / `——` / em-dash:禁止使用,硬拦**。strict_gate 对破折号 fail-close,命中即阻断,不放行。

**软提示项(记入 `polish_risk_flags` / `polish_change_report.md`,**不阻断交付**,由人工取舍),学术散文正当修辞,别硬削平**:
- 英文单句>30词 / 中文单句>50字(科学方法学段落常含数据列表的合法长句)。
- `-ing` 拖尾从句(`, thereby ...ing` / `, reflecting ...`)。
- scare quotes(普通短语裹双引号)。
- 解释性冒号(概念冒号后接句子片段)。
- `not only...but also`、修辞问句。

> 降软不等于放任:软提示仍逐段列给用户看,该收敛就收敛;只是它不再 fail-closed 卡交付,把"这处长句要不要改"的判断权交回作者,而不是脚本替作者一律铲平。破折号例外:它是硬拦、禁止使用,不交作者取舍。`from A to B` 检测已从 common.py 移除(科学文本高频合法,信噪比差)。

**非散文豁免**:参考文献、作者名单、单位、资助、关键词、致谢、图表标题、纯数据清单等(atomize 标 `prose=false` 或润色器标 `polished_by=unchanged-nonprose`)保留原文不润色,**去AI/句长检测对它们不适用**(否则参考文献标题里的冒号/范围/问句会被误判);红线(数值/引用/语气/meaning)仍对全部单元核验。

> atomize 能识别**非 Word 样式的标题**(`1. Introduction` / `2.1 Foo` / 已知章节名等普通段落),据此推断 section_type 与 prose 标志。子小节按名无法归类时退回 other(只影响软性被动目标)。

本 SKILL.md 文本自身也遵守上述去AI规则。

## ❌ 禁止动作清单(润色时绝不做)
对现有规则的集中索引,逐条对应正文已有约束,违反任一即 strict_gate 或盲检拦截:
- ❌ 改动数值/统计量/p值/n=N/百分比/单位/引用标记[n]/DOI/专名(基因蛋白细胞系物种),见 Red Lines
- ❌ 升级不确定性动词(may/suggest/可能 改成 prove/demonstrate/证实),见 Polish Prompt #5
- ❌ 凭空增加原文没有的程度词(significantly/extensively/显著 等),等同升级语气,meaning_changed 必为 false
- ❌ 为求变化做同义替换、破坏全文术语一致,见 Polish Prompt #4
- ❌ 裸写需排版字符(H2O 不写成 H<sub>2</sub>O、10^6 不写成 10<sup>6</sup>、基因斜体退化为正体),见 字符级排版契约
- ❌ 润色后残留 AI 套话禁词(delve into / 值得注意的是 等)或**装饰性破折号(—/——)**,二者均 Anti-AI **硬拦**、命中即 exit 1;长句/scare quotes/解释性冒号/-ing 拖尾为软提示(记报告不阻断),别硬删削平文风
- ❌ 只改被点名片段而非全文逐段覆盖,本技能是纯润色,覆盖每一段
- ❌ 未经用户确认就把该段写回 polished/,见 交互式逐段润色协议
- ❌ 主 agent 自评 DoD 不委托独立盲检subagent,见 DoD 委托盲检(强制)

## DoD 自检清单(润色收口)
机器可读真源,`references/dod_checklist.json` 的 `polish-dod` gate。strict_gate 运行前,必须委托独立subagent盲检。

通用 14 项(id: PL-G1 ~ PL-G14,其中 PL-G11 为科学内容零改动硬项、PL-G12 为软报告、PL-G13 为字符级自检硬项、PL-G14 为拉丁斜体软提醒):
- **PL-G1 数值保留**,每段数值/统计量集合与原文一字不差。
- **PL-G2 无语气升级**,不确定性动词未被升级。
- **PL-G3 引用保留**,引用标记与 DOI 集合前后一致。
- **PL-G4 去AI**,散文单元 find_ai_style_markers 的**硬拦**项(AI 套话禁词表 + **破折号**)无残留;长句/scare quotes/解释性冒号/-ing 拖尾/修辞问句为软提示,记报告不阻断(见 Anti-AI 规则的分级);非散文单元豁免。
- **PL-G5 meaning 未变**,每段 meaning_changed=false,专名未动,语义层人工逐段对照。
- **PL-G6 逐段全覆盖**,无 PLACEHOLDER 残留,无遗漏段落。
- **PL-G7 被动语态合区间(软报告)**,各段被动比例落在 section_type 目标区间附近;区间为软目标,只报告不阻断交付。
- **PL-G8 术语一致**,全文术语用词前后一致(人工核)。
- **PL-G9 结构完整性**,合并稿段落顺序与小节结构与原稿一致,引用编号连续。
- **PL-G10 缩略语首展一致(软报告)**,`abbreviation_index.json` 的 undefined_use / duplicate_definition / title_abbreviation 已列出供人工取舍;润色未破坏既有首展、未新增缩略语问题。纯润色不主动改缩略语定义,原稿固有问题只报告不阻断交付(与 revise-sci 的硬门禁 RV-G7 区分)。
- **PL-G11 科学内容零改动(语义等价的唯一权威)**,盲检补脚本红线之外的语义盲区:润色是否仅改语言、未改科学实质(事实/机制陈述、方法描述、因果方向、限定条件与适用范围、结论确切含义均与原文等价)。任一处科学内容被实质改写或含义偏移即 fail,列出原文与润色后对应句为证。**⑥ 这是判定 meaning 未变的唯一权威**:改写方在 polished/<idx>.json 里自填 `meaning_changed=false` 只是自证、不足信;strict_gate 交付前会读独立subagent写回的 `<root>/.review_return_polish-dod.json`,要求 PL-G11 verdict==pass 且证据非空,缺独立裁决/非 pass/空证据一律 fail-closed。即"没有独立盲检 = meaning 未核 = 拦",自填 false 不能替代。
  - ⚠️ **【P4·盲检降级告警】** 若环境派不出真正独立的subagent来做本项语义等价盲检,**绝不能同一 AI 自评自过**(自己润的自己判"意思没改坏"= 没有盲检)。必须告诉用户「本环境语义盲检不可靠,请你逐段亲自核对:改后有没有改变原意/数据/专名」,把这一核验交回用户,不得伪造盲检通过。好在 polish-sci 逐段一停让你每段都看得到改动点,本就有人肉兜底。
- **PL-G12 常识合理性(🟡软报告,不阻断)**,盲检subagent顺带扫一遍是否有明显常识/事实硬伤(单位量级离谱、生理/机制常识错误、前后数值逻辑矛盾等)被原文带入或润色引入。**仅提示不阻断**,纯润色默认原文内容正确,本项只在发现明显硬伤时记入报告供人工判断,绝不自动改内容(与 PL-G1~G11 的核验/硬拦区分,也与 reviewer-simulator 的完整科学性审查区分)。
- **PL-G13 润色后语法拼写与字符级格式自检(硬项)**,`python scripts/proofread_polished.py --project-root <root>` 对润色输出(polished/<idx>.json 的 polished_text)扫 misspelling / chinese_punct / subsup_bare,命中任一则 ok=false、阻断交付并列出问题供用户处理。**只报告不自动改**,脚本纯读 polished/ 并输出 proofread_report.json,绝不写回任何 json/docx/原稿(改与不改由用户决断,守"科学内容零改动"铁律)。
- **PL-G14 拉丁短语斜体软提醒(🟡软/人工确认,不阻断)**,PL-G13 同一次 `proofread_polished.py` 运行产出的 `proofread_report.json` 里 `latin_italic_missing` 类别:润色输出中 `in vitro`/`in vivo`/`ex vivo`/`in situ`/`de novo`/`post hoc`/`per se` 等公认须斜体的拉丁短语若裸写(未被 `*...*` 斜体标记包裹)则报告。**仅提示,不阻断、不进 `--fail-on`、不扣分**,由人工确认是否补斜体(`et al.`/`e.g.`/`vs.` 等正体惯例不在词表内)。

🔴 **委托盲检(强制)**,主 agent 不得自评 DoD。必须:
1. `python scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate polish-dod --files <...> --workdir <root>`,把打印的任务包交给独立subagent(默认继承主 agent 模型/用户指定)。
2. subagent只依据文件实际内容逐项裁决,返回 JSON 写到约定路径。
3. `python scripts/delegate_review.py verify ... --gate polish-dod --workdir <root>`,fail-closed 校验。任一缺项/fail/证据为空 -> exit 1,不得声明完成。
4. **① DoD 停**:盲检(尤其 PL-G11 语义等价)通过后,**不要直接 merge 交付**。先把每一项(PL-G1~PL-G14)的裁决结论逐条摆给用户看(通过/软提示/需人工确认的都列清),然后 **🛑 HALT 等用户确认**,用户点头才进 strict_gate + merge + report。这是交付前最后一道人肉闸,用户此刻仍可喊停或补要求(补要求即 LOG_CMD 记入决定日志)。

🔴 **结构完整性闸口(前置)**,合并后立即核对段落数与原稿一致、无错位、引用编号连续,再进交付。

通过条件,delegate_review verify 通过 + strict_gate.py exit 0 输出 `STRICT_GATE: PASS`。

## 发现 AI 改坏/偷懒了怎么办(用户自救)

【P4·自救指引】润色最怕两件事:改动点写得含糊、糊弄过去;悄悄把语气或科学内容改了。你无需读代码,直接复制下面话术怼回去,把 AI 拉回"只准动语言"的铁律:

- 「你改动点只写了'优化表达'太笼统,逐词列出你改了哪些词、为什么」
- 「第 X 段你把'可能提示'润成了'表明',这是升级语气,改回去」
- 「恢复逐段停,我要每段都看」
- 「你把某处数值/结论/专名改了,立刻改回,你只准动语言」

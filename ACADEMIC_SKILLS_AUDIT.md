# 七个学术技能 · 审计与优化状态

> 维护者:Claude Code · 最近更新:2026-06-16
> 范围:general-sci-writing / review-writing / sci2doc / reviewer-simulator / reviewer-response-sci / nsfc-proposal / revise-sci

## 一、已完成(2026-06-15 ~ 06-16,已 commit + push origin/main)

**第一批 · 流程修复**
- gsw:图集规划前置(Phase 2.5)+ storyline↔图集双向迭代;投稿前合规门禁(Phase 10.5:伦理/注册号/CONSORT-STROBE-ARRIVE/统计完整性/ICMJE/reviewer COI)
- review-writing:提纲可回修迭代闸(不前置检索)+ 检索日志可复现 + 放开 scoping review + 概念框架图
- sci2doc:研究主线设计门禁(Step 0.5)+ GB/T 7714 著录生成器 + 查重预检 + 符号表 + 源 SCI 引文做候选种子
- reviewer-simulator:全类型合规审计 + 统计独立子清单 + 给编辑保密意见 + 全文通读初判
- reviewer-response-sci:edit_plan 回填脚本化(aggregate-edit-plan)+ 承诺↔落点一致性门禁 + strategy 落为 unit 字段
- nsfc-proposal:科学问题属性论证校验(SPA-WARN)+ 代表作匹配(V-11)+ 备选路线硬门禁(V-12)+ 一致性时序分层 + 独立预期成果段

**第二批 · citation_guard 全面统一**
- 以 gsw 版为权威基准:白名单仅 {pubmed-cli, paper-search},禁用 {websearch, openalex-cli, tavily};移除 tavily 死逻辑;空 index → ok=false(fail-closed);修 openalex family 映射死条目
- 覆盖 review-writing/sci2doc/reviewer-simulator(四份字节一致 md5=63612d8)
- reviewer-response-sci(增量模型)补禁 openalex;revise-sci(rows 模型)补撤稿检查 + 空输入 fail-closed + 白名单补 pubmed-cli
- CLAUDE.md 同步:删 OpenAlex 检索源,仅留 PubMed CLI + paper-search

## 二、流程评分与行数(opus 多领域专家实测,2026-06-16)

| 技能 | 流程评分 | SKILL.md 行数 | 瘦身目标 |
|---|---|---|---|
| general-sci-writing | 9/10 | 608 | ~520-550 |
| review-writing | 8.5/10 | 844 ⚠最长 | ~520(清单见下) |
| sci2doc | 8/10 | 496 | ~400(Non-Negotiable 与 Contract 去重) |
| reviewer-simulator | 8.5/10 | 471 | 砍~80(重复训诫) |
| reviewer-response-sci | 7.5/10 | 297 | 文档对齐脚本能力(非篇幅) |
| nsfc-proposal | 8.5/10 | 259 | 不缩,补 V-11/V-12 摘要上浮 |
| revise-sci | 8.5/10 | 249 | 移开发日志到 CHANGELOG |
- 7 个技能 SKILL.md 均无乱码(U+FFFD 检测通过)

## 三、实测发现的 Bug(✅ 2026-06-16 全部 13 个已修复并实测通过)

> B7 经复查为 agent 管道误判(代码本就正确 sys.exit);其余 12 个 + 4 个🟢已修。

### 🔴 阻断级(照文档走就翻车)
| ID | 技能 | 问题 | 定位 | 状态 |
|---|---|---|---|---|
| B1 | gsw | write-cycle 开箱即死:preflight strict 要求 revision_plan/mentor_plan/submission_state 等文件存在,但 init 不创建 | state_manager.py preflight_validate_state(~1547);默认 preflight_strict=True | 待修 |
| B2 | revise-sci | atomize_comments 静默丢弃评论:severity 判定硬编码中文串,英文/措辞变动→count:0 且 ok:true→空 docx | atomize_comments.py:245-250 | 待修 |
| B3 | sci2doc | init 前置页泄漏到 cwd(数据污染):渲染传 project_root 而非 effective_root | state_manager.py:1647 | 待修 |
| B4 | sci2doc | custom 格式 pending_template→ready 永久卡死:missing_requirements 只累加不重算 | thesis_profile.py:897,940-944 | 待修 |

### 🟡 中危
| ID | 技能 | 问题 | 定位 | 状态 |
|---|---|---|---|---|
| B5 | review-writing | SKILL.md 谎报"openalex maps to paper-search, passes guard",实际已禁→交叉学科用户 guard 卡死 | SKILL.md L510-512 | 待修 |
| B6 | sci2doc | documented write-cycle 新项目必失败(同 B1,未提 --preflight-lenient) | state_manager.py:1692 | 待修 |
| B7 | sci2doc/gsw | 门禁失败 exit code 不传播(numbering/outline/validate 返回 exit 0 仅 JSON ok=false) | 多处 | 待修 |
| B8 | reviewer-response | strategy 字段只写不读(无任何消费),SKILL.md 夸大其作用 | build_full_package.py:786 | 待修 |
| B9 | reviewer-response | manuscript_edit_plan.md 无脚本生成,但 aggregate-edit-plan 硬依赖(文档说脚本建骨架) | build_full_package.py / run_pipeline.py | 待修 |
| B10 | reviewer-response | consistency_check 承诺↔落点门禁被停用词击穿(split()[1:3] 取到冠词"a",无 len>3 过滤) | consistency_check.py:84-87 | 待修 |
| B11 | reviewer-response | aggregate-edit-plan 不识别中文占位符【待AI翻译...】→泄漏进交付物,不计 PENDING 无告警 | state_manager.py:208-215 | 待修 |
| B12 | reviewer-response | reviewer 区块解析对格式脆弱(强制冒号/大小写敏感),失败静默把全文塞进 Reviewer #1 | build_full_package.py:97,112 | 待修 |
| B13 | nsfc | humanizer 正则盲区:`不仅A，而且B`(带逗号)漏检;`不是…而是…`同 | humanizer_zh.py:315-316 | 待修 |

### 🟢 低危/文档
- gsw:matrix 误读 storyline 内嵌 key_claims 字段 → 误报 unknown section ids
- nsfc:references/08 RULES 残留旧 V-01~V-10,未同步 V-11/V-12(代码对、文档旧);02 文档 V-09 severity 标注待核
- reviewer-response:SKILL.md 称读顶层 ok,实际在 report 嵌套层 {"report":{"ok":...}}
- sci2doc:reference_renderer GB/T 7714 偏差(DOI 前双空格;外文作者未"姓+名缩写")
- nsfc:tests/ 目录承诺未实现

## 四、瘦身清单(review-writing 844→~520,最优先)
- L305-340 outline.md 完整模板(init 已生成)→删,留指针(-33)
- L271-293 SKILL_DIR 探测 Python → references/env_check.md(-22)
- L470-544 Per-Section Search Loop 伪代码 → 留骨架~15行,细节下沉(-45)
- L753-794 连贯性/缩写扫描清单 + 未来方向/元数据模板 → references(-30)
- L86-95 期刊差异表 + CNKI/万方重复说明(3处)→ citation_styles.md(-14)
- 原则:砍模板和散文,留流程骨架和门禁命令

## 五、可借鉴点(来自 imbad0202/academic-research-skills,按价值)
1. Generator-Evaluator Contract:paper-blind 预承诺→paper-visible 评分,防"先读稿再合理化标准"漂移
2. Devil's Advocate 角色 + CRITICAL 硬门禁:对抗性审稿角色,可阻断 Accept(我方 reviewer-simulator 是单一审稿人)
3. Revision Patch Protocol:锚点+哈希+确定性应用,防未触碰区域被静默改写
4. Material Passport 跨会话断点续传(从任意阶段哈希恢复)
5. Calibration Mode:在金标准集上标定 FNR/FPR,量化审稿可信度
6. Style Calibration:用户历史论文→提取个人学风作软约束
7. disclosure 模式:按目标期刊生成 AI 使用声明
8. integrity_verification_agent:独立完整性核查层(7 类 AI 失败模式:幻觉引用/实现bug/方法论捏造等),比单纯 citation_guard 更宽
- **对方独有候选新增**:deep-research(系统调研前置)、academic-pipeline(端到端编排器)
- **我方独有**:sci2doc(SCI→中文博论)、nsfc-proposal(国自然)

## 六、待办优先级
1. ✅ B1-B4 阻断级已修(2026-06-16)
2. ✅ B5-B13 中危已修
3. ✅ 文档同步 + reference_renderer 格式已修
4. ⬜ review-writing 瘦身 844→~520(清单见第四节,待用户确认是否做)
5. ⬜ 其余瘦身:gsw 608→~550、sci2doc 496→~400、reviewer-simulator 砍~80
6. ⬜ 借鉴点评估(Devil's Advocate / Generator-Evaluator / Calibration 可选增强)

## 七、下一步执行计划(2026-06-16 拟定,待用户批准)

> 核心矛盾:瘦身(减)与借鉴点(加)方向相反。策略 = **先瘦身降负担,借鉴点只挑低成本高价值的精简引入**。分两阶段,阶段一做完实测通过再进阶段二。

### 阶段一:瘦身(纯减,优先)
方法论(复用 gsw v2.19 重构经验):**砍模板/散文/重复,留流程骨架+门禁命令+HALT;细节下沉 references 按需 Read**。每个技能瘦身后,派 agent"以新用户身份按 SKILL.md 从零实操"实测,确认不因下沉导致跳步(吸取本次端到端实测教训)。

| 技能 | 现行 | 目标 | 主要下沉项 |
|---|---|---|---|
| review-writing | 844 | ~520 | outline 模板(L305-340)、SKILL_DIR 探测(L271-293)、检索循环伪代码(L470-544 留骨架)、扫描/未来方向/元数据模板(L753-794)、期刊表(L86-95)+CNKI 重复(3处) |
| sci2doc | 496 | ~400 | Non-Negotiable 20 条与各 Contract 的重复(缩写/三线表/对齐)合并去重,Non-Negotiable 留指针 |
| reviewer-simulator | 471 | ~390 | 重复训诫("语气严苛"等同义反复~80 行)精简 |
| general-sci-writing | 608 | ~550 | Phase 10.5 合规门禁细则下沉,留触发+阻断条件;Phase 11-16 精简 |
| revise-sci | 249 | ~235 | "第十七轮"开发日志移到 CHANGELOG |
| nsfc-proposal | 259 | 不缩 | V-11/V-12 摘要上浮(小增,提升可见性) |
| reviewer-response-sci | 297 | 不缩 | 已较精炼 |

执行方式:派 6 个 sonnet agent(按技能),带各自下沉清单 → 瘦身后逐个端到端实测 → 通过才提交。

### 阶段二:从 academic-research-skills 引入高价值能力(opus 彻查后,2026-06-16)
**事实更正**:该仓库**仅 4 个技能,无任何 AI 文生图**(穷举 grep 零命中)。所谓"生图"=academic-paper 的 visualization_agent 生成 **matplotlib/ggplot2 代码**(9 类统计图,含 forest/funnel plot),非 DALL-E/SD。

候选(按 价值/成本 排序,待用户选范围):
| # | 能力 | 接入我方 | 成本 | 推荐 |
|---|---|---|---|---|
| 1 | **统计配图代码生成**(16 模板+决策树+APA caption+色盲安全+VLM 验证) | gsw/review/sci2doc 写作配图空白;本地已有 matplotlib/seaborn skill 可复用 | 轻 | ⭐强推 |
| 2 | **引用完整性硬门**(100% Crossref/S2 API 核验存在性,灰区=FAIL,7类幻觉检查) | 接各写作技能产出后,防幻觉引用 | 中 | ⭐强推 |
| 3 | WHY-HOW-WHAT 轻量文献档 | review-writing 前置中间档 | 轻 | 可选 |
| 4 | 魔鬼代言人对抗角色 | reviewer-simulator(挑核心论点漏洞,CRITICAL 可阻断接收) | 中 | 可选 |
| 5 | Patch 修订协议(anchorize→patch→确定性 apply) | revise-sci 降整篇重写漂移 | 中 | 可选 |
| 6 | calibration FNR/FPR 校准 | reviewer-simulator 自报误差 | 中 | 可选 |
| 7 | ⏸ deep-research/pipeline 全编排器 | —— | 重 | 不建议全盘移植:我方定位是单技能深做,非流水线产品;只借"阶段转换注入原则提醒"防 context rot |

### 阶段二 · 已确认范围与详细计划(✅ 2026-06-16 全部完成)
> 完成:2.1 系统综述方法学(PRISMA/RoB/meta/GRADE,review-writing)、2.2 配图 opt-in(gsw/sci2doc/review)、2.3 引用完整性增强(by-title 核验)、2.4 魔鬼代言人+calibration(reviewer-simulator)、2.5 Patch 修订(revise-sci)、2.6 WHY-HOW-WHAT(review-writing)。均实测通过。
引入 6 项(配图 opt-in),编排器移阶段三不做。**总原则:补的功能尽量放 references/scripts,SKILL.md 只加触发点,不让主文件再膨胀(与瘦身协调)。每项改完实测、分批 commit。**

**2.1 系统综述方法学 → review-writing(重点)**
- 解除对 systematic/meta 的排除,新增"系统综述模式"(与叙述性/scoping 并列,模式开关)
- 补:PRISMA 2020(检索→去重→筛选→纳入,数字流图)、纳入/排除标准登记、RoB(RoB2/ROBINS-I)、可选 meta(效应量/异质性/森林图数据)、GRADE 证据分级
- 放 references/systematic_review_methodology.md + state_manager 加 PRISMA 计数字段;SKILL.md 仅加模式触发点
- 复杂度:中-重;验证:按系统综述模式实操一个样例

**2.2 配图代码生成(opt-in)→ gsw / sci2doc / review-writing**
- opt-in:figure 阶段问"是否需 AI 生成配图代码?"默认否(基础实验自作图;生信等启用)
- matplotlib/ggplot2 代码,9 类统计图(含 forest/funnel),APA caption,色盲安全,300DPI
- 复用本地 matplotlib/seaborn skill + 新增 references/statistical_figure_standards.md;不重造
- 复杂度:轻;验证:生成 forest plot 代码跑通

**2.3 引用完整性增强 → 统一 citation_guard(6 份共享)**
- 增强非新建:① 无 DOI/PMID 条目用 Crossref/S2 按标题核验存在性(不只进 manual queue)② 扩展失败模式提示(伪造结果/方法论捏造等)
- 保持白名单政策(pubmed-cli/paper-search);先改 gsw 权威版+测,再同步覆盖其余 5 份
- 复杂度:中;风险:S2 限流、标题匹配假阳→阈值+人工复核;验证:无 DOI 条目 by-title 核验

**2.4 reviewer-simulator 增强**
- 魔鬼代言人:对抗复查维度(核心论点漏洞/cherry-picking,CRITICAL 阻断接收),放 review_rubric.md,SKILL.md 留触发点
- calibration:可选模式,金标准集测 FNR/FPR(无标注集则跳过)
- 复杂度:中

**2.5 Patch 修订协议 → revise-sci**
- anchorize→patch→确定性 apply(哈希校验,只改触及 block),2 脚本
- 复杂度:中;验证:改一 block 确认其他 block 字节不变

**2.6 WHY-HOW-WHAT 轻量文献档 → review-writing**
- 中间档(介于快速摘要与完整综述):WHY 动机/HOW 方法/WHAT 发现 三层结构化;轻量模式
- 复杂度:轻

### 执行顺序
1. **阶段一瘦身(全部)→ 端到端实测** — 先确立干净精炼基线
2. **阶段二 2.1-2.6** — 补功能(下沉优先)→ 各项实测 → 分批 commit
3. 阶段三编排器:本轮不做(见下)

### 阶段三(列入计划,本轮不做)
编排器:7 技能串 research→write→review→revise→finalize 总控 + 状态机 + 跨 session 断点续跑;或先只借"阶段转换强制注入核心原则提醒"防 context rot。待阶段一二完成后评估。

### 高风险项与缓解
- 系统综述方法学:子系统大 → 独立 references + 模式开关,主文件最小,防 review-writing 膨胀
- 引用完整性增强:改 6 份共享 citation_guard → 先 gsw 权威版改+测再同步,白名单政策不变
- 配图 opt-in 默认关 → 不打扰基础实验用户

## 八、端到端实测发现(2026-06-16,7 opus agent 真实驱动技能写内容)

**验证用户判断**:每个技能**确实内置评审/质量闭环**(pipeline 无需独立)。两层:
- 机器硬门禁(强·真拦):citation_guard 双向核验 + 撤稿检测、Patch 哈希、导出门禁、GB7714
- AI 自觉软门禁(无脚本·靠纪律):compliance/reviewer/coherence/缩写扫描
- reviewer-simulator 可直接作其他技能的下游评审(缺统一稿件交换格式)

**评分**:reviewer-simulator 88 / nsfc 88 / sci2doc 82 / review-writing 80 / gsw 75 / reviewer-response 72 / revise-sci 70

**亮点(实测真生效)**:nsfc 抓出真实撤稿文献 PMID32746878;reviewer-simulator 魔鬼代言人把"结果有效"稿从接收压到大修;revise-sci Patch 字节级不变+哈希拦截;sci2doc custom 导出门禁。

**🔴 死锁级(真实使用必踩)**:
- revise-sci:带编号参考文献的稿**无法过 strict_gate**(export `# References` 一级标题未判 references→剥掉"1."→gate 字面检测 startswith("1.") 必 FAIL)→ 修复中
- reviewer-response:① risk_check 把合法 p 值当捏造**硬拦**(补统计场景不可交付)② build 非幂等,填完重跑**丢工作** ③ --resume 跳过 build→交付**陈旧 HTML** → 修复中

**🟡 中危(待定)**:gsw(merge banner 假阳/working_titles 误读/passive 阈值 50-70 vs ≤30 矛盾/init 缺 abbreviations);sci2doc(Step0.5 outline 门禁无代码强制/缩略语正则/Anti-Drift 白名单冲突);review(PRISMA 不变式无校验/word_counter 硬编码字数);reviewer-response(consistency 双语匹配全量误报);nsfc(humanizer 规则空心化/字段契约未文档化);revise-sci(中文审稿解析退化)

**🟢 优化方向**:软门禁(reviewer/compliance/coherence/缩写/anti-AI)脚本化,降低"走过场"风险;CRITICAL/PRISMA 不变式加机器兜底。

**✅ 2026-06-16 全部修复**:🔴 死锁(revise-sci 参考文献导出 / reviewer-response p值·幂等·HTML·一致性)+ 🟡 全部(gsw banner/working_titles/passive 50-70/init;sci2doc outline门禁代码化/缩略语/白名单;review PRISMA不变式/字数;nsfc humanizer 7→15禁用词/字段契约)。

**去 AI 三项(2026-06-16 新增)**:禁装饰性破折号 / 禁 scare quotes(自造词双引号引用)/ 禁解释性冒号——之前 7 技能基本零覆盖,现已补入**全部 7 技能** anti-AI 规则文字 + style_checker / check_quality / humanizer_zh 检测脚本(保守检测,容许少量假阳;保留术语首次定义、原文引用、比例/时间/标题等合法用法)。

## 九、部分完成自检清单(Definition-of-Done,待补入各技能收口)
**硬规则**:清单未逐项确认通过,**不得向用户声明"该部分完成"**。能脚本核的项挂已有脚本一键跑;人工项逐项确认。

**通用 6 项(全技能)**:① 引文 [n]↔参考列表一一对应(无孤儿/无缺号,编号连续)② 本部分新增引用已过 citation_guard ③ 符合 storyline/主线(不跑题、不与主线矛盾)④ 占位符清零(CITE_PENDING/DATA_PENDING/【待AI】)⑤ 去 AI(三项+句长+禁词,见第十节)⑥ 字数达标。

**技能特有项**:
- **gsw**(每节收口):figure data_status 非 pending+无像素定量+实验逻辑批判+节末 Vancouver 列表+未超期刊字数+只改原子化源
- **review**(每节收口):综合非罗列+矛盾仲裁+引用类型匹配+检索日志+概念框架图一致;〔systematic〕PRISMA 自洽/RoB/GRADE
- **sci2doc**(节+章收口):编号连续+实验-方法映射+一实验≥一图表+三线表+缩略语首展+GB7714 著录+自我抄袭标注+章后 self-check
- **reviewer-simulator**(报告收口):21 占位符+verdict 枚举+CRITICAL 阻断+合规审计+统计子清单+魔鬼代言人+给编辑保密意见
- **reviewer-response**(unit+整包收口):逐条覆盖(Editor 独立)+strategy 基调+承诺↔落点一致+edit_plan 回填+反驳有据+citation registry+各 gate
- **nsfc**(每部分 Phase 收口):H/O/RC/KSQ 一致性(V01-12)+科学问题属性论证+V11 代表作+V12 备选路线+撤稿检测+预期成果段

## 十、去 AI 完整化(对照 humanizer-zh,2026-06-16 调研,5 层:句/词/修辞/结构/标点)
**🔴 最大空白(用户明确担心:长难句/复杂句易暴露 AI):**
- 中文句长无任何硬上限——6 技能全缺 → 补:**中文单句 ≤50 字、从句嵌套 ≤2 层、短长句交替(连续 3 句差异 <5 字告警)**+脚本检测
- 英文单句 ≤30 词硬上限——仅 gsw 有 → 同步到 review/sci2doc/reviewer-response/revise
- -ing 分词从句(", reflecting/ensuring/highlighting…")——仅 review 提及 → 推广 5 技能 + style_checker 正则
**⚠️ 标准割裂(需按文体区分,不一刀切):**
- 被动语态:gsw 50-70%(原始研究)vs review ≤30%(综述)→ 在规则里明确"原始研究 50-70% / 综述 ≤30%"
- 中/英文 AI 禁词表只部分技能有脚本 → 同步(英文表→review/sci2doc;中文表→gsw/sci2doc)
**P1-P2 补充**:同义词循环(同概念同段保持一致称谓)、系动词回避(is/has 不替成 serves as/features)、公式化"挑战与展望"结构、粗体过度、表情符号、模糊归因。
**已充分覆盖(无需动)**:破折号/scare quotes/解释性冒号(三项 6 技能全有脚本)、三段式/否定排比/比喻夸张/正文列表。

## 十一、TODO(下一步执行)
1. ✅ **补 DoD 自检清单**(第九节)到 **7 技能**收口处 + "未全过不得汇报完成"硬规则(2026-06-16)
2. ✅ **去 AI 完整化**(第十节):中文句长 ≤50 字/英文 ≤30 词/-ing 从句/被动按文体区分/中英文禁词同步——多数有脚本检测(style_checker/check_quality/humanizer_zh/risk_check/common.py)(2026-06-16)
3. ⬜(暂缓)阶段三:7 技能编排器
4. ✅ **自检/评审委托独立子代理**(见第十二、十三节):7 技能 DoD 自检改委托独立子代理盲检 + `.claude/agents/academic-blind-reviewer` 预定义 + delegate_review.py pack/verify 脚本固定(2026-06-16)
5. ✅ 实施后 git commit + darwin 7 judge 盲评(见第十三节);⬜ 按需加载优化(各技能 SKILL.md 可瘦身,见第十三节短板,待后续)
6. ✅ **新功能:结构完整性前置闸口**(见第十三节)——写完即检、verify 未 exit0 不得进下一节;opus 双向实测通过(2026-06-16)
7. ⬜ 反例黑名单补强(darwin 共性短板:多数技能缺"❌不要做什么"集中清单);⬜ SKILL.md 按需加载瘦身(gsw/review/reviewer-simulator 偏长)

## 十二、自检/评审委托独立子代理(用户要求 + 三平台调研,2026-06-16)
> 备注:去 AI 的"中英文"指**最终产品(论文/标书)的语言**,非 skill 文本。

**核心原则**:技能的自检/评审**不由主 agent 执行**——主 agent 带着写作上下文自评会**失真 + 注意力稀释**(截图实证:reviewer-simulator 用主 agent 直接审,无隔离)。改为**委托独立上下文的子代理**;流程每步用**脚本固定**防 AI 失忆遗漏。

**三平台子代理机制(调研结论)**:
| 维度 | Claude Code | Codex | OpenCode |
|---|---|---|---|
| 上下文隔离 | 最严(单向,只返最终消息) | 独立 context | session 级(较粗) |
| 并行 | subagents + agent teams(实验性) | 自动并行 max_threads=6 + CSV 批量 | 弱(顺序为主) |
| 自定义 agent | `.claude/agents/` YAML(最全) | `.codex/agents/` TOML | `.opencode/agents/` |
| 技能内触发 | 自然语言即可(最稳) | 需显式 "spawn" | `@mention` 较稳 |
| 结构化返回 | 系统 prompt 要 JSON | CSV+schema(有协议) | 无保证 |

**委托方案(按技能目的:单子代理 vs 并行 team)**:
- **评审多视角**(reviewer-simulator):**并发 N 个独立子代理盲评**(每角色独立上下文、互不知情)→ 主 agent 汇总。**不用 agent team**(对抗讨论是噪音 + team 实验性 + token 高)
- **reviewer-response 一致性核验**:单子代理盲评
- **写作自检 DoD**(gsw/sci2doc/review/nsfc 每节):**单子代理盲检,顺序逐节**(节间有逻辑依赖,并行易漏检);例外:同一节多维度(格式/证据/语言)可并发 fan-out(token 3x,仅 Abstract/Discussion 等高优先级)
- **对抗辩论**(可选升级):agent team,仅 Claude Code + 需用户确认
- **结论**:绝大多数用"独立子代理盲评/盲检",隔离是核心、不是并行

**跨平台可移植写法**:SKILL.md 用**纯自然语言**描述委托——
- 优先路径:派独立子代理,只给稿件路径 + checklist、**不给写作上下文**、要求结构化(JSON)返回
- 降级路径(无子代理能力):主 agent 切换"审稿人视角" + 清空工作记忆重核,不因"自己刚写完"默认通过
- Claude Code 额外:`.claude/agents/blind-reviewer.md` 预定义(tools 限 Read/Glob、model、输出 JSON)强化精确性;Codex 并行用 CSV 批量;OpenCode 用 `@mention`

**每步脚本固定**:委托前脚本生成"子代理任务包"(稿件路径+checklist+约束);委托后脚本校验返回(结构化完整性)+ 写状态文件——防失忆/遗漏。

**不确定项(调研标注,实施时验证)**:OpenCode 真实并行度、Codex 从 skill 文件触发子代理的稳定性、OpenCode 结构化返回可靠性——故降级路径必须保留。

## 十三、实施落地 + Darwin 评估 + 新功能(2026-06-16,已 commit)

**实施(委托盲检落地,commit 7e288a7 / cd95b2a)**
- 地基:`delegate_review.py`(pack 生成盲检任务包 + 返回路径约定;verify 校验返回 fail-closed,缺项/fail/无证据→exit1)+ `.claude/agents/academic-blind-reviewer.md`(限 Read/Glob/Grep/Bash,JSON 输出)
- 7 技能各建 `references/dod_checklist.json`(DoD 机器可读真源)+ SKILL.md DoD 闸口改委托盲检 + 降级路径;delegate_review.py 7 份字节一致(md5 c8fe254)
- reviewer-simulator 额外:多视角评审改"并发 N 独立子代理盲评"(第四步半协议)

**Darwin 7 judge 盲评结果(9 维 rubric,满分100)**
| 技能 | 分 | 守规(委托盲检/citation白名单/去AI) | 主短板 |
|---|---|---|---|
| general-sci-writing | 74 | 全✅ | SKILL.md 594行偏长可瘦~100 |
| review-writing | 81 | 全✅ | DoD散文与json双写、Step4未显式触发三禁 |
| sci2doc | 77.5 | ✅ | scare quotes正则漏中英混合 |
| reviewer-simulator | 72 | ⚠ | 多视角并发依赖平台子代理能力(降级时隔离失真) |
| reviewer-response-sci | 77 | ⚠→已修 | (原)三禁宣而不检、RR13命令缺参 |
| nsfc-proposal | 78 | ⚠→已修 | (原)9个DoD命令flag虚构 |
| revise-sci | 65 | ❌→已修 | (原)5个DoD命令虚构、检查点🔴少 |

**Darwin 暴露的系统性 bug + 修复(commit a5e27be)**
- ⚠ 扩散时子代理在 dod_checklist 虚构脚本命令(flag/子命令不存在,一跑就 argparse error → 盲检无法核验、fail-closed 失效)。逐项 --help 核验后全修:review(R10/R12)、sci2doc(--category/validate_all)、nsfc(N1/N9/N47/6字数项 summary→count)、reviewer-response(RR13)、revise(RV-G3/R4/R5/R6/R7)。独立检查器复核无残留虚构。
- 去AI"宣而不检":reviewer-response risk_check.py 补三禁、revise common.py 补 scare-quote+解释性冒号,均自测检出。
- reviewer-simulator validate_report_html.py 补 VERDICT_CLASS 校验(A2 门禁)。
- **教训**:扩散脚本命令必须独立 --help 核验签名,不能只查脚本文件存在。

**新功能#4:结构完整性前置闸口(commit a5e27be)**
- 各 gate 加"结构完整性"item(gsw G13/review R15/sci2doc S6+S8/简 B8/response RR14/nsfc N52-58/revise RV-R8):对照 storyline/outline 逐结构组件核对(如 Discussion 四段含强制 Limitations),缺段即 fail。
- SKILL.md 加显性前置闸口:**上一节 verify 必须 exit0(含结构完整性)才能进下一节——写完即检,不过不进**。
- **opus 双向实测通过**:缺 Limitations 段→G13 fail→verify exit1 拦截;四段齐全→G13 pass→exit0 放行,无误拦。

**自检流程启动时机**:每节/每章/每部分**落盘后、进入下一节前**(写作类);报告/letter **出具前**(审稿/回复类)。机制=主 agent 写完→pack→派独立子代理盲检→verify;exit≠0 则据证据修复重检,**未过不得声明完成/不得进下一节**。

## 十四、本轮新决策与计划(2026-06-16,用户确认)

**核查结论(4 问,Explore 实证)**
- Q1 gsw figure:已符合——/figure 逐图逐子图(panel)循环:发图→中文(结果+讨论)草稿+❓→用户确认→英文落盘 figure_N.md→下一张。无需改。
- Q2 review 系统综述:已整合非分支——review_type 枚举(narrative/critical/scoping/systematic/why-how-what),共用 5 阶段主流程,systematic 仅按需挂接 PICO/PRISMA/RoB/GRADE(+可选 meta)。无需改结构。
- Q4 revise-sci vs reviewer-response:前者重型全管道(回复+改后正文 docx+Patch哈希),后者轻量只出 HTML 回复包不改稿;上下游关系不冗余。

**本轮要做(用户拍板)** — ✅ 全部完成(commit 516c3e8/5a8dd8e/7f458ea)
1. ✅ **sci2doc 学位区分**:解除"仅博士≥8万"硬锁;开头**询问学位类型 + 询问具体正文字数**(默认博士 5w/硕士 3w,可配置);**正文定义=摘要→正文结束(全文参考文献前),排除"论文综述"章及其参考文献**。改点:SKILL.md(去博士锁+询问+正文定义)、state_manager.py(动态字数门禁、degree_type、正文统计排除综述)、check_quality.py(动态 target + 页眉博士/硕士)、QUICK_START.md。
2. ✅ **sci2doc 通用材料库**:新增多格式(PDF/Word/Excel/md/图片)分析→结构化素材档(实验数据/方法/图表清单),供按章扩写引用。放 references/scripts,SKILL.md 只加触发点。
3. ✅ **触发词理清**:revise-sci description 补中文触发词(改稿/修改稿子/修订正文/退稿改进/返修);gsw 与 reviewer-response/revise 在 description 写清分工边界,降低误路由。
4. ✅ **所有 7 个学术 SKILL.md 去AI化**:移除 AI 腔/施压套话(如"任何偏离视为失败")/装饰破折号/scare quotes/解释性冒号/废话段(说白了/综上),提升文档可读性(对齐 darwin dim7)。注意:这是 skill 文本本身去AI,与"产品去AI"并行不冲突。
5. ✅ opus 实测新功能(学位区分 + 材料库,含自检)。

**仍挂起**:按需加载瘦身(darwin 指出 gsw/review/reviewer-simulator 偏长)、反例黑名单补强。

**opus 实测发现 6 bug 并已修(commit 5a8dd8e)**:综述章作用域继承(子小节泄漏)、摘要计入正文、默认值按学位、degree白名单、material safe_name碰撞、exclude_from_body_count落地。独立复验通过。

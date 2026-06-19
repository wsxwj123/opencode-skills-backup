# 八个学术技能 · 审计与优化状态

> 维护者:Claude Code · 最近更新:2026-06-16
> 范围:general-sci-writing / review-writing / sci2doc / reviewer-simulator / reviewer-response-sci / nsfc-proposal / revise-sci / polish-sci

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
| B4 | sci2doc | custom 格式 pending_template→ready 永久卡死:missing_requirements 只累加不重算 | thesis_profile.py:944-960 | ✅已修(2026-06-16复核:每次 normalize 重置 missing=[]再重算,status 不继承旧值) |

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
7. ✅ 反例黑名单补强(2026-06-16:6 技能补齐,opus 审计全 PASS,见第十五节);🟡 SKILL.md 按需加载瘦身(本轮只清真冗余 review-writing DoD,未空砍执行主线;如需压到具体行数待用户给目标值)

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

## 十五、反例黑名单补强 + 瘦身 + 同步链修复(2026-06-16,commit 901eb8a/cb44d82)

**反例黑名单(darwin 共性短板)** — ✅ 6 技能补齐
- 现状核查:仅 review-writing 已有"绝对禁止"块;其余 6 个全缺集中黑名单。
- 做法:每技能派 sonnet 子代理从**自身文档真实失败模式**提炼 8~16 条 ❌(非通用套话),我手写 revise-sci 的;均去 AI(用"／"与全角括号,无装饰破折号/scare quotes/解释性冒号)。放置:gsw 写作禁忌内、sci2doc Common Mistakes 后、reviewer-simulator 特殊注意事项后(无序号避免冲突一二三)、reviewer-response 收口前、nsfc Quality Gates 后、revise-sci DoD 前。
- opus 独立对抗审计(真实性/矛盾性/去AI三项逐条核)。

**瘦身(反向拷问后只做真冗余)**:这些 SKILL.md 已是高度"📖 pointer+references"按需加载结构,行数长 ≠ 注意力稀释,不空砍执行主线。仅清理 review-writing DoD 与 dod_checklist.json **逐字重复的 15 项清单**(pack 运行本就完整打印,已实测验证 15/15),收敛为指针+分组总览,-18 行。其余文件未动。

**同步链修复(Q2+Q3 根因)**:`.github/workflows/sync-custom-skills.yml` 原仅同步 6 技能、**漏 revise-sci**(paths/rm/checkout/add 四处都缺)。已四处补齐 + 名称 6→7。push main 触发 Action 成功,**custom-skills 分支现含全部 7 技能含 revise-sci**(已 gh api 验证)。

**三平台同步(Q1)**:claude=唯一源已与 origin/main 同步;opencode/codex 本是纯文件副本,本轮 commit 前落后 10~34 处,已 rsync 重新镜像(排除 .git/.system/.github/.review_*),**7 技能三处现 diff 全 0**。

**Figpad 调研(Q4 整合问)**:Figpad/academic-writing-polisher 是纯指令零代码 skill、MIT-0、能力远低于 revise-sci(后者 25 脚本全管道),**不建议整合**,唯一可借鉴 Risk Flags 观念。revise-sci 是审稿意见驱动改稿(非全文润色),polish 仅作用于被改片段;**有原子化拆分**(atomize_manuscript.py + comment-scoped state window),但围绕意见落点,非 sci2doc 式 materials/ 全量素材库。

**opus 黑名单审计结果**:6 个黑名单逐条核真实性/矛盾性/去AI三项,**全部 PASS,无编造/无矛盾/无 AI 痕迹**,每条都能在正文或 references 找到对应规则。

**审计附带揪出 2 处既有文档矛盾(非黑名单引入)**:
- ✅ **已修**:sci2doc Acceptance Checklist 残留 `Body target >= 80,000`(解除博士锁时漏改),与新博硕地板(50000/30000)冲突 → 改为学位地板值表述。
- ⏳ **待用户定**:nsfc V-12 验证阶段冲突——SKILL.md 正文称 V-12 延到 Phase 7 验、Phase 2 不验;references(02/05/08)定义 V-12 "阻断 Phase 3"。黑名单对齐了 references。究竟哪个阶段是权威,需领域决策后统一,本轮不擅改。

## 十六、用户逐技能提问闭环表(截至 2026-06-16)

> 仅统计**用户明确提出的问题**;darwin 自查发现的 backlog 单列(见下)。

| 技能 | 用户提的问题 | 结论/动作 | 状态 |
|---|---|---|---|
| general-sci-writing | figure-plan 是否逐图逐子图确认后落盘原子文件 | Explore 实证已符合(发图→中文草稿+❓→确认→英文落盘),无需改 | ✅ 闭环 |
| review-writing | systematic 模式该整合非分支?与普通综述区别 | 已是 review_type 枚举整合(非分支),共用主流程仅按需挂接 PICO/PRISMA/RoB/GRADE | ✅ 闭环 |
| sci2doc | 是否分析用户材料落盘 + 博硕区分(正文定义/字数) | 新增 material_ingest 通用材料库;开头问学位+字数(博5w/硕3w可配);正文=摘要→正文末排综述章 | ✅ 闭环(+本轮修 80000 遗留) |
| revise-sci | 用途(润色还是审稿驱动)?Figpad 整合?有无原子化拆分 | 审稿意见驱动改稿(非全文润色,polish 仅改片段);Figpad 不整合(零代码能力低);有原子化拆分(围绕意见落点) | ✅ 闭环 |
| reviewer-response-sci | 与 revise-sci 的区别 | 只出 HTML 回复包不改稿(revise 改主稿+出 docx+Patch);description 已写分工 | ✅ 闭环 |
| reviewer-simulator | (无专门提问) | 受益于委托并发盲评 + VERDICT_CLASS 校验 + 黑名单 | — 无未决 |
| nsfc-proposal | (无专门提问) | 受益于 N1-N58 + 命令 bug 修复 + 黑名单;**但审计发现 V-12 阶段冲突待你定** | ⏳ 1 项待决 |

**结论:用户明确提出的每条逐技能问题均已闭环。** 唯一需你拍板的是 nsfc V-12 验证阶段(Phase 3 阻断 vs Phase 7 验证,究竟哪个权威)。

**非用户提出、仍挂起的 darwin backlog**(供决定是否后续处理,本轮未动):① 第六节 B3(sci2doc init 前置页泄漏 cwd,行号已漂移待重核)+ 其余中危项(第190行清单:gsw passive 阈值矛盾、review PRISMA 无校验、reviewer-response 双语匹配误报、nsfc humanizer 空心化等);② 暂缓的 7 技能编排器;③ 激进瘦身(待目标行数)。

## 十七、本轮范围(2026-06-16 用户拍板,执行中)

**用户决策**:① darwin backlog **逐个核实+修复**(复杂代码用 opus 子代理);② **不再做 skill 瘦身**(彻底搁置);③ V-12 冲突要解释(已解释)。

**V-12 冲突定论方向**:references(02/05/08)"阻断 Phase 3" 正确;SKILL.md(135/157)误把 V-12 与依赖 F/预算的 V-06/07/09/11 混为一类、误延后到 Phase 7。alternative_plan 只依赖 M(Phase 3 已写),不依赖后期字段。**修复方向:以代码实际执行点为准,改 SKILL.md 对齐 references**(opus 按代码定论)。

**本轮新增任务(todolist)**:
- T1 nsfc V-12:按代码实测确定真实执行点,改 SKILL.md/references 统一(opus)。
- T2 darwin backlog 逐技能核实+修复(opus,每技能独立 dir 防冲突):sci2doc(B3 cwd 泄漏/Step0.5 outline 门禁无强制/缩略语正则/Anti-Drift 白名单)、gsw(passive 阈值 50-70 vs ≤30 矛盾/merge banner 假阳/working_titles 误读/init 缺 abbreviations)、review(PRISMA 不变式无校验/word_counter 硬编码)、reviewer-response(consistency 双语匹配误报)、nsfc(humanizer 空心化/字段契约未文档化)、revise-sci(中文审稿解析退化)。**先核实 live/stale(B4 即曾误标),只修 live。**
- T3 跨技能一致性审计 + 实测:4 维(流程合理性 / 去AI化 / 文献反向验证 / 自检委托盲检)在 7 技能是否统一,缺口补齐(opus,在 T2 修复后审计)。
- T4 Figpad polish gap:revise-sci 的 polish 相比通用润色缺什么能力(opus 读 revise-sci polish 代码 + 已有 Figpad 结论)。
- T5 缺失技能域:纯论文润色、图片生成(gpt-img2/生信图)是另起技能还是整合进现有?(现有已有 write/humanizer-zh、generate-image/gpt-image-2/comfyui/matplotlib/seaborn/scientific-visualization——评估是否够用 / 是否需学术专用封装)。
- T6 状态文件 + 提交收尾。

### 十七.1 T1+T2 执行结果(2026-06-16,8 opus 子代理,commit aa9ad39..38caf9e)

**规律:darwin backlog 大半 STALE(早被修过,同 B4)。逐个核实后只有 5 处真 LIVE,已修。**

| 技能 | flagged 项 | 判定 | 处置 |
|---|---|---|---|
| review-writing | PRISMA 不变式无校验 | STALE | 已实现 `_validate_prisma_invariants`(写入时校验+非阻断警告) |
| review-writing | word_counter 硬编码 | **LIVE** | ✅ 修正则:`**Word Count Target:**` 加粗格式原被静默忽略回退默认,加 `[*_]*` |
| revise-sci | 中文审稿解析退化 | **LIVE** | ✅ `atomize_comments.py` 编号正则补全角标点(．、、（4）),8段→4条正确 |
| gsw | merge banner 假阳 | **LIVE** | ✅ style_checker/proofread 加 `is_merged_derivative` 过滤合并稿 |
| gsw | passive阈值矛盾/working_titles/init-abbrev | STALE×3 | passive 全仓统一50-70%("≤30"实为单句词数,flag 误读);其余已实现 |
| sci2doc | 缩略语氨基酸排除过宽 | **LIVE** | ✅ 收窄为仅排除标准三字母残基码+位点号,P53/Bcl2/Th1 不再误删 |
| sci2doc | B3 init泄漏cwd/Step0.5门禁/Anti-Drift | STALE×3 | 已用 effective_root+abspath;preflight 已 fail-closed;白名单无冲突 |
| nsfc | V-12 文档冲突(T1) | **LIVE(文档)** | ✅ 代码定论 V-12=ERROR每次全量算、Phase3起硬门控;改 SKILL.md+json 对齐,代码零改 |
| nsfc | humanizer空心化/字段契约 | STALE×2 | 检测全生效;契约已集中于 references/02 §2.2 |

全部改动已 py_compile + JSON 校验 + 新增行无 em-dash + 复核 diff 为外科改动;5 技能已镜像 opencode/codex(diff 全 0)。

**核实中浮现、本轮未改的待决项(新发现,非原 flag)**:
- reviewer-response:双语"承诺↔落点"校验偏松会**漏报**(英文承诺新增实验、实际只改图注却放行)。与原 flag(误报)相反。建议另开 backlog 收紧(需中文承诺↔落点语义比对,属新逻辑)。
- sci2doc:缩略语英文全称无左边界会吞句首词(`We used Polymerase Chain Reaction (PCR)`)。修法有歧义,待定方向。
- nsfc:代码无 phase 概念,V-12 的"Phase 2 不读其结论"靠操作者自觉;建议 Phase 2/3 门控改用 `validate-one <rule>` 精确取该阶段规则,机制上防"看全量输出误判"。需用户确认是否落地。

### 十七.2 T4 Figpad polish gap 结论

revise-sci 的 polish 在"防过度改写"上**已强于 Figpad**(meaning_changed/scope_respected/locked-context 三重硬门禁 + 去AI五项代码强制,均超 Figpad 软自检)。真缺口仅 3 个**片段级可门禁化**点,建议作为新增强(非 backlog):A 数值/统计值守卫(raw↔polished 数字 token 比对);B 不确定性动词校准(防谨慎动词升级为强断言,并需先验证 common.py:84 是否误删主动词 demonstrates);C Risk Flags 输出化(保留 fail,额外输出风险清单)。不补:全文自由润色、全文术语词典(违反 scope-lock)。

### 十七.3 T5 缺失技能域结论

- **纯论文润色 → 真缺**,建议新建轻量 `polish-sci`。`write`/`humanizer-zh` 目标函数相反(注入个性/删 hedging/被动改主动=有害),且无"引用/数值/基因名/统计量零改动"红线。不整合进 gsw(污染18-phase流)。反问待用户:独立技能 vs gsw 加"只润色"入口模式,取决于润色请求频率。
- **图片生成 → 不缺**。scientific-schematics(机制图)+matplotlib/seaborn/scientific-visualization(生信统计图)+gsw/review 内置 opt-in 配图三层齐备;最多图型清单补一行 volcano/MA plot。

### 十七.4 T3 跨技能 4 维一致性审计结论(opus,共享脚本 md5 取证)

**已统一 2 维**:
- 维度4 自检:**最统一**。`delegate_review.py` 7 份字节一致(md5 c8fe254a);7/7 接入委托盲检 + 结构完整性项 + 前置闸口 + dod_checklist 机器真源;gate 名 SKILL.md↔JSON 全对得上。前置闸口粒度差异(review/sim 用产物级)合理。
- 维度1 流程:7/7 有骨架+确认点+门禁;写作类用交互式 HALT、流水线类用 Intake 前置+脚本串行 gate,差异合理。

**3 个 HIGH 真缺口(宣称有实则脚本无)→ ✅ 全部补齐(commit dc7ec98/d6f349a/d71e141)**:
- G1 review-writing 无去AI脚本 → ✅ 复用 gsw style_checker.py 适配综述(被动单向≤30%可配、扫drafts/、补单句>30词),接线 Phase3 D5+dod R5。smoke-test 脏稿命中全部/净稿满分。
- G2 reviewer-simulator 无去AI脚本 → ✅ 复用 nsfc humanizer_zh.py + 新增 scan_report_humanize.py(剥HTML取正文再扫),接线第七步+dod B7。smoke-test 脏/净/端到端全过。
- G3 nsfc citation_validator 缺 provider 白名单 → ✅ 用现成 search_source 字段加 FORBIDDEN_PROVIDER_FAMILIES(tavily/openalex 拦,pubmed/paper-search 过,缺字段保守放行)。
  > 三处均 py_compile+JSON+功能 smoke 复核通过;新脚本含 em-dash 属检测正则(合法)。残留:被动正则偏严(可配+人评兜底)、provider 声明式校验固有边界(真论文+假标签查不出/缺字段可规避)——记录待你定是否收紧。

**MID(记录,本轮不动)**:response/revise 去AI脚本缺 forbidden-word 黑名单(common.py 仅4词样例);citation_guard 三套实现(全功能/精简/nsfc validator)长期应收敛归一,避免改双向阈值要动3处。

**可豁免差异(合理,不动)**:sci2doc/nsfc 无 -ing 检测(中文文体);中文技能无被动50-70%层;review/sim 前置闸口产物级。

### 十七.5 待你拍板的决策(汇总)
1. 纯论文润色:新建 `polish-sci` vs gsw 加"只润色"入口模式。
2. revise-sci polish 三增强 A/B/C(数值守卫/不确定性动词校准/Risk Flags 输出)是否做。
3. 新发现 3 项:reviewer-response 漏报收紧、sci2doc 英文全称吞句首词、nsfc validate-one 防误判。
4. MID:response/revise 补禁词表、citation_guard 三实现收敛。
5. (trivial)gsw/review 图型清单补 volcano/MA plot。

## 十八、决策落地批次(2026-06-16,commit cddaf3e..625e45e)

**用户拍板**:polish-sci 新建 / revise-sci A/B/C 都做 / 补 volcano+MA / 补 response·revise 禁词表 / 不做 citation_guard 收敛(澄清:citation_guard 只有 4/7 共享 gsw 版,response·revise·nsfc 是各自变体,收敛=重构,暂不做)。

- ✅ 新发现 3 项修复:sci2doc 英文全称剥句首功能词(_trim_en_prefix);reviewer-response 漏报收紧(SUBSTANTIVE_ADD_RE,仅新增类承诺,6 组 smoke 含上轮误报形态确认不复发);nsfc validate 加 `--phase/--rules` 过滤(PHASE_RULES),并把 V-10 移出 phase2/3(它含 M被F覆盖检查、F 早期为空必假阳,结构子检查与 V-01/02/08 重叠不漏)。
- ✅ trivial:gsw/review 图型清单补 volcano/MA plot。
- ✅ revise-sci polish 三增强:A 数值守卫(numeric_tokens_preserved)/B 不确定性动词校准(detect_certainty_upgrade,且核实 trailing-ing 正则不误删主动词=STALE 无 bug)/C Risk Flags 输出(polish_risk_flags,保留 fail);+MID 补 AI 套话禁词表(find_ai_style_markers)。均加 strict_gate 校验项 + smoke。
- ✅ MID:reviewer-response risk_check 补 forbidden_ai_phrase 禁词表(23 英+14 中,去重防双报,WARN 级)。
- ⏳ **polish-sci 新建**:待设计确认后建(复用 revise-sci 强化后 common.py 检测器 + delegate_review;纯润色全文,红线保留引用/数值/基因名/统计量)。

全部 opus 子代理产出经主 agent py_compile + JSON + em-dash + 功能 smoke 复核(含修掉代理在代码注释里写的 em-dash);每逻辑一 commit,5 技能镜像 opencode/codex 全 0。

## 十九、polish-sci 新建(2026-06-16,commit bbfd108)— 学术技能升至 8 个

✅ **polish-sci**:纯论文润色技能(无审稿意见、逐段全文润语言)。文件树:SKILL.md + references(dod_checklist.json[polish-dod PL-G1~G9] + polish_rules.json[被动阈值/不确定性梯度/红线]) + scripts(common.py 从 revise-sci 复制并加中文 certainty 模式 / delegate_review.py 字节复制 / atomize_manuscript / polish_units[pack+verify] / merge_manuscript[--docx 可选] / strict_gate / polish_report)。
- 复用:revise-sci 强化后 common.py(数值守卫/语气校准/AI 套话禁词表)+ delegate_review 盲检(第 8 个接入)。
- 红线:引用/数值/专名零改、meaning_changed 必 false;strict_gate fail-closed。
- 端到端 smoke:正常润色 PASS;数值改错/语气升级/留 AI 套话/meaning 变 均 FAIL exit1。py_compile×7 通过、2 JSON 解析、delegate_review pack 打印 9 项。
- 分工:gsw 写新稿 / revise-sci 意见驱动改片段 / polish-sci 纯润色全文,三者 description not_for 互斥。
- 接入同步链:sync workflow 升 8 技能(paths/rm/checkout/add 四处+名称);镜像 opencode/codex;记忆 custom_skills_list 与 MEMORY 索引升 8。
- 残留:polish-sci 的 common.py 因加中文 certainty 与 revise-sci 版不再字节一致(各自维护);docx 导出已实现但 smoke 只验 md 路径;语义层 meaning 守卫靠人工(DoD 已标)。

## 二十、citation_guard 全统一(2026-06-16/17,commit 49b2b08)— 方案B 共享核心

用户明确要求所有文献反验证技能统一。**方案B**:抽 `citation_guard_core.py`(反幻觉策略原语,纯函数,无 IO/argparse)为**唯一真源**,7 技能各留薄适配层。不用方案A(单一字节文件)因 nsfc 是被 import 的库+有 P1 矩阵业务、且 7 技能 6 套产出契约+4 种数据模型,强行字节统一会炸管道+塞死代码。

- **core**(md5 `805f0321`,7 份字节一致):provider 白名单(allow paper-search/pubmed-cli,禁 websearch/openalex-cli/tavily)、DOI·PMID 在线核验、无 ID 时 by-title 存在性、逐源 title 0.72、撤稿、year、HTTP 重试;`validate_core(...,require_identifier=False,prefetched=None)` 两开关。核验强度取基准版为下限,outlier 只增强不削弱。
- **基准 4**(gsw/review/sci2doc/reviewer-simulator):适配层保 `report.ok` 契约,重构前后契约 before==after 零漂移。
- **reviewer-response**:保顶层 status 契约 + **空 registry=放行**业务语义 + 补 allowlist(旧仅黑名单漏未知 provider)。
- **revise-sci**(最高危):两层 loader + prefetched 防 429 + 保 `summary.all_rows_guard_verified`/per-citation `guard_verified` 3 处消费契约 + 空=拦(`bool(rows)` 初值)fail-closed 不削弱。
- **nsfc**:最克制,仅 `validate_entry` 核验段调 core(`require_identifier=True` 保无 ID 硬失败),reason 翻译过滤保三级语义;`matrix_check`/`verify_all`/`extract_citation_numbers` 等 import API + `search_source` 字段 + 默认 paper-search 兼容全留,`diagnosis_engine`/`state_manager` import 零回归(还顺带修了离线误报 title_mismatch 旧 bug)。
- **polish-sci 豁免**(只冻结原引用集合不引新文献)。
- **CI 守卫**:sync workflow 加步骤断言 7 份 core md5 一致,漂移即阻断同步(防今后改 core 漏同步)。
- 改阈值只需改 core + 重新镜像即全局生效。8 opus 子代理(1 个中途 API 死亡但只复制了 core 无损、已重启),全部经主 agent md5+编译+import+契约+smoke 复核;7 技能镜像 opencode/codex 全 0。

> 教训:子代理 API 中途死亡可能留半成品,重启前必须先查工作树状态(本次 nsfc 仅复制 core 未改 validator=无损,重启即可)。

## 二十一、权威·当前未完成/未解决/未实测清单(截至 2026-06-17)

> 本节为**最新权威状态**,优先于前面各节的散落标记。特别地:**第三节 B1-B13 表格里残留的"待修"单元格已过时**——经第六节"全修"+2026-06-17 抽查(B1 三文件已改 OPTIONAL_STATE_FILES+建目录;B2 已中英双语 severity;B5 已改 openalex FORBIDDEN;B7 已 sys.exit 传播)确认 B1-B13 均已修,表格未回填而已。

### A. 未完成的功能(开发层面)
- **A1 7 技能编排器**(deep-research 前置 / academic-pipeline 端到端):一直"暂缓不做"。决定=不做(定位是单技能深做,非流水线产品)。
- **A2 SKILL.md 瘦身**:用户明确**不做了**。关闭。
- **A3 可选借鉴点(从未做)**:Generator-Evaluator Contract(盲承诺→可见评分防漂移)、Style Calibration(用户历史论文提个人学风作软约束)、disclosure(按期刊生成 AI 使用声明)、integrity_verification_agent(7 类 AI 失败模式独立核查层,比 citation_guard 更宽)。状态=未做、可选。已做的借鉴点:Devil's Advocate+calibration(reviewer-simulator)、Patch 修订(revise)、WHY-HOW-WHAT+系统综述(review)、配图 opt-in。

### B. 未解决的问题(已知、有意保留或待定)
- **B-语义守卫**:所有润色/改稿技能(revise-sci/polish-sci/reviewer-response)的"换词是否改了论点"meaning 守卫**只能靠人工逐段对照**,无脚本能查(本质局限,已在各 DoD 标注人工核)。
- **B-citation_guard 声明式边界**:provider 白名单只验声明的 source_provider/search_source,**真论文+假来源标签查不出**;nsfc 缺字段→默认放行(可被"不写字段"规避)。保守设计,未收紧。
- **B-core 收紧副作用**:统一后 core 比旧版更严,历史"勉强通过"的引用条目首次跑可能多拦几条(预期收紧,非回归);response 适配层有意过滤 `source_trace_missing` 以保旧 pass 语义。
- **B-polish A 数值守卫盲区**:同值不同表示(0.5↔50%、p=0.03↔p<0.05)会被判漂移误 fail(保守误报方向,人工经 risk_flags 放行)。
- **B-去AI脚本固有误报**:近年来/realm/testament、被动正则偏严等可能误报,均 WARN 不阻断。
- **B-缩略语全称**:全称真以功能词开头(如 The Hague Institute)会被误剥(罕见,可接受权衡)。
- **B-文档低危待核**:sci2doc GB/T 7714(DOI 前双空格/外文作者姓+名缩写)格式偏差是否已修待核;nsfc `tests/` 目录承诺未实现。

### C. 未实测的(重点)
- **C1 真实完整稿端到端**:所有 8 技能都只经过**子代理构造样例的 smoke/单元测**,**没有用一份真实完整论文/标书从头跑完整管道**。polish-sci 本次跑了 2 段样例端到端(正负向通过),但非真实长稿。
- **C2 在线文献核验(--live)**:citation_guard 全部用 `--offline` 测;**真打 Crossref/eutils 的在线行为未实测**(需联网+代理),线上重试/限流靠 core 逻辑未真实验证。
- **C3 docx 导出**:polish-sci `--docx`、其余技能 docx 导出多数只验 md 路径,docx 实际渲染未实跑。
- **C4 委托盲检真实子代理**:delegate_review 的 pack/verify 脚本已测,但"派真实独立子代理读稿返 JSON"的完整闭环未在真实任务里跑过。

### 建议下一步(若继续)
按价值:C1 真实稿端到端(最能暴露跳步/集成问题)> C2 在线核验抽测 > A3 可选借鉴点(integrity_verification_agent 最有价值)。B 类多为有意的保守设计或本质局限,非缺陷。

## 二十二、polish-sci 真实稿端到端实测(C1+C3,2026-06-17,commit 96c39ba/fbaa120)

用真实 `<测试稿>.docx`(25MB,234 段)跑 polish-sci 完整管道。**这是首次真实长稿端到端**,一次暴露 4 类样例测不出的集成 bug,全部已修:

1. **非 Word 样式标题识别失效**:真实稿"1. Introduction"等是普通段落→section_type 全 other。修:`looks_like_heading` 内容式识别(编号/已知章节名)+ abstract 行内引导特判 + `prose` 标志。
2. **门禁对非散文误判(35 处假阳)**:参考文献(116段)/作者名单的冒号、范围、问句标题被去AI检测拦。修:非散文(`prose=false` 或 `polished_by=unchanged-nonprose`)豁免去AI/句长,红线(数值/引用/语气/meaning)仍对全部单元查。
3. **句长硬拦过严**:方法学合法长句(浓度梯度/参数列表)被硬拦。修:句长 >30词 改软警告(记入报告不阻断,本就声明软检查)。
4. **from-A-to-B 假阳**:`from 24 to 72 h` 数值范围被当 AI 修辞。修:span 含数字即合法范围不判;同款 FP 已传播修 `revise-sci/common.py`。

**最终结果**:全稿 strict_gate **PASS 234/234**(exit 0);merge 出 77KB md;**docx 导出 docx_ok=true(C3 实测过)**;report 列 17 条句长软警告供人工取舍;红线抽查(42-45°C / 2 of 6 / alpha-1-antitrypsin / pBV220-PelB-PPE-His / [99] / 50 passages)全保留;标题作者顺序完整。润色成品已交付用户 Desktop。
**结构 prose 标志全新跑验证**:119 非散文 / 115 散文,pack 存根带 prose,独立于润色器标签生效。

→ 第二十一节 C1(真实稿端到端)、C3(docx 导出)状态更新为 ✅ 已实测(以 polish-sci 为例)。其余技能的真实稿端到端仍未逐一做(C1 仅 polish-sci 完成)。

## 二十三、本轮计划(2026-06-17 用户批准):成稿索引提取 + 摄入技能真稿实测

**用户拍板**:做"原子化时建 figure/reference 交叉索引";reviewer-simulator/revise-sci 用 测试稿 真稿测。

**背景(实测证据)**:
- polish-sci 原子化 测试稿 ✅(234段);revise-sci `atomize_manuscript` 拆 28 节基本对,但**前置页第3条单位"3 某机构 Key Laboratory…"被误判为标题**(行首数字);reviewer-simulator **不做原子化**(整篇读入设计)。
- 摄入类(polish/revise/simulator)目前 atomize 只拆节,**没有从成稿反向抽 figure+图注、[n]+参考文献的交叉索引**(写作类 gsw/review 边写边建,摄入类缺)。

**要做(todolist)**:
- T14 建**共享 manuscript_index 提取器**(DRY,一份真源):`figure_index`(Figure N + 图注 + 引用它的 unit)+ `reference_index`([n]→参考条目→引用 unit,标孤儿:引而未列/列而未引)。定位=审阅辅助+完整性提示,启发式解析"好但非100%"。
- T15 接入 polish-sci / revise-sci / reviewer-simulator 的 atomize/ingest(reviewer-simulator 加一个轻量"抽索引"步以支撑图文/引文审计)。
- T16 修 revise-sci 前置页 affiliation 行首数字误判为标题(实测发现的小 bug)。
- T17 用 测试稿 实测:三技能索引正确性 + **reviewer-simulator 完整审稿跑通(Q2)**。
- T18 状态文件+记忆+learnings+提交+镜像。

**复杂代码用 opus 子代理;每步实测;红线:索引是辅助不替代红线核验。**

## 二十四、索引提取器落地 + reviewer-simulator 真稿审稿实测(2026-06-17,commit ec1be6f..)

**用户 Q3 落地**:建共享 `manuscript_index.py`(自包含、3摄入技能字节一致 md5 fc8d66ca),成稿原子化时反向抽 figure_index(图+图注+引用段+孤儿)+ reference_index([n]→参考条目→引用段+孤儿)+ 人读 manuscript_index.md。接入 polish-sci(步1.5)、revise-sci(pipeline+run_pipeline单入口best-effort)、reviewer-simulator(第四步技术审计辅助)。测试稿 实测三技能一致:9图0孤儿 / 116参考 / 19孤儿引用(列而未引,真实断层)。

**用户 Q1/Q2 实测结论**:
- polish-sci ✅ 原子化正确(234段)、全管道跑通(前轮)。
- revise-sci:atomize 拆 27 节正确(修了 affiliation 行首数字误判 T16);完整流程需审稿意见(仅稿是 intake 中间态)。
- **reviewer-simulator ✅ 真稿完整审稿跑通**:强制门→data初始化→索引辅助审计(实质用于问题9)→全文提取(263段)→空index豁免→四视角(顺序模拟,嵌套限制)→13区块HTML报告→validate OK→去AI OK→DoD盲检ok,判大修。

**真稿暴露并修的关键 bug**:`validate_report_html.py` 扫占位符含模板 `<script>` 里的 `{{...}}` 字面量→**每份正确报告都被误判FAIL**(门禁形同虚设/反而全卡)。修:扫描前剥 script/style。验证 broken→exit1 / 正常→exit0 / REGRESSION_OK。

**残留**:reviewer-simulator 四视角真实运行应为并发子代理(测试环境嵌套限制降为顺序);其余技能真稿端到端仍未逐一(已测 polish-sci 全程 + reviewer-simulator 全程 + revise-sci 原子化)。

## 二十五、用户 6 问逐技能核查(2026-06-17)

**用户问:每个技能流程是否完整、自检是否都在。逐项核查(读真实 SKILL.md/脚本,非凭记忆):**

| # | 问题 | 核查结论 |
|---|------|----------|
| Q1a | gsw Phase4 是什么 | **模板库非流程步骤**。写各章前 `Read references/writing-templates.md`:Intro 五层漏斗 / Methods 可重复性硬清单(货号·RRID·STR·IACUC·accession·IRB·版本+种子·参数·统计独立) / Discussion 四段式(含强制 Limitations) / Online vs STAR 按期刊 / Figure Prompt |
| Q1b | gsw Phase2.5 vs Phase6 冲突? | **不冲突不合并,职责正交**。2.5=图集规划(文献检索前·无图文件·定 Figure 1-N 骨架与 main/SI);6=识图(写作时逐节·用户逐张发真图·出结果讨论草稿)。已内置 6→2.5 迭代回路 |
| Q1c | gsw 自检为何看不到 | **有,在 Phase8 逐节收口**(SKILL.md:352-362):DoD 清单+委托盲检(delegate_review+academic-blind-reviewer)+进入下一节前置闸口(verify exit0)。总览没展开 Phase8 子项故未显现 |
| Q2 | review polish mode 原子拆分?自检? | **都有**。Phase0-P Step2 按标题层级原子拆分→drafts/section_XX_XX.md(用户确认后才写);自检在 Phase3 收口(manuscript-dod 15项+盲检+前置闸口),polish 路由到 Phase3 故共用 |
| Q3a | nsfc 自检为何看不到 | **有,且 8 技能里最密**:P1-P7 每个 Phase 独立 DoD+委托盲检+fail-closed+前置闸口。总览只 grep 顶层"Execution Workflow"未展开 Phase 内联,故显得简短 |
| Q3b | nsfc 是否问实验设计 | **部分——真弱点**。有 Mode Handshake+Inputs Required(basics/科学问题属性四选一/materials/约束);**缺结构化追问实验设计·技术路线·预实验数据的交互环节**,M(技术路线)由 Phase2 AI 据 H/O/RC 展开,靠每 Phase 停顿确认+V-12 备选路线兜底 |
| Q5 | polish-sci vs 其他 polish mode | **纯语言锁内容 vs 混合返修**。polish-sci 只动语言,红线锁死引文/数字/基因名,不补内容不检索;review/nsfc 的 polish 会改写+补缺失节+检索 |
| Q6 | 图片如何提取落盘(9 张主图) | **真缺口:无图片导出落盘功能**。manuscript_index.py/atomize_manuscript.py 全是纯文本正则,只抽"Figure N+图注文字+引用它的 unit"写进 figure_index.json,**不解码/不导出图片二进制**;sci2doc material_ingest.process_image 只对用户单独给的图片文件记路径+大小,**不从 docx 内部解压 word/media/ 嵌入图**。9 张主图的图注/引用关系被索引,**图片本身未落盘到 figures/** |
| Q4 | revise-sci opus 实测基本功能 | **完成**。26/26 语法通过、关键 CLI --help 正常、docx 原子化(5节)+manuscript_index 跑通。发现 2 bug:**high**=短机构名"3 某机构 Key Laboratory…"(8词)被 `is_heading` 误判标题并被相邻空 section flush **静默吞掉**(上轮 T16 的 `≤12 词` 防护挡不住短机构名)→**已修**;**mid**=`atomize_manuscript/atomize_comments` 仅吃 .docx,非 docx 输入抛 `PackageNotFoundError` 无友好报错(契约性缺陷,暂记录待用户拍板) |

**Q4 high bug 修复(2026-06-17):** root cause=编号标题正则 + 仅靠词数阈值,8 词机构名漏过。正解=**加机构词排除**(`_AFFILIATION_HINT_RE`:universit/institut/laborator/hospital/college/faculty/academ/ministr + department/school/center/centre/division of-for + 中文 大学/学院/研究院/研究所/重点实验室/实验室/医院)。改两处(两技能同隐患,实现位置不同):
- `revise-sci/common.py is_heading` 编号分支(≤12词粗筛后追加机构词排除)
- `polish-sci/atomize_manuscript.py looks_like_heading` 编号分支(≤8词后追加机构词排除;polish 阈值更紧但 7 词机构名仍会漏,测试稿 真机构名更长才侥幸没暴露)
回归 PASS:机构名(8词/系/center for)排除 + 真标题(含"Materials and Methods"多词/3.1子标题/Results and Discussion)保留,两技能各 7/7。

**两个待决真缺口(待用户拍板,未动手):**
1. **图片导出落盘**:docx 可解压 `word/media/` 或 python-docx inline_shapes 导出嵌入图到 `figures/`(技术简单);PDF 需 PyMuPDF(较麻烦)。价值:sci2doc 转学位论文把原图搬进产物有实际用;审稿/润色类不读像素,现有图注索引已够。
2. **nsfc 实验设计问询**:可补一个 Phase 0.5「实验设计/技术路线/预实验」结构化问询环节,替代当前"AI 据 H/O/RC 自行展开 M"。

**设计哲学说明**:gsw/sci2doc 的"AI 不读像素"(Zero-Hallucination 读图红线)是当初不做自动抠图的原因——图由用户逐张提供+口述确认。

## 第二十六节 第三轮：4 个 high/mid 项并行修复（2026-06-17）

### 已完成（4 个 opus 子代理并行）

**A. revise-sci 真稿 reviewer-html intake 端到端实测（PASS）**
材料：/Users/wsxwj/Desktop/<测试稿>.docx + 上轮生成的 _review_report.html
17 阶段全部跑通，strict_gate PASS。intake 5 字段（comment_title/problem_description/evidence_anchor/root_cause/author_strategy）完整保留。20 评论 + 27 段 + 9 图 + 116 引文索引齐。
新发现 4 bug：
- **B1 high**：build_reference_registry.py 只认数字 [n] 风格，看不懂作者-年份风格（如 BRAY F, LAVERSANNE M ... 2024），测试稿 116 条参考被识别为 0 条；且 strict_gate 在 references_section_found=false 时 coverage_audit vacuously PASS（更危险）—— 待修
- B2 mid：R1-Major-08 因"Advanced Materials"字面匹配被锚到 References 段，锚定算法应给 References 段降权 —— 待修
- B3/B4 low：build_reference_registry --output-md 必填未文档化；revise_units 缺 --comment-id 调试入口 —— 待修

**B. nsfc 新增 Phase 0.5「实验设计与技术路线结构化问询」**
nsfc-proposal/SKILL.md +45/-8 行。新流程节点：Phase 0 → 0.5 → 1。
- 触发时机：Phase 0 mapping count 确定后强制问询；信息充足可"✓回放确认"省略追问但不得静默跳过
- 逐 RC 5 字段：methods / preliminary_data / feasibility / alternative_plan / ethics
- 落盘 data/experimental_design.json（schema_version 1.0 + entries[]）
- Phase 2 写 M 前必须 Read 该 JSON；V-12 alternative_plan 直接复用
- 新增 5 项 DoD（全为人工/语义核验，无脚本可执行项）

**C. 3 技能 docx 抠图脚本统一落地**
新脚本 extract_docx_images.py 三份字节一致（md5=ea0a8cd5），分别放 polish-sci/revise-sci/sci2doc 的 scripts/ 下。
- 解压 docx 内 word/media/ 所有图到 figures/figure_NN.<ext>（保留扩展 png/jpeg/...）
- 同步出 image_manifest.json
- 不做 OCR、不读像素，贴合"AI 不读像素"哲学
- 集成：polish Pipeline 加 1.6 步、revise run_pipeline.py best-effort try/except、sci2doc Step 0 docx 专用门
- 测试稿 真稿测试：10 张全抠出（1 jpeg 头图 + 9 主图，体量 1–6MB）
- PDF 抠图（PyMuPDF）留 TODO

**D. gsw 流程 2 个 high 缺口已补**
新脚本 figure_analysis_gate.py + abbreviation_consistency.py 进 general-sci-writing/scripts/。
- Phase 8 step 0b 加 figure_analysis 加载硬门禁（缺/未就绪 exit 1）
- Phase 10 step 7 缩略词从 AI 自评升级为脚本化（重复定义/未定义就用/Title 出现缩写）
- DoD 新增 G14/G15，dod_checklist.json 同步加 script 字段
- 冒烟 8 case ALL PASS

### 本轮 commit（fd38beb 之后）
预期 1 个 commit：feat(skills): 第三轮流程完整性补强（nsfc Phase0.5 + docx抠图 + gsw闸门 + revise-sci真稿测）
含：
- nsfc-proposal/SKILL.md
- polish-sci/SKILL.md + scripts/extract_docx_images.py
- revise-sci/SKILL.md + scripts/extract_docx_images.py + scripts/run_pipeline.py
- sci2doc/SKILL.md + scripts/extract_docx_images.py
- general-sci-writing/SKILL.md + references/dod_checklist.json + scripts/figure_analysis_gate.py + scripts/abbreviation_consistency.py
- ACADEMIC_SKILLS_AUDIT.md（本节）

### 遗留（下一窗口）
1. revise-sci B1 high（build_reference_registry 作者-年份风格盲点 + strict_gate vacuous PASS）
2. revise-sci B2 mid（锚定算法 References 段降权）
3. revise-sci B3/B4 low（CLI 文档化、单条调试入口）
4. PDF 抠图（PyMuPDF）
5. nsfc Phase 0.5 真稿实测尚未做
6. 测试稿/某省 测试稿专名在 AUDIT 文档自身的泛化（不影响发布，sync workflow 不带 AUDIT）
7. 流程审计组2 报的 reviewer-response-sci 委托独立盲检未强制化（一致性缺口）

## 第二十七节 第四轮：清空全部遗留项（2026-06-17）

### 已完成（3 个 opus 子代理并行 + 主代理收尾）

**E. revise-sci 真稿测发现的 4 bug 全修**
- B1(high) build_reference_registry.py 现支持作者-年份风格参考文献：扩 HEADING_RE 别名、新增 PLAIN_HEADING_RE（无 # 前缀纯文本 References/参考文献 标题）、AUTHOR_INITIALS_REF_RE（BRAY F, LAVERSANNE M, et al. 类）。真稿验证：AdvMat 116 条参考完整 pipeline 与纯文本 dump 路径均识别 116 条（修复前纯标题路径返回 0）
- B1配套(high) strict_gate.py 空洞 PASS 守卫：正文有引用标记但 reference_entries==0 / references_section_found=false → FAIL（exit 1）；正文无引用则豁免不误伤。双用例验证通过
- B2(mid) revise_units.py 锚定对 References 段候选乘 0.15 降权（非排除）：含"Advanced Materials"的评论现锚到正文而非参考条目
- B3(low) SKILL.md Pipeline 补全 revise_units/merge_manuscript/reference_sync/build_reference_registry/export_docx 完整参数（含 --output-md）
- B4(low) revise_units.py 新增 --comment-id 单条调试入口

**G. docx 抠图加 PDF 支持 + workflow 断言**
- extract_docx_images.py 加 .pdf 分支（PyMuPDF/fitz 按 xref 抠图）；缺 PyMuPDF 时优雅降级（stderr 提示 + note:pymupdf-missing + exit 0 不崩溃）；docx 分支零改动
- 三份字节一致（md5=bc396376），3 个 SKILL.md 措辞更新为"支持 docx 与 pdf"
- sync workflow 新增断言：3 份 extract_docx_images.py md5 一致（任一漂移 exit 1）
- 自测：docx 回归仍 10 张图、PDF 真实抠图 2 张、PDF 缺库降级、YAML 语法 OK

**H. reviewer-response-sci 盲检核实 + AUDIT 脱敏**
- reviewer-response-sci 委托盲检经核实**早已强制存在**（DoD 第274-285行，gate=response-dod，items RR1-RR14，对齐 gsw/nsfc 模板五要素齐全），无需改动
- 注：该技能 delegate_review.py 只有 pack/verify 子命令，无 list-gates
- ACADEMIC_SKILLS_AUDIT.md 测试稿专名脱敏 11→0（AdvMat/AdvancedMaterials→测试稿、Hunan→某省/某机构）

### 至此遗留项清空情况
第二十六节列的 7 项遗留：① B1 high ✅修 ② B2 mid ✅修 ③ B3/B4 low ✅修 ④ PDF 抠图 ✅加 ⑤ nsfc Phase0.5 真稿实测（仍未做，留作可选验证）⑥ AUDIT 专名脱敏 ✅ ⑦ reviewer-response 盲检 ✅核实早已强制。
唯一剩余：nsfc Phase 0.5 真稿端到端实测（功能已实现，仅缺一次真稿走查，非阻断）。

### git 状态
本节随第四轮 commit 一起推送。8 技能 PII 全清零、流程完整、盲检全统一、docx+pdf 抠图落地、参考文献作者-年份风格识别修复。

## 第二十八节 自检脚本化闭环 + 综述功能补缺 + 投稿包（2026-06-19）

### 背景
用户核心诉求：自检不能靠 AI 自觉、要脚本硬拦；并对标小红书"21-skill 综述"补功能缺口。本轮两个 commit 完成。中途用户删本地 ~50 技能导致并发写入被抹，已用"两阶段目录隔离 + 落盘后 git 验证"重做成功。

### commit 412dc5a（已 push）
- prewrite_gate.py（gsw/review/sci2doc/nsfc）：开写每节前硬拦 6 项机械合规——上一节完成/故事线大纲/素材就位(gsw subprocess 复用 figure_analysis_gate+abbreviation_consistency)/占位符清零/缩略词一致/上一节盲检(当时仅warn)。
- review-writing 补 3 Phase：1.5 研究空白识别(research_gap.json) / 1.6 对标综述库+framing_guide / 5 投稿包(Cover Letter/Title Page/CRediT/COI/Funding/DAS/Keywords)。state_manager VALID_PHASES+路由表同步，3 新 gate。
- gsw：Phase 8.6 目标期刊风格深度学习(gate journal-study-dod)；Keywords 设为 submission-pack 强制产出+Phase10.5 compliance 阻断。

### commit（本节）：盲检 warning→脚本硬拦
- delegate_review.py（8 份全改 byte 一致 md5 6b569ca0）：verify 新增可选 --section/--root；全过且传 --section 时落盘 <root>/.review_pass/<section>.json；不传 --section 与旧版逐字节等价(向后兼容)。
- 4 份 prewrite_gate.py：「上一节盲检通过」从 warning 升级硬检查——读上一节 .review_pass 标记，缺失即 FAIL exit 1 拒绝开写；第一节 N/A。
- 4 份 SKILL.md：盲检 verify 命令加 --section+说明。
- nsfc 特殊：盲检按 Phase 粒度，硬检查仅跨 Phase 边界生效(P3 子节内部一次性盲检，同 Phase prev 判 N/A)。

### 闭环达成
开写前置自检 6 项全部脚本硬拦(含最关键盲检)，AI 无法静默跳过。

### 对标小红书 21-skill：功能覆盖
原缺 4 项本轮补齐：研究空白识别/对标综述库/目标刊风格学习/Cover Letter(并入投稿包)。架构裁决：不拆 21 独立 skill(底层脚本已共享+上层场景化是正确形态)。

### 遗留(下一窗口,非阻断)
1. 新增各 Phase(研究空白/对标库/目标刊/投稿包/Phase0.5)真稿端到端实测
2. nsfc Phase 0.5 真稿实测

## 第二十九节 新功能真稿实测 + 强制自检验证（2026-06-19）

### 强制自检实测结论
prewrite_gate 4 技能 × 4 场景全过：盲检无法绕过——伪造标记 / 缺标记 / 无旁路参数三种规避手段均 exit 1，开写被硬拦。nsfc 跨 Phase 粒度精确生效（同 Phase 子节判 N/A，跨 Phase 边界硬校验上一节 .review_pass）。开写前 6 项机械合规为真·脚本强制，AI 无法静默跳过。

### 新 Phase 实测
review 1.5/1.6/5 + gsw 8.6 共 5 个 gate 的 pack/verify 全通过、schema 自洽、fail-closed 生效；投稿包分级与 gsw submission-guide/compliance-gate 对齐。

### 本节修复
1. 4 份 SKILL.md（gsw/review/sci2doc/nsfc）盲检拦截描述对齐脚本：散文从「未落盘降级 warning 不阻断」改为「缺 .review_pass/<上一节>.json 即 prewrite_gate 硬拦 exit 1，须先跑 delegate_review verify --section <上一节> 落盘」；nsfc 版补「仅跨 Phase 边界生效，同 Phase 子节 N/A」。
2. review Phase 1.5 选定 gap 落盘衔接（防长会话丢主线）：HALT 确认选题后，research_gap.json 选中项加 selected=true + outline.md 顶部写主线锚点；Phase 2/3 entry 各加开写前 Read research_gap.json 取 selected gap 作主线依据。
3. research-gap-dod 的 G2 孤儿引文检查扩覆盖：原仅校 gaps+hotspots 的 support_refs，现补 candidate_topics 的 support_refs 与 controversies 的 side_a_refs/side_b_refs；正负用例验证（孤儿 50/99 检出、合法编号 NO_ORPHANS）。

### 记录不改项
review + gsw 的 submission-pack-dod 同名 pack 记录仅在同目录互覆盖；真实使用时各自项目根独立，不冲突，无需改。

### 遗留（下一窗口，非阻断）
1. nsfc Phase 0.5 真稿实测
2. 新 Phase 用真实文献走更长端到端

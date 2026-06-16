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

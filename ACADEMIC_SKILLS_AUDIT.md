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

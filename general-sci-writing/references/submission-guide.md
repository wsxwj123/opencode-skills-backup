# 投稿包详细指南 (submission-guide)

> 被 SKILL.md 的 **Phase 8 (`/submission-pack`)** 引用。执行该阶段时 `Read` 本文件。

## 1. 逐项询问明细（必须主动问，不要静默用空白）

- **Cover letter**：目标期刊编辑姓名 / 核心 significance 一句话 / 3 个 key findings / 适配期刊的理由 / 3 位 suggested reviewer 名字与邮箱 / 是否有 opposed reviewer / 通讯作者信息+ORCID
- **Data Availability**：原始数据是否 deposit？哪个 repository？accession number？源数据 Supp Data 编号？
- **Code Availability**：是否有自定义代码？GitHub URL？license？Zenodo DOI？
- **CRediT**：每位作者承担哪些 role（11 类），用作者首字母缩写（分配指南见第 5 节）
- **COI**：所有作者有无 competing interests（专利、咨询、股权）
- **Funding**：每个 funder + grant number + 受资助 PI
- **Highlights**（Cell 系强制）：3-5 条 ≤85 字符，写完后必须 `wc -L` 确认
- **One-sentence summary / eTOC**：Nature 系 ~150 字符，Cell ~125 字符
- **Graphical abstract**：按 `submission_package.json.graphical_abstract_spec` 出，用户自己画或交付 BioRender，本流程不画

## 2. 目标期刊适配（按需读取）

从 `project_config.json` 读 `target_journal`，挑出该期刊的 `required_by` 项强制：如 Nature 必给 one-sentence summary 与 DAS，Cell 必给 highlights + graphical abstract。

## 3. 报告规范 checklist（强制）

`Read templates/reporting_checklists.json` → 按 `project_config.json` 的 `research_field` 自动挂对应 checklist（如 `drug_delivery`→ARRIVE，`clinical_pharmacy_llm`→CONSORT/STROBE/TRIPOD，CS→ML reproducibility）。再叠加 `target_journal` 特定要求（Nature Reporting Summary、Cell STAR Methods 等）。逐项核查 Methods 与 Results 是否齐全，缺项必须补到 Methods 后才能 `/merge`。**动物实验 ARRIVE 不全 = 多数期刊编辑桌面拒**。

## 4. Source Data .xlsx 准备（Nature/Cell 强制，其他多数期刊 strongly preferred）

- **格式**：一个 `submission/source_data.xlsx`，**每张主图一个 sheet**（Sheet 命名 `Figure 1A`、`Figure 1B`...）。
- **内容**：每个 sheet 含**该 panel 的全部原始数值**（n 个独立实验、每个数据点的原始值，而非只是 mean ± SD）。
- **行列规范**：第一列为分组/时间点；其后各列为各重复（n=1, n=2, ...）；最末行可放 mean / SEM / P 值汇总。
- **不能藏数据**：审稿人会比对 source data 与图表，**数值对不上 = 学术不端嫌疑**。
- 用户自己准备 .xlsx（脚本生成出错率高），AI 给规范 + 检查 sheet 命名与 figures_database 的 figure_id 是否对应。

## 5. CRediT 角色分配指南（学生常犯困）—— 11 类对应典型角色

- **Conceptualization** → 通常 PI + 提出 idea 的核心学生
- **Methodology** → 设计实验方案的人（学生 + PI）
- **Investigation** → 真正做实验的学生（**博士生主体**）
- **Formal analysis** → 跑统计 / 数据处理的人
- **Resources** → 提供独家试剂 / 样本 / 设备的人
- **Writing – original draft** → 写初稿的人（**博士生主体**）
- **Writing – review & editing** → 改稿的人（PI + 共同作者）
- **Visualization** → 出图的人
- **Supervision** → 直接指导的 PI
- **Project administration** → 协调多 lab 的负责人
- **Funding acquisition** → 拿钱的 PI
- **规则**：① 每个 role 至少一位作者，全员覆盖 11 类（无人对应的写"N/A"并解释）② 一位作者可承担多个 role ③ 通讯作者通常 ≥ 4 个 role（含 Supervision/Funding）。

## 6. Acknowledgments 模板（投稿必备但常忘）—— 必须含以下类别，无则写 N/A

- **非作者贡献者**（提供试剂/样本/技术指导但不达 authorship 标准的人）
- **技术平台**（核心设施、共享仪器、生物信息平台）
- **样本/资源来源**（biobank、动物中心、临床中心）
- **预印本/讨论致谢**（在会议或 bioRxiv 收到的有用反馈）
- **Funding 不放 Acks**（独立 funding 章节）

## 7. 红线

① 严禁 `{{VAR}}` 残留 ② 严禁伪造 reviewer 邮箱 ③ COI 已有需主动声明严禁瞒报 ④ Funding 无则写 "This work received no specific external funding"，**不留空** ⑤ **Source Data 数值必须与图对应** —— 不一致即学术不端嫌疑 ⑥ Acks 不能空，无则各类写 N/A。

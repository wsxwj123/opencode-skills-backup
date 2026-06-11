# 文献政策 (citation-policy)

> 被 SKILL.md 的 Role 区与 **Phase 3 (`/literature`)** 引用。检索文献、入库、核验前 `Read` 本文件。
> 底线（不编造文献）已在 SKILL.md 顶部 P0#1 常驻；本文件是完整执行细则。

## 文献检索工具（学科路由，Mandatory）

1. **判断学科类型**：
   - 生命科学 / 医学 / 临床 / 生化 / 药学 → **首选 PubMed CLI**
   - CS / AI / 工程 / 物理 / 跨学科 → **首选 paper-search MCP**（arXiv/Google Scholar）
2. **PubMed CLI**（生命科学首选）：`esearch`/`efetch`/`einfo`（路径 `~/edirect/`），必须带 `< /dev/null`，走代理 `http_proxy=http://127.0.0.1:7897`。
   - 示例：`export http_proxy=http://127.0.0.1:7897 && esearch -db pubmed -query "xxx" < /dev/null | efetch -format abstract`
   - 可用性检查：若 `~/edirect/esearch` 不存在，自动安装：`sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`
3. **paper-search MCP**（CS/AI首选 / 预印本 / PubMed无结果时fallback）：`mcp__paper-search-mcp__search_arxiv`、`mcp__paper-search-mcp__search_pubmed` 等。
4. **严禁**：`tavily`、`websearch`、`openalex`（pyalex）— 无论有无 DOI/PMID。
5. **串行执行（Mandatory）**：所有检索调用（含 paper-search MCP 与 PubMed CLI）必须串行执行，禁止并行，每次间隔 ≥1s。

## 文献真实性硬约束 (Zero-Fabrication Policy)

1. **零容忍**：严禁编造虚拟文献；严禁把不同文献的标题/作者/期刊/年份/DOI 交叉拼接成"新文献"。
2. **来源强制**：写入 `literature_index.json` 的每条文献必须来自 MCP 检索原始结果，并保留可追溯来源信息（至少包含 `source_provider` + `source_id`，如 PMID/DOI/arXiv ID/S2 ID 之一）。
3. **Provider 白名单**：`citation_guard.py` 允许的 provider：`pubmed-cli`（首选）、`paper-search`（CS/AI首选/备用/预印本）；`tavily` 仅限摘要补全与反向验证（见下条）；`openalex-cli` 及 `websearch` 一律阻断。文献**检索**阶段严禁使用 tavily。
4. **Tavily 边界**：`tavily` 只能用于无 DOI/PMID 条目的摘要补全最后兜底；凡带 DOI/PMID 的 Tavily 条目必须判为失败，禁止入库。
5. **入库前核对**：入库前必须核对"标题-作者-DOI/ID"来自同一条原始记录；任一关键字段冲突则判定为无效条目，禁止入库。
6. **双向核验失败处理**：若出现 `title_mismatch`、`doi_invalid_or_unresolved`、`pmid_invalid_or_unresolved`、`id_mismatch`，必须立即设为 `verified=false`，写入 `manual_review_queue.json`，禁止正文引用。
7. **不确定处理**：无法完成同源核验的条目必须标记为 `unverified`；未带 `source_provider` / `source_id` 的条目不得入库。`unverified` 与 `needs_manual_review=true` 条目都**禁止在正文使用 `[n]` 引用**，也不得进入参考文献列表。
8. **补全边界**：摘要补全协议仅允许补全 `abstract` 字段，禁止改写已核验文献的核心元数据（标题/作者/期刊/年份/DOI）。
9. **强制核验门禁**：任何正文写作前与交付前，必须执行：
   - `python scripts/citation_guard.py --index literature_index.json --mcp-cache mcp_literature_cache.json --mcp-ttl-days 30 --manual-review manual_review_queue.json --log verification_run_log.json --report citation_guard_report.json`
   - 若返回非零或报告 `ok=false`，立即阻断写作；必须先处理 `manual_review_queue.json` 后再继续。
   - guard 报告必须显式包含 provider policy、bidirectional failure 与 manual review 触发原因，便于追溯。
   - 不改变检索优先级（学科路由：生命科学→PubMed CLI / CS/AI→paper-search MCP）；仅增加核验门禁。
   - Phase 3 结束时和最终交付前，`--require-mcp` 为强制参数（非建议），确保所有文献有 MCP 证据轨。

## 引用类型按语境（Citation Type by Context，MANDATORY）

- 背景/综述性表述 → 优先引用 Reviews 或 Systematic Reviews，也可引用 Original Articles 作为直接证据支撑。
- 具体机制/实验论点 → 必须以 Original Articles 为主要证据；严禁用 Review 代替 Original Article 作为具体实验论点的唯一支撑。
- 临床疗效/安全性论点 → Clinical Trials（与 Original Articles 同等优先级）。
- 前沿/新兴论点 → Preprints（仅在无同行评审等效文献时使用；引用列表须标注 [Preprint]）。

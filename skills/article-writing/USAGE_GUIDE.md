# Article Writing Skill (v2.16.4) 使用指南

## 📘 完整工作流程示例 (v2.16.4)

### 研究方向配置示例

`article-writing` 默认使用医药领域中的 `drug_delivery` 配置，适用于纳米载体、工程菌、外泌体、病毒载体、细胞治疗等药物递送论文；只有在用户明确指定时才切换到其他 field profile。

**保持默认药物递送配置**：
```bash
python scripts/config_manager.py load drug_delivery
```

**使用药物递送配置**：
```bash
python scripts/state_manager.py set-field --field drug_delivery
```

**使用计算机科学配置**：
```bash
python scripts/state_manager.py set-field --field computer_science
```

**回退到通用配置**：
```bash
python scripts/state_manager.py set-field --field default
```

---

### 场景：撰写一篇pH响应性脂质体治疗三阴性乳腺癌的论文

---

## 文献核验硬门禁（新增默认要求）

在任何 `/write` 或最终交付前，必须先执行：

```bash
python scripts/citation_guard.py \
  --index literature_index.json \
  --mcp-cache mcp_literature_cache.json \
  --mcp-ttl-days 30 \
  --manual-review manual_review_queue.json \
  --log verification_run_log.json \
  --report citation_guard_report.json
```

执行规则：
- 只有 `paper-search` 与受限 `tavily` provider family 能通过 guard。
- `tavily` 仅可用于无 DOI/PMID 的反向核验或摘要补全兜底；带 identifier 的 Tavily 条目会直接失败。
- 只要 `citation_guard` 返回非零、`citation_guard_report.json` 中 `ok=false`，或 `manual_review_queue.json` 非空，都必须先处理，不能继续正文写作。
- `unverified` 或 `needs_manual_review=true` 的条目不得出现在 `[n]` 引用和参考文献列表中。

## 第一步：项目初始化

**用户输入**：
``` 
/init
```

**AI执行**：
```
在同一条消息中先询问：
1. 项目保存路径在哪里？
2. 是否保持默认医药领域药物递送配置（drug_delivery），还是切换到其他 field？

✅ 项目初始化完成！
...
```

---

## 第二步：预审模式

**用户输入**：
```
/preview
...（提供实验设计）...
```

**AI执行**：
```
[Context Check]
- Project Config: ✅ Loaded
...

## 📋 预审报告
...
```

---

## 第三步：故事脉络构建 (v2.0核心更新)

**用户输入**：
```
/storyline
```

**AI执行**：
```
[Context Check]
- Memory: ✅ Loaded
- Lit Index: ✅ Loaded (27 refs)

正在构建v2.0融合式提纲...

## Storyline (Results & Discussion Integrated)

### Section 3.1: 材料表征 (Key Section)
- **Results**: Figure 1A (TEM), 1B (DLS), 1C (Zeta)
- **Discussion Points**:
  1. **Mechanism**: Explain why pH 6.5 triggers charge reversal (protonation of DOPE).
  2. **Comparison**: Compare size stability with [Zhang et al. 2023].
  3. **Significance**: Validate the design rationale.

### Section 3.2: 体外细胞摄取
- **Results**: Figure 2A (Flow), 2B (Confocal)
- **Discussion Points**:
  1. **Mechanism**: Electrostatic attraction facilitates uptake.
  2. **Contrast**: Highlight 3.5-fold increase vs non-responsive control.

...

确认这个融合式结构吗？
```

**用户确认**：
```
确认
```

---

## 第四步：撰写章节 (融合模式 + 自我修正)

**前置条件**：
```bash
python scripts/citation_guard.py --index literature_index.json --mcp-cache mcp_literature_cache.json --manual-review manual_review_queue.json --log verification_run_log.json --report citation_guard_report.json
```

若输出包含以下任一情况，必须先停止：
- `source_provider_not_allowed`
- `tavily_not_for_identifier_entries`
- `manual_confirmation_required_bidirectional_failure`
- `manual_review_queue.json` 中仍有待人工确认条目

**用户输入**：
```
/write results_3.1
```

**AI执行**：
```
[Context Check]
- Storyline: ✅ Loaded (Focus: Section 3.1)
- Fig Database: ✅ Loaded (Fig 1A-1C data confirmed)
- Lit Index: ✅ Loaded (Ref 006 available for comparison)

⚠️ **Writing Mode**: Deep Analysis (Key Section) + Self-Correction

(Thinking Process: Draft -> Critique: "Too verbose?" -> Polish)

---

## 3.1 Characterization of pH-responsive charge-reversal liposomes

The pH-responsive liposomes were successfully prepared using the film hydration method. Transmission electron microscopy (TEM) revealed a uniform spherical morphology with a mean diameter of 120±15 nm (Figure 1A). **This size range is critical for tumor accumulation**, as particles larger than 200 nm are rapidly cleared by the spleen, while those smaller than 10 nm are eliminated by the kidneys [1]. Dynamic light scattering (DLS) confirmed a narrow polydispersity index (PDI < 0.15) (Figure 1B), indicating high batch-to-batch consistency suitable for clinical translation.

A key feature of our design is the charge-reversal capability. As shown in Figure 1C, the zeta potential shifted dramatically from -15 mV at pH 7.4 to +25 mV at pH 6.5 (P<0.001). **This transition is driven by the protonation of the imidazole group in the lipid headgroup**, which disrupts the charge balance in the acidic tumor microenvironment. **Unlike previous designs that required pH 5.0 to switch** [6], our system responds at pH 6.5, which better matches the extracellular pH of solid tumors, ensuring the transition occurs *before* cellular uptake rather than only inside lysosomes.

### References
1. Blanc L, et al. Size-dependent circulation. J Control Release. 2011;150(2):236-46.
6. Zhang X, et al. Charge-reversal strategy. Nano Lett. 2020;20(8):6185-94.

### Figure Legends
**Figure 1. Characterization of pH-responsive liposomes.** (A) TEM image (scale bar = 100 nm). (B) Size distribution by DLS (n=3). (C) Zeta potential change (n=3, ***P<0.001).

---

#### 🧪 Experimental Logic Critique
- **Design Check**: 对照组设置合理 (pH 7.4 vs 6.5)。
- **Reliability**: n=3 是标准设置，P<0.001 显著性极高。
- **Consistency**: DLS 粒径与 TEM 吻合。
- **Verdict**: Reliable.

#### 📊 Status Dashboard
| Metric | Status / Value | Action Required? |
| :--- | :--- | :--- |
| **Word Count** | Sect: **320** | Total: **1540** |
| **Data Logic** | ✅ Pass | None |
| **SI Loop** | Pending: 0 | None |
| **State Sync** | ✅ Saved | None |
| **Snapshot** | ✅ Created | v4_results_3.1 |

#### 🤔 Reverse Interrogation
您只展示了 pH 6.5 的变化，但体内环境很复杂。是否测试过血清稳定性？

#### 💡 You Might Want to Know
为了增强论证，可以在 SI 中补充一段血清共孵育的粒径变化图 (Figure S1) 以证明其长循环能力。
```

---

## 第五步：质量检查

**用户输入**：
```
/check
```

**AI执行**：
```
[Context Check] ...

## 📋 Quality Report
- **Citation Density**: 2.5 refs/paragraph (Healthy)
- **Writing Depth**: Section 3.1 analysis depth > 200 words (Pass)
- **Data Conflicts**: None found.
```

---

## 第六步：最终合并与导出 (v2.1)

**用户输入**：
```
/merge
```

**AI执行**：
```
✅ Merged Markdown saved to: manuscripts/Full_Manuscript.md
✅ Docx generated: manuscripts/Full_Manuscript.docx
```

**用户输入**：
```
/export_bib
```

**AI执行**：
```
正在导出参考文献...
✅ 成功生成 `references.bib` (27条)
您现在可以将此文件导入 Zotero 或 EndNote。
```

---

**提示**：
v2.0版本中，您不再需要单独撰写Discussion章节。所有的机制探讨和文献对比都已融入上述Results写作中。最后只需撰写Conclusion。v2.16.4 起，文献 guard 也会同时检查 provider policy 和人工复核队列，避免将错配条目带入正文。

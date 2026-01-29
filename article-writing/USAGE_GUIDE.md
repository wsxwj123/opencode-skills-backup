# Article Writing Skill (v2.1) 使用指南

## 📘 完整工作流程示例 (v2.1)

### 场景：撰写一篇pH响应性脂质体治疗三阴性乳腺癌的论文

---

## 第一步：项目初始化

**用户输入**：
```
/init
```

**AI执行**：
```
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

The pH-responsive liposomes were successfully prepared using the film hydration method. Transmission electron microscopy (TEM) revealed a uniform spherical morphology with a mean diameter of 120±15 nm (Figure 1A). **This size range is critical for tumor accumulation**, as particles larger than 200 nm are rapidly cleared by the spleen, while those smaller than 10 nm are eliminated by the kidneys [Ref 1]. Dynamic light scattering (DLS) confirmed a narrow polydispersity index (PDI < 0.15) (Figure 1B), indicating high batch-to-batch consistency suitable for clinical translation.

A key feature of our design is the charge-reversal capability. As shown in Figure 1C, the zeta potential shifted dramatically from -15 mV at pH 7.4 to +25 mV at pH 6.5 (P<0.001). **This transition is driven by the protonation of the imidazole group in the lipid headgroup**, which disrupts the charge balance in the acidic tumor microenvironment. **Unlike previous designs that required pH 5.0 to switch** [Zhang et al., Ref 6], our system responds at pH 6.5, which better matches the extracellular pH of solid tumors, ensuring the transition occurs *before* cellular uptake rather than only inside lysosomes.

---

✅ Section 3.1 Completed (Word count: 320)

📸 **Smart Snapshot Triggered**:
- Reason: Generated key content for Section 3.1
- Action: Saving snapshot `v4_results_3.1_auto`... Done.

➡️ Next: Write Section 3.2?
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
v2.0版本中，您不再需要单独撰写Discussion章节。所有的机制探讨和文献对比都已融入上述Results写作中。最后只需撰写Conclusion。

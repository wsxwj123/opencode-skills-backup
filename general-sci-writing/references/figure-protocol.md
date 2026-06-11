# 识图产物模板 (figure-protocol)

> 被 SKILL.md 的 **Phase 4 (`/figure`)** 引用。每张大图收口、落盘 `figure_analysis/figure_{N}.md` 与 `add-figure` 入库时 `Read` 本文件取模板。
> 读图红线（Zero-Hallucination、只读符号化信息、不数散点、读不到就问）见 SKILL.md 正文，本文件只提供落盘模板。

## `figure_analysis/figure_{N}.md` 模板（落盘正文用英文；下方字段中文仅为说明）

```markdown
# Figure {N}: <大图主题>   <!-- section: <section_id> -->
> 进度: [3/5 识别中 | 完成]

## Panel A — <图类型: 散点/WB/HE/荧光/CLSM/流式/拍照…>
- **分组**: <组1, 组2, …>
- **坐标/量纲**: <Y轴指标(单位); 线性/log>
- **组间比较**: <组1 vs 组2 = ***>   <!-- source: star_on_graph -->
- **❓待确认**: 误差棒类型? n=? 星号阈值?
- **结果(Results)**: <客观描述方向与比较结果，不解释>
- **讨论(Discussion)**: <基于设计/假设/本图数据的推理> <!-- [CITE_PENDING: 机制关键词] -->

## Panel B — …
```

## `figures_database.json` 条目示例（收口 `add-figure` 用；传**单个** figure 对象，命令按 `figure_id` 自动安全合并）

```json
{
  "figure_id": "Figure 2",
  "section": "results_3.2",
  "title": "Cytotoxicity of nanoparticles",
  "data_status": "ready",
  "panels": [
    {"panel": "A", "assay": "CCK-8",
     "groups": ["Control", "NP-L", "NP-H"],
     "comparisons": [{"pair": ["NP-H", "Control"], "sig": "***", "p": null, "source": "star_on_graph"}],
     "error_bar": "SD", "stat_test": "one-way ANOVA + Tukey", "n": 3}
  ]
}
```

（`data_status`：核心定量齐全=`ready`，缺核心项=`pending`；`section` 值必须 = storyline 的 section_id，代码里 `section`/`section_id` 混用，统一写 `section`。）

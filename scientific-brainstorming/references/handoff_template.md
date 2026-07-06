# Brainstorm Handoff Template（脑暴收尾结构化产物）

会话收敛时按此模板产出一份**结构化交接文件**，供下游写作技能直接读取，避免"手抄丢失假设严谨性"。

## 铁律
- 这是**探索性产出**，不是结论。假设是待验证的猜想，Research Gap 未经系统检索确认（brainstorming 不检索文献）——文件顶部必须标注这一状态，防下游误当定论。
- **不要编造**未在对话中出现的内容。用户没谈到的字段留空并标 `（未讨论）`，不脑补。
- 假设部分**必须**带"自变量 / 因变量 / 预期效应方向 / 证伪条件"四要素——这正是手抄最易丢、方法学最要紧的部分；对话里没明确的，标 `（待明确）` 提示用户后续补。

## 结构化字段（三种格式共用同一份内容）

```
状态：探索性脑暴产出 · 假设待验证 · Gap 未经系统检索确认
主题 (Topic)：
研究问题 (Research Questions)：
  RQ1 …
假设 (Hypotheses)：
  H1 陈述：…
     自变量：…  因变量：…  预期效应方向：…  证伪条件：…
研究缺口 (Research Gap)：…（待 review-writing / gsw 系统检索验证）
方法方向 (Method Directions)：…
下一步 (Next Steps)：…（文献检索 / 预实验 / 合作等）
待解问题 (Open Questions)：…
```

## 三种交付格式（AI 直接生成对应文本，无需脚本）

- **md（默认）**：上面的结构化字段直接写成 Markdown 章节，存 `brainstorm_handoff.md`。
- **html**：同结构渲染为单文件 HTML（简洁排版、可离线打开），存 `brainstorm_handoff.html`。
- **mermaid**：思维导图形式，中心节点=主题，一级分支=研究问题 / 假设 / Gap / 方法方向 / 下一步，假设分支下挂四要素。用 ```mermaid mindmap``` 代码块，存 `brainstorm_handoff.mmd` 或嵌入 md。

## 下游接口（怎么被写作技能吃）
- **general-sci-writing `/preview`**：读"研究问题 + 假设四要素"作为 storyline 起点。
- **review-writing outline**：读"研究缺口 + 方法方向"作为综述框架线索。
- 传给下游时提醒：假设四要素与证伪条件需在真实数据/文献上重新验证，不可直接当已证结论。

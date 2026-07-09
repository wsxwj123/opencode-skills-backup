# Decision Rules

## A. 选择回复基调
- 审稿意见正确且有证据支持：`Accept and revise`
- 意见部分成立：`Partially accept with bounded revision`
- 意见与研究边界冲突：`Respectfully disagree with evidence`
- 审稿建议超出当前工作范围但有价值：`Alternative improvement`

## B. 英文高频句式
> **与去 AI 禁词表的口径（务必一致）**：下列致谢/缓冲句是**允许**的外交缓冲，不属于被禁的"空致谢"。禁的是副词叠加的浮夸致谢（"we greatly/sincerely/deeply appreciate"）、"this is an excellent suggestion"、以及 ≥3 条回复用同一句开头。缓冲句只用**一句**，其后必须紧跟实质回应；Push back / Partial 基调尤其可用一句缓冲软化否定。`risk_check.py` 的 `ai_appreciation` 正则已按此放行无副词的单句致谢。

- Appreciation（每条至多一句，其后紧跟实质回应）:
  - "We thank the reviewer for this valuable comment."
  - "We appreciate this suggestion and have revised the manuscript accordingly."

- Accept and revise:
  - "We agree with the reviewer and have clarified this point in the revised manuscript."
  - "To address this concern, we have added ... in Section X."

- Partial acceptance:
  - "We agree in principle; however, within the scope of the current study, ..."
  - "Accordingly, we have revised the text to better delimit this boundary."

- Respectful disagreement:
  - "We respectfully note that ..."
  - "Based on the current data, this interpretation is supported by ..."

- Scope limitation without overpromise:
  - "This is an important point. While additional experiments are beyond the scope of the present study, we have ..."

## C. 风险红线
- 禁止虚构：新增实验、未报告统计结果、不存在的图表与引用。
- 禁止攻击性表达：avoid "the reviewer is wrong" 等对抗句式。
- 禁止空泛承诺：avoid "we will definitely prove" without evidence.

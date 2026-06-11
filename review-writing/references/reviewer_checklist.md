# Reviewer Simulator Checklist

Checklist-anchored evaluation per reviewer-simulator skill methodology.
For each dimension, answer every checklist item (Y/N). Dimension passes when ALL items = Y.

## D1 — Novelty & Contribution

- [ ] Proposes at least one new framework, hypothesis, taxonomy, or perspective not in prior reviews
- [ ] Clearly states how this section advances beyond existing reviews (explicit "gap → contribution" sentence)
- [ ] Does NOT merely summarize existing work without synthesis

## D2 — Arbitration & Critical Analysis

- [ ] Identifies ≥1 contradiction or debate between cited studies
- [ ] Provides *why* analysis for each contradiction (not just "results conflict")
- [ ] Takes a position or proposes a reconciling explanation (does not sit on the fence)

## D3 — Evidence Density & Traceability

- [ ] Every factual claim has ≥1 citation; key claims have ≥2 independent sources
- [ ] No citation-free paragraphs (except transition/framing sentences)
- [ ] Evidence types match claim types (original article for mechanism, clinical trial for efficacy, review for background context)

## D4 — Flow & Coherence

- [ ] Opening sentence of each paragraph connects to the previous paragraph's conclusion (causal/contrastive link, not bolted-on transition)
- [ ] Section has a clear internal arc: setup → evidence → synthesis → implication
- [ ] No orphan paragraphs (paragraphs that could be moved elsewhere without breaking logic)

## D5 — Anti-AI Compliance

- [ ] Zero banned words/phrases from Anti-AI Writing Style lists
- [ ] Sentence length rhythm: no 3+ consecutive sentences within ±5 words of each other
- [ ] Passive voice ≤30% of sentences per paragraph (EN mode)
- [ ] No templated transitions ("Furthermore", "In addition", "Moreover" as sentence openers)

## Gate Rule

Any dimension with ≥1 failed item → internal revision targeting that item (max 2 rounds).
After 2 rounds, if any item still fails → **HALT**, output the specific failed checklist items as structured feedback:

```
【问题】(failed item description)
证据锚点: (paragraph/sentence where the failure occurs)
根源分析: (why it fails — e.g., "Paragraph 3 lists 4 studies without comparing their findings")
修复方向: (specific action — e.g., "Add a synthesis sentence after the 4th citation contrasting dosage findings")
```

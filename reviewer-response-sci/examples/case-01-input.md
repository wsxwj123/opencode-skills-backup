# Case 01 Input (Single Comment)

Use this as the direct input package for one run of `reviewer-response-sci`.

## review_comment
There is a serious discrepancy in the cell viability data presented for quercetin (Que) treatment in Figure 4B and Figure S3D. The data points and bar graphs clearly indicated that the cell viability in the "TAC + Que" group is lower than in the "TAC" group alone. This is directly opposite to the stated conclusion in the text, which claimed that Que exhibited a protective effect. This inconsistency is observed in both the main figure and the supplementary figure, suggesting it is not an isolated error. If the data is correct as plotted, it would imply that quercetin exacerbates TAC-induced cell death rather than alleviating it, which would fundamentally contradict the core narrative of the paper regarding quercetin's efficacy. The authors must urgently clarify this discrepancy.

## manuscript_excerpt
As described above, a dual-targeting drug delivery strategy was required regarding the contradiction of Prdx1 functions in SAP, which meant to promote intracellular Prdx1 expression and neutralize extracellular Prdx1. Through literature review and pharmacological screening, we identified quercetin (Que)—a natural flavonoid—as a potent regulator of intracellular Prdx1, exhibiting robust antioxidant and anti-inflammatory properties. As shown in Figure 4A, Que exhibited a protective effect on MPC-38 cells exposed to taurocholate acid (TAC). Interestingly, the efficacy of Que nearly disappeared in Prdx1-knockdown cells (Figure 4B), which indicated the Prdx1-dependent manner of Que efficacy. And flow cytometry and BODIPY 581/591 staining were performed to further verified that the lack of Prdx1 could significantly weaken the effects of Que (Figure 4C-D). Further, after Que intervention, the expression level of Prdx1 was investigated in MPC-38 cells. The results revealed that no significant differences were observed in RNA or protein level of Prdx1 (Figure S3A and S3B), though the concentration of Que rised. Meanwhile, the expression of potential regulatory factors of Prdx1 such as HIF-1α, NRF2 and SP1 did not change evidently (Figure S3C). All evidence proved Que may act through regulating post-translation modification level of Prdx1 rather than its expression.

However, the low solubility and bioavailability of Que limited its applications. Given substantial evidence that extracellular vesicles (EVs) enhance the loading efficiency and cellular internalization of poorly soluble drugs, we subsequently isolated EVs derived from HEK-293T cells and loaded them with Que (detailed nanoscale characterization provided below). Co-IP results demonstrated that EV-Que significantly enhanced Prdx1 acetylation compared to free Que (Figure 4G). More importantly, these treatments did not affect the total expression level of Prdx1 protein. And cell viability of MPC-38 cells pre-treated by TAC significantly increased under EV@Que protection when compared to that of single Que (Figure S3D). We speculated this may be attributed to the ability of EVs to promote the intracellular uptake of Que.

## study_facts
- Reviewer observed inconsistency between plotted values and textual claim around Figure 4B and Figure S3D.
- The manuscript excerpt currently claims a protective effect of Que and stronger protection by EV@Que.
- Claim scope to protect: interpretation about Que efficacy under TAC injury and Prdx1 dependence.
- Any statement about repeated experiments, corrected plotting, or new assays must only be included if verified by authors.

## editor_note (optional)
Journal of Controlled Release revision context; keep tone constructive, factual, and concise.

## Output reminder
- Part 1: bilingual reviewer comment (txt code block)
- Part 2: formal English response (txt code block)
- Part 3: revised manuscript excerpt clean version (txt code block)
- Part 4: Chinese modification notes with 🔴 and 🟡

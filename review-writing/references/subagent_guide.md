# Subagent Delegation Guide

Delegate mechanical tasks to subagent; main agent focuses on synthesis and writing.

**Model:** Read `subagent_model` from `outline.md`. If unspecified, use same model as current session.

## Delegatable Tasks

| Task | Input → Output |
|------|---------------|
| Batch literature search | Search strategy → `tmp/papers_X_X.json` (section-specific) |
| Metadata extraction + Zotero write | papers.json → Zotero entries |
| Anti-AI compliance scan | Draft text → violation report |
| BibTeX formatting | literature data → refs.bib |
| Word count + citation validation | Draft → stats report |

## NOT Delegatable

Outline design, synthesis writing, Reviewer Simulator decisions, user interaction, HALT decisions.

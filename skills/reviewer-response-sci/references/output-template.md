# Output Template (One-Shot Hierarchical HTML)

Produce **one single HTML file**.

## Required hierarchy
- TOC Level 1: `回复审稿人的邮件`
- TOC Level 1: `Reviewer #1`, `Reviewer #2`, ...
- TOC Level 2 (inside reviewer): `Major`, `Minor`
- TOC Level 3 (inside section): `Comment 1`, `Comment 2`, ...

## Required page schema for each leaf comment
1. 审稿人意图理解
   - 先展示该条 reviewer 原始意见（English）
   - 再展示“应如何理解”中英对照（上下排列）
2. Response to Reviewer（中英对照）
   - English box + 中文 box（上下排列）
   - 两个 box 都必须有复制按钮
3. 可能需要修改的正文/附件内容（中英对照）
   - English box + 中文 box（上下排列）
   - 若不需要修改，写 `无`
   - 两个 box 都必须有复制按钮
4. 修改说明（中文，含 🔴 / 🟡）
5. Evidence Attachments (Text + Image + Table)

## Interaction requirements
- Click TOC item to show one corresponding page.
- Keep only one content page visible at a time.
- Responsive layout for desktop and mobile.

## Missing data behavior
- If no image/table data available, keep module and fill `Not provided by user`.
- If revised excerpt is not confidently extractable, keep explicit placeholder and do not fabricate.

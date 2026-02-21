# Sci2Doc 使用说明

## 目标与边界

- 正文目标：不少于 80,000 中文字符
- 各章字数：不硬编码，必须按项目材料与用户协商确定
- 中文摘要：1500-2500 字
- 结构：独立绪论章 + 多个研究章 + 独立总结章（总章节数 >= 5）
- 参考文献：全书末尾统一
- 综述：用户另行撰写，不纳入本技能正文考核

## 核心脚本

- `scripts/state_manager.py`
  - 防失忆、防爆 token、写作门禁、快照/回滚
- `scripts/atomic_md_workflow.py`
  - 原子化小节 markdown、编号校验、章节/全文合并、自检、节级快照
- `scripts/count_words_docx.py`
  - 字数统计（读取 `thesis_profile.json`）
- `scripts/check_quality.py`
  - 质量检查（读取 `thesis_profile.json`）
- `scripts/merge_chapters.py`
  - docx 合并（可高保真）

## 统一配置

所有目标参数以 `thesis_profile.json` 为准（`init` 自动生成）。

查看配置：

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile --show
```

更新配置：

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile \
  --body-target 80000 --abstract-min 1500 --abstract-max 2500 \
  --references-min 80 --min-chapters 5 \
  --chapter-target 1:12000 --chapter-target 2:17000 --chapter-target 3:17000
```

## 端到端流程

### 1. 初始化

```bash
python3 scripts/state_manager.py --project-root "${save_path}" init \
  --title "论文中文题目" --author "作者姓名" --major "学科"
```

### 2. 写前门禁

```bash
python3 scripts/state_manager.py --project-root "${save_path}" \
  write-cycle --chapter 2 --token-budget 6000 --tail-lines 80 --json-summary
```

### 3. 原子化写作

在 `${save_path}/atomic_md/第2章/` 下维护小节文件：
- `2.1_引言.md`
- `2.2_实验A_材料方法.md`
- `2.3_实验A_结果讨论.md`

编号校验：

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" validate --chapter 2
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  validate --chapter 2 --enforce-research-structure
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" validate-experiment-map --chapter 2
```

实验映射标记约定：`[实验] EXP-2-1`、`[对应实验] EXP-2-1`、`[图] 图2-1` / `[表] 表2-1`。

### 4. 小结即快照

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  section-snapshot --chapter 2 --section 2.3
```

### 5. 章节合并与自检

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" merge --chapter 2 --to-docx
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  self-check --docx "${save_path}/02_分章节文档/第2章_自动合并.docx"
```

说明：
- 若已配置 `chapter_targets`，章节自检优先使用该章节目标字数。
- 章节自检不强制“全文参考文献下限”；参考文献下限在全文总检时执行。

### 6. 章节收口

```bash
python3 scripts/state_manager.py --project-root "${save_path}" \
  write-cycle --chapter 2 --finalize --summary "第2章完成并自检通过" --snapshot
```

### 7. 全文合并

优先 md 全文合并：

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" merge-full --to-docx
```

可选 docx 高保真合并：

```bash
python3 scripts/merge_chapters.py \
  --input-dir "${save_path}/02_分章节文档" \
  --output "${save_path}/03_合并文档/完整博士论文.docx" \
  --require-high-fidelity
```

### 8. 全文总检

```bash
python3 scripts/state_manager.py --project-root "${save_path}" word-count
python3 scripts/check_quality.py "${save_path}/03_合并文档/完整博士论文.docx" \
  --output json --enforce-full-structure
```

全文门禁包含：
- 章节数不少于 `thesis_profile.targets.min_chapters`（默认 5）
- 第一章应为绪论/引言
- 最后一章应为总结/结论/展望类章节
- 参考文献位置校验：仅一个参考文献章节，且其后不再出现“第X章”正文标题

## 研究章节写作规范

第2章到第N-1章统一结构：

1. 引言
2. 材料与方法
3. 结果与讨论
4. 实验结论
5. 小结

强制规则：
- 结果与讨论必须和方法实验一一对应
- 一个实验至少对应一个独立图或表
- 禁止“先堆全部结果，后统一讨论”的 SCI 论文式结构

## 反机械化写作要求

章节提交前必须做一次 `humanizer-zh` 风格校正：
- 减少模板化连接词堆叠
- 去掉空泛拔高表达
- 证据先行、结论后置
- 降低段落机械重复

## 回滚

普通回滚：

```bash
python3 scripts/state_manager.py --project-root "${save_path}" rollback --target snapshot
```

严格镜像回滚：

```bash
python3 scripts/state_manager.py --project-root "${save_path}" rollback --target snapshot --strict-mirror
```

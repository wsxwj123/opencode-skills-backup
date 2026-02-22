# Sci2Doc Quick Start

> 用最短流程完成：初始化 -> 原子化写作 -> 章节自检 -> 全文合并

## 1. 安装依赖

```bash
pip3 install python-docx
pip3 install docxcompose
```

说明：第二行用于高保真 docx 合并，可选。

## 2. 初始化项目

```bash
python3 scripts/state_manager.py --project-root "${save_path}" init \
  --title "论文题目" --author "作者" --major "专业"
```

## 3. 确认并设置目标配置

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile --show
python3 scripts/state_manager.py --project-root "${save_path}" profile \
  --body-target 80000 --abstract-min 1500 --abstract-max 2500 \
  --references-min 80 --min-chapters 5 \
  --chapter-target 1:12000 --chapter-target 2:17000
```

## 4. 写前门禁

```bash
python3 scripts/state_manager.py --project-root "${save_path}" \
  write-cycle --chapter 2 --token-budget 6000 --tail-lines 80 --json-summary
```

## 5. 原子化小节

目录约定：`${save_path}/atomic_md/第2章/`

命名约定：`2.1_引言.md`、`2.2_实验A_材料方法.md` ...

校验编号：

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" validate --chapter 2
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  validate --chapter 2 --enforce-research-structure
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" validate-experiment-map --chapter 2
```

## 6. 小结完成即快照

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  section-snapshot --chapter 2 --section 2.3
```

## 7. 合并章节并自检

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" merge --chapter 2 --to-docx
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  self-check --docx "${save_path}/02_分章节文档/第2章_自动合并.docx"
```

提示：
- 配置了 `chapter_targets` 时，章节自检按章节目标判断。
- 参考文献下限在全文总检阶段检查，不在章节自检阶段卡住。

## 8. 章节收口

```bash
python3 scripts/state_manager.py --project-root "${save_path}" \
  write-cycle --chapter 2 --finalize --summary "第2章完成并通过自检" --snapshot
```

## 9. 合并全文

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" merge-full --to-docx
```

## 10. 全文总检

```bash
python3 scripts/state_manager.py --project-root "${save_path}" word-count
python3 scripts/check_quality.py "${save_path}/03_合并文档/完整博士论文.docx" \
  --output json --enforce-full-structure
```

## 硬规则提醒

- 正文 >= 80,000 中文字
- 各章字数必须先和用户协商后写入 profile
- 中文摘要 1500-2500
- 参考文献统一放全书末尾
- 综述由用户另写，不纳入本技能正文考核
- 研究章结构固定：引言/材料与方法/结果与讨论/实验结论/小结
- 一个实验至少一个独立图或表

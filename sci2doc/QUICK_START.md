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

## 3.1 样式二选一

- `默认设置`：直接使用内置中南大学博士论文格式。
- `自定义样式`：必须先写入院校、页边距、页眉页脚距离，以及详细文字规范或模板证据。

如果自定义信息不完整，项目状态会自动保持为 `pending_template`，允许继续整理 markdown，但禁止导出 `.docx` 和格式验收。

## 3.2 结构化 JSON 更新

推荐把明确的格式要求写进 `format_profile_json`，把封面/摘要等信息写进 `project_info_json`。

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile \
  --format-profile-json '{
    "page_margins_cm": {"top": 2.8, "bottom": 2.6, "left": 3.0, "right": 3.1},
    "header_distance_cm": 1.2,
    "footer_distance_cm": 1.6,
    "page_numbering": {
      "front_matter": {"format": "upperRoman", "start": 1},
      "body": {"format": "decimal", "start": 1},
      "back_matter": {"format": "decimal", "start": null}
    },
    "style_profile": {
      "body": {"font_east_asia": "SimSun", "font_size_pt": 12, "line_spacing_pt": 20},
      "heading1": {"font_east_asia": "SimHei", "font_size_pt": 16}
    }
  }' \
  --project-info-json '{
    "classification": "R73",
    "udc": "616-006",
    "abstract_zh": "这里写中文摘要",
    "keywords_zh": ["肿瘤学", "人工智能"],
    "abstract_en": "Write English abstract here",
    "keywords_en": ["oncology", "artificial intelligence"]
  }'
```

限制：
- `--format-profile-json` 和 `--project-info-json` 只接受 JSON object。
- 未知字段、错误类型、非法页码格式都会被脚本直接拒绝。
- 支持的页码格式：`decimal`、`lowerRoman`、`upperRoman`、`lowerLetter`、`upperLetter`。

## 3.3 只有文字要求时怎么映射

如果用户不给 `.docx/.dotx` 模板，只给规则文本，优先映射到这些字段：

- “正文宋体小四，固定值 20 磅，两端对齐，首行缩进 2 字符” -> `style_profile.body`
- “一级标题黑体三号居中，段前 18 磅，段后 12 磅” -> `style_profile.heading1`
- “中文摘要标题黑体三号，摘要正文宋体四号 1.5 倍行距” -> `style_profile.front_matter.zh_abstract`
- “目录前置页用大写罗马数字，正文从 1 开始” -> `page_numbering`
- “页边距上 2.8 下 2.6 左 3.0 右 3.1，页眉 1.2，页脚 1.6” -> `page_margins_cm` + `header_distance_cm` + `footer_distance_cm`

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
  self-check --target "${save_path}/02_分章节文档/第2章_自动合并.docx"
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
# 字数统计（支持 .md / atomic_md 目录，自动检测路径类型）
python3 scripts/state_manager.py --project-root "${save_path}" word-count
# 或直接指定路径：
python3 scripts/count_words.py "${save_path}/atomic_md"

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
- 表格使用三线表（管道表语法自动转换）
- 缩略语首次出现写全称，后续仅用缩略语
- 引用格式：英文方括号 + 英文逗号，编号升序
- 禁止破折号、问句、比喻、主观夸大、排比句式

## 新增检查项速查

| 检查项 | 类别 | 级别 | 说明 |
|--------|------|------|------|
| 三线表边框 | 三线表 | error/warning | 顶底 1.5pt、表头分隔 0.5pt、无竖线 |
| 引用格式 | 引用格式 | error | 中文逗号/括号、缺逗号、逆序范围 |
| 引用排序 | 引用格式 | warning | 编号未升序 |
| 破折号 | 标点规范 | error | 正文中使用了—— |
| 问句 | 陈述规范 | warning | 正文出现？ |
| 比喻 | 修辞规范 | error | 犹如/如同/...的桥梁等 |
| 主观夸大 | 客观性 | warning | 令人震惊/远超预期等 |
| 过度书面化 | 语言通俗性 | warning | 有鉴于此/毋庸置疑等 |
| 排比句式 | 修辞规范 | warning | 连续3句相同前缀 |
| 缩略语一致性 | 缩略语 | error/warning | 首次未展开/冗余展开 |

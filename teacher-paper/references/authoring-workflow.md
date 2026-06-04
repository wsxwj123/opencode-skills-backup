# 试卷撰写流程（原子化工作流）

> 解决"资料多时上下文易丢、改某题要重读全卷"的问题。
> 原子化思想：**每个部分单独成文件，最后合并**。
> 全程用 `assemble.py` 脚手架与合并，`make_paper.py` 出 Word。
>
> 注：下文命令里的 `scripts/` 指 `<SKILL_DIR>/scripts/`（`<SKILL_DIR>` 为本 skill 实际目录，由 `setup.py` 自动解析，不要写死）。为简洁本文用相对写法，实际运行请补全为绝对路径。

## 工程目录结构

每份试卷是一个独立工程文件夹（建在用户工作目录，不污染 skill）：

```
<试卷名>_工程/
├── meta.json              # 试卷元信息（年级/类型/总分/时长/标题/注意事项）
├── 00_manifest.md         # 进度索引：每题考点·分值·难度·状态（防上下文丢失）
├── materials/             # 抓取/上传/识图的原始素材（备查、可溯源）
│   │                      # 命名：<板块>_<来源>-<简述>.md，文件首两行写 来源/抓取日期
│   ├── 非连_中新网-种子库.md
│   ├── 文言_古诗文网-世说新语德行.md
│   ├── 现代文_意林-补碗.md
│   ├── 截图_用户-真题第3页.md   # 用户截图经 多模态识别 或 ocr_image.py 转成的文字
│   └── 作文素材_作文周刊-成长.md
├── items/                 # 原子化内容，每个文件一段，按文件名前缀数字排序
│   ├── 100_sec_积累运用.json   # 大题分隔（init 自动生成，下同）
│   ├── 110_sub_积累.json
│   ├── 111_q01_字音字形.json
│   ├── 112_q02_默写.json
│   ├── 120_sub_运用.json
│   ├── 121_q03_病句.json … 124_q06_拟标题.json
│   ├── 200_sec_阅读.json
│   ├── 210_sub_非连.json
│   ├── 211_mat_非连材料.json   # 多题共享的阅读材料，单独成文件
│   ├── 212_q07.json 213_q08.json 214_q09.json
│   ├── 220_sub_小说.json  221_mat_小说.json  222_q10.json…224_q12.json
│   ├── 230_sub_古诗文.json 231_mat_诗.json 232_q13.json 233_q14.json
│   ├── 234_mat_文言.json 235_q15.json 236_q16.json 237_q17.json 238_q18.json
│   ├── 240_sub_名著.json  241_mat_名著.json  242_q19.json 243_q20.json
│   └── 300_sec_写作.json  301_q21_作文.json
└── build/                 # 合并产物
    ├── content.json
    ├── 试卷.docx
    └── 参考答案及解析.docx
```

**原子文件命名**：`NNN_类型_描述.json`，`NNN` 为**3位数字序号**（与 init 生成的分隔文件 100/110/120/200… 对齐），控制全卷顺序（section/sub/material/question 混排）。assemble.py 按前缀数字**自然排序**，混用不同位数也能正确排序，但统一 3 位最清晰。section/sub/material 只有 `paper`，题目文件有 `paper`+`answer`。

## 原子题文件格式（items/*.json）

```json
{
  "meta": {
    "num": "7", "score": 2, "difficulty": 0.7,
    "type": "非连续性文本-信息理解选择题",
    "knowledge_point": "信息筛选与细节判断",
    "intent": "考查比对多则材料、识别偷换概念",
    "source": "节选自《科学之友》2024年第6期",
    "status": "已出"
  },
  "paper":  [ {"type":"question","num":"7","score":"（2分）","text":"..."},
             {"type":"options","items":["A. ...","B. ...","C. ...","D. ..."]} ],
  "answer": [ {"type":"answer","num":"7","score":"（2分）","text":"C"},
             {"type":"analysis","text":"【解析】A项偷换'同一条件'为'不同条件'……"} ]
}
```
- `paper`/`answer` 的 block 类型见 `scripts/make_paper.py` 顶部文档。
- section 文件示例：`{"meta":{"status":"-"},"paper":[{"type":"section","text":"二、阅读（共50分）"}],"answer":[{"type":"section","text":"二、阅读（共50分）"}]}`
- 共享材料文件：`paper` 放 `material`/`table` 块，`answer` 留空 `[]`。

### 选文 material 块的标题/出处/排版（对标真题，build 有完整性门禁）

阅读题的选文**必须随卷给全文**（缺则 build 拒绝出卷）。material 块按文体写：

```json
// 非连续性文本：多则材料 + 出处右对齐（出处必标）
{"type":"material","label":"【材料一】","title":"天气预报中的统计与概率",
 "paras":["……正文（楷体首行缩进）……"],"source":"（节选自《科学之友》2024年第6期）"}

// 小说/散文：标题+作者+正文（1000-1500字）+出处
{"type":"material","title":"老街","author":"佚名",
 "paras":["①……","②……"],"source":"（选自《读者》2024年第6期）"}

// 古诗词：layout=verse → 标题/作者/诗句整体居中（不要合并成一段）
{"type":"material","title":"柳梢青·春感","author":"〔宋〕刘辰翁","layout":"verse",
 "paras":["铁马蒙毡，银花洒泪，春入愁城。","那堪独坐青灯，想故国高台月明。"],
 "source":"（选自《须溪词》）"}
```

- 选文正文默认**楷体**、首行缩进2字；`title`/`author` 楷体居中；`source` 宋体右对齐（脚本自动，无需手设字体对齐）。
- **小说选文净字数 1000-1500**，越界 build 告警。
- 引号会自动规范（`'我的母亲'`→`“我的母亲”`），但应优先正确书写。

### 🔴 阅读类素材的溯源字段（硬门禁，必填）

凡 `paper` 里含**带正文的 material 块**（非连/小说/散文/古诗词/文言/名著的选文），该文件 meta **必须**有：

```json
"meta": {
  "status": "-",
  "source": "中国新闻网 2026-05-20《XXX》 https://www.chinanews.com.cn/...",  // 真实来源URL/出处；教师原创须写 "原创-已声明"
  "source_file": "非连_新闻-种子库.md"   // materials/ 下真实存在的抓取原文文件名（原创可省）
}
```

`assemble.py build` 校验（v3.11.0+）多道门禁，任一不过即 exit 2：
- 缺 `source` / 非原创缺 `source_file` / source_file 指向不存在 → 拒
- source 是 URL 但 materials 原文无 `fetch_web.py --save` 凭证头（或凭证 URL/字节数与 meta 不符）→ 拒
- meta 标"原创"+卷面 material 出处写"节选自《…》" → 拒（自相矛盾）
- 古诗词标"原创" → 拒（须真作）
- items/ 无任何 num+score 题目 → 拒（避免空白卷）

正确流程：先 `fetch_web.py "<URL>" --save 工程/materials/非连_新闻-种子库.md`（自动写凭证），再据真实原文命题、回填 source/source_file。
逃逸口（仅在用户明确知情时加）：`--allow-unsourced` 跳门禁、`--allow-empty` 允许空卷、`--accept-fallback` 允许兜底、`--listening-mode` 处理英语听力。**AI 不得自行加任一。**

## 端到端八步

### 1. 建工程
```bash
python3 scripts/assemble.py init "九年级中考模拟语文_工程" \
  --stage 九年级 --type 中考模拟 --title "九年级语文（中考模拟）试卷"
```
生成目录骨架、`meta.json`、`00_manifest.md`、`items/` 内的 section/sub 占位文件。

> v3.x 起参数用 `--stage`（学段，如 七年级/九年级/高三），旧 `--grade` 兼容保留。
> 兜底门禁：学段+科目既无样卷又无预设时 init 会拒绝，须 AskUserQuestion 问清地区/卷型，确认后加 `--accept-fallback` 重跑；
> 英语含听力时 init 也会拒，须三选一后加 `--listening-mode omit|as-reading|user-audio` 重跑。

### 2. 选材（联网 + 本地）
按 `references/material-sources.md`：
- 文言文：抓古诗文网《世说新语》《古文观止》节选 → 存 `materials/文言文_*.md`
- 现代文：抓/搜《意林》《读者》风格美文 → `materials/现代文_*.md`
- 作文素材：抓《作文周刊》《意林·作文素材》或时文 → `materials/作文素材_*.md`
- 非连：抓科普+数据图表
```bash
# v3.10.0 起：网络素材必须用 --save 落盘，脚本会自动写抓取凭证头（url/字节/sha256）
python3 scripts/fetch_web.py "<url>" --save "九年级..._工程/materials/文言文_世说新语-管宁割席.md"
```
> **凭证机制**：build 校验素材时会读凭证头校对 URL 与字节数。**用 shell `>` 重定向落盘的素材无凭证，build 会拒**——一律走 `--save`。
> 抓不到 → 提示用户截图/给 PDF，用 `read_material.py` 读本地。**每份素材都落盘**，后续命题只读相关素材文件，上下文不膨胀。
> 扫描版 PDF（无文字层）会自动走 OCR 兜底（v3.12.0），需本机装 rapidocr-onnxruntime / paddleocr / pytesseract 任一。

### 3. 规划蓝图（写 manifest）
对照 `references/exam-templates.md` 的 21 题结构，在 `00_manifest.md` 列出每题：题号·题型·考点·分值·难度·拟用素材·状态（待出）。这是全卷"地图"。

### 4. 逐题原子化命题
一次只专注一题：读该题对应的 `materials/` 素材 → 写 `items/NN_qXX.json`（paper+answer+解析+命题意图）→ manifest 标"已出"。
- 严格遵循 `references/anti-ai-guidelines.md` 去AI感。
- 共享阅读材料先写 `items/NN_mat_*.json`，再写其下各题。

### 5. 去AI感自检
逐题对照 anti-ai 自检清单：题干是否简洁、选项是否参差、材料是否有生活质感、默写是否有情境、干扰项是否反映真实错误。不合格就改对应 json。

### 6. 合并出卷
```bash
python3 scripts/assemble.py build "九年级中考模拟语文_工程"
```
脚本：读 meta.json 生成头部 → 按文件名排序合并所有 items → 写 `build/content.json` → 调 make_paper.py 生成 `build/试卷.docx` 与 `build/参考答案及解析.docx`。
- build 时按 `meta.expected_questions` 与 `meta.total` 校验题量/分值（长沙九年级语文为 21 题/120 分/20-50-50，其它科目按其样卷或预设的 expected_questions）；缺字段或不符仅 warn 不阻断。
- 阅读类素材溯源/凭证/完整性、空卷、未知 block type 走硬门禁（见上节）。
- make_paper 渲染时未知 block type 会 stderr warn（防 stem/choice 等错写被静默丢弃）。

### 7. 审题迭代
分板块展示给用户。用户要改哪题 → **只改对应 `items/NN_qXX.json`** → 重跑 `assemble.py build`。其余题零改动、零风险。

### 8. 定稿
全部 status=定稿 → 交付 `build/` 下两个 Word 文件。

## 为什么这样设计

| 痛点 | 原子化方案 |
|------|-----------|
| 资料多→上下文塞满、AI忘前文 | 素材落盘 materials/，命题时只读当前题相关文件 |
| 改一题怕动全卷 | 一题一文件，改谁读谁，其余不动 |
| 中途中断难续 | manifest 记录每题状态，随时断点续作 |
| 分值/题量易算错 | build 自动校验 21题/120分/20-50-50 |
| 反复重排版 | 内容与排版分离，json 改完一键重生成 Word |

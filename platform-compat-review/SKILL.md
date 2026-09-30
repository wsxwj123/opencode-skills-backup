---
name: platform-compat-review
description: 跨平台兼容性审查的排查点目录,通用于任何 Node/Tauri/Electron/CLI 项目,覆盖 Windows 与 macOS(含 WebView2 / WKWebView / Chromium dev 预览 / iOS Safari 的引擎差异,以及 cmd.exe、PowerShell、codesign、quarantine、TCC 等平台机制)。只要用户提到「检查兼容性」「Windows/Mac 上报错、打不开、找不到文件、乱码、排版错」「发版前兼容审查」「cmd.exe / .cmd / npm 装的 CLI / PowerShell / 反斜杠 / CRLF / 签名 / 公证 / 隔离标记 / FDA / 软链 / 路径大小写」,或者 dev-flow 走到发布前、判官通过后需要做平台兼容审查,都要调用本技能:它告诉审查员**去哪里看、看到什么算有问题**(不给修法),先跑 scripts/scan.mjs 定位候选位置,再按 references/review-checklist.md 逐类核对,最后按模板出报告并给出真机验证清单。用户说「新问题加进去」时,按本文件末尾的追加规范写入 references/checkpoints.md。
---

# 跨平台兼容性审查(platform-compat-review)

定位:**审查员的排查清单**,与项目无关。它回答"去哪里看、看到什么算有问题、为什么会这样、历史上在哪炸过、本机验不了时怎么交给真机验"。它**不给修法**——修法由当轮的方案/开发按当时代码决定;写死在清单里的修法会过时,还会诱导审查员照抄而不去核实。

覆盖两个平台的三类差异:①操作系统机制(进程/命令行/路径/文件系统/签名/权限);②渲染引擎(dev 预览的 Chromium、Windows 的 WebView2、mac 的 WKWebView、手机的 Safari 不是同一个东西);③分发链路(安装器、包管理镜像、代理、更新)。

| 文件 | 用途 | 什么时候读 |
|---|---|---|
| `references/checkpoints.md` | 排查点目录,每条五段:排查 / 判据 / 机制 / 事故 / 真机;条目带 [Win] [Mac] [Both] 标签 | 扫描命中某条 ID 时读对应条;写报告引用 ID |
| `references/review-checklist.md` | 逐类核对清单(要回答的问题)+ 报告模板 + 真机验证单模板 | 每次审查照着过一遍 |
| `scripts/scan.mjs` | 静态扫描,把 diff/全树里疑似命中排查点的行列出来(只定位,不定罪;`--platform win|mac|all`) | 审查第一步就跑 |
| `scripts/crt-roundtrip.mjs` | Windows cmd.exe + CRT 命令行引号往返模拟器:对真源码的引号函数跑 15 条用例 | 改动了任何"经 cmd.exe 起进程"的拼接逻辑时必跑 |

## 审查流程(五步,顺序固定)

1. **定范围**。有 tag/基线就用 `git diff <base>..HEAD --name-only`,排除 `tests/`、`.devflow/`、`CHANGELOG.md`、生成物目录;没有基线就扫全树。报告开头写清看了哪些文件、审的是哪个平台(或两个)。
2. **跑扫描**。
   ```bash
   node ~/.claude/skills/platform-compat-review/scripts/scan.mjs --root <repo> --base <rev> --platform all
   ```
   每条命中带一个 ID。扫描只负责"指出位置",是不是问题要按 checkpoints.md 该条的**判据**逐个核实(它故意宁多勿漏)。
3. **逐类核对**。打开 `references/review-checklist.md`,按 A 进程与命令行 → B 路径与文件系统 → C 原生模块与运行时 → D 渲染引擎 → E 分发/签名/网络 → G 预警 过一遍。凡条目写着"列表",必须 grep 全仓把调用点列全、逐个标注(平台可达性 / 参数来源),报告附表——抽查两处就下结论正是历史上漏掉的方式。凡 diff 触及"经 cmd.exe 起进程"的代码,用 `scripts/crt-roundtrip.mjs` 拿真源码跑。
4. **写报告**。用 checklist 末尾的模板:裁决(可发 / 需修后发)、问题清单(致命 / 必修 / 建议,每条给 `文件:行号`、什么输入出什么错、对应 ID、需要谁按什么判据改——不替开发写代码)、已核对无问题清单(防误报,下一轮别重复报)、必须真机验证项、外部指令原文。
5. **回写排查点**。审查里发现的新坑、真机验证推翻的假设,按下面的追加规范写进 `checkpoints.md`;没有新坑也要在报告里写一句"本轮无新增排查点"。

## 为什么这样做

- **扫描 + 核对分开**:正则抓得住 `wmic`、`['/c'` 旧拼法、`window.confirm` 这类字面模式,抓不住"引号函数漏了反斜杠规则"这种语义问题;后者只能靠模拟器跑真源码或人工推演。两者都要,缺一样就会漏。
- **只给判据不给修法**:同一个排查点在不同项目、不同版本里正确做法不一样;审查员的价值是"看出来",开发的价值是"改对"。
- **报告要写"已核对无问题"**:审查代理每轮新开,不写这段下一轮会把同样的东西再报一遍。
- **真机验证单是交付物的一部分**:mac 上验不了 Windows,Windows 上验不了 mac 的签名/TCC;每条真机项都要写清怎么操作、看什么、什么算过。
- **dev 预览复现不了的 bug 不许拿 Chromium 行为推根因**:必须用"项目内能用 vs 不能用"的差分,或真机坐实。

## 追加新排查点的规范(用户说"加进去"时照此办)

在 `references/checkpoints.md` 对应类别末尾追加一条,格式固定,五段缺一不可,标题带平台标签:

```
### <类别字母>-<序号> [Win|Mac|Both] <一句话标题>
- 排查:去看哪些代码/形态(调用点、文件、正则、模板…),用项目无关的说法
- 判据:看到什么算有问题(具体形态,不是"注意平台差异")
- 机制:一句为什么(帮审查员判断边界情况)
- 事故:项目 + 版本/轮次 + 日期(证明不是臆想;别的项目的事故也收)
- 真机:本机验不了时怎么验、什么算过
```

同一根因的不同表现合并成一条;能写成正则的判据同步加进 `scripts/scan.mjs` 的 RULES(带 `plat`,hint 写"核对什么");改完跑一次 `node scripts/scan.mjs --root <repo>` 确认不误报。未踩过但有依据的推演放 G 预警,验实后搬进 A–E 给正式 ID。

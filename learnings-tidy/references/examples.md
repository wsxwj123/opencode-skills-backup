# 真实 before / after（首次压缩或不熟时读）

素材取自本机两次真实整理：
`~/.learnings/ERRORS.md.bak-20260930`（原件）↔ `~/.learnings/ERRORS.md`（压缩件），
`~/.learnings/LEARNINGS.md.bak-20260930-020558`（原件）↔ `~/.learnings/LEARNINGS.md`（压缩件）。
下面每组给「合并前 N 条要点 / 合并后形态」，方便对照手感。

---

## 组 1 · 去模板元数据（PubMed 空结果）

**前**（原件，12 行）：
```markdown
### [ERR-20260911-001] pubmed-empty-result-as-negative-evidence

**Logged**: 2026-09-11
**Priority**: high
**Status**: resolved
**Area**: research

#### Summary
用 PubMed 检索 `pBV220 AND (periplasmic OR PelB OR OmpA)` 返 0 篇，据此判断"该组合无文献前例"——结论错误。文献真实存在。
#### Error
```
esearch -db pubmed -query "pBV220 AND (periplasmic OR PelB OR OmpA)" → 0 hits
```
#### Context
- 反例 1：Wu 2024, Nat Commun 15:10503 —— pBV220 + PelB 信号肽，42°C 15 min 诱导。
- 反例 2：Chen 2022, Nat Commun 13:4468 —— pBV220 + OmpA 信号肽，45°C 30 min。
#### Metadata
- Related Files: /Users/wsxwj/Zotero default/storage/5V5ULSIV/, .../6ZA9VTIM/
```

**后**（压缩件，1 条）：
```markdown
- **PubMed 空结果 ≠ 文献不存在**：`pBV220 AND (periplasmic OR PelB OR OmpA)` 返 0 篇，
  但文献真实存在（Wu 2024 Nat Commun 15:10503、Chen 2022 Nat Commun 13:4468）……
```
删掉 5 个记账字段 + 4 个 `####` 小标题；报错命令、两篇文献的期刊卷期原样保留。

> **注（该样例的瑕疵）**：`Related Files` 里两条 Zotero 存储路径是硬事实，
> 按手法②应先搬进正文再删字段——真实那次压缩漏了它。这正是 `coverage_check` 要兜的场景：
> 缺失清单会点出 `/storage/5V5ULSIV`，让人回补。

---

## 组 2 · 同族合并 · 子代理 16k 输出上限（≥8 → 1）

**前**：原件在四个日期各写一条，合计 8 条，角度各异——
4 次实锤版（`Claude's response exceeded the 16000 output token maximum`）、
只读审查代理无 Write 必崩版、`architect-reviewer` 复发第 5 次版、
general-purpose 一次 Write 600 行版、恢复方法（SendMessage 续跑）版……
每条都带自己的硬约束数字（≤80 行 / ≤120 行 / ≤2500 字 / ≤5000 token / ≤1500 字）。

**后**：1 条（ERRORS.md 四节），把 8 条的独有硬事实全部并入：
「硬约束写法」『只读审查代理 + 让它在回话给完整报告 = 必崩』「产报告的代理也要分节写」
「判据：>20KB/600 行就必须拆」「恢复：SendMessage 续跑」。
→ 族内 **8 条硬约束数字一个没少**，只是不再按日期分 8 段。

---

## 组 3 · 同族合并 + 累计计数 · zsh 词分割 / glob（3 → 1）

**前**（原件 237-246 行，含「同族（2026-06-16 / 2026-08-11）」与「同族（2026-09-21）」两段附录）：

- 现象：`rm -f a_*.jpg a_*.png a_*.webp` 当 png 不存在 → `no matches found` 整条 abort。
- 同族①：`rg` 参数里带可能为空的 glob 也中断 → 先 `rg --files | rg '<pattern>'`。
- 同族③：`TESTS="a b c"; for f in $TESTS` 在 zsh 下不拆词。
- 同族⑤：`SRC="a/*.sh b/*"; grep -l x $SRC` 既不拆词也不展开通配，结果全 0 不报错。
- 同族⑥：目录名以 `-` 开头时 `ls "$d"*.jsonl` 被当选项，得出假结论。

**后**（ERRORS.md 三节，1 条，规则后标「累计 3+ 次」）：
```markdown
- **zsh 未加引号的变量不按空格拆词**（bash 会）：`A="--session-id $U"; cmd $A` 整段当一个参数……
  规则（累计 3+ 次）：多值用数组 `FILES=( dir/*.py(N) )` + `"${FILES[@]}"`……
```
每条同族的独有串（`rg --files`、`(N)`、`while IFS= read -r`、`${=X}`）都还在。

---

## 组 4 · 精简表述 + 去元数据（LEARNINGS 两条）

**前**（原件，各带 `**Logged** | **Priority** | **Area**` 一行 + 现象 + 规则）：

```markdown
## [LRN-20260922-001] 语音打断（barge-in）不能用写死的绝对音量阈值
**Logged**: 2026-09-22 | **Priority**: medium | **Area**: audio-ui
- 现象：bot 播放语音时"一直在听我说话"反复被打断……判定是 rms>0.06 持续 200ms 即算开口……
- 规则：打断阈值必须相对环境底噪（播放开始先校准 300-400ms，阈值=clamp(底噪×K, MIN, MAX)）……

## 2026-09-22 NovelAI 生图：两条踩出来的规则（telegram bot 发图场景）
- `mode=revise` + `--reuse-seed` 只能做微调（换表情、换角度、换光线）。姿势或服装的大改必须走 `mode=new`……
- 单个局部特征别给 1.8+ 的高权重……降到 ~1.2 并补 `natural even skin tone`……
- 发 NSFW 续图前先 Read 一眼生成的图再发……
```

**后**（压缩件，各 1 行）：

```markdown
- **语音打断（barge-in）不能用写死的绝对音量阈值**：判定必须相对环境底噪（播放开始先校准 300-400ms，
  阈值=clamp(底噪×K, MIN, MAX)）……给用户灵敏度档位。
- **2026-09-22 NovelAI 生图（telegram bot 发图）**：①`mode=revise`+`--reuse-seed` 只能微调……
  ②……降到 ~1.2 并补 `natural even skin tone`；③发 NSFW 续图前先 Read 一眼……
```
删 `**Logged/Priority/Area**` 行；NovelAI 三条要点并成 1 行，`300-400ms` / `1.2` / `--reuse-seed` 等数字与命令原样在。

---

## 组 5 · 反例：**不该合并**的更正链（NovelAI 认证失败 ×3）

原件里三条约互相推翻：

1. 「认证失败 = 令牌过期」→「重试就好，是间歇性网络失败」→「重试成功是因为用户中途换了令牌」。

三条是**证据演化**，不是同族冗余。合并成一条会把「曾被误判」的教训压掉，读者拿到一个
被后续更正推翻的结论。**正确处理**：只留最后正确那条（「大概率是令牌过期，重试 1-2 次无效就换令牌」），
正文补一句「曾误判为间歇性网络失败——忽略了第三方可能中途改环境」，前两条的措辞不并进来。

> 判断口诀：**同族合并的是「同一个坑的多份记录」；互相更正的链条是两个不同的坑（一个是踩坑，一个是误判）。**

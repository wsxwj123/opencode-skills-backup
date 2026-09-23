# INTERFACE：idea-bomb 收敛化改造 对外接口约定

本文件是**测试设计的唯一输入**。写测试的人看不到 PLAN.md、看不到实现代码，只看这份。
凡本文件未写明的行为，实现方不得擅自发明；发现遗漏请回头补本文件，不要在代码里默认。

定稿日期：2026-09-23

---

## 0. 通用约定（所有脚本、所有子命令共同遵守）

### 0.1 脚本位置与调用形式

```
python3 /Users/wsxwj/.claude/skills/idea-bomb/scripts/ib_map.py  <子命令> [选项]
python3 /Users/wsxwj/.claude/skills/idea-bomb/scripts/ib_seed.py <子命令> [选项]
```

仅依赖 Python 3 标准库，不引入第三方包。平台仅 macOS。

### 0.2 数据文件路径与覆盖参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--map <路径>` | `~/.idea-bomb/migration_map.json` | 迁移地图。`ib_map.py` 所有子命令都支持 |
| `--session-dir <路径>` | `~/.idea-bomb/session` | 种子会话目录。`ib_seed.py` 所有子命令支持；`ib_map.py commit` 也支持（只读用） |
| `--backup-dir <路径>` | `<map 所在目录>/backups` | 脚本产生的备份存放处。`ib_map.py` 支持 |
| `--today <YYYY-MM-DD>` | 系统本地日期 | **仅供测试注入**。用于构造"同一天"的日上限场景，避免测试依赖真实时钟 |

**硬性要求**：三个路径参数必须真正生效，测试全程只操作临时目录里的副本，绝不触碰
`~/.idea-bomb/migration_map.json`。任何子命令在收到 `--map` 时不得回退到默认路径。

### 0.3 标准输出：永远是单个 JSON 对象

无论成功还是被拒，stdout 都输出**一个** JSON 对象（UTF-8，`ensure_ascii=False`，末尾一个换行）。
测试断言 stdout 的 JSON，不断言 stderr。

成功：
```json
{"ok": true, "command": "commit", "...": "..."}
```

被拒：
```json
{"ok": false, "command": "commit", "gate": "required_fields",
 "errors": [{"field": "falsification", "code": "MISSING", "msg": "缺少证伪点"}]}
```

- `ok`：布尔，必有。
- `command`：字符串，等于被调用的子命令名，必有。
- `gate`：字符串，仅 `ok=false` 时必有，取值见 0.5。
- `errors`：数组，仅 `ok=false` 时必有，**至少一个元素**。每个元素必有 `field`、`code`、`msg` 三个键。
  - `field`：出问题的字段名；与具体字段无关的错误用 `"-"`。
  - `code`：机器可读错误码，取值见 0.6。测试断言 `code`，不断言 `msg` 文本。
  - `msg`：中文人话说明，内容不做断言（允许实现方自由措辞）。

stderr 用于人类可读的提示与警告（如完整性警告），不参与任何断言。

### 0.4 退出码

| 退出码 | 含义 | 何时出现 |
|---|---|---|
| `0` | 成功 / 放行 | 操作完成，或检查通过 |
| `2` | **业务性拒绝**（闸门拦下） | 字段不合格、超上限、有积压、裁决值非法等 |
| `3` | 输入格式错误 | stdin 不是合法 JSON、必需参数缺失、参数值类型不对 |
| `4` | 数据文件异常 | map 文件不存在/无法解析、备份失败、原子写回读校验失败 |
| `1` | 未预期异常 | 兜底，正常路径不应出现 |

退出码 `2`/`3`/`4` 时 stdout 仍必须输出符合 0.3 的 JSON。

### 0.5 `gate` 字段取值

`backlog`（零积压闸）、`seed_cap`（种子数量闸）、`hypothesis_cap`（假说数量闸）、
`required_fields`（写回必填闸）、`verdict`（裁决终态闸）、`addressing`（寻址校验）、
`seed_link`（种子引用校验）、`input`（输入格式）、`storage`（存储与写入）。

### 0.6 错误码 `code` 全表

| code | 含义 |
|---|---|
| `MISSING` | 字段完全不存在 |
| `EMPTY` | 字段存在，但去掉首尾空白后为空字符串，或为 `null`，或为空列表/空字典 |
| `PLACEHOLDER` | 命中占位词表（见 0.7） |
| `TOO_SHORT` | 长度低于该字段规定的最小值 |
| `WRONG_TYPE` | 类型不符（例如 `feasibility_layers` 传了字符串） |
| `TOO_FEW` | 元素个数不足（例如 `feasibility_layers` 不足 3 层、`novelty_queries` 条目不够） |
| `NOT_ALLOWED` | 取值不在允许集合内（例如 `user_verdict` 不是三终态） |
| `CAP_EXCEEDED` | 超出日上限 |
| `BACKLOG_NOT_EMPTY` | 库中存在未裁决项 |
| `UNKNOWN_SEED` | 引用的 `seed_id` 在当天会话中不存在 |
| `SEED_ALREADY_USED` | 该 `seed_id` 当天已被展开过 |
| `INDEX_OUT_OF_RANGE` | 下标越界 |
| `PREFIX_MISMATCH` | 下标对应的 cell 的 `idea` 前缀与 `expect` 不符 |
| `ALREADY_DECIDED` | 目标 cell 已有终态裁决，未加 `--allow-overwrite` |
| `BAD_JSON` | stdin 或数据文件无法解析为 JSON |
| `IO_FAILED` | 备份失败、临时文件写失败、回读校验失败 |

### 0.7 占位词表（判定"未裁决"和"敷衍填充"的唯一依据）

对字符串 `s`，先 `s.strip()`，再做**大小写不敏感**判定。命中任一条即视为占位：

1. `strip()` 后为空字符串。
2. 完全等于下列任一：
   `-` `—` `–` `?` `？` `无` `空` `暂无` `N/A` `NA` `n/a` `null` `None` `TODO` `TBD`
3. **以**下列任一词**开头**（这一条是关键，真实数据里存在 `待定：拟作 2027 青基主线方案 A` 这类"占位词 + 补充说明"）：
   `待定` `待确认` `待柚子确认` `待议` `待补` `待填` `未定` `暂定` `搁置` `pending` `Pending` `PENDING` `tbd` `TBD` `todo` `TODO`

注意：`搁置` 在占位词表内。它是本次改造要用 `归档` 取代的旧中间态。

**反例（必须判为"不是占位"，测试要覆盖）**：
`不建议作主课题`、`已否决（2026-09-15）：套索肽+活菌组合打不过纯肽方案，不做`、
`建议立即纳入工作流`、`定位为元件，不作主课题`、`未检索到直接工作`、`未见先例`。

最后两个尤其重要：它们以"未"开头但不在占位词表里，是合法的查新结论，**不得**被判为占位。

### 0.8 长度计数口径

所有"最小长度"均按 **Python `len()`（Unicode 码位）** 计，中文 1 个字符算 1。
计数前先 `strip()`。例：`"未见先例"` 长度为 4。

### 0.9 日期口径

"当天"= 本地日历日，格式 `YYYY-MM-DD`。测试用 `--today` 注入，不依赖真实时钟。
跨午夜按两天处理，不做特殊补偿。

---

## 1. 迁移地图字段契约

### 1.1 文件整体结构（不变）

```json
{
  "version": 1,
  "note": "……",
  "cells": [ {…}, {…} ],
  "rejected_or_downgraded": [ {…} ],
  "_integrity": { "writes": 12, "last_write": "2026-09-23T21:40:11+08:00",
                  "last_cells_count": 105, "last_sha256": "……" }
}
```

- `version`、`note`、`rejected_or_downgraded` 脚本**只读不写**，原样保留。
- `_integrity` 为本次新增的顶层键，由脚本维护，见 4.3。
- 新 cell 一律 **追加到 `cells` 末尾**，不插入、不重排、不删除。

### 1.2 cell 的两种 schema

| | schema 1（存量 103 格） | schema 2（本次起新写入） |
|---|---|---|
| 判定方式 | **没有** `schema` 键，或 `schema != 2` | `schema == 2`（整数） |
| 谁写的 | 历史对话直接写入 | `ib_map.py commit` |
| 受新必填规则约束吗 | **否，永久豁免** | 是 |

**铁规**：任何子命令都不得对 schema 1 的 cell 施加新必填字段校验，也不得改写它的
既有字段（`verdict` 子命令只允许改 `user_verdict`、`restart_condition`、`archived`、
`verdict_date` 四个键）。

### 1.3 schema 2 cell 的必填字段

| 字段 | 类型 | 规则 | 违反时的 code |
|---|---|---|---|
| `idea` | str | 非占位，长度 ≥30 | MISSING / EMPTY / PLACEHOLDER / TOO_SHORT |
| `hypothesis` | dict | 必须恰好含 4 个键：`background`、`gap`、`design`、`innovation`；每个值为 str，非占位，长度 ≥30 | MISSING / WRONG_TYPE / TOO_FEW（缺键时 field 写成 `hypothesis.gap` 这种点路径） |
| `feasibility_layers` | dict | ≥3 个键；每个值为 str，非占位，长度 ≥10。**不校验键名** | MISSING / WRONG_TYPE / TOO_FEW / EMPTY / TOO_SHORT |
| `falsification` | str | 非占位，长度 ≥30 | MISSING / EMPTY / PLACEHOLDER / TOO_SHORT |
| `novelty_queries` | list[str] | 每条非占位且长度 ≥3。条目数下限见 1.4 | MISSING / WRONG_TYPE / TOO_FEW / EMPTY / TOO_SHORT |
| `closest_work` | str | 非占位，长度 ≥4 | MISSING / EMPTY / PLACEHOLDER / TOO_SHORT |
| `diff` | str | **条件必填**，见 1.5 | MISSING / EMPTY / PLACEHOLDER / TOO_SHORT |
| `novelty` | str | 仅校验非占位，**不校验取值集合** | MISSING / EMPTY / PLACEHOLDER |
| `feasibility` | str | 仅校验非占位，**不校验取值集合** | MISSING / EMPTY / PLACEHOLDER |
| `quadrant` | str | 仅校验非占位，**不校验取值集合** | MISSING / EMPTY / PLACEHOLDER |
| `platform` | str | 非占位 | MISSING / EMPTY / PLACEHOLDER |
| `disease` | str | 非占位 | MISSING / EMPTY / PLACEHOLDER |
| `method` | str | 必须 ∈ `{"transfer", "combine", "angle"}` | MISSING / NOT_ALLOWED |
| `status` | str | 必须 ∈ `{"untried", "done", "failed"}` | MISSING / NOT_ALLOWED |
| `user_verdict` | str | 必须 ∈ `{"采纳", "否决", "归档"}`，**精确相等，不做前缀匹配** | MISSING / NOT_ALLOWED |
| `restart_condition` | str | 仅当 `user_verdict == "归档"` 时必填，非占位，长度 ≥10；其余情况可缺省 | MISSING / EMPTY / PLACEHOLDER / TOO_SHORT |
| `seed_id` | str | 由 `--seed-id` 传入，不从 stdin 读 | 见 3.3 |

**为什么 `novelty`/`feasibility`/`quadrant` 不校验取值**：真实数据里它们是自由文本
（`中-高`、`中高`、`甜区（创新中-高×可行高）`、`高但无意义`）。强枚举会把用户的自然写法判成
非法。只查非空。

**为什么 `feasibility_layers` 不校验键名**：真实数据里键名有 `biology`/`机制`/`delivery_signal`/
`safety_executability`/`measure`/`caveat` 等 30 余种。只查"是 dict、≥3 个键、每个值非空且 ≥10 字"。

### 1.4 `novelty_queries` 的条目数下限（与 `method` 联动）

| `method` | 下限 | 理由 |
|---|---|---|
| `transfer` | **≥2** | 跨界迁移必须用源领域原名再搜一遍，只搜目标领域会漏掉撞车 |
| `combine` / `angle` | **≥1** | |

### 1.5 `diff` 的条件必填规则

先判断 `closest_work` 是否为「无先例声明」：`strip()` 后**包含**下列任一子串即算是——
`未检索到` `未检索` `检索未见` `未见先例` `未见直接` `无直接先例` `无先例` `未找到先例` `0命中` `无命中`

| `closest_work` 是无先例声明？ | `diff` 要求 |
|---|---|
| 是 | **可缺省、可为空、可为 `—`**，一律放行 |
| 否 | 必填，非占位，长度 ≥10 |

**这条规则的来历**：真实数据里 `未见先例`(4字)、`无直接先例`(5字)、`未检索到直接工作`(8字)
是合法查新结论，此时 `diff` 写 `—` 或 `无` 也合理；但同一批数据里也有 `closest_work` 写了
具体 PMID 却把 `diff` 留成 `None` 的敷衍条目。一刀切的长度门槛会把两者一起砍，所以拆成条件规则。

### 1.6 由脚本强制写入、忽略调用方输入的字段

下列字段即使 stdin 里提供了，也**一律被脚本的值覆盖**：

| 字段 | 脚本写入的值 |
|---|---|
| `schema` | 整数 `2` |
| `date` | 当天日期（`--today` 或系统本地日期），`YYYY-MM-DD` |
| `committed_at` | 写入时刻，ISO 8601 带时区 |
| `seed_id` | `--seed-id` 参数值 |
| `archived` | `user_verdict == "归档"` 时为 `true`，否则不写这个键 |

**可断言行为**：stdin 里传 `"date": "1999-01-01"`，写入后该 cell 的 `date` 必须是当天日期。
这条防的是靠伪造日期绕开日上限。

---

## 2. `ib_seed.py`：第一段种子登记

只读写 `<session-dir>/seeds-<YYYYMMDD>.json`，**完全不碰迁移地图**。

### 2.1 `register`

```
python3 ib_seed.py register [--session-dir P] [--today YYYY-MM-DD]
```

stdin：JSON 数组，每个元素是一个对象，必含 `text` 键（字符串）。

```json
[{"text": "把宿主免疫的昼夜相位当成工程菌治疗的隐藏变量"},
 {"text": "用菌分裂稀释当瘤内活菌计时器"}]
```

校验顺序（**遇第一类错误即整批拒绝，一条不写**）：

1. stdin 不是合法 JSON，或不是数组 → 退出码 `3`，`gate=input`，`code=BAD_JSON`。
2. 数组为空 → 退出码 `3`，`gate=input`，`code=EMPTY`，`field="-"`。
3. 任一元素不是对象、或缺 `text`、或 `text` 非字符串 → 退出码 `3`，`gate=input`，
   `code=MISSING` 或 `WRONG_TYPE`，`field="[i].text"`（i 为 0 起下标）。
4. 任一 `text` 占位或 `strip()` 后长度 <8 → 退出码 `2`，`gate=input`，
   `code=PLACEHOLDER` 或 `TOO_SHORT`，`field="[i].text"`。
5. **数量闸**：当天已登记数 + 本批数量 > 8 → 退出码 `2`，`gate=seed_cap`，
   `code=CAP_EXCEEDED`，`field="-"`；响应体额外带 `{"already": n, "incoming": m, "cap": 8}`。

成功（退出码 `0`）：
```json
{"ok": true, "command": "register", "date": "2026-09-23",
 "registered": [{"seed_id": "S1", "text": "……"}, {"seed_id": "S2", "text": "……"}],
 "total_today": 2, "cap": 8}
```

**`seed_id` 生成规则**：`"S" + 当天序号`，序号从 1 开始，按当天登记顺序单调递增，
跨批次不重置。即当天先注册 3 个得 S1-S3，再注册 2 个得 S4-S5。

**追加语义**：同一天多次 `register` 是**追加**，不是覆盖。已登记的种子不会被清掉。

### 2.2 `list`

```
python3 ib_seed.py list [--session-dir P] [--today YYYY-MM-DD]
```

无 stdin。退出码恒为 `0`，即使当天没有任何种子（此时 `seeds` 为空数组、`total_today` 为 0）。

```json
{"ok": true, "command": "list", "date": "2026-09-23",
 "seeds": [{"seed_id": "S1", "text": "……", "registered_at": "2026-09-23T10:02:33+08:00"}],
 "total_today": 1, "cap": 8}
```

### 2.3 会话文件

- 路径：`<session-dir>/seeds-<YYYYMMDD>.json`（如 `seeds-20260923.json`）。
- 目录不存在则自动创建。
- 该文件是**可丢弃的临时态**，损坏或删除不影响迁移地图。因此它的写入**不要求**备份与原子写。
- 文件内容无法解析为 JSON 时：退出码 `4`，`gate=storage`，`code=BAD_JSON`，
  **不得**静默重建覆盖（否则会悄悄清零当天配额）。

---

## 3. `ib_map.py`：迁移地图的唯一写入通道

### 3.0 全子命令共同的前置行为

1. 读 `--map` 指向的文件。文件不存在 → 退出码 `4`，`gate=storage`，`code=IO_FAILED`。
   无法解析为 JSON → 退出码 `4`，`gate=storage`，`code=BAD_JSON`。**任何情况下都不得
   重建或覆盖一个无法解析的地图文件。**
2. 完整性检查（见 4.3）：结果写进响应体的 `integrity` 字段，**不影响退出码**。

### 3.1 `status`（只读）

```
python3 ib_map.py status [--map P] [--backup-dir P]
```

无 stdin。**退出码恒为 `0`**（只报告，不判定）。

```json
{"ok": true, "command": "status",
 "total": 103, "schema1": 103, "schema2": 0,
 "decided": 16, "undecided": 87, "archived": 0,
 "undecided_items": [
   {"index": 0, "idea_prefix": "让厌氧工程菌从被动乏氧富集升级", "user_verdict": "待定", "date": "2026-07-08"}
 ],
 "integrity": {"checked": true, "external_edit_suspected": false},
 "backups": {"dir": "/Users/…/backups", "count": 3, "bytes": 556860,
             "note": "脚本不会自动删除备份，需手动清理"}}
```

- `undecided` 的判定：`user_verdict` 缺失，或其值命中 0.7 占位词表。**这是黑名单判定，
  不是白名单**——`不建议作主课题` 这类值算作已裁决。
- `idea_prefix`：该 cell `idea` 字段的**前 12 个字符**（不足 12 则全取）。
- `undecided_items` 按 `index` 升序。
- `archived`：`archived == true` 的 cell 数。

### 3.2 `gate`（只读判定，闸门 3）

```
python3 ib_map.py gate [--map P]
```

无 stdin。判定唯一一件事：未裁决数是否为 0。

| 条件 | 退出码 | 输出 |
|---|---|---|
| `undecided == 0` | `0` | `{"ok": true, "command": "gate", "undecided": 0, "total": N}` |
| `undecided > 0` | `2` | `{"ok": false, "command": "gate", "gate": "backlog", "undecided": 87, "errors": [{"field": "-", "code": "BACKLOG_NOT_EMPTY", "msg": "…"}], "undecided_items": [ … ]}` |

`undecided_items` 格式同 3.1，**最多返回 30 条**，并附 `"undecided_truncated": true`（不足 30 条时该键为 `false`）。

**边界**：空地图（`cells` 为 `[]`）→ `undecided == 0` → 退出码 `0`。

**关键约束**：`gate` **不校验任何新必填字段**，只看裁决。所以 103 个老格子在补齐裁决后
就能让 `gate` 通过，不需要回填 `hypothesis`/`falsification` 等新字段。

### 3.3 `commit`（写入新假说，闸门 1 下半 + 闸门 2 + 闸门 4）

```
python3 ib_map.py commit --seed-id S3 [--map P] [--session-dir P]
                         [--backup-dir P] [--today YYYY-MM-DD]
```

stdin：**单个** JSON 对象，即待写入的 cell（字段见 1.3）。

校验顺序（**任一步失败即拒绝，地图一个字节都不改**）：

1. stdin 非合法 JSON 或不是对象 → 退出码 `3`，`gate=input`，`code=BAD_JSON`。
2. 缺 `--seed-id` → 退出码 `3`，`gate=input`，`code=MISSING`，`field="--seed-id"`。
3. **种子引用校验**：该 `seed_id` 不在当天会话文件中（含会话文件不存在）→ 退出码 `2`，
   `gate=seed_link`，`code=UNKNOWN_SEED`。
4. **种子复用校验**：地图中已存在 `schema==2 且 date==当天 且 seed_id==该值` 的 cell →
   退出码 `2`，`gate=seed_link`，`code=SEED_ALREADY_USED`。
5. **假说数量闸**：地图中 `schema==2 且 date==当天` 的 cell 数已 **≥3** → 退出码 `2`，
   `gate=hypothesis_cap`，`code=CAP_EXCEEDED`，响应体带 `{"today_count": 3, "cap": 3}`。
6. **必填字段闸**：按 1.3/1.4/1.5 逐项校验。**收集全部错误后一次性返回**，不是遇到第一个
   就退出——否则用户要来回补七八次。退出码 `2`，`gate=required_fields`，
   `errors` 含所有不合格项。
7. **裁决终态闸**：`user_verdict` 不精确等于 采纳/否决/归档 之一 → 退出码 `2`，
   `gate=verdict`，`code=NOT_ALLOWED`。归档缺 `restart_condition` → 同样拒绝，
   `gate=verdict`，`field="restart_condition"`。
8. 全部通过 → 按 1.6 覆写受控字段 → 走 4.1 的安全写入流程 → 退出码 `0`。

成功输出：
```json
{"ok": true, "command": "commit", "index": 103, "seed_id": "S3",
 "date": "2026-09-23", "user_verdict": "采纳",
 "today_count": 1, "cap": 3,
 "backup": "/Users/…/backups/migration_map.20260923-214011.json",
 "cells_before": 103, "cells_after": 104}
```

**`commit` 不做零积压检查**。零积压是**开工前**的闸（闸门 3），不是写入时的闸。理由：
新 cell 必须自带终态裁决（第 7 步），写进去的东西天然不会造成积压。

### 3.4 `verdict`（给已有格子下裁决，闸门 4；F6 分诊用）

```
python3 ib_map.py verdict [--map P] [--backup-dir P] [--today YYYY-MM-DD] [--allow-overwrite]
```

stdin：JSON **数组**（单条也要用数组包，不支持裸对象）。

```json
[{"index": 12, "expect": "让定植菌持续分泌信号", "user_verdict": "归档",
  "restart_condition": "若能论证 VE-cadherin 连接可逆自恢复，且给出微出血定量数据"},
 {"index": 13, "expect": "把蛋白酶从降解ECM", "user_verdict": "采纳"}]
```

每条的字段：

| 字段 | 必填 | 规则 |
|---|---|---|
| `index` | 是 | 整数，`cells` 的 0 起下标 |
| `expect` | 是 | 字符串，必须是 `cells[index]["idea"]` 的**前缀**（区分大小写、不做 strip 以外的归一化）；长度 ≥6 |
| `user_verdict` | 是 | 精确 ∈ `{"采纳", "否决", "归档"}` |
| `restart_condition` | 条件 | `user_verdict == "归档"` 时必填，非占位，长度 ≥10 |

校验顺序（**全有或全无：任一条不合格则整批拒绝，一格不写**）：

1. stdin 非合法 JSON 数组 → 退出码 `3`，`gate=input`，`code=BAD_JSON`。
2. 数组为空 → 退出码 `3`，`gate=input`，`code=EMPTY`。
3. `index` 越界或非整数 → 退出码 `2`，`gate=addressing`，`code=INDEX_OUT_OF_RANGE`，
   `field="[i].index"`。
4. `expect` 缺失/过短 → 退出码 `2`，`gate=addressing`，`code=MISSING`/`TOO_SHORT`。
   `expect` 不是目标 `idea` 的前缀 → 退出码 `2`，`gate=addressing`，`code=PREFIX_MISMATCH`，
   响应体该条带 `"actual_prefix"`（目标 cell `idea` 的前 12 字）便于排错。
5. 同一批次里 `index` 重复 → 退出码 `2`，`gate=addressing`，`code=NOT_ALLOWED`，
   `field="[i].index"`。
6. `user_verdict` 非三终态 → 退出码 `2`，`gate=verdict`，`code=NOT_ALLOWED`。
   归档缺 `restart_condition` → `gate=verdict`，`field="[i].restart_condition"`。
7. **覆盖保护**：目标 cell 当前 `user_verdict` **不是**占位（即已有真实裁决），且未传
   `--allow-overwrite` → 退出码 `2`，`gate=verdict`，`code=ALREADY_DECIDED`。
   传了 `--allow-overwrite` 则放行。
8. 全部通过 → 逐条改写 → 走 4.1 安全写入 → 退出码 `0`。

**`verdict` 只允许修改目标 cell 的这四个键**，其余字段原样保留：

| 键 | 值 |
|---|---|
| `user_verdict` | 传入值 |
| `restart_condition` | 传入值（仅归档时） |
| `archived` | 归档时 `true`；采纳/否决时若该键原本存在则置 `false`，原本不存在则不新增 |
| `verdict_date` | 当天日期 |

**绝不校验新必填字段**。老格子缺 `hypothesis`/`falsification`/`feasibility_layers` 一律放行——
这是 87 格存量能被清掉的前提。

**绝不自动裁决**：脚本没有任何"AI 自动判定 user_verdict"的模式，值只能由 stdin 显式给出。

成功输出：
```json
{"ok": true, "command": "verdict", "updated": 42,
 "by_verdict": {"采纳": 3, "否决": 5, "归档": 34},
 "undecided_before": 87, "undecided_after": 45,
 "backup": "/Users/…/backups/migration_map.20260923-214530.json",
 "cells_before": 103, "cells_after": 103}
```

注意 `cells_after == cells_before`：**归档不搬家**，格子留在 `cells` 原位打标，
不移入 `rejected_or_downgraded`，下标因此永远稳定。

`rejected_or_downgraded` 数组被冻结：脚本只读、不写、不删。

---

## 4. 写入行为的可观测后果

`ib_map.py` 的 `commit` 和 `verdict` 是仅有的两个写入子命令。两者走**完全相同**的写入流程。

### 4.1 安全写入流程（顺序固定）

```
1. json.load(map)          失败 → 退出码 4 / storage / BAD_JSON，原文件不动
2. before_count = len(cells)
3. 备份：copy2(map → backup-dir/migration_map.<YYYYMMDD-HHMMSS>.json)
     backup-dir 不存在则创建
     备份失败 → 退出码 4 / storage / IO_FAILED，不进入写入
     备份后校验：备份文件字节数 == 原文件字节数，不等 → 退出码 4 / storage / IO_FAILED
4. 内存中修改
5. 写临时文件 <map>.tmp-<pid>：write → flush → os.fsync(fd) → close
6. 回读校验：json.load(tmp) 成功，且 len(cells) == 期望值
     （commit 期望 before_count+1；verdict 期望 before_count）
     不满足 → 删除临时文件 → 退出码 4 / storage / IO_FAILED，原文件仍是旧内容
7. os.replace(tmp, map)    同目录 rename，原子替换
8. 更新 _integrity（见 4.3）——与第 7 步同一次写入完成，不是第二次写文件
```

### 4.2 可断言的观测点

| 观测点 | 断言内容 |
|---|---|
| 备份文件名 | 正则 `^migration_map\.\d{8}-\d{6}\.json$`，位于 `--backup-dir` |
| 备份内容 | 与**写入前**的 map 逐字节相同 |
| 备份时机 | 即使写入在第 6 步失败，备份文件**也已经产生**（备份在修改之前） |
| 成功响应 | `backup` 字段是备份文件的绝对路径，且该路径存在 |
| 失败后原文件 | 任何非 0 退出码下，map 文件的 sha256 与调用前相同 |
| 临时文件残留 | 任何退出码下，`<map>.tmp-*` 都不得残留 |
| 自动删除 | 脚本**永不删除**任何备份文件。连续 5 次写入后 backup-dir 里应有 5 个文件 |
| 只追加 | `commit` 后 `cells[0..before_count-1]` 与调用前逐字段相同，新 cell 在末尾 |
| 不搬家 | `verdict` 后 `len(cells)` 不变，`rejected_or_downgraded` 逐字节不变 |

### 4.3 `_integrity` 字段

顶层键，脚本维护：

```json
"_integrity": {"writes": 13, "last_write": "2026-09-23T21:45:30+08:00",
               "last_cells_count": 104, "last_sha256": "<替换后 map 文件的 sha256>"}
```

- **首次遇到没有 `_integrity` 的地图**（103 格存量就是这种）：视为 bootstrap，
  `integrity.checked = false`，**不报警**，在本次写入时建立该字段。
- 之后每次任何子命令（含只读的 `status`/`gate`）启动时：重算当前 map 文件的 sha256，
  与 `last_sha256` 比对。
  - 相同 → `{"checked": true, "external_edit_suspected": false}`
  - 不同 → `{"checked": true, "external_edit_suspected": true}`，同时 stderr 打印一行
    中文警告。**退出码不受影响，不阻断任何操作。**
- 用途：检测"绕过脚本直接编辑 JSON"。**这是事后发现，不是事前阻止。**

---

## 5. 边界值总表（测试必须逐条覆盖）

### 5.1 数量闸

| 场景 | 期望 |
|---|---|
| 当天登记 8 个种子（一批） | 放行，退出码 0，`total_today=8` |
| 当天先登记 5 个，再登记 3 个 | 两次都放行，`total_today=8` |
| 当天先登记 5 个，再登记 4 个 | 第二次拒绝，退出码 2，`gate=seed_cap`，`CAP_EXCEEDED`；**且第二批一个都没写进会话文件**（`list` 仍为 5） |
| 当天一批登记 9 个 | 拒绝，退出码 2，`CAP_EXCEEDED` |
| 登记 0 个（空数组） | 退出码 3，`code=EMPTY` |
| 昨天已登记 8 个，今天登记 1 个（`--today` 注入不同日期） | 放行（配额按日重置） |
| 当天已有 2 个 schema2 cell，commit 第 3 个 | 放行，退出码 0，`today_count=3` |
| 当天已有 3 个 schema2 cell，commit 第 4 个 | 拒绝，退出码 2，`gate=hypothesis_cap`，`CAP_EXCEEDED` |
| 地图里有 47 个 `date=2026-09-15` 的 **schema1** cell，今天 commit 第 1 个 | 放行（老格子不计入日上限，因为它们不是 schema2） |
| stdin 里写 `"date": "1999-01-01"` 试图绕开日上限 | `date` 被覆写为当天；若当天已满 3 个仍然拒绝 |

### 5.2 必填字段闸

| 场景 | 期望 |
|---|---|
| 完整合格 cell | 放行，退出码 0 |
| 缺 `falsification` | 拒绝，`gate=required_fields`，含 `{"field":"falsification","code":"MISSING"}` |
| `falsification` 为 `""` / `"   "` | 拒绝，`code=EMPTY` |
| `falsification` 为 `"待补"` | 拒绝，`code=PLACEHOLDER` |
| `falsification` 长 29 字符 | 拒绝，`code=TOO_SHORT` |
| `falsification` 长 30 字符 | **放行**（边界含等号） |
| `hypothesis` 只有 3 个键 | 拒绝，缺的那个键报 `field="hypothesis.<键名>"`，`code=MISSING` |
| `hypothesis.gap` 长 30、其余 ≥30 | 放行 |
| `hypothesis` 是字符串 | 拒绝，`code=WRONG_TYPE` |
| `feasibility_layers` 有 2 个键 | 拒绝，`code=TOO_FEW` |
| `feasibility_layers` 有 3 个键，键名是 `机制`/`体系实现`/`三年立项` | **放行**（不校验键名） |
| `feasibility_layers` 有 3 个键但其中一个值是 `""` | 拒绝，`code=EMPTY`，`field="feasibility_layers.<键名>"` |
| `novelty` = `"中-高"` | 放行 |
| `novelty` = `"甜区（创新中-高×可行高）"` 这类长文本 | 放行（不校验取值） |
| `quadrant` = `"—"` | 拒绝，`code=PLACEHOLDER` |
| `method` = `"重组合 + 换角度"` | 拒绝，`code=NOT_ALLOWED`（schema2 必须是三个英文枚举之一） |
| `method` = `"transfer"` + `novelty_queries` 只有 1 条 | 拒绝，`code=TOO_FEW`，`field="novelty_queries"` |
| `method` = `"transfer"` + `novelty_queries` 有 2 条 | 放行 |
| `method` = `"angle"` + `novelty_queries` 有 1 条 | 放行 |
| `novelty_queries` = `[]` | 拒绝，`code=EMPTY` |
| `novelty_queries` = `["ab"]` | 拒绝，`code=TOO_SHORT`（单条 <3） |
| 同时缺 `falsification` 和 `diff` | **一次返回两条 errors**（不是只报第一条） |

### 5.3 `diff` 条件规则

| `closest_work` | `diff` | 期望 |
|---|---|---|
| `"未见先例"` | 缺省 | 放行 |
| `"未检索到直接工作"` | `"—"` | 放行 |
| `"检索未见直接先例，但这不等于绝对没有"` | `""` | 放行 |
| `"PMID 40476548（Nano Lett 2025…）"` | 缺省 | 拒绝，`field="diff"`，`code=MISSING` |
| `"PMID 40476548（Nano Lett 2025…）"` | `"无"` | 拒绝，`code=PLACEHOLDER` |
| `"PMID 40476548（Nano Lett 2025…）"` | 9 个字符 | 拒绝，`code=TOO_SHORT` |
| `"PMID 40476548（Nano Lett 2025…）"` | 10 个字符 | 放行 |
| `""` | 任意 | 拒绝，`field="closest_work"`，`code=EMPTY` |

### 5.4 裁决终态闸

| `user_verdict` 输入 | `commit` / `verdict` 的期望 |
|---|---|
| `"采纳"` | 放行 |
| `"否决"` | 放行 |
| `"归档"` + `restart_condition` 长 10 | 放行 |
| `"归档"` + 无 `restart_condition` | 拒绝，`gate=verdict`，`field="restart_condition"`，`code=MISSING` |
| `"归档"` + `restart_condition` 长 9 | 拒绝，`code=TOO_SHORT` |
| `"归档"` + `restart_condition` = `"待定"` | 拒绝，`code=PLACEHOLDER` |
| `"待定"` | 拒绝，`code=NOT_ALLOWED` |
| `"待柚子确认"` | 拒绝，`code=NOT_ALLOWED` |
| `"pending"` / `"PENDING"` | 拒绝，`code=NOT_ALLOWED` |
| `"搁置"` | 拒绝，`code=NOT_ALLOWED` |
| `""` / `"   "` | 拒绝，`code=NOT_ALLOWED` |
| `"采纳：作为 2027 青基主线"` | 拒绝，`code=NOT_ALLOWED`（**精确相等，不做前缀匹配**；补充说明请写进别的字段） |
| 缺 `user_verdict` 键 | 拒绝，`code=MISSING` |

### 5.5 零积压闸与老数据

| 场景 | 期望 |
|---|---|
| 地图含 87 个占位裁决 | `gate` 退出码 2，`undecided=87` |
| 地图含 `"不建议作主课题"` 的 cell | 该 cell **不计入** `undecided`（黑名单判定） |
| 地图含 `"已否决（2026-09-15）：…"` | 不计入 `undecided` |
| 地图含 `"待定：拟作 2027 青基主线方案 A"` | **计入** `undecided`（前缀匹配） |
| 地图所有 cell 都有终态裁决 | `gate` 退出码 0 |
| `cells` 为空数组 | `gate` 退出码 0，`undecided=0` |
| cell 完全缺 `user_verdict` 键 | 计入 `undecided` |

### 5.6 老数据兼容（**最关键的一组，必须全绿**）

用真实地图的副本（103 格，全部 schema1）跑：

| 断言 | 期望 |
|---|---|
| `status` | 退出码 0，`total=103`，`schema1=103`，`schema2=0`，`undecided=87` |
| `verdict` 给一个缺 `feasibility_layers`/`falsification`/`hypothesis` 的老格子写 `"归档"` + 重启条件 | **放行**，退出码 0 |
| `verdict` 批量给 87 格写裁决 | 放行，`updated=87`，`undecided_after=0`，`cells_after=103` |
| 被改过的老格子 | 除 `user_verdict`/`restart_condition`/`archived`/`verdict_date` 外，所有原字段逐字段不变（含 `intervention_2026-09-12` 这类非常规键） |
| `verdict` 目标是已有 `"不建议作主课题"` 的格子，不带 `--allow-overwrite` | 拒绝，`code=ALREADY_DECIDED` |
| 同上，带 `--allow-overwrite` | 放行 |
| 全程 | 任何子命令都不得因老格子缺新必填字段而返回非 0 退出码 |

### 5.7 寻址与数据安全

| 场景 | 期望 |
|---|---|
| `verdict` 的 `index=999`（超界） | 拒绝，`code=INDEX_OUT_OF_RANGE`，地图未改 |
| `expect` 与目标 `idea` 前缀不符 | 拒绝，`code=PREFIX_MISMATCH`，响应带 `actual_prefix`，地图未改 |
| 批量 50 条里第 37 条 `expect` 不符 | **整批拒绝**，`updated` 不出现，地图逐字节未改 |
| 同一批里 `index` 重复 | 拒绝，`code=NOT_ALLOWED` |
| map 文件内容是 `"{ broken"` | 退出码 4，`code=BAD_JSON`，**文件未被重建或覆盖** |
| map 文件不存在 | 退出码 4，`code=IO_FAILED`，**不创建空地图** |
| backup-dir 指向一个只读目录 | 退出码 4，`code=IO_FAILED`，map 未改 |
| 任意失败路径结束后 | 无 `<map>.tmp-*` 残留 |
| 手动改动 map 后再跑 `status` | `integrity.external_edit_suspected=true`，**退出码仍为 0** |

---

## 6. 本接口**不**保证的事（诚实声明，别拿它当闸门）

写测试的人不必为下列项设计断言——脚本层面根本不具备这些能力：

1. **假说内容的真假与质量。** 闸门只能保证四要素字段存在、非占位、够长。四段 30 字的
   空话一样能通过。
2. **`novelty_queries` 里的检索式是否真的跑过。** 脚本不联网、不查证，它只检查这个字段
   有没有填、条数够不够。
3. **第一段在对话里实际展示了多少个种子。** 脚本只保证"登记进会话文件的不超过 8 个"，
   保证不了"说出口的不超过 8 个"。
4. **AI 是否愿意调用这些脚本。** 直接用编辑器改 `migration_map.json` 可以绕过全部四个闸门。
   `_integrity` 只能在**下一次**脚本运行时报出"疑似被外部编辑"，属事后发现。
5. **裁决是否明智。** 闸门保证每格有终态，不保证那个终态是对的。

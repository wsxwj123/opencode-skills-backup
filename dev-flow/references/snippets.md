# snippets：派子代理时照抄的片段（跨阶段共用）

只放多个阶段共用的三样：预算块、security-review 前置命令、测试摘要怎么出。各阶段的逐字禁令和报告格式在各阶段文件里。

## 1. 预算块（派任何子代理都贴进 prompt，按角色填数）

照抄这段，N / K 换成下表的数；M 那句只给测试设计代理，其他角色不贴：

> 预算：工具调用不超过 N 次；最终报告不超过 K 字，报告格式按派工说明里的要求。只做本 prompt 列出的几处；派工清单里的文件必须读完，不通读和任务无关的文件；不为了验证测试本身去搭假服务。快到上限还没做完，就停下来交中间报告，说清做到哪、还差什么。
> （测试设计代理加这句）测试用例不超过 M 条，超出要在报告里写理由。

| 角色 | 工具调用上限 N | 测试条数上限 M | 报告上限 K |
|---|---|---|---|
| 调研+方案（中档合成一个代理）；标准档的单独调研代理也用这档 | 120 | 不贴 | 4000 字 |
| 方案盲审 | 60 | 不贴 | 4000 字 |
| 测试设计 | 标准档 100 / 中档 60 / 轻档 40 | 标准档 30（超出要在 TEST-PLAN 写理由）/ 中档 25 / 轻档 15 | 4000 字 |
| 开发（每个代理） | 轻档 60 / 中档 120 / 标准档 200 | 不贴（开发代理不写验收测试） | 3000 字 |
| 裁判 | 60；skill 项目按测试 prompt 条数乘 10 | 不贴 | 3000 字 |
| 安全审计 | 60 | 不贴 | 4000 字 |

用完了：代理交中间报告后，同一轮续用再给一份同样的预算，不算跨轮；连续两次用完还没做完，停下向用户汇报。续用开发代理做下一项时预算重新给一份，禁令重贴。

限工具调用次数不限 token（代理数不准 token，数得清调用）。没有机械保证，靠代理自觉；主会话在每个代理返回时把工具报回的用量记进 `.devflow/HISTORY.md`，事后对账。

**任务总闸**（主会话记账）：所有代理合计，轻档超 300 次调用或 60 万 token、中档超 600 次或 150 万、标准档超 1500 次或 400 万，停下向用户汇报再决定。都是初始值，记账两周后按 HISTORY.md 校准。

## 2. 跑内置 security-review 之前，先补 origin/HEAD

内置 security-review 靠 `git diff origin/HEAD...` 找改动，这个引用只有 clone 来的仓自带，本地起家的仓没有，技能会报"有歧义的参数 origin/HEAD"。跑之前先执行：

```bash
git rev-parse -q --verify origin/HEAD >/dev/null || { git remote get-url origin >/dev/null 2>&1 && git fetch -q origin && git remote set-head origin -a; } || git symbolic-ref refs/remotes/origin/HEAD refs/heads/master
```

有远端就 fetch 后建真引用（一次永久）；没远端或网络被拦，造一个指向本地主分支的替身（`master` / `main` 按实际填）。造过替身的，06 建仓 push 后跑 `git remote set-head origin -a` 归正。

## 3. 测试摘要怎么出（裁判只看摘要，不看几千行原始输出）

先让测试框架出机器可读的报告，原始输出也落盘：

```bash
# pytest
pytest tests/acceptance -q --junitxml=.devflow/junit-<任务名>.xml 2>&1 | tee .devflow/test-output-<任务名>.txt
# jest
npx jest --json --outputFile=.devflow/jest-<任务名>.json 2>&1 | tee .devflow/test-output-<任务名>.txt
# playwright（用环境变量指定 json 落点，别用重定向，stderr 会混进 json）
PLAYWRIGHT_JSON_OUTPUT_NAME=.devflow/pw-<任务名>.json npx playwright test --reporter=json 2>&1 | tee .devflow/test-output-<任务名>.txt
# 全量回归（含单测）：同样的命令把目录换成整个测试目录，报告文件加 -full 后缀，例如
pytest -q --junitxml=.devflow/junit-<任务名>-full.xml 2>&1 | tee .devflow/test-output-<任务名>-full.txt
```

其他框架（node test、go test、cargo test）用它们的 `-json` 或 `-v` 输出落盘，计数从落盘文件 grep，不凭记忆估。

从报告文件抄数。junit 的总数在文件头：

```bash
grep -oE '(tests|failures|errors|skipped)="[0-9]+"' .devflow/junit-<任务名>.xml | head -4   # 计数
grep -B1 -A2 -E '<(failure|error|skipped)' .devflow/junit-<任务名>.xml                      # 每条失败/跳过及原因
```

jest 的 json 看 `numPassedTests / numFailedTests / numPendingTests` 和 `testResults[].assertionResults[]`，playwright 看 `stats` 和 `suites[].specs[]`。

摘要文件 `.devflow/test-summary-<任务名>.md` 固定五段：
1. 通过 / 失败 / 跳过各几条
2. 失败用例清单：用例名 + 断言信息各一行
3. 每条跳过的用例和原因（一条不省，跳过最容易藏问题）
4. 全量回归结果（从 -full 报告抄计数）和锁定核查结果（轻档：锁 tag 等于账本值；标准档：LOCK 文件值等于 git 推导值和账本值；锁在当前 HEAD 历史里，`tests/acceptance/` diff 为空，测试运行环境没被改）
5. 实点 / 真调结果

末尾列原始输出和报告文件路径，裁判只许 grep 对照，并抽一处计数核对。

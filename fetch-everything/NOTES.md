# fetch-everything 开发状态与计划

> 最后更新：2026-06-14

## 当前能力（已实测，8 类场景通过）

- 普通网页 / 技术文档：在线服务（markdown.new / r.jina.ai 等）秒级拿正文
- JS 动态渲染：质量门否决空壳 → 降级浏览器渲染拿到真实内容
- 微信 / 小红书等动态站：识别后只走 Scrapling、不补在线服务（必风控）
- 短链重定向、403/错误页优雅失败、孤儿进程回收
- 质量门**否决式判定**：盾页/验证/未渲染特征一票否决（不被内容长度架空），软噪音（微信扫一扫等）仅扣分不误杀
- run_cmd 进程组（防孤儿 chromium）、scrapling 读入即删 tmp、环境代理透传 `--proxy`、early-exit 优先级降级

## CF / 登录态：暂停（先不做）

- CDP 兜底路线已实现：环境变量 `FETCH_CDP_URL` opt-in，不设则完全不启用（默认流程实测不变）。
- 障碍：Chrome 149 禁止对默认 profile 开 `--remote-debugging-port`，CDP 连不上日常 Chrome 活会话；独立 profile 能开但无登录态。
- 决策：CF/登录态路线在本技能内**暂停**；CDP 代码保留为可选（独立 profile / 可调试环境仍有效），未在 Chrome 149 默认 profile 验证通过。
- 需登录态/反爬的站：用**本机已装的 autocli**（nashsu/AutoCLI，Chrome 扩展桥接复用登录态），**不集成进本技能**。
  - autocli 与 OpenCLI 是机制几乎相同的同类项目；本机已有 autocli，**不必加 OpenCLI（重复）**。
  - ✅ 已打通（2026-06-15）：扩展从 release 下载解压到 `~/.autocli-extension/`，Chrome `chrome://extensions` → 开发者模式 → Load unpacked 加载；daemon 监听 `127.0.0.1:19925`。`autocli doctor` 三项全绿，`autocli read <知乎URL>` 实测完整抓取登录态正文。
  - 分工：需登录态/反爬正文 → `autocli read <URL>`（Readability，已验证）；通用网页 → 本技能 fetch_everything.py。零冗余。
  - 已知限制：`zhihu hot`/`search` 等结构化 adapter 命令在页面内 `fetch` 知乎内部 API 时报 `TypeError: Failed to fetch`（上游 adapter / 知乎 API 变更，非扩展连接问题）；正文需求 `read` 已覆盖，不在本技能内修上游 adapter。

## 同步

claude 源（带 git）→ push GitHub `opencode-skills-backup` → rsync 镜像到 opencode / codex 纯文件副本。

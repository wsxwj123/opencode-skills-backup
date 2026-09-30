# platform-compat-review

跨平台(Windows / macOS)兼容性审查的 Claude Code 技能:告诉审查员**去哪里看、看到什么算有问题**,不给修法。适用于任何 Node / Tauri / Electron / CLI 项目。

## 内容
- `SKILL.md` —— 五步审查流程(定范围 → 扫描 → 逐类核对 → 报告 → 回写排查点)与追加规范
- `references/checkpoints.md` —— 排查点目录:W-(Windows 事故)/ M-(macOS 事故)/ X-(跨平台)/ G-(未踩预警),每条五段:排查 / 判据 / 机制 / 事故 / 真机,带 [Win] [Mac] [Both] 标签
- `references/review-checklist.md` —— 逐问句核对清单 + 报告模板 + 分平台真机验证单
- `scripts/scan.mjs` —— 静态扫描:`node scripts/scan.mjs --root <repo> [--base <rev>] [--platform win|mac|all] [--json]`,只定位候选位置不定罪
- `scripts/crt-roundtrip.mjs` —— Windows cmd.exe + CRT 命令行引号往返模拟器:`node scripts/crt-roundtrip.mjs <module.js> [--export winCmdSpawnSpec]`

## 安装
```bash
git clone git@github.com:wsxwj123/platform-compat-review.git ~/.claude/skills/platform-compat-review
```
Claude Code 重启后自动加载;说「检查 Windows/Mac 兼容性」即触发。

## 追加新排查点
按 `SKILL.md` 末尾的五段格式写进 `references/checkpoints.md`,能写正则的同步进 `scripts/scan.mjs` 的 RULES(hint 只写"核对什么"),跑一次 `node scripts/scan.mjs --root <repo>` 确认不误报。

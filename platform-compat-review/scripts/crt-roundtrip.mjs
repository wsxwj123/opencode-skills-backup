#!/usr/bin/env node
// cmd.exe + UCRT 命令行引号往返模拟器(W-A2 / W-F2)。
//   node crt-roundtrip.mjs <module-path> [--export winCmdSpawnSpec] [--arg-index 3]
// 对模块导出的 spec 函数 (resolved, args, opts) -> { file, args } 跑固定用例:
//   取 args[argIndex](默认 3,即 cmd.exe /d /s /c 之后那一整行),
//   按 cmd `/s` 规则剥掉整条命令的首尾引号,再按 UCRT parse_command_line 切成 argv,
//   与 [resolved, ...args] 逐字比对。任一用例不还原 → 退出码 1。
// 规则复刻:2N 个 \ + " → N 个 \ 并切换引号态;2N+1 个 \ + " → N 个 \ + 字面 ";
//          引号态内 "" → 字面 " 且保持引号态(与 CommandLineToArgvW 一致)。
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const argv = process.argv.slice(2);
const modPath = argv.find((a) => !a.startsWith('--'));
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
if (!modPath) { console.error('用法: node crt-roundtrip.mjs <module> [--export name] [--arg-index 3]'); process.exit(2); }
const exportName = opt('--export', 'winCmdSpawnSpec');
const argIndex = Number(opt('--arg-index', '3'));

function crtParse(cmdline) {
  const out = []; let i = 0, inQ = false, cur = '', started = false;
  while (i < cmdline.length) {
    const c = cmdline[i];
    if (!inQ && (c === ' ' || c === '\t')) { if (started) { out.push(cur); cur = ''; started = false; } i++; continue; }
    started = true;
    let bs = 0; while (cmdline[i] === '\\') { i++; bs++; }
    if (cmdline[i] === '"') {
      let copy = true;
      if (bs % 2 === 0) {
        if (inQ && cmdline[i + 1] === '"') { i++; }
        else { copy = false; inQ = !inQ; }
      }
      cur += '\\'.repeat(Math.floor(bs / 2));
      if (copy) cur += '"';
      i++;
    } else { cur += '\\'.repeat(bs); if (i < cmdline.length) { cur += cmdline[i]; i++; } }
  }
  if (started) out.push(cur);
  return out;
}
const cmdStrip = (s) => (s.startsWith('"') && s.endsWith('"') ? s.slice(1, -1) : s);

const CASES = [
  ['尾 1 个 \\', ['C:\\npm\\claude.cmd', '-e', 'ROOT=D:\\data\\', '--', 'npx']],
  ['盘根 D:\\', ['C:\\npm\\claude.cmd', 'project', 'purge', '-y', 'D:\\']],
  ['尾 2 个 \\', ['C:\\npm\\claude.cmd', 'D:\\a\\\\', 'next']],
  ['尾 3 个 \\', ['C:\\npm\\claude.cmd', 'D:\\a\\\\\\', 'next']],
  ['纯反斜杠 token', ['C:\\npm\\claude.cmd', '\\', 'next']],
  ['中间反斜杠', ['C:\\npm\\claude.cmd', 'C:\\a\\b', 'next']],
  ['空串 token', ['C:\\npm\\claude.cmd', '', 'next']],
  ['元字符/空格/内嵌引号', ['C:\\npm\\claude.cmd', 'mcp<2', 'a&b', 'x|y', 'p^q', 'has space', 'say "hi"', 'next']],
  ['路径带空格', ['C:\\Program Files\\nodejs\\npx.cmd', '-y', 'pkg', 'C:\\Users\\John Smith\\Documents']],
  ['单个引号 token', ['C:\\npm\\claude.cmd', '"', 'next']],
  ['反斜杠紧邻内嵌引号 a\\"b', ['C:\\npm\\claude.cmd', 'a\\"b', 'next']],
  ['两反斜杠+引号 a\\\\"b', ['C:\\npm\\claude.cmd', 'a\\\\"b', 'next']],
  ['token 以 \\" 结尾', ['C:\\npm\\claude.cmd', 'a\\"', 'next']],
  ['引号后跟反斜杠 a"\\', ['C:\\npm\\claude.cmd', 'a"\\', 'next']],
  ['JSON 参数', ['C:\\npm\\claude.cmd', '--config', '{"k":"v\\\\w","n":1}', 'next']],
];

const mod = await import(pathToFileURL(resolve(modPath)).href);
const spec = mod[exportName];
if (typeof spec !== 'function') { console.error(`模块没有导出函数 ${exportName}`); process.exit(2); }

let fail = 0;
for (const [name, toks] of CASES) {
  const [resolved, ...rest] = toks;
  const s = spec(resolved, rest, {});
  const line = s?.args?.[argIndex];
  const ok = typeof line === 'string' && JSON.stringify(crtParse(cmdStrip(line))) === JSON.stringify(toks)
    && s.file === 'cmd.exe' && s?.opts?.windowsVerbatimArguments === true;
  if (!ok) fail++;
  console.log(`${ok ? '✅' : '❌'} ${name.padEnd(28)} ${ok ? '' : ' 得到: ' + JSON.stringify(typeof line === 'string' ? crtParse(cmdStrip(line)) : s)}`);
}
console.log(fail ? `\n${fail} 条不还原 —— 引号函数不完整(对照 checkpoints.md W-A2 的四条规则)。` : `\n${CASES.length}/${CASES.length} 往返全部还原。`);
process.exit(fail ? 1 : 0);

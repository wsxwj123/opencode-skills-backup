#!/usr/bin/env node
// 跨平台兼容性静态扫描:按 references/checkpoints.md 的判据抓已知反模式,只定位不定罪。
//   node scan.mjs --root <repo> [--base <rev>] [--platform win|mac|all] [--json]
// --base 给了只扫该 rev..HEAD 的**新增行**(diff 的 + 行);不给就扫全树。
// 每条规则带 id(对应 checkpoints.md)、plat(win/mac/both)、sev(must/hint);hint 文案写"核对什么",不写修法。
import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative, extname } from 'node:path';

const args = process.argv.slice(2);
const opt = (k, d = null) => { const i = args.indexOf(k); return i >= 0 ? (args[i + 1] ?? d) : d; };
const ROOT = opt('--root', process.cwd());
const BASE = opt('--base');
const PLAT = (opt('--platform', 'all') || 'all').toLowerCase();
const JSON_OUT = args.includes('--json');

const EXT = new Set(['.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.rs', '.yml', '.yaml', '.bat', '.cmd', '.nsh', '.ps1', '.sh', '.command', '.css']);
const SKIP_DIR = /(^|[\\/])(node_modules|dist|target|\.git|\.claude|\.devflow|generated|coverage|scratchpad)([\\/]|$)/;
// 跳过:测试目录、check-*.mjs 自测脚本(夹具里的 /tmp 是故意的)、*.local.* 私有文件。
const SKIP_FILE = /(^|[\\/])tests[\\/]|(^|[\\/])check-[^\\/]*\.mjs$|\.local\.[a-z]+$|CHANGELOG\.md$/;

const RULES = [
  // ── A 进程与命令行 ──
  { id: 'W-A5',  plat: 'win',  sev: 'must', re: /\bwmic\b/, hint: '核对 wmic 是不是首选路径(Win11 24H2 已移除;只允许作为 CIM 之后的回落)' },
  { id: 'W-A2',  plat: 'win',  sev: 'must', re: /spawn(?:Sync)?\(\s*['"]cmd(?:\.exe)?['"]\s*,\s*\[\s*['"]\/c['"]/, hint: '核对这条 cmd.exe 命令行:参数是否可能含 <>|&^/空格/引号/尾反斜杠,拼法是否为 verbatim 全套;用户可控内容有没有进来' },
  { id: 'W-A2',  plat: 'win',  sev: 'must', re: /\[\s*['"]\/c['"]\s*,/, hint: "核对这个 ['/c', …] 数组最终交给谁、参数来源是否可控、是否经统一引号函数" },
  { id: 'W-A2',  plat: 'both', sev: 'must', re: /shell\s*:\s*true/, hint: '核对 shell:true 下每个参数的来源:任一可控即注入面(Windows 是 cmd 元字符,mac 是 sh 元字符)' },
  { id: 'W-A6',  plat: 'win',  sev: 'hint', re: /process\.env\.SHELL\b/, hint: '核对该调用在 win32 是否会走到(Windows 没有 SHELL)' },
  { id: 'W-A6',  plat: 'win',  sev: 'hint', re: /['"]-lc['"]|['"]\/bin\/(?:ba)?sh['"]/, hint: '核对 login shell 写法在 win32 是否有分支绕开(mac 上反而常需要它补 PATH,见 M-A1)' },
  { id: 'W-A9',  plat: 'win',  sev: 'hint', re: /\blsof\b/, hint: '核对 lsof 是否只在非 win32 分支;win32 那条路怎么查进程' },
  { id: 'W-A9',  plat: 'win',  sev: 'hint', re: /\.kill\(\s*-|process\.kill\(\s*-/, hint: '核对负 pid/进程组信号在 win32 是否会走到;Windows 分支怎么杀整棵树' },
  { id: 'W-A10', plat: 'both', sev: 'hint', re: /\b(?:execFileSync|execSync|spawnSync)\(/, hint: '核对同步 spawn 是否在请求路径、超时多长、首次执行大 exe 会不会被杀软扫描拖住' },
  { id: 'W-A12', plat: 'both', sev: 'hint', re: /\breaddirSync\(/, hint: '核对同步枚举会不会扫到 PATH 目录(System32 数千项、断掉的映射盘)或超大目录' },
  { id: 'X-A7',  plat: 'both', sev: 'hint', re: /\.slice\(0,\s*[A-Z_][A-Z0-9_]*\)\s*(?:===|!==)|(?:===|!==)[^\n]*\.slice\(0,\s*[A-Z_]/, hint: '核对:截断值参与相等判据(显示口径 vs 比较口径必须一致;越界样例会突变,CJK/emoji 更早触发)' },
  { id: 'W-A17', plat: 'both', sev: 'hint', re: /\bsetTimeout\(/, hint: '核对:这个延迟定时器是否在停用/卸载路径 clearTimeout(重试/重探/退避类最易漏;回调里有 spawn 或请求时按 W-A17 判)' },
  { id: 'W-A15', plat: 'win',  sev: 'must', re: /['"]powershell(?:\.exe)?['"](?![^\n]*ExecutionPolicy)/, hint: '核对 powershell 调用:执行策略参数、输出编码(中文系统 cp936 乱码)、内联里有没有裸调 npm 系命令' },
  { id: 'W-A15', plat: 'win',  sev: 'hint', re: /-Command[^\n]*\b(?:npm|npx|claude)\s(?![^\n]*\.cmd)/, hint: '核对 PowerShell 内联里裸调的 npm/npx/claude 在 Restricted 策略下会不会挑到 .ps1' },
  { id: 'M-A1',  plat: 'mac',  sev: 'hint', re: /\bspawn\(\s*['"](?:node|npm|npx|claude|git|python3?|uv|uvx|brew)['"]/, hint: '核对 GUI(非终端)起的进程能否找到这个命令:mac 图形应用的 PATH 不含 Homebrew/nvm/pyenv,需要 login shell 解析或固定候选' },
  { id: 'M-A2',  plat: 'mac',  sev: 'hint', re: /\bxattr\b(?!.*\/usr\/bin\/xattr)/, hint: '核对 xattr 是否写了 /usr/bin/xattr 绝对路径(pyenv/conda 的同名 python 命令会遮蔽系统 xattr)' },
  { id: 'M-A3',  plat: 'mac',  sev: 'hint', re: /^\s*timeout\s+\d/m, hint: 'macOS 没有 timeout 命令(coreutils 才有):核对这条 shell 在 mac 会不会走到' },
  { id: 'M-A3',  plat: 'mac',  sev: 'hint', re: /\bsed\s+-i\s+(?!'')(?!"")[^\s]/, hint: 'BSD sed 的 -i 需要备份后缀参数(`-i \'\'`),GNU 写法在 mac 报错:核对脚本目标平台' },
  { id: 'M-A3',  plat: 'mac',  sev: 'hint', re: /\breadlink\s+-f\b/, hint: '旧版 macOS 无 readlink -f:核对是否用 realpath/Node 解析' },
  { id: 'M-A5',  plat: 'both', sev: 'hint', re: /\bpip3?\s+install\b|python3?\s+-m\s+pip\s+install\b/, hint: '核对这条 pip install 对系统/发行版 Python 会不会撞 PEP 668(有没有 venv/--user/pipx);入口解释器与 pip 是否同一个;装后有无 import 自检' },
  // ── B 路径与文件系统 ──
  { id: 'W-B1',  plat: 'win',  sev: 'must', re: /\bpath\.posix\b/, hint: '核对 path.posix 产出的路径会不会用于 Windows 文件系统' },
  { id: 'W-B1',  plat: 'win',  sev: 'must', re: /['"]\/tmp(?:\/|['"])/, hint: '核对硬编码 /tmp 在 win32 是否会走到;mac 上还要看 M-B1 的 /private/tmp 别名' },
  { id: 'W-B1',  plat: 'win',  sev: 'hint', re: /\.split\(\s*['"]\/['"]\s*\)/, hint: "核对按 '/' 切的字符串是否可能是 Windows 路径" },
  { id: 'W-B1',  plat: 'win',  sev: 'hint', re: /`\$\{[^}]+\}\/\$\{[^}]+\}`/, hint: '核对模板串拼的是不是路径(混合分隔符会到哪去)' },
  { id: 'W-B2',  plat: 'win',  sev: 'hint', re: /process\.env\.HOME\b/, hint: '核对读 HOME 的地方在 Windows 拿到什么;测试里设 HOME 是否同时设了 USERPROFILE' },
  { id: 'W-B3',  plat: 'win',  sev: 'hint', re: /\benv\.PATH\b(?![^\n]*\bPath\b)/, hint: '核对这个 env 对象是不是展开后的普通对象(键名可能是 Path)' },
  { id: 'W-B5',  plat: 'win',  sev: 'hint', re: /(?:stdout|output|out|result|text)[^\n]*\.split\(\s*['"]\\n['"]\s*\)/, hint: '核对这段文本来源会不会带 \\r(子进程输出/Windows 检出的文件)' },
  { id: 'W-B7',  plat: 'win',  sev: 'hint', re: /file:\\?\/\\?\//, hint: '核对从 file:// URL 抓出来的本地路径:win32 的 file:///C:/… 剥掉前缀是 /C:/…,不能当绝对路径读(用 URL 解析或判盘符)' },
  { id: 'M-B1',  plat: 'mac',  sev: 'hint', re: /startsWith\(\s*['"]\/(?:tmp|var)\b/, hint: 'mac 上 /tmp 与 /var 是 /private 的软链:核对比较两侧是否都做过 realpath' },
  { id: 'M-B2',  plat: 'mac',  sev: 'hint', re: /\bfs\.watch\(|chokidar/, hint: 'mac 上 fs.watch 每个目录占一个 fd(chokidar v4 无 fsevents):核对监听目录规模与 EMFILE 处理' },
  { id: 'X-B4',  plat: 'both', sev: 'hint', re: /startsWith\(\s*(?:HOME|home|homedir\(\))\s*\)/, hint: '前缀检查不带分隔符会放行同级目录(/Users/x2):核对是否 === 或 startsWith(HOME+sep)' },
  { id: 'W-B13', plat: 'win',  sev: 'hint', re: /setPermissions|getWindowsAttributes/, hint: '核对 win32 权限位语义:只映射读/写两档,去掉写位=置 FILE_ATTRIBUTE_READONLY(后续追加/unlink+rename 全失败);0o600 只是清只读、拿不到「同机不可读」' },
  { id: 'X-B6',  plat: 'win',  sev: 'hint', re: /\.isWritable\(\)/, hint: '核对这个值是不是被当成「能不能写」:win32 上 nsIFile.isWritable() 对目录恒为 true(只读属性,不读 ACL),mac 上才是真 access(W_OK)' },
  // ── D 渲染引擎 ──
  { id: 'D-1',   plat: 'both', sev: 'must', re: /\bwindow\.(?:confirm|alert)\(|(?<![\w.])(?:confirm|alert)\(/, hint: '原生 confirm/alert 在 Tauri 两个 webview 都不可用:核对是否真会执行到' },
  { id: 'D-2',   plat: 'both', sev: 'hint', re: /navigator\.platform/, hint: '核对前端自判平台的用途与准确性' },
  { id: 'D-4',   plat: 'both', sev: 'hint', re: /\b\d+(?:vw|vh)\b(?![^\n]*(?:--app-h|min\())/, hint: '核对裸 vw/vh 在 zoom 下于 WebView2/Chromium 是否会撑出视口(WKWebView 已折 zoom,两边不一样)' },
  { id: 'D-4',   plat: 'both', sev: 'hint', re: /\bsticky\b/, hint: '核对 sticky 所在滚动容器有没有残留 transform' },
  { id: 'D-4',   plat: 'mac',  sev: 'hint', re: /<summary[^>]*(?:flex|grid)/, hint: 'WKWebView 上 <summary> 的 display 非 list-item 会禁用原生 details 切换:核对是否受控展开' },
  // ── E 分发 / 签名 ──
  { id: 'W-E2',  plat: 'win',  sev: 'hint', re: /\.msi\b/, hint: '核对文案提到的产物形态与 bundle.targets 是否一致' },
  { id: 'M-E1',  plat: 'mac',  sev: 'hint', re: /\bcp\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+[^\n]*\.app\b/, hint: 'cp -R 复制 .app 会破坏签名(FDA 失效):核对是否该用 ditto 且先删旧目录' },
  { id: 'M-E1',  plat: 'mac',  sev: 'hint', re: /\bditto\b/, hint: 'ditto 叠加进已存在的旧 bundle 会残留旧文件、codesign --verify 报 sealed resource missing:核对是否先 rm -rf 目标' },
  // ── G 预警 ──(验实后搬 A–E 并换正式 ID)
  { id: 'G-13',  plat: 'win',  sev: 'must', re: /(?:command|file)\s*:\s*['"](?:cmd\.exe|cmd|git|node|npm|npx|python3?|sh)['"]/, hint: '核对交给 Gecko Subprocess.call 的 command 是不是绝对路径:Windows 实现 isExecutableFile 拒绝非绝对路径(报 does not exist, or is not executable),不搜 PATH' },
  { id: 'G-13',  plat: 'win',  sev: 'must', re: /\[\s*['"]\/[dsqDSQ]['"]\s*,/, hint: '核对这串 cmd 开关最终交给谁:交 Gecko Subprocess 时只有 command 匹配 \\cmd.exe$ 且 arguments.length===3 且 arguments[1] 为 /C|/S/C 才走 cmd 特例,其余形态每个参数会被 quoteString 再转义一次(CRT 转义 cmd.exe 不认)' },
];

function listFiles(dir, out = []) {
  for (const ent of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, ent.name);
    const rel = relative(ROOT, p);
    if (SKIP_DIR.test(rel + (ent.isDirectory() ? '/' : ''))) continue;
    if (ent.isDirectory()) listFiles(p, out);
    else if (EXT.has(extname(ent.name)) && !SKIP_FILE.test(rel)) out.push(rel);
  }
  return out;
}

function collectLines() {
  const rows = [];
  if (BASE) {
    const diff = execFileSync('git', ['diff', `${BASE}..HEAD`, '--unified=0', '--no-color', '--', '.'], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
    let file = null, line = 0;
    for (const raw of diff.split(/\r?\n/)) {
      if (raw.startsWith('+++ ')) { file = raw.slice(4).replace(/^b\//, ''); continue; }
      if (raw.startsWith('--- ')) continue;
      const hunk = raw.match(/^@@ -\d+(?:,\d+)? \+(\d+)/);
      if (hunk) { line = Number(hunk[1]); continue; }
      if (!file || file === '/dev/null') continue;
      if (raw.startsWith('+')) {
        if (EXT.has(extname(file)) && !SKIP_DIR.test(file) && !SKIP_FILE.test(file)) rows.push({ file, line, text: raw.slice(1) });
        line++;
      } else if (!raw.startsWith('-')) line++;
    }
  } else {
    for (const file of listFiles(ROOT)) {
      const src = readFileSync(join(ROOT, file), 'utf8').split(/\r?\n/);
      src.forEach((text, i) => rows.push({ file, line: i + 1, text }));
    }
  }
  return rows;
}

const isComment = (t) => /^\s*(\/\/|\*|\/\*|#|<!--|;|rem\s)/i.test(t);
const wantPlat = (p) => PLAT === 'all' || p === 'both' || p === PLAT;
const hits = [];
for (const { file, line, text } of collectLines()) {
  if (isComment(text)) continue;
  for (const r of RULES) if (wantPlat(r.plat) && r.re.test(text)) hits.push({ id: r.id, plat: r.plat, sev: r.sev, hint: r.hint, file, line, text: text.trim().slice(0, 140) });
}
const order = { must: 0, hint: 1 };
hits.sort((a, b) => order[a.sev] - order[b.sev] || a.file.localeCompare(b.file) || a.line - b.line);

if (JSON_OUT) { console.log(JSON.stringify(hits, null, 2)); }
else {
  const scope = BASE ? `diff ${BASE}..HEAD 新增行` : '全树';
  console.log(`# platform-compat scan(${scope},platform=${PLAT},root=${ROOT})\n`);
  if (!hits.length) console.log('无命中。');
  else {
    console.log('| 级别 | ID | 平台 | 位置 | 片段 | 核对什么 |\n|---|---|---|---|---|---|');
    for (const h of hits) console.log(`| ${h.sev} | ${h.id} | ${h.plat} | \`${h.file}:${h.line}\` | \`${h.text.replace(/\|/g, '\\|').replace(/`/g, "'")}\` | ${h.hint} |`);
    const n = (s) => hits.filter((h) => h.sev === s).length;
    console.log(`\n必修候选 ${n('must')} / 提醒 ${n('hint')}。命中 ≠ 定罪:按 checkpoints.md 该条的判据人工核实,误报写进报告"已核对无问题"。`);
  }
}
// 用 exitCode 而不是 process.exit():大输出经管道时 exit() 会截断还没刷完的 stdout。
process.exitCode = hits.some((h) => h.sev === 'must') ? 1 : 0;

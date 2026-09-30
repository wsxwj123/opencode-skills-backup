# 跨平台排查点目录(checkpoints)

> 只回答两个问题:**去哪里看**、**看到什么算有问题**。不写修法。
> 每条五段:排查(去看哪些代码/形态)· 判据(什么样算有问题)· 机制(一句为什么)· 事故(历史出处,证明不是臆想;来自 claude-gui 的标注版本/轮次,其他项目的照收)· 真机(本机验不了时怎么验、什么算过)。
> 标签:[Win] 只在 Windows 出事;[Mac] 只在 macOS 出事;[Both] 两边都会。ID 稳定不重排:W- 源自 Windows 事故,M- 源自 mac 事故,X- 跨平台通用,G- 预警(未踩)。
>
> 目录:A 进程与命令行(含 M-A5 安装脚本装 Python 包)· B 路径与文件系统 · C 原生模块与运行时 · D 渲染引擎(Chromium dev / WebView2 / WKWebView / iOS Safari)· E 分发 / 签名 / 安装 / 网络 · F 排查方法 · G 预警

---

## A 进程与命令行

### W-A1 [Win] 直接 spawn / execFile 到 `.cmd/.bat`
- 排查:所有 `spawn`/`execFile`/`execFileSync`/`pty.spawn`/Rust `Command::new` 的第一参;凡可能落到包管理器装的工具(npm 系工具在 Windows 都是 `.cmd` 壳)或 `where` 给出的无扩展名 shim 的调用点;交给 SDK/第三方库的可执行路径。
- 判据:第一参可能是 `.cmd/.bat` 却没经 `cmd.exe`;或把 `.cmd` 路径交给了只会直接 spawn 的库。
- 机制:Node ≥18.20/20.12 拒绝非 shell 模式直跑批处理(CVE-2024-27980),报 EINVAL/ENOENT。
- 事故:claude-gui v0.2.138;r106(0.2.374)。
- 真机:用 npm 装的 CLI 走一遍主链路(对话、后台探测、添加外部服务)。

### W-A2 [Win] 经 cmd.exe 的参数引号(也是权限体系的安全边界)
- 排查:每一处 `cmd.exe /c`(含 Rust 侧)的参数拼法;负责拼引号的函数;它的**所有**消费者(修一条路漏另一条路发生过两次)。
- 判据:①参数里可能出现 `< > | & ^`、空格、内嵌 `"`、结尾 `\`、`\"` 的任一形态,而拼法不是"每 token 引号 + `""` + 引号前反斜杠翻倍 + 结尾反斜杠翻倍 + 外层引号 + `/d /s /c` + `windowsVerbatimArguments`"全套;②任何用户可控内容(模型名、提示词、外部服务参数、路径)进入这条命令行;③`scripts/crt-roundtrip.mjs` 对真源码跑往返有一行不还原。
- 机制:libuv 只给含空格/引号的参数加引号,元字符裸露给 cmd;cmd 只看引号奇偶,目标程序的 CRT 另有反斜杠规则(`\"` 是转义引号)。
- 事故:claude-gui v0.2.182(`--model x&calc` = 局域网 RCE);r108;r110/r111(`mcp<2` 报 "The system cannot find the file specified.";尾反斜杠吞后续参数)。
- 真机:传含 `<`、含空格路径、尾部 `\` 的参数各一例。

### W-A3 [Win] 引号挡不住的三样:`%VAR%`、换行、8191
- 排查:进入 cmd 命令行的每个参数来源:会不会带 `%`、换行、超长。
- 判据:用户/长文本走 argv 而不是 stdin/临时文件;位置参数无长度上限;命令行总长逼近 8191(引号让每 token 多 2 字符)。
- 机制:cmd 的 `%` 展开与逐行解析发生在引号解析之前;8191 是 cmd 硬上限。
- 事故:claude-gui r108 审查;r111。;claude-gui r113 发版前审查(0.2.376,2026-09-06):后台代理 `--bg <prompt>` 只补了 8191 长度门,含换行的 prompt 仍裸进 cmd 命令行(界面单行输入打不出,直接打 HTTP 接口可达),且既有「单词含 &|<>^」守卫因换行属空白字符而整条跳过

### W-A4 [Win] node-pty 与 cmd.exe
- 排查:`pty.spawn` 的第二参形态与第一参来源。
- 判据:verbatim 形态(`['/d','/s','/c','"…"']`)以数组传给 node-pty(它会再转义引号);`file` 是裸 `cmd.exe`(winpty 路径不搜 PATH)。
- 机制:node-pty 对 string[] 自己加引号,对 string 原样透传;conpty 与 winpty 对 `file` 解析不同。
- 事故:claude-gui r110c/r111。
- 真机:PTY 类功能(远程控制/终端)在 Win10 build <18309 与新版各验一次。

### W-A5 [Win] `wmic`
- 排查:所有 `wmic` 出现点及调用顺序。
- 判据:`wmic` 是首选路径(而非 `Get-CimInstance` 之后的回落)。
- 机制:Win11 24H2 起默认镜像移除。
- 事故:claude-gui v0.2.142。

### W-A6 [Win] login shell 惯性
- 排查:`process.env.SHELL`、`-lc`、`/bin/bash`、`/bin/sh` 出现点。
- 判据:该调用在 Windows 也会走到(没有 win32 分支绕开)。
- 机制:Windows 没有 SHELL,`/bin/bash` 不存在 → ENOENT。注意 mac 上这套写法反而常是必要的(M-A1)。
- 事故:claude-gui v0.2.1x。

### W-A7 [Both] 参数里的双引号
- 排查:`execFile`/PowerShell/sh 调用里拼字符串带 `"` 的地方。
- 判据:参数靠字符串拼接而非数组;PowerShell 内联用双引号包用户内容;sh `-c` 字符串里插用户内容。
- 事故:claude-gui v0.2.1x。

### W-A8 [Win] 无控制台进程的 stdio 与日志去向
- 排查:GUI/安装器起后端进程的方式;诊断日志用 `console.log` 还是 `console.error`;新增的 `cmd.exe` 子进程会不会弹黑窗。
- 判据:后端 stdout 未重定向(无效句柄阻塞写入);关键诊断走 stdout(装机版丢 null,只有 stderr 落日志)。
- 事故:claude-gui v0.2.13;r108 审查。
- 真机:双击能开;后台探测时有无黑窗闪。

### W-A9 [Both] 进程树、信号、孤儿、查进程
- 排查:所有杀进程/查进程的代码(`kill(-pid)`、`child.kill`、`lsof`、`taskkill`、CIM 查询、`claude stop` 类命令);长期子进程有没有父进程退出清理。
- 判据:Windows 分支用了负 pid/信号语义;只杀壳不杀树(`spawn('uvx …')` 的孙进程);按 pid 杀多个指向同一 supervisor 的后台代理;父进程退出没有 killAll(mac 上被 launchd 收养后继续跑,重启后内存表为空再起第二个并发写同一文件)。
- 事故:claude-gui 后台任务可视化、MCP 探测、2026-05-29。

### W-A10 [Both] 请求路径上的同步 spawn / 同步扫目录
- 排查:路由处理函数里的 `execFileSync/execSync/spawnSync/readdirSync/statSync`;首次执行大二进制的地方;并发预热与同步兜底同写一个缓存的地方。
- 判据:在请求路径同步跑且超时 >2s;目录枚举可能扫到 PATH 目录或超大目录;缓存写入没有"只保留有效值/谁先到"的并发口径。
- 机制:Windows Defender 首次扫 80MB exe 可达数秒;SMB 断盘 stat 卡到超时;单线程服务全冻。
- 事故:claude-gui r108(两次判官各抓到一半竞态)。
- 真机:冷启后立刻打开会触发探测的页面,不卡。

### W-A11 [Win] 错误文案的来源判断
- 排查:把子进程错误翻成人话的地方。
- 判据:只翻译 Node ENOENT;`The system cannot find the file specified.` 这类原文被当成"命令不在 PATH"。
- 机制:这句原文来自 cmd 重定向失败或 Rust `os error 2`,不是 Node ENOENT。
- 事故:claude-gui r110。

### W-A12 [Win] 命令解析:PATH 快照、候选目录、枚举、`where` 多命中
- 排查:所有"找可执行文件"的逻辑:PATH 来源(进程启动快照 vs 注册表实时)、候选目录清单(`.local\bin`、`%APPDATA%\npm`、Python `Scripts`、scoop、`%LOCALAPPDATA%\Programs\nodejs`)、目录内怎么判存在(exists vs readdir)、`where` 多行取法、缓存、安装器候选与运行时候选是否同一份。
- 判据:只信启动时 PATH;真 Windows 上 readdir 枚举;注册表 PATH 同步读且无缓存;`where` 取第一行(可能是无扩展名 shim);解析失败原样 spawn 后没给人话。
- 机制:安装器写注册表 PATH 后已运行进程不刷新;NTFS 大小写不敏感 exists 已够;读出来的是**已展开**的值——`nsWindowsRegKey.readStringValue` 对 `REG_EXPAND_SZ` 走 ExpandEnvironment(mozilla-central `xpcom/ds/nsWindowsRegKey.cpp`,2026-09-14 实取),`%USERPROFILE%` 拿到的是绝对路径,调用方不需要自己展开。
- 事故:claude-gui v0.2.98/146;r106/r108。
- 真机:工具不在 PATH 时能否被找到;PATH 挂断掉的映射盘不卡。

### M-A1 [Mac] 图形应用起的进程拿不到终端里的 PATH
- 排查:GUI(Tauri/Electron/launchd 起的服务)里 spawn `node/npm/npx/git/python/uv/brew` 等裸命令的地方;找可执行文件的候选清单。
- 判据:依赖 `process.env.PATH` 而它来自 launchd(不含 Homebrew `/opt/homebrew/bin`、nvm、pyenv);没有 login shell 解析(`sh -lc 'command -v x'`)或固定候选;应用内自带的 node 抢了 PATH(带 Team ID 签名校验的 node 拒绝第三方原生模块,报 `Cannot find native binding` / `different Team IDs`)。
- 机制:mac 图形应用的环境变量不经过 shell 配置文件;POSIX 裸 spawn 是 `posix_spawnp` 按继承的 PATH 找。
- 事故:claude-gui find_node / env-check;README 常见问题。
- 真机:从 Finder 双击启动(不是终端 `open`/`npm start`),看能否找到 CLI/git/uv。

### M-A2 [Mac] shim 遮蔽系统命令
- 排查:调用 `xattr`、`python`、`sed`、`readlink` 等系统命令的脚本与 spawn。
- 判据:没写绝对路径,而用户环境有 pyenv/conda/Homebrew 的同名命令(pyenv 的 `xattr` 是 Python 版,`-dr` 不认)。
- 事故:claude-gui 持久自签(xattr 坑)。

### M-A3 [Mac] BSD 工具与 GNU 工具的差异
- 排查:项目内 shell 脚本、CI 步骤、判官/测试脚手架里的 `sed -i`、`timeout`、`readlink -f`、`date -d`、`grep -P`、`xargs -d`。
- 判据:用了 GNU 专有写法且会在 mac 跑(macOS 无 `timeout`,BSD sed `-i` 要备份后缀参数)。
- 事故:claude-gui r106 判官"373 全红"假警报(macOS 无 timeout)。

### M-A4 [Mac] launchd 守护进程与重启
- 排查:常驻 daemon/agent 的 plist、启动方式、改代码后的重启动作。
- 判据:改了它 import 的模块没有 `launchctl kickstart -k`(ESM 加载时求值,老代码继续跑);被收养的孤儿进程。
- 事故:claude-gui bot 常驻代理(2026-09-03)。

### M-A5 [Both] 安装脚本往系统 Python 装包(PEP 668)
- 排查:安装/部署脚本与 README 里的 `pip install`、`python3 -m pip install`;项目各入口用的是哪个解释器(裸 `python3`、`/usr/bin/python3`、venv、pyenv shim)。
- 判据:对系统/发行版 Python(Homebrew、Debian/Ubuntu、Fedora)直接 `pip install` 而没有 venv、`--user`/`--break-system-packages` 或 pipx → 装机在 `externally-managed-environment` 处中断;入口用的解释器与 pip 用的不是同一个(pyenv/conda 混装、`/usr/bin/python3` 硬编码)→ 装了也 import 不到;装完没有 import 自检。
- 机制:PEP 668 标记文件 `EXTERNALLY-MANAGED` 让 pip ≥23 拒绝写系统 site-packages;用户 site 与 venv 不受影响。
- 事故:claude-tgbot 2026-09-04(另一台 Mac 的 Homebrew Python,install.sh 第②步中断)。
- 真机:全新 Homebrew Python 的机器跑一遍安装脚本;混装 pyenv 的机器看 `which -a python3` 与 import 自检。

### W-A13 [Win] 包管理器装的 CLI 是 `.cmd` 壳,SDK 要真二进制;壳包可能残缺
- 排查:给 SDK 的 CLI 路径怎么来的;壳包识别(文件头、体积);残缺壳的处理;日志能否看出实际用的哪个二进制。
- 判据:SDK 拿到 `.cmd` 或 null(回落自带旧版);只看文件头不看体积(慢源中断留几百字节残缺 exe 被放行);scoop/pnpm 布局没有提示。
- 机制:npm 包是引导壳,真二进制在包内。
- 事故:claude-gui r106;r108 建-2;npm 引导壳(npmmirror 16–20KB/s)。
- 真机:日志里实际二进制路径与 `--version` 一致;能力探测(如快照 flag)生效。

### W-A14 [Win] `.bat` 模板里调 `.cmd` 不加 `call`
- 排查:生成/内置的 `.bat/.cmd` 模板。
- 判据:`npm`/`npx` 等行前没有 `call`(cmd 跳到另一个批处理不返回,后续命令全丢)。
- 事故:claude-gui v0.2.147。

### W-A15 [Win] PowerShell:执行策略、输出编码、网络代理
- 排查:所有 `powershell` 调用的参数;内联 `-Command` 里调用的命令;`irm`/`Invoke-WebRequest` 的代理;给用户的文档命令。
- 判据:缺 `-ExecutionPolicy Bypass`;内联里裸调 `npm/npx/claude`(挑到 .ps1 被拦);文档教用户在 PowerShell 敲 `npx …`;PS 网络请求依赖 `HTTP_PROXY` env;输出编码没设 UTF-8(见 G-1)。
- 机制:Restricted 只拦 `.ps1` 文件,但 npm 系命令的 shim 就是 .ps1;PS 5.1 只认 WinINET 代理。
- 事故:claude-gui v0.2.63;2026-09-01;r85。

### W-A16 [Both] 子进程不继承系统代理
- 排查:起 git/npm/curl/node fetch 的地方有没有注入代理 env;代理探活对非回环地址的处理;本机 TUN 模式会不会掩盖问题。
- 判据:开系统代理(非 TUN)的机器上该功能失败;探活把企业代理当死代理删掉;开发机常年 TUN 让代理路径从未被真正测过。
- 事故:claude-gui r29;r48 ②;2026-09-03。

---

### X-A7 [Both] 「显示用截断」参与相等判据 → 长文本路径下判据失效(重复/误判)
- 排查:同一份数据同时用于"显示(有长度上限)"和"幂等/去重判据(比较相等)"的地方——尤其"宿主不截断、前端截断"这种两端不同口径的字段;上限按 UTF-16 码元还是字节;截断点是否可能落在代理对中间。
- 判据:上限值之下的样例全绿、刚好越界的样例行为突变(多一条/少一条/判重失败);同一份数据两个消费者拿到的长度不同却直接 `===`;CJK 与 emoji 比 ASCII 更早触发(中文 1 字 = 1 码元但 UTF-8 3 字节,emoji = 2 码元)。
- 机制:前端为防坏值灌爆视图加的上限,会让"看文本是否相等"这类判据在越界后必然为假;比较口径必须与显示口径解耦(要么都不截断,要么两侧按同一上限截断)。
- 事故:zotero-claudian R14(2026-09-14):`inFlight.userText` 宿主不截断、UI 截 4000 码元 → 发送方**自己**的视图里重复一条用户气泡(实测 4001 码元起,emoji 更早);21 条既有用例全绿掩盖了它,靠"直调真源码的长文本复现脚本"才抓到。
- 真机:粘一段 >4000 中文字符(含一个 emoji 落在第 4000 码元处)发一轮,看用户气泡是否只有一条。

### W-A17 [Both] 停用/卸载路径没清掉的延迟定时器会在停用后继续起子进程
- 排查:插件/服务停用路径(shutdown/unload/dispose/onShutdown)里是否 `clearTimeout`/`clearInterval` 了所有"稍后再跑"的定时器(尤其失败重试、冷启重探、退避重连这类);对照同文件里已做对的同类收尾。
- 判据:停用代码只注销观察者/关监听、没有清定时器;而定时器回调里有 spawn/网络请求;停用后仍能观察到新的子进程或请求。
- 机制:定时器持有模块闭包,UI 引用没了不代表定时器没了;停用只清 UI 侧状态时,回调照常触发。
- 事故:zotero-claudian R15(2026-09-14):15s 重探定时器未在 `stopCliStatusWatch` 清理(同文件 `stopReaderContextWatch` 已做对,属漏抄);停用插件后仍会起 1–3 个 `claude --version`。审查报告里判"必修"。
- 真机:触发一次重试窗口(如探测超时)后立刻停用插件,看任务管理器 15s 内是否冒出新的子进程。

## B 路径与文件系统

### W-B1 [Win] 分隔符与硬编码路径
- 排查:`split('/')` 取文件名;`${a}/${b}` 拼路径;`path.posix`;`/tmp`;前端做路径字符串运算的地方。
- 判据:任一出现在会在 Windows 执行的代码路径上。
- 事故:claude-gui 路径分隔符显示;WINDOWS-REVIEW-0.2.370 低-1。

### W-B2 [Win] HOME 与 USERPROFILE;APPDATA 缺省;测试的 HOME
- 排查:`process.env.HOME` 读点;候选目录对 `APPDATA/LOCALAPPDATA` 的缺省;单测里设 `HOME` 的地方。
- 判据:直接读 HOME;缺省不回落;测试只设 HOME 不设 USERPROFILE(Windows 上会写真实用户目录)。
- 事故:claude-gui r48 ④/r49a。

### W-B3 [Win] `Path` vs `PATH`
- 排查:`{...process.env}` 展开后读 `PATH` 的地方;用 PATH 做缓存 key 的地方。
- 判据:只读 `PATH` 没有 `Path` 回落(展开成普通对象后键名大小写不再无关)。
- 事故:claude-gui r108。

### X-B4 [Both] 大小写不敏感文件系统与路径当 key
- 排查:用路径做 Map key、hash、比较的地方;断言"返回值等于盘上真名"的测试;前缀检查。
- 判据:两侧没有同一口径的 canonical(realpath + 大小写归一);前缀检查 `startsWith(HOME)` 没带分隔符(`/Users/x2` 绕过);APFS 与 NTFS 默认都不区分大小写,但 git/Linux CI 区分。
- 事故:claude-gui r108;r48 ③;2026-05-29。

### W-B5 [Win] CRLF
- 排查:切分子进程输出/文件内容的 `split('\n')`;`^…$` 正则;文件内容比较与生成物;`.gitattributes`。
- 判据:行尾会带 `\r`;比较两端换行口径不同;仓库没有 eol 规则(Windows 检出 autocrlf)。
- 事故:claude-gui r109/r111。

### W-B6 [Both] ESM 动态 import 与脚本入口判断
- 排查:`import(<路径字符串>)`;`pathToFileURL(process.argv[1]).href === import.meta.url` 这类入口判断。
- 判据:路径没经 `pathToFileURL`(Windows 盘符被当 URL scheme);入口判断没经 realpath(软链下静默 no-op)。
- 事故:claude-gui gen-release-notes / gen-changelog。

### W-B7 [Win] Windows 路径形态的正则
- 排查:匹配临时目录、后台任务输出、用户目录下路径的正则;从 `file://` URL、日志/子进程输出里"抓一段路径"的正则(抓到的可能是 URL 形态而不是盘符形态)。
- 判据:只认 `/`;假设有 mac 才有的路径段(如 `-uid`);从 `file:///C:/…` 抓出来的 `/C:/…` 直接当本地路径喂给 fs —— Windows 的绝对路径是 `C:\…`,带前导 `/` 的捕获值读不到,而且因为"正则命中了"往往会跳过为这种情况准备的回落分支(回落只在抓不到时才走)。
- 机制:`file:///abs/path`(POSIX)与 `file:///C:/path`(Windows)前缀层数相同;剥掉 `file://` 之后一侧是绝对路径、另一侧是 `/C:/…`,Windows 的路径解析不会把它当盘符路径。
- 事故:claude-gui 后台任务可视化;v0.2.129;claude-gui 0.2.379 审查(`server/routes/subscription-usage.js` 的 `/insights-report` 从 stdout 抓 `file://` 读回 HTML;Windows 面未真机验证,按判据收)。
- 真机:Windows 上跑一次该功能(如 /insights 报告),看返回的是内容还是"未找到生成的报告文件";同时看抓到的路径是 `/C:/…` 还是 `C:\…`。

### W-B8 [Both] 临时文件
- 排查:每回合写临时文件的地方及其清理;临时目录路径含空格的传参;临时文件与目标是否同卷。
- 判据:没有清理;清理没包 try(Windows 上文件被占会抛);跨卷 rename(EXDEV)。
- 事故:claude-gui C5;RESEARCH-win-audit-0250。

### W-B9 [Win] 文件被占用与读半截
- 排查:`unlink/rename` 失败分支;读配置失败时对状态基线的处理;"自写标记"有无时效。
- 判据:把 EBUSY/EPERM 归因成别的错误;失败后记录已删导致孤儿;读失败推进了状态版本;标记永久悬挂。
- 事故:claude-gui r58 I1;WINDOWS-REVIEW-0.2.370 中-2/低-3。

### W-B10 [Win] 垃圾文件名、ADS、带空格路径
- 排查:目录/压缩包的"单根"判定;路径校验对 `:`;生成 Windows 绝对路径引用的地方。
- 判据:没过滤 `Thumbs.db/desktop.ini/ehthumbs.db`;没拒绝 ADS 冒号;带空格/反斜杠的引用没真机验过。
- 事故:claude-gui r48 ①;WINDOWS-REVIEW-0.2.370 低-2。

### W-B11 [Win] Tauri `resource_dir()` 的 `\\?\` 前缀
- 排查:Rust 侧把路径传给 node/子进程的地方。
- 判据:没剥 `\\?\`(非 C 盘/网络盘打不开)。
- 事故:claude-gui v0.2.55。

### W-B12 [Both] hook 命令里的重定向;控制台编码
- 排查:写进用户配置的 hook 命令;Python 子脚本的 print。
- 判据:cmd 风格 `>NUL`(Git Bash 下落盘成 `NUL` 文件)或 `/dev/null` 混用;打印 emoji 到 cp936 控制台。
- 事故:claude-gui 2026-06-16;全局 learnings。

### M-B1 [Mac] `/tmp` `/var` 是 `/private` 的软链
- 排查:比较/哈希/前缀检查路径的地方;把 `os.tmpdir()` 结果与用户给的 `/tmp/...` 比对的地方。
- 判据:一侧 realpath 一侧没有 → 不相等;CLI 按 cwd 算的 hash 目录名与 GUI 算的对不上。
- 事故:claude-gui 标题 cwd 隔离(/tmp→/private/tmp)、resolveWorkspacePath。

### M-B2 [Mac] 文件监听的 fd 上限与 fsevents
- 排查:`fs.watch`/chokidar 的监听范围与版本(v4 无 fsevents,每目录一个 fd)。
- 判据:监听上千目录 → EMFILE;没有 polling/深度限制。
- 事故:claude-gui 2026-05-29(`~/.claude` 上千 jsonl)。

### M-B3 [Mac] 应用包内的资源布局
- 排查:从应用包定位资源/版本文件的代码。
- 判据:mac 是 `Contents/Resources/_up_/…`、主程序在 `Contents/MacOS/<Cargo 包名>`;Windows 没有 `resources\` 层(见 W-E1);`open -a` 会掩盖主程序名错误。
- 事故:claude-gui 2026-08-26。

### M-B4 [Mac] 文件名 Unicode 归一化
- 排查:比较来自 Windows/压缩包/网络的中文文件名与本地列目录结果的地方。
- 判据:mac 存 NFD、Windows 存 NFC,字节不同视觉相同 → 找不到文件。
- 事故:预警级(未踩)。

### X-B5 [Both] 平台专属垃圾/元数据文件
- 排查:导入目录/压缩包时的"单根"或"文件清单"判定。
- 判据:mac 的 `.DS_Store`、`__MACOSX/`、`._*` AppleDouble 与 Windows 的 `Thumbs.db/desktop.ini` 未过滤。
- 事故:claude-gui r48 ①(Windows 侧)。

### W-B13 [Win] POSIX 模式位在 Windows 上只映射读/写两档:去掉写位 = 置只读属性,后续写入全失败
- 排查:所有 `IOUtils.setPermissions(path, mode)` / `nsIFile.setPermissions` 调用点,以及把 `0o600`/`0o400`/`0o700` 当"权限收紧"用的地方;`mode` 是否含写位(`& 0o200`)。
- 判据:①`mode` 不含任何写位(如 `0o400`/`0o500`)→ Windows 上 `_wchmod` 会**置 `FILE_ATTRIBUTE_READONLY`**,随后同文件的追加写(`appendOrCreate`)、`unlink`、`rename`/覆盖兜底全部失败——"收紧权限"直接把功能锁死;②注释/文档声称 `0o600` 能"让同机其他用户不可读"——Windows 上读权限由 ACL 决定,该位只影响只读属性,承诺不成立(说法问题);③`mode > 0o777` 或目标不存在 → 抛错,调用方没有 catch。
- 机制:`nsLocalFileWin::SetPermissions` 把 `PR_IRUSR|…` 折成 `_S_IREAD`、`PR_IWUSR|…` 折成 `_S_IWRITE` 后交 `_wchmod`;MSVC CRT 的语义是"没给 `_S_IWRITE` 就置只读,给了就清掉"。所以 `0o600` 与 `0o644` 在 Windows 上是同一个结果(清只读),而 `0o400` 与 `0o600` 是生死之别。
- 事故:zotero-claudian R8–R11 审查(2026-09-11):会话索引/历史每轮追加后都 `setPermissions(path, 0o600)`(`src/modules/sections.ts:1467-1478`),被列为"最需要核实的一条";查上游 `xpcom/io/nsLocalFileWin.cpp:2677-2705` 判定写位保留、**不变只读**(非缺陷),但由此发现"将来改成 0o400 就会静默毁掉会话历史写入"的悬崖,建议用 `assert(mode & 0o200)` 单测锁住。
- 真机:Windows 上让该功能连写 3 次以上(追加型场景),看文件是否随每次变长、`attrib <文件>` 有没有 `R`;以及调试日志里有没有 chmod 失败行。

### X-B6 [Both] `nsIFile.isWritable()` 对目录在 Windows 上恒为 true(只读属性,不读 ACL)
- 排查:拿 `isWritable()` / `isReadable()` 当"能不能写/能不能读"用的地方——权限校验、诊断报告的可写性字段、安装前检查。
- 判据:被测对象是**目录**(或可能解析成目录)且在 Windows 上 → 该值恒为 `true`,与真实可写性无关;报告/校验里出现 `writable=true` 却被 ACL 拒绝写,即命中。
- 机制:`nsLocalFileWin::IsWritable` 先 `IsDirectory(aIsWritable)`(把"是不是目录"写进同一出参),紧接 `if (*aIsWritable) return NS_OK;` 提前返回——目录一律判可写;只有文件才去读 `FILE_ATTRIBUTE_READONLY`。macOS/Linux 是 `access(path, W_OK)` 真检查。
- 事故:zotero-claudian R9–R11 审查(2026-09-11):`/diag` 的 `workspace: … writable=` 字段(`src/modules/sections.ts:1794-1800`)在 Windows 上对任何已存在的工作区目录恒真——该字段正是为 Windows 排障加的,结果在 Windows 上说谎。
- 真机:Windows 上把被测目录设成 ACL 拒绝写(或用只读介质/受控文件夹),同一份诊断输出里的该字段不得为 `true`;macOS 上 `chmod 500` 的目录必须为 `false`。

---

## C 原生模块与运行时

### W-C1 [Both] 原生模块 ABI
- 排查:顶层 `import` 原生模块(node-pty 等)的地方;用户系统 node 版本与构建期 ABI。
- 判据:加载失败让整个后端起不来而不是功能降级;mac 上还有"应用内 node 带 Team ID 校验拒绝第三方 .node"(M-A1)。
- 事故:claude-gui v0.2.53。

### W-C2 [Both] Node 版本地板
- 排查:新依赖/升级依赖的 `engines`;app 自己的地板与启动自检。
- 判据:依赖要求高于 app 地板且没有告警(公开版用户自带 Node)。
- 事故:claude-gui r57 F1。

### W-C3 [Both] 能力探测缓存
- 排查:按二进制路径缓存的探测;同一台机是否有多条路径(壳与包内 exe;mac 的多安装切换)。
- 判据:只预热一条;日志版本号被当实时值。
- 事故:claude-gui r108。

### X-C4 [Both] 构建产物陈旧
- 排查:构建脚本有没有清 `dist`/`.vite` 缓存;装机后版本握手。
- 判据:前端改动"修了没生效"、health 报新版本但行为旧 = 旧 bundle;升级没完全退出旧后端进程(界面新、后端旧)。
- 事故:claude-gui 0.2.263(vite 缓存);stale backend(6677 旧进程)。

---

## D 渲染引擎(dev Chromium / WebView2 / WKWebView / iOS Safari)

### D-1 [Both] 原生 `confirm/alert`
- 排查:`window.confirm`、`window.alert`、裸 `confirm(`。
- 判据:出现即问题(Tauri 两个 webview 都禁用)。
- 事故:claude-gui 删会话/删 agent。

### D-2 [Both] 平台判定与快捷键提示
- 排查:`navigator.platform`;快捷键文案(Ctrl vs Cmd)。
- 判据:前端自判平台而不是用后端下发。
- 事故:claude-gui r106。

### D-3 [Win] 窄面板与更宽的字体度量
- 排查:新增的横向 flex 行(左文右按钮)。
- 判据:不允许换行且左列可被压到零宽;把预览压到 ~280px 看一眼。
- 事故:claude-gui r112。

### D-4 [Both] 引擎分裂
- 排查:裸 `vw/vh` 定尺寸;portal 到 body 的 fixed 菜单坐标(是否 ÷ 页面 zoom);模态挂载位置(祖先残留 transform);sticky footer;`<summary>` 的 display;`<details>` 展开控制。
- 判据:尺寸/坐标假设了某一引擎的 zoom 行为(WKWebView 已把 zoom 折进 vh,Chromium/WebView2 不折);模态渲染在带 transform 的祖先内;WKWebView 上 `<summary>` 设 flex/grid 禁用原生切换;dev 复现不了的真机 bug 用 Chromium 行为推根因。
- 事故:claude-gui 第 222 轮卡点 5;0.2.255 审计批;v0.2.147。

### D-5 [Both] 内存与崩溃自愈
- 排查:大列表是否全量渲染;大图是否双份内存;WebView2 `ProcessFailed`/WKWebView 进程终止有无处理。
- 判据:多窗格 + 长历史 + 大图时内存无上限;崩了不自愈。
- 事故:claude-gui r29;r58 S2。

### D-6 [Mac] 原生层"吞事件"的指控
- 排查:任何"WKWebView 原生层不给事件"的结论。
- 判据:没有同版最小复现就下的结论(claude-gui 的右键案:三层最小复现证明事件全进 DOM,真凶是自家手势时序 + 陈旧产物)。
- 事故:claude-gui 文件树右键翻案。

### D-7 [Both] 手机 Safari
- 排查:移动端布局的输入框字号、覆盖层高度来源、`dvh`。
- 判据:输入框 <16px 聚焦自动放大不回退;覆盖层高度依赖测量值;裸 dvh 在地址栏伸缩时跳动。
- 事故:claude-gui 0.2.256。

### D-8 [Win] 截图热键
- 排查:`ms-screenclip` 完成/取消的判定;组件缺失的处理。
- 事故:claude-gui 0.2.225。

---

## E 分发 / 签名 / 安装 / 网络

### W-E1 [Win] Windows 产物布局
- 排查:安装根目录布局假设(有没有 `resources\` 层);主程序名来源(Cargo 包名 vs productName);`tasklist`/安装器主杀的进程名;相关测试的断言是抄实现还是从事实源推导。
- 判据:任何一处从 mac 类推而未真机取证。
- 事故:claude-gui 2026-08-26。

### W-E2 [Win] 安装包形态与文案;自动更新退出路径
- 排查:`bundle.targets` 与 release 正文/README 的一致性;updater 退出是否经过清理路径。
- 判据:文案提到不存在的产物;`process::exit(0)` 绕过退出事件(待真机)。
- 事故:claude-gui r109/r111;发布后验证债。

### W-E3 [Win] 安装器的检测盲区与 winget
- 排查:安装器候选目录;`winget` 调用有无探测兜底。
- 判据:提权进程读不到当前用户 PATH;`winget` 不存在时卡死。
- 事故:claude-gui v0.2.98/147。

### W-E4 [Both] 后端自身 fetch 与系统代理模式
- 判据:系统代理模式下拉列表/更新失败而 TUN 正常。
- 事故:claude-gui 2026-09-03(待办)。

### W-E5 [Win] 用户名带空格的路径
- 真机:找一台带空格用户名的机器跑主链路。

### W-E6 [Both] 包镜像与平台分包
- 排查:CI 发布后的镜像同步动作;安装器对平台包缺失的处理;`optionalDependencies`。
- 判据:只 GET 不触发同步(npmmirror 要 PUT syncs);平台包缺失被静默跳过;大平台包在镜像上极慢导致中断残缺。
- 事故:claude-gui 2026-08-26;npm 引导壳。

### W-E7 [Win] CI WiX 下载 504
- 判据:重跑失败 job 即可。

### W-E9 [Both] 权限/模式异常先查配置残留
- 排查:用户配置文件里的残留键。
- 事故:claude-gui r48 audit-sdk。

### M-E1 [Mac] 签名、复制方式与 FDA
- 排查:构建产物的签名身份(adhoc 还是持久证书);装机复制方式(`cp -R` vs `ditto`);ditto 前有没有删旧目录;`codesign --verify --deep --strict` 有没有跑。
- 判据:adhoc 签名(每次构建 cdhash 变,TCC 记录失效,FDA "勾选实为死",子进程 openat 卡 30s);`cp -R` 破坏签名;ditto 叠加进旧 bundle 残留旧文件 → verify 报 sealed resource missing。
- 事故:claude-gui adhoc TCC csreq;持久自签根治 FDA;装机反复踩。
- 真机:装完 `codesign --verify --deep --strict` 过;FDA 勾选后子进程读受保护目录不卡。

### M-E2 [Mac] Gatekeeper / quarantine / 公证
- 排查:分发说明、dmg 重打包、下载渠道。
- 判据:未公证 app 报"已损坏"(macOS 15 起右键打开也不放行);dmg 经非浏览器渠道传输更易带隔离标记;文档里的 `xattr` 没写 `/usr/bin/` 绝对路径。
- 事故:claude-gui README/release notes。

### M-E3 [Mac] 钥匙串与签名身份
- 排查:构建脚本对签名钥匙串的解锁与搜索列表;签名失败的回落。
- 判据:`errSecInternalComponent`(钥匙串锁着)、`item could not be found`(钥匙串掉出搜索列表)时静默回落 adhoc → 装上 FDA 失效。
- 事故:claude-gui release.local.sh 多次。

### M-E4 [Mac] 架构与系统版本
- 排查:发布产物的架构;README 的支持范围。
- 判据:只出 Apple Silicon 包却没写明;Intel 用户报打不开。
- 事故:claude-gui README。

### X-E5 [Both] 开发机代理环境掩盖网络问题
- 排查:任何"本机能通"的网络结论。
- 判据:开发机常年 TUN(fake-IP 劫持直连,SSH/HTTPS 间歇被拦);`Could not resolve host` 先查解析器不查代理;"走代理通"≠"需要代理"。
- 事故:claude-gui 代理 vs DNS 误诊;GitHub 网络操作规则。

---

## F 排查方法

### F-1 [Both] 在另一平台模拟目标平台分支
- 用注入式纯函数(platform / fs / env / now / probe / 路径拼接口径)造对方平台的布局;"注入函数被调用 ≥1 次"这种断言可被独立满足,别当强锁。

### F-2 [Win] 引号/命令行改动必跑往返模拟
- `scripts/crt-roundtrip.mjs <module>` 对真源码跑;手推会漏(r111 漏了一半)。

### F-3 [Both] 跨平台分支没在该平台跑过就当它是坏的;断言从事实源推导不抄实现;写另一平台分支先问"是不是从本机平台类推的"
- 事故:claude-gui 2026-08-26。

### F-4 [Both] 改共用 helper 的返回形状,每个消费者按新形状逐个判,不按"与本 bug 无关"回滚
- 事故:claude-gui r110 remote-control。

### F-5 [Both] 真机验证单写法
- 每条:操作 / 看什么 / 什么算过。给出日志位置(Windows `%USERPROFILE%\<app>\server.log`、mac `~/Library/Logs` 或应用自定日志)、终端复现源码的命令、历史欠账清单位置。

### F-6 [Both] dev 预览 ≠ 真机
- dev 预览是 Chromium,真机是 WKWebView/WebView2;dev 复现不了的真机 bug,根因靠"项目内能用 vs 不能用"的差分或真机坐实,禁止拿 Chromium 行为推断。

### F-7 [Both] "同代码不同行为"先怀疑陈旧产物
- 改了还复发、health 报新版本但行为旧、dev 读源码不复现 → 先查改动进没进 HEAD/产物(见 X-C4)。

---

## G 预警(未踩;验实后搬进 A–E 给正式 ID)

### G-1 [Win] 中文用户名 / 中文路径 + 子进程输出编码
- 排查:所有解析子进程 stdout 的地方(`where`、cmd 内建、未设输出编码的 PowerShell、注册表 PATH、进程列表);`encoding:'utf8'` 的读取。
- 判据:中文 Windows 上这些输出是 OEM cp936 字节,按 UTF-8 解会出 U+FFFD → 路径不存在/命令找不到/进程名乱码。
- 真机:中文名账户上装 CLI,看日志里解析出的路径是否可读;添加外部服务;看进程面板。

### G-2 [Win] 生成的 `.bat` 含非 ASCII 且按 UTF-8 写盘
- 排查:所有写 `.bat/.cmd` 的地方。
- 判据:内容含中文/符号、文件按 UTF-8 写、首行没有代码页处理 → cmd 按 cp936 读成乱码;带 BOM 首行命令失败。

### G-3 [Both] 用户手编 JSON 带 BOM
- 排查:所有 `JSON.parse(readFileSync(用户配置))` 读点及 catch 分支。
- 判据:BOM 让解析抛错被吞成"文件不存在",表现为配置莫名重置且无日志。

### G-4 [Both] zip 内非 ASCII 文件名
- 排查:解包路径对条目名编码的处理。
- 判据:Windows 资源管理器压缩的包条目名是 cp936、无 UTF-8 标志;mac 压缩带 `__MACOSX/`。

### G-5 [Win] cmd 的 `%VAR%`/`!VAR!` 与 PowerShell 内联插值
- 排查:进入 cmd 命令行与 `powershell -Command` 字符串的用户文本。
- 判据:`%…%` 在引号内仍展开;`!…!` 只在 `/v:on` 展开;PS 内联里 `$`、反引号、`"` 被解释。

### G-6 [Both] 正则 / WQL / `-like` / sh 里拼路径或用户输入
- 排查:`new RegExp(变量)`、WQL `like`、`-like`、`sh -c "${x}"` 的拼接来源。
- 判据:拼进去的是路径(反斜杠是转义)或含通配/引号的文本。

### G-7 [Both] `localhost` 与 `::1`
- 排查:文档/脚本/客户端里写 `localhost` 的地方;服务监听地址。
- 判据:系统把 `localhost` 先解析成 `::1` 而服务只听 `127.0.0.1`。

### G-8 [Both] OneDrive/iCloud 占位文件、长路径、保留设备名
- 排查:项目目录可能在云同步文件夹;深路径;创建文件名的校验。
- 判据:读"仅联机"占位文件阻塞;Windows 路径 >260 未开长路径;文件名为 `CON/NUL/AUX/COM1` 或结尾点/空格;iCloud 的 `.icloud` 占位。

### G-9 [Both] 符号链接权限、执行位、`sh` 依赖
- 排查:`fs.symlink`;`.sh`/`.command`/shebang 脚本;hook 里的 `bash -c`。
- 判据:Windows 文件软链需开发者模式(目录 junction 不需要);脚本无执行位;hook 依赖 Git Bash 存在;mac 上 `.command` 首次需右键打开。

### G-10 [Both] 信号语义:Windows `SIGTERM` 硬杀;提权进程;mac 沙箱
- 排查:对子进程发信号的地方;杀失败分支;受 TCC/沙箱限制的目录访问。
- 判据:写到一半的文件可能截断;提权进程普通权限杀不掉且无提示;子进程访问 Documents/Desktop 触发 TCC 弹窗或静默拒绝。

### G-11 [Both] 防火墙首次监听弹窗
- 排查:监听 `0.0.0.0` 的地方及用户被拒后的提示。
- 判据:用户点取消后局域网设备永远连不上且界面无解释(Windows 防火墙、mac 的"允许传入连接")。

### G-12 [Win] 经 `.cmd` 壳的命令行长度门要给壳的二次展开留余量
- 排查:所有对「经 cmd.exe 起 `.cmd`/`.bat`」的调用做长度上限判定的地方;判定用的上限值是不是裸 8191;目标 `.cmd` 是不是 npm cmd-shim(内容含 `"%_prog%" … %*`)。
- 判据:上限直接取 8191、没有为壳自身展开预留余量——外层命令行刚好卡在上限内时,壳把 `%*` 展开进 `"%_prog%" "%dp0%\node_modules\…\cli.js" %*` 之后那一行仍受 8191 约束,会在批处理内部二次截断,门等于白设;旧的「原文 7000 字面量」门歪打正着留了约 1200 余量。
- 机制:8191 约束的是「cmd 处理的每一条命令行」,不是「进程链上只算一次」;`%*` 展开发生在壳内部,长度只增不减。
- 事故:claude-gui r113 发版前审查(0.2.376,2026-09-06,建议-3;未真机复验,先按预警收)。
- 真机:拿一条把外层刚好顶到上限的 prompt 派任务,看目标程序收到的参数是否完整;完整则可去掉余量,截断则按壳前缀实测值下调上限。

### G-13 [Win] Gecko/XPCOM `Subprocess` 不是 node `child_process`:command 必须绝对路径;cmd.exe 有专属特例;其余参数会被二次转义
- 排查:Zotero / Thunderbird / 任何 XUL 宿主里 `Subprocess.call({command, arguments})`(`resource://gre/modules/Subprocess.sys.mjs`)的每一处调用点;`command` 是裸命令名还是绝对路径;要起 `.cmd/.bat` 时传的是 `['/c', 整行]` 还是 `[程序, '/C', 整行]`;`command` 指向的是不是 reparse point(符号链接)。
- 判据:①`command` 不是绝对路径(如 `'cmd.exe'`、裸 `'git'`)→ Windows 实现 `subprocess_win.sys.mjs::isExecutableFile` 在 `!PathUtils.isAbsolute(path)` 时返回 false,`Subprocess.sys.mjs` 直接抛 `File at path "…" does not exist, or is not executable`(errorCode=ERROR_BAD_EXECUTABLE),进程根本没起;②要经 cmd.exe 时,worker 只在 `command` 匹配 `/\\cmd\.exe$/i` **且** `arguments.length === 3` **且** `arguments[1]` 匹配 `/^(\/S)?\/C$/i` 时走 cmd 特例(对 `arguments[2]` 原样补一层外层引号),不命中就走通用分支把每个参数按 MSVCRT 规则 `quoteString`,而 stdio 的 `.cmd` 目标被点名时又会自己改成 `['cmd.exe','/s/c', '"' + args.join(' ') + '"']`;③`command` 指向 reparse point(Windows 符号链接)时 `isExecutableFile` 也返回 false(`IOUtils.stat` 的 type 为 `"other"`)。
- 机制:node 会自己按 `COMSPEC`/PATH 找 `cmd.exe` 并按 CRT 规则拼命令行;Gecko 是 `CreateProcessW(lpApplicationName=command, lpCommandLine=args.join(' '))`,既不搜 PATH,也不存在 `windowsVerbatimArguments` 这类开关——预转义过的整行会被 `quoteString` 再转义一次,而 cmd.exe 不认 CRT 转义。
- 事故:zotero-claudian 0.1.0-rc2 发版前审查(2026-09-11,致命-1/-3):win32 `.cmd` 通道传 `file:'cmd.exe'` + `['/d','/s','/c', 已 quoteWinArg 转义的整行]`,上游源码(esr115/esr140 两版同读)判定必失败;`crt-roundtrip.mjs` 对该项目真源码跑 15/15 不还原,仅在整行外再包一层引号则 15/15 还原。未真机复验,先按预警收。
- 真机:Windows 上让 CLI 解析结果落 `.cmd` 壳,发一轮对话,看 Zotero 调试日志里 `procError` 的 `reason`/`stderrTail` 原文;若为 `File at path "cmd.exe" does not exist, or is not executable` 即命中①,`不是内部或外部命令 / 系统找不到指定的路径` 即命中②。另:`%USERPROFILE%\.local\bin\claude.exe` 若是符号链接,看是否被报成不可执行(命中③)。

### G-15 [Win] 诊断/探针采集丢弃子进程的 stderr 与 spawn 异常原文,报告无法定位 cmd 通道类故障
- 排查:所有"探针/自检/诊断报告"里跑子进程的地方:spawn 的 catch 分支把异常原文放哪了(stderr?还是只 log 后返回 `{ok:false}`);stdout 管道读走的同时 stderr 是丢弃还是留存;失败原因有没有进最终给用户看的文本。
- 判据:探针返回值只有 `{ok:false}` / `{timedOut}` 这类布尔,失败时用户看到的文本是"无法执行""失败"这类无信息量的话,而异常原文与 stderr 只进了应用内日志(用户按流程不会去翻)→ 命中。最典型:Windows 上 cmd 通道/`.cmd` 壳类故障的唯一判据就是 Gecko 抛的原文(`File at path "…" does not exist, or is not executable` / `不是内部或外部命令`)。
- 机制:探针的定位是"让用户贴一段输出就能定位根因",而失败原文在 spawn 抛错对象和 stderr 里,不在 stdout 里——只读 stdout 的探针天然取不到它。
- 事故:zotero-claudian R9–R11 审查(2026-09-11,建议-1):`/diag` 的 `cli:` 行失败时只输出 `(error: 无法执行)`,而 `runProbe`(`src/modules/sections.ts:414-438`)把 spawn 异常的 `String(err)` 只写进 `Zotero.debug`、stderr 直接读掉丢弃(`:452-453`)——正是 G-13 那族故障最需要的一手信息被丢在报告之外。
- 真机:把可执行路径指向一个不存在/不可执行的路径跑一次诊断,报告里应能看到上游原文而不是"无法执行"(否则就是命中)。

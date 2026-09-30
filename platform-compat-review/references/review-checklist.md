# 跨平台兼容性核对清单 + 报告模板

> 用法:每轮审查逐条过。每条是一个**要回答的问题**,不是要套的修法;答案落到 `文件:行` 与"为什么没问题 / 为什么有问题"。括号里的 ID 指向 `checkpoints.md`,判据以那里为准;[scan] 表示 `scripts/scan.mjs` 会先列出候选位置;[Win]/[Mac]/[Both] 标明哪一侧要看。
>
> 深度要求:凡写着"列表"的条目,必须 **grep 全仓列出清单**并逐个标注(平台可达性 / 参数来源),报告附表;不要抽查两处就下结论——历史上漏掉的都是"没列全"。

## 0. 定范围与基线
- [ ] 基线 diff:`git diff <上一发布 tag>..HEAD --name-only`,排除 `tests/`、`.devflow/`、`CHANGELOG.md`、生成物;列出本轮触及的文件;写明审的是哪一侧平台。
- [ ] 读上一份审查报告的"已核对无问题",本轮只报 diff 引入或触及的;误报也写进"已核对"。
- [ ] 跑 `node scripts/scan.mjs --base <tag> --platform all`,逐条核实;命中的不是问题也要写一句为什么。
- [ ] 本轮改动里有没有"从本机平台类推到另一平台"的分支?每一处都问一遍(F-3)。

## A 进程与命令行
- [ ] **列表**:全仓 `spawn`/`execFile`/`execFileSync`/`spawnSync`/`pty.spawn`/Rust `Command::new` 的调用点,每条标:第一参来源(常量 / 解析结果 / 用户输入)、在 win32 与 darwin 分别是否会走到、参数里有无可控内容。(W-A1/A2/M-A1)
- [ ] [Win] 第一参可能落到 `.cmd/.bat`/无扩展名 shim 的,是否都经 cmd.exe?交给 SDK/库的路径是不是真 exe?(W-A1/A13)
- [ ] [Win] 经 cmd.exe 的每一条:参数可能出现 `< > | & ^`、空格、内嵌 `"`、结尾 `\`、`\"` 中的哪些?拼法是否 verbatim 全套?统一引号函数的**全部消费者**是否都换了?(W-A2)[scan]
- [ ] [Win] 本轮动过引号/拼接 → `scripts/crt-roundtrip.mjs <module>` 对真源码跑,15 行全 ✅(F-2)
- [ ] [Win] 进入命令行的用户文本:`%`、换行、超长?走 argv 还是 stdin/临时文件?有无长度上限?(W-A3)
- [ ] [Win] node-pty:第二参形态、`file` 绝对路径、winpty 那条路(W-A4)
- [ ] [Win] `wmic` 是不是首选?(W-A5)[scan]
- [ ] [Win] `SHELL`/`-lc`/`/bin/bash`/`lsof`/负 pid 信号在 win32 会走到吗?(W-A6/A9)[scan]
- [ ] [Mac] 图形应用起的进程能找到 node/git/uv/brew 吗?PATH 来自哪里?有没有 login shell 解析或固定候选?应用内自带 node 会不会抢 PATH?(M-A1)[scan]
- [ ] [Mac] 调用 `xattr`/`python`/`sed` 等系统命令写绝对路径了吗?(M-A2)[scan]
- [ ] [Mac] 项目内 shell 脚本/CI/测试脚手架有 GNU 专有写法(`timeout`、`sed -i`、`readlink -f`)吗?(M-A3)[scan]
- [ ] [Mac] 改了常驻 daemon 依赖的模块,重启动作在流程里吗?(M-A4)
- [ ] [Both] 杀进程能杀到整棵树吗?长期子进程有退出清理吗?按 pid 杀会不会误杀共享 supervisor 的代理?(W-A9)
- [ ] [Both] 请求路径上的同步 spawn/扫目录:超时多长?首次执行大二进制会不会被杀软拖住?缓存并发口径?(W-A10)[scan]
- [ ] [Win] 错误翻译只认 Node ENOENT 吗?cmd/Rust 原文会不会被误判?(W-A11)
- [ ] [Win] 找可执行文件:PATH 来源、候选目录、exists vs readdir、`where` 多行、缓存、安装器候选同一份?(W-A12)
- [ ] [Win] 诊断日志走 stderr 吗?新增 cmd.exe 子进程会不会弹黑窗?(W-A8)
- [ ] [Win] `.bat/.cmd` 模板调 `.cmd` 有 `call` 吗?(W-A14)
- [ ] [Win] `powershell` 调用:执行策略、输出编码(cp936)、内联裸调 npm 系命令、网络代理(W-A15/G-1)[scan]
- [ ] [Both] 起 git/npm/curl 的地方注入代理了吗?探活会不会误删企业代理?本机 TUN 有没有掩盖问题?(W-A16/X-E5)

## B 路径与文件系统
- [ ] [Win] 硬编码 `/`、`path.posix`、`/tmp`、模板串拼路径、按 `/` 切文件名:在 win32 会走到吗?(W-B1)[scan]
- [ ] [Win] `HOME` 读点;`APPDATA/LOCALAPPDATA` 缺省;测试设 `HOME` 是否同时设 `USERPROFILE`(W-B2)[scan]
- [ ] [Win] 展开后的 env 读 `PATH` 有没有 `Path` 回落(W-B3)[scan]
- [ ] [Both] 路径当 key/比较:两侧 canonical 口径一致?前缀检查带分隔符?(X-B4)[scan]
- [ ] [Mac] `/tmp`、`/var` 与 `/private/...` 的比较两侧都 realpath 了吗?CLI 与 GUI 算出的 hash 目录名一致吗?(M-B1)[scan]
- [ ] [Win] 切分子进程输出/文件的 `split('\n')`、`^…$` 正则、文件比较、`.gitattributes`:CRLF 会进来吗?(W-B5)[scan]
- [ ] [Both] 动态 `import(路径)`、脚本入口判断经 realpath 了吗?(W-B6)
- [ ] [Win] 匹配 Windows 路径的正则接受 `\\` 吗?假设了 mac 才有的路径段吗?(W-B7)
- [ ] [Both] 临时文件:清理?清理包 try?与目标同卷?(W-B8)
- [ ] [Win] unlink/rename 失败分支的归因与残留;读配置失败对状态基线的影响;自写标记有无时效(W-B9)
- [ ] [Both] 平台垃圾文件(`.DS_Store`/`__MACOSX`/`._*`/`Thumbs.db`/`desktop.ini`)、ADS 冒号、带空格路径、保留设备名、长路径(W-B10/X-B5/G-8)
- [ ] [Win] Rust 侧传给 node 的路径有 `\\?\` 前缀吗?(W-B11)
- [ ] [Mac] 文件监听规模与 fd 上限(M-B2);应用包内资源布局是否按平台真机取证(M-B3/W-E1)
- [ ] [Both] hook 命令、子脚本的编码与重定向写法(W-B12)

## C 原生模块与运行时
- [ ] [Both] 原生模块顶层 import 失败会拖垮后端吗?mac 上应用内 node 的 Team ID 校验?(W-C1/M-A1)
- [ ] [Both] 新依赖/升级的 `engines` 高于 app 地板吗?有告警吗?(W-C2)
- [ ] [Both] 能力探测缓存覆盖了所有路径吗?(W-C3)
- [ ] [Both] 构建脚本清了 `dist`/`.vite` 缓存吗?装机后版本握手过吗?旧后端进程退干净了吗?(X-C4)

## D 渲染引擎
- [ ] [Both] `window.confirm/alert`、`navigator.platform`(D-1/D-2)[scan]
- [ ] [Win] 新增横向 flex 行:允许换行?左列有最小宽度?把预览压到 ~280px 看过吗?(D-3)
- [ ] [Both] 裸 `vw/vh`、portal 菜单坐标 ÷ zoom、模态挂载、sticky footer、`<summary>` display:假设了哪个引擎?dev 复现不了的 bug 是不是拿 Chromium 行为推的根因?(D-4/F-6)[scan]
- [ ] [Both] 大列表/大图内存与崩溃自愈(D-5)
- [ ] [Mac] 任何"原生层吞事件"的结论有同版最小复现吗?(D-6)
- [ ] [Both] 手机 Safari:输入框字号、覆盖层高度、dvh(D-7)

## E 分发 / 签名 / 安装 / 网络
- [ ] [Win] 产物布局、主程序名、进程名:真机取证还是类推?测试断言抄实现还是从事实源推导?(W-E1)
- [ ] [Win] 文案提到的产物与 `bundle.targets` 一致吗?自动更新退出路径(W-E2)[scan]
- [ ] [Win] 安装器候选目录、winget 探测(W-E3)
- [ ] [Both] 包发布后镜像同步;平台分包缺失的处理(W-E6)
- [ ] [Mac] 签名身份是持久证书还是 adhoc?装机用 ditto 且先删旧目录了吗?`codesign --verify --deep --strict` 跑了吗?(M-E1)[scan]
- [ ] [Mac] 分发说明覆盖 quarantine/公证/macOS 15 行为了吗?`xattr` 写绝对路径了吗?(M-E2)
- [ ] [Mac] 构建脚本对钥匙串锁定/掉出搜索列表的处理是失败还是静默回落 adhoc?(M-E3)
- [ ] [Mac] 架构与系统版本支持范围写明了吗?(M-E4)
- [ ] [Both] 后端 fetch 与系统代理模式(W-E4,已知待办,别当新回归报)
- [ ] [Both] "本机网络能通"的结论有没有被开发机代理环境掩盖?(X-E5)

## G 预警(每轮都问一遍,验实后升级)
- [ ] [Win] 本轮新增的子进程输出解析,在 cp936 输出下会怎样?(G-1)
- [ ] [Win] 新写的 `.bat/.ps1`:编码与首行处理(G-2)
- [ ] [Both] 新增的用户 JSON 读点:BOM、解析失败有日志吗?(G-3)
- [ ] [Both] 解包路径对非 ASCII 条目名的处理(G-4)
- [ ] [Win] 进入 cmd/PowerShell 字符串的用户文本:`%`、`$`、反引号(G-5)
- [ ] [Both] 拼进正则/WQL/`-like`/`sh -c` 的是不是路径或用户输入?(G-6)
- [ ] [Both] 文档/脚本里的 `localhost`(G-7);云同步占位文件/长路径/保留名(G-8);symlink/执行位/`sh`(G-9);信号硬杀/提权/TCC(G-10);防火墙(G-11)

## F 收尾
- [ ] "必须真机验证"逐条写成 操作 / 看什么 / 什么算过,分平台(F-5)
- [ ] 新排查点按 SKILL.md 的五段格式追加到 `checkpoints.md`(带平台标签,并同步 scan 规则)

---

## 报告模板(逐字用)

```
# 平台兼容性审查 — <版本>(<base>..<HEAD>,<轮次>,平台:Windows / macOS / 两者)

范围:<N 个非测试文件 / +x −y>(已排除 …)。基线:<上一份报告> 的"已核对无问题"不重复报。
调用点清单:见附表(spawn/execFile/pty/Command::new 全量,标 win32/darwin 可达性与参数来源)。

## ① 裁决:可发 / 需修后发(致命 N / 必修 N / 建议 N)
一句话说为什么。

## ② 问题清单
### 必修-1 [Win|Mac|Both] <一句话>(ID)
- 位置:`文件:行`
- 什么输入出什么错:…
- 判据依据:checkpoints.md 该条的哪一句
- 需要谁改:<模块/函数>,按什么判据验收(不替开发写代码)
### 建议-1 …

## ③ 已核对无问题
按 A/B/C/D/E/G 分组,每条一行,说清"为什么没问题"。

## ④ 必须真机验证
Windows:1. 操作 … / 看 … / <阈值> 算过
macOS:1. …

## ⑤ 新增排查点
无 / <ID> 已追加到 checkpoints.md

## ⑥ 外部指令原文
无
```

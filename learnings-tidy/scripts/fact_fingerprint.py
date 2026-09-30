#!/usr/bin/env python3
"""fact_fingerprint.py —— 从 learnings 文件抽取「硬事实」清单（JSON）。

硬事实 = 压缩时一个字都不许删的东西：
  code       反引号内的命令/路径/字符串原文
  path       绝对路径（/… 或 ~/…）
  number     数字+单位 / 裸数字(>=2 位) / 版本号
  term       出现 >=2 次的专有名词（含 . _ - 分隔符或大写或数字的 token）

疑似凭证（sk-…/ghp_…/token=… 等）单列在 credentials 里，**只记形状与行号，绝不落原文**——
压缩的规则是「凭证必须删掉」，所以它们不参与覆盖率比对。

用法：
  python3 fact_fingerprint.py <file>                # 抽取 → JSON 到 stdout
  python3 fact_fingerprint.py --out fp.json <file>  # 抽取并写文件
  python3 fact_fingerprint.py --diff A.json B.json  # 比对两份指纹，报 missing/new
  python3 fact_fingerprint.py --selftest            # 自检：证明抽取有判别力

只读输入文件；不联网；除 --out 指定外不写任何文件。
"""
import argparse
import json
import re
import sys
from collections import Counter

CODE_RE = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(r"(?:~|/)[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+")
NUM_UNIT_RE = re.compile(
    r"\d[\d,._]*\s?(?:k|K|ms|s|h|GB|MB|KB|%|次|行|字|条|个|篇|天|分钟|秒|人|万|"
    r"token|tokens|bytes|B|℃|GB|TB|d|D)(?![A-Za-z0-9])"   # 不能用 \b：CJK 是 \w，"3 次只" 会漏
)
VER_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)*(?:[-.][A-Za-z0-9.]+)*")
BARE_NUM_RE = re.compile(r"\b\d{3,}\b")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.+\-]{2,}")
# 必须带分隔符，否则会把 skill-manager / skills_dir / Desktop 误判成凭证
CRED_RE = re.compile(
    r"(?:sk|ghp|xoxb|glpat)[-_][A-Za-z0-9_-]{8,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|(?:token|TOKEN|api[_-]?key|API[_-]?KEY|secret|SECRET|password|PASSWORD)"
    r"\s*[=:]\s*[^\s`\"']{6,}"
)
# kind 优先级：数值越小越「硬」，同 value 多 kind 时取优先级高者
PRIORITY = {"credential": 0, "code": 1, "path": 2, "number": 3, "term": 4}

# 单个通用命令词不算硬事实（可作为案例叙述删）；出现在完整命令里时才随命令保留
GENERIC_CMDS = {
    "ls", "grep", "git", "python3", "python", "sed", "awk", "cat", "find", "rm", "cd",
    "echo", "head", "tail", "curl", "node", "npm", "npx", "pnpm", "yarn", "pytest",
    "bash", "zsh", "sh", "docker", "ps", "lsof", "kill", "mv", "cp", "mkdir", "chmod",
    "open", "rg", "jq", "tr", "wc", "sort", "uniq", "cut", "xargs", "launchctl", "tmux",
    "obsidian", "perl", "printf", "read", "diff", "patch", "tar", "export", "source",
    "eval", "alias", "which", "whoami", "mount", "df", "du", "stat", "file", "test",
    "true", "false", "env", "sudo", "brew", "pip", "pip3", "make", "deno", "bun", "uv",
    "gh", "wget", "ssh", "scp", "rsync", "nohup", "disown", "setsid", "timeout",
    "gtimeout", "codesign", "mdutil", "security", "osascript", "defaults", "setopt",
    "cmd", "powershell", "react", "hunt", "workdir",
}


def _substantive(tok):
    """token 是否算「有内容」（非纯变量/占位/单选项/通用命令词）。返回清洗后的串或 None。"""
    t = tok.strip("\"'`(),;:[]{}")
    if not t or not re.search(r"[A-Za-z0-9]", t):
        return None
    if t[0] in "$(" or t.startswith("..."):       # 变量占位符 / 残缺片段
        return None
    if t in GENERIC_CMDS or t.startswith("-"):     # 单个通用命令词 / 单选项 -o
        return None
    return t


def _is_hard_span(span):
    """反引号片段是否算「硬事实」：完整命令/报错原文/路径/URL/文件名/版本/端口/环境变量名。"""
    span = span.strip()
    if len(span) < 2 or not re.search(r"[A-Za-z0-9]", span):
        return False
    sub = []
    for x in re.split(r"\s+", span):
        s = _substantive(x) if x else None
        if s:
            sub.append(s)
    if len(sub) >= 2:                              # 完整命令 / 报错句子
        return True
    if re.search(r":\s", span):                    # 报错串（`curl: (56)` / `(eval):1: …`）
        return True
    if len(sub) == 1:                              # 单词形态：只认路径/URL/文件名/版本/常量名
        t = sub[0]
        if re.search(r"[A-Za-z0-9][./:@]|[./:@][A-Za-z0-9]|\d+\.\d+", t):
            return True
        if re.fullmatch(r"[A-Z0-9_]{4,}", t):
            return True
    return False


def _cred_shape(raw):
    """把凭证压成形状串：只暴露前缀，绝不回显原文。"""
    m = re.match(r"[A-Za-z_]+", raw)
    return "<credential:%s…>" % (m.group(0)[:6] if m else "?")


def _is_term(tok):
    """只保留「像专有名词」的 token，滤掉纯小写英文常用词。"""
    if tok.lower() in {"the", "and", "for", "with", "not", "you", "this", "that"}:
        return False
    if any(c in tok for c in "._-/+"):
        return True
    if any(c.isdigit() for c in tok):
        return True
    return any(c.isupper() for c in tok[1:]) or tok.isupper()


def _fingerprint_text(text, name):
    kinds, counts, creds = {}, Counter(), []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in CRED_RE.finditer(line):
            creds.append({"line": lineno, "shape": _cred_shape(m.group(0))})
        found = []
        for m in CODE_RE.finditer(line):
            span = m.group(1).strip()
            if _is_hard_span(span):                # 变量占位/单命令词/残缺片段不计入
                found.append(("code", span))
        found += [("path", m.group(0)) for m in PATH_RE.finditer(line)]
        found += [("number", m.group(0).strip()) for m in NUM_UNIT_RE.finditer(line)]
        found += [("number", m.group(0)) for m in VER_RE.finditer(line)]
        found += [("number", m.group(0)) for m in BARE_NUM_RE.finditer(line)]
        for kind, v in found:
            counts[v] += 1
            if v not in kinds or PRIORITY[kind] < PRIORITY[kinds[v]]:
                kinds[v] = kind
    tok = Counter(m.group(0) for m in TOKEN_RE.finditer(text))
    for v, c in tok.items():
        if c >= 2 and v not in kinds and len(v) >= 3 and _is_term(v):
            kinds[v] = "term"
            counts[v] = c
    items = [{"text": v, "kind": k, "count": counts[v]} for v, k in kinds.items()]
    items.sort(key=lambda d: (PRIORITY[d["kind"]], -d["count"], d["text"]))
    stats = Counter(d["kind"] for d in items)
    return {"file": name, "stats": {"items": len(items), "credentials": len(creds),
            **{k: stats.get(k, 0) for k in ("code", "path", "number", "term")}},
            "items": items, "credentials": creds}


def extract(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return _fingerprint_text(fh.read(), path)


def diff(fp_a, fp_b):
    a = {it["text"]: it for it in fp_a["items"]}
    b = {it["text"]: it for it in fp_b["items"]}
    miss = [a[t] for t in sorted(a.keys() - b.keys())]
    new = [b[t] for t in sorted(b.keys() - a.keys())]
    return miss, new


def _selftest():
    # 混入真硬事实与「非硬事实」（变量占位符 / 单命令词 / 残缺片段），两类都要判对
    sample = ("报错 `LibreSSL SSL_read: bad decrypt` 与 `curl: (56)`；端口 7897；"
              "路径 /Users/wsxwj/.learnings/ERRORS.md；版本 2.1.269；"
              "子代理 16k 输出上限，16000 token；重试 3 次；token=abcdef123456；"
              "连续 7 次以内重试。"   # 回归：数字+单位后紧跟汉字，旧 `\b` 会漏
              "噪声：`$VAR`、`${arr[@]}`、`${=A}`、`, TodoWrite`、`...）EOF`、`-o`、`ls`、`grep`。")
    fp = _fingerprint_text(sample, "<selftest>")
    have = {it["text"] for it in fp["items"]}
    expect = ["LibreSSL SSL_read: bad decrypt", "7897",
              "/Users/wsxwj/.learnings/ERRORS.md", "2.1.269", "16000", "7 次"]
    miss = [e for e in expect if e not in have]
    if miss:
        print("FAIL 漏抽: %s" % miss)
        return 1
    noise = ["$VAR", "${arr[@]}", "${=A}", ", TodoWrite", "...）EOF", "-o", "ls", "grep"]
    bad = [n for n in noise if n in have]
    if bad:
        print("FAIL 非硬事实被计入: %s" % bad)
        return 1
    if fp["stats"]["credentials"] != 1:
        print("FAIL 凭证未识别")
        return 1
    blob = json.dumps(fp, ensure_ascii=False)
    if "abcdef123456" in blob:
        print("FAIL 凭证原文进了指纹")
        return 1
    lossy = sample.replace("7897", "XXXX").replace("2.1.269", "")
    fp2 = _fingerprint_text(lossy, "<lossy>")
    gone = set(have - {it["text"] for it in fp2["items"]})
    if not {"7897", "2.1.269"} <= gone:
        print("FAIL 差分抓不到故意删掉的事实: %s" % sorted(gone))
        return 1
    print("PASS fact_fingerprint: 抽到 %d 项事实，识别 %d 处凭证（已脱敏），差分可辨。"
          % (len(have), fp["stats"]["credentials"]))
    return 0


def main():
    ap = argparse.ArgumentParser(description="抽 learnings 文件的硬事实指纹")
    ap.add_argument("file", nargs="?", help="待抽取文件")
    ap.add_argument("--out", help="把 JSON 写到该路径（默认 stdout）")
    ap.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"), help="比对两份指纹 JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.diff:
        with open(args.diff[0], encoding="utf-8") as f1, open(args.diff[1], encoding="utf-8") as f2:
            miss, new = diff(json.load(f1), json.load(f2))
        print("missing(before→after 丢了 %d 项):" % len(miss))
        for it in miss:
            print("  - [%s] %s" % (it.get("kind", "?"), it["text"]))
        print("new(after 多出 %d 项):" % len(new))
        for it in new:
            print("  + [%s] %s" % (it.get("kind", "?"), it["text"]))
        return 1 if miss else 0
    if not args.file:
        ap.error("需要 <file>，或 --diff，或 --selftest")
    fp = extract(args.file)
    out = json.dumps(fp, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print("写入 %s：%d 项事实" % (args.out, fp["stats"]["items"]))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

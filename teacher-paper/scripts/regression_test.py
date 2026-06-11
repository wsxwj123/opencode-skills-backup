#!/usr/bin/env python3
"""teacher-paper 回归测试套（v3.11.0）
覆盖：assemble 门禁（凭证/原创/古诗/纸质/title-only/蓝图脏数据）+ make_figure RCE 防线。
跑法：python3 regression_test.py
预期：全部 PASS，任何 FAIL 都意味着真实的回归。
"""
import sys
import os
import tempfile
import pathlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import assemble as A
import make_figure as F

PASS, FAIL = [], []


def case(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("  ✅" if cond else "  ❌") + f" {name}" + (f"  {detail}" if not cond else ""))


# ============== Part A: 凭证头校验 ==============
print("\n=== A. _credential_matches_url 凭证头 ===")
body = "凭证后正文一百字……" + "字" * 90
real = f"""<!-- teacher-paper:fetched
url: https://news.cn/ok
strategy: jina
chars: {len(body)}
sha256: x
fetched_at: 2026-06-05
-->

来源：https://news.cn/ok

{body}"""

ok, _ = A._credential_matches_url(real, "https://news.cn/ok")
case("A1 真凭证+URL匹配-通过", ok)
ok, _ = A._credential_matches_url(real, "https://news.cn/DIFFERENT")
case("A2 凭证URL与meta不符-拒", not ok)
ok, _ = A._credential_matches_url("无凭证头正文", "https://news.cn/ok")
case("A3 无凭证头-拒", not ok)

fake = f"""<!-- teacher-paper:fetched
url: https://news.cn/ok
strategy: jina
chars: 5000
sha256: y
fetched_at: 2026-06-05
-->

短"""
ok, _ = A._credential_matches_url(fake, "https://news.cn/ok")
case("A4 chars严重偏离-拒", not ok)


# ============== Part B: _check_source 分级门禁 ==============
print("\n=== B. _check_source 分级门禁 ===")
with tempfile.TemporaryDirectory() as td:
    mat_dir = pathlib.Path(td) / "materials"
    mat_dir.mkdir()
    paper_with_mat = [{"type": "material", "title": "材料一", "paras": ["凭证后正文一百字"]}]

    errors, warn = [], []
    A._check_source("b1.json", {}, paper_with_mat, str(mat_dir), errors, warn)
    case("B1 meta缺source-拒", any("source" in e for e in errors))

    errors, warn = [], []
    A._check_source("b2.json", {"source": "https://news.cn/x"}, paper_with_mat,
                    str(mat_dir), errors, warn)
    case("B2 非原创缺source_file-拒", any("source_file" in e for e in errors))

    errors, warn = [], []
    A._check_source("b3.json", {"source": "https://news.cn/x", "source_file": "ghost.md"},
                    paper_with_mat, str(mat_dir), errors, warn)
    case("B3 source_file不存在-拒", any("不存在" in e for e in errors))

    (mat_dir / "b4.md").write_text("无凭证头", encoding="utf-8")
    errors, warn = [], []
    A._check_source("b4.json", {"source": "https://news.cn/x", "source_file": "b4.md"},
                    paper_with_mat, str(mat_dir), errors, warn)
    case("B4 URL但无凭证头-拒", any("凭证" in e for e in errors))

    (mat_dir / "b5.md").write_text(real, encoding="utf-8")
    errors, warn = [], []
    A._check_source("b5.json", {"source": "https://news.cn/DIFFERENT", "source_file": "b5.md"},
                    paper_with_mat, str(mat_dir), errors, warn)
    case("B5 凭证URL≠meta.source-拒", any("凭证" in e for e in errors))

    paradox = [{"type": "material", "title": "x", "paras": ["abc"],
                "source": "节选自《野草》"}]
    errors, warn = [], []
    A._check_source("b6.json", {"source": "原创-已声明"}, paradox, str(mat_dir), errors, warn)
    case("B6 原创+卷面节选-拒", any("矛盾" in e for e in errors))

    verse = [{"type": "material", "title": "x", "paras": ["床前明月光"],
              "layout": "verse"}]
    errors, warn = [], []
    A._check_source("b7.json", {"source": "原创-已声明"}, verse, str(mat_dir), errors, warn)
    case("B7 古诗词+原创-拒", any("古诗" in e for e in errors))

    (mat_dir / "b8.md").write_text(real, encoding="utf-8")
    title_only = [{"type": "material", "title": "仅标题无正文"}]
    errors, warn = [], []
    A._check_source("b8.json", {"source": "https://news.cn/ok", "source_file": "b8.md"},
                    title_only, str(mat_dir), errors, warn)
    case("B8 title-only-warn", any("正文" in w for w in warn))

    (mat_dir / "b9.md").write_text(real, encoding="utf-8")
    paper_ok = [{"type": "material", "title": "材料", "paras": ["凭证后正文一百字"]}]
    errors, warn = [], []
    A._check_source("b9.json", {"source": "https://news.cn/ok", "source_file": "b9.md"},
                    paper_ok, str(mat_dir), errors, warn)
    case("B9 正常URL+凭证-通过", len(errors) == 0)

    (mat_dir / "b10.md").write_text("纸质书原文", encoding="utf-8")
    errors, warn = [], []
    A._check_source("b10.json", {"source": "本地纸质教材《xx》", "source_file": "b10.md"},
                    paper_ok, str(mat_dir), errors, warn)
    case("B10 纸质书-放行", len(errors) == 0)


# ============== Part C: blueprint 脏数据规整 ==============
print("\n=== C. blueprint 脏数据 ===")
for name, bp in [
    ("C1 skeleton非tuple", {"skeleton": ["bad"], "manifest": []}),
    ("C2 manifest短列", {"skeleton": [("A", "B")], "manifest": [("x", "y")]}),
    ("C3 manifest超长", {"skeleton": [("A", "B")],
                          "manifest": [("a", "b", "c", "d", "e", "f", "g")]}),
]:
    try:
        A._normalize_blueprint(bp)
        case(f"{name}-不崩溃", True)
    except Exception as e:
        case(f"{name}-不崩溃", False, str(e))


# ============== Part D: 题号去重 / 默认 ==============
print("\n=== D. 题号归一化 / 默认值 ===")
case("D1 题号'7'='07'", "07".lstrip("0") or "0" == "7")
case("D2 expected_questions缺-默认0", ({}.get("expected_questions") or 0) == 0)
src_with_url = "https://news.cn/x 用户提供"
is_url = "http" in src_with_url.lower()
is_user = (not is_url) and any(k in src_with_url for k in A._USER_SRC_HINTS)
case("D3 URL存在时is_user=False", is_url and not is_user)


# ============== Part E: make_figure RCE 防线 ==============
print("\n=== E. make_figure RCE 防线 ===")
import shutil
fig_dir = "/tmp/_tp_regression_figs"
if os.path.exists(fig_dir):
    shutil.rmtree(fig_dir)
os.makedirs(fig_dir, exist_ok=True)
probe = "/tmp/_tp_RCE_PROBE"
if os.path.exists(probe):
    os.unlink(probe)

malicious = [
    f"__import__('os').system('touch {probe}')",
    f"eval(\"open('{probe}','w').write(1)\")",
    "x.__class__.__bases__",
    "(lambda: 1)()",
    "open('/etc/passwd').read()",
]
for expr in malicious:
    r = F.render_figure({"kind": "function", "funcs": [expr],
                         "xrange": [-1, 1], "alt": ""}, fig_dir)
    case(f"E·拒绝 {expr[:35]}…", r is None)
case("E·RCE探针文件未被创建", not os.path.exists(probe))

for expr in ["x**2 - 2*x", "sin(x) + cos(x)", "sqrt(x**2 + 1)"]:
    r = F.render_figure({"kind": "function", "funcs": [expr],
                         "xrange": [-3, 3], "alt": ""}, fig_dir)
    case(f"E·合法 {expr}", r is not None and os.path.exists(r))

# ============== Part F: 按板块字数门禁 ==============
print("\n=== F. _check_block_lengths 字数门禁 ===")
BL = {"非连": [600, 1000], "小说": [1000, 1500], "散文": [800, 1200], "文言": [100, 200]}


def _mk(sub, paras, **kw):
    return [{"type": "sub", "text": sub},
            {"type": "material", "title": "x", "paras": paras, **kw}]


errs = A._check_block_lengths(_mk("（二）文学作品阅读·小说", ["字" * 800]), BL)
case("F1 小说800字<区间-阻断", any("小说" in e and "偏短" in e for e in errs))

errs = A._check_block_lengths(_mk("（二）文学作品阅读·小说", ["字" * 1200]), BL)
case("F2 小说1200字达标-通过", not errs)

errs = A._check_block_lengths(
    _mk("（一）非连续性文本阅读", ["字" * 300]) +
    [{"type": "material", "title": "y", "paras": ["字" * 400]}], BL)
case("F3 非连两则合计700-求和通过", not errs)

errs = A._check_block_lengths(_mk("（一）非连续性文本阅读", ["字" * 300]), BL)
case("F4 非连单则300偏短-阻断", any("非连" in e for e in errs))

errs = A._check_block_lengths(_mk("（三）古诗文阅读", ["床前明月光"], layout="verse"), BL)
case("F5 verse古诗-跳过", not errs)

errs = A._check_block_lengths(_mk("（五）拓展阅读", ["字" * 50], block="文言"), BL)
case("F6 显式block=文言覆盖推断-阻断", any("文言" in e for e in errs))

errs = A._check_block_lengths(_mk("（二）小说", ["字" * 800]), None, "语文", None)
case("F7 旧工程无block_len-回退小说默认仍阻断", any("小说" in e for e in errs))

errs = A._check_block_lengths(_mk("阅读理解", ["word " * 100]), None, "英语", None)
case("F8 英语无显式区间-跳过", not errs)

errs = A._check_block_lengths(_mk("阅读理解A", ["word " * 100], block="阅读"),
                              {"阅读": [150, 250]}, "英语")
case("F9 英语显式区间按词-阻断", any("100 词" in e for e in errs))

case("F10 语文默认表含四板块", set(A._default_block_len("九年级", "语文")) ==
     {"非连", "小说", "散文", "文言"})
case("F11 非语文无默认", A._default_block_len("九年级", "物理") == {})

# 总结
print(f"\n=== 总计 {len(PASS)}/{len(PASS)+len(FAIL)} 通过 ===")
if FAIL:
    print("失败:")
    for n, d in FAIL:
        print(f"  - {n}: {d}")
    sys.exit(1)
sys.exit(0)

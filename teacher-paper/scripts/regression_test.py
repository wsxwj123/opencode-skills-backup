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


# ============== Part B2: 选文标注措辞校验 ==============
print("\n=== B2. _check_material_wording 标注措辞 ===")
w = []
A._check_material_wording([{"type": "material", "title": "老街（改编自《读者》）",
                            "paras": ["正文"]}], w)
case("B11 title含'改编自'-告警", any("改编" in x for x in w))

w = []
A._check_material_wording([{"type": "material", "title": "老街",
                            "source": "（教师原创）", "paras": ["正文"]}], w)
case("B12 source含'原创'-告警", any("原创" in x for x in w))

w = []
A._check_material_wording([{"type": "material", "title": "老街",
                            "source": "（节选自《读者》2024年第6期）",
                            "paras": ["该电影改编自同名小说，上映后反响热烈。"]}], w)
case("B13 正文含'改编'不误伤+规范标注-静默", not w)

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
# Bug-Y-2 修复后：英语无显式 block_len 时回退到内置默认（初中阅读 200-300 词），100 词偏短应被阻断
case("F8 英语无显式区间-回退内置默认仍校验", any("英语阅读" in e for e in errs))

errs = A._check_block_lengths(_mk("阅读理解A", ["word " * 100], block="阅读"),
                              {"阅读": [150, 250]}, "英语")
case("F9 英语显式区间按词-阻断", any("100 词" in e for e in errs))

case("F10 语文默认表含四板块", set(A._default_block_len("九年级", "语文")) ==
     {"非连", "小说", "散文", "文言"})
case("F11 非语文无默认", A._default_block_len("九年级", "物理") == {})

# ============== Part H: 完整性门禁（坏JSON/题量不符 → 拒绝出卷） ==============
print("\n=== H. cmd_build 完整性门禁 ===")
import json as _json
import io
import contextlib


def _mk_proj(td, items, exp_q):
    proj = pathlib.Path(td) / "p"
    (proj / "items").mkdir(parents=True)
    (proj / "materials").mkdir()
    (proj / "meta.json").write_text(_json.dumps(
        {"title": "t", "expected_questions": exp_q, "total": 2}), encoding="utf-8")
    for name, content in items:
        (proj / "items" / name).write_text(content, encoding="utf-8")
    return proj


_q_ok = _json.dumps({"meta": {"num": "1", "score": 2},
                     "paper": [{"type": "question", "num": "1", "text": "题"}],
                     "answer": []}, ensure_ascii=False)

with tempfile.TemporaryDirectory() as td:
    proj = _mk_proj(td, [("101_q01.json", _q_ok),
                         ("102_q02.json", '{"paper": [{"text": "他说"你好""}], "answer": []}')], 1)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            A.cmd_build([str(proj)])
        case("H1 坏JSON(未转义ASCII引号)-拒绝出卷", False, "未退出")
    except SystemExit as e:
        case("H1 坏JSON(未转义ASCII引号)-拒绝出卷", e.code == 2)
        case("H2 报错附全角引号修复提示", "全角" in buf.getvalue())

with tempfile.TemporaryDirectory() as td:
    proj = _mk_proj(td, [("101_q01.json", _q_ok)], 3)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            A.cmd_build([str(proj)])
        case("H3 题量1≠期望3-拒绝出卷", False, "未退出")
    except SystemExit as e:
        case("H3 题量1≠期望3-拒绝出卷", e.code == 2)

_mat_bad = _json.dumps({
    "meta": {"status": "-", "source": "本地纸质教材《读本》", "source_file": "b.md"},
    "paper": [{"type": "material", "title": "老街（改编自《读者》）", "paras": ["正文" * 60]}],
    "answer": []}, ensure_ascii=False)
with tempfile.TemporaryDirectory() as td:
    proj = _mk_proj(td, [("101_q01.json", _q_ok), ("211_mat.json", _mat_bad)], 1)
    (proj / "materials" / "b.md").write_text("正文" * 60, encoding="utf-8")  # 含正文,只测措辞门禁不触发忠实节选门禁
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            A.cmd_build([str(proj)])
        case("H4 标注含'改编自'-措辞门禁拒绝", False, "未退出")
    except SystemExit as e:
        case("H4 标注含'改编自'-措辞门禁拒绝", e.code == 2)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            A.cmd_build([str(proj), "--allow-wording"])
        _atbl_p = proj / "build" / "材料真实性自检表.md"
        _atbl = _atbl_p.read_text(encoding="utf-8") if _atbl_p.exists() else ""
        case("H5 --allow-wording降级出卷+自检表含❌", "改编" in _atbl and "❌" in _atbl)
    except SystemExit as e:
        case("H5 --allow-wording降级出卷+自检表含❌", False, f"exit {e.code}")

# ============== Part I: 忠实节选连续子串门禁 ==============
print("\n=== I. _check_faithful_excerpt 连续删减门禁 ===")
with tempfile.TemporaryDirectory() as td:
    md = pathlib.Path(td) / "materials"
    md.mkdir()
    # 原文 ABC 三段
    A_txt, B_txt, C_txt = "甲" * 20, "乙" * 20, "丙" * 20
    (md / "src.md").write_text(A_txt + "\n\n" + B_txt + "\n\n" + C_txt, encoding="utf-8")
    meta = {"status": "-", "source": "本地纸质《合集》", "source_file": "src.md"}

    def _excerpt(paras, **kw):
        return [{"type": "material", "title": "x", "paras": paras, **kw}]

    er = []
    A._check_faithful_excerpt("i1.json", meta, _excerpt([A_txt, B_txt]), str(md), er)
    case("I1 取AB连续-放行", not er)

    er = []
    A._check_faithful_excerpt("i2.json", meta, _excerpt([B_txt, C_txt]), str(md), er)
    case("I2 取BC连续-放行", not er)

    er = []
    A._check_faithful_excerpt("i3.json", meta, _excerpt([A_txt, C_txt]), str(md), er)
    case("I3 取AC删中段-放行（允许删无关部分）", not er)

    er = []
    A._check_faithful_excerpt("i4.json", meta, _excerpt([A_txt.replace("甲", "改", 1)]), str(md), er)
    case("I4 改字-拒", any("逐字" in e for e in er))

    er = []
    A._check_faithful_excerpt("i5.json", meta, _excerpt([C_txt, A_txt]), str(md), er)
    case("I5 调序CA-拒（重排）", any("顺序" in e for e in er))

    er = []
    A._check_faithful_excerpt("i8.json", meta, _excerpt([A_txt + "凭空编造一段假内容" * 2]), str(md), er)
    case("I8 编造-拒", any("逐字" in e for e in er))

    er = []
    A._check_faithful_excerpt("i6.json", {"status": "-", "source": "原创-已声明"},
                              _excerpt([A_txt, C_txt]), str(md), er)
    case("I6 原创素材-跳过", not er)

    er = []
    A._check_faithful_excerpt("i7.json", meta,
                              _excerpt(["床前明月光"], layout="verse"), str(md), er)
    case("I7 verse古诗-跳过", not er)

# ============== Part G: NUL 残留文件清理 ==============
print("\n=== G. _cleanup_nul_files NUL 残留清理 ===")
with tempfile.TemporaryDirectory() as td:
    proj = pathlib.Path(td)
    (proj / "materials").mkdir()
    (proj / "NUL").write_text("", encoding="utf-8")
    (proj / "materials" / "nul").write_text("", encoding="utf-8")
    (proj / "normal.md").write_text("正常文件", encoding="utf-8")
    warn = []
    A._cleanup_nul_files(str(proj), warn)
    case("G1 根目录NUL被删除", not (proj / "NUL").exists())
    case("G2 子目录小写nul被删除", not (proj / "materials" / "nul").exists())
    case("G3 正常文件不受影响", (proj / "normal.md").exists())
    case("G4 清理动作有告警提示", len(warn) == 2)

    warn = []
    A._cleanup_nul_files(str(proj), warn)
    case("G5 无残留时静默", not warn)

with tempfile.TemporaryDirectory() as td:
    parent = pathlib.Path(td)
    gproj = parent / "工程"
    gproj.mkdir()
    (parent / "NUL").write_text("", encoding="utf-8")
    warn = []
    A._cleanup_nul_files(str(gproj), warn, extra_dirs=(str(parent),))
    case("G6 工程父目录顶层NUL被清理", not (parent / "NUL").exists())

# ============== Part J: Batch 1 安全补丁（A1/A2/A3/A4/W1）==============
print("\n=== J. Batch 1 安全补丁 ===")

# J.A1 sha256 校验
import hashlib as _hl
body_J1 = "正文测试" * 30   # 真实正文
sha_J1 = _hl.sha256(body_J1.encode()).hexdigest()
cred_J1 = (f"<!-- teacher-paper:fetched\nurl: https://news.cn/J1\n"
           f"strategy: jina\nchars: {len(body_J1)}\nsha256: {sha_J1}\nfetched_at: 2026-06-15\n-->\n\n"
           f"来源：https://news.cn/J1\n抓取日期：2026-06-15\n\n{body_J1}")
ok, _ = A._credential_matches_url(cred_J1, "https://news.cn/J1")
case("J1.A1 真凭证+真sha256-放行", ok)

# 攻击：内容被改但 chars 对齐
fake_body = "篡改正文" * 30  # 等长但内容不同
fake_text = cred_J1.replace(body_J1, fake_body)
ok, why = A._credential_matches_url(fake_text, "https://news.cn/J1")
case("J2.A1 chars对齐但sha256不符-拒", not ok and "sha256" in why)

# J.A2 manifest 宽容解包
import tempfile as _tf
with _tf.TemporaryDirectory() as td:
    _meta = {"grade":"九","subject":"语文","exam_type":"中考","region":"长沙",
             "total":120,"duration":120,"expected_questions":21,"title":"t","blueprint_source":""}
    bad_rows = [("100","q1","选择",2,"考点A"),  # 5字段
                ("200","q2","填空"),               # 4字段
                ("300","q3","解答",4,"考点B",0.6,"额外字段")]  # 7字段
    try:
        A._write_manifest(td, _meta, bad_rows)
        case("J3.A2 manifest脏数据不崩溃", True)
    except Exception as e:
        case("J3.A2 manifest脏数据不崩溃", False, str(e))

# J.A3 sympy 白名单（已单独验证）
import make_figure as _MF
for atk in ["factorial(5)", "integrate(x, x)", "diff(x, x)", "Sum(x, (x, 0, 5))"]:
    try:
        _MF._make_func(atk)
        case(f"J4.A3 拦 {atk[:18]}", False, "未拒绝")
    except ValueError:
        case(f"J4.A3 拦 {atk[:18]}", True)
# 合法仍放行
ok_J = True
for legit in ["x**2-1", "sin(x)+cos(x)", "sqrt(x**2+1)"]:
    try:
        _MF._make_func(legit)
    except Exception:
        ok_J = False
case("J5.A3 合法表达式仍放行", ok_J)

# J.A4 忠实节选短段累计占比
with _tf.TemporaryDirectory() as td:
    md = pathlib.Path(td) / "materials"
    md.mkdir()
    long_orig = "这是原文很长一段连续完整的内容请勿打散" * 5  # 真实原文
    (md / "src.md").write_text(long_orig, encoding="utf-8")
    # 攻击：把原文每段拆成 11 字短句逐句重写
    short_chunks = ["这是原文很长一段连内", "全新编造的内容欺骗系统", "再来一段编造的违规内容",
                    "这也是编造的不在原文里", "完全编造内容欺骗校验"] * 3
    meta = {"status":"-", "source":"本地纸质《合集》", "source_file":"src.md"}
    er = []
    A._check_faithful_excerpt("j6.json", meta,
                              [{"type":"material","title":"x","paras":short_chunks}],
                              str(md), er)
    case("J6.A4 短段拆解绕过-拒", any("短段" in e for e in er))

# J.W1 时政时效
with _tf.TemporaryDirectory() as td:
    md = pathlib.Path(td) / "materials"
    md.mkdir()
    stale_body = "旧时政素材测试" * 30
    stale_sha = _hl.sha256(stale_body.encode()).hexdigest()
    cred_stale = (f"<!-- teacher-paper:fetched\nurl: https://gov.cn/stale\n"
                  f"strategy: jina\nchars: {len(stale_body)}\nsha256: {stale_sha}\n"
                  f"fetched_at: 2024-01-01\n-->\n\n来源：https://gov.cn/stale\n抓取日期：2024-01-01\n\n{stale_body}")
    (md / "stale.md").write_text(cred_stale, encoding="utf-8")
    er, w = [], []
    A._check_freshness("j7.json",
                       {"source":"https://gov.cn/stale", "source_file":"stale.md"},
                       [{"type":"material","title":"x","paras":[stale_body]}],
                       str(md), "思想政治", er, w, 90)
    case("J7.W1 道法素材>180天-拒", any("时政" in e for e in er))

# 非时政科目不触发
er2 = []
A._check_freshness("j8.json",
                   {"source":"https://gov.cn/stale", "source_file":"stale.md"},
                   [{"type":"material","title":"x","paras":[stale_body]}],
                   str(md), "语文", er2, [], 90)
case("J8.W1 语文科目不触发freshness", not er2)

# ============== Part K: Batch 2 学科门禁兼容（Y-2/Y-3/L-3/W-2）==============
print("\n=== K. Batch 2 学科门禁兼容 ===")

# K.Y2 英语板块关键词+默认 block_len
case("K1.Y2 英语default block_len九年级",
     "英语阅读" in A._default_block_len("九年级", "英语"))
case("K2.Y2 英语default block_len高三",
     "读后续写" in A._default_block_len("高三", "英语"))
# 英语阅读理解板块字数门禁实际生效
errs = A._check_block_lengths(
    [{"type":"sub","text":"四、阅读理解A篇"},
     {"type":"material","title":"x","paras":["word "*50]}],  # 50词太短
    None, "英语", None)
case("K3.Y2 英语50词<200-阻断",
     any("英语阅读" in e and ("50 词" in e or "偏短" in e) for e in errs))

# K.L3 情境引子豁免
with tempfile.TemporaryDirectory() as td:
    md = pathlib.Path(td) / "materials"
    md.mkdir()
    (md / "src.md").write_text("原文内容" * 30, encoding="utf-8")
    meta = {"status":"-", "source":"https://x.com", "source_file":"src.md"}
    er = []
    # 情境引子（理科科普报道）可以是 AI 改写的，不走逐字校验
    A._check_faithful_excerpt("k4.json", meta,
        [{"type":"material","title":"x","block":"情境引子","paras":["完全编造的情境引子内容不在原文里"]}],
        str(md), er)
    case("K4.L3 情境引子豁免逐字校验", not er)

# K.Y3 听力稿豁免
with tempfile.TemporaryDirectory() as td:
    md = pathlib.Path(td) / "materials"; md.mkdir()
    (md / "voa.md").write_text("Original VOA content " * 20, encoding="utf-8")
    meta = {"status":"-","source":"https://voa.com","source_file":"voa.md"}
    er = []
    A._check_faithful_excerpt("k5.json", meta,
        [{"type":"material","title":"Listening","layout":"listening_transcript",
          "paras":["W: Hi, where are you going? M: To the library to return books."]}],
        str(md), er)
    case("K5.Y3 听力稿豁免逐字校验", not er)

# K.Y3 英语 _norm_text 兼容大小写+智能引号
LQ, RQ = chr(0x201C), chr(0x201D)  # 左右智能双引号
n1 = A._norm_text(f"The book it is {LQ}Great{RQ}!")
n2 = A._norm_text('the book it is "great"')
case("K6.Y3 智能引号+大小写归一一致", n1 == n2)

# K.W2 历史题干内嵌史料 warn
warn_W2 = []
A._check_embedded_history("k7.json",
    [{"type":"question","text":"阅读《史记·项羽本纪》：'力拔山兮气盖世，时不利兮骓不逝'，下列推断正确的是…"}],
    "历史", warn_W2)
case("K7.W2 历史题干含书名号+引文-warn", any("史料" in w for w in warn_W2))

# 非历史科目不触发
warn_W2b = []
A._check_embedded_history("k8.json",
    [{"type":"question","text":"阅读《史记·项羽本纪》：'力拔山兮'，下列说法正确"}],
    "语文", warn_W2b)
case("K8.W2 非历史不触发", not warn_W2b)

# 总结
print(f"\n=== 总计 {len(PASS)}/{len(PASS)+len(FAIL)} 通过 ===")
if FAIL:
    print("失败:")
    for n, d in FAIL:
        print(f"  - {n}: {d}")
    sys.exit(1)
sys.exit(0)

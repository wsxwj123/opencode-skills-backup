"""Char-level gate contract tests (D1/D2/F1/F3). Self-contained, no pytest.

双向断言:该报的报、不该报的不报。全部 WARN 级,合成输入。
Run: python scripts/test_charlevel_contract.py  (rc=0 = all pass)
"""

import sys
import proofread as P


def _types(issues):
    return [i["type"] for i in issues]


# ── D1: 中文句内夹半角标点 ───────────────────────────────────────────────────
def test_d1_flags_halfwidth_in_chinese():
    # 半角逗号两侧紧邻汉字 → 应报
    issues = P.check_halfwidth_in_cn("我们测量了样本,然后分析了数据。")
    assert any(i["type"] == "halfwidth_punct_in_cn" for i in issues), "D1 漏报中文句内半角逗号"
    # 分号、冒号、括号
    assert P.check_halfwidth_in_cn("第一组;第二组"), "D1 漏报半角分号"
    assert P.check_halfwidth_in_cn("结果:显著"), "D1 漏报半角冒号"
    assert P.check_halfwidth_in_cn("方法(改进版本"), "D1 漏报半角左括号"


def test_d1_no_false_positive_on_english():
    # 纯英文句内半角逗号 → 不报
    assert not P.check_halfwidth_in_cn("We measured the sample, then analyzed it."), "D1 误报英文半角逗号"
    # DOI / URL / 数字区间 → 不报(无汉字夹半角)
    assert not P.check_halfwidth_in_cn("10.1038/s41586-020-2649,2 and http://a.org/x:y"), "D1 误报 DOI/URL"
    assert not P.check_halfwidth_in_cn("range 1,000-2,000 (n=5)"), "D1 误报数字区间"
    # 全角已正确 → 不报
    assert not P.check_halfwidth_in_cn("我们测量了样本，然后分析了数据。"), "D1 误报全角逗号"


# ── D2: 上下标裸写 ───────────────────────────────────────────────────────────
def test_d2_flags_bare_formulas():
    assert any(i["found"] == "H2O" for i in P.check_subsup("dissolved in H2O at RT")), "D2 漏报裸写 H2O"
    assert any(i["found"] == "CO2" for i in P.check_subsup("under 5% CO2")), "D2 漏报裸写 CO2"
    assert P.check_subsup("IC50 was 2 nM"), "D2 漏报裸写 IC50"
    assert P.check_subsup("area of 5 cm2"), "D2 漏报裸写 cm2"
    assert P.check_subsup("density 10^6 cells"), "D2 漏报裸写 10^6"


def test_d2_no_false_positive_when_wrapped():
    # 已带 markdown 上下标 ~2~ → 不报
    assert not any(i["found"] == "H2O" for i in P.check_subsup("dissolved in H~2~O")), "D2 误报已带 ~2~ 的 H2O"
    assert not P.check_subsup("area of 5 cm^2^"), "D2 误报已带 ^2^ 的 cm"
    # 已带 HTML sub/sup → 不报
    assert not P.check_subsup("CO<sub>2</sub> incubator"), "D2 误报已带 <sub> 的 CO2"
    assert not P.check_subsup("10<sup>6</sup> cells"), "D2 误报已带 <sup> 的幂"


# ── F1: 中文错别字 ───────────────────────────────────────────────────────────
def test_f1_flags_typos():
    assert any(i["found"] == "帐号" for i in P.check_chinese_typos("请输入帐号和密码")), "F1 漏报 帐号"
    assert any(i["found"] == "既使" for i in P.check_chinese_typos("既使失败也要继续")), "F1 漏报 既使"
    assert P.check_chinese_typos("软件按装完成"), "F1 漏报 按装"


def test_f1_no_false_positive():
    # 正确写法 → 不报
    assert not P.check_chinese_typos("请输入账号和密码"), "F1 误报正确的 账号"
    assert not P.check_chinese_typos("即使失败也要继续"), "F1 误报正确的 即使"
    # 主观字 的/地/得 不在词表 → 不报
    assert not P.check_chinese_typos("他跑得很快，慢慢地走"), "F1 误报主观的 得/地"


# ── F3: 英文学术错拼 ─────────────────────────────────────────────────────────
def test_f3_flags_misspellings():
    assert any(i["found"].lower() == "occured" for i in P.check_misspellings("the reaction occured fast")) \
        or P.check_academic_misspellings("the reaction occured fast"), "F3/既有词表 漏报 occured"
    assert P.check_academic_misspellings("two seperate experiments were enviroment"), "F3 漏报 enviroment"
    assert any(i["found"].lower() == "signficant" for i in P.check_academic_misspellings("a signficant result")), "F3 漏报 signficant"
    assert P.check_academic_misspellings("flourescence imaging"), "F3 漏报 flourescence"


def test_f3_no_false_positive():
    # 正确拼写 → 不报
    assert not P.check_academic_misspellings("a significant fluorescence measurement in the environment"), "F3 误报正确拼写"
    # 专有名词/合法词不在表 → 不报
    assert not P.check_academic_misspellings("PMG colonized the tumor and FUS heating worked"), "F3 误报专有名词"


def test_f3_warn_severity():
    # F3 必须是 warn 级(不阻断)
    for i in P.check_academic_misspellings("enviroment"):
        assert i["severity"] == "warn", "F3 严重度必须为 warn"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
理科配图渲染器 —— teacher-paper skill 自包含组件（matplotlib 后端）

为什么需要它：理科（数学/物理/化学/生物）题目常需配图。本模块用 matplotlib
把"图的结构化描述(spec)"渲染成 PNG，由 make_paper.py 插入 Word。
能自动画的类型（matplotlib 可行子集）：
  - function   函数图像：y=f(x) 一条或多条曲线、坐标轴、网格
  - geometry   平面几何：点/线段/多边形/标注（基础）
  - number_line 数轴：刻度、实心/空心点、区间
  - bar/line/pie/scatter 统计图
  - vector     受力/矢量箭头图（物理）
  - climate    气候类型图（地理）：气温折线 + 降水柱状双轴
  - pyramid    人口金字塔（地理）：左男右女对称水平条形
画不了的（电路图/化学结构式/复杂装置/立体几何/政区图/真实地图）：返回 None，由调用方降级为
用户提供图片或 ［图：alt］ 占位。绝不假装能画。

另提供 render_formula：把 LaTeX 公式用 matplotlib mathtext 渲成 PNG（复杂公式用）。

对外接口（被 make_paper.py 调用，约定）：
    render_figure(spec: dict, out_dir: str) -> str|None   # 返回 png 路径，画不了返回 None
    render_formula(latex: str, out_dir: str) -> str|None  # 返回 png 路径

spec 形如：{"kind":"function","funcs":["x**2-2*x-3"],"xrange":[-2,4],"alt":"抛物线"}
单独运行做自检：python3 make_figure.py selftest <输出目录>
"""

# Windows 控制台默认 GBK：强制 stdout/stderr 用 UTF-8，避免中文 print 乱码（幂等，mac/Linux 无副作用）
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

import sys
import os
import re
import hashlib
import math

try:
    import matplotlib
    matplotlib.use("Agg")  # 无界面后端，服务器/CI 可用
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    raise  # 让调用方捕获 ImportError 并降级（make_paper 已处理）


# 中文字体兜底（找不到 CJK 字体时标注中文会变方框；按平台常见字体优先）
_CJK_FONTS = ["PingFang SC", "Heiti SC", "STHeiti", "Songti SC",
              "Arial Unicode MS", "Microsoft YaHei", "SimHei", "SimSun",
              "Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]
matplotlib.rcParams["font.sans-serif"] = _CJK_FONTS
matplotlib.rcParams["axes.unicode_minus"] = False  # 负号正常显示


def _stable_key(obj):
    """规整成与 dict 键顺序无关的字符串，避免逻辑相同的 spec 因键序不同算出不同哈希。"""
    if isinstance(obj, dict):
        return "{" + ",".join(f"{k!r}:{_stable_key(v)}"
                              for k, v in sorted(obj.items())) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_stable_key(x) for x in obj) + "]"
    return repr(obj)


def _out_path(out_dir, spec_or_text):
    """按内容算稳定文件名，避免重复渲染、便于缓存。哈希键序无关。"""
    os.makedirs(out_dir, exist_ok=True)
    key = _stable_key(spec_or_text).encode("utf-8")
    h = hashlib.md5(key).hexdigest()[:12]
    return os.path.join(out_dir, f"fig_{h}.png")


def _save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.1,
                facecolor="white")
    plt.close(fig)
    return path


# ---- 安全的一元函数解析（禁用任意 eval；只允许数学表达式） ----
_EXPR_RE = re.compile(r"^[\w\s\.\+\-\*\/\(\)\^,]+$")  # 仅允许数学字符


def _make_func(expr):
    """把 'x**2-2*x-3' 这类字符串编译成可对 numpy 数组求值的函数。
    用 sympy parse_expr（带 transformations 但不 eval）解析→lambdify(numpy)。
    并把自由符号限定为 {x}、函数调用限定为数学白名单，封堵 __import__/系统调用
    等 RCE 路径。表达式只能包含字母/数字/数学符号字符。"""
    if not isinstance(expr, str) or not _EXPR_RE.match(expr):
        raise ValueError(
            f"非法函数表达式：{expr!r}（仅允许字母/数字/.+-*/()^, 字符；"
            f"合法示例：'x**2-2*x-3'、'sin(x)+cos(x)'、'sqrt(x**2+1)'）")
    import sympy
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations, implicit_multiplication_application)
    x = sympy.symbols("x")
    transformations = standard_transformations + (
        implicit_multiplication_application,)
    e = parse_expr(expr, local_dict={"x": x}, transformations=transformations,
                   evaluate=True)
    # 自由符号白名单
    if not (e.free_symbols <= {x}):
        raise ValueError(f"表达式含未声明符号：{e.free_symbols - {x}}")
    # 函数调用白名单（按 sympy 类名比对，禁止 __import__/getattr 等）
    allowed_func_names = {"sin", "cos", "tan", "asin", "acos", "atan",
                          "sinh", "cosh", "tanh", "exp", "log", "ln",
                          "sqrt", "Abs", "Pow", "Min", "Max"}
    for fn in e.atoms(sympy.Function):
        if fn.func.__name__ not in allowed_func_names:
            raise ValueError(f"表达式含禁用函数：{fn.func.__name__}")
    return sympy.lambdify(x, e, "numpy")


def _fig_function(spec, out_dir):
    funcs = spec.get("funcs") or ([spec["func"]] if spec.get("func") else [])
    if not funcs:
        return None
    xr = spec.get("xrange", [-10, 10])
    xs = np.linspace(float(xr[0]), float(xr[1]), 400)
    fig, ax = plt.subplots(figsize=(spec.get("w", 5), spec.get("h", 4)))
    legends = spec.get("legends") or []
    drew_with_label = False
    drew_any_curve = False
    for i, expr in enumerate(funcs):
        try:
            ys = _make_func(expr)(xs)
        except Exception as ex:
            print(f"[make_figure] 函数 {expr!r} 解析失败：{ex}", file=sys.stderr)
            continue
        ys = np.broadcast_to(np.asarray(ys, dtype=float), xs.shape).copy()
        ys[~np.isfinite(ys)] = np.nan  # 去掉除零/溢出点
        lbl = legends[i] if i < len(legends) and legends[i] else None
        ax.plot(xs, ys, label=lbl, linewidth=1.8)
        drew_any_curve = True
        if lbl:
            drew_with_label = True
    if not drew_any_curve:
        # 所有 funcs 都解析失败 → 不出空白坐标轴图占位，返回 None 让上游降级
        plt.close(fig)
        print(f"[make_figure] funcs 全部解析失败，已放弃生成函数图：{funcs!r}",
              file=sys.stderr)
        return None
    if spec.get("yrange"):
        ax.set_ylim(float(spec["yrange"][0]), float(spec["yrange"][1]))
    # 坐标轴过原点（中学函数图像习惯）
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlabel(spec.get("xlabel", "x"))
    ax.set_ylabel(spec.get("ylabel", "y"))
    if spec.get("title"):
        ax.set_title(spec["title"])
    if drew_with_label:
        ax.legend()
    return _save(fig, _out_path(out_dir, spec))


def _fig_geometry(spec, out_dir):
    """平面几何：points={"A":[x,y],...}; segments=[["A","B"],...];
    polygons=[["A","B","C"],...]; circles=[{"center":"O","r":2}]。"""
    pts = spec.get("points", {})
    if not pts:
        return None
    fig, ax = plt.subplots(figsize=(spec.get("w", 4.5), spec.get("h", 4.5)))
    for poly in spec.get("polygons", []):
        xy = [pts[p] for p in poly if p in pts]
        if len(xy) >= 2:
            xy.append(xy[0])
            xs, ys = zip(*xy)
            ax.plot(xs, ys, color="black", linewidth=1.6)
    for seg in spec.get("segments", []):
        if seg[0] in pts and seg[1] in pts:
            (x1, y1), (x2, y2) = pts[seg[0]], pts[seg[1]]
            ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.6)
    for c in spec.get("circles", []):
        ctr = pts.get(c.get("center"), c.get("center", [0, 0]))
        ax.add_patch(plt.Circle(ctr, float(c["r"]), fill=False,
                                color="black", linewidth=1.6))
    for name, (x, y) in pts.items():
        ax.plot(x, y, "o", color="black", markersize=3)
        ax.annotate(name, (x, y), textcoords="offset points",
                    xytext=(5, 5), fontsize=12)
    ax.set_aspect("equal")
    ax.axis("off")
    if spec.get("title"):
        ax.set_title(spec["title"])
    return _save(fig, _out_path(out_dir, spec))


def _fig_number_line(spec, out_dir):
    lo, hi = float(spec.get("min", -5)), float(spec.get("max", 5))
    if hi < lo:
        lo, hi = hi, lo
    step = float(spec.get("ticks", 1))
    if step <= 0 or not math.isfinite(step):  # 防 ticks=0/负/NaN 死循环
        step = 1
    if (hi - lo) / step > 200:                # 防 range 过大 artist 爆炸
        step = (hi - lo) / 200 or 1
    fig, ax = plt.subplots(figsize=(spec.get("w", 6), spec.get("h", 1.2)))
    ax.axhline(0, color="black", linewidth=1.2)
    t = lo
    while t <= hi + 1e-9:
        ax.plot([t, t], [-0.1, 0.1], color="black", linewidth=1)
        ax.annotate(f"{t:g}", (t, -0.12), ha="center", va="top", fontsize=9)
        t += step
    # 箭头
    ax.annotate("", xy=(hi + step * 0.5, 0), xytext=(lo - step * 0.5, 0),
                arrowprops=dict(arrowstyle="->", color="black"))
    for iv in spec.get("intervals", []):
        a, b = float(iv["from"]), float(iv["to"])
        ax.plot([a, b], [0, 0], color="red", linewidth=3, alpha=0.6)
    for p in spec.get("points", []):
        x = float(p["x"])
        filled = p.get("filled", True)
        ax.plot(x, 0, "o", markersize=9, color="red",
                markerfacecolor="red" if filled else "white")
        if p.get("label"):
            ax.annotate(p["label"], (x, 0.13), ha="center", fontsize=11)
    ax.set_ylim(-0.6, 0.5)
    ax.axis("off")
    return _save(fig, _out_path(out_dir, spec))


def _fig_stats(spec, out_dir):
    kind = spec["kind"]
    fig, ax = plt.subplots(figsize=(spec.get("w", 5), spec.get("h", 4)))
    if kind == "pie":
        ax.pie(spec["values"], labels=spec.get("labels"), autopct="%1.0f%%")
        ax.set_aspect("equal")
    elif kind == "scatter":
        ax.scatter(spec["x"], spec["y"], color="steelblue")
        ax.grid(True, linestyle="--", alpha=0.4)
    elif kind == "line":
        ax.plot(spec["x"], spec["y"], marker="o", color="steelblue")
        ax.grid(True, linestyle="--", alpha=0.4)
    else:  # bar
        ax.bar([str(c) for c in spec["x"]], spec["y"], color="steelblue")
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    if kind != "pie":
        ax.set_xlabel(spec.get("xlabel", ""))
        ax.set_ylabel(spec.get("ylabel", ""))
    if spec.get("title"):
        ax.set_title(spec["title"])
    return _save(fig, _out_path(out_dir, spec))


def _fig_vector(spec, out_dir):
    """受力/矢量图：vectors=[{"start":[0,0],"end":[3,2],"label":"F1","color":"r"}]。"""
    vecs = spec.get("vectors", [])
    if not vecs:
        return None
    fig, ax = plt.subplots(figsize=(spec.get("w", 4.5), spec.get("h", 4.5)))
    xs_all, ys_all = [0], [0]
    for v in vecs:
        x0, y0 = v.get("start", [0, 0])
        x1, y1 = v["end"]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=2,
                                    color=v.get("color", "black")))
        if v.get("label"):
            ax.annotate(v["label"], ((x0 + x1) / 2, (y0 + y1) / 2),
                        textcoords="offset points", xytext=(6, 6), fontsize=12)
        xs_all += [x0, x1]
        ys_all += [y0, y1]
    if spec.get("dot_at_origin", True):
        ax.plot(0, 0, "o", color="black", markersize=6)
    m = 1.0
    ax.set_xlim(min(xs_all) - m, max(xs_all) + m)
    ax.set_ylim(min(ys_all) - m, max(ys_all) + m)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3)
    if spec.get("title"):
        ax.set_title(spec["title"])
    return _save(fig, _out_path(out_dir, spec))


def _fig_climate(spec, out_dir):
    """气候类型图（地理高频）：气温折线(左轴,红) + 降水柱状(右轴,蓝)，x 为 12 个月。
    temp=[12 个月气温], prec=[12 个月降水]，长度须为 12。"""
    temp = spec.get("temp")
    prec = spec.get("prec")
    if not temp or not prec:
        return None
    months = spec.get("months") or [str(i) for i in range(1, 13)]
    fig, ax1 = plt.subplots(figsize=(spec.get("w", 5.5), spec.get("h", 4)))
    ax2 = ax1.twinx()
    ax2.bar(months, prec, color="steelblue", alpha=0.75, width=0.6)
    ax2.set_ylabel(spec.get("prec_label", "降水量 / mm"))
    ax1.plot(months, temp, color="firebrick", marker="o", linewidth=1.8)
    ax1.set_ylabel(spec.get("temp_label", "气温 / ℃"))
    ax1.set_xlabel(spec.get("xlabel", "月份"))
    ax1.set_zorder(ax2.get_zorder() + 1)  # 折线压在柱状之上
    ax1.patch.set_visible(False)
    if spec.get("title"):
        ax1.set_title(spec["title"])
    return _save(fig, _out_path(out_dir, spec))


def _fig_pyramid(spec, out_dir):
    """人口金字塔（地理高频）：左男右女对称水平条形，y 为年龄组。
    ages=["0-14",...], male=[...], female=[...]，三者等长。"""
    ages = spec.get("ages")
    male = spec.get("male")
    female = spec.get("female")
    if not ages or not male or not female:
        return None
    import matplotlib.ticker as mticker
    fig, ax = plt.subplots(figsize=(spec.get("w", 5.5), spec.get("h", 4.5)))
    y = list(range(len(ages)))
    ax.barh(y, [-abs(v) for v in male], color="steelblue",
            label=spec.get("male_label", "男"))
    ax.barh(y, [abs(v) for v in female], color="indianred",
            label=spec.get("female_label", "女"))
    ax.set_yticks(y)
    ax.set_yticklabels(ages)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{abs(v):g}"))
    ax.set_xlabel(spec.get("xlabel", "人口 / %"))
    ax.legend()
    if spec.get("title"):
        ax.set_title(spec["title"])
    return _save(fig, _out_path(out_dir, spec))


_DISPATCH = {
    "function": _fig_function, "plot": _fig_function,
    "geometry": _fig_geometry,
    "number_line": _fig_number_line, "numberline": _fig_number_line,
    "bar": _fig_stats, "line": _fig_stats, "pie": _fig_stats,
    "scatter": _fig_stats,
    "vector": _fig_vector, "force": _fig_vector,
    "climate": _fig_climate,
    "pyramid": _fig_pyramid, "population_pyramid": _fig_pyramid,
}


def render_figure(spec, out_dir):
    """按 spec['kind'] 渲染 PNG，返回路径；不支持的 kind 或渲染失败返回 None
    （调用方据此降级为用户提供图/占位）。"""
    if not isinstance(spec, dict):
        return None
    kind = spec.get("kind")
    fn = _DISPATCH.get(kind)
    if not fn:
        return None  # 电路/化学结构等不在自动可画范围
    try:
        return fn(spec, out_dir)
    except Exception as e:
        print(f"[make_figure] 渲染 kind={kind} 失败：{e}")
        return None


def render_formula(latex, out_dir):
    """把 LaTeX 公式用 matplotlib mathtext 渲成透明背景 PNG（复杂公式用）。
    latex 不带 $；失败返回 None。"""
    if not latex:
        return None
    try:
        fig = plt.figure(figsize=(0.01, 0.01))
        t = fig.text(0, 0, f"${latex}$", fontsize=18)
        path = _out_path(out_dir, "formula:" + latex)
        fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.05,
                    transparent=True)
        plt.close(fig)
        del t
        return path
    except Exception as e:
        print(f"[make_figure] 公式渲染失败：{e}")
        return None


def _selftest(out_dir):
    samples = [
        {"kind": "function", "funcs": ["x**2-2*x-3"], "xrange": [-3, 5],
         "title": "二次函数"},
        {"kind": "function", "funcs": ["sin(x)", "cos(x)"], "xrange": [-6, 6],
         "legends": ["sin x", "cos x"]},
        {"kind": "geometry",
         "points": {"A": [0, 0], "B": [4, 0], "C": [1, 3]},
         "polygons": [["A", "B", "C"]], "title": "三角形ABC"},
        {"kind": "number_line", "min": -3, "max": 3,
         "points": [{"x": 1, "label": "a", "filled": True}],
         "intervals": [{"from": 1, "to": 3}]},
        {"kind": "bar", "x": ["甲", "乙", "丙"], "y": [3, 5, 2],
         "ylabel": "人数", "title": "统计"},
        {"kind": "pie", "values": [40, 35, 25], "labels": ["A", "B", "C"]},
        {"kind": "vector",
         "vectors": [{"start": [0, 0], "end": [3, 0], "label": "F₁"},
                     {"start": [0, 0], "end": [0, 2], "label": "F₂"}],
         "title": "受力分析"},
        {"kind": "climate",
         "temp": [3, 5, 10, 16, 21, 25, 28, 27, 22, 16, 9, 4],
         "prec": [40, 45, 60, 80, 100, 140, 180, 160, 90, 60, 50, 40],
         "title": "某地气候"},
        {"kind": "pyramid", "ages": ["0-14", "15-64", "65+"],
         "male": [20, 55, 8], "female": [18, 53, 12],
         "title": "人口金字塔"},
    ]
    ok = 0
    for s in samples:
        p = render_figure(s, out_dir)
        print(f"  {s['kind']:11} -> {p if p else '✗失败'}")
        ok += 1 if p and os.path.exists(p) else 0
    f = render_formula(r"\int_{0}^{1} x^2\,dx = \frac{1}{3}", out_dir)
    print(f"  {'formula':11} -> {f if f else '✗失败'}")
    ok += 1 if f and os.path.exists(f) else 0
    print(f"[selftest] {ok}/{len(samples)+1} 通过")
    return ok == len(samples) + 1


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        d = sys.argv[2] if len(sys.argv) > 2 else "/tmp/tp_fig_selftest"
        ok = _selftest(d)
        sys.exit(0 if ok else 1)
    print(__doc__)

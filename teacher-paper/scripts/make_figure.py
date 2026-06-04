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
画不了的（电路图/化学结构式/复杂装置/立体几何）：返回 None，由调用方降级为
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
import hashlib

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


def _out_path(out_dir, spec_or_text):
    """按内容算稳定文件名，避免重复渲染、便于缓存。"""
    os.makedirs(out_dir, exist_ok=True)
    key = repr(spec_or_text).encode("utf-8")
    h = hashlib.md5(key).hexdigest()[:12]
    return os.path.join(out_dir, f"fig_{h}.png")


def _save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.1,
                facecolor="white")
    plt.close(fig)
    return path


# ---- 安全的一元函数解析（禁用任意 eval；只允许数学表达式） ----
def _make_func(expr):
    """把 'x**2-2*x-3' 这类字符串编译成可对 numpy 数组求值的函数。
    用 sympy 解析→lambdify(numpy)，避免任意代码执行。sympy 不可用时退回
    受限 eval（仅暴露 numpy 数学函数与符号 x）。"""
    try:
        import sympy
        x = sympy.symbols("x")
        e = sympy.sympify(expr)
        f = sympy.lambdify(x, e, "numpy")
        return f
    except Exception:
        safe = {k: getattr(np, k) for k in
                ("sin", "cos", "tan", "exp", "log", "sqrt", "abs",
                 "pi", "e", "arcsin", "arccos", "arctan", "sinh", "cosh")}

        def f(xv):
            return eval(expr, {"__builtins__": {}}, dict(safe, x=xv))  # noqa: S307
        return f


def _fig_function(spec, out_dir):
    funcs = spec.get("funcs") or ([spec["func"]] if spec.get("func") else [])
    if not funcs:
        return None
    xr = spec.get("xrange", [-10, 10])
    xs = np.linspace(float(xr[0]), float(xr[1]), 400)
    fig, ax = plt.subplots(figsize=(spec.get("w", 5), spec.get("h", 4)))
    legends = spec.get("legends") or []
    for i, expr in enumerate(funcs):
        try:
            ys = _make_func(expr)(xs)
        except Exception:
            continue
        ys = np.asarray(ys, dtype=float)
        ys[~np.isfinite(ys)] = np.nan  # 去掉除零/溢出点
        ax.plot(xs, ys, label=legends[i] if i < len(legends) else None,
                linewidth=1.8)
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
    if any(legends):
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
    step = float(spec.get("ticks", 1))
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


_DISPATCH = {
    "function": _fig_function, "plot": _fig_function,
    "geometry": _fig_geometry,
    "number_line": _fig_number_line, "numberline": _fig_number_line,
    "bar": _fig_stats, "line": _fig_stats, "pie": _fig_stats,
    "scatter": _fig_stats,
    "vector": _fig_vector, "force": _fig_vector,
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

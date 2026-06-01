#!/usr/bin/env python3
"""
原子化组卷器 —— teacher-paper skill 自包含组件
把"每题一个 json 文件"的原子化内容合并成整卷，并调用 make_paper.py 出 Word。
解决资料多时上下文易丢、改一题要重排全卷的问题。详见 references/authoring-workflow.md。

用法：
    # 1) 建工程脚手架（目录 + meta.json + manifest + 大题/小题分隔文件 + 脚本副本）
    #    全学段全科目：--stage 学段 --subject 科目 --region 地区 --type 类型
    #                  --total 总分 --duration 时长 --questions 题量
    #    结构来源优先级：--blueprint-file 样卷结构 > presets/预设 > 内置长沙语文 > 通用兜底
    python3 assemble.py init "<工程目录>" [--stage 九年级] [--subject 语文] [--type 中考模拟]
            [--region 长沙] [--total 120] [--duration 120] [--blueprint-file 结构.json]

    # 2) 合并 items/ 下所有原子文件 → build/content.json → 生成两个 Word
    python3 assemble.py build "<工程目录>"

原子文件（items/NN_*.json）格式：
    {"meta":{"num":"7","score":2,"status":"已出", ...}, "paper":[...], "answer":[...]}
  - NN 为序号前缀（建议3位），控制全卷顺序；section/sub/material 文件可无 num/score。
  - paper/answer 的 block 类型见 make_paper.py 顶部文档。
"""
import sys
import os
import re
import json
import glob
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# 注意事项前 5 条通用，第 6 条按本卷题量/时长/满分动态生成。
_NOTICE_BASE = [
    "答题前，请考生先将自己的姓名、准考证号填写清楚，并认真核对条形码上的"
    "姓名、准考证号；",
    "必须在答题卡上答题，在草稿纸、试题卷上答题无效；",
    "答题时，请考生注意各题题号后面的答题要求；",
    "请勿折叠答题卡，保持字体工整、笔迹清晰、卡面清洁；",
    "答题卡上不准使用涂改液、涂改胶和贴纸；",
]


def _default_notice(questions, duration, total):
    last = "本学科试卷"
    if questions:
        last += f"共{questions}道题目，"
    last += f"考试时量{duration}分钟，满分{total}分。"
    return _NOTICE_BASE + [last]


# 长沙中考语文固定骨架（内置默认，对标 2025 真题原卷版，板块用"共N分"）
SKELETON = [
    ("100_sec_积累运用", "一、积累运用（共20分）"),
    ("110_sub_积累", "（一）积累"),
    ("120_sub_运用", "（二）运用"),
    ("200_sec_阅读", "二、阅读（共50分）"),
    ("210_sub_非连", "（一）非连续性文本阅读（共8分）"),
    ("220_sub_小说", "（二）文学作品阅读（共16分）"),
    ("230_sub_古诗文", "（三）古诗文阅读（共18分）"),
    ("240_sub_名著", "（四）名著阅读（共8分）"),
    ("300_sec_写作", "三、写作（共50分）"),
]

# 长沙九年级语文 manifest（题号·题型·分值·考点·难度）——内置默认
_CHANGSHA_MANIFEST = [
    ("111", "q01", "成语·字音·字形 选择", 2, "字音字形", "0.85"),
    ("112", "q02", "古诗文名句默写", 4, "情境默写", "0.85"),
    ("121", "q03", "病句修改 选择", 2, "语病辨析", "0.7"),
    ("122", "q04", "仿写·创意命名", 4, "语言运用", "0.65"),
    ("123", "q05", "口语交际·信息提炼", 4, "口语交际", "0.65"),
    ("124", "q06", "新闻消息·拟标题", 4, "概括", "0.6"),
    ("212", "q07", "非连·信息理解 选择", 2, "信息筛选", "0.7"),
    ("213", "q08", "非连·分析推断 选择", 2, "推断", "0.65"),
    ("214", "q09", "非连·拓展应用 简答", 4, "迁移应用", "0.55"),
    ("222", "q10", "小说·理解分析 多选", 4, "综合理解", "0.6"),
    ("223", "q11", "小说·结构/手法 简答", 6, "手法分析", "0.5"),
    ("224", "q12", "小说·主旨探究 简答", 6, "探究", "0.45"),
    ("232", "q13", "古诗词·理解赏析 选择", 2, "诗词鉴赏", "0.6"),
    ("233", "q14", "古诗词·手法赏析 简答", 4, "鉴赏", "0.5"),
    ("235", "q15", "文言·实词理解 选择", 2, "文言实词", "0.65"),
    ("236", "q16", "文言·断句 选择", 2, "文言断句", "0.6"),
    ("237", "q17", "文言·翻译", 4, "文言翻译", "0.55"),
    ("238", "q18", "文言·形象/内容 分析", 4, "内容分析", "0.55"),
    ("242", "q19", "名著·理解分析 选择", 2, "名著识记", "0.6"),
    ("243", "q20", "名著·创意探究 简答", 6, "探究", "0.45"),
    ("301", "q21", "作文", 50, "写作", "—"),
]

# 通用学科大题骨架（样卷/预设都缺时的兜底；只给大题分隔，细目靠样卷或人工补）
_GENERIC_SECTIONS = {
    "语文": ["一、积累与运用", "二、阅读", "三、写作"],
    "数学": ["一、选择题", "二、填空题", "三、解答题"],
    "英语": ["一、听力", "二、单项选择", "三、完形填空", "四、阅读理解", "五、书面表达"],
    "物理": ["一、选择题", "二、填空题", "三、实验与作图", "四、计算题"],
    "化学": ["一、选择题", "二、填空与简答", "三、实验探究", "四、计算题"],
    "生物": ["一、选择题", "二、非选择题"],
    "道德与法治": ["一、选择题", "二、非选择题"],
    "政治": ["一、选择题", "二、非选择题"],
    "思想政治": ["一、选择题", "二、非选择题"],
    "历史": ["一、选择题", "二、非选择题"],
    "地理": ["一、选择题", "二、综合题（读图分析）"],
}
# 未列科目按文/理倾向兜底
_GENERIC_DEFAULT = ["一、选择题", "二、非选择题"]

# 预设目录（init 通常从技能 scripts/ 运行，预设在技能根 presets/）
_PRESET_DIRS = [
    os.path.join(os.path.dirname(HERE), "presets"),
    os.path.join(HERE, "presets"),
]


def is_sec_name(name):
    """骨架文件名含 _sec_ 即为大题分隔（兼容任意大题数，不写死前缀）。"""
    return "_sec_" in name


def _changsha_chinese_blueprint():
    return {
        "source": "内置默认·长沙九年级语文",
        "total": 120, "duration": 120, "questions": 21,
        "title": None, "subtitle": None, "notice": None,
        "skeleton": list(SKELETON),
        "manifest": list(_CHANGSHA_MANIFEST),
        "summary": "合计：21题 / 120分（一20·二50·三50）",
    }


def _generic_blueprint(stage, subject, etype):
    secs = _GENERIC_SECTIONS.get(subject, _GENERIC_DEFAULT)
    skeleton = []
    for i, text in enumerate(secs, 1):
        skeleton.append((f"{i}00_sec_{i}", text))
    # 学段给个保守满分/时长默认（务必可被 --total/--duration 覆盖）
    if "小学" in stage or stage in ("一年级", "二年级", "三年级", "四年级",
                                    "五年级", "六年级"):
        total, dur = 100, 90
    elif "高" in stage:
        total, dur = (150 if subject in ("语文", "数学", "英语") else 100), 120
    else:
        total, dur = 100, 120
    return {
        "source": f"通用兜底·{subject}（建议传样卷自动解析以更贴合本地卷）",
        "total": total, "duration": dur, "questions": 0,  # 0=题量未知，跳过题量校验
        "title": None, "subtitle": None, "notice": None,
        "skeleton": skeleton, "manifest": [],
        "summary": f"结构为通用兜底（{len(secs)}个大题），请按本地样卷补充各题题型与分值。",
    }


def _normalize_blueprint(d):
    """把外部蓝图/预设 JSON 补齐字段并统一类型。skeleton/manifest 转成元组列表。"""
    d.setdefault("source", "外部蓝图")
    d.setdefault("total", 120)
    d.setdefault("duration", 120)
    d.setdefault("questions", 0)
    for k in ("title", "subtitle", "notice", "summary"):
        d.setdefault(k, None)
    d["skeleton"] = [tuple(x) for x in d.get("skeleton", [])]
    d["manifest"] = [tuple(x) for x in d.get("manifest", [])]
    return d


def _load_preset(stage, subject, region):
    """按 {stage}_{subject}_{region}.json → {stage}_{subject}.json 查预设。"""
    names = [f"{stage}_{subject}_{region}.json", f"{stage}_{subject}.json"]
    for d in _PRESET_DIRS:
        for n in names:
            fp = os.path.join(d, n)
            if os.path.isfile(fp):
                try:
                    bp = _normalize_blueprint(_read_json(fp))
                    bp["source"] = f"预设 {n}"
                    return bp
                except (json.JSONDecodeError, OSError) as e:
                    print(f"[警告] 预设 {n} 读取失败（{e}），跳过")
    return None


def _resolve_blueprint(stage, subject, region, etype, opt):
    """蓝图解析优先级：样卷蓝图文件 > 预设 > 内置长沙语文 > 通用兜底。"""
    bf = opt.get("blueprint-file")
    if bf:
        try:
            bp = _normalize_blueprint(_read_json(bf))
            bp["source"] = f"样卷蓝图 {os.path.basename(bf)}"
            return bp
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"[警告] --blueprint-file 读取失败（{e}），改用预设/兜底")
    p = _load_preset(stage, subject, region)
    if p:
        return p
    if subject == "语文" and stage in ("九年级", "初三"):
        return _changsha_chinese_blueprint()
    return _generic_blueprint(stage, subject, etype)


# 阅读类素材真实性硬门禁：含选文正文的材料文件禁止编造，
# meta 必须声明 source（来源URL 或 "原创-已声明"）+ source_file（materials/ 下真实文件）。


def cmd_init(args):
    if not args:
        print("用法：assemble.py init <工程目录|工程名>\n"
              "      [--stage 学段] [--subject 科目] [--type 考试类型] [--region 地区]\n"
              "      [--total 总分] [--duration 时长分钟] [--questions 题量]\n"
              "      [--title ..] [--blueprint-file <样卷解析出的结构json>]\n"
              "      [--mode 全程确认|全自动] [--on-desktop] [--decisions '<json>']\n"
              "  说明：结构来源优先级 = 样卷蓝图文件 > presets/预设 > 内置长沙九年级语文 > 通用兜底。\n"
              "       不带参数即默认九年级语文·长沙中考模拟（21题/120分/120分钟）。")
        sys.exit(1)
    proj = args[0]
    opt = _parse_opts(args[1:])

    # 工程位置：传入纯工程名（不含任何路径分隔符）或显式 --on-desktop → 建到桌面
    # 同时判断 / 和 \：Windows 上用户也可能用正斜杠，os.sep 只有 \ 会漏判
    has_sep = ("/" in proj) or ("\\" in proj)
    if not os.path.isabs(proj) and ("--on-desktop" in args or not has_sep):
        desktop = _detect_desktop()
        if desktop:
            proj = os.path.join(desktop, proj)
            print(f"[位置] 未指定项目文件夹，工程建在桌面：{proj}")
        else:
            print(f"[位置] 未探测到桌面目录，工程建在当前目录：{os.path.abspath(proj)}")

    if os.path.exists(os.path.join(proj, "meta.json")):
        print(f"[提示] {proj} 已是工程目录，init 将覆盖 meta.json 与 00_manifest.md "
              f"及 9 个大题分隔文件；items/ 下你写的题目文件不受影响。")
    # 学段/科目/类型/地区：stage 兼容旧 --grade；subject 默认语文
    stage = opt.get("stage", opt.get("grade", "九年级"))
    subject = opt.get("subject", "语文")
    etype = opt.get("type", opt.get("exam-type", "中考模拟"))
    region = opt.get("region", "长沙")
    school = opt.get("school", "")
    mode = opt.get("mode", "全自动")  # 全程确认 / 全自动
    # 决策点：优先从文件读（跨平台稳妥，避免命令行传 JSON 在 Windows 引号问题），
    # 其次从 --decisions 直接传 JSON 字符串（mac/Linux 方便）。
    decisions = {}
    if opt.get("decisions-file"):
        try:
            decisions = _read_json(opt["decisions-file"])
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"[警告] --decisions-file 读取失败（{e}），已忽略")
    elif opt.get("decisions"):
        try:
            decisions = json.loads(opt["decisions"])
        except json.JSONDecodeError:
            print("[警告] --decisions 不是合法 JSON，已忽略")

    # —— 解析本卷蓝图：样卷蓝图 > 预设 > 内置长沙语文 > 通用兜底 ——
    bp = _resolve_blueprint(stage, subject, region, etype, opt)

    def _ovr_int(key, default):
        try:
            return int(opt[key]) if opt.get(key) else default
        except (TypeError, ValueError):
            return default
    total = _ovr_int("total", bp["total"])
    duration = _ovr_int("duration", bp["duration"])
    questions = _ovr_int("questions", bp["questions"])
    title = opt.get("title") or bp.get("title") \
        or f"{stage}{subject}（{etype}）试卷"
    subtitle = opt.get("subtitle") or bp.get("subtitle") \
        or f"（满分：{total}分　时间：{duration}分钟）"
    notice = bp.get("notice") or _default_notice(questions, duration, total)

    for sub in ("", "materials", "items", "build"):
        os.makedirs(os.path.join(proj, sub), exist_ok=True)

    # 把技能脚本复制一份到工程 scripts/，之后在工程内跑，避免误改技能本体脚本。
    _copy_scripts(proj)

    meta = {
        "school": school, "year": "", "term": "",
        "grade": stage, "subject": subject, "exam_type": etype,
        "region": region, "total": total, "duration": duration,
        "expected_questions": questions,
        "title": title,
        "subtitle": subtitle,
        "notice": notice,
        "blueprint_source": bp.get("source", ""),
        "work_mode": mode,          # 工作模式：全程确认 / 全自动
        "decisions": decisions,     # 开工前一次性确定的决策点（作业指导书）
    }
    _write_json(os.path.join(proj, "meta.json"), meta)

    # 写大题/小题分隔文件（按蓝图骨架，大题数不写死）
    for name, text in bp["skeleton"]:
        btype = "section" if is_sec_name(name) else "sub"
        block = {"type": btype, "text": text}
        atom = {"meta": {"status": "-"}, "paper": [block],
                "answer": [block] if btype == "section" else []}
        _write_json(os.path.join(proj, "items", name + ".json"), atom)

    _write_manifest(proj, meta, bp.get("manifest", []), bp.get("summary"))
    _write_json(os.path.join(proj, "items", "_README.json"),
                {"meta": {"note": "本文件不会被合并（无下划线开头排除规则除外）；"
                                  "原子题命名 NN_qXX_描述.json，见 authoring-workflow.md"},
                 "paper": [], "answer": []})
    proj_scripts = os.path.join(proj, "scripts")
    print(f"[完成] 工程已初始化：{proj}")
    print(f"  - 规格：{stage}{subject}·{etype}·{region}　"
          f"{total}分 / {duration}分钟 / {questions or '题量待定'}题")
    print(f"  - 结构来源：{bp.get('source', '')}")
    print(f"  - meta.json / 00_manifest.md 已生成")
    print(f"  - items/ 已含 {len(bp['skeleton'])} 个大题·小题分隔文件")
    if os.path.isdir(proj_scripts):
        print(f"  - scripts/ 已复制技能脚本副本（之后在工程内运行，"
              f"不改技能本体）")
        print(f"  之后请用工程内副本出卷："
              f"\n    python3 \"{os.path.join(proj_scripts, 'assemble.py')}\" "
              f"build \"{proj}\"")
    print(f"  下一步：抓素材到 materials/，逐题写 items/NN_qXX.json，再 build。")


def _copy_scripts(proj):
    """把技能 scripts/ 下的 .py 与 requirements.txt 复制到 工程/scripts/，
    使 AI 在工程内运行、修改脚本时都不触及技能本体。__pycache__ 不复制。"""
    dst = os.path.join(proj, "scripts")
    os.makedirs(dst, exist_ok=True)
    copied = 0
    for fn in os.listdir(HERE):
        if fn.endswith(".py") or fn == "requirements.txt":
            try:
                shutil.copy2(os.path.join(HERE, fn), os.path.join(dst, fn))
                copied += 1
            except OSError as e:
                print(f"[警告] 复制脚本 {fn} 失败：{e}")
    return copied


def _write_manifest(proj, meta, rows, summary=None):
    """rows 来自蓝图（[(前缀,题号,题型,分值,考点,难度)]）；为空（通用兜底）时
    写出空表骨架，提示按样卷补充。"""
    qn = meta.get("expected_questions") or "—"
    lines = [
        f"# {meta['title']} —— 命题进度索引（manifest）",
        "",
        "> 状态：待出 / 已出 / 已审 / 定稿。改某题只动对应 items/NN_qXX.json。",
        "",
        f"- 学段：{meta['grade']}　科目：{meta['subject']}　类型：{meta['exam_type']}"
        f"　地区：{meta['region']}",
        f"- 规格：{qn}题 / {meta['total']}分 / {meta['duration']}分钟",
        f"- 结构来源：{meta.get('blueprint_source', '')}",
        "",
        "| 文件前缀 | 题号 | 题型 | 分值 | 考点 | 难度 | 拟用素材 | 状态 |",
        "|------|------|------|------|------|------|----------|------|",
    ]
    for pre, q, typ, score, kp, diff in rows:
        qnum = q[1:] if isinstance(q, str) and q[:1] == "q" else q
        lines.append(f"| {pre} | {qnum} | {typ} | {score} | {kp} | {diff} |  | 待出 |")
    if not rows:
        lines.append("|  |  | （结构为通用兜底，请按本地样卷补充各题） |  |  |  |  | 待出 |")
    lines += ["", summary or f"合计：{qn}题 / {meta['total']}分", ""]
    with open(os.path.join(proj, "00_manifest.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def cmd_build(args):
    if not args:
        print("用法：assemble.py build <工程目录>")
        sys.exit(1)
    proj = args[0]
    meta_path = os.path.join(proj, "meta.json")
    if not os.path.exists(meta_path):
        print(f"[错误] 找不到 {meta_path}；请先运行：assemble.py init <工程目录>")
        sys.exit(1)
    try:
        meta = _read_json(meta_path)
    except json.JSONDecodeError as e:
        print(f"[错误] meta.json 不是合法 JSON：{e}")
        sys.exit(1)

    paper = [
        {"type": "title", "text": meta.get("title", "试卷")},
        {"type": "subtitle", "text": meta.get("subtitle", "")},
        {"type": "info"},
    ]
    if meta.get("notice"):
        paper.append({"type": "notice", "items": meta["notice"]})
    answers = [
        {"type": "title", "text": meta.get("title", "试卷") + "　参考答案及解析"},
    ]

    files = glob.glob(os.path.join(proj, "items", "*.json"))
    files = [f for f in files if not os.path.basename(f).startswith("_")]
    files = sorted(files, key=_sort_key)  # 自然数排序，避免字典序把"100"排到"90"前

    total = 0
    nums = []
    warn = []
    source_errors = []  # 阅读类素材真实性硬门禁的违规项
    materials_dir = os.path.join(proj, "materials")
    for fp in files:
        try:
            atom = _read_json(fp)
        except json.JSONDecodeError as e:
            warn.append(f"{os.path.basename(fp)} 非合法JSON已跳过（{e}）")
            continue
        p_blocks = atom.get("paper", [])
        a_blocks = atom.get("answer", [])
        if not isinstance(p_blocks, list) or not isinstance(a_blocks, list):
            warn.append(f"{os.path.basename(fp)} 的 paper/answer 不是列表，已跳过（避免内容被逐字符拆散）")
            continue
        paper.extend(p_blocks)
        answers.extend(a_blocks)
        m = atom.get("meta", {})

        # —— 阅读类素材真实性硬门禁 ——
        _check_source(fp, m, p_blocks, materials_dir, source_errors)

        if m.get("score") is not None and str(m.get("status", "")) != "-":
            try:
                total += float(m["score"])
            except (TypeError, ValueError):
                pass
        if m.get("num"):
            nums.append(str(m["num"]))
            if m.get("score") is None:
                warn.append(f"题{m['num']} 缺 score 字段（未计入总分）")

    # 校验（expected_questions=0 表示题量未知/通用兜底 → 跳过题量与分值校验）
    exp_q = meta.get("expected_questions", 21)
    exp_total = meta.get("total", 120)
    if exp_q:
        if len(nums) != exp_q:
            warn.append(f"题量 {len(nums)} ≠ 期望 {exp_q}（题号：{','.join(nums) or '无'}）")
        if abs(total - exp_total) > 0.01:
            warn.append(f"分值合计 {total:g} ≠ 期望 {exp_total}")
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        warn.append(f"题号重复：{','.join(dup)}")

    # —— 选文完整性硬门禁：阅读板块有题却无选文正文 → 学生无法作答，拒绝出卷 ——
    completeness_errors = _check_materials_present(paper)
    # —— 小说选文字数检查（1000-1500 字），越界仅告警不阻断 ——
    _check_novel_length(paper, warn)

    # —— 阅读类素材真实性硬门禁：有违规则拒绝出卷（除非显式 --allow-unsourced）——
    allow_unsourced = "--allow-unsourced" in args
    if completeness_errors:
        print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
        print("\n🔴 [选文完整性门禁] 以下阅读板块有题目却没有选文材料，学生无法作答：")
        for e in completeness_errors:
            print("   - " + e)
        print("\n  阅读题的选文/材料必须随卷给出（material 块且含 paras 正文）。")
        print("  请在该板块补上 material 选文原子文件后重跑 build。")
        if not allow_unsourced:
            print("\n  已拒绝出卷。补齐选文后重跑；如确需强制出卷，加 --allow-unsourced。")
            sys.exit(2)
        print("\n  ⚠️ 你使用了 --allow-unsourced，跳过完整性门禁强制出卷（风险自负）。")
    if source_errors:
        print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
        print("\n🔴 [素材溯源门禁] 以下阅读类素材未通过真实性校验：")
        for e in source_errors:
            print("   - " + e)
        print("\n  阅读材料（非连/小说/古诗文/名著）禁止编造，必须：")
        print("  ① 用 fetch_web.py 抓取真实新闻/科普/古籍原文，落盘到 工程/materials/；")
        print("  ② 在该题 meta 写 source（来源URL/出处）与 source_file（materials/下文件名）；")
        print("  ③ 确属教师原创的现代文，meta.source 显式写 '原创-已声明' 方可放行。")
        if not allow_unsourced:
            print("\n  已拒绝出卷。修正后重跑；如确需强制出卷，加 --allow-unsourced。")
            sys.exit(2)
        print("\n  ⚠️ 你使用了 --allow-unsourced，跳过门禁强制出卷（风险自负）。")

    content = {
        "paper_path": os.path.join(proj, "build",
                                   meta.get("title", "试卷") + ".docx"),
        "answer_path": os.path.join(proj, "build",
                                    meta.get("title", "试卷") + "_参考答案及解析.docx"),
        "paper": paper, "answers": answers,
    }
    cpath = os.path.join(proj, "build", "content.json")
    os.makedirs(os.path.dirname(cpath), exist_ok=True)  # build/ 可能被删
    _write_json(cpath, content)
    md_path = os.path.join(proj, "build", "content.md")
    _write_markdown_bundle(md_path, paper, answers)

    print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
    if warn:
        print("[校验告警] " + "；".join(warn))
    else:
        print("[校验通过] 题量与分值符合期望")

    python_cmd = _python_cmd_with_module("docx")
    if python_cmd != [sys.executable]:
        print("[后端] 当前 Python 缺少 docx，改用：" + " ".join(python_cmd))
    r = subprocess.run(
        python_cmd + [os.path.join(HERE, "make_paper.py"), cpath],
        capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("[make_paper 失败]\n" + r.stderr.strip())
        sys.exit(1)

    # 明确告知成卷位置（绝对路径），方便 AI 转告用户并询问是否打开所在文件夹。
    build_dir = os.path.abspath(os.path.join(proj, "build"))
    print("\n[文件位置] 两份成卷已生成在：")
    print("  目录： " + build_dir)
    print("  试卷： " + os.path.abspath(content["paper_path"]))
    print("  答案： " + os.path.abspath(content["answer_path"]))
    print("  打开所在文件夹（按系统选其一，勿直接打开文件）：")
    print(f"    macOS:   open \"{build_dir}\"")
    print(f"    Windows: explorer \"{build_dir}\"")
    print(f"    Linux:   xdg-open \"{build_dir}\"")


def _write_markdown_bundle(path, paper_blocks, answer_blocks):
    """Export a readable Markdown mirror for Pandoc/MCP/Office fallback paths."""
    parts = [
        "# 学生试卷",
        "",
        _blocks_to_markdown(paper_blocks),
        "",
        "\\pagebreak",
        "",
        "# 参考答案及解析",
        "",
        _blocks_to_markdown(answer_blocks),
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def _blocks_to_markdown(blocks):
    lines = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "title":
            lines += ["# " + str(b.get("text", "")), ""]
        elif t == "subtitle":
            lines += [str(b.get("text", "")), ""]
        elif t == "info":
            lines += ["学校__________ 班级__________ 姓名__________ 考号__________", ""]
        elif t == "notice":
            lines += ["**注意事项：**"]
            for i, item in enumerate(b.get("items", []), 1):
                lines.append(f"{i}. {item}")
            lines.append("")
        elif t == "section":
            lines += ["## " + str(b.get("text", "")), ""]
        elif t == "sub":
            lines += ["### " + str(b.get("text", "")), ""]
        elif t == "para":
            lines += [str(b.get("text", "")), ""]
        elif t == "material":
            if b.get("label"):
                lines += ["**" + str(b.get("label")) + "**", ""]
            if b.get("title"):
                lines += ["#### " + str(b.get("title")), ""]
            if b.get("author"):
                lines += [str(b.get("author")), ""]
            for para in b.get("paras", []):
                lines += [str(para), ""]
        elif t == "table":
            lines.extend(_table_to_markdown(b.get("rows", [])))
            lines.append("")
        elif t == "question":
            num = b.get("num", "")
            score = b.get("score", "")
            head = f"{num}. " if num else ""
            lines += [f"{head}{b.get('text', '')}{score}", ""]
        elif t == "options":
            for opt in b.get("items", []):
                lines.append(str(opt))
            lines.append("")
        elif t == "blank_lines":
            for _ in range(int(b.get("count", 3) or 3)):
                lines.append("____________________________________________")
            lines.append("")
        elif t == "essay_grid":
            lines += [str(b.get("note", "请在作文格内作答。")), "",
                      "> 作文方格纸请以 Word 版为准。", ""]
        elif t == "answer":
            num = b.get("num", "")
            score = b.get("score", "")
            head = f"{num}. " if num else ""
            lines += [f"**{head}{score}** {b.get('text', '')}", ""]
        elif t == "analysis":
            lines += [str(b.get("text", "")), ""]
        elif t == "pagebreak":
            lines += ["\\pagebreak", ""]
        elif t == "spacer":
            lines.append("")
    return "\n".join(lines).strip()


def _table_to_markdown(rows):
    rows = [r for r in (rows or []) if r]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    normalized = [[str(row[i]) if i < len(row) else "" for i in range(width)]
                  for row in rows]
    out = ["| " + " | ".join(normalized[0]) + " |",
           "| " + " | ".join(["---"] * width) + " |"]
    for row in normalized[1:]:
        out.append("| " + " | ".join(row) + " |")
    return out


def _python_cmd_with_module(module):
    candidates = [[sys.executable]]
    for name in ("python3", "python"):
        p = _which(name)
        if p:
            candidates.append([p])
    if os.name == "nt":
        py = _which("py")
        if py:
            candidates.append([py, "-3"])
    seen = set()
    for cmd in candidates:
        key = tuple(cmd)
        if key in seen:
            continue
        seen.add(key)
        try:
            r = subprocess.run(cmd + ["-c", f"import {module}"],
                               capture_output=True, timeout=8)
        except Exception:
            continue
        if r.returncode == 0:
            return cmd
    return [sys.executable]


def _which(name):
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        path = os.path.join(folder, name)
        if os.name == "nt":
            for suffix in ("", ".exe", ".bat", ".cmd"):
                p = path + suffix
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p
        elif os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


# 无值布尔开关：出现即为 True，不吞掉后一个参数
_BOOL_FLAGS = {"on-desktop", "allow-unsourced"}


def _parse_opts(args):
    opt = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if "=" in key:                      # 支持 --key=value 写法
                k, v = key.split("=", 1)
                opt[k] = v
                i += 1
            elif key in _BOOL_FLAGS:             # 布尔开关，不取值
                opt[key] = True
                i += 1
            else:
                val = args[i + 1] if i + 1 < len(args) else ""
                opt[key] = val
                i += 2
        else:
            i += 1
    return opt


# 阅读板块小标题关键词（这些板块必须随卷给出选文，否则学生无法作答）
_READING_SUBS = ("非连", "非文学", "文学作品", "小说", "散文", "古诗文",
                 "诗歌", "文言", "名著")


def _check_materials_present(paper):
    """遍历成卷 paper：每个阅读类小标题(sub)区间内，若有题目(question)却没有任何
    带正文(paras)的选文(material)，判为'有题无文'，返回违规板块列表（阻断出卷）。
    古诗文板块常含古诗词+文言文两篇选文，只要该区间至少有一篇选文即视为通过。"""
    errors = []
    region, has_mat, has_q = None, False, False

    def _flush():
        if region and any(k in region for k in _READING_SUBS) and has_q \
                and not has_mat:
            errors.append(f"{region}：有题目但缺选文材料（material 含 paras 正文）")

    for b in paper:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "sub":
            _flush()
            region, has_mat, has_q = b.get("text", ""), False, False
        elif t == "section":
            _flush()
            region, has_mat, has_q = None, False, False
        elif t == "material" and b.get("paras"):
            has_mat = True
        elif t == "question":
            has_q = True
    _flush()
    return errors


def _novel_text_len(paras):
    """统计选文正文净字数（去空白/换行）。"""
    return sum(len(re.sub(r"\s", "", str(p))) for p in (paras or []))


def _check_novel_length(paper, warn):
    """小说(文学作品)选文字数应在 1000-1500；越界加入告警（不阻断）。
    识别：处于'小说/文学作品'小标题区间内、layout 非 verse 的 material 选文。"""
    region = None
    for b in paper:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t in ("sub", "section"):
            region = b.get("text", "") if t == "sub" else None
        elif t == "material" and b.get("paras") and region \
                and ("小说" in region or "文学作品" in region) \
                and b.get("layout") != "verse":
            n = _novel_text_len(b.get("paras"))
            if n < 1000 or n > 1500:
                warn.append(f"小说选文约 {n} 字，建议 1000-1500 字"
                            f"（{'偏短' if n < 1000 else '偏长'}）")


def _needs_source(meta, paper_blocks):
    """判断该原子文件是否承载'阅读选文/材料'，需强制溯源。
    只对真正含选文正文的文件把关（共享材料文件，或题目自带 material 正文块），
    不牵连同篇选文下只有题干/选项的小题文件——那些选文真实性由材料文件负责。"""
    for b in paper_blocks:
        if isinstance(b, dict) and b.get("type") == "material":
            if b.get("paras") or b.get("title"):  # 带实质正文才算选文
                return True
    return False


def _check_source(fp, meta, paper_blocks, materials_dir, errors):
    """阅读类素材必须声明 source + source_file，且 source_file 真实存在。
    source 允许两类：来源URL/出处，或显式标注 '原创-已声明'（教师自知并担责）。"""
    if not _needs_source(meta, paper_blocks):
        return
    name = os.path.basename(fp)
    source = str(meta.get("source", "")).strip()
    sfile = str(meta.get("source_file", "")).strip()
    if not source:
        errors.append(f"{name}：阅读类素材缺 meta.source（须填来源URL/出处，"
                      f"或显式写 '原创-已声明'）")
    is_original = "原创" in source
    if not is_original:
        # 非原创（即取自真实文献/新闻）必须有落盘原文佐证
        if not sfile:
            errors.append(f"{name}：缺 meta.source_file（真实素材须把抓取原文落盘 "
                          f"materials/ 并在此指向该文件）")
        elif not os.path.exists(os.path.join(materials_dir, sfile)):
            errors.append(f"{name}：source_file 指向的 materials/{sfile} 不存在"
                          f"（禁止凭空编造真实素材）")


def _detect_desktop():
    """跨平台探测真实桌面目录，返回绝对路径或 None。
    Windows：先查注册库的 Desktop 项（兼容中文'桌面'/OneDrive 重定向），再回退常见名。
    macOS/Linux：~/Desktop，再回退 XDG 的 Desktop。"""
    home = os.path.expanduser("~")
    # Windows：注册表 Shell Folders 里的 Desktop 才是真实路径
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            val, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            val = os.path.expandvars(val)
            if os.path.isdir(val):
                return val
        except Exception:
            pass
    # 常见候选（含中文桌面、OneDrive 下的桌面）
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "桌面"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive", "桌面"),
    ]
    # Linux XDG
    xdg = os.path.join(home, ".config", "user-dirs.dirs")
    if os.path.isfile(xdg):
        try:
            with open(xdg, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("XDG_DESKTOP_DIR"):
                        raw = line.split("=", 1)[1].strip().strip('"')
                        raw = raw.replace("$HOME", home)
                        if os.path.isdir(raw):
                            return raw
        except Exception:
            pass
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def _sort_key(path):
    """按文件名前缀数字自然排序，无数字前缀的排到最后。"""
    name = os.path.basename(path)
    m = re.match(r"(\d+)", name)
    return (int(m.group(1)) if m else 10 ** 9, name)


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("init", "build"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "init":
        cmd_init(sys.argv[2:])
    else:
        cmd_build(sys.argv[2:])


if __name__ == "__main__":
    main()

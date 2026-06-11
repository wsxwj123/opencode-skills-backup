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

# 注意事项：分"卷面直接作答"（本技能默认，因不生成答题卡）与"用答题卡"两套，
# 避免出现"卷面没答题卡却让在答题卡上答题"的自相矛盾。末条按题量/时长/满分动态生成。
_NOTICE_PAPER = [  # 卷面直接作答（默认）
    "答题前，请将自己的姓名、班级、考号等信息填写在试卷密封线内的指定位置；",
    "请用黑色字迹的签字笔或钢笔，在试卷上对应题目处作答，字迹工整、卷面清洁；",
    "答题时请注意各题题号后面的答题要求；",
    "不得使用涂改液、涂改胶；如需修改，可划去后在旁边订正。",
]
_NOTICE_SHEET = [  # 配套答题卡（仅当用户明确使用答题卡时）
    "答题前，请考生先将自己的姓名、准考证号填写清楚，并认真核对条形码上的"
    "姓名、准考证号；",
    "必须在答题卡上答题，在草稿纸、试题卷上答题无效；",
    "答题时，请考生注意各题题号后面的答题要求；",
    "请勿折叠答题卡，保持字体工整、笔迹清晰、卡面清洁；",
    "答题卡上不准使用涂改液、涂改胶和贴纸；",
]


def _default_notice(questions, duration, total, answer_method="卷面作答"):
    base = _NOTICE_SHEET if str(answer_method).strip() in ("答题卡", "涂卡") \
        else _NOTICE_PAPER
    last = "本学科试卷"
    if questions:
        last += f"共{questions}道题目，"
    last += f"考试时量{duration}分钟，满分{total}分。"
    return base + [last]


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
    ("233", "q14", "古诗词·手法赏析 简答", 5, "鉴赏", "0.5"),
    ("235", "q15", "文言·实词理解 选择", 2, "文言实词", "0.65"),
    ("236", "q16", "文言·断句 选择", 2, "文言断句", "0.6"),
    ("237", "q17", "文言·翻译", 3, "文言翻译", "0.55"),
    ("238", "q18", "文言·形象/内容 分析", 4, "内容分析", "0.55"),
    ("242", "q19", "名著·理解分析 选择", 2, "名著识记", "0.6"),
    ("243", "q20", "名著·创意探究 简答", 6, "探究", "0.45"),
    ("301", "q21", "作文", 50, "写作", "—"),
]

# 通用学科大题骨架（样卷/预设都缺时的兜底；只给大题分隔，细目靠样卷或人工补）
_GENERIC_SECTIONS = {
    "语文": ["一、积累与运用", "二、阅读", "三、写作"],
    "英语": ["一、听力", "二、单项选择", "三、完形填空", "四、阅读理解", "五、书面表达"],
    "道德与法治": ["一、选择题", "二、非选择题（材料分析）"],
    "政治": ["一、选择题", "二、非选择题（材料分析）"],
    "思想政治": ["一、选择题", "二、非选择题（材料分析）"],
    "历史": ["一、选择题", "二、非选择题（材料解析）"],
    "地理": ["一、选择题", "二、综合题（材料分析）"],
    "数学": ["一、选择题", "二、填空题", "三、解答题"],
    "物理": ["一、选择题（单选+多选）", "二、填空与实验探究题", "三、综合计算题"],
    "化学": ["一、选择题（单选+不定项）", "二、填空与简答题", "三、实验探究题", "四、计算题"],
    "生物": ["一、选择题", "二、非选择题（识图·实验·遗传分析）"],
}
# 未列科目按通用兜底（选择 + 非选择）
_GENERIC_DEFAULT = ["一、选择题", "二、非选择题"]
# 理科科目：题目常含图形，出卷时须提醒用户手动补图；程序层面不拦截（有预设文件即加载）
_FIGURE_HEAVY_SUBJECTS = ("数学", "物理", "化学", "生物")

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
        total, dur = (150 if subject in ("语文", "英语") else 100), 120
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


# 科目别名：政治/道法 等异名归一到预设的规范名，避免为每个异名复制一份预设文件。
_SUBJECT_ALIASES = {
    "政治": "思想政治", "道德与法治": "思想政治", "道法": "思想政治",
}


def _load_preset(stage, subject, region):
    """查预设：按 [本名→别名] × [{stage}_{subject}_{region} → {stage}_{subject}] 顺序。
    region 非"通用"时若无地区专版，自动回退到基名（基名即通用版，无需复制 _通用 文件）。"""
    subjects = [subject]
    alias = _SUBJECT_ALIASES.get(subject)
    if alias and alias not in subjects:
        subjects.append(alias)
    names = []
    for sub in subjects:
        names.append(f"{stage}_{sub}_{region}.json")
        names.append(f"{stage}_{sub}.json")
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
              "      [--answer-method 卷面作答|答题卡] [--sealing-line true]\n"
              "      [--page-number false] [--scope 范围] [--textbook 版本] [--answer-detail 详细|简略]\n"
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
    # 先记下"CLI 是否显式给了值"，未给的稍后用蓝图自带字段回填（蓝图自描述）
    stage_cli = opt.get("stage", opt.get("grade"))
    subject_cli = opt.get("subject")
    etype_cli = opt.get("type", opt.get("exam-type"))
    region_cli = opt.get("region")
    stage = stage_cli or "九年级"
    subject = subject_cli or "语文"
    etype = etype_cli or "中考模拟"
    region = region_cli or "长沙"
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
    # 蓝图（样卷/预设）自带学段·科目·地区·类型时，CLI 未显式指定则以蓝图为准，
    # 避免「样卷是七年级北京，却被默认成九年级长沙」的张冠李戴。
    if not stage_cli and bp.get("stage"):
        stage = bp["stage"]
    if not subject_cli and bp.get("subject"):
        subject = bp["subject"]
    if not etype_cli and bp.get("exam_type"):
        etype = bp["exam_type"]
    if not region_cli and bp.get("region"):
        region = bp["region"]

    # 英语含听力大题时（预设或兜底皆可能）：纯文字卷无音频，须先与用户三选一。
    if subject == "英语" and any("听力" in str(t) for _, t in bp.get("skeleton", [])):
        print("[提示] 本卷英语含『听力』大题，但本技能出纯文字卷无音频。"
              "请先与用户三选一：①省略听力(分值并入其它板块) ②附听力文字稿当阅读 "
              "③用户自备音频(本卷只出题干选项)；据此再决定是否保留听力大题。")
    # B1修复：理科科目（有配图需求）无论走预设还是兜底，均在 init 时提示手动补图。
    if subject in _FIGURE_HEAVY_SUBJECTS:
        print(f"[提示] 『{subject}』理科题目常含图形（电路图/几何图/坐标图/装置图等），"
              f"本技能文字卷不自动配图。"
              f"含图题请在题干用文字描述代替，或用 figure 块由用户提供图片；"
              f"build 在缺图处输出 ［图：…］ 占位，需人工补图后交付。")

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
    # 作答方式：默认"卷面作答"（本技能不生成答题卡）；用户用答题卡时传 --answer-method 答题卡
    answer_method = opt.get("answer-method") or bp.get("answer_method") or "卷面作答"
    notice = bp.get("notice") or _default_notice(questions, duration, total,
                                                 answer_method)

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
        "answer_method": answer_method,   # 卷面作答（默认）/ 答题卡
        # 卷面工程项（AI 可按用户需求改）：页码默认开；密封线默认关；
        "page_number": _opt_bool(opt.get("page-number"), True),
        "sealing_line": _opt_bool(opt.get("sealing-line"), False),
        "exam_scope": opt.get("scope", ""),       # 考试范围/单元/课次
        "textbook": opt.get("textbook", ""),      # 教材版本/册次
        "answer_detail": opt.get("answer-detail", "详细"),  # 答案解析详略：详细/简略/含采分点
    }
    # 小说选文字数区间：蓝图指定则带上，build 校验按此；默认（不写）即 1000-1500。
    if bp.get("novel_len"):
        meta["novel_len"] = bp["novel_len"]
    # 各板块字数区间：蓝图/预设显式给 block_len 优先；否则按科目内置默认（仅语文）；
    # 旧字段 novel_len 兼容并入 block_len["小说"]。build 按此表做字数门禁。
    block_len = bp.get("block_len") or _default_block_len(stage, subject)
    if bp.get("novel_len"):
        block_len = dict(block_len)
        block_len["小说"] = bp["novel_len"]
    if block_len:
        meta["block_len"] = block_len
    _write_json(os.path.join(proj, "meta.json"), meta)

    # 写大题/小题分隔文件（按蓝图骨架，大题数不写死）
    # B4修复：re-init 时跳过已存在的分隔文件，保留用户可能做过的修改。
    for name, text in bp["skeleton"]:
        fp_sec = os.path.join(proj, "items", name + ".json")
        if os.path.exists(fp_sec):
            continue  # 已有则保留，不覆盖
        btype = "section" if is_sec_name(name) else "sub"
        block = {"type": btype, "text": text}
        atom = {"meta": {"status": "-"}, "paper": [block],
                "answer": [block] if btype == "section" else []}
        _write_json(fp_sec, atom)

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
            except shutil.SameFileError:
                copied += 1  # B7修复：源=目标（在技能目录内 init），静默跳过
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
        # B8修复："q01-q10" → "01-10"，"q01" → "01"
        if isinstance(q, str) and q[:1] == "q":
            qnum = q[1:].replace("-q", "-")
        else:
            qnum = q
        lines.append(f"| {pre} | {qnum} | {typ} | {score} | {kp} | {diff} |  | 待出 |")
    if not rows:
        lines.append("|  |  | （结构为通用兜底，请按本地样卷补充各题） |  |  |  |  | 待出 |")
    lines += ["", summary or f"合计：{qn}题 / {meta['total']}分", ""]
    with open(os.path.join(proj, "00_manifest.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _find_soffice():
    """找 LibreOffice/soffice 可执行文件（docx→pdf 转换器）。"""
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac if os.path.exists(mac) else None


def _export_pdf(docx_paths, out_dir):
    """把 docx 批量转 PDF。优先 LibreOffice；没有则提示用户用 Word/WPS 手动导出。"""
    soffice = _find_soffice()
    if not soffice:
        print("[PDF] 未找到 LibreOffice/soffice，无法自动转 PDF。"
              "可用 Word/WPS/Pages 打开 docx 后『另存为/导出 PDF』。")
        return
    ok = 0
    for dp in docx_paths:
        try:
            r = subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf",
                 "--outdir", out_dir, dp],
                capture_output=True, text=True, timeout=120)
            pdf = os.path.splitext(dp)[0] + ".pdf"
            if r.returncode == 0 and os.path.exists(pdf):
                print(f"[PDF] 已生成：{pdf}")
                ok += 1
            else:
                print(f"[PDF] 转换失败：{os.path.basename(dp)}　{r.stderr.strip()[:200]}")
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"[PDF] 转换异常：{os.path.basename(dp)}　{e}")
    return ok


def _cleanup_nul_files(project_dir, warn):
    """清理名为 NUL 的残留文件：cmd 风格重定向（>NUL / 2>NUL）在 Windows 的
    Git Bash 下不会指向空设备，而是真的创建一个名为 NUL 的文件。
    Windows 原生 API 删除保留名文件需要 \\\\?\\ 前缀。"""
    for root, _dirs, fnames in os.walk(project_dir):
        for name in fnames:
            if name.upper() != "NUL":
                continue
            fp = os.path.join(root, name)
            try:
                os.remove(fp)
            except OSError:
                removed = False
                if os.name == "nt":
                    try:
                        os.remove("\\\\?\\" + os.path.abspath(fp))
                        removed = True
                    except OSError:
                        pass
                if not removed:
                    warn.append(f"发现残留文件 {fp}（疑似 '>NUL' 重定向误生成），自动删除失败，请手动删除")
                    continue
            warn.append(f"已清理残留文件 {fp}——由 cmd 风格 '>NUL' 重定向误生成，命令一律用 bash 语法，不要重定向到 NUL")


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
    if meta.get("sealing_line"):       # 密封线（仅试卷，紧跟填写区）
        paper.append({"type": "sealing"})
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
    _cleanup_nul_files(proj, warn)
    # B3修复：同一数字前缀的多个 _sec_ 文件会重复输出大题标题，只保留第一个。
    _seen_sec_prefix = set()
    _deduped = []
    for _f in files:
        _bn = os.path.basename(_f)
        if is_sec_name(_bn):
            _prefix = _sort_key(_f)[0]
            if _prefix in _seen_sec_prefix:
                warn.append(f"{_bn} 与同前缀大题分隔文件重复，已跳过（避免标题重复）")
                continue
            _seen_sec_prefix.add(_prefix)
        _deduped.append(_f)
    files = _deduped
    source_errors = []  # 阅读类素材真实性硬门禁的违规项
    figure_errors = []  # 缺图硬门禁：题干含"如图"但无 figure block
    allow_missing_fig = "--allow-missing-figure" in args
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
        is_question = (m.get("score") is not None and str(m.get("status", "")) != "-")

        # —— 缺图硬门禁：题干含"如图/图中/图所示"等图引用字样但 paper 无 figure 块 ——
        if is_question:
            _check_missing_figure(fp, p_blocks, figure_errors)

        # —— 阅读类素材真实性硬门禁 ——
        _check_source(fp, m, p_blocks, materials_dir, source_errors, warn)

        if is_question:
            try:
                total += float(m["score"])
            except (TypeError, ValueError):
                pass
        if m.get("num"):
            nums.append(str(m["num"]))
            if m.get("score") is None:
                warn.append(f"题{m['num']} 缺 score 字段（未计入总分）")

    # 校验（expected_questions=0 表示题量未知/通用兜底/题量待定预设 → 跳过题量门禁，但仍校验总分）
    exp_q = meta.get("expected_questions", 21)
    exp_total = meta.get("total", 120)
    if exp_q:
        if len(nums) != exp_q:
            warn.append(f"题量 {len(nums)} ≠ 期望 {exp_q}（题号：{','.join(nums) or '无'}）")
        if abs(total - exp_total) > 0.01:
            warn.append(f"分值合计 {total:g} ≠ 期望 {exp_total}")
    else:
        # B6修复：题量未知时仍校验总分（total 来自预设，是可信期望值）；只跳过题量门禁。
        warn.append(f"⚠️题量门禁已跳过（预设未指定固定题量）；"
                    f"当前实得 {len(nums)} 题/合计 {total:g} 分，目标总分 {exp_total}。"
                    f"请务必向用户确认大题题型与分值分布（或提供样卷 --blueprint-file）再定稿。")
        if total > 0 and abs(total - exp_total) > 0.01:
            warn.append(f"分值合计 {total:g} ≠ 期望 {exp_total}（题量门禁跳过，但分值校验仍有效）")
    nums_norm = [n.lstrip("0") or "0" for n in nums]
    dup = sorted({n for n in nums_norm if nums_norm.count(n) > 1})
    if dup:
        warn.append(f"题号重复：{','.join(dup)}")

    # —— 选文完整性硬门禁：阅读板块有题却无选文正文 → 学生无法作答，拒绝出卷 ——
    completeness_errors = _check_materials_present(paper)
    # —— 选文字数门禁：按板块校验（区间来自 meta.block_len；旧工程回退 novel_len/小说默认）——
    length_errors = _check_block_lengths(paper, meta.get("block_len"),
                                         meta.get("subject", ""), meta.get("novel_len"))

    # —— 选文出处措辞：真实性铁律要求忠实节选，标注应为'节选自'而非'改编自' ——
    _check_material_wording(paper, warn)

    # —— 政史地史实/数据真实性提醒：溯源门禁只覆盖 material 选文块，题干内嵌的
    #    史实/年代/数据/地名等不触发门禁，须人工核验，不可编造。——
    _subj = str(meta.get("subject", ""))
    if any(k in _subj for k in ("历史", "地理", "政治", "道德与法治", "道法")):
        warn.append(f"⚠️『{_subj}』题干内嵌的史实/年代/数据/地名不受溯源门禁覆盖，"
                    f"请人工核验真实性，严禁编造（地图/图表需用户提供）。")

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

    # —— 缺图硬门禁：题干含"如图"但 paper 无 figure block ——
    if figure_errors:
        print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}",
              file=sys.stderr)
        print("\n🔴 [缺图门禁] 以下题目题干引用了图，但 paper 块里没有 figure 块：", file=sys.stderr)
        for e in figure_errors:
            print("   - " + e, file=sys.stderr)
        print("\n  含图题须在 figure 块写 src=用户提供的图片路径，或把题干改为纯文字描述。", file=sys.stderr)
        if not allow_missing_fig:
            print("\n  已拒绝出卷。补图后重跑；如确需带 ［图：alt］ 占位强制出卷，加 --allow-missing-figure。",
                  file=sys.stderr)
            sys.exit(2)
        print("\n  ⚠️ 你使用了 --allow-missing-figure，缺图位置将留 ［图：alt］ 文字占位（学生可能看不懂题）。",
              file=sys.stderr)

    # —— 选文字数门禁：越界默认拒绝出卷（--allow-length 降级为告警）——
    allow_length = "--allow-length" in args
    if length_errors:
        if allow_length:
            warn.extend(e + "（--allow-length 已降级为告警）" for e in length_errors)
        else:
            print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
            print("\n🔴 [字数门禁] 以下选文字数越界（区间来自 meta.block_len，"
                  "默认值见对应科目文档第 2 节）：")
            for e in length_errors:
                print("   - " + e)
            print("\n  已拒绝出卷。请补充/精简选文（同步修订 materials/ 原文节选范围）后重跑；")
            print("  如确需越界出卷，加 --allow-length（降级为告警，须告知用户字数不达标）。")
            sys.exit(2)

    content = {
        "paper_path": os.path.join(proj, "build",
                                   meta.get("title", "试卷") + ".docx"),
        "answer_path": os.path.join(proj, "build",
                                    meta.get("title", "试卷") + "_参考答案及解析.docx"),
        "paper": paper, "answers": answers,
        "meta": meta,   # 透传页码/密封线等渲染选项给 make_paper
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

    # 可选：导出 PDF（--pdf）。需本机有 LibreOffice/soffice，否则提示手动导出。
    if "--pdf" in args or meta.get("output_pdf"):
        _export_pdf([os.path.abspath(content["paper_path"]),
                     os.path.abspath(content["answer_path"])],
                    os.path.abspath(os.path.join(proj, "build")))

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
            if b.get("source"):
                lines += [str(b.get("source")), ""]
        elif t == "figure":
            spec = b.get("spec", b)
            lines += [f"［图：{spec.get('alt', '此处应有配图，请手动补充')}］", ""]
        elif t == "table":
            lines.extend(_table_to_markdown(b.get("rows", [])))
            lines.append("")
        elif t == "question":
            num = b.get("num", "")
            score = b.get("score", "")
            text = b.get("text", "")
            # B5修复：若 text 已以 "N." 或 "N、" 或 "N．" 开头则不再加前缀，避免双重题号。
            if num and not any(text.startswith(f"{num}{sep}") for sep in (".", "、", "．", " ")):
                head = f"{num}. "
            else:
                head = ""
            lines += [f"{head}{text}{score}", ""]
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
_BOOL_FLAGS = {"on-desktop", "allow-unsourced", "pdf"}


def _opt_bool(val, default):
    """把命令行字符串/None 解析成布尔；None→default，false/0/no/off→False，其余→True。"""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() not in ("false", "0", "no", "off", "否", "关")


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


def _novel_text_len(paras, is_english=False):
    """统计选文正文长度：中文按净字数（去空白），英文按单词数。"""
    if is_english:
        return sum(len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", str(p)))
                   for p in (paras or []))
    return sum(len(re.sub(r"\s", "", str(p))) for p in (paras or []))


# 板块识别关键词（顺序匹配，先匹配先得；material.block 显式声明优先于推断）
_BLOCK_KEYWORDS = (("非连", "非连"), ("非文学", "非连"), ("信息类", "非连"),
                   ("散文", "散文"), ("小说", "小说"), ("文学作品", "小说"),
                   ("文言", "文言"), ("名著", "名著"))


def _default_block_len(stage, subject):
    """按科目给出各板块默认字数区间（净字数）。
    仅语文有内置默认（九年级规格，与 references/subjects/语文.md 第2节区间表一致）；
    其它科目无默认——蓝图/预设显式给 block_len 才校验（英语词数必须显式给）。"""
    if "语文" in str(subject):
        return {"非连": [600, 1000], "小说": [1000, 1500],
                "散文": [800, 1200], "文言": [100, 200]}
    return {}


def _check_block_lengths(paper, block_len, subject="", legacy_novel_len=None):
    """按板块校验选文字数/词数，返回 errors 列表（默认阻断，--allow-length 降级告警）。
    板块归属：material.block 显式声明优先；否则按所在 sub 小标题关键词推断。
    同一 sub 区间内同板块多则材料求和（非连"合计 600-1000"语义）。
    跳过：layout=verse（古诗词不按字数）、推断不出板块、板块无配置区间。
    旧工程兼容：meta 无 block_len 时回退 {"小说": novel_len or [1000,1500]}
    （英语卷无显式区间则不校验，中文默认区间不适用）。"""
    is_english = "英语" in str(subject)
    if not block_len:
        if is_english and not legacy_novel_len:
            return []
        block_len = {"小说": legacy_novel_len or [1000, 1500]}
    unit = "词" if is_english else "字"
    sums, order = {}, []          # 按 (sub区间序号, 板块) 求和
    region, region_idx = None, 0
    for b in paper:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t in ("sub", "section"):
            region = b.get("text", "") if t == "sub" else None
            region_idx += 1
        elif t == "material" and b.get("paras") and b.get("layout") != "verse":
            blk = b.get("block")
            if not blk and region:
                blk = next((v for k, v in _BLOCK_KEYWORDS if k in region), None)
            if not blk or blk not in block_len:
                continue
            key = (region_idx, blk)
            if key not in sums:
                sums[key] = 0
                order.append(key)
            sums[key] += _novel_text_len(b.get("paras"), is_english)
    errors = []
    for key in order:
        blk = key[1]
        try:
            lo, hi = int(block_len[blk][0]), int(block_len[blk][1])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        n = sums[key]
        if n < lo or n > hi:
            errors.append(f"『{blk}』选文合计约 {n} {unit}，要求 {lo}-{hi} {unit}"
                          f"（{'偏短' if n < lo else '偏长'}）——请补充/精简选文，"
                          f"或调整 meta.block_len 区间")
    return errors


def _needs_source(meta, paper_blocks):
    """判断该原子文件是否承载'阅读选文/材料'，需强制溯源。
    只对真正含选文正文的文件把关（共享材料文件，或题目自带 material 正文块），
    不牵连同篇选文下只有题干/选项的小题文件——那些选文真实性由材料文件负责。"""
    for b in paper_blocks:
        if isinstance(b, dict) and b.get("type") == "material":
            if b.get("paras") or b.get("title"):  # 带实质正文才算选文
                return True
    return False


_USER_SRC_HINTS = ("用户提供", "用户提交", "用户给", "截图", "誊录", "手抄",
                   "扫描件", "纸质")


_WORDING_BAD = ("改编", "改写", "编译", "整理自", "据原文改", "综合整理", "编写自")


def _check_material_wording(paper, warn):
    """选文出处标注措辞校验（软提醒）：material.source 出现'改编/改写/编译/整理自…'等
    暗示二次创作的措辞时提醒改'节选自'。真实性铁律要求忠实节选——逐字、可删减，
    禁重排/改写/编造，故标注应为'节选自'。"""
    for b in paper:
        if isinstance(b, dict) and b.get("type") == "material":
            src = str(b.get("source", ""))
            hit = [w for w in _WORDING_BAD if w in src]
            if hit:
                warn.append(f"选文出处『{src}』含{'/'.join(hit)}——按真实性铁律须忠实节选"
                            f"（逐字可删减、禁重排改写编造），标注请改为'节选自…'。")


_FIG_CUES = ("如图", "如下图", "下图", "图中", "图所示", "根据图", "看图",
             "观察图", "请看图", "依据图")


def _check_missing_figure(fp, paper_blocks, errors):
    """题干含'如图/如下图/图中/图所示'等图引用字样，但 paper 块里没有 figure block
    （也没有 src 提供的图）→ 拒绝出卷。AI 不能写出"如图所示"却不给图。"""
    has_fig = any(isinstance(b, dict) and b.get("type") == "figure" for b in paper_blocks)
    if has_fig:
        return
    for b in paper_blocks:
        if not isinstance(b, dict):
            continue
        text = str(b.get("text", "")) + str(b.get("stem", ""))
        for opt in (b.get("options") or b.get("items") or []):
            text += str(opt)
        if any(cue in text for cue in _FIG_CUES):
            errors.append(f"{os.path.basename(fp)}：题干含『{next(c for c in _FIG_CUES if c in text)}』"
                          f"等图引用字样，但 paper 块里没有 figure 块——必须补图"
                          f"（figure 块写 src=用户提供的图片，或把题干改为纯文字描述）。")
            return


_FETCH_CRED_MARK = "teacher-paper:fetched"


def _parse_fetch_credential(text):
    """解析 materials 文件抓取凭证头。返回 dict(url=..., chars=..., sha256=...) 或 None。
    凭证头由 fetch_web.py --save 写入，结构：
        <!-- teacher-paper:fetched
        url: <真实 URL>
        strategy: jina/readability/raw
        chars: <字节数>
        sha256: <内容哈希>
        fetched_at: <时间戳>
        -->
    """
    if not text or _FETCH_CRED_MARK not in text:
        return None
    head = text[:1500]                # 凭证须在文件头，不在文末手补
    if _FETCH_CRED_MARK not in head:
        return None
    info = {}
    for line in head.splitlines():
        line = line.strip()
        for key in ("url", "chars", "sha256", "strategy"):
            if line.startswith(key + ":"):
                info[key] = line[len(key) + 1:].strip()
    return info if info.get("url") else None


def _credential_matches_url(text, source_url):
    """凭证头里的 URL 必须与 meta.source 一致——防止"复制别处凭证 + 改 meta.source"伪造。
    chars 也要与文件实际内容长度匹配，防止"加凭证头 + 篡改正文"。"""
    info = _parse_fetch_credential(text)
    if not info:
        return False, "无凭证头"
    if info["url"].strip() != source_url.strip():
        return False, f"凭证 URL ({info['url']}) ≠ meta.source ({source_url})"
    try:
        declared = int(info.get("chars", "0"))
        # 文件正文 = 全文 - 凭证头(到第一个 "-->\n" 之后)；以"来源："行后视为正文起点
        body_start = text.find("-->")
        body = text[body_start + 3:].strip() if body_start >= 0 else text
        # 去掉自动写入的"来源/抓取日期"两行
        body_lines = body.splitlines()
        while body_lines and (body_lines[0].startswith("来源：")
                              or body_lines[0].startswith("抓取日期：")
                              or not body_lines[0].strip()):
            body_lines.pop(0)
        actual = len("\n".join(body_lines))
        # 允许 ±20% 偏差（编辑器换行/末尾空行可能差几字节）
        if declared > 0 and abs(actual - declared) > max(50, declared * 0.2):
            return False, f"凭证声明 {declared} 字，实测 {actual} 字（差异>20%）"
    except (ValueError, KeyError):
        pass
    return True, ""


def _norm_text(s):
    """归一化：去掉空白与标点，只留汉字/字母/数字，用于'选文是否为原文子串'的
    忠实节选校验——忽略标点风格差异（弯/直引号、句读不同），但改字/缺字仍会落空。"""
    return re.sub(r"\W+", "", str(s or ""), flags=re.UNICODE)


def _check_source(fp, meta, paper_blocks, materials_dir, errors, warn):
    """阅读类素材真实性门禁，分级把关（errors=硬拒绝，warn=软提醒）：
    - 缺 source：拒绝。
    - 标'原创'：堵死「meta标原创、卷面却印外部出处」自相矛盾；古诗词标原创直接拒绝。
    - 非原创且 source 是 URL：materials 原文必须带 fetch_web.py 抓取凭证头，
      否则判为「凭记忆默写+补假URL」拒绝（除非显式标 '用户提供-…'）。
    - 非原创、非URL的纯出处（纸质书/杂志）：程序无法核验，放行但 warn 提示人工核对。
    - 忠实节选子串校验：选文每段去空白后须为原文连续子串，改写/重排会落空 → warn。"""
    if not _needs_source(meta, paper_blocks):
        return
    name = os.path.basename(fp)
    source = str(meta.get("source", "")).strip()
    sfile = str(meta.get("source_file", "")).strip()
    mats = [b for b in paper_blocks
            if isinstance(b, dict) and b.get("type") == "material"
            and (b.get("paras") or b.get("title"))]
    if not source:
        errors.append(f"{name}：阅读类素材缺 meta.source（须填来源URL/出处，"
                      f"或显式写 '原创-已声明' / '用户提供-<出处>'）")
        return

    is_original = "原创" in source
    is_url = "http" in source.lower()
    # is_user 仅当 source 不含 URL 时生效：URL 既然给了就应可核验，不许用"截图"二字降级
    is_user = (not is_url) and any(k in source for k in _USER_SRC_HINTS)

    # —— 原创逃逸收口：堵死「meta 标原创、卷面却印外部出处」自相矛盾 ——
    if is_original:
        for b in mats:
            msrc = str(b.get("source", ""))
            if any(k in msrc for k in ("节选自", "选自", "出自", "摘自", "改编自")):
                errors.append(f"{name}：meta.source 标'原创'，但选文出处却写『{msrc}』"
                              f"——自相矛盾。原创素材不应有外部出处；若确为真实节选，"
                              f"请把 meta.source 改为真实来源并落盘原文佐证。")
            if b.get("layout") == "verse":
                errors.append(f"{name}：古诗词标'原创'不合理——古诗词须取真实公版作品"
                              f"并溯源（ctext/古诗文网），不可原创。")
        return

    # —— 非原创：必须有落盘原文佐证 ——
    if not sfile:
        errors.append(f"{name}：缺 meta.source_file（真实素材须把原文落盘 "
                      f"materials/ 并在此指向该文件）")
        return
    if os.path.isabs(sfile):
        # B2修复：禁止绝对路径——os.path.join(materials_dir, "/abs/path") 会忽略 materials_dir
        errors.append(f"{name}：source_file 不得使用绝对路径，"
                      f"请填 materials/ 下的相对文件名（如 '非连_来源-标题.md'）")
        return
    fpath = os.path.join(materials_dir, sfile)
    if not os.path.exists(fpath):
        errors.append(f"{name}：source_file 指向的 materials/{sfile} 不存在"
                      f"（禁止凭空编造真实素材）")
        return
    try:
        with open(fpath, encoding="utf-8") as f:
            src_doc = f.read()
    except (OSError, UnicodeDecodeError):
        src_doc = ""

    # —— 抓取凭证分级：URL 来源本可脚本抓取，必须带凭证头且 URL/字节数与 meta 一致——
    #    堵死「凭记忆默写+补假URL」「复制别处凭证头+换 meta.source」「带凭证头但篡改正文」
    if is_url:
        ok, why = _credential_matches_url(src_doc, source)
        if not ok:
            errors.append(f"{name}：meta.source 是网络链接，但 materials/{sfile} "
                          f"凭证校验未过（{why}）——疑似凭记忆默写后补假来源或篡改正文。"
                          f"请用 `fetch_web.py \"<url>\" --save materials/{sfile}` 重新抓取；"
                          f"若确为用户手工提供，请把 meta.source 标为 '用户提供-<出处>'（去掉 URL）。")
            return
    elif not is_user:
        warn.append(f"{name}：素材来源『{source}』非网络链接、无法用抓取凭证核验，"
                    f"请人工核对该选文是否逐字属实。")

    # —— 忠实节选·子串校验（软提醒，汇总所有 miss）——
    src_norm = _norm_text(src_doc)
    if not src_norm:
        warn.append(f"{name}：materials/{sfile} 内容为空或无法读取，无法校验"
                    f"选文是否忠实节选。")
        return
    for b in mats:
        # title-only 块（无 paras）无法校验正文——必须 warn,不能静默放行
        if not b.get("paras"):
            warn.append(f"{name}：material 块仅有 title 无 paras 正文，"
                        f"无法校验选文是否忠实节选，请人工核对。")
            continue
        miss_paras = []
        for para in b.get("paras") or []:
            p = _norm_text(para)
            if len(p) >= 12 and p not in src_norm:
                miss_paras.append(str(para)[:18])
        if miss_paras:
            warn.append(f"{name}：选文有 {len(miss_paras)} 段未在 materials/{sfile} "
                        f"原文中逐字找到（如『{miss_paras[0]}…』）"
                        f"——可能被改写/重排，请核对是否忠实节选。")


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

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
    # Bug-Z-1：把蓝图 manifest 写入 meta，build 可对照逐题分值
    if bp.get("manifest"):
        meta["expected_per_question"] = {}
        for row in bp["manifest"]:
            try:
                q_raw = str(row[1] if len(row) > 1 else "")
                score_raw = row[3] if len(row) > 3 else None
                # 题号归一："q01" → "1"
                qnum = q_raw.lstrip("q").lstrip("0") or "0"
                if score_raw is not None and str(score_raw) not in ("—", ""):
                    meta["expected_per_question"][qnum] = float(score_raw)
            except (ValueError, TypeError, IndexError):
                continue
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
    _nul_warn = []
    _cleanup_nul_files(proj, _nul_warn,
                       extra_dirs=(os.path.dirname(os.path.abspath(proj)) or ".", os.getcwd()))
    for _w in _nul_warn:
        print(f"  [清理] {_w}")


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
    # Bug-A2 修复：宽容解包，蓝图行少给/多给字段都不再崩溃（用占位填充）
    for raw in rows:
        try:
            row = list(raw) if isinstance(raw, (list, tuple)) else [raw]
        except TypeError:
            row = ["", str(raw), "", "", "", ""]
        # 补齐到 6 字段、截断超出
        row = (row + ["", "", "", "", "", ""])[:6]
        pre, q, typ, score, kp, diff = row
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


def _cleanup_nul_files(project_dir, warn, extra_dirs=()):
    """清理名为 NUL 的残留文件：cmd 风格重定向（>NUL / 2>NUL）在 Windows 的
    Git Bash 下不会指向空设备，而是真的创建一个名为 NUL 的文件（OneDrive 同步
    会因保留名报错）。工程目录递归清理；extra_dirs（工程父目录/当前目录，NUL
    常被建在这两处）只清顶层。Windows 原生 API 删除保留名文件需要 \\\\?\\ 前缀。"""
    targets = []
    for root, _dirs, fnames in os.walk(project_dir):
        targets += [os.path.join(root, n) for n in fnames if n.upper() == "NUL"]
    for d in extra_dirs:
        try:
            targets += [os.path.join(d, n) for n in os.listdir(d) if n.upper() == "NUL"]
        except OSError:
            continue
    for fp in dict.fromkeys(os.path.realpath(t) for t in targets):
        try:
            os.remove(fp)
        except OSError:
            removed = False
            if os.name == "nt":
                try:
                    os.remove("\\\\?\\" + fp)
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
    _cleanup_nul_files(proj, warn,
                       extra_dirs=(os.path.dirname(os.path.abspath(proj)) or ".", os.getcwd()))
    # B3修复：同一数字前缀的多个 _sec_ 文件会重复输出大题标题，只保留第一个。
    # Bug-B1 修复：同一数字前缀的多个题目文件（如 101_q01.json + 101_q01_v2.json）
    # 会双倍读入造成同号双题。去重策略：完全相同的数字前缀只保留第一个，其余 warn 跳过。
    _seen_sec_prefix = set()
    _seen_q_prefix = set()
    _deduped = []
    for _f in files:
        _bn = os.path.basename(_f)
        _prefix = _sort_key(_f)[0]
        if is_sec_name(_bn):
            if _prefix in _seen_sec_prefix:
                warn.append(f"{_bn} 与同前缀大题分隔文件重复，已跳过（避免标题重复）")
                continue
            _seen_sec_prefix.add(_prefix)
        else:
            # 题目/题材/子分隔 等非 section 文件按前缀去重
            if _prefix in _seen_q_prefix:
                warn.append(f"{_bn} 与同前缀题目/材料文件重复，已跳过（避免同号双题）")
                continue
            _seen_q_prefix.add(_prefix)
        _deduped.append(_f)
    files = _deduped
    source_errors = []  # 阅读类素材真实性硬门禁的违规项
    figure_errors = []  # 缺图硬门禁：题干含"如图"但无 figure block
    parse_errors = []   # 完整性硬门禁：坏 JSON / 结构错误的原子文件（跳过=静默漏题）
    excerpt_errors = []  # 忠实节选硬门禁：材料非原文连续子串（跳段/改字/重排）
    stale_errors = []    # W-1：道法/思想政治时政素材过期
    audit_rows = []     # 材料真实性自检表（build 自动生成）
    quality_rows = []   # Batch6-L3 Phase 3.5 自审表（考点/难度/风格机器统计）
    allow_missing_fig = "--allow-missing-figure" in args
    materials_dir = os.path.join(proj, "materials")
    for fp in files:
        try:
            atom = _read_json(fp)
        except json.JSONDecodeError as e:
            parse_errors.append(
                f"{os.path.basename(fp)} 非合法JSON（{e}）——最常见原因：JSON 字符串内的"
                f"中文引述写了未转义的 ASCII 双引号 \"，请直接改为全角“”")
            continue
        p_blocks = atom.get("paper", [])
        a_blocks = atom.get("answer", [])
        if not isinstance(p_blocks, list) or not isinstance(a_blocks, list):
            parse_errors.append(f"{os.path.basename(fp)} 的 paper/answer 不是列表")
            continue
        # Batch6-L1：听力稿位置硬门禁——录音稿不能在 paper 字段（会让听力题退化为阅读题）
        for _b in p_blocks:
            if isinstance(_b, dict) and _b.get("type") == "material" \
                    and _b.get("layout") == "listening_transcript":
                parse_errors.append(f"{os.path.basename(fp)} 的 paper 字段含听力录音稿"
                                    f"(layout=listening_transcript)——录音稿必须写到 answer 字段，"
                                    f"由老师按答案文档朗读，不能印在学生试卷上（否则听力题退化为阅读题）")
                break
        paper.extend(p_blocks)
        answers.extend(a_blocks)
        m = atom.get("meta", {})
        is_question = (m.get("score") is not None and str(m.get("status", "")) != "-")

        # —— 缺图硬门禁：题干含"如图/图中/图所示"等图引用字样但 paper 无 figure 块 ——
        if is_question:
            _check_missing_figure(fp, p_blocks, figure_errors)
            # Bug-W-2：历史题干内嵌史料软提醒（warn，不阻断；机器无法判真伪）
            _check_embedded_history(fp, p_blocks, meta.get("subject", ""), warn)

        # —— 阅读类素材真实性硬门禁 ——
        _pre_src_err = len(source_errors)
        _check_source(fp, m, p_blocks, materials_dir, source_errors, warn)
        # —— 忠实节选硬门禁：材料只能从原文首尾连续删减（禁跳段/改字/重排）——
        _check_faithful_excerpt(fp, m, p_blocks, materials_dir, excerpt_errors)
        # —— Bug-W-1 时政时效硬门禁：道法/思想政治素材抓取距今需 ≤ 时政窗口 ——
        _window = int(meta.get("decisions", {}).get("时政窗口", _FRESHNESS_DEFAULT_DAYS) or _FRESHNESS_DEFAULT_DAYS)
        _check_freshness(fp, m, p_blocks, materials_dir, meta.get("subject", ""),
                         stale_errors, warn, _window)
        # —— 材料真实性自检表行（build 自动生成，交付时原样转发用户）——
        for _b in p_blocks:
            if isinstance(_b, dict) and _b.get("type") == "material" and _b.get("paras"):
                _hits = _block_wording_hits(_b)
                audit_rows.append({
                    "file": os.path.basename(fp),
                    "title": str(_b.get("title") or _b.get("label") or "（无标题）"),
                    "source": str(m.get("source", "")) or "❌缺",
                    "source_file": str(m.get("source_file", "")) or "—",
                    "src_ok": len(source_errors) == _pre_src_err,
                    "wording": ("✓节选规范" if not _hits
                                else "❌含:" + "/".join(w for _, w in _hits)),
                })

        if is_question:
            try:
                total += float(m["score"])
            except (TypeError, ValueError):
                pass
            # Batch6-L3：收集 Phase 3.5 自审数据（考点/难度/题干长度）
            stems = " ".join(str(b.get("text") or b.get("stem") or "")
                             for b in p_blocks if isinstance(b, dict)
                             and b.get("type") in ("question", "stem"))
            quality_rows.append({
                "num": str(m.get("num", "?")),
                "kp": str(m.get("knowledge_point") or m.get("knowledge") or "未标"),
                "diff": str(m.get("difficulty", "-")),
                "stem_len": len(stems),
                "type": str(m.get("type", "")),
            })
        if m.get("num"):
            nums.append(str(m["num"]))
            if m.get("score") is None:
                warn.append(f"题{m['num']} 缺 score 字段（未计入总分）")
            # Bug-Z-1：逐题分值对照 manifest 期望值
            exp_pq = meta.get("expected_per_question") or {}
            qn = str(m["num"]).lstrip("0") or "0"
            if qn in exp_pq and m.get("score") is not None:
                try:
                    actual = float(m["score"])
                    expected = float(exp_pq[qn])
                    if abs(actual - expected) > 0.01:
                        warn.append(f"题{m['num']} 实际 {actual:g} 分 ≠ manifest 期望 {expected:g} 分"
                                    f"（真题/样卷分值被改写；若有意调整请同步更新 00_manifest.md）")
                except (ValueError, TypeError):
                    pass

    # 校验（expected_questions=0 表示题量未知/通用兜底/题量待定预设 → 跳过题量门禁，但仍校验总分）
    exp_q = meta.get("expected_questions", 21)
    exp_total = meta.get("total", 120)
    if exp_q:
        if len(nums) != exp_q:
            parse_errors.append(f"题量 {len(nums)} ≠ 期望 {exp_q}（题号：{','.join(nums) or '无'}）")
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

    # —— 选文标注措辞硬门禁：标注含'改编/改写/整理自'或'原创'字样 → 拒绝出卷 ——
    wording_errors = []
    _check_material_wording(paper, wording_errors)

    # —— 政史地史实/数据真实性提醒：溯源门禁只覆盖 material 选文块，题干内嵌的
    #    史实/年代/数据/地名等不触发门禁，须人工核验，不可编造。——
    _subj = str(meta.get("subject", ""))
    if any(k in _subj for k in ("历史", "地理", "政治", "道德与法治", "道法")):
        warn.append(f"⚠️『{_subj}』题干内嵌的史实/年代/数据/地名不受溯源门禁覆盖，"
                    f"请人工核验真实性，严禁编造（地图/图表需用户提供）。")

    # —— 卷面完整性硬门禁：坏 JSON 原子文件 / 题量不符 → 静默漏题，拒绝出卷 ——
    allow_incomplete = "--allow-incomplete" in args
    if parse_errors:
        if allow_incomplete:
            warn.extend(e + "（--allow-incomplete 已降级为告警，卷面可能缺题）" for e in parse_errors)
        else:
            print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
            print("\n🔴 [完整性门禁] 以下问题会导致卷面静默缺题：")
            for e in parse_errors:
                print("   - " + e)
            print("\n  已拒绝出卷。修复对应 items/*.json 后重跑 build；")
            print("  如确认缺题可接受（如分批预览），加 --allow-incomplete（降级为告警，须告知用户缺了哪些题）。")
            sys.exit(2)

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

    # —— W-1 时政时效硬门禁：道法/思想政治素材抓取距今超 2 倍窗口 → 拒绝出卷 ——
    allow_stale = "--allow-stale" in args
    if stale_errors:
        if allow_stale:
            warn.extend(e.split("。请")[0] + "（--allow-stale 已降级为告警）" for e in stale_errors)
        else:
            print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
            print("\n🔴 [时政时效门禁] 以下道法/思想政治素材已过期：")
            for e in stale_errors:
                print("   - " + e)
            print("\n  已拒绝出卷。重新抓取近 1-3 月新闻；如确需保留旧素材，加 --allow-stale 并告知用户。")
            sys.exit(2)

    # —— 选文标注措辞硬门禁：'改编/改写/整理自'或卷面自称'原创' → 拒绝出卷 ——
    allow_wording = "--allow-wording" in args
    if wording_errors:
        if allow_wording:
            warn.extend(e + "（--allow-wording 已降级为告警）" for e in wording_errors)
        else:
            print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
            print("\n🔴 [措辞门禁] 以下选文标注违反真实性铁律：")
            for e in wording_errors:
                print("   - " + e)
            print("\n  已拒绝出卷。把标注改为'节选自…'（教师原创只写在 meta.source）后重跑；")
            print("  仅当选文标题本身确实含这些词（如书名）误伤时，加 --allow-wording 降级为告警并告知用户。")
            sys.exit(2)

    # —— 忠实节选硬门禁：材料只能从原文首尾连续删减（禁跳段/改字/重排）——
    allow_excerpt = "--allow-excerpt" in args
    if excerpt_errors:
        if allow_excerpt:
            warn.extend(e.split("。若确为")[0] + "（--allow-excerpt 已降级为告警，请人工担保真实性）"
                        for e in excerpt_errors)
        else:
            print(f"[合并] 已读 {len(files)} 个原子文件，题量 {len(nums)}，分值合计 {total:g}")
            print("\n🔴 [忠实节选门禁] 以下选文疑似改字/编造/重排（材料未逐字取自真实原文）：")
            for e in excerpt_errors:
                print("   - " + e)
            print("\n  已拒绝出卷。材料可删减无关部分，但保留的每段须逐字取自真实原文、按原文顺序；")
            print("  重新抓原文、按原文逐字节选后重跑。")
            sys.exit(2)

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

    # —— 材料真实性自检表：build 自动生成并打印，交付时必须原样转发给用户 ——
    if audit_rows:
        _tbl = ["| 文件 | 选文标题 | meta.source | source_file | 溯源 | 标注措辞 |",
                "|---|---|---|---|---|---|"]
        for r in audit_rows:
            _tbl.append(f"| {r['file']} | {r['title']} | {r['source']} | "
                        f"{r['source_file']} | {'✓' if r['src_ok'] else '❌'} | {r['wording']} |")
        _audit_md = ("# 材料真实性自检表（build 自动生成）\n\n"
                     "> 交付时必须把本表原样转发给用户复核；出现 ❌ 说明使用了 --allow-* 开关带病出卷，必须显式告知。\n\n"
                     + "\n".join(_tbl) + "\n")
        _apath = os.path.join(proj, "build", "材料真实性自检表.md")
        os.makedirs(os.path.dirname(_apath), exist_ok=True)
        with open(_apath, "w", encoding="utf-8") as f:
            f.write(_audit_md)
        print("\n[材料自检表] 已写入 build/材料真实性自检表.md（交付时必须原样转发给用户）：")
        for ln in _tbl:
            print("  " + ln)

    # —— Batch6-L3：Phase 3.5 自审表机器化 ——
    _audit_md, _audit_issues = _gen_self_audit(quality_rows)
    if _audit_md:
        _spath = os.path.join(proj, "build", "Phase3.5_自审表.md")
        os.makedirs(os.path.dirname(_spath), exist_ok=True)
        with open(_spath, "w", encoding="utf-8") as f:
            f.write(_audit_md)
        print("\n[Phase 3.5 自审表] 已写入 build/Phase3.5_自审表.md")
        if _audit_issues:
            print("  🔴 自审 Issue（修复对应题后重跑 build）：")
            for it in _audit_issues:
                print("    " + it)
        else:
            print("  ✅ 自审通过（考点分布/难度梯度/题干长度均正常）")

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

    # —— Batch6-L4：多 allow 开关审计聚合 ——
    _allow_used = [a for a in (
        "--allow-unsourced", "--allow-missing-figure", "--allow-length",
        "--allow-incomplete", "--allow-wording", "--allow-excerpt",
        "--allow-stale") if a in args]
    if _allow_used:
        _msg = f"本次启用了 {len(_allow_used)} 个降级开关：{', '.join(_allow_used)}"
        if len(_allow_used) >= 2:
            print(f"\n🔴 [降级开关审计] ⚠️ {_msg}", file=sys.stderr)
            print("    多个开关同时使用会绕过大量真实性/规格门禁，相当于关闭质量保障；"
                  "必须向用户逐一说明每个开关绕过了什么。", file=sys.stderr)
        else:
            print(f"\n⚠️ [降级开关] {_msg}（向用户说明被绕过的检查）")
        # 同步追加到材料自检表
        _apath = os.path.join(proj, "build", "材料真实性自检表.md")
        if os.path.exists(_apath):
            try:
                with open(_apath, "a", encoding="utf-8") as f:
                    f.write(f"\n\n## ⚠️ 降级开关使用记录\n\n{_msg}\n")
            except OSError:
                pass

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
                   ("文言", "文言"), ("名著", "名著"),
                   # Bug-Y-2：英语板块关键词（按词计），让英语字数门禁实际生效
                   ("阅读理解", "英语阅读"), ("english_reading", "英语阅读"),
                   ("完形填空", "完形"), ("完形", "完形"), ("cloze", "完形"),
                   ("七选五", "七选五"), ("seven_choose_five", "七选五"),
                   ("语法填空", "语法填空"), ("读后续写", "读后续写"),
                   ("书面表达", "书面表达"), ("短文改错", "短文改错"))


def _default_block_len(stage, subject):
    """按科目给出各板块默认字数区间（净字数/词数）。
    与 references/subjects/语文.md / 英语.md 第2节区间表对齐。
    其它科目无默认——蓝图/预设显式给 block_len 才校验。"""
    if "语文" in str(subject):
        return {"非连": [600, 1000], "小说": [1000, 1500],
                "散文": [800, 1200], "文言": [100, 200]}
    if "英语" in str(subject):
        # Bug-Y-2: 英语按词计；按学段大致区分（初中阅读较短，高中较长）
        s = str(stage)
        if any(k in s for k in ("高一", "高二", "高三", "高中", "高考")):
            return {"英语阅读": [300, 400], "完形": [250, 350],
                    "七选五": [250, 350], "语法填空": [180, 240],
                    "读后续写": [120, 180], "书面表达": [80, 120], "短文改错": [110, 140]}
        # 初中
        return {"英语阅读": [200, 300], "完形": [180, 250],
                "书面表达": [60, 100]}
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
            # Bug-Y-2：英语 block_len 缺失时回退到默认（按学段从 _default_block_len）
            block_len = _default_block_len("", subject) or {}
            if not block_len:
                return []
        else:
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


def _block_wording_hits(block):
    """返回 material 块标注性字段（source/title/label/author）命中的违规措辞列表。
    正文 paras 不扫描：选文原文合法包含'改编'等词（如影视改编报道），误伤率高。"""
    hits = []
    for field in ("source", "title", "label", "author"):
        val = str(block.get(field, ""))
        if not val:
            continue
        hits.extend((field, w) for w in _WORDING_BAD if w in val)
        if "原创" in val:
            hits.append((field, "原创"))
    return hits


def _check_material_wording(paper, errors):
    """选文标注措辞硬门禁：material 标注性字段出现'改编/改写/编译/整理自…'等暗示
    二次创作的措辞，或'原创'字样（卷面不应自称原创，原创声明只写在
    meta.source='原创-已声明'）→ 拒绝出卷（--allow-wording 降级为告警）。
    真实性铁律要求忠实节选——逐字、可删减，禁重排/改写/编造，标注应为'节选自'。"""
    for b in paper:
        if not (isinstance(b, dict) and b.get("type") == "material"):
            continue
        for field, word in _block_wording_hits(b):
            val = str(b.get(field, ""))
            if word == "原创":
                errors.append(f"选文{field}『{val}』含'原创'字样——卷面不应自称原创，"
                              f"教师原创只在 meta.source 写'原创-已声明'，卷面标注请删除或改实际出处。")
            else:
                errors.append(f"选文{field}『{val}』含'{word}'——按真实性铁律须忠实节选"
                              f"（逐字可删减、禁重排改写编造），标注请改为'节选自…'。")


_FIG_CUES = ("如图", "如下图", "下图", "图中", "图所示", "根据图", "看图",
             "观察图", "请看图", "依据图")


def _check_missing_figure(fp, paper_blocks, errors):
    """题干含'如图/如下图/图中/图所示'等图引用字样，但 paper 块里没有 figure block
    （也没有 src 提供的图）→ 拒绝出卷。AI 不能写出"如图所示"却不给图。
    Bug-B2 修复：只扫题干文字（text/stem），不扫 options——选项里出现"下图错误/
    上图正确"等是答案表述，不是题干引用，扫了会误伤无图题。"""
    has_fig = any(isinstance(b, dict) and b.get("type") == "figure" for b in paper_blocks)
    if has_fig:
        return
    for b in paper_blocks:
        if not isinstance(b, dict):
            continue
        # 只扫题干文字，不扫选项
        if b.get("type") not in ("question", "stem"):
            continue
        text = str(b.get("text", "")) + str(b.get("stem", ""))
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
        for key in ("url", "chars", "sha256", "strategy", "fetched_at"):
            if line.startswith(key + ":"):
                info[key] = line[len(key) + 1:].strip()
    return info if info.get("url") else None


def _parse_manual_credential(text):
    """Batch6-L2 修复：解析手抄/截图素材的两行裸文本元信息（SKILL.md:219 要求）。
        来源：<URL 或 出处>
        抓取日期：YYYY-MM-DD
    时政时效门禁/溯源校验对这类素材也需可识别。返回 dict(source=..., fetched_at=...) 或 None。"""
    if not text:
        return None
    head = text[:800]
    info = {}
    for line in head.splitlines():
        line = line.strip()
        # 兼容中英冒号
        for raw, key in (("来源：", "source"), ("来源:", "source"),
                         ("抓取日期：", "fetched_at"), ("抓取日期:", "fetched_at"),
                         ("Source:", "source"), ("Fetched:", "fetched_at")):
            if line.startswith(raw):
                info[key] = line[len(raw):].strip()
                break
    return info if info.get("fetched_at") else None


_HISTORY_SUBJECTS = ("历史",)
# 引号字符集：中文书名号《》+ 智能引号 “”‘’ + 中式角引号「」『』
_QUOTE_CHARS = (chr(0x300A) + chr(0x300B) + chr(0x201C) + chr(0x201D) +
                chr(0x2018) + chr(0x2019) + chr(0x300C) + chr(0x300D) +
                chr(0x300E) + chr(0x300F))
_EMBEDDED_QUOTE_RE = re.compile("[" + _QUOTE_CHARS + "]")


def _check_embedded_history(fp, p_blocks, subject, warn):
    """Bug-W-2：历史题干内嵌长史料段（≥30字+含书名号/智能引号）触发 warn 提醒人工溯源。
    历史 40-50% 分值是'史料+设问'，史料嵌 stem 里完全绕过 _check_faithful_excerpt——
    机器无法知道这段史料真伪，只能提醒命题者人工核查。"""
    if not any(k in str(subject) for k in _HISTORY_SUBJECTS):
        return
    name = os.path.basename(fp)
    for b in p_blocks:
        if not (isinstance(b, dict) and b.get("type") == "question"):
            continue
        text = str(b.get("text") or "")
        if len(text) < 30 or not _EMBEDDED_QUOTE_RE.search(text):
            continue
        snippet = text[:30] + "…"
        warn.append(f"{name}：题干含内嵌史料『{snippet}』——历史题干史料不受溯源门禁覆盖，"
                    f"请人工核验：①引文是否真实存在 ②出处是否准确 ③标点字句是否忠实。"
                    f"严禁编造伪史料。")


_POLITICAL_SUBJECTS = ("思想政治", "政治", "道德与法治", "道法")
_FRESHNESS_DEFAULT_DAYS = 90  # 时政时效默认窗口：90 天


def _check_freshness(fp, meta, paper_blocks, materials_dir, subject, errors, warn, window_days):
    """Bug-W-1：道法/思想政治 等时政科目的素材抓取日期距今须 ≤ window_days。
    超期则告警（warn）；超 2 倍则升级为硬拒绝（errors，可 --allow-stale 降级）。"""
    if not any(k in str(subject) for k in _POLITICAL_SUBJECTS):
        return
    if not _needs_source(meta, paper_blocks):
        return
    sfile = str(meta.get("source_file", "")).strip()
    if not sfile or os.path.isabs(sfile):
        return
    fpath = os.path.join(materials_dir, sfile)
    if not os.path.exists(fpath):
        return
    try:
        with open(fpath, encoding="utf-8") as f:
            head = f.read(1500)
    except (OSError, UnicodeDecodeError):
        return
    info = _parse_fetch_credential(head) or _parse_manual_credential(head)
    if not info or not info.get("fetched_at"):
        # Batch6-L2：手抄/截图素材也无 fetched_at → 时政科目硬要求两行元信息
        warn.append(f"{os.path.basename(fp)}：时政素材 {sfile} 缺抓取日期元信息——"
                    f"手抄/截图素材请在 materials/ 文件开头加两行：'来源：<出处>' 和 "
                    f"'抓取日期：YYYY-MM-DD'，否则时政时效门禁无法核验是否过期。")
        return
    import datetime
    try:
        fetched = datetime.datetime.strptime(info["fetched_at"][:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return
    age = (datetime.datetime.now() - fetched).days
    name = os.path.basename(fp)
    if age > window_days * 2:
        errors.append(f"{name}：时政素材 {sfile} 抓取于 {info['fetched_at'][:10]} "
                      f"（距今 {age} 天 > {window_days*2} 天硬阈值）——道法/思想政治"
                      f"高度依赖近 1-3 月时事，超期素材会导致整卷过时。请重新抓取最新"
                      f"报道；若确需保留旧素材，加 --allow-stale 并向用户说明。")
    elif age > window_days:
        warn.append(f"{name}：时政素材 {sfile} 抓取于 {info['fetched_at'][:10]} "
                    f"（距今 {age} 天 > {window_days} 天软阈值）——建议核对是否仍属"
                    f"当前热点；近 1-3 月报道最稳。")


def _gen_self_audit(quality_rows):
    """Batch6-L3 修复：Phase 3.5 自审表机器化。
    统计：考点重复、难度方差、题干长度分布。返回 markdown 字符串与 issue 列表。"""
    if not quality_rows:
        return "", []
    issues = []
    # 1) 考点重复（同考点 >2 次）
    from collections import Counter
    kp_counter = Counter(r["kp"] for r in quality_rows if r["kp"] not in ("未标", "-"))
    repeats = {k: c for k, c in kp_counter.items() if c >= 3}
    # 2) 难度方差/分布
    diffs = []
    for r in quality_rows:
        try:
            d = float(r["diff"])
            if 0 < d <= 1:
                diffs.append(d)
        except (ValueError, TypeError):
            pass
    if diffs:
        avg = sum(diffs) / len(diffs)
        diff_min, diff_max = min(diffs), max(diffs)
        diff_spread = diff_max - diff_min
    else:
        avg = diff_min = diff_max = diff_spread = 0
    # 3) 题干长度分布（识别"前简短后冗长"风格突变）
    stem_lens = [r["stem_len"] for r in quality_rows]
    avg_stem = sum(stem_lens) / max(len(stem_lens), 1)
    long_stem_n = sum(1 for L in stem_lens if L > avg_stem * 2.5)

    # 生成 issue
    if repeats:
        issues.append(f"⚠️ 考点重复：{len(repeats)} 个考点出现≥3次："
                      + "、".join(f"{k}×{c}" for k, c in repeats.items()))
    if diffs and diff_spread < 0.25:
        issues.append(f"⚠️ 难度梯度过窄：max-min={diff_spread:.2f}<0.25，全卷难度均匀"
                      f"（缺乏'基础送分→中档→拉分压轴'分层）")
    if long_stem_n >= 3:
        issues.append(f"⚠️ 题干长度突变：{long_stem_n} 题题干长度>均值2.5倍，"
                      f"可能前后风格不统一")

    # 生成 markdown
    rows = ["| 题号 | 考点 | 难度 | 题干长度 | 题型 |", "|---|---|---|---|---|"]
    for r in quality_rows:
        rows.append(f"| {r['num']} | {r['kp']} | {r['diff']} | {r['stem_len']} | {r['type'][:20]} |")

    summary = [
        f"- **总题数**: {len(quality_rows)}",
        f"- **考点分布**: 共 {len(kp_counter)} 个独立考点；重复≥3次: {len(repeats)} 个",
        f"- **难度分布**: 均值 {avg:.2f}，范围 [{diff_min:.2f}, {diff_max:.2f}]，跨度 {diff_spread:.2f}",
        f"- **题干长度**: 均值 {avg_stem:.0f} 字，突出长题（>均值2.5倍）: {long_stem_n} 题",
    ]
    md = ("# Phase 3.5 自审表（build 自动生成）\n\n"
          "> ⚠️ 出现的 issue 必须返工对应题目重跑 build，全绿才可进入 Phase 4 交付用户。\n\n"
          "## 整卷统计\n" + "\n".join(summary) + "\n\n"
          + ("## 🔴 自审 Issue\n" + "\n".join(issues) + "\n\n" if issues else
             "## ✅ 自审通过（无明显异常）\n\n")
          + "## 逐题明细\n" + "\n".join(rows) + "\n")
    return md, issues


def _extract_body(text):
    """从凭证文件中抽出正文（去掉 <!-- --> 凭证头 + 来源/抓取日期两行）。"""
    body_start = text.find("-->")
    body = text[body_start + 3:].strip() if body_start >= 0 else text
    body_lines = body.splitlines()
    while body_lines and (body_lines[0].startswith("来源：")
                          or body_lines[0].startswith("抓取日期：")
                          or not body_lines[0].strip()):
        body_lines.pop(0)
    return "\n".join(body_lines)


def _credential_matches_url(text, source_url):
    """凭证头里的 URL 必须与 meta.source 一致——防止"复制别处凭证 + 改 meta.source"伪造。
    chars + sha256 都要与文件实际内容匹配，防止"加凭证头 + 篡改正文 + 对齐字数"绕过。
    """
    import hashlib
    info = _parse_fetch_credential(text)
    if not info:
        return False, "无凭证头"
    if info["url"].strip() != source_url.strip():
        return False, f"凭证 URL ({info['url']}) ≠ meta.source ({source_url})"
    body = _extract_body(text)
    try:
        declared = int(info.get("chars", "0"))
        actual = len(body)
        # 允许 ±20% 偏差（编辑器换行/末尾空行可能差几字节）
        if declared > 0 and abs(actual - declared) > max(50, declared * 0.2):
            return False, f"凭证声明 {declared} 字，实测 {actual} 字（差异>20%）"
    except (ValueError, KeyError):
        pass
    # 🔴 sha256 强校验：堵"chars 对得上但内容被改"的绕过路径（Bug-A1）
    declared_sha = (info.get("sha256") or "").strip().lower()
    if declared_sha and len(declared_sha) == 64:
        actual_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if actual_sha != declared_sha:
            return False, (f"凭证 sha256 不匹配（声明 {declared_sha[:12]}…，"
                           f"实测 {actual_sha[:12]}…）——正文被篡改")
    return True, ""


def _norm_text(s):
    """归一化：去掉空白与标点，只留汉字/字母/数字，用于'选文是否为原文子串'的
    忠实节选校验——忽略标点风格差异（弯/直引号、句读不同），但改字/缺字仍会落空。
    Bug-Y-3：兼容英语——智能引号/不间断空格先归一，再小写化（英语大小写差异不算改字）。"""
    s = str(s or "")
    # 智能引号 / 不间断空格 → ASCII
    s = (s.replace("‘", "'").replace("’", "'")
           .replace("“", '"').replace("”", '"').replace(" ", " "))
    s = re.sub(r"\W+", "", s, flags=re.UNICODE)
    return s.lower()


def _check_source(fp, meta, paper_blocks, materials_dir, errors, warn):
    """阅读类素材真实性门禁，分级把关（errors=硬拒绝，warn=软提醒）：
    - 缺 source：拒绝。
    - 标'原创'：堵死「meta标原创、卷面却印外部出处」自相矛盾；古诗词标原创直接拒绝。
    - 非原创且 source 是 URL：materials 原文必须带 fetch_web.py 抓取凭证头，
      否则判为「凭记忆默写+补假URL」拒绝（除非显式标 '用户提供-…'）。
    - 非原创、非URL的纯出处（纸质书/杂志）：程序无法核验，放行但 warn 提示人工核对。
    （忠实节选的"只能首尾连续删减"校验已独立为硬门禁 _check_faithful_excerpt）"""
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
    # 注：忠实节选「只能首尾连续删减」的子串校验已独立为硬门禁 _check_faithful_excerpt（build 调用）。
    # title-only 材料（有来源但无 paras 正文）：无原文可比，提示人工核对（完整性门禁另会拦缺正文）
    for b in mats:
        if not b.get("paras"):
            warn.append(f"{name}：material 块仅有 title 无 paras 正文，"
                        f"无法核验选文是否属实，请人工核对。")


def _check_faithful_excerpt(fp, meta, paper_blocks, materials_dir, errors):
    """忠实节选硬门禁（落地'材料保真：允许合理删减，但禁造假/改字/重排'）：
    每段保留的正文必须逐字取自 source_file 原文（去标点空白后是原文子串），
    且各段按原文出现顺序排列。**允许删掉无关部分（含中间段，ABC→AC 可以）**，
    但禁止改字/编造（段落不在原文）、禁止重排（段落顺序与原文颠倒）→ 拒绝出卷。
    跳过：原创素材（无原文可比）、verse 古诗词（逐句默写、另行核验）、
    缺 source_file/文件不存在（由 _check_source 溯源门禁先行拦截）、过短材料。"""
    if not _needs_source(meta, paper_blocks):
        return
    source = str(meta.get("source", "")).strip()
    sfile = str(meta.get("source_file", "")).strip()
    if "原创" in source or not sfile or os.path.isabs(sfile):
        return
    fpath = os.path.join(materials_dir, sfile)
    if not os.path.exists(fpath):
        return
    try:
        with open(fpath, encoding="utf-8") as f:
            src_norm = _norm_text(f.read())
    except (OSError, UnicodeDecodeError):
        return
    if not src_norm:
        return
    name = os.path.basename(fp)
    for b in paper_blocks:
        if not (isinstance(b, dict) and b.get("type") == "material"):
            continue
        if b.get("layout") == "verse":
            continue
        # Bug-L-3：理科情境引子（命题情境，非阅读选文）跳过逐字校验，仅靠溯源
        if b.get("block") == "情境引子":
            continue
        # Bug-Y-3：英语听力稿（教师改写/原创，非阅读节选）跳过逐字校验
        if b.get("layout") == "listening_transcript":
            continue
        pos = 0  # 上一段在原文中的结束位置（保证按原文顺序、禁重排）
        # Bug-A4 修复：短段累计占比统计，防"拆成 11 字短句逐句编造"绕过门禁
        total_len = 0
        short_len = 0
        broke = False
        for para in (b.get("paras") or []):
            p = _norm_text(para)
            total_len += len(p)
            if len(p) < 12:        # 过短段落（标题/过渡句）暂不逐字校验
                short_len += len(p)
                continue
            idx = src_norm.find(p, pos)
            if idx >= 0:
                pos = idx + len(p)
                continue
            snippet = str(para)[:18]
            if p in src_norm:      # 原文里有但在 pos 之前 → 顺序颠倒
                errors.append(f"{name}：选文段落顺序与 materials/{sfile} 原文不一致"
                              f"（如『{snippet}…』排在前文之前）——只能按原文顺序删减，禁止重排。")
            else:                  # 原文里根本没有 → 改字或编造
                errors.append(f"{name}：选文有段落未在 materials/{sfile} 原文中逐字出现"
                              f"（如『{snippet}…』）——疑似改字或编造，材料每段须逐字取自真实原文"
                              f"（可删减无关部分，但不可改写）。")
            broke = True
            break
        # 短段累计占比 >30% 且全文 >50 字 → 疑似刻意拆短句绕过，拒绝
        if not broke and total_len > 50 and short_len * 10 > total_len * 3:
            errors.append(f"{name}：选文 {short_len}/{total_len} 字位于"
                          f"≤11字短段（{short_len*100//total_len}%>30%）——疑似刻意拆短句"
                          f"绕过逐字校验。请按原文段落自然换行，每段保留 ≥12 字便于核验。")


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

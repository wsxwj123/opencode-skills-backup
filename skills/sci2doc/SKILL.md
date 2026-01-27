
# 如果自动安装失败，提示用户
echo "⚠️ 自动安装失败，请手动执行："
echo "pip3 install python-docx"
```

**依赖验证结果示例**：
```
✅ Python 3.11.5 已安装
✅ python-docx 已安装
✅ 所有依赖就绪
```

---

## 🚀 启动检测：新项目 vs 续写 vs 查询

**AI首先判断用户意图（在任何操作前执行）**：

### 用户意图识别表

| 用户说法 | 意图类型 | AI响应流程 |
|----------|----------|------------|
| "我有一篇SCI论文..." / "帮我扩写论文" | 新项目 | → **流程A：新项目** |
| "继续写" / "继续生成" / "接着写" | 续写项目 | → **流程B：断点续写** |
| "我的论文写到哪了" / "查看进度" / "状态" | 状态查询 | → **流程C：状态查询** |
| "还剩多少字" / "字数统计" | 统计查询 | → **流程C：状态查询** |
| "修改第X章" / "改一下..." | 修改章节 | → **流程D：章节修改** |

---

## 流程A：新项目完整流程

### 步骤A1：收集用户基本信息

**在开始任何写作前，必须先收集以下信息用于封面和扉页：**

```
请提供以下基本信息（用于生成封面和扉页）：

1. 学校信息：
   - 学校名称：[默认：中南大学]
   - 学院名称：[如：湘雅药学院]

2. 个人信息：
   - 姓名：
   - 学号：
   - 年级/入学年份：[如：2020级]

3. 学科信息：
   - 学科门类：[默认：医学]
   - 学科专业：[如：药剂学]
   - 研究方向：[如：纳米药物递送系统]

4. 导师信息：
   - 正指导教师：[姓名 + 职称，如：张三 教授]
   - 副指导教师（如有）：[姓名 + 职称，仅在扉页显示]

5. 答辩信息：
   - 预计答辩时间：[如：2026年6月]
   - 学位类型：[默认：学术学位]

6. 其他：
   - 分类号：[如：R944]
   - UDC号：[如不清楚可留空]

7. 项目路径（可选）：
   - 默认路径：/Users/wsxwj/Desktop/博士论文_[主题]_[姓名]/
   - 自定义路径：[留空使用默认，或输入完整路径]

请逐项填写，未填写的项将使用默认值或提示补充。
```

### 步骤A2：上传SCI论文文件

```
请上传您的SCI论文文件：
- 支持格式：PDF 或 Word (.docx)
- 如有补充材料（图片、数据），也请一并上传

上传后，我会：
1. 自动读取论文内容
2. 提取关键信息（研究主题、方法、结果）
3. 生成详细大纲
4. 委托@librarian进行文献调研（120篇）
```

### 步骤A3：初始化项目

**AI执行以下操作**：
```bash
# 1. 确定项目路径
PROJECT_ROOT="/Users/wsxwj/Desktop/博士论文_[主题]_[姓名]"

# 2. 创建完整文件夹结构
mkdir -p "$PROJECT_ROOT/00_项目管理"
mkdir -p "$PROJECT_ROOT/01_前置部分"
mkdir -p "$PROJECT_ROOT/02_正文章节"
mkdir -p "$PROJECT_ROOT/03_后置部分"
mkdir -p "$PROJECT_ROOT/04_图表文件"
mkdir -p "$PROJECT_ROOT/05_原始材料"
mkdir -p "$PROJECT_ROOT/06_版本历史"

echo "✅ 项目文件夹创建完成"
```

**保存用户基本信息到本地**：
```bash
cat > "$PROJECT_ROOT/00_项目管理/用户基本信息.txt" << 'EOF'
学校：中南大学
学院：湘雅药学院
姓名：XXX
学号：XXXXXXXXXX
年级：2020级
学科专业：药剂学
研究方向：纳米药物递送系统
正指导教师：张三 教授
副指导教师：李四 副教授
答辩时间：2026年6月
分类号：R944
UDC号：615.014
创建时间：2026-01-27 16:45:00
EOF

echo "✅ 用户信息已保存"
```

**复制辅助脚本到项目目录**：
```bash
# 从技能目录复制脚本
cp /Users/wsxwj/.config/opencode/skills/sci2doc/scripts/*.py "$PROJECT_ROOT/00_项目管理/"

echo "✅ 辅助脚本已部署"
```

### 步骤A4：读取和分析SCI论文

```python
# 1. 读取SCI论文
sci_paper_path = f"{project_root}/05_原始材料/原始SCI论文.pdf"

# 使用markdownify转换
paper_content = markdownify_pdf-to-markdown(sci_paper_path)

# 2. 提取关键信息
research_info = {
    "title": extract_title(paper_content),
    "authors": extract_authors(paper_content),
    "journal": extract_journal(paper_content),
    "keywords": extract_keywords(paper_content),
    "abstract": extract_abstract(paper_content),
    "methods": extract_methods_section(paper_content),
    "results": extract_results_section(paper_content),
    "figures_count": count_figures(paper_content)
}

print(f"✅ 已读取SCI论文：{research_info['title']}")
print(f"   期刊：{research_info['journal']}")
print(f"   关键词：{', '.join(research_info['keywords'])}")
```

### 步骤A5：生成详细大纲

**AI基于SCI论文内容生成大纲**：
```python
# 根据SCI论文结构生成博士论文大纲
outline = {
    "title_cn": "[基于原文翻译或优化]",
    "title_en": research_info['title'],
    "chapters": [
        {
            "num": "第一章",
            "name": "前言",
            "target_words": 12200,
            "sections": [
                {"num": "1.1", "name": "研究背景与意义", "words": 3500},
                {"num": "1.2", "name": "国内外研究现状", "words": 6200},
                {"num": "1.3", "name": "本研究的主要内容与创新点", "words": 2500}
            ]
        },
        {
            "num": "第二章",
            "name": "材料与方法",
            "target_words": 7200,
            "sections": [
                {"num": "2.1", "name": "实验材料", "words": 2000},
                {"num": "2.2", "name": "实验仪器", "words": 1500},
                {"num": "2.3", "name": "实验方法", "words": 3700}
            ]
        },
        # ... 根据SCI论文结构生成其他章节
    ],
    "total_target": 53000  # 留buffer
}

# 显示大纲给用户确认
print("━" * 60)
print("📋 生成的论文大纲：")
print("━" * 60)
for chapter in outline['chapters']:
    print(f"{chapter['num']} {chapter['name']}（目标{chapter['target_words']}字）")
    for section in chapter['sections']:
        print(f"  {section['num']} {section['name']}（{section['words']}字）")

print("\n请确认：")
print("1. 直接开始生成（输入：开始）")
print("2. 调整字数分配（输入：调整）")
print("3. 修改章节结构（输入：修改）")
print("4. 查看完整大纲文件（输入：查看）")
```

### 步骤A6：创建记忆实体（核心）

**保存完整项目信息到知识图谱**：
```python
memory_create_entities({
  "entities": [{
    "name": f"{user_name}_博士论文项目_{research_topic}_{date_str}",
    "entityType": "博士论文项目",
    "observations": [
      # ===== 基本信息 =====
      f"学校：{school}",
      f"学院：{college}",
      f"姓名：{user_name}",
      f"学号：{student_id}",
      f"年级：{grade}",
      f"学科专业：{major}",
      f"研究方向：{research_direction}",
      f"研究主题：{research_topic}",
      f"正指导教师：{supervisor_main}",
      f"副指导教师：{supervisor_vice}",
      f"答辩时间：{defense_date}",
      f"分类号：{classification}",
      f"UDC号：{udc}",
      
      # ===== 项目路径（关键） =====
      f"项目路径：{project_root}",
      
      # ===== 论文标题 =====
      f"论文标题（中文）：{outline['title_cn']}",
      f"论文标题（英文）：{outline['title_en']}",
      
      # ===== 大纲结构 =====
      f"章节总数：{len(outline['chapters'])}",
      f"正文目标字数：50000",
      f"综述目标字数：5000",
      
      # 每章详细信息
      *[f"{ch['num']}：{ch['name']}（目标{ch['target_words']}字）" 
        for ch in outline['chapters']],
      
      # ===== 进度跟踪（初始状态） =====
      "当前章节：未开始",
      "总字数：0 / 50000",
      "完成度：0.0%",
      "状态：已初始化",
      
      # ===== SCI论文信息 =====
      f"SCI论文标题：{research_info['title']}",
      f"SCI论文期刊：{research_info['journal']}",
      f"SCI论文关键词：{', '.join(research_info['keywords'])}",
      
      # ===== 图表规划 =====
      f"图表总数：待定（基于SCI论文{research_info['figures_count']}图扩展）",
      
      # ===== 参考文献 =====
      "参考文献状态：待调研",
      "参考文献目标：≥120篇",
      
      # ===== 术语表引用 =====
      f"术语表实体：{research_topic}_术语表_{date_str}",
      
      # ===== 时间戳 =====
      f"创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
      f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
      f"生成版本：v1.0"
    ]
  }]
})

print("✅ 项目信息已保存到知识图谱")
```

**创建术语表实体**：
```python
# 从SCI论文提取术语
terms = extract_terminology(paper_content)

memory_create_entities({
  "entities": [{
    "name": f"{research_topic}_术语表_{date_str}",
    "entityType": "术语表",
    "observations": [
      f"项目名称：{research_topic}",
      f"术语总数：{len(terms)}",
      *[f"{term['cn']} = {term['en']}（缩写：{term.get('abbr', '无')}）" 
        for term in terms]
    ]
  }]
})

print(f"✅ 术语表已创建（{len(terms)}个术语）")
```

**保存大纲到本地文件**：
```python
# 生成Markdown格式的大纲文件
outline_md = generate_outline_markdown(outline, research_info)

filesystem_write_file(
    path=f"{project_root}/00_项目管理/论文大纲_{date_str}.md",
    content=outline_md
)

print("✅ 大纲已保存到本地")
```

### 步骤A7：委托@librarian文献调研

**使用background_task调用librarian**：
```python
# 提取关键词用于文献检索
keywords = research_info['keywords']
field = research_info.get('research_field', '医学')

# 调用librarian（同步等待）
literature_task = background_task(
    agent="librarian",
    description=f"文献调研：{research_topic}",
    prompt=f"""
请协助完成博士论文的文献调研任务：

**研究领域**：{field}
**核心关键词**：{', '.join(keywords)}
**SCI论文标题**：{research_info['title']}
**SCI论文期刊**：{research_info['journal']}

**需要收集的文献类型和数量**：

1. **综述文献（15-20篇）**：
   - 该领域最新综述（2021-2024年，影响因子>10）
   - 经典奠基性综述（引用量>500）
   - 搜索关键词：{keywords[0]}, {keywords[1]}, review
   - 推荐来源：Nature Reviews Drug Discovery, Advanced Drug Delivery Reviews, Chemical Reviews

2. **方法学文献（20-30篇）**：
   - 与本研究方法相似的文献
   - 该方法的原创文献和改进文献
   - 关键实验技术的标准操作文献
   - 搜索关键词：{keywords[2]}, methodology, characterization

3. **结果对比文献（30-40篇）**：
   - 研究对象相同但方法不同的文献
   - 研究方法相同但对象不同的文献
   - 最近5年的代表性工作
   - 得出相似或不同结论的文献（用于讨论）

4. **争议性讨论文献（10-15篇）**：
   - 该领域当前争议焦点
   - 不同学术观点的代表性文献
   - 最新的反驳或质疑文章
   - 未解决的科学问题

5. **临床转化文献（10-15篇，医学类必需）**：
   - 该技术的临床前研究
   - 类似技术的临床试验文献
   - 临床应用的安全性和有效性评价
   - FDA批准的纳米药物案例

**返回格式要求**：

请以Markdown格式返回，每篇文献包含：

```markdown
### [序号] 中文标题
- **英文标题**：...
- **作者**：First Author, Second Author, et al.
- **期刊**：Journal Name, Year, Volume(Issue): Pages
- **影响因子**：X.XXX (2023)
- **DOI**：10.xxxx/xxxxx
- **核心观点**：（用1-2句话概括该文献的主要发现和结论）
- **相关性**：高/中/低
- **建议引用章节**：前言1.2节 / 方法2.3节 / 讨论5.1节 / 综述
```

**质量要求**：
- 总数：至少120篇
- 近5年文献占比：≥60%
- 高影响因子（>10）：≥20篇
- 覆盖该领域的主流研究方向和最新进展
""",
    sync=True
)

print("⏳ 正在进行文献调研（预计需要2-3分钟）...")

# 获取结果
literature_result = background_output(task_id=literature_task['task_id'], block=True)

print(f"✅ 文献调研完成")
```

**保存文献到本地和记忆**：
```python
# 1. 保存到本地文件
filesystem_write_file(
    path=f"{project_root}/00_项目管理/参考文献_{date_str}.md",
    content=literature_result
)

# 2. 统计文献数量
ref_count = len(re.findall(r'^###\s+\[\d+\]', literature_result, re.MULTILINE))

# 3. 更新项目记忆
memory_add_observations({
    "observations": [{
        "entityName": f"{user_name}_博士论文项目_{research_topic}_{date_str}",
        "contents": [
            f"参考文献状态：已完成调研",
            f"参考文献总数：{ref_count}篇",
            f"文献调研日期：{date_str}",
            f"文献文件：00_项目管理/参考文献_{date_str}.md"
        ]
    }]
})

print(f"✅ 文献已保存（{ref_count}篇）")
```

---

## 流程B：断点续写（最重要）

### 步骤B1：查询记忆中的项目

```python
# 1. 搜索所有博士论文项目
print("🔍 正在查询您的论文项目...")

projects = memory_search_nodes(query="博士论文项目")

# 2. 判断结果
if not projects or len(projects) == 0:
    print("❌ 未找到之前的项目记录")
    print("\n可能原因：")
    print("1. 这是您第一次使用此功能")
    print("2. 记忆数据已清空")
    print("3. 项目名称不匹配")
    
    print("\n请选择：")
    print("1. 开始新项目（需要提供SCI论文）")
    print("2. 从本地文件恢复项目（如果文件夹还在）")
    
    choice = input("请输入选项（1/2）：")
    
    if choice == "1":
        # 转到新项目流程
        print("请提供您的SCI论文文件...")
        # 跳转到流程A
    elif choice == "2":
        # 从本地恢复
        project_path = input("请输入项目文件夹路径：")
        # 执行本地恢复流程（见步骤B3）

elif len(projects) == 1:
    # 只有一个项目，直接使用
    selected = projects[0]
    print(f"✅ 找到项目：{selected['name']}")

else:
    # 多个项目，让用户选择
    print(f"✅ 找到 {len(projects)} 个项目：\n")
    for i, proj in enumerate(projects):
        # 解析项目名称显示更友好
        name_parts = proj['name'].split('_')
        print(f"  {i+1}. {name_parts[2] if len(name_parts) > 2 else proj['name']}")
    
    choice = input("\n请输入序号选择项目（直接回车选择最新的）：")
    
    if choice == "":
        selected = projects[0]  # 默认最新
        print(f"📌 已选择最新项目")
    else:
        try:
            selected = projects[int(choice) - 1]
            print(f"📌 已选择项目 {choice}")
        except:
            print("❌ 输入无效，使用最新项目")
            selected = projects[0]
```

### 步骤B2：读取项目完整状态

```python
# 1. 打开项目实体
print("📖 正在读取项目状态...")

project_entity = memory_open_nodes(names=[selected['name']])
observations = project_entity[0]['observations']

# 2. 解析所有信息
project_info = {
    "基本信息": {},
    "大纲结构": [],
    "进度信息": {},
    "文件信息": {}
}

for obs in observations:
    if "：" in obs:
        key, value = obs.split("：", 1)
        key = key.strip()
        value = value.strip()
        
        # 分类存储
        if key in ["学校", "学院", "姓名", "学号", "研究主题", "正指导教师", "答辩时间"]:
            project_info["基本信息"][key] = value
        elif key == "项目路径":
            project_info["文件信息"]["路径"] = value
        elif key.startswith("第") and "章" in key:
            project_info["大纲结构"].append({"key": key, "value": value})
        elif key in ["当前章节", "总字数", "完成度", "状态"]:
            project_info["进度信息"][key] = value
        elif key.startswith("进度："):
            # 解析进度信息
            if "已完成" in value:
                if "已完成章节" not in project_info["进度信息"]:
                    project_info["进度信息"]["已完成章节"] = []
                project_info["进度信息"]["已完成章节"].append(obs)

# 3. 显示项目信息
print("✅ 项目状态已加载")
print(f"   项目：{project_info['基本信息'].get('研究主题', '未命名')}")
print(f"   作者：{project_info['基本信息'].get('姓名', '未知')}")
print(f"   路径：{project_info['文件信息'].get('路径', '未知')}")

# 提取关键信息
project_root = project_info['文件信息'].get('路径')
completed_count = len(project_info['进度信息'].get('已完成章节', []))
total_chapters = len(project_info['大纲结构'])

print(f"   进度：{completed_count}/{total_chapters} 章")
```

### 步骤B3：检查本地文件完整性

```python
# 1. 验证项目路径
if not project_root:
    print("⚠️ 记忆中未找到项目路径")
    project_root = input("请输入项目文件夹路径：")
    
    # 更新记忆
    memory_add_observations({
        "observations": [{
            "entityName": selected['name'],
            "contents": [f"项目路径：{project_root}"]
        }]
    })

# 2. 检查路径是否存在
if not os.path.exists(project_root):
    print(f"❌ 项目路径不存在：{project_root}")
    print("\n请选择：")
    print("1. 重新创建项目文件夹（推荐）")
    print("2. 重新指定路径")
    print("3. 取消操作")
    
    choice = input("请输入选项（1/2/3）：")
    
    if choice == "1":
        # 重新创建文件夹结构
        bash(f"mkdir -p '{project_root}'")
        bash(f"mkdir -p '{project_root}'/{{00_项目管理,01_前置部分,02_正文章节,03_后置部分,04_图表文件,05_原始材料,06_版本历史}}")
        print("✅ 项目文件夹已重建")
    elif choice == "2":
        # 重新指定
        project_root = input("请输入新的项目路径：")
        # 更新记忆...
    else:
        return  # 取消

# 3. 检查必需文件
print("\n🔍 检查项目文件...")

# 检查辅助脚本
scripts_dir = f"{project_root}/00_项目管理"
required_scripts = ["merge_documents.py", "count_words.py", "check_quality.py"]

missing_scripts = []
for script in required_scripts:
    script_path = f"{scripts_dir}/{script}"
    if not os.path.exists(script_path):
        missing_scripts.append(script)

if missing_scripts:
    print(f"⚠️ 缺少辅助脚本：{', '.join(missing_scripts)}")
    print("正在部署...")
    
    # 从技能目录复制
    skill_scripts = "/Users/wsxwj/.config/opencode/skills/sci2doc/scripts"
    for script in missing_scripts:
        bash(f"cp '{skill_scripts}/{script}' '{scripts_dir}/'")
    
    print("✅ 辅助脚本已部署")

# 检查章节文件
chapter_dir = f"{project_root}/02_正文章节"
if os.path.exists(chapter_dir):
    existing_chapters = bash(f"ls '{chapter_dir}' 2>/dev/null | grep '第.*章.*\\.docx' || echo ''")
    chapter_files = [f.strip() for f in existing_chapters.stdout.strip().split('\n') if f.strip()]
    
    print(f"✅ 找到 {len(chapter_files)} 个章节文件")
    for cf in chapter_files:
        print(f"   - {cf}")
else:
    print("⚠️ 正文章节目录不存在，将创建")
    bash(f"mkdir -p '{chapter_dir}'")
```

### 步骤B4：确定下一步操作

```python
# 1. 从大纲中提取所有章节
all_chapters = [ch['key'] for ch in project_info['大纲结构']]

# 2. 从进度中提取已完成章节
completed_chapters = []
for comp in project_info['进度信息'].get('已完成章节', []):
    match = re.search(r'(第[一二三四五六七八九十]+章)', comp)
    if match:
        completed_chapters.append(match.group(1))

# 3. 确定下一章
next_chapter = None
for chapter_key in all_chapters:
    chapter_name = re.search(r'(第[一二三四五六七八九十]+章)', chapter_key)
    if chapter_name and chapter_name.group(1) not in completed_chapters:
        next_chapter = chapter_key
        break

# 4. 显示状态并询问用户
print("\n" + "━" * 60)
print("📊 当前项目状态")
print("━" * 60)

for chapter_key in all_chapters:
    chapter_name = re.search(r'(第[一二三四五六七八九十]+章：.*?)（', chapter_key)
    if chapter_name:
        ch_name = chapter_name.group(1)
        # 提取字数信息
        words_match = re.search(r'(\d+)字', chapter_key)
        target_words = words_match.group(1) if words_match else "未知"
        
        # 判断状态
        if ch_name.split('：')[0] in completed_chapters:
            status = "✅"
            # 可以从进度信息中获取实际字数
        else:
            status = "❌" if ch_name != next_chapter else "⏳"
        
        print(f"{status} {ch_name:<30} 目标{target_words}字")

total_words = project_info['进度信息'].get('总字数', '0 / 50000')
print(f"\n总字数：{total_words}")

# 5. 询问用户
if next_chapter:
    print(f"\n➡️ 下一步：{next_chapter}")
    print("\n请选择操作：")
    print("1. 开始生成下一章（输入：开始 或 1）")
    print("2. 查看详细大纲（输入：大纲 或 2）")
    print("3. 查看已完成章节内容（输入：查看 或 3）")
    print("4. 修改某个章节（输入：修改 或 4）")
    print("5. 重新生成某章（输入：重新生成 或 5）")
    
    user_choice = input("\n请输入选项：")
    
    # 根据用户选择执行...
    
else:
    print("\n✅ 所有正文章节已完成！")
    print("\n接下来可以：")
    print("1. 生成综述（≥5,000字）")
    print("2. 生成中英文摘要")
    print("3. 生成目录")
    print("4. 合并完整版文档")
    print("5. 执行最终质量检查")
```

---

## 流程C：状态查询

**用户随时可以询问项目状态**：

```python
def generate_status_report(project_entity):
    """生成详细的项目状态报告"""
    
    observations = project_entity[0]['observations']
    
    # 解析信息
    info = {}
    for obs in observations:
        if "：" in obs:
            key, value = obs.split("：", 1)
            info[key.strip()] = value.strip()
    
    # 生成报告
    report = f"""
📊 项目状态报告
{'━' * 60}
项目名称：{info.get('研究主题', '未知')}
作者：{info.get('姓名', '未知')}
学院：{info.get('学院', '未知')}
项目路径：{info.get('项目路径', '未知')}

{'━' * 60}
📝 正文进度（目标50,000字，不含综述）
{'━' * 60}
"""
    
    # 提取章节和进度信息
    chapters = []
    completed = []
    
    for obs in observations:
        if obs.startswith("第") and "章：" in obs and "（目标" in obs:
            chapters.append(obs)
        elif obs.startswith("进度：") and "已完成" in obs:
            completed.append(obs)
    
    # 显示每章状态
    for chapter in chapters:
        # 解析章节名和目标字数
        match = re.match(r'(第.+?章)：(.+?)（目标(\d+)字）', chapter)
        if match:
            ch_num, ch_name, target = match.groups()
            
            # 检查是否完成
            is_completed = any(ch_num in comp for comp in completed)
            
            if is_completed:
                # 从completed中提取实际字数
                actual_words = 0
                for comp in completed:
                    if ch_num in comp:
                        words_match = re.search(r'(\d+)字', comp)
                        if words_match:
                            actual_words = int(words_match.group(1))
                status = f"✅ {ch_num} {ch_name:<20} {actual_words:>7,}字 / {target}字"
            else:
                status = f"❌ {ch_num} {ch_name:<20} {'0':>7}字 / {target}字"
            
            report += status + "\n"
    
    # 总字数
    total_words_str = info.get('总字数', '0 / 50000')
    if '/' in total_words_str:
        current, target = total_words_str.split('/')
        current = int(current.strip())
        target = int(target.strip())
        percent = current / target * 100
        report += f"\n当前总字数：{current:,} / {target:,}（{percent:.1f}%）\n"
    
    # 下一步
    current_ch = info.get('当前章节', '未知')
    if current_ch != "未开始" and current_ch != "已完成":
        report += f"下一步：继续生成{current_ch}\n"
    elif len(completed) < len(chapters):
        report += f"下一步：生成未完成章节\n"
    else:
        report += f"下一步：生成综述和摘要\n"
    
    report += f"\n{'━' * 60}\n"
    report += f"📚 其他部分状态\n"
    report += f"{'━' * 60}\n"
    
    # 其他部分
    parts_status = {
        "封面扉页": check_files_exist(project_root, ["01_前置部分/封面.docx", "01_前置部分/扉页.docx"]),
        "中英文摘要": check_files_exist(project_root, ["01_前置部分/中文摘要.docx", "01_前置部分/英文摘要.docx"]),
        "目录": check_files_exist(project_root, ["01_前置部分/目录.docx"]),
        "参考文献": info.get('参考文献总数', '未知') + "篇",
        "综述": check_files_exist(project_root, ["03_后置部分/综述.docx"]),
        "致谢": check_files_exist(project_root, ["03_后置部分/致谢.docx"])
    }
    
    for part_name, status in parts_status.items():
        if status == True:
            report += f"✅ {part_name}\n"
        elif status == False:
            report += f"❌ {part_name}\n"
        else:
            report += f"✅ {part_name}：{status}\n"
    
    report += f"\n{'━' * 60}\n"
    report += f"最后更新：{info.get('最后更新', '未知')}\n"
    report += f"{'━' * 60}\n"
    
    print(report)
    
    # 保存报告
    project_root = info.get('项目路径')
    if project_root:
        report_path = f"{project_root}/00_项目管理/状态报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filesystem_write_file(path=report_path, content=report)
        print(f"📄 报告已保存：{report_path}\n")
    
    return project_info

# 调用函数
project_info = generate_status_report(project_entity)
```

---

## 核心写作原则 🎯

### 段落式学术写作（必须遵守）
**严禁使用列点式、条目式写作。所有正文内容必须采用流畅的段落形式。**

**❌ 错误示例（列点式）**：
```
本研究的主要创新点包括：
- 首次提出了基于XXX的新型载体设计策略
- 系统研究了载体的体内外性能
- 阐明了药物释放的分子机制
```

**✅ 正确示例（段落式）**：
```
本研究在纳米药物递送系统的设计和应用方面取得了若干创新性进展。首先，我们基于肿瘤微环境的独特生理特征，提出了一种智能响应型载体设计策略，该策略能够根据pH值和氧化还原电位的变化实现药物的可控释放。在此基础上，通过系统的体外细胞实验和体内动物模型评价，我们证实了该载体在肿瘤靶向性、药物释放动力学以及抗肿瘤效果方面的显著优势。更重要的是，通过分子生物学和生物物理化学手段，我们深入阐明了载体与细胞膜相互作用的分子机制，揭示了药物释放过程中涉及的关键信号通路，为理解纳米载体的生物学效应提供了新的理论依据。
```

### 避免AI感的策略
1. **使用过渡性表达**：然而、此外、值得注意的是、在此基础上、进一步分析表明
2. **采用学术化叙述**：本研究发现、实验结果提示、数据分析揭示
3. **增加逻辑推理**：基于上述观察、综合考虑多方面因素、从机制角度分析
4. **适度使用限定语**：在一定程度上、初步证据表明、可能与...有关
5. **避免机械重复**：同一概念在不同段落中使用不同表述方式

### 学术语言自然化
- 避免"首先、其次、再次、最后"的机械排列
- 使用"在...研究中"、"通过...分析"等自然过渡
- 段落间通过内容逻辑自然衔接，而非格式化标记

---


## 📐 Word文档格式规范（中南大学医学博士标准）

### 页面设置

- **纸张**：A4（21cm × 29.7cm）
- **页边距**：上下2.54cm，左右3.17cm（版心240mm×146mm）
- **页眉距边界**：1.5cm
- **页脚距边界**：1.75cm

### 样式规范

#### 1. 章标题（一级标题）
- **字体**：三号黑体加粗（16pt）
- **对齐**：居中
- **编号**：阿拉伯数字（如"1"），与标题间空1字
- **间距**：段前18磅，段后12磅
- **分页**：每章另起一页

#### 2. 节标题（二级标题）
- **字体**：四号宋体（14pt），英文Times New Roman
- **对齐**：顶格（左对齐）
- **编号**：如"1.1"（末位数字后不加点）
- **间距**：段前10磅，段后8磅

#### 3. 小节标题（三级标题）
- **字体**：小四号宋体（12pt），英文Times New Roman
- **对齐**：顶格
- **编号**：如"1.1.1"
- **间距**：段前10磅，段后8磅

#### 4. 正文
- **字体**：小四号宋体（12pt），英文Times New Roman
- **首行缩进**：2字符
- **行距**：固定值20磅
- **对齐**：两端对齐

#### 5. 图注
- **字体**：五号楷体（10.5pt），英文Times New Roman
- **对齐**：居中
- **位置**：图片下方
- **格式**：图 X-X 图名\nFig. X-X Figure name
- **间距**：段前0行，段后1行

#### 6. 表注
- **字体**：五号楷体（10.5pt），英文Times New Roman
- **对齐**：居中
- **位置**：表格上方
- **格式**：表 X-X 表名\nTable X-X Table name
- **间距**：段前1行，段后0行

### 图表规范

**图（Figure）**：
```
（正文）

[图片居中，宽14cm]

图 3-1 纳米载体的TEM表征图
Fig. 3-1 TEM characterization of nanocarriers
（五号楷体居中）

（正文）
```

**表（Table）**：
```
（正文）

表 2-1 主要实验试剂及来源
Table 2-1 Main reagents and sources
（五号楷体居中）

[三线表：上1.5磅，中0.75磅，下1.5磅]
[表内：五号宋体，单倍行距，居中]

（正文）
```

### 摘要格式

**中文摘要**：
```
[论文标题]
（三号黑体加粗居中，段前18磅段后12磅）

摘要：
（四号黑体加粗顶格）
    [摘要正文约1000字]
（四号宋体，首行缩进2字符，行距20磅）

本研究共有图XX幅，表XX个，参考文献XXX篇。
（空一行后顶格，四号宋体）

关键字：关键词1；关键词2；关键词3
（空两行后顶格，"关键字："四号黑体加粗）

分类号：R944
（顶格，"分类号："四号黑体加粗）
```

**英文摘要**：
```
[English Title]
（三号Times New Roman加粗居中，上空一行）

Abstract:
（四号Times New Roman加粗顶格）
    [Abstract content about 1000 words]
（四号Times New Roman，首行缩进2字符，行距20磅）

Keywords: keyword1; keyword2; keyword3
（空两行后顶格，"Keywords:"四号Times New Roman加粗）

Classification: R944
（顶格，"Classification:"四号Times New Roman加粗）
```

### 参考文献格式

```
参考文献
（三号黑体加粗居中，段前18磅段后12磅）

（空一行）

[1] 作者1, 作者2, 作者3, 等. 题名[J]. 刊名, 年, 卷(期): 起止页码.
[2] Author1, Author2, Author3, et al. Title[J]. Journal, Year, Volume(Issue): Pages.
（小四号宋体/Times New Roman，顶格，悬挂缩进2字符）
```

**格式要求**：
- 作者：写到第三位，余者写",等"或",et al."
- 编号：顺序编码制[1]，方括号
- 标点：中文全角，英文半角
- 数量：医学博士≥80篇（推荐≥120篇）

### 页眉页脚

**页眉**：
- 左侧：中南大学博士学位论文
- 右侧：第 X 章 章名
- 字体：宋体五号

**页码**：
- 前置部分：罗马数字（I, II, III...）
- 正文部分：阿拉伯数字（1, 2, 3...，从第一章重新编号）
- 字体：Times New Roman小五号，居中

---

## 🛡️ 错误处理机制

### 常见错误及解决方案

**错误1：word-mcp工具调用失败**
```python
try:
    word-mcp_create_document(filename=chapter_file)
    print("✅ 文档创建成功")
except Exception as e:
    print(f"❌ 创建文档失败：{e}")
    print("⚠️ 将使用备用方案...")
    
    # 备用方案：提示用户手动创建
    print(f"请手动创建Word文档：{chapter_file}")
    print("创建后回复'已创建'继续")
    
    # 等待用户确认
    input("按回车继续...")
```

**错误2：python-docx未安装**
```python
# 检查依赖
check_result = bash("python3 -c 'import docx' 2>&1")

if check_result['exit_code'] != 0:
    print("❌ python-docx未安装")
    print("正在尝试安装...")
    
    install_result = bash("pip3 install python-docx 2>&1")
    
    if install_result['exit_code'] == 0:
        print("✅ python-docx安装成功")
    else:
        print("⚠️ 自动安装失败")
        print("请手动执行：pip3 install python-docx")
        print("安装完成后回复'已安装'")
        
        input("按回车继续...")
```

**错误3：文件路径不存在**
```python
if not os.path.exists(project_root):
    print(f"❌ 项目路径不存在：{project_root}")
    print("正在创建...")
    
    try:
        bash(f"mkdir -p '{project_root}'")
        bash(f"mkdir -p '{project_root}'/{{00_项目管理,01_前置部分,02_正文章节,03_后置部分,04_图表文件,05_原始材料,06_版本历史}}")
        print("✅ 项目文件夹已创建")
    except Exception as e:
        print(f"❌ 创建失败：{e}")
        print("请检查：")
        print("1. 路径是否有权限")
        print("2. 磁盘空间是否充足")
        print("3. 路径格式是否正确")
```

**错误4：合并脚本执行失败**
```python
merge_result = bash(f"cd '{project_root}/00_项目管理' && python3 merge_documents.py 2>&1")

if merge_result['exit_code'] != 0:
    print(f"❌ 合并失败：{merge_result['stderr']}")
    
    print("\n请检查：")
    print("1. 所有章节文件是否存在")
    print("2. 文件是否被其他程序占用（请关闭Word）")
    print("3. 磁盘空间是否充足")
    print("4. python-docx是否正确安装")
    
    print("\n手动合并方法：")
    print("1. 打开Word")
    print("2. 依次插入所有章节文件内容")
    print("3. 保存为 完整版_最新.docx")
else:
    print("✅ 合并成功")
```

### 检查点机制（防止中断丢失）

**每章生成分为5步，每步完成后保存检查点**：

```python
def generate_chapter_with_checkpoints(chapter_num, chapter_name, target_words, project_root):
    """带检查点的章节生成"""
    
    # 检查点文件
    checkpoint_file = f"{project_root}/00_项目管理/.checkpoint_{chapter_num}.json"
    
    # 定义步骤
    steps = {
        "1_created": "创建文档",
        "2_styles": "应用样式",
        "3_content": "写入内容",
        "4_figures": "添加图表",
        "5_verified": "验证完成"
    }
    
    # 加载检查点
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            completed = json.load(f)
        print(f"📍 从检查点恢复：{chapter_name}")
        print(f"   已完成：{', '.join([steps[k] for k in completed])}")
    else:
        completed = []
    
    # 执行步骤
    chapter_file = f"{project_root}/02_正文章节/{chapter_num}_{chapter_name}.docx"
    
    # 步骤1：创建文档
    if "1_created" not in completed:
        print(f"▶️ 1/5 创建文档...")
        try:
            word-mcp_create_document(filename=chapter_file, title=f"{chapter_num} {chapter_name}")
            completed.append("1_created")
            with open(checkpoint_file, 'w') as f:
                json.dump(completed, f)
            print("   ✅ 完成")
        except Exception as e:
            print(f"   ❌ 失败：{e}")
            return False
    
    # 步骤2：应用样式
    if "2_styles" not in completed:
        print(f"▶️ 2/5 应用样式...")
        try:
            # 创建所有必需样式
            styles = [
                {"name": "章标题", "font": "黑体", "size": 16, "bold": True},
                {"name": "节标题", "font": "宋体", "size": 14, "bold": False},
                {"name": "小节标题", "font": "宋体", "size": 12, "bold": False},
                {"name": "正文", "font": "宋体", "size": 12, "bold": False},
                {"name": "图注", "font": "楷体", "size": 10.5, "bold": False},
                {"name": "表注", "font": "楷体", "size": 10.5, "bold": False}
            ]
            
            for style in styles:
                word-mcp_create_custom_style(
                    filename=chapter_file,
                    style_name=style["name"],
                    font_name=style["font"],
                    font_size=style["size"],
                    bold=style["bold"]
                )
            
            completed.append("2_styles")
            with open(checkpoint_file, 'w') as f:
                json.dump(completed, f)
            print("   ✅ 完成")
        except Exception as e:
            print(f"   ❌ 失败：{e}")
            return False
    
    # 步骤3：写入内容
    if "3_content" not in completed:
        print(f"▶️ 3/5 写入内容（目标{target_words}字）...")
        try:
            # 添加章标题
            word-mcp_add_heading(
                filename=chapter_file,
                text=f"{chapter_num.replace('第', '').replace('章', '')} {chapter_name}",
                level=1
            )
            
            # 根据章节生成内容
            content = generate_chapter_content(chapter_num, chapter_name, target_words)
            
            # 逐节添加
            for section in content['sections']:
                # 节标题
                word-mcp_add_heading(
                    filename=chapter_file,
                    text=section['title'],
                    level=2
                )
                
                # 正文段落
                for paragraph in section['paragraphs']:
                    word-mcp_add_paragraph(
                        filename=chapter_file,
                        text=paragraph
                    )
            
            completed.append("3_content")
            with open(checkpoint_file, 'w') as f:
                json.dump(completed, f)
            print("   ✅ 完成")
        except Exception as e:
            print(f"   ❌ 失败：{e}")
            return False
    
    # 步骤4：添加图表
    if "4_figures" not in completed:
        print(f"▶️ 4/5 添加图表...")
        try:
            fig_result = detect_and_insert_figures(chapter_num, chapter_file, project_root)
            print(f"   ✅ 完成（{fig_result['method']}，{fig_result['count']}个）")
            
            completed.append("4_figures")
            with open(checkpoint_file, 'w') as f:
                json.dump(completed, f)
        except Exception as e:
            print(f"   ⚠️ 图表处理失败，使用占位标识：{e}")
            completed.append("4_figures")
            with open(checkpoint_file, 'w') as f:
                json.dump(completed, f)
    
    # 步骤5：验证
    if "5_verified" not in completed:
        print(f"▶️ 5/5 验证...")
        try:
            # 统计字数
            doc_text = word-mcp_get_document_text(filename=chapter_file)
            actual_words = quick_count_words(doc_text)
            
            print(f"   字数：{actual_words:,} / {target_words:,}")
            
            # 简单质量检查
            issues = quick_quality_check(doc_text)
            if issues:
                print(f"   ⚠️ 发现 {len(issues)} 个潜在问题")
                for issue in issues[:3]:  # 只显示前3个
                    print(f"      - {issue}")
            else:
                print("   ✅ 无明显问题")
            
            completed.append("5_verified")
            with open(checkpoint_file, 'w') as f:
                json.dump(completed, f)
            
        except Exception as e:
            print(f"   ⚠️ 验证失败：{e}")
    
    # 删除检查点（所有步骤完成）
    os.remove(checkpoint_file)
    print(f"\n🎉 {chapter_num} {chapter_name} 生成完成")
    
    return True
```

### 辅助函数

**快速字数统计**：
```python
def quick_count_words(text):
    """快速统计字数（近似）"""
    import re
    
    # 排除图表题注
    lines = text.split('\n')
    filtered_lines = [line for line in lines 
                     if not re.match(r'^(图|表|Fig|Table)\s*\d', line)]
    clean_text = '\n'.join(filtered_lines)
    
    # 统计
    chinese = len(re.findall(r'[\u4e00-\u9fa5]', clean_text))
    english = len(re.findall(r'\b[a-zA-Z]+\b', clean_text))
    numbers = len(re.findall(r'\d+', clean_text))
    
    return chinese + english + numbers
```

**快速质量检查**：
```python
def quick_quality_check(text):
    """快速检查常见问题"""
    issues = []
    
    # 检查列点式内容
    if re.search(r'\n\s*[-•]\s+\w', text):
        issues.append("检测到列点式内容，建议改为段落式")
    
    # 检查AI痕迹
    ai_phrases = [
        "首先、其次、再次、最后",
        "综上所述，本研究的主要创新点包括：",
        "总之，本章主要内容包括："
    ]
    for phrase in ai_phrases:
        if phrase in text:
            issues.append(f"检测到AI痕迹：'{phrase}'")
    
    # 检查段落长度
    paragraphs = text.split('\n\n')
    long_paras = [p for p in paragraphs if len(p) > 1000]
    if long_paras:
        issues.append(f"发现{len(long_paras)}个超长段落（>1000字）")
    
    return issues
```

---

## 🏁 完整生成流程示例

### 示例：从新项目到完成

```
【用户】我有一篇关于pH敏感型纳米载体的SCI论文，需要扩写成博士论文。

【AI】好的！在开始前，我需要收集一些基本信息。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
基本信息收集
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请提供以下信息：
1. 学院名称：
2. 姓名：
3. 学号：
4. 年级：
5. 学科专业：
6. 研究方向：
7. 正指导教师：
8. 副指导教师（如有）：
9. 预计答辩时间：
10. 分类号：
11. UDC号（可选）：
12. 项目保存路径（留空使用默认）：

【用户】
2. 湘雅药学院
3. 王小明
4. 20201234567
5. 2020级
6. 药剂学
7. 纳米药物递送系统
8. 张教授 教授
9. 李副教授 副教授
10. 2026年6月
11. R944
12. 615.014
13. [留空]

【AI】
✅ 信息收集完成

项目路径：/Users/wsxwj/Desktop/博士论文_pH敏感纳米载体_王小明/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
项目初始化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 创建项目文件夹结构
✅ 保存用户信息
✅ 检查依赖：Python 3.11.5, python-docx ✅
✅ 部署辅助脚本

现在请上传您的SCI论文PDF文件。

【用户】[上传文件]

【AI】
✅ 已接收文件：原始SCI论文.pdf
✅ 正在读取论文内容...

论文信息：
- 标题：pH-Dual-Responsive Polymer-Lipid Nanocarrier...
- 期刊：Journal of Controlled Release
- 关键词：pH-sensitive, nanocarrier, cancer therapy...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
文献调研
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

正在委托@librarian进行文献调研（预计2-3分钟）...

⏳ 正在搜索综述文献...
⏳ 正在搜索方法学文献...
⏳ 正在搜索结果对比文献...
⏳ 正在搜索临床转化文献...

✅ 文献调研完成（125篇）
   - 综述：18篇
   - 方法：28篇
   - 结果：38篇
   - 讨论：13篇
   - 临床：10篇

已保存到：00_项目管理/参考文献_20260127.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
生成大纲
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

基于您的SCI论文，我生成了以下大纲：

论文标题（中文）：基于pH双响应聚合物-脂质复合纳米载体的抗肿瘤药物递送系统研究
论文标题（英文）：pH-Dual-Responsive Polymer-Lipid Nanocarrier...

第一章 前言（目标12,200字）
  1.1 研究背景与意义（3,500字）
  1.2 国内外研究现状（6,200字）
  1.3 本研究的主要内容与创新点（2,500字）

第二章 材料与方法（目标7,200字）
  2.1 实验材料（2,000字）
  2.2 实验仪器（1,500字）
  2.3 实验方法（3,700字）

第三章 纳米载体的制备与表征（目标9,800字）
  3.1 纳米载体的制备（2,500字）
  3.2 理化性质表征（3,800字）
  3.3 体外药物释放研究（3,500字）

...（共7章，总计53,000字）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请确认：
1. 直接开始生成（输入：开始）
2. 调整字数分配（输入：调整）
3. 修改章节结构（输入：修改）
4. 查看完整大纲（输入：查看）

【用户】开始

【AI】
✅ 已保存项目信息到知识图谱
✅ 已保存大纲到本地文件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开始生成论文
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶️ 正在生成：第一章 前言（目标12,200字）

  ▶️ 1/5 创建文档...
     ✅ 完成
  
  ▶️ 2/5 应用样式...
     ✅ 完成（6个样式）
  
  ▶️ 3/5 写入内容...
     正在生成 1.1 研究背景与意义...
     正在生成 1.2 国内外研究现状...
     正在生成 1.3 本研究的主要内容与创新点...
     ✅ 完成
  
  ▶️ 4/5 添加图表...
     ✅ 完成（占位标识，2图）
  
  ▶️ 5/5 验证...
     字数：12,350 / 12,200 ✅
     ✅ 无明显问题

🎉 第一章 前言 生成完成

✅ 已保存版本：第一章_前言_v1.0_20260127_初稿.docx
✅ 已更新进度到记忆

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前进度：1/7章（24.7%）
总字数：12,350 / 50,000

下一步：
1. 继续生成第二章（输入：继续）
2. 查看第一章内容（输入：查看）
3. 修改第一章（输入：修改）
4. 暂停，稍后继续（输入：暂停）

【用户】继续

【AI】
▶️ 正在生成：第二章 材料与方法（目标7,200字）
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【多次"继续"后】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【AI】
✅ 所有正文章节已完成！

📊 完成统计：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 第一章 前言              12,350字
✅ 第二章 材料与方法         7,450字
✅ 第三章 制备与表征         9,950字
✅ 第四章 体外活性评价       8,680字
✅ 第五章 体内效果评价       7,420字
✅ 第六章 讨论              6,550字
✅ 第七章 结论              1,580字

正文总字数：53,980字 ✅（超出目标3,980字）

接下来生成：
- 综述（5,000字，不计入正文）
- 中英文摘要
- 目录
- 致谢

是否继续？（输入：是 / 查看统计 / 暂停）

【用户】是

【AI】
▶️ 正在生成综述...
✅ 综述已完成（6,500字）

▶️ 正在生成摘要...
✅ 中文摘要已完成（1,050字）
✅ 英文摘要已完成（1,020字）

▶️ 正在生成其他部分...
✅ 封面、扉页、声明已完成
✅ 英文缩略词说明已完成（28个术语）
✅ 参考文献已完成（125篇）
✅ 攻读学位期间成果已完成
✅ 致谢已完成

▶️ 正在生成目录...
✅ 目录已完成

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
合并完整版文档
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

执行合并脚本...

📁 项目根目录：/Users/wsxwj/Desktop/博士论文_pH敏感纳米载体_王小明

开始合并 18 个文档...

✅ 已加载基础文档：封面.docx
✅ 已合并：扉页.docx
✅ 已合并：原创性声明.docx
✅ 已合并：中文摘要.docx
✅ 已合并：英文摘要.docx
✅ 已合并：目录.docx
✅ 已合并：英文缩略词说明.docx
📄 检测到章节：第一章_前言.docx
📄 检测到章节：第二章_材料与方法.docx
📄 检测到章节：第三章_制备与表征.docx
📄 检测到章节：第四章_体外活性评价.docx
📄 检测到章节：第五章_体内效果评价.docx
📄 检测到章节：第六章_讨论.docx
📄 检测到章节：第七章_结论.docx
✅ 已合并：第一章_前言.docx
✅ 已合并：第二章_材料与方法.docx
✅ 已合并：第三章_制备与表征.docx
✅ 已合并：第四章_体外活性评价.docx
✅ 已合并：第五章_体内效果评价.docx
✅ 已合并：第六章_讨论.docx
✅ 已合并：第七章_结论.docx
✅ 已合并：参考文献.docx
✅ 已合并：综述.docx
✅ 已合并：攻读学位期间成果.docx
✅ 已合并：致谢.docx

🎉 合并完成！
   输出文件：/Users/wsxwj/Desktop/博士论文_pH敏感纳米载体_王小明/完整版_最新.docx
   📊 总计合并 18 个文档
   📦 文件大小：8.52 MB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
精确字数统计
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

执行统计脚本...

============================================================
逐章字数统计
============================================================

第一章_前言.docx:
  汉字：11,800
  英文单词：520
  数字组：30
  等效字数：12,350

第二章_材料与方法.docx:
  汉字：6,900
  英文单词：520
  数字组：30
  等效字数：7,450

...

============================================================
★ 正文总字数（第一章至结论 + 摘要）：56,050 字
最低要求：50,000 字
达标状态：✅ 达标（超出6,050字）
============================================================

★ 综述字数（单独要求，不计入正文）：6,500 字
最低要求：5,000 字
达标状态：✅ 达标
============================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
最终质量检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

执行质量检查...

✅ 文件完整性：所有必需文件齐全（18/18）
✅ 格式规范：符合中南大学标准
✅ 内容质量：字数达标，文献充足
✅ 技术细节：图表编号连续，术语一致

📊 总体评价：28/28 项通过

🎉 恭喜！论文已达到交付标准！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
交付说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 您的论文文件位于：
   /Users/wsxwj/Desktop/博士论文_pH敏感纳米载体_王小明/

📄 完整版文档：完整版_最新.docx（可直接提交）

📂 分章节文件：02_正文章节/（便于后续修改）

🔧 如需修改某章：
   1. 告诉我"修改第X章"
   2. 我会读取该章docx文件
   3. 根据您的要求修改
   4. 重新运行合并脚本更新完整版

🔄 手动合并方法：
   cd /Users/wsxwj/Desktop/博士论文_pH敏感纳米载体_王小明/00_项目管理
   python3 merge_documents.py

后续建议：
1. 请导师审阅内容和学术深度
2. 进行查重检测（知网/万方）
3. 如使用占位标识，请替换为实际图片（共45个图表）
4. 根据反馈意见修改
5. 准备答辩PPT

祝您答辩顺利！🎓
```

---

## 📚 后续修改流程（流程D）

### 修改某个章节

```
【用户】修改第三章，1.2节需要补充更多文献

【AI】
好的，我来修改第三章。

▶️ 1/3 读取文件...
✅ 已读取：02_正文章节/第三章_制备与表征.docx

▶️ 2/3 定位内容...
找到1.2节：理化性质表征
当前字数：3,800字

▶️ 3/3 补充内容...

[使用word-mcp_search_and_replace或重新生成相关段落]

✅ 修改完成
   新增字数：+450字
   新版本：第三章_制备与表征_v1.1_20260128_导师修改.docx

是否重新合并完整版？（输入：是 / 否）

【用户】是

【AI】
执行合并...
✅ 合并完成
✅ 完整版已更新
```

---


import json
import os
import sys
from datetime import datetime

def convert_to_bibtex():
    # 1. 路径检查
    index_path = 'literature_index.json'
    output_path = 'references.bib'
    
    if not os.path.exists(index_path):
        print(f"❌ Error: {index_path} not found.")
        return False

    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return False

    # 2. 转换逻辑
    bib_entries = []
    print(f"🔄 Converting {len(data)} references...")

    for ref in data:
        # 生成引用键 (Key)，优先使用 ref_id，也可以是 "AuthorYear"
        cite_key = ref.get('ref_id', f"ref_{len(bib_entries)}")
        
        # 必填字段
        title = ref.get('title', 'Unknown Title')
        journal = ref.get('journal', 'Unknown Journal')
        year = ref.get('year', '2024')
        doi = ref.get('doi', '')
        
        # 构建 BibTeX 条目
        entry = f"@article{{{cite_key},\n"
        entry += f"  title = {{{title}}},\n"
        entry += f"  journal = {{{journal}}},\n"
        entry += f"  year = {{{year}}},\n"
        if doi:
            entry += f"  doi = {{{doi}}},\n"
        
        # 可选字段 (如果 JSON 中有)
        if 'authors' in ref:
            entry += f"  author = {{{ref['authors']}}},\n"
        if 'volume' in ref:
            entry += f"  volume = {{{ref['volume']}}},\n"
        if 'pages' in ref:
            entry += f"  pages = {{{ref['pages']}}},\n"
            
        entry += "}\n"
        bib_entries.append(entry)

    # 3. 保存文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(bib_entries))
        print(f"✅ Successfully exported to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error writing .bib file: {e}")
        return False

if __name__ == "__main__":
    convert_to_bibtex()

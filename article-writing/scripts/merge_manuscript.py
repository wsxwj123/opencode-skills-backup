import os
import glob
import sys
import subprocess
import json

def merge_and_convert():
    # 1. 定义顺序
    # 这里的通配符非常重要，必须能匹配原子化文件 (如 04_Results_3.1_Title.md)
    order_patterns = [
        '01_Abstract*.md',
        '02_Introduction*.md',
        '03_Methods*.md',
        '04_Results*.md',     # 匹配所有 04_Results 开头的文件
        '05_Discussion*.md',
        '06_Conclusion*.md',
        '07_References*.md'
    ]
    
    manuscript_dir = 'manuscripts'
    output_md = os.path.join(manuscript_dir, 'Full_Manuscript.md')
    output_docx = os.path.join(manuscript_dir, 'Full_Manuscript.docx')
    
    if not os.path.exists(manuscript_dir):
        print(f"❌ Error: {manuscript_dir} directory not found.")
        return

    # 2. 合并内容
    full_content = ""
    print("🔄 Merging files...")
    
    # 这一步会自动按文件名排序，这正是我们想要的 (04_Results_3.1 < 04_Results_3.2)
    for pattern in order_patterns:
        full_pattern = os.path.join(manuscript_dir, pattern)
        files = sorted(glob.glob(full_pattern))
        
        if not files:
            # 如果没有找到文件，不报错，继续下一个（可能该章节还未写）
            continue
            
        for file_path in files:
            print(f"   + Adding {os.path.basename(file_path)}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        full_content += content + "\n\n---\n\n"
            except Exception as e:
                print(f"❌ Error reading {file_path}: {e}")

    # 3. 保存 Markdown
    try:
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ Merged Markdown saved to: {output_md}")
    except Exception as e:
        print(f"❌ Error writing markdown: {e}")
        return

    # 4. 尝试转换为 Docx (依赖系统 Pandoc)
    print("🔄 Attempting Docx conversion using pandoc...")
    try:
        # 检查 pandoc 是否存在
        subprocess.run(['pandoc', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # 执行转换
        cmd = ['pandoc', output_md, '-o', output_docx, '--reference-doc=custom-reference.docx'] if os.path.exists('custom-reference.docx') else ['pandoc', output_md, '-o', output_docx]
        
        subprocess.run(cmd, check=True)
        print(f"✅ Docx generated: {output_docx}")
        
    except FileNotFoundError:
        print("⚠️ Pandoc not found in system PATH. Skipping Docx conversion.")
        print("   (You can still use the Full_Manuscript.md file)")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")

if __name__ == "__main__":
    merge_and_convert()

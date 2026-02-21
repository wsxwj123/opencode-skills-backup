#!/usr/bin/env python3
"""
查找并更新 MCP 服务器的 GitHub 仓库地址
"""

import os
import subprocess
import json
from pathlib import Path

# MCP 服务器目录
MCP_BASE_DIR = Path.home() / "Documents" / "Cline" / "MCP"

# 需要查找 Git 仓库的 MCP 服务器
MCP_SERVERS = [
    {
        "name": "file-to-pdf",
        "path": MCP_BASE_DIR / "file-to-pdf" / "file-converter-mcp",
        "description": "文件格式转换"
    },
    {
        "name": "office-editor",
        "path": MCP_BASE_DIR / "ms-edit-mcp" / "office-editor-mcp-main",
        "description": "Office 文档编辑"
    },
    {
        "name": "ppt-mcp",
        "path": MCP_BASE_DIR / "ppt-mcp",
        "description": "PowerPoint 操作"
    },
    {
        "name": "word-mcp",
        "path": MCP_BASE_DIR / "word-mcp" / "Office-Word-MCP-Server",
        "description": "Word 文档操作"
    },
    {
        "name": "claude-document",
        "path": MCP_BASE_DIR / "document",
        "description": "Claude 文档处理"
    },
    {
        "name": "reddit",
        "path": MCP_BASE_DIR / "mcp-server-reddit",
        "description": "Reddit 数据访问"
    },
    {
        "name": "paper-search",
        "path": MCP_BASE_DIR / "paper-search-mcp" / "paper-search-mcp",
        "description": "学术论文搜索"
    },
    {
        "name": "quickchart",
        "path": MCP_BASE_DIR / "quickchart-mcp-server",
        "description": "图表生成"
    },
    {
        "name": "drawio",
        "path": MCP_BASE_DIR / "drawio-mcp-server" / "drawio-mcp-server",
        "description": "Draw.io 图表编辑"
    },
    {
        "name": "markdownify",
        "path": MCP_BASE_DIR / "markdownify",
        "description": "格式转换为 Markdown"
    }
]


def get_git_remote(repo_path):
    """获取 Git 仓库的远程地址"""
    try:
        if not repo_path.exists():
            return None, f"路径不存在: {repo_path}"
        
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 解析 git remote -v 的输出
        lines = result.stdout.strip().split('\n')
        remotes = {}
        
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                remote_name = parts[0]
                remote_url = parts[1]
                if remote_name not in remotes:
                    remotes[remote_name] = remote_url
        
        # 优先返回 origin，否则返回第一个
        return remotes.get('origin', list(remotes.values())[0] if remotes else None), None
        
    except subprocess.CalledProcessError:
        return None, "不是 Git 仓库或无远程地址"
    except Exception as e:
        return None, f"错误: {str(e)}"


def main():
    """主函数"""
    print("=" * 80)
    print("MCP 服务器 Git 仓库查找工具")
    print("=" * 80)
    print()
    
    results = []
    
    for server in MCP_SERVERS:
        name = server['name']
        path = server['path']
        desc = server['description']
        
        print(f"📦 {name} ({desc})")
        print(f"   路径: {path}")
        
        remote_url, error = get_git_remote(path)
        
        if remote_url:
            print(f"   ✅ Git 仓库: {remote_url}")
            results.append({
                "name": name,
                "description": desc,
                "path": str(path),
                "git_repo": remote_url,
                "status": "success"
            })
        else:
            print(f"   ❌ {error}")
            results.append({
                "name": name,
                "description": desc,
                "path": str(path),
                "git_repo": None,
                "status": "failed",
                "error": error
            })
        
        print()
    
    # 保存结果到 JSON 文件
    output_file = Path(__file__).parent / "mcp_repos.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("=" * 80)
    print(f"✅ 结果已保存到: {output_file}")
    
    # 统计
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = len(results) - success_count
    
    print(f"📊 统计: 成功 {success_count} 个，失败 {failed_count} 个")
    print("=" * 80)


if __name__ == "__main__":
    main()

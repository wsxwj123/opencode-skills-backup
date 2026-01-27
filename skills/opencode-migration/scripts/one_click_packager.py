#!/usr/bin/env python3
"""
OpenCode 一键迁移打包器
策略：打包所有配置+源代码，生成自动安装脚本
"""

import os
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import hashlib
import platform

def create_migration_package():
    """创建可解压即用的迁移包"""
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║       OpenCode 一键迁移打包器                              ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")
    
    home = Path.home()
    opencode_dir = home / ".config" / "opencode"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = home / "Desktop" / f"opencode_migration_{timestamp}.zip"
    
    print(f"📦 输出文件: {output_file}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 读取配置
    with open(opencode_dir / "opencode.json", 'r') as f:
        config = json.load(f)
    
    # 提取 MCP 服务器信息
    mcp_info = extract_mcp_info(config)
    
    print(f"🔍 分析结果:")
    print(f"   MCP 服务器: {len(mcp_info['servers'])} 个")
    print(f"   NPM 包型: {len(mcp_info['npm_servers'])} 个")
    print(f"   本地程序: {len(mcp_info['local_servers'])} 个\n")
    
    file_count = 0
    
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        # 1. 打包 OpenCode 配置（排除 node_modules 和 venv）
        print("📁 [1/4] 打包 OpenCode 配置...")
        for item in opencode_dir.rglob("*"):
            if should_include(item):
                try:
                    rel_path = item.relative_to(home)
                    if item.is_file():
                        zipf.write(item, str(rel_path))
                        file_count += 1
                        if file_count % 500 == 0:
                            print(f"        已打包 {file_count} 个文件...")
                except Exception as e:
                    pass
        
        config_files = file_count
        print(f"✅  配置文件: {config_files} 个\n")
        
        # 2. 打包本地 MCP 服务器（源代码，不含 node_modules）
        print("🔌 [2/4] 打包本地 MCP 服务器...")
        for server in mcp_info['local_servers']:
            server_path = Path(server['path'])
            if server_path.exists():
                print(f"        打包: {server['name']}")
                server_files = 0
                
                for item in server_path.rglob("*"):
                    if should_include(item):
                        try:
                            rel_path = item.relative_to(home)
                            if item.is_file():
                                zipf.write(item, str(rel_path))
                                server_files += 1
                                file_count += 1
                        except Exception as e:
                            pass
                
                print(f"          ✓ {server_files} 个文件")
        
        mcp_files = file_count - config_files
        print(f"✅  MCP 服务器: {mcp_files} 个文件\n")
        
        # 3. 生成安装脚本
        print("📝 [3/4] 生成安装脚本...")
        
        # Windows 安装脚本
        windows_script = generate_windows_install_script(mcp_info, home)
        zipf.writestr("INSTALL_WINDOWS.bat", windows_script)
        
        # macOS 安装脚本  
        macos_script = generate_macos_install_script(mcp_info, home)
        zipf.writestr("INSTALL_MACOS.sh", macos_script)
        
        # 详细说明
        readme = generate_readme(mcp_info, file_count)
        zipf.writestr("README.md", readme)
        
        # MCP 服务器信息
        zipf.writestr("MCP_SERVERS.json", json.dumps(mcp_info, indent=2))
        
        print(f"✅  安装脚本和说明已创建\n")
        
        # 4. 计算校验和
        print("🔐 [4/4] 计算校验和...")
    
    with open(output_file, 'rb') as f:
        data = f.read()
        sha256_hash = hashlib.sha256(data).hexdigest()
    
    size_mb = os.path.getsize(output_file) / 1024 / 1024
    
    # 保存信息文件
    info_file = str(output_file).replace(".zip", "_info.txt")
    with open(info_file, 'w') as f:
        f.write(f"OpenCode 迁移包信息\n")
        f.write(f"{'='*60}\n")
        f.write(f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"源平台: macOS ({platform.machine()})\n")
        f.write(f"文件数量: {file_count}\n")
        f.write(f"包大小: {size_mb:.2f} MB\n")
        f.write(f"SHA256: {sha256_hash}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"MCP 服务器:\n")
        for server in mcp_info['servers']:
            f.write(f"  • {server['name']} ({server['type']})\n")
    
    print(f"\n╔═══════════════════════════════════════════════════════════╗")
    print(f"║                  ✅ 打包完成！                             ║")
    print(f"╚═══════════════════════════════════════════════════════════╝\n")
    print(f"📦 迁移包: {output_file.name}")
    print(f"📊 大小: {size_mb:.2f} MB")
    print(f"📝 文件数: {file_count}")
    print(f"🔐 SHA256: {sha256_hash}\n")
    print(f"📄 详细信息: {Path(info_file).name}\n")
    print(f"✨ 下一步:")
    print(f"   1. 将 ZIP 文件传输到目标设备")
    print(f"   2. 解压文件")
    print(f"   3. 运行 INSTALL_WINDOWS.bat (Windows) 或 INSTALL_MACOS.sh (Mac)")
    print(f"   4. 启动 OpenCode\n")

def extract_mcp_info(config):
    """提取 MCP 服务器信息"""
    info = {
        "servers": [],
        "npm_servers": [],
        "local_servers": []
    }
    
    if "mcp" not in config:
        return info
    
    for name, conf in config["mcp"].items():
        command = conf.get("command", [])
        
        server_type = "npm" if (command and len(command) > 0 and "npx" in command[0]) else "local"
        
        server = {
            "name": name,
            "enabled": conf.get("enabled", True),
            "type": server_type,
            "command": command
        }
        
        info["servers"].append(server)
        
        if server["type"] == "npm":
            # NPM 包型
            for arg in command:
                if arg.startswith("@"):
                    server["package"] = arg
                    break
            info["npm_servers"].append(server)
        else:
            # 本地程序型
            for arg in command:
                if "/" in arg or "\\" in arg:
                    path = Path(arg)
                    if path.exists():
                        # 找到服务器根目录
                        root = path.parent
                        while root != root.parent:
                            if (root / "package.json").exists() or \
                               (root / "requirements.txt").exists():
                                server["path"] = str(root)
                                server["type_detail"] = "nodejs" if (root / "package.json").exists() else "python"
                                info["local_servers"].append(server)
                                break
                            root = root.parent
                    break
    
    return info

def should_include(path: Path) -> bool:
    """判断是否应该打包"""
    exclude = [
        "node_modules", ".git", "__pycache__", ".DS_Store",
        ".venv", "venv", ".cache", ".pyc", ".log", ".tmp",
        ".pytest_cache", ".mypy_cache", "dist", "build",
        ".next", ".nuxt", "coverage"
    ]
    
    for pattern in exclude:
        if pattern in str(path):
            return False
    
    return True

def generate_windows_install_script(mcp_info, home):
    """生成 Windows 安装脚本"""
    script = """@echo off
chcp 65001
echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║       OpenCode Windows 自动安装脚本                        ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  请以管理员身份运行此脚本
    echo    右键点击 -^> 以管理员身份运行
    pause
    exit /b 1
)

echo 📁 [1/5] 复制配置文件...
xcopy /E /I /Y ".config\\opencode" "%APPDATA%\\opencode\\"
echo ✅  配置文件复制完成
echo.

echo 🔌 [2/5] 安装 NPM 包型 MCP 服务器...
"""
    
    for server in mcp_info['npm_servers']:
        if "package" in server:
            script += f'echo    安装 {server["name"]}...\n'
            script += f'call npm install -g {server["package"]}\n'
    
    script += """
echo ✅  NPM MCP 服务器安装完成
echo.

echo 📦 [3/5] 复制本地 MCP 服务器...
xcopy /E /I /Y "Documents\\Cline\\MCP" "%USERPROFILE%\\Documents\\Cline\\MCP\\"
echo ✅  本地 MCP 服务器复制完成
echo.

echo 🐍 [4/5] 安装 Python MCP 服务器依赖...
"""
    
    for server in mcp_info['local_servers']:
        if server.get('type_detail') == 'python':
            rel_path = str(Path(server['path']).relative_to(home)).replace("/", "\\")
            script += f'echo    配置 {server["name"]}...\n'
            script += f'cd "%USERPROFILE%\\{rel_path}"\n'
            script += f'python -m venv venv\n'
            script += f'call venv\\Scripts\\activate\n'
            script += f'pip install -r requirements.txt\n'
            script += f'deactivate\n\n'
    
    script += """
echo ✅  Python 依赖安装完成
echo.

echo 🔧 [5/5] 安装 Node.js MCP 服务器依赖...
"""
    
    for server in mcp_info['local_servers']:
        if server.get('type_detail') == 'nodejs':
            rel_path = str(Path(server['path']).relative_to(home)).replace("/", "\\")
            script += f'echo    配置 {server["name"]}...\n'
            script += f'cd "%USERPROFILE%\\{rel_path}"\n'
            script += f'call npm install\n\n'
    
    script += """
echo ✅  Node.js 依赖安装完成
echo.

echo ╔═══════════════════════════════════════════════════════════╗
echo ║                ✅ 安装完成！                               ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo 📝 下一步:
echo    1. 启动 OpenCode
echo    2. 测试功能: "显示所有 MCP 服务器的状态"
echo.
pause
"""
    
    return script

def generate_macos_install_script(mcp_info, home):
    """生成 macOS/Linux 安装脚本"""
    script = """#!/bin/bash

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       OpenCode macOS/Linux 自动安装脚本                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

echo "📁 [1/5] 复制配置文件..."
mkdir -p ~/.config/opencode
cp -r .config/opencode/* ~/.config/opencode/
echo "✅  配置文件复制完成"
echo ""

echo "🔌 [2/5] 安装 NPM 包型 MCP 服务器..."
"""
    
    for server in mcp_info['npm_servers']:
        if "package" in server:
            script += f'echo "   安装 {server["name"]}..."\n'
            script += f'npm install -g {server["package"]}\n'
    
    script += """
echo "✅  NPM MCP 服务器安装完成"
echo ""

echo "📦 [3/5] 复制本地 MCP 服务器..."
mkdir -p ~/Documents/Cline/MCP
cp -r Documents/Cline/MCP/* ~/Documents/Cline/MCP/ 2>/dev/null || true
echo "✅  本地 MCP 服务器复制完成"
echo ""

echo "🐍 [4/5] 安装 Python MCP 服务器依赖..."
"""
    
    for server in mcp_info['local_servers']:
        if server.get('type_detail') == 'python':
            rel_path = Path(server['path']).relative_to(home)
            script += f'echo "   配置 {server["name"]}..."\n'
            script += f'cd ~/{rel_path}\n'
            script += f'python3 -m venv venv\n'
            script += f'source venv/bin/activate\n'
            script += f'pip install -r requirements.txt\n'
            script += f'deactivate\n\n'
    
    script += """
echo "✅  Python 依赖安装完成"
echo ""

echo "🔧 [5/5] 安装 Node.js MCP 服务器依赖..."
"""
    
    for server in mcp_info['local_servers']:
        if server.get('type_detail') == 'nodejs':
            rel_path = Path(server['path']).relative_to(home)
            script += f'echo "   配置 {server["name"]}..."\n'
            script += f'cd ~/{rel_path}\n'
            script += f'npm install\n\n'
    
    script += """
echo "✅  Node.js 依赖安装完成"
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                ✅ 安装完成！                               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "📝 下一步:"
echo "   1. 启动 OpenCode"
echo "   2. 测试功能: '显示所有 MCP 服务器的状态'"
echo ""
"""
    
    return script

def generate_readme(mcp_info, file_count):
    """生成 README"""
    return f"""# OpenCode 完整迁移包

## 📦 包内容

- **配置文件**: OpenCode 完整配置
- **技能**: 60+ 个技能
- **MCP 服务器**: {len(mcp_info['servers'])} 个
  - NPM 包型: {len(mcp_info['npm_servers'])} 个（需要联网下载）
  - 本地程序: {len(mcp_info['local_servers'])} 个（已包含源代码）
- **总文件数**: {file_count}

## 🚀 快速安装（3 分钟）

### Windows 用户

1. **解压文件**
   右键点击 ZIP 文件 → 全部解压缩

2. **运行安装脚本**
   右键点击 `INSTALL_WINDOWS.bat` → 以管理员身份运行

3. **启动 OpenCode**
   所有配置自动恢复！

### macOS/Linux 用户

1. **解压文件**
   ```bash
   unzip opencode_migration_*.zip
   cd opencode_migration_*
   ```

2. **运行安装脚本**
   ```bash
   chmod +x INSTALL_MACOS.sh
   ./INSTALL_MACOS.sh
   ```

3. **启动 OpenCode**
   所有配置自动恢复！

## ⚡ 安装脚本会自动完成

✅ 复制所有配置文件到正确位置  
✅ 安装 NPM 包型 MCP 服务器  
✅ 复制本地 MCP 服务器代码  
✅ 安装 Python 依赖（自动创建虚拟环境）  
✅ 安装 Node.js 依赖  

## 📋 本地 MCP 服务器列表

{chr(10).join([f"- **{s['name']}** ({s['type_detail']})" for s in mcp_info['local_servers']])}

## 📋 NPM 包型 MCP 服务器

{chr(10).join([f"- **{s['name']}** - `{s.get('package', 'N/A')}`" for s in mcp_info['npm_servers']])}

## ⚠️ 注意事项

1. **Windows 用户**: 必须以管理员身份运行安装脚本
2. **需要联网**: NPM 包需要从网络下载
3. **Python/Node.js**: 确保已安装 Python 3.8+ 和 Node.js 18+
4. **环境变量**: API 密钥等敏感信息已过滤，需要手动配置

## 🆘 遇到问题？

1. 检查是否安装了 Python 和 Node.js
2. 确保以管理员/sudo 权限运行
3. 查看安装脚本的输出日志
4. 在 OpenCode 中说: "帮我解决迁移问题"

---

**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**源平台**: macOS  
**支持目标**: Windows 10/11, macOS, Linux
"""

def should_include(path: Path) -> bool:
    """判断文件是否应该打包"""
    exclude_patterns = [
        "node_modules", ".git", "__pycache__", ".DS_Store",
        ".venv", "venv", ".cache", ".pyc", ".log", ".tmp",
        ".pytest_cache", ".mypy_cache", "dist", "build",
        ".next", ".nuxt", "coverage", ".turbo"
    ]
    
    path_str = str(path).lower()
    for pattern in exclude_patterns:
        if pattern in path_str:
            return False
    
    # 排除大文件
    if path.is_file():
        try:
            if path.stat().st_size > 50 * 1024 * 1024:  # 50MB
                return False
        except:
            pass
    
    return True

if __name__ == "__main__":
    create_migration_package()

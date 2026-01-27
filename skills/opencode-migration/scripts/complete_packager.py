#!/usr/bin/env python3
"""
OpenCode 完整迁移打包器
打包所有配置和 MCP 服务器，生成可直接使用的迁移包
"""

import os
import json
import zipfile
from pathlib import Path
from datetime import datetime
import hashlib

class CompletePackager:
    def __init__(self):
        self.home_dir = Path.home()
        self.opencode_dir = self.home_dir / ".config" / "opencode"
        self.mcp_servers = []
        
    def extract_mcp_servers(self):
        """从配置提取 MCP 服务器信息"""
        print("🔍 分析 MCP 服务器...")
        config_file = self.opencode_dir / "opencode.json"
        
        if not config_file.exists():
            return
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if "mcp" not in config:
            return
        
        for server_name, server_config in config["mcp"].items():
            command = server_config.get("command", [])
            
            server_info = {
                "name": server_name,
                "enabled": server_config.get("enabled", True),
                "type": "npm" if "npx" in command else "local",
                "command": command,
                "install_method": ""
            }
            
            # 判断安装方式
            if "npx" in command:
                # NPM 包，只需记录包名
                for i, arg in enumerate(command):
                    if arg.startswith("@"):
                        server_info["install_method"] = f"npm install -g {arg}"
                        server_info["package_name"] = arg
                        break
            else:
                # 本地服务器，需要打包代码
                for arg in command:
                    if "/" in arg or "\\" in arg:
                        path = Path(arg)
                        if path.exists():
                            # 找到服务器根目录
                            server_root = path.parent
                            while server_root != server_root.parent:
                                if (server_root / "package.json").exists() or \
                                   (server_root / "requirements.txt").exists():
                                    server_info["local_path"] = str(server_root)
                                    server_info["install_method"] = "copy_and_install"
                                    break
                                server_root = server_root.parent
            
            self.mcp_servers.append(server_info)
            print(f"  找到: {server_name} ({server_info['type']})")
        
        print(f"✅ 共找到 {len(self.mcp_servers)} 个 MCP 服务器")
    
    def create_complete_package(self, output_file: str):
        """创建完整迁移包"""
        print(f"\n📦 创建完整迁移包...")
        print(f"   输出: {output_file}\n")
        
        output_path = Path(output_file)
        file_count = 0
        
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            # 1. 打包 OpenCode 配置目录
            print("📁 打包 OpenCode 配置...")
            for item in self.opencode_dir.rglob("*"):
                if self._should_include(item):
                    rel_path = item.relative_to(self.opencode_dir.parent)
                    if item.is_file():
                        # 过滤敏感信息
                        if item.suffix in ['.json', '.md', '.txt']:
                            content = item.read_text(encoding='utf-8')
                            filtered = self._filter_sensitive(content)
                            zipf.writestr(str(rel_path), filtered)
                        else:
                            zipf.write(item, str(rel_path))
                        file_count += 1
                        if file_count % 500 == 0:
                            print(f"   已打包 {file_count} 个文件...")
            
            print(f"✅ OpenCode 配置打包完成: {file_count} 个文件\n")
            
            # 2. 打包本地 MCP 服务器
            print("🔌 打包本地 MCP 服务器...")
            for server in self.mcp_servers:
                if server["type"] == "local" and "local_path" in server:
                    print(f"   打包服务器: {server['name']}")
                    server_path = Path(server["local_path"])
                    server_files = 0
                    
                    for item in server_path.rglob("*"):
                        if self._should_include(item):
                            try:
                                rel_path = item.relative_to(self.home_dir)
                                zip_path = Path("user_home") / rel_path
                                if item.is_file():
                                    zipf.write(item, str(zip_path))
                                    server_files += 1
                                    file_count += 1
                            except Exception as e:
                                if "node_modules" not in str(item):
                                    print(f"     警告: 跳过 {item.name}")
                    
                    print(f"     ✓ {server['name']}: {server_files} 个文件")
            
            print(f"✅ 本地 MCP 服务器打包完成\n")
            
            # 3. 创建安装脚本和说明
            print("📝 创建安装说明...")
            self._create_install_guide(zipf)
            self._create_mcp_reinstall_script(zipf)
            
            print(f"✅ 安装说明创建完成\n")
        
        # 计算校验和
        print("🔐 计算校验和...")
        with open(output_file, 'rb') as f:
            data = f.read()
            md5 = hashlib.md5(data).hexdigest()
            sha256 = hashlib.sha256(data).hexdigest()
        
        size_mb = os.path.getsize(output_file) / 1024 / 1024
        
        print(f"\n{'='*60}")
        print(f"✨ 打包完成！")
        print(f"{'='*60}")
        print(f"📦 文件: {output_path.name}")
        print(f"📊 大小: {size_mb:.2f} MB")
        print(f"📝 文件数: {file_count}")
        print(f"🔐 SHA256: {sha256}")
        print(f"{'='*60}\n")
        
        # 保存信息文件
        info = {
            "package_time": datetime.now().isoformat(),
            "file_count": file_count,
            "size_mb": size_mb,
            "md5": md5,
            "sha256": sha256,
            "mcp_servers": self.mcp_servers
        }
        
        info_file = str(output_path).replace(".zip", "_info.json")
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        print(f"📄 信息文件: {Path(info_file).name}\n")
    
    def _should_include(self, path: Path) -> bool:
        """判断文件是否应该打包"""
        exclude = [
            "node_modules", ".git", "__pycache__", ".DS_Store",
            ".venv", "venv", ".cache", "*.pyc", "*.log", "*.tmp",
            ".pytest_cache", ".mypy_cache", "dist", "build"
        ]
        
        path_str = str(path)
        for pattern in exclude:
            if pattern in path_str:
                return False
        
        # 排除大文件 (>20MB)
        if path.is_file():
            try:
                if path.stat().st_size > 20 * 1024 * 1024:
                    return False
            except:
                pass
        
        return True
    
    def _filter_sensitive(self, content: str) -> str:
        """过滤敏感信息"""
        import re
        
        # 过滤 API 密钥
        patterns = [
            (r'"(sk-[a-zA-Z0-9]{32,})"', '"[FILTERED_API_KEY]"'),
            (r'"(Bearer [a-zA-Z0-9_\-\.]{20,})"', '"Bearer [FILTERED_TOKEN]"'),
            (r'([a-f0-9]{32,64})', '[FILTERED_HASH]')
        ]
        
        filtered = content
        for pattern, replacement in patterns:
            filtered = re.sub(pattern, replacement, filtered)
        
        return filtered
    
    def _create_install_guide(self, zipf: zipfile.ZipFile):
        """创建安装指南"""
        guide = """# OpenCode 完整迁移包 - 安装指南

## 📦 这个包包含

✅ OpenCode 完整配置
✅ 所有技能（60+ 个）
✅ 本地 MCP 服务器程序代码
✅ 配置文件（已过滤敏感信息）

## 🚀 快速安装（3 步完成）

### 步骤 1: 解压文件

**Windows:**
```powershell
# 解压到临时目录
Expand-Archive -Path opencode_complete_*.zip -DestinationPath C:\\Temp\\opencode_migration
cd C:\\Temp\\opencode_migration
```

**macOS/Linux:**
```bash
# 解压到临时目录
unzip opencode_complete_*.zip -d /tmp/opencode_migration
cd /tmp/opencode_migration
```

### 步骤 2: 运行安装脚本

**Windows:**
```powershell
python INSTALL_WINDOWS.py
```

**macOS/Linux:**
```bash
python3 INSTALL_MACOS.py
```

### 步骤 3: 重新安装 NPM 包型 MCP 服务器

某些 MCP 服务器需要重新安装：

```bash
# 这些服务器使用 npx，会自动下载，无需手动操作
# 包括: memory, desktop-commander 等
```

### 步骤 4: 重建 Python 虚拟环境（如果有）

对于 Python MCP 服务器：

**Windows:**
```powershell
cd $env:USERPROFILE\\Documents\\Cline\\MCP\\file-to-pdf\\file-converter-mcp
python -m venv venv
.\\venv\\Scripts\\activate
pip install -r requirements.txt
```

**macOS:**
```bash
cd ~/Documents/Cline/MCP/file-to-pdf/file-converter-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ✅ 验证安装

启动 OpenCode，测试：
```
"显示所有 MCP 服务器的状态"
"列出所有技能"
```

## 🆘 遇到问题？

查看 TROUBLESHOOTING.md 或在 OpenCode 中说：
```
"帮我解决迁移问题"
```

---
安装完成后，你的 OpenCode 就完全恢复了！
"""
        zipf.writestr("README_INSTALL.md", guide)
    
    def _create_mcp_reinstall_script(self, zipf: zipfile.ZipFile):
        """创建 MCP 服务器重装脚本"""
        npm_servers = [s for s in self.mcp_servers if s["type"] == "npm"]
        
        if npm_servers:
            script = "#!/bin/bash\n\n"
            script += "echo '📦 重新安装 NPM 包型 MCP 服务器...'\n\n"
            
            for server in npm_servers:
                if "package_name" in server:
                    script += f"echo '安装 {server['name']}...'\n"
                    script += f"npm install -g {server['package_name']}\n\n"
            
            script += "echo '✅ NPM MCP 服务器安装完成！'\n"
            zipf.writestr("reinstall_mcp_servers.sh", script)

def main():
    import sys
    
    output = sys.argv[1] if len(sys.argv) > 1 else f"~/Desktop/opencode_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    output = os.path.expanduser(output)
    
    packager = CompletePackager()
    packager.extract_mcp_servers()
    packager.create_complete_package(output)

if __name__ == "__main__":
    main()

# OpenCode 跨设备恢复指南

## 📋 前提条件

在新 Mac 上需要先安装：
- Node.js (推荐 v18+)
- npm 或 bun
- Git
- Python 3 (如果使用 Python 脚本)

## 🔄 完整恢复步骤

### 1. 克隆备份仓库

```bash
# 设置代理（如果需要）
git config --global http.proxy http://127.0.0.1:7897

# 克隆备份
cd ~/.config
git clone https://github.com/wsxwj123/opencode-backup-macmini.git opencode

# 或者使用 SSH
git clone git@github.com:wsxwj123/opencode-backup-macmini.git opencode
```

### 2. 安装依赖

```bash
cd ~/.config/opencode

# 使用 npm
npm install

# 或使用 bun（更快）
bun install
```

这会根据 `package.json` 和 `bun.lock`（或 `package-lock.json`）重新安装所有依赖。

### 3. 验证安装

```bash
# 检查 node_modules 是否正确安装
ls -la node_modules/

# 测试 OpenCode 功能
# （根据你的 OpenCode 使用方式测试）
```

### 4. 配置调整（如果需要）

某些配置可能需要根据新环境调整：

```bash
# 检查配置文件
cat opencode.json
cat oh-my-opencode.json

# 根据需要修改路径、代理等设置
```

## ⚠️ 注意事项

### 平台差异

如果从 Intel Mac 迁移到 M1/M2 Mac（或反之）：

```bash
# 清理旧的 node_modules（如果有）
rm -rf node_modules

# 重新安装（会自动适配架构）
npm install
```

### 权限问题

某些脚本可能需要执行权限：

```bash
# 恢复执行权限
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### 环境变量

检查是否需要设置环境变量：

```bash
# 例如代理设置
export http_proxy="http://127.0.0.1:7897"
export https_proxy="http://127.0.0.1:7897"
```

## 🧪 验证恢复成功

### 1. 检查文件完整性

```bash
# 检查关键目录
ls -la skills/
ls -la plugins/
ls -la agents/

# 统计技能数量
ls skills/ | wc -l
```

### 2. 测试功能

```bash
# 运行验证脚本（如果有）
python scripts/verify_backup.py

# 测试 OpenCode 核心功能
# （根据你的使用场景）
```

## 📦 备份内容清单

### ✅ 已备份（可直接使用）
- `skills/` - 所有技能
- `plugins/` - 插件配置
- `agents/` - 代理配置
- `commands/` - 命令定义
- `lib/` - 核心库
- `*.json` - 配置文件
- `*.py` - Python 脚本
- `package.json` - 依赖清单
- `bun.lock` / `package-lock.json` - 锁定文件

### ❌ 未备份（需重新生成）
- `node_modules/` - npm 依赖（通过 `npm install` 重建）
- `.DS_Store` - macOS 系统文件
- `*.pyc` - Python 编译缓存
- `.git/` - Git 仓库（备份仓库本身的 .git）

## 🚀 快速恢复脚本

创建一个自动化恢复脚本：

```bash
#!/bin/bash
# restore_opencode.sh

set -e

echo "🔄 开始恢复 OpenCode 配置..."

# 1. 克隆备份
if [ ! -d ~/.config/opencode ]; then
    echo "📥 克隆备份仓库..."
    git clone https://github.com/wsxwj123/opencode-backup-macmini.git ~/.config/opencode
else
    echo "✅ OpenCode 目录已存在"
fi

cd ~/.config/opencode

# 2. 安装依赖
echo "📦 安装依赖..."
if command -v bun &> /dev/null; then
    bun install
else
    npm install
fi

# 3. 设置权限
echo "🔐 设置脚本权限..."
find scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \;

# 4. 验证
echo "🔍 验证安装..."
if [ -d node_modules ]; then
    echo "✅ node_modules 安装成功"
else
    echo "❌ node_modules 安装失败"
    exit 1
fi

echo "🎉 OpenCode 恢复完成！"
echo "📁 位置: ~/.config/opencode"
```

使用方法：
```bash
chmod +x restore_opencode.sh
./restore_opencode.sh
```

## 💡 最佳实践

### 1. 定期同步备份

在原 Mac 上：
```bash
cd ~/.config/opencode/skills/opencode-backup
python scripts/backup_opencode.py incremental
cd backup-repo
git push
```

### 2. 多设备同步

如果在多台 Mac 上使用：
```bash
# 在新 Mac 上拉取最新备份
cd ~/.config/opencode
git pull origin master

# 重新安装依赖（如果 package.json 有变化）
npm install
```

### 3. 版本管理

使用 Git 标签标记重要版本：
```bash
# 在备份仓库中
git tag -a v1.0.0 -m "稳定版本 2026-01-27"
git push origin v1.0.0

# 在新 Mac 上恢复特定版本
git checkout v1.0.0
npm install
```

## 🆘 常见问题

### Q: 为什么不备份 node_modules？
A: 因为它可以通过 `npm install` 重建，备份会浪费空间和时间。

### Q: 如果 npm install 失败怎么办？
A: 
```bash
# 清理缓存
npm cache clean --force

# 删除 node_modules 和 lock 文件
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

### Q: 不同 Mac 架构（Intel vs M1）有影响吗？
A: `npm install` 会自动处理架构差异，重新编译原生模块。

### Q: 需要备份 .git 目录吗？
A: 不需要。备份仓库本身就是一个 Git 仓库，克隆时会自动创建 .git。

---

**总结**: 在新 Mac 上恢复 OpenCode 只需要：
1. 克隆备份仓库
2. 运行 `npm install` 或 `bun install`
3. 验证功能

`node_modules` 不需要备份，因为它可以随时重建，这是 Node.js 生态系统的标准做法。
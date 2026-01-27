#!/bin/bash
# OpenCode 自动恢复脚本
# 用于在新 Mac 上快速恢复 OpenCode 配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
BACKUP_REPO="https://github.com/wsxwj123/opencode-backup-macmini.git"
OPENCODE_DIR="$HOME/.config/opencode"
PROXY="http://127.0.0.1:7897"

echo "============================================"
echo "  OpenCode 自动恢复脚本"
echo "============================================"
echo ""

# 检查是否需要代理
read -p "是否需要设置 Git 代理？(y/n): " use_proxy
if [ "$use_proxy" = "y" ]; then
    echo -e "${YELLOW}设置 Git 代理: $PROXY${NC}"
    git config --global http.proxy "$PROXY"
    git config --global https.proxy "$PROXY"
    export http_proxy="$PROXY"
    export https_proxy="$PROXY"
fi

# 1. 克隆备份仓库
if [ -d "$OPENCODE_DIR" ]; then
    echo -e "${YELLOW}⚠️  OpenCode 目录已存在: $OPENCODE_DIR${NC}"
    read -p "是否覆盖？(y/n): " overwrite
    if [ "$overwrite" = "y" ]; then
        echo -e "${YELLOW}备份现有目录...${NC}"
        mv "$OPENCODE_DIR" "${OPENCODE_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    else
        echo -e "${RED}❌ 恢复已取消${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}📥 克隆备份仓库...${NC}"
git clone "$BACKUP_REPO" "$OPENCODE_DIR"

cd "$OPENCODE_DIR"

# 2. 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Node.js${NC}"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}✅ Node.js 版本: $(node --version)${NC}"

# 3. 安装依赖
echo -e "${GREEN}📦 安装依赖...${NC}"

if command -v bun &> /dev/null; then
    echo "使用 bun 安装依赖..."
    bun install
elif command -v npm &> /dev/null; then
    echo "使用 npm 安装依赖..."
    npm install
else
    echo -e "${RED}❌ 未检测到 npm 或 bun${NC}"
    exit 1
fi

# 4. 设置脚本权限
echo -e "${GREEN}🔐 设置脚本权限...${NC}"
find scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \; 2>/dev/null || true

# 5. 验证安装
echo -e "${GREEN}🔍 验证安装...${NC}"

if [ ! -d "node_modules" ]; then
    echo -e "${RED}❌ node_modules 安装失败${NC}"
    exit 1
fi

if [ ! -d "skills" ]; then
    echo -e "${RED}❌ skills 目录不存在${NC}"
    exit 1
fi

# 统计技能数量
skill_count=$(ls -1 skills | wc -l | tr -d ' ')
echo -e "${GREEN}✅ 检测到 $skill_count 个技能${NC}"

# 6. 清理（如果使用了代理）
if [ "$use_proxy" = "y" ]; then
    read -p "是否清除 Git 代理设置？(y/n): " clear_proxy
    if [ "$clear_proxy" = "y" ]; then
        git config --global --unset http.proxy
        git config --global --unset https.proxy
        echo -e "${GREEN}✅ 已清除 Git 代理设置${NC}"
    fi
fi

echo ""
echo "============================================"
echo -e "${GREEN}🎉 OpenCode 恢复完成！${NC}"
echo "============================================"
echo ""
echo "📁 安装位置: $OPENCODE_DIR"
echo "📊 技能数量: $skill_count"
echo "📦 依赖包: node_modules/"
echo ""
echo "💡 下一步:"
echo "  1. 检查配置文件: cat $OPENCODE_DIR/opencode.json"
echo "  2. 测试 OpenCode 功能"
echo "  3. 根据需要调整配置"
echo ""
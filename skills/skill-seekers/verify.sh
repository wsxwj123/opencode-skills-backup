#!/bin/bash

# Skill Seekers 验证脚本
# 用于验证 skill 是否正确安装和配置

set -e

echo "======================================"
echo "Skill Seekers 验证工具"
echo "======================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. 检查 Python 版本
echo "1. 检查 Python 版本..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
        success "Python $PYTHON_VERSION (>= 3.10)"
    else
        error "Python $PYTHON_VERSION (需要 >= 3.10)"
        exit 1
    fi
else
    error "未找到 Python 3"
    exit 1
fi

# 2. 检查 skill-seekers 安装
echo ""
echo "2. 检查 skill-seekers 安装..."
if command -v skill-seekers &> /dev/null; then
    success "skill-seekers 已安装"
    VERSION=$(skill-seekers --version 2>&1 | head -1 || echo "未知")
    echo "   版本: $VERSION"
else
    error "skill-seekers 未安装"
    echo "   安装命令: pip3 install skill-seekers"
    exit 1
fi

if command -v skill-seekers-codebase &> /dev/null; then
    success "skill-seekers-codebase 已安装"
else
    warning "skill-seekers-codebase 未安装或不在 PATH 中"
fi

# 3. 检查 OpenCode skill 目录
echo ""
echo "3. 检查 OpenCode Skill 目录..."
SKILL_DIR="$HOME/.config/opencode/skills/skill-seekers"
if [ -d "$SKILL_DIR" ]; then
    success "Skill 目录存在: $SKILL_DIR"
    
    # 检查关键文件
    if [ -f "$SKILL_DIR/SKILL.md" ]; then
        success "SKILL.md 存在"
    else
        error "SKILL.md 不存在"
    fi
    
    if [ -f "$SKILL_DIR/skill.yaml" ]; then
        success "skill.yaml 存在"
    else
        warning "skill.yaml 不存在(可选)"
    fi
    
    if [ -f "$SKILL_DIR/USAGE.md" ]; then
        success "USAGE.md 存在"
    else
        warning "USAGE.md 不存在(可选)"
    fi
else
    error "Skill 目录不存在: $SKILL_DIR"
fi

# 4. 检查环境变量
echo ""
echo "4. 检查环境变量(可选)..."
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    success "ANTHROPIC_API_KEY 已设置"
else
    warning "ANTHROPIC_API_KEY 未设置(API 增强需要)"
fi

if [ ! -z "$GITHUB_TOKEN" ]; then
    success "GITHUB_TOKEN 已设置"
else
    warning "GITHUB_TOKEN 未设置(推荐设置以避免速率限制)"
fi

if [ ! -z "$GOOGLE_API_KEY" ]; then
    success "GOOGLE_API_KEY 已设置"
else
    warning "GOOGLE_API_KEY 未设置(Gemini 平台需要)"
fi

if [ ! -z "$OPENAI_API_KEY" ]; then
    success "OPENAI_API_KEY 已设置"
else
    warning "OPENAI_API_KEY 未设置(OpenAI 平台需要)"
fi

# 5. 测试基础命令
echo ""
echo "5. 测试基础命令..."

# 测试 config 命令
if skill-seekers config --show &> /dev/null; then
    success "config --show 正常"
else
    warning "config --show 可能需要初始化"
fi

# 6. 检查输出目录
echo ""
echo "6. 检查输出目录..."
if [ -d "$HOME/.config/skill-seekers" ]; then
    success "配置目录存在: ~/.config/skill-seekers"
else
    warning "配置目录不存在(首次运行时会创建)"
fi

# 7. 总结
echo ""
echo "======================================"
echo "验证总结"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# 统计错误和警告
if ! command -v skill-seekers &> /dev/null; then
    ERRORS=$((ERRORS + 1))
fi

if [ ! -d "$SKILL_DIR" ]; then
    ERRORS=$((ERRORS + 1))
fi

if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$GITHUB_TOKEN" ]; then
    WARNINGS=$((WARNINGS + 1))
fi

echo "错误: $ERRORS"
echo "警告: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    success "所有关键检查通过!"
    echo ""
    echo "🎉 Skill Seekers 已正确安装和配置!"
    echo ""
    echo "下一步:"
    echo "  1. 在 OpenCode 中打开项目"
    echo "  2. 告诉 AI: \"使用 skill-seekers 分析当前项目\""
    echo "  3. 或运行: skill-seekers-codebase --directory . --output output/test/"
    echo ""
else
    error "发现 $ERRORS 个错误,请修复后重试"
    exit 1
fi

# 8. 快速测试示例
echo "======================================"
echo "快速测试示例"
echo "======================================"
echo ""
echo "你可以运行以下命令测试:"
echo ""
echo "1. 分析本地项目:"
echo "   skill-seekers-codebase --directory . --output output/test/ --depth surface"
echo ""
echo "2. 评估文档页数:"
echo "   skill-seekers estimate --url https://react.dev"
echo ""
echo "3. 配置 GitHub token:"
echo "   skill-seekers config --github"
echo ""
echo "4. 查看配置:"
echo "   skill-seekers config --show"
echo ""
echo "5. 在 OpenCode 中使用:"
echo "   打开 OpenCode,告诉 AI: \"用 skill-seekers 为当前项目生成 skill\""
echo ""

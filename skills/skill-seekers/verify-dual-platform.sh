#!/usr/bin/env bash
set -euo pipefail

# verify-dual-platform.sh - 验证双平台 skill 完整性

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✓${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <skill目录>"
  echo "示例: $0 ~/.config/opencode/skills/my-skill"
  exit 1
fi

SKILL_DIR="$1"
SKILL_NAME=$(basename "$SKILL_DIR")

echo "验证 skill: $SKILL_NAME"
echo "目录: $SKILL_DIR"
echo ""

ERRORS=0
WARNINGS=0

# 检查目录存在
if [[ ! -d "$SKILL_DIR" ]]; then
  error "目录不存在"
  exit 1
fi

# 检查必需文件
echo "检查必需文件..."
if [[ -f "$SKILL_DIR/SKILL.md" ]]; then
  success "SKILL.md"
else
  error "缺少 SKILL.md"
  ((ERRORS++))
fi

if [[ -f "$SKILL_DIR/.opencode-skill" ]]; then
  success ".opencode-skill"
else
  warn "缺少 .opencode-skill"
  ((WARNINGS++))
fi

if [[ -f "$SKILL_DIR/.claude-skill" ]]; then
  success ".claude-skill"
else
  warn "缺少 .claude-skill"
  ((WARNINGS++))
fi

if [[ -f "$SKILL_DIR/.skillrc" ]]; then
  success ".skillrc"
else
  warn "缺少 .skillrc"
  ((WARNINGS++))
fi

# 检查元数据格式
echo ""
echo "检查元数据格式..."

if [[ -f "$SKILL_DIR/.opencode-skill" ]]; then
  if grep -q "name:" "$SKILL_DIR/.opencode-skill"; then
    success ".opencode-skill 格式正确"
  else
    error ".opencode-skill 格式错误"
    ((ERRORS++))
  fi
fi

if [[ -f "$SKILL_DIR/.claude-skill" ]]; then
  if python3 -m json.tool "$SKILL_DIR/.claude-skill" >/dev/null 2>&1; then
    success ".claude-skill JSON 格式正确"
  else
    error ".claude-skill JSON 格式错误"
    ((ERRORS++))
  fi
fi

# 检查内容目录
echo ""
echo "检查内容结构..."

if [[ -d "$SKILL_DIR/references" ]]; then
  success "包含 references/ 目录"
else
  warn "缺少 references/ 目录"
  ((WARNINGS++))
fi

if [[ -d "$SKILL_DIR/examples" ]]; then
  success "包含 examples/ 目录"
else
  warn "缺少 examples/ 目录"
  ((WARNINGS++))
fi

# 统计
echo ""
echo "========================================="
echo "验证结果"
echo "========================================="
echo "错误: $ERRORS"
echo "警告: $WARNINGS"
echo ""

if [[ $ERRORS -eq 0 ]]; then
  success "验证通过！Skill 可以正常使用"
  exit 0
else
  error "发现 $ERRORS 个错误，请修复"
  exit 1
fi

#!/bin/bash
# OpenCode 迁移技能打包脚本

set -e

echo "📦 打包 OpenCode 迁移技能..."

# 检查目录结构
if [ ! -f "SKILL.md" ]; then
    echo "❌ 错误: 找不到 SKILL.md 文件"
    exit 1
fi

if [ ! -d "scripts" ]; then
    echo "❌ 错误: 找不到 scripts 目录"
    exit 1
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
SKILL_NAME="opencode-migration"
PACKAGE_FILE="${SKILL_NAME}.skill"

echo "📁 创建技能包结构..."

# 复制文件
cp -r SKILL.md scripts references assets "$TEMP_DIR/"

# 创建技能包
cd "$TEMP_DIR"
zip -r "$PACKAGE_FILE" ./* > /dev/null

# 移动回原目录
cd - > /dev/null
mv "$TEMP_DIR/$PACKAGE_FILE" .

# 清理
rm -rf "$TEMP_DIR"

# 计算校验和
echo "🔐 计算校验和..."
MD5_SUM=$(md5sum "$PACKAGE_FILE" | cut -d' ' -f1)
SHA256_SUM=$(sha256sum "$PACKAGE_FILE" | cut -d' ' -f1)
FILE_SIZE=$(du -h "$PACKAGE_FILE" | cut -f1)

echo ""
echo "🎉 技能打包完成!"
echo "   技能包: $PACKAGE_FILE"
echo "   文件大小: $FILE_SIZE"
echo "   MD5: $MD5_SUM"
echo "   SHA256: $SHA256_SUM"
echo ""
echo "📋 包含内容:"
echo "   - SKILL.md (主技能文件)"
echo "   - scripts/ (4个Python脚本)"
echo "   - references/ (4个参考文档)"
echo "   - assets/ (检查清单和示例配置)"
echo ""
echo "🚀 使用方式:"
echo "   1. 将 $PACKAGE_FILE 复制到目标设备的技能目录"
echo "   2. 在 OpenCode 中加载技能"
echo "   3. 使用命令: '请帮我迁移 OpenCode 到新电脑'"
echo ""
echo "💡 技能功能:"
echo "   • 一键分析 OpenCode 配置"
echo "   • 智能打包配置和文件"
echo "   • 跨平台兼容性处理"
echo "   • 自动安装和验证"
#!/bin/bash
# ========================================
# AI 自治开发系统 - 环境初始化脚本
# 每次 AI 启动时首先执行此脚本
# ========================================

set -e

# 定位项目根目录（init.sh 放在项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

AUTONOMY_DIR=".autonomy"

echo "🔧 [init] AI 自治开发系统启动中..."

# 1. 加载环境变量
if [ -f "$AUTONOMY_DIR/config/.env" ]; then
    echo "📦 [init] 加载 .env 环境变量..."
    set -a
    source "$AUTONOMY_DIR/config/.env"
    set +a
else
    echo "⚠️  [init] 未找到 .autonomy/config/.env，请先配置 API Key"
fi

# 2. 检查 Python 环境
echo "🐍 [init] 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    echo "   Python3: $(python3 --version)"
else
    echo "❌ [init] 未找到 python3，请先安装"
    exit 1
fi

# 3. 安装 Python 依赖
if [ -f "$AUTONOMY_DIR/requirements.txt" ]; then
    echo "📦 [init] 安装 Python 依赖..."
    pip3 install -q -r "$AUTONOMY_DIR/requirements.txt"
fi

# 4. 检查 Git 状态
echo "📋 [init] Git 状态:"
git status --short 2>/dev/null || echo "   (非 Git 仓库)"

# 5. 检查核心文件
echo "📂 [init] 检查核心文件..."
for f in feature_list.json progress.txt CLAUDE.md; do
    if [ -f "$f" ]; then
        echo "   ✅ $f"
    else
        echo "   ❌ $f 缺失!"
    fi
done

# 6. 显示当前模型配置
if command -v python3 &> /dev/null && [ -f "$AUTONOMY_DIR/config/providers.json" ]; then
    echo "🤖 [init] 当前活跃模型:"
    python3 -c "
import json
with open('$AUTONOMY_DIR/config/providers.json') as f:
    cfg = json.load(f)
active = cfg['active_provider']
p = cfg['providers'][active]
print(f\"   {p['name']} ({p['model']})\")
"
fi

echo ""
echo "✅ [init] 环境初始化完成！"
echo "========================================="
echo "  下一步：读取 feature_list.json 获取任务"
echo "========================================="

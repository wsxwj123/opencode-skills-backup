#!/bin/bash

# Skill Seekers 功能测试脚本
# 快速测试各个核心功能是否正常工作

set -e

echo "======================================"
echo "Skill Seekers 功能测试"
echo "======================================"
echo ""

# 创建临时测试目录
TEST_DIR="/tmp/skill-seekers-test-$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "测试目录: $TEST_DIR"
echo ""

# 测试计数器
PASSED=0
FAILED=0
SKIPPED=0

test_command() {
    local name="$1"
    local cmd="$2"
    local expect_fail="${3:-false}"
    
    echo "测试: $name"
    echo "命令: $cmd"
    
    if eval "$cmd" &> "$TEST_DIR/test.log"; then
        if [ "$expect_fail" = "true" ]; then
            echo "❌ 失败: 命令应该失败但成功了"
            FAILED=$((FAILED + 1))
        else
            echo "✅ 通过"
            PASSED=$((PASSED + 1))
        fi
    else
        if [ "$expect_fail" = "true" ]; then
            echo "✅ 通过(预期失败)"
            PASSED=$((PASSED + 1))
        else
            echo "❌ 失败"
            echo "错误信息:"
            tail -5 "$TEST_DIR/test.log"
            FAILED=$((FAILED + 1))
        fi
    fi
    echo ""
}

# 1. 基础命令测试
echo "======================================"
echo "1. 基础命令测试"
echo "======================================"
echo ""

test_command "版本信息" "skill-seekers --version"
test_command "帮助信息" "skill-seekers --help"
test_command "配置显示" "skill-seekers config --show"

# 2. 评估功能测试
echo "======================================"
echo "2. 评估功能测试"
echo "======================================"
echo ""

# 创建简单的测试配置
cat > test-config.json << 'EOF'
{
  "name": "test",
  "description": "Test configuration",
  "base_url": "https://example.com/",
  "start_urls": ["https://example.com/"],
  "url_patterns": ["https://example.com/**"],
  "max_pages": 10
}
EOF

test_command "配置验证" "skill-seekers validate test-config.json"

# 3. 本地代码分析测试(使用当前目录)
echo "======================================"
echo "3. 本地代码分析测试"
echo "======================================"
echo ""

# 创建简单的测试项目
mkdir -p test-project
cat > test-project/main.py << 'EOF'
def hello(name):
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))
EOF

cat > test-project/README.md << 'EOF'
# Test Project

A simple test project.
EOF

echo "测试: 分析本地项目(surface 深度)"
if skill-seekers-codebase \
    --directory test-project \
    --depth surface \
    --output output/test-project \
    --ai-mode none \
    &> "$TEST_DIR/test.log"; then
    echo "✅ 通过"
    PASSED=$((PASSED + 1))
    
    # 检查输出文件
    if [ -f "output/test-project/SKILL.md" ]; then
        echo "✅ SKILL.md 已生成"
        PASSED=$((PASSED + 1))
    else
        echo "❌ SKILL.md 未生成"
        FAILED=$((FAILED + 1))
    fi
else
    echo "❌ 失败"
    tail -10 "$TEST_DIR/test.log"
    FAILED=$((FAILED + 1))
fi
echo ""

# 4. 打包测试
echo "======================================"
echo "4. 打包测试"
echo "======================================"
echo ""

if [ -d "output/test-project" ]; then
    echo "测试: 打包生成的 skill"
    if yes | skill-seekers package output/test-project/ --no-open &> "$TEST_DIR/test.log"; then
        echo "✅ 通过"
        PASSED=$((PASSED + 1))
        
        # 检查 zip 文件
        if [ -f "output/test-project.zip" ]; then
            echo "✅ ZIP 文件已生成"
            PASSED=$((PASSED + 1))
        else
            echo "❌ ZIP 文件未生成"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "❌ 失败"
        tail -10 "$TEST_DIR/test.log"
        FAILED=$((FAILED + 1))
    fi
else
    echo "⏭️  跳过(没有可打包的 skill)"
    SKIPPED=$((SKIPPED + 1))
fi
echo ""

# 5. 配置管理测试
echo "======================================"
echo "5. 配置管理测试"
echo "======================================"
echo ""

test_command "列出配置源" "skill-seekers config --show"

# 6. 清理
echo "======================================"
echo "清理测试文件"
echo "======================================"
echo ""

cd /
rm -rf "$TEST_DIR"
echo "✅ 测试目录已清理"
echo ""

# 总结
echo "======================================"
echo "测试总结"
echo "======================================"
echo ""
echo "通过: $PASSED"
echo "失败: $FAILED"
echo "跳过: $SKIPPED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 所有测试通过!"
    exit 0
else
    echo "❌ 有 $FAILED 个测试失败"
    exit 1
fi

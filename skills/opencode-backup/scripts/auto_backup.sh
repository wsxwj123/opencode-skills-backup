#!/bin/bash
# OpenCode 自动备份脚本

set -e

# 配置
BACKUP_DIR="/Users/wsxwj/.config/opencode/skills/opencode-backup"
LOG_DIR="$BACKUP_DIR/logs"
LOG_FILE="$LOG_DIR/backup_$(date +%Y%m%d_%H%M%S).log"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 设置代理
export http_proxy="http://127.0.0.1:7897"
export https_proxy="http://127.0.0.1:7897"

echo "=== OpenCode 自动备份开始 $(date) ===" | tee -a "$LOG_FILE"

# 切换到备份目录
cd "$BACKUP_DIR"

# 执行增量备份
echo "执行增量备份..." | tee -a "$LOG_FILE"
if python scripts/backup_opencode.py incremental 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 增量备份成功" | tee -a "$LOG_FILE"
    
    # 检查是否有变更
    if grep -q "检测到.*个文件变更" "$LOG_FILE" || grep -q "没有检测到变更" "$LOG_FILE"; then
        echo "备份状态检查完成" | tee -a "$LOG_FILE"
    else
        echo "⚠️  备份状态检查异常" | tee -a "$LOG_FILE"
    fi
else
    echo "❌ 增量备份失败" | tee -a "$LOG_FILE"
    exit 1
fi

# 每周日执行完整备份
if [ "$(date +%u)" = "7" ]; then
    echo "今天是周日，执行完整备份..." | tee -a "$LOG_FILE"
    if python scripts/backup_opencode.py backup 2>&1 | tee -a "$LOG_FILE"; then
        echo "✅ 完整备份成功" | tee -a "$LOG_FILE"
    else
        echo "❌ 完整备份失败" | tee -a "$LOG_FILE"
    fi
fi

echo "=== OpenCode 自动备份结束 $(date) ===" | tee -a "$LOG_FILE"

# 清理旧日志（保留最近30天）
find "$LOG_DIR" -name "backup_*.log" -mtime +30 -delete 2>/dev/null || true

echo "✅ 自动备份任务完成"
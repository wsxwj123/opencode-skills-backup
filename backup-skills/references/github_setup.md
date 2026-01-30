# GitHub 仓库设置指南

## 1. 创建 GitHub 仓库

### 1.1 登录 GitHub
1. 访问 [GitHub](https://github.com)
2. 使用您的账号登录

### 1.2 创建新仓库
1. 点击右上角的 "+" 图标
2. 选择 "New repository"
3. 填写仓库信息：
   - **Repository name**: `opencode-skills-backup`（建议名称）
   - **Description**: `Backup for OpenCode skills`
   - **Visibility**: `Private`（推荐）或 `Public`
   - **Initialize with README**: 取消勾选（备份脚本会创建）
   - **Add .gitignore**: 选择 `Python`
   - **Add a license**: 可选

4. 点击 "Create repository"

### 1.3 获取仓库 URL
创建成功后，复制仓库的 HTTPS 或 SSH URL：
- **HTTPS**: `https://github.com/<username>/opencode-skills-backup.git`
- **SSH**: `git@github.com:<username>/opencode-skills-backup.git`

## 2. 配置 Git 认证

### 2.1 HTTPS 认证（推荐）
使用个人访问令牌（PAT）：

1. **生成访问令牌**：
   - 进入 GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - 点击 "Generate new token" → "Generate new token (classic)"
   - 设置权限：
     - `repo`（完全控制仓库）
     - `workflow`（可选）
   - 生成并复制令牌

2. **使用令牌**：
   ```bash
   # 设置远程仓库时使用令牌
   git remote add origin https://<token>@github.com/<username>/opencode-skills-backup.git
   ```

### 2.2 SSH 认证
使用 SSH 密钥：

1. **生成 SSH 密钥**（如果还没有）：
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   ```

2. **添加公钥到 GitHub**：
   - 复制公钥：`cat ~/.ssh/id_ed25519.pub`
   - GitHub Settings → SSH and GPG keys → New SSH key
   - 粘贴公钥并保存

3. **测试连接**：
   ```bash
   ssh -T git@github.com
   ```

## 3. 本地 Git 配置

### 3.1 设置用户信息
```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

### 3.2 配置代理（如果需要）
如果使用代理，配置 Git：
```bash
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

### 3.3 配置凭证存储
```bash
# macOS 钥匙串
git config --global credential.helper osxkeychain

# Windows
git config --global credential.helper wincred

# Linux
git config --global credential.helper cache
```

## 4. 初始化备份仓库

### 4.1 手动初始化
```bash
cd /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo

# 设置远程仓库
git remote add origin <your-repo-url>

# 首次推送
git add .
git commit -m "Initial backup"
git push -u origin main
```

### 4.2 使用备份脚本
备份脚本会自动检测并提示设置远程仓库。

## 5. 验证设置

### 5.1 检查远程仓库
```bash
cd /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo
git remote -v
```

### 5.2 测试推送
```bash
echo "# Test" >> README.md
git add README.md
git commit -m "Test commit"
git push
```

## 6. 故障排除

### 6.1 认证失败
**问题**: `remote: Invalid username or password`

**解决方案**：
1. 检查令牌是否过期
2. 重新生成访问令牌
3. 更新远程仓库 URL：
   ```bash
   git remote set-url origin https://<new-token>@github.com/<username>/opencode-skills-backup.git
   ```

### 6.2 网络连接问题
**问题**: `Failed to connect to github.com`

**解决方案**：
1. 检查代理设置
2. 测试网络连接：
   ```bash
   curl -v https://github.com
   ```
3. 临时关闭代理：
   ```bash
   git config --global --unset http.proxy
   git config --global --unset https.proxy
   ```

### 6.3 权限不足
**问题**: `Permission denied (publickey)`

**解决方案**：
1. 检查 SSH 密钥是否添加到 GitHub
2. 测试 SSH 连接：
   ```bash
   ssh -T git@github.com
   ```
3. 切换到 HTTPS：
   ```bash
   git remote set-url origin https://github.com/<username>/opencode-skills-backup.git
   ```

## 7. 安全建议

### 7.1 保护访问令牌
- 不要将令牌提交到代码中
- 使用环境变量存储令牌
- 定期轮换令牌

### 7.2 仓库权限
- 使用私有仓库保护敏感信息
- 限制仓库访问权限
- 定期审查仓库活动

### 7.3 备份策略
- 定期测试备份恢复
- 保留多个备份版本
- 监控备份状态

## 8. 自动化配置

### 8.1 环境变量
创建 `.env` 文件：
```bash
GITHUB_TOKEN=your_personal_access_token
GITHUB_USERNAME=your_username
GITHUB_REPO=opencode-skills-backup
```

### 8.2 自动化脚本
创建初始化脚本：
```bash
#!/bin/bash
# init_backup.sh

REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git"

cd /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo
git remote add origin $REPO_URL
echo "Remote repository configured"
```

## 9. 监控和维护

### 9.1 检查备份状态
```bash
# 查看最近提交
cd /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo
git log --oneline -5

# 查看文件变更
git status
```

### 9.2 清理旧备份
```bash
# 删除超过30天的备份分支（如果需要）
git branch | grep backup- | xargs git branch -d
```

### 9.3 更新配置
定期检查并更新：
- Git 配置
- 访问令牌
- 备份策略
#!/bin/bash
# 一次性设置：创建 GitHub 仓库并安装每小时自动推送的 macOS 后台任务。
# 用法：bash ~/论文/llm-rl-papers/mac/setup.sh
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NAME="llm-rl-papers"
LABEL="com.llm-rl-papers.autopush"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "== 仓库目录：$REPO_DIR"
command -v git >/dev/null || { echo "未找到 git，请先运行：xcode-select --install"; exit 1; }
if ! command -v gh >/dev/null; then
  if command -v brew >/dev/null; then brew install gh; else echo "未找到 GitHub CLI（gh）。请先安装 Homebrew（https://brew.sh）或从 https://cli.github.com 安装 gh 后重试。"; exit 1; fi
fi
gh auth status >/dev/null 2>&1 || gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git

cd "$REPO_DIR"
[ -d .git ] || git init -b main
git config user.name >/dev/null || git config user.name "$(gh api user --jq .login)"
git config user.email >/dev/null || git config user.email "$(gh api user --jq .id)+$(gh api user --jq .login)@users.noreply.github.com"
git add -A
git diff --cached --quiet || git commit -m "Initial import: LLM + RL paper list"

OWNER="$(gh api user --jq .login)"
if ! git remote get-url origin >/dev/null 2>&1; then
  if gh repo view "$OWNER/$NAME" >/dev/null 2>&1; then
    git remote add origin "https://github.com/$OWNER/$NAME.git"
  else
    gh repo create "$NAME" --private --source=. --remote=origin \
      --description "LLM + Reinforcement Learning papers from top venues (2023-), curated weekly"
  fi
fi
git push -u origin HEAD

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$REPO_DIR/mac/autopush.sh</string></array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/llm-rl-papers-autopush.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/llm-rl-papers-autopush.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "== 完成：https://github.com/$OWNER/$NAME"
echo "   后台任务每小时检查一次本地变更并推送；日志：~/Library/Logs/llm-rl-papers-autopush.log"

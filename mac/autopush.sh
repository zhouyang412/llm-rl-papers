#!/bin/bash
# 由 launchd 每小时调用：若有本地变更则提交并推送。
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
cd "$(dirname "$0")/.." || exit 1
[ -d .git ] || exit 0
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "Weekly update $(date +%F)"
fi
if [ -n "$(git log --oneline @{u}..HEAD 2>/dev/null)" ]; then
  git push -q origin HEAD && echo "$(date '+%F %T') pushed" || echo "$(date '+%F %T') push failed"
fi

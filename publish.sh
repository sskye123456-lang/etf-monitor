#!/bin/bash
# 每日发布：拉数据 -> 生成看板 -> 提交 -> 推送到 GitHub（Pages 自动更新）。
# 建议交易日收盘后运行（如 18:30）。
# crontab 示例（周一至周五 18:30）：
#   30 18 * * 1-5 /Users/ambershao/Workspace/project02/etf-monitor/publish.sh >> /Users/ambershao/Workspace/project02/etf-monitor/data/run.log 2>&1
set -e
cd "$(dirname "$0")"

./.venv/bin/python run.py

# 只在看板有变化时提交推送
if ! git diff --quiet -- docs/index.html; then
  git add docs/index.html
  git commit -m "data: 更新 ETF 资金流看板 $(date +%F)"
  git push origin main
  echo "已推送，GitHub Pages 将在 1~2 分钟后更新。"
else
  echo "看板无变化，跳过推送。"
fi

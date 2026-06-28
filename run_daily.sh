#!/bin/bash
# 每日定时入口。建议交易日收盘后（如 18:30）运行。
# crontab 示例（每周一到周五 18:30）：
#   30 18 * * 1-5 /Users/ambershao/Workspace/project02/etf-monitor/run_daily.sh >> /Users/ambershao/Workspace/project02/etf-monitor/data/run.log 2>&1
cd "$(dirname "$0")" || exit 1
./.venv/bin/python run.py

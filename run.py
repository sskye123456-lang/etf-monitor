# -*- coding: utf-8 -*-
"""一键流程：抓快照 -> 计算 -> 生成看板。"""
import datetime as dt
import fetch
import dashboard

if __name__ == "__main__":
    print(f"===== ETF 监控 {dt.datetime.now():%Y-%m-%d %H:%M} =====")
    fetch.main()          # 拉取并落盘当日快照
    dashboard.main()      # 重算并生成 HTML
    print("完成。本地预览：docs/index.html")

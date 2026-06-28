# -*- coding: utf-8 -*-
"""
拉取全市场 ETF 当日快照（东方财富），保存到 data/snapshots/<交易日>.csv。

每天保存一份，文件名用东财返回的「数据日期」（即交易日），
非交易日重复跑不会覆盖、不会污染历史。
"""
import os
import sys
import datetime as dt

import akshare as ak
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.join(HERE, "data", "snapshots")

# 我们需要保留的字段（其余丢弃，控制文件大小）
KEEP = {
    "代码": "code",
    "名称": "name",
    "最新价": "price",
    "IOPV实时估值": "iopv",
    "涨跌幅": "pct",
    "成交额": "amount",
    "最新份额": "shares",        # 关键：算份额变动
    "流通市值": "float_mv",
    "总市值": "total_mv",
    "主力净流入-净额": "main_inflow",   # Day1 兜底用的盘中资金流
    "数据日期": "data_date",
}


def fetch_snapshot() -> pd.DataFrame:
    """拉取并标准化当日 ETF 快照。"""
    df = ak.fund_etf_spot_em()
    df = df[list(KEEP.keys())].rename(columns=KEEP)
    # 类型清洗
    for col in ["price", "iopv", "pct", "amount", "shares", "float_mv", "total_mv", "main_inflow"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["data_date"] = pd.to_datetime(df["data_date"]).dt.strftime("%Y-%m-%d")
    # 估算净值：优先 IOPV，缺失退回最新价
    df["nav"] = df["iopv"].fillna(df["price"])
    df = df.dropna(subset=["shares", "nav"])
    return df


def save_snapshot(df: pd.DataFrame) -> str:
    """按交易日落盘，返回文件路径。"""
    os.makedirs(SNAP_DIR, exist_ok=True)
    trade_date = df["data_date"].mode().iloc[0]  # 取众数作为交易日
    path = os.path.join(SNAP_DIR, f"{trade_date}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main():
    print(f"[{dt.datetime.now():%H:%M:%S}] 拉取全市场 ETF 快照 ...")
    df = fetch_snapshot()
    path = save_snapshot(df)
    trade_date = df["data_date"].mode().iloc[0]
    print(f"  交易日 {trade_date}：{len(df)} 只 ETF -> {os.path.relpath(path, HERE)}")
    return path


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

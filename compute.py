# -*- coding: utf-8 -*-
"""
核心分析：基于历史快照计算多周期资金流。

资金净流入 = 份额变动 × 净值估算   （与「ETF 资金轮动」看板算法一致）
单位统一换算成「亿元」。

冷启动（只有 1 份快照）时，「今日」列退回东财盘中「主力净流入」近似，
并在 meta 中标记 basis='main_inflow'，从第 2 天起自动切换为份额变动算法。
"""
import os
import glob
import datetime as dt

import pandas as pd

from classify import classify

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.join(HERE, "data", "snapshots")

# (key, 展示名, 回看自然日)。"1日" 特殊处理为「上一份快照」。
PERIODS = [
    ("d1", "最近1日", 1),
    ("w1", "最近1周", 7),
    ("w2", "最近2周", 14),
    ("m1", "最近1月", 30),
    ("m3", "最近3月", 90),
    ("m6", "最近6月", 180),
    ("ytd", "今年以来", None),   # None = 今年1月1日
    ("m12", "最近12月", 365),
]


def load_snapshots() -> dict:
    """读入全部快照，返回 {date(str): DataFrame(index=code)}，按日期升序。"""
    out = {}
    for path in sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv"))):
        date = os.path.splitext(os.path.basename(path))[0]
        df = pd.read_csv(path, dtype={"code": str})
        df["code"] = df["code"].str.zfill(6)
        out[date] = df.set_index("code")
    return dict(sorted(out.items()))


def _pick_baseline(dates, target_date):
    """在已有日期里挑一个 <= target_date 且最接近的，作为对比基准。没有返回 None。"""
    candidates = [d for d in dates if d <= target_date]
    return candidates[-1] if candidates else None


def compute(snaps: dict):
    """返回 (latest_df, meta)。latest_df 含每只 ETF 的分类与各周期资金流(亿元)。"""
    if not snaps:
        raise RuntimeError("没有任何快照，请先运行 fetch.py")

    dates = list(snaps.keys())
    today = dates[-1]
    cur = snaps[today].copy()

    # 分类
    cls = cur["name"].apply(classify)
    cur["sub"] = cls.apply(lambda x: x[0])
    cur["big"] = cls.apply(lambda x: x[1])

    meta = {"trade_date": today, "n_snapshots": len(dates),
            "periods": {}, "basis": {}}

    for key, label, days in PERIODS:
        if key == "d1":
            base_date = dates[-2] if len(dates) >= 2 else None
        elif days is None:  # YTD
            jan1 = f"{today[:4]}-01-01"
            base_date = _pick_baseline(dates[:-1], jan1) or (dates[0] if dates[0] < today else None)
        else:
            target = (dt.date.fromisoformat(today) - dt.timedelta(days=days)).isoformat()
            base_date = _pick_baseline(dates[:-1], target)

        col = f"flow_{key}"
        if base_date is None:
            # 没有足够历史
            if key == "d1":
                # 冷启动：用东财盘中主力净流入近似今日
                cur[col] = cur["main_inflow"] / 1e8
                meta["basis"][key] = "main_inflow"
                meta["periods"][key] = {"label": label, "base_date": None, "available": True}
            else:
                cur[col] = pd.NA
                meta["periods"][key] = {"label": label, "base_date": None, "available": False}
            continue

        base = snaps[base_date]
        d_shares = cur["shares"] - cur.index.map(base["shares"])
        cur[col] = (d_shares * cur["nav"]) / 1e8     # 亿元
        meta["basis"][key] = "shares"
        meta["periods"][key] = {"label": label, "base_date": base_date, "available": True}

    return cur, meta


def aggregate(latest: pd.DataFrame, level: str = "big") -> pd.DataFrame:
    """按 big / sub 汇总各周期资金流，返回汇总表（含规模、ETF只数）。"""
    flow_cols = [f"flow_{k}" for k, _, _ in PERIODS]
    g = latest.groupby(level)
    out = g[flow_cols].sum(min_count=1)
    out["scale"] = g["float_mv"].sum() / 1e8        # 规模(亿元)
    out["count"] = g.size()
    # 按最近1日资金流降序
    out = out.sort_values("flow_d1", ascending=False)
    return out


if __name__ == "__main__":
    snaps = load_snapshots()
    latest, meta = compute(snaps)
    print(f"交易日 {meta['trade_date']} | 快照数 {meta['n_snapshots']} | ETF {len(latest)}")
    print("\n=== 大类资金轮动（最近1日, 亿元）===")
    big = aggregate(latest, "big")
    print(big[["flow_d1", "flow_w1", "flow_m1", "scale", "count"]].round(1).to_string())

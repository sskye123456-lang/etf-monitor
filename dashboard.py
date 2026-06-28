# -*- coding: utf-8 -*-
"""
生成单文件 HTML 看板：data/dashboard.html

风格对标「ETF 份额雷达 / 资金轮动」：暗色、红=流入、绿=流出。
- 顶部：交易日、合计规模、今日净流入
- 资金轮动：大类横向分流条形图（可切周期）
- 热力表：大类 / 细分行业 两层切换，多周期红绿热力
- ETF 明细：可搜索、按当前周期排序
数据以 JSON 内嵌，纯静态，双击即可在浏览器打开。
"""
import os
import json
import datetime as dt

import pandas as pd

from compute import load_snapshots, compute, aggregate, PERIODS
from classify import BIG_ORDER

HERE = os.path.dirname(os.path.abspath(__file__))
# 输出到 docs/index.html —— GitHub Pages 直接服务该目录
OUT = os.path.join(HERE, "docs", "index.html")


def _flows_dict(row):
    out = {}
    for k, _, _ in PERIODS:
        v = row.get(f"flow_{k}")
        out[k] = None if pd.isna(v) else round(float(v), 2)
    return out


def build_payload():
    snaps = load_snapshots()
    latest, meta = compute(snaps)

    big = aggregate(latest, "big")
    sub = aggregate(latest, "sub")

    def agg_records(df, with_big=False):
        recs = []
        for name, row in df.iterrows():
            rec = {"name": name,
                   "flows": _flows_dict(row),
                   "scale": round(float(row["scale"]), 1),
                   "count": int(row["count"])}
            if with_big:
                # 取该细分所属大类（细分内大类唯一）
                rec["big"] = latest.loc[latest["sub"] == name, "big"].iloc[0]
            recs.append(rec)
        return recs

    # 大类按固定顺序，再附上未在表里的
    big_recs = agg_records(big, with_big=False)
    order = {n: i for i, n in enumerate(BIG_ORDER)}
    big_recs.sort(key=lambda r: order.get(r["name"], 99))

    etf_recs = []
    for code, row in latest.iterrows():
        etf_recs.append({
            "code": code, "name": row["name"], "sub": row["sub"], "big": row["big"],
            "nav": round(float(row["nav"]), 3), "pct": round(float(row["pct"]), 2),
            "scale": round(float(row["float_mv"]) / 1e8, 2),
            "flows": _flows_dict(row),
        })

    # 各周期合计净流入
    totals = {}
    for k, _, _ in PERIODS:
        vals = [r["flows"][k] for r in big_recs if r["flows"][k] is not None]
        totals[k] = round(sum(vals), 1) if vals else None
    total_scale = round(float(latest["float_mv"].sum()) / 1e8, 0)

    return {
        "trade_date": meta["trade_date"],
        "n_snapshots": meta["n_snapshots"],
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods": [{"key": k, "label": lb,
                     "available": meta["periods"][k]["available"],
                     "basis": meta["basis"].get(k, "shares")}
                    for k, lb, _ in PERIODS],
        "totals": totals, "total_scale": total_scale, "n_etf": len(latest),
        "big": big_recs, "sub": agg_records(sub, with_big=True), "etf": etf_recs,
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETF 资金流监控 · __DATE__</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2230;--line:#2a3140;--txt:#e6edf3;--mut:#8b949e;
--red:#f85149;--redbg:#3d1418;--green:#3fb950;--greenbg:#0f2e1a;--accent:#58a6ff;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:18px;max-width:1280px;margin:0 auto}
h1{font-size:22px;font-weight:700;letter-spacing:.5px}
.sub{color:var(--mut);font-size:12px;margin-top:4px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 18px;min-width:150px}
.card .k{color:var(--mut);font-size:12px}.card .v{font-size:20px;font-weight:700;margin-top:2px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}
.tab{background:var(--panel);border:1px solid var(--line);color:var(--mut);padding:6px 14px;border-radius:20px;cursor:pointer;font-size:13px}
.tab.on{background:var(--accent);color:#0d1117;border-color:var(--accent);font-weight:600}
.tab.na{opacity:.4;cursor:not-allowed}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.panel h2{font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.note{color:var(--mut);font-size:12px;font-weight:400}
/* diverging bars */
.rot{display:grid;grid-template-columns:120px 1fr 120px;align-items:center;gap:4px 10px;margin:5px 0}
.rot .lbl{font-size:13px}.rot .lf{text-align:right;color:var(--green)}.rot .rt{color:var(--red)}
.bar{position:relative;height:18px}
.bar .mid{position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--line)}
.bar .fill{position:absolute;top:0;height:100%;border-radius:3px}
.bar .pos{left:50%;background:var(--red)}.bar .neg{right:50%;background:var(--green)}
/* heatmap table */
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 8px;text-align:right;white-space:nowrap}
th{color:var(--mut);font-weight:500;border-bottom:1px solid var(--line);cursor:pointer;position:sticky;top:0;background:var(--panel)}
th.l,td.l{text-align:left}
tbody tr:hover{background:#ffffff08}
td.name{font-weight:600}.tag{color:var(--mut);font-size:11px;margin-left:6px}
.cell{border-radius:4px}
.search{background:var(--panel2);border:1px solid var(--line);color:var(--txt);padding:8px 12px;border-radius:8px;width:240px;font-size:13px}
.wrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:10px}
.muted{color:var(--mut)}
.switch{display:flex;gap:6px}.switch .tab{padding:5px 12px}
.foot{color:var(--mut);font-size:11px;margin-top:18px;line-height:1.7}
</style></head><body>
<h1>📡 ETF 资金流监控</h1>
<div class="sub" id="subtitle"></div>
<div class="cards" id="cards"></div>

<div class="tabs" id="periodTabs"></div>

<div class="panel">
  <h2>🔄 大类资金轮动 <span class="note" id="rotNote"></span></h2>
  <div id="rotation"></div>
</div>

<div class="panel">
  <h2>🔥 资金流热力表
    <span class="switch" style="margin-left:auto">
      <span class="tab on" id="lvBig" onclick="setLevel('big')">大类</span>
      <span class="tab" id="lvSub" onclick="setLevel('sub')">细分行业</span>
    </span>
  </h2>
  <div class="wrap"><table id="heat"></table></div>
</div>

<div class="panel">
  <h2>📋 ETF 明细 <span class="note">（按当前周期排序，点击表头可切换）</span>
    <input class="search" id="q" placeholder="搜代码/名称/行业…" oninput="renderETF()" style="margin-left:auto">
  </h2>
  <div class="wrap"><table id="etf"></table></div>
</div>

<div class="foot" id="foot"></div>

<script>
const DATA = __JSON__;
let curPeriod = (DATA.periods.find(p=>p.available)||DATA.periods[0]).key;
let level = 'big';
let etfSort = curPeriod;

const fmt = v => v==null ? '—' : (v>=0?'+':'') + v.toFixed(1);
const fmtScale = v => v>=10000 ? (v/10000).toFixed(2)+'万' : v.toFixed(0);

// 红绿热力色：正=红 负=绿，强度按列内最大绝对值归一
function cellColor(v, maxAbs){
  if(v==null||maxAbs<=0) return '';
  const t = Math.min(Math.abs(v)/maxAbs, 1);
  const a = (0.10 + 0.55*t).toFixed(2);
  return v>=0 ? `background:rgba(248,81,73,${a})` : `background:rgba(63,185,80,${a})`;
}
const colorTxt = v => v==null?'muted':(v>=0?'':'');

function renderHeader(){
  document.getElementById('subtitle').innerHTML =
    `交易日 <b>${DATA.trade_date}</b> · 全市场 ${DATA.n_etf} 只 ETF · 已积累快照 ${DATA.n_snapshots} 份 · 生成于 ${DATA.generated}`;
  const t = DATA.totals[curPeriod];
  document.getElementById('cards').innerHTML = `
    <div class="card"><div class="k">合计规模</div><div class="v">${fmtScale(DATA.total_scale)} 亿</div></div>
    <div class="card"><div class="k">${plabel(curPeriod)}净流入</div>
      <div class="v" style="color:${t>=0?'var(--red)':'var(--green)'}">${fmt(t)} 亿</div></div>
    <div class="card"><div class="k">ETF 数量</div><div class="v">${DATA.n_etf}</div></div>`;
}
const plabel = k => DATA.periods.find(p=>p.key==k).label;
const pinfo  = k => DATA.periods.find(p=>p.key==k);

function renderTabs(){
  document.getElementById('periodTabs').innerHTML = DATA.periods.map(p=>
    `<span class="tab ${p.key==curPeriod?'on':''} ${p.available?'':'na'}"
      onclick="${p.available?`setPeriod('${p.key}')`:''}">${p.label}${p.available?'':' ·待积累'}</span>`).join('');
}

function setPeriod(k){ curPeriod=k; etfSort=k; renderAll(); }
function setLevel(l){ level=l;
  document.getElementById('lvBig').className='tab '+(l=='big'?'on':'');
  document.getElementById('lvSub').className='tab '+(l=='sub'?'on':'');
  renderHeat(); }

function renderRotation(){
  const recs = DATA.big.map(r=>({name:r.name, v:r.flows[curPeriod]}))
    .filter(r=>r.v!=null).sort((a,b)=>b.v-a.v);
  const maxAbs = Math.max(1, ...recs.map(r=>Math.abs(r.v)));
  const info = pinfo(curPeriod);
  document.getElementById('rotNote').textContent =
    info.basis=='main_inflow' ? '（今日为东财盘中主力净流入近似，T+1 起切换为份额变动算法）'
                              : `（份额变动 × 净值；对比基准已就绪）`;
  document.getElementById('rotation').innerHTML = recs.map(r=>{
    const w = (Math.abs(r.v)/maxAbs*50).toFixed(1);
    return `<div class="rot">
      <div class="lbl lf">${r.v<0?fmt(r.v):''}</div>
      <div class="bar"><div class="mid"></div>
        ${r.v>=0?`<div class="fill pos" style="width:${w}%"></div>`
                :`<div class="fill neg" style="width:${w}%"></div>`}</div>
      <div class="lbl rt">${r.v>=0?r.name+' '+fmt(r.v):r.name}</div></div>`;
  }).join('');
}

function renderHeat(){
  const rows = level=='big' ? DATA.big : DATA.sub;
  const cols = DATA.periods;
  // 每列最大绝对值
  const maxAbs = {};
  cols.forEach(c=>{ maxAbs[c.key]=Math.max(1,...rows.map(r=>Math.abs(r.flows[c.key]??0))); });
  let h = `<thead><tr><th class="l">${level=='big'?'大类':'细分行业'}</th>
    <th>规模/亿</th><th>数量</th>`+
    cols.map(c=>`<th>${c.label}</th>`).join('')+`</tr></thead><tbody>`;
  const sorted = [...rows].sort((a,b)=>(b.flows[curPeriod]??-1e9)-(a.flows[curPeriod]??-1e9));
  for(const r of sorted){
    h+=`<tr><td class="l name">${r.name}${r.big&&level=='sub'?`<span class="tag">${r.big}</span>`:''}</td>
      <td class="muted">${r.scale}</td><td class="muted">${r.count}</td>`;
    for(const c of cols){
      const v=r.flows[c.key];
      h+=`<td class="cell" style="${cellColor(v,maxAbs[c.key])}">${fmt(v)}</td>`;
    }
    h+=`</tr>`;
  }
  document.getElementById('heat').innerHTML=h+`</tbody>`;
}

function renderETF(){
  const q=(document.getElementById('q').value||'').trim().toLowerCase();
  let rows=DATA.etf;
  if(q) rows=rows.filter(r=>r.code.includes(q)||r.name.toLowerCase().includes(q)
        ||r.sub.toLowerCase().includes(q)||r.big.toLowerCase().includes(q));
  rows=[...rows].sort((a,b)=>(b.flows[etfSort]??-1e9)-(a.flows[etfSort]??-1e9)).slice(0,300);
  const cols=DATA.periods;
  let h=`<thead><tr><th class="l">代码</th><th class="l">名称</th><th class="l">行业</th>
    <th>规模/亿</th><th>涨跌%</th>`+
    cols.map(c=>`<th onclick="etfSort='${c.key}';renderETF()" style="${c.key==etfSort?'color:var(--accent)':''}">${c.label}</th>`).join('')+`</tr></thead><tbody>`;
  const maxAbs={}; cols.forEach(c=>{maxAbs[c.key]=Math.max(1,...rows.map(r=>Math.abs(r.flows[c.key]??0)))});
  for(const r of rows){
    h+=`<tr><td class="l muted">${r.code}</td><td class="l name">${r.name}</td>
      <td class="l muted">${r.sub}<span class="tag">${r.big}</span></td>
      <td class="muted">${r.scale}</td>
      <td style="color:${r.pct>=0?'var(--red)':'var(--green)'}">${r.pct>=0?'+':''}${r.pct}</td>`;
    for(const c of cols) h+=`<td class="cell" style="${cellColor(r.flows[c.key],maxAbs[c.key])}">${fmt(r.flows[c.key])}</td>`;
    h+=`</tr>`;
  }
  if(!rows.length) h+=`<tr><td class="l muted" colspan="20">无匹配</td></tr>`;
  document.getElementById('etf').innerHTML=h+`</tbody>`;
}

function renderAll(){ renderHeader(); renderTabs(); renderRotation(); renderHeat(); renderETF(); }
document.getElementById('foot').innerHTML =
  `数据来源：东方财富（akshare fund_etf_spot_em）｜资金净流入 = 份额变动 × 净值估算，单位亿元，红=流入 绿=流出。`+
  `<br>份额型资金流需逐日积累快照，多周期列随快照增多自动点亮；「今日·待积累」期间用盘中主力净流入近似。仅供研究，非投资建议。`;
renderAll();
</script></body></html>"""


def main():
    payload = build_payload()
    html = (HTML.replace("__JSON__", json.dumps(payload, ensure_ascii=False))
                .replace("__DATE__", payload["trade_date"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  看板已生成 -> {os.path.relpath(OUT, HERE)}  ({len(html)//1024} KB)")
    return OUT


if __name__ == "__main__":
    main()

# ETF 资金流监控

每天监控 A 股全市场 ETF（约 1500+ 只），按**行业大类 / 细分行业**两层汇总资金流入流出，
生成一张暗色风格、红=流入 绿=流出 的 HTML 看板，双击即可在浏览器查看。

数据来源：东方财富（通过开源库 [akshare](https://akshare.akfamily.xyz)），免费、无需账号。

> 资金净流入 = 份额变动 × 净值估算（与"ETF 资金轮动"看板同口径），单位：亿元。

**🌐 在线看板**：部署到 GitHub Pages 后是一个公开链接，发给谁都能看；每个交易日收盘后自动更新（链接部署完回填到这里）。

---

## 快速开始

```bash
cd etf-monitor
./.venv/bin/python run.py          # 抓快照 → 计算 → 生成 docs/index.html
open docs/index.html               # 本地浏览器预览
```

首次运行已配好虚拟环境（`.venv/`）。如需在新机器重建：

```bash
/usr/local/bin/python3.14 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

## 看板功能

- **顶部卡片**：合计规模、当前周期净流入、ETF 数量
- **周期切换**：最近 1日 / 1周 / 2周 / 1月 / 3月 / 6月 / 今年以来 / 12月
- **大类资金轮动**：横向分流条形图（左绿流出、右红流入）
- **资金流热力表**：大类 ↔ 细分行业两层切换，多周期红绿热力
- **ETF 明细**：可搜索（代码/名称/行业），点表头按任意周期排序

## 关于多周期与冷启动

akshare 拿不到**历史份额**，所以份额型资金流必须**从今天起逐日积累快照**：

- **第 1 天**：只有"最近 1日"列，且用东财盘中**主力净流入**近似（看板会标注）；
  其余周期显示"待积累"。
- **第 2 天起**："最近 1日"切换为标准的"份额变动 × 净值"算法；
  随着快照变多，1周 / 1月 / … 各列自动点亮。

快照存于 `data/snapshots/<交易日>.csv`，一天一份，非交易日重复跑不会污染。

## 每天自动发布到 GitHub Pages

`publish.sh` = 生成看板 → 提交 → 推送，Pages 在 1~2 分钟后自动更新线上链接。
建议交易日收盘后运行（如 18:30）。

**crontab**（周一至周五 18:30）：

```cron
30 18 * * 1-5 /Users/ambershao/Workspace/project02/etf-monitor/publish.sh >> /Users/ambershao/Workspace/project02/etf-monitor/data/run.log 2>&1
```

安装：`crontab -e` 后粘贴上面一行。
（`run_daily.sh` 是不推送、只生成本地文件的版本。）

## 文件结构

| 文件 | 作用 |
|------|------|
| `fetch.py` | 拉取东财全市场 ETF 快照，落盘 `data/snapshots/` |
| `classify.py` | 行业分类规则（名称→细分行业→大类，~100% 覆盖） |
| `compute.py` | 多周期资金流计算 + 大类/细分聚合 |
| `dashboard.py` | 生成单文件 HTML 看板 |
| `run.py` | 一键编排：fetch → compute → dashboard |
| `publish.sh` | 每日定时：生成 → 提交 → 推送（Pages 自动更新） |
| `run_daily.sh` | 仅本地生成、不推送的定时入口 |

## 调整行业分类

所有行业归类规则集中在 `classify.py` 的 `RULES` 列表里，按顺序匹配、第一条命中即返回。
改关键词或新增细分行业，编辑这一个文件即可。

---

*仅供研究学习，非投资建议。*

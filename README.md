# A 股框架笔记：网站项目

## 目录
- `pipeline/fetch.py`：抓取数据，写入 `data/raw/`
- `pipeline/analyze.py`：各节点的判定规则、打分、关注条件、今日变化（所有阈值都在这里）
- `pipeline/build.py` + `style.css`：生成静态页面到 `docs/`（GitHub Pages 从这里发布）
- `data/manual.json`：人工维护的外部环境、政策打分和事件
- `data/trades.json`：操作记录
- `data/snapshots/`：每天的判定快照（用于对比变化、操作记录的信号快照）
- `docs/`：要发布的网站文件

## 每日运行
```
python3 -I pipeline/fetch.py <项目根目录>
python3 -I pipeline/build.py <项目根目录>
```
然后把 `docs/` 发布到托管平台。

## 数据来源
东方财富数据中心（PMI、CPI、PPI、出口、工业增加值、社零、GDP、M1/M2、LPR、中美国债、两融）、东方财富行情（指数、离岸人民币）、中证指数公司（中证全指、沪深 300 市盈率）。

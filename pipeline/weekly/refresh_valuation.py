"""刷新核验文件的价格敏感字段，财务口径保持不变。
用法：python3 -I pipeline/weekly/refresh_valuation.py <根目录> <历史文件>
历史文件：{asof, rows: {股票代码: [{TRADE_DATE,PB_MRQ,PE_TTM,TOTAL_MARKET_CAP}]}, errors}
来源 RPT_VALUEANALYSIS_DET；取截止日前五年完整交易日，不能用单日涨跌推算历史分位。
"""
import json,sys,math
from pathlib import Path
root=Path(sys.argv[1]);raw=json.loads(Path(sys.argv[2]).read_text());p=root/'data/raw/stock_pick/verify.json';v=json.loads(p.read_text())
if raw.get('errors'):raise SystemExit('估值历史有缺口，停止写入')
changes=[]
for c,x in v.items():
 if c.startswith('_'):continue
 rows=sorted(raw['rows'][c],key=lambda r:r['TRADE_DATE']);last=rows[-1];date=last['TRADE_DATE'][:10]
 if date!=raw['asof']:raise SystemExit(c+' 最新估值日期不一致')
 hist=sorted(r['PB_MRQ'] for r in rows if r.get('PB_MRQ') is not None);now=last['PB_MRQ'];q=(len(hist)-1)*.95
 if len(hist)<20 or now is None:raise SystemExit(c+' 估值样本不足')
 pb95=hist[math.floor(q)]+(hist[math.ceil(q)]-hist[math.floor(q)])*(q%1)
 x['valuation_sample_start']=rows[0]['TRADE_DATE'][:10];x['valuation_n']=len(hist)
 x['valuation_window']='上市以来' if len(hist)<1000 else '近五年'
 before=x.get('pb',0)>x.get('pb95',float('inf'))
 x.update(pb=round(now,6),pe_ttm=last.get('PE_TTM'),mc=round(last['TOTAL_MARKET_CAP']/1e8,2),pbpct5=round(sum(y<=now for y in hist)/len(hist)*100),pb95=round(pb95,6),val_date=date)
 x['pe_norm']=round(x['mc']/x['np_avg5'],2) if x.get('np_avg5',0)>0 else None
 if before!=(x['pb']>x['pb95']):changes.append({'code':c,'name':x['name'],'old_veto':before,'new_veto':x['pb']>x['pb95'],'pb':x['pb'],'pb95':x['pb95']})
v['_meta']['valuation_asof']=raw['asof'];v['_meta']['valuation_source']='RPT_VALUEANALYSIS_DET，过去五年日频PB_MRQ；分位为不高于现值的样本占比，95%阈值用线性插值；PE与总市值为同日值。财务字段报告期与原核验日期保持不变。'
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
(root/f'data/raw/weekly/valuation_changes_{raw["asof"]}.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
print('updated',len(v)-1,'valuation rows; veto changes',changes)

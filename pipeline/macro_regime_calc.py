"""Reproducible numbers behind the 2026-11-13 macro regime rewrite (分子/分母/水龙头).
Usage: python3 -I pipeline/macro_regime_calc.py <root>  -> docs/data/macro-regime-evidence.json"""
import json,sys,bisect,statistics as st,datetime
from pathlib import Path

def rows(root,name):
    d=json.loads((root/'data/raw'/(name+'.json')).read_text());return d['rows'] if isinstance(d,dict) and 'rows' in d else d

def compute(root):
    root=Path(root);bond={x['SOLAR_DATE'][:10]:x for x in rows(root,'bond')};bd=sorted(bond)
    def cn10(d):
        i=bisect.bisect_right(bd,d)-1
        while i>=0 and not bond[bd[i]].get('EMM00166466'):i-=1
        return bond[bd[i]]['EMM00166466']
    out={'method':'股债差=1/PE−中国10年国债；分位为样本内小于当前值的观测占比。回测用扩张窗口分位（至少250个观测）与之后120个交易日收益，样本重叠、独立事件少，只作提醒。PPI基数推算用统计局公布的同比与2025年5—10月环比。','erp':{},'backtest':{}}
    for name,label in [('pe_all','中证全指'),('pe_hs300','沪深300')]:
        pe=[x for x in rows(root,name) if x.get('pe') and x.get('close')]
        erp=[100/x['pe']-cn10(x['date']) for x in pe];cur=erp[-1]
        out['erp'][name]={'label':label,'date':pe[-1]['date'],'pe':pe[-1]['pe'],'cn10y':cn10(pe[-1]['date']),'erp_pct':round(cur,2),'percentile':round(100*sum(e<cur for e in erp)/len(erp),1),'sample_start':pe[0]['date'],'n':len(erp)}
        res=[]
        for i in range(250,len(pe)-120):
            p=sum(e<erp[i] for e in erp[:i+1])/(i+1);res.append((p,pe[i+120]['close']/pe[i]['close']-1))
        hi=[r for p,r in res if p>=.8]
        out['backtest'][name]={'label':label,'bucket':'股债差分位≥80%','n':len(hi),'median_pct':round(100*st.median(hi),1),'win_pct':round(100*sum(r>0 for r in hi)/len(hi),0)}
    m=sorted(rows(root,'margin'),key=lambda x:x['DIM_DATE']);cur=m[-1];pk=max(m[-250:],key=lambda x:x['RZRQYE'])
    zb=[x['RZYEZB'] for x in m if x.get('RZYEZB')]
    out['margin']={'date':cur['DIM_DATE'][:10],'balance_trn':round(cur['RZRQYE']/1e12,2),'peak_date':pk['DIM_DATE'][:10],'peak_trn':round(pk['RZRQYE']/1e12,2),'from_peak_pct':round(100*(cur['RZRQYE']/pk['RZRQYE']-1),1),'share_of_float_pct':round(cur['RZYEZB'],2),'share_percentile_since':m[0]['DIM_DATE'][:10],'share_percentile':round(100*sum(z<cur['RZYEZB'] for z in zb)/len(zb),0)}
    idx={}
    for name,label in [('idx_all','中证全指'),('idx_hs300','沪深300'),('idx_cyb','创业板指'),('idx_kc50','科创50')]:
        r=rows(root,name);h=max(r[-300:],key=lambda x:x['close']);lo=min([x for x in r if x['date']>=h['date']],key=lambda x:x['close'])
        idx[name]={'label':label,'high_date':h['date'],'high':h['close'],'low_date':lo['date'],'low':lo['close'],'drawdown_pct':round(100*(lo['close']/h['close']-1),1),'last_date':r[-1]['date'],'last':r[-1]['close']}
    wk={}
    for x in rows(root,'idx_hs300'):
        y,w,_=datetime.date.fromisoformat(x['date']).isocalendar();wk[(y,w)]=x['close']
    ks=sorted(wk);best=n=0
    for a,b in zip(ks,ks[1:]):
        n=n+1 if wk[b]<wk[a] else 0;best=max(best,n)
    idx['hs300_longest_weekly_losing_streak_in_sample']=best
    out['index']=idx
    ppi={x['TIME']:x['BASE_SAME'] for x in rows(root,'ppi')}
    mom_2025=[-0.4,-0.4,-0.2,0.0,0.0,0.1]  # 2025年5—10月环比；7、8月统计局口径为未上涨，按-0.2/0.0计
    base=1.0
    for x in mom_2025:base*=1+x/100
    oct26,apr26=ppi['2026年10月份'],ppi['2026年04月份']
    level=(1+oct26/100)/(1+apr26/100)*base
    need=((1.045/level)**(1/6)-1)*100
    out['ppi_base']={'oct2026_yoy':oct26,'apr2026_yoy':apr26,'mom_2025_may_oct':mom_2025,'level_oct26_vs_apr26_pct':round(100*(level-1),2),'apr2027_yoy_if_flat':round(100*(level-1),1),'avg_mom_needed_for_4_5pct':round(need,2)}
    hk=json.loads((root/'data/raw/hk/valuations.json').read_text())['indices']['hsi']
    v=hk['rows'][-1] if isinstance(hk,dict) and 'rows' in hk else hk[-1]
    us=json.loads((root/'docs/data/market-verdict-evidence.json').read_text())['observations']['hk']
    out['hk']={'date':v['date'],'pe':v['pe_ratio'],'dividend_yield':v['dividend_yield_pct'],'earnings_yield':round(100/v['pe_ratio'],2),'us10y':us['us10']['value'],'us10y_date':us['us10']['date'],'gap_vs_us10y':round(100/v['pe_ratio']-us['us10']['value'],2),'hibor_1m':round(us['hibor'],2)}
    for name in ['hsi','hstech']:
        r=json.loads((root/'data/raw/hk'/(name+'.json')).read_text())['rows']
        for a,b,key in [('2026-06-01','2026-07-15','june_low'),('2026-09-25','2026-11-11','oct_low')]:
            lo=min([x for x in r if a<=x['date']<=b],key=lambda x:x['close']);out['hk'][name+'_'+key]={'date':lo['date'],'close':lo['close']}
    cnb=[(d,bond[d]) for d in bd if bond[d].get('EMM00166466')]
    out['rates']={'cn10y_now':cnb[-1][1]['EMM00166466'],'cn10y_now_date':cnb[-1][0],'cn10y_year_ago':[b['EMM00166466'] for d,b in cnb if d<='2025-11-13'][-1],'us10y_year_ago':[b['EMG00001310'] for d,b in cnb if d<='2025-11-13' and b.get('EMG00001310')][-1]}
    return out

if __name__=='__main__':
    root=Path(sys.argv[1]);o=compute(root);(root/'docs/data/macro-regime-evidence.json').write_text(json.dumps(o,ensure_ascii=False,indent=1));print(json.dumps(o,ensure_ascii=False)[:3000])

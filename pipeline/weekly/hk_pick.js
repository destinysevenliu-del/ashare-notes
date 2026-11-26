// 港股顺势选股：取数与指标（在 https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_VALUEANALYSIS_DET&pageSize=1 页面执行）
// 用法：await hkPick('2026-11-25') ；约2—3分钟。结果在返回值，保存为 data/raw/stock_pick/hk_enrich.json 后由 pipeline/hk_pick.py 使用。
// 口径：
//  候选范围＝截止日港股通（南向）可买股票，按东方财富港股行业：银行、电讯、石油及天然气、煤炭、工用运输、半导体。
//  价格＝RPT_MUTUAL_STOCK_HOLDRANKS（南向持股日表，MUTUAL_TYPE=002）的每日收盘价与涨跌幅，复权方法与A股相同（由涨跌幅从最新收盘价倒推）。
//  南向持股占比＝该表 HOLD_SHARES_RATIO（占港股股本%），20日变化为截止日与20个交易日前之差（百分点）。
//  财务＝RPT_HKF10_FN_MAININDICATOR 最新一期（港元口径）：营收同比、归母利润同比（均为报告期累计）、ROE、每股净资产、滚动每股收益、每股经营现金流、基本每股收益。
//  分红＝RPT_HKF10_INFO_DIVIDEND 中 ASSIGN_PERIOD 以“2025”开头的方案合计（2025年度，港元；人民币方案按“相当于港币”或汇率折算），与A股“2025年度每股分红”同口径。
//  港股市值＝RPT_HKF10_INFO_ORGPROFILE 的港股股本 HK_SHARES × 收盘价（只含H股/港股部分）。
async function hkPick(asof, inds = ['银行', '电讯', '石油及天然气', '煤炭', '工用运输', '半导体'], cnyPerHkd = 0.855) {
  const all = async q => { let out = [], p = 1; for (;;) { let d; for (let i = 0; i < 4; i++) { try { d = await fetch('/api/data/v1/get?' + new URLSearchParams({ ...q, pageNumber: p })).then(r => r.json()); break } catch (e) { await new Promise(r => setTimeout(r, 1500)) } } const r = (d && d.result) || { data: [], pages: 1 }; out = out.concat(r.data || []); if (p >= (r.pages || 1)) break; p++ } return out };
  const day = s => s.slice(0, 10);
  const shift = (d, n) => { const t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10) };
  const uni = (await all({ reportName: 'RPT_MUTUAL_STOCK_HOLDRANKS', columns: 'SECURITY_CODE,SECURITY_NAME,INDUSTRY', pageSize: 500, filter: `(MUTUAL_TYPE="002")(INTERVAL_TYPE="1")(HOLD_DATE='${asof}')` })).filter(x => inds.includes(x.INDUSTRY));
  const codes = uni.map(x => x.SECURITY_CODE), out = {};
  for (const x of uni) out[x.SECURITY_CODE] = { name: x.SECURITY_NAME, ind: x.INDUSTRY };
  for (let i = 0; i < codes.length; i += 8) {
    const cs = codes.slice(i, i + 8), inn = '(' + cs.map(c => '"' + c + '"').join(',') + ')';
    const px = await all({ reportName: 'RPT_MUTUAL_STOCK_HOLDRANKS', columns: 'SECURITY_CODE,HOLD_DATE,CLOSE_PRICE,CHANGE_RATE,HOLD_SHARES_RATIO', pageSize: 500, sortColumns: 'HOLD_DATE', sortTypes: 1, filter: `(MUTUAL_TYPE="002")(INTERVAL_TYPE="1")(SECURITY_CODE in ${inn})(HOLD_DATE>='${shift(asof, -400)}')(HOLD_DATE<='${asof}')` });
    const mi = await all({ reportName: 'RPT_HKF10_FN_MAININDICATOR', columns: 'SECURITY_CODE,REPORT_DATE,REPORT_TYPE,CURRENCY,OPERATE_INCOME_YOY,HOLDER_PROFIT_YOY,HOLDER_PROFIT,ROE_AVG,BPS,EPS_TTM,PER_NETCASH_OPERATE,BASIC_EPS', pageSize: 500, sortColumns: 'REPORT_DATE', sortTypes: -1, filter: `(SECURITY_CODE in ${inn})(REPORT_DATE>='${shift(asof, -400)}')` });
    const dv = await all({ reportName: 'RPT_HKF10_INFO_DIVIDEND', columns: 'SECURITY_CODE,ASSIGN_PERIOD,PLAN_EXPLAIN', pageSize: 500, filter: `(SECURITY_CODE in ${inn})(NOTICE_DATE>='${shift(asof, -800)}')` });
    const op = await all({ reportName: 'RPT_HKF10_INFO_ORGPROFILE', columns: 'SECURITY_CODE,HK_SHARES', pageSize: 50, filter: `(SECURITY_CODE in ${inn})` });
    for (const c of cs) {
      const o = out[c];
      const p = px.filter(x => x.SECURITY_CODE === c && x.CLOSE_PRICE != null).sort((a, b) => a.HOLD_DATE < b.HOLD_DATE ? -1 : 1);
      if (p.length > 60) {
        const n = p.length, adj = new Array(n); adj[n - 1] = p[n - 1].CLOSE_PRICE;
        for (let k = n - 1; k > 0; k--) adj[k - 1] = adj[k] / (1 + (p[k].CHANGE_RATE || 0) / 100);
        const y1 = shift(asof, -365), win = adj.filter((_, k) => day(p[k].HOLD_DATE) > y1), hi = Math.max(...win), lo = Math.min(...win), cc = adj[n - 1];
        const ma = adj.slice(-60).reduce((s, v) => s + v, 0) / Math.min(60, n);
        Object.assign(o, { close: p[n - 1].CLOSE_PRICE, pxdate: day(p[n - 1].HOLD_DATE), pos52: hi > lo ? Math.round((cc - lo) / (hi - lo) * 100) / 100 : null, dd: Math.round((cc / hi - 1) * 1000) / 10,
          ret60: n > 60 ? Math.round((cc / adj[n - 61] - 1) * 1000) / 10 : null, vsMA60: Math.round((cc / ma - 1) * 1000) / 10,
          sb: p[n - 1].HOLD_SHARES_RATIO, sb20: n > 20 && p[n - 21].HOLD_SHARES_RATIO != null ? Math.round((p[n - 1].HOLD_SHARES_RATIO - p[n - 21].HOLD_SHARES_RATIO) * 100) / 100 : null });
      }
      const m = mi.filter(x => x.SECURITY_CODE === c).sort((a, b) => a.REPORT_DATE < b.REPORT_DATE ? 1 : -1)[0];
      if (m) Object.assign(o, { rpt: m.REPORT_TYPE, cur: m.CURRENCY, rev_yoy: m.OPERATE_INCOME_YOY, np_yoy: m.HOLDER_PROFIT_YOY, np: m.HOLDER_PROFIT, roe: m.ROE_AVG, bps: m.BPS, eps_ttm: m.EPS_TTM, ocfps: m.PER_NETCASH_OPERATE, beps: m.BASIC_EPS });
      let dps = 0, parts = [];
      for (const x of dv.filter(x => x.SECURITY_CODE === c && /^2025/.test(x.ASSIGN_PERIOD || ''))) {
        const t = x.PLAN_EXPLAIN || ''; let v = null;
        const h = t.match(/港币\s*([\d.]+)\s*元/) || t.match(/港元\s*([\d.]+)/); const r = t.match(/人民币\s*([\d.]+)\s*元/);
        if (h) v = +h[1]; else if (r) v = +r[1] / cnyPerHkd;
        if (v) { dps += v; parts.push(x.ASSIGN_PERIOD + ' ' + t) }
      }
      o.dps = dps ? Math.round(dps * 10000) / 10000 : null; o.dps_parts = parts;
      const s = op.find(x => x.SECURITY_CODE === c); if (s && o.close) o.mc = Math.round(s.HK_SHARES * o.close / 1e8);
    }
    window._hkst = i;
  }
  return { asof, cnyPerHkd, stocks: out };
}

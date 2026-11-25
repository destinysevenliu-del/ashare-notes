// 上证指数位置（首页“上证指数在什么位置”，数据写入 data/sse_view.json）
// 一、分位：在 https://www.csindex.com.cn 页面执行 await sseLevel('20261124')
//    返回当前收盘、市盈率、点位分位（2005、2016年以来）、市盈率分位（2011、2016年以来）、2011年以来市盈率区间、高点。
//    分位＝样本内低于当前值的交易日占比，四舍五入；剔除周末与重复行。
// 二、分解：在 https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_VALUEANALYSIS_DET&pageSize=1 页面执行
//    await sseDecomp('2026-11-24', [[期初日, 标签, 期初上证点位, 期末上证点位], ...])
//    沪市A股（60、688开头）每只股票：期初总市值×（期末收盘/期初收盘−1），按期末行业（东方财富 BOARD_NAME）分成
//    银行（银行Ⅱ）、半导体与其他，按期初总市值加权。bank_pts＝期初点位×银行权重×银行涨跌；exbank_level＝期初点位×(1＋剔除银行涨跌)。
//    2026-11-25 用本脚本重算11月11日的结果，与旧版逐项一致（剔除银行点位差1点为四舍五入）。
async function sseLevel(asof) {
  let rows = [];
  for (let y = 2005; y <= Number(asof.slice(0, 4)); y++) {
    const d = await fetch(`/csindex-home/perf/index-perf?indexCode=000001&startDate=${y}0101&endDate=${y}1231`).then(r => r.json());
    for (const x of d.data || []) rows.push([x.tradeDate, x.close, x.peg, x.tradingVol]);
  }
  rows.sort((a, b) => a[0] < b[0] ? -1 : 1);
  const ded = [];
  for (const r of rows) {
    const wd = new Date(r[0].slice(0, 4) + '-' + r[0].slice(4, 6) + '-' + r[0].slice(6) + 'T00:00:00Z').getUTCDay();
    if (wd === 0 || wd === 6) continue;
    if (ded.length && ded.at(-1)[1] === r[1] && ded.at(-1)[3] === r[3]) continue;
    ded.push(r);
  }
  const upto = ded.filter(r => r[0] <= asof), cur = upto.at(-1);
  const pct = (arr, v) => Math.round(arr.filter(x => x < v).length / arr.length * 100);
  const lv = s => pct(upto.filter(r => r[0] >= s).map(r => r[1]), cur[1]);
  const pe = s => pct(upto.filter(r => r[0] >= s && r[2]).map(r => r[2]), cur[2]);
  const pa = upto.filter(r => r[0] >= '20110101' && r[2]).map(r => r[2]);
  const s16 = upto.filter(r => r[0] >= '20160101');
  const hi16 = s16.reduce((a, b) => b[1] > a[1] ? b : a), hiAll = upto.reduce((a, b) => b[1] > a[1] ? b : a);
  const exbankPct = v => pct(s16.map(r => r[1]), v);
  return { date: cur[0], close: cur[1], pe: cur[2], level_pct: { since2005: lv('20050101'), since2016: lv('20160101') },
    pe_pct: { since2011: pe('20110101'), since2016: pe('20160101') }, pe_range_since2011: [Math.min(...pa), Math.max(...pa)],
    hi16: hi16.slice(0, 2), hiAll: hiAll.slice(0, 2), exbankPct };
}
async function sseDecomp(end, periods) {
  const all = async q => { let out = [], p = 1; for (;;) { const d = await fetch('/api/data/v1/get?' + new URLSearchParams({ ...q, pageNumber: p })).then(r => r.json()); const r = d.result || { data: [], pages: 1 }; out = out.concat(r.data || []); if (p >= (r.pages || 1)) break; p++; } return out; };
  const snap = async dt => { const m = {}; for (const x of await all({ reportName: 'RPT_VALUEANALYSIS_DET', columns: 'SECURITY_CODE,BOARD_NAME,TOTAL_MARKET_CAP,CLOSE_PRICE', pageSize: 500, filter: `(TRADE_DATE='${dt}')` })) if (/^(60|688)/.test(x.SECURITY_CODE) && x.CLOSE_PRICE > 0) m[x.SECURITY_CODE] = x; return m; };
  const E = await snap(end), out = [];
  for (const [from, label, sse0, sse1] of periods) {
    const S = await snap(from); let T = 0, TR = 0, B = 0, BR = 0, SM = 0, SR = 0, O = 0, OR = 0;
    for (const c in S) {
      const e = E[c]; if (!e) continue;
      const mv = S[c].TOTAL_MARKET_CAP, r = e.CLOSE_PRICE / S[c].CLOSE_PRICE - 1, bd = e.BOARD_NAME || S[c].BOARD_NAME;
      T += mv; TR += mv * r;
      if (bd === '银行Ⅱ') { B += mv; BR += mv * r; } else if (bd === '半导体') { SM += mv; SR += mv * r; } else { O += mv; OR += mv * r; }
    }
    const bw = B / T, br = BR / B, sr = SR / SM, ex = (SR + OR) / (SM + O);
    out.push({ from, label, sse0, actual: +((sse1 / sse0 - 1) * 100).toFixed(1), approx: +(TR / T * 100).toFixed(1), bank_w: +(bw * 100).toFixed(1),
      bank_ret: +(br * 100).toFixed(1), bank_pts: Math.round(sse0 * bw * br), semi_ret: +(sr * 100).toFixed(1), semi_pts: Math.round(sse0 * SM / T * sr),
      exbank_ret: +(ex * 100).toFixed(1), exbank_level: Math.round(sse0 * (1 + ex)), other_ret: +(OR / O * 100).toFixed(1) });
  }
  return out;
}

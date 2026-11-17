// 每周价格更新：浏览器取数备用通道（Python 无法访问东方财富时使用）。
// 用法：在浏览器打开 https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_VALUEANALYSIS_DET&pageSize=1
//       然后在该页执行本文件内容，再执行 await weeklyMetrics(["600135",...], "2026-11-20")
// 返回值是 {asof, via, metrics:{code:{...}}}，保存为 data/raw/weekly/metrics_<asof>.json 后交给 weekly_update.py。
// 计算口径必须与 pipeline/weekly/metrics.py 完全一致（test_weekly.py 用同一份样本核对两边结果）。
async function weeklyMetrics(codes, asof) {
  const B = '/api/data/v1/get?';
  const get = async q => { for (let i = 0; i < 4; i++) { try { const d = await fetch(B + new URLSearchParams(q)).then(r => r.json()); return d.result || { data: [], pages: 1 }; } catch (e) { await new Promise(r => setTimeout(r, 1500 * (i + 1))); } } throw new Error('fetch failed ' + q.reportName); };
  const all = async (report, sort, filter) => { let out = [], p = 1; for (;;) { const r = await get({ reportName: report, columns: 'ALL', pageSize: 500, pageNumber: p, sortColumns: sort, sortTypes: -1, filter }); out = out.concat(r.data || []); if (p >= (r.pages || 1)) break; p++; } return out; };
  const day = s => s.slice(0, 10);
  const shift = (d, n) => { const t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };
  const from = shift(asof, -400), y1 = shift(asof, -365), l6 = shift(asof, 182);
  const raw = {};
  for (let i = 0; i < codes.length; i += 10) {
    const cs = codes.slice(i, i + 10), inn = '(' + cs.map(c => '"' + c + '"').join(',') + ')';
    for (const x of await all('RPT_VALUEANALYSIS_DET', 'TRADE_DATE', `(SECURITY_CODE in ${inn})(TRADE_DATE>='${from}')(TRADE_DATE<='${asof}')`)) (raw[x.SECURITY_CODE] ??= { px: [], mg: [], hd: [], lf: [] }).px.push([day(x.TRADE_DATE), x.CLOSE_PRICE, x.CHANGE_RATE]);
    for (const x of await all('RPTA_WEB_RZRQ_GGMX', 'DATE', `(SCODE in ${inn})(DATE>='${shift(asof, -60)}')(DATE<='${asof}')`)) (raw[x.SCODE] ??= { px: [], mg: [], hd: [], lf: [] }).mg.push([day(x.DATE), x.RZYE, x.RZYEZB]);
    for (const x of await all('RPT_F10_EH_HOLDERNUM', 'END_DATE', `(SECURITY_CODE in ${inn})(END_DATE>='${shift(asof, -400)}')`)) (raw[x.SECURITY_CODE] ??= { px: [], mg: [], hd: [], lf: [] }).hd.push([day(x.END_DATE), x.TOTAL_NUM_RATIO, x.HOLD_FOCUS, x.FREEHOLD_RATIO_TOTAL, day(x.NOTICE_DATE || x.END_DATE)]);
    for (const x of await all('RPT_LIFT_STAGE', 'FREE_DATE', `(SECURITY_CODE in ${inn})(FREE_DATE>'${asof}')(FREE_DATE<='${l6}')`)) (raw[x.SECURITY_CODE] ??= { px: [], mg: [], hd: [], lf: [] }).lf.push([day(x.FREE_DATE), x.TOTAL_RATIO]);
  }
  const bond_rows = (await get({ reportName: 'RPTA_WEB_TREASURYYIELD', columns: 'SOLAR_DATE,EMM00166466,EMG00001310', pageSize: 15, sortColumns: 'SOLAR_DATE', sortTypes: -1, filter: `(SOLAR_DATE<='${asof}')` })).data || [];
  const ty = (await get({ reportName: 'RPTA_WEB_TREASURYYIELD', columns: 'SOLAR_DATE,EMM00166466', pageSize: 5, sortColumns: 'SOLAR_DATE', sortTypes: -1, filter: `(SOLAR_DATE<='${asof}')` })).data.filter(x => x.EMM00166466 != null)[0];
  const metrics = {};
  for (const c of codes) metrics[c] = compute(raw[c] || { px: [], mg: [], hd: [], lf: [] }, asof, y1);
  return { asof, via: 'browser', bond_rows, cn10y: ty ? { date: day(ty.SOLAR_DATE), value: ty.EMM00166466 } : null, metrics };
}
function compute(r, asof, y1) {
  const r2 = v => v == null ? null : Math.round(v * 100) / 100, r1 = v => v == null ? null : Math.round(v * 10) / 10;
  const px = r.px.filter(x => x[1] != null).sort((a, b) => a[0] < b[0] ? -1 : 1);
  const out = {};
  if (px.length) {
    const n = px.length, adj = new Array(n); adj[n - 1] = px[n - 1][1];
    for (let i = n - 1; i > 0; i--) adj[i - 1] = adj[i] / (1 + (px[i][2] || 0) / 100);
    const c = adj[n - 1], win = adj.filter((_, i) => px[i][0] > y1), hi = Math.max(...win), lo = Math.min(...win);
    const last60 = adj.slice(-60), ma = last60.reduce((s, v) => s + v, 0) / last60.length;
    Object.assign(out, { close: px[n - 1][1], pxdate: px[n - 1][0], pos52: hi > lo ? r2((c - lo) / (hi - lo)) : null, dd: r1((c / hi - 1) * 100), ret60: n > 60 ? r1((c / adj[n - 61] - 1) * 100) : null, vsMA60: r1((c / ma - 1) * 100) });
  }
  const mg = r.mg.filter(x => x[1] != null).sort((a, b) => a[0] < b[0] ? -1 : 1);
  if (mg.length) { const m = mg.length; Object.assign(out, { marginPct: r2(mg[m - 1][2]), margin20: m > 20 && mg[m - 21][1] ? r1((mg[m - 1][1] / mg[m - 21][1] - 1) * 100) : null }); }
  const hd = r.hd.filter(x => x[4] <= asof).sort((a, b) => a[0] < b[0] ? -1 : 1);
  if (hd.length) { const h = hd[hd.length - 1]; Object.assign(out, { holdersChg: r1(h[1]), hdate: h[0], focus: h[2], top10free: h[3] == null ? null : Math.round(h[3]) }); }
  out.lift6m = r1(r.lf.reduce((s, x) => s + (x[1] || 0), 0) * 100);
  return out;
}
// 中证全指（逻辑二暂停条件）：在 https://www.csindex.com.cn 任一页面执行
async function csiAll(asof) {
  const s = asof.replace(/-/g, ''), st = String(Number(s.slice(0, 4)) - 1) + s.slice(4);
  const d = await fetch(`/csindex-home/perf/index-perf?indexCode=000985&startDate=${st}&endDate=${s}`).then(r => r.json());
  const rows = []; for (const x of d.data) { const dt = x.tradeDate.slice(0, 4) + '-' + x.tradeDate.slice(4, 6) + '-' + x.tradeDate.slice(6); const wd = new Date(dt + 'T00:00:00Z').getUTCDay(); if (wd === 0 || wd === 6) continue; if (rows.length && rows[rows.length - 1].close === x.close && rows[rows.length - 1].vol === x.tradingVol) continue; rows.push({ date: dt, close: x.close, vol: x.tradingVol }); }
  return rows.map(x => ({ date: x.date, close: x.close }));
}

if (typeof module !== 'undefined') module.exports = { compute };

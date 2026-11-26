// 港股逻辑二（动量＋空头下降）：取数、回测、筛选。在东方财富数据中心页面执行
// （https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_VALUEANALYSIS_DET&pageSize=1）。
// 步骤：1) await hkLoad('2026-11-25')  取港股通名单、港股股本、近两年周收盘、财务（约5—6分钟，进度看 window._hst）
//       2) 在证监会页面算出空头占比分档字符串（见 交接文档 2026-11-26），粘贴为 window._enc
//       3) 回测与筛选用 hkFeat(代码, 周序号) 逐股计算（步骤与分组定义见 更新流程.md 5a、hk_logic2.json backtest）
// 口径：周收盘取每周最后一个交易日；超额收益＝个股13周涨跌−同期全部样本等权平均；财务可见日＝期末+62天（年报+90天）。
async function hkLoad(asof) {
  const all = async q => { let out = [], p = 1; for (;;) { let d; for (let i = 0; i < 5; i++) { try { d = await fetch('/api/data/v1/get?' + new URLSearchParams({ ...q, pageNumber: p })).then(r => r.json()); break } catch (e) { await new Promise(r => setTimeout(r, 2000)) } } const r = (d && d.result) || { data: [], pages: 1 }; out = out.concat(r.data || []); if (p >= (r.pages || 1)) break; p++ } return out };
  const day = s => s.slice(0, 10);
  const t7 = await all({ reportName: 'RPT_MUTUAL_STOCK_HOLDRANKS', columns: 'HOLD_DATE', pageSize: 1000, sortColumns: 'HOLD_DATE', sortTypes: 1, filter: `(MUTUAL_TYPE="002")(INTERVAL_TYPE="1")(SECURITY_CODE="00700")(HOLD_DATE>='2023-09-01')(HOLD_DATE<='${asof}')` });
  const wk = {}; for (const x of t7) { const d = day(x.HOLD_DATE), t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() - ((t.getUTCDay() + 6) % 7)); wk[t.toISOString().slice(0, 10)] = d }
  const W = Object.values(wk).sort(); window._wds = W;
  const uni = await all({ reportName: 'RPT_MUTUAL_STOCK_HOLDRANKS', columns: 'SECURITY_CODE,SECURITY_NAME,INDUSTRY', pageSize: 500, filter: `(MUTUAL_TYPE="002")(INTERVAL_TYPE="1")(HOLD_DATE='${asof}')` });
  window._uni = uni; const codes = uni.map(x => x.SECURITY_CODE);
  const sh = {}; for (let i = 0; i < codes.length; i += 50) { const inn = '(' + codes.slice(i, i + 50).map(c => '"' + c + '"').join(',') + ')'; for (const r of await all({ reportName: 'RPT_HKF10_INFO_ORGPROFILE', columns: 'SECURITY_CODE,HK_SHARES', pageSize: 100, filter: `(SECURITY_CODE in ${inn})` })) sh[r.SECURITY_CODE] = r.HK_SHARES } window._sh = sh;
  const px = {}, ch = []; for (let i = 0; i < W.length; i += 40) ch.push(W.slice(i, i + 40));
  for (let i = 0; i < codes.length; i += 12) { const inn = '(' + codes.slice(i, i + 12).map(c => '"' + c + '"').join(',') + ')'; for (const c of ch) { const dl = '(' + c.map(d => "'" + d + "'").join(',') + ')'; for (const r of await all({ reportName: 'RPT_MUTUAL_STOCK_HOLDRANKS', columns: 'SECURITY_CODE,HOLD_DATE,CLOSE_PRICE', pageSize: 500, filter: `(MUTUAL_TYPE="002")(INTERVAL_TYPE="1")(SECURITY_CODE in ${inn})(HOLD_DATE in ${dl})` })) (px[r.SECURITY_CODE] ??= {})[day(r.HOLD_DATE)] = r.CLOSE_PRICE } window._hst = 'px ' + i }
  window._px = px;
  const F = {}; for (let i = 0; i < codes.length; i += 40) { const inn = '(' + codes.slice(i, i + 40).map(c => '"' + c + '"').join(',') + ')'; for (const r of await all({ reportName: 'RPT_HKF10_FN_MAININDICATOR', columns: 'SECURITY_CODE,REPORT_DATE,REPORT_TYPE,OPERATE_INCOME,GROSS_PROFIT,HOLDER_PROFIT', pageSize: 500, filter: `(SECURITY_CODE in ${inn})(REPORT_DATE>='2024-01-01')` })) (F[r.SECURITY_CODE] ??= []).push([day(r.REPORT_DATE), r.OPERATE_INCOME, r.GROSS_PROFIT, r.HOLDER_PROFIT, r.REPORT_TYPE]); window._hst = 'fin ' + i }
  const S = {}; for (const [c, rs] of Object.entries(F)) { rs.sort((a, b) => a[0] < b[0] ? -1 : 1); S[c] = rs.map((r, k) => { const pv = rs[k - 1]; const gap = pv ? (new Date(r[0]) - new Date(pv[0])) / 864e5 : 999; const cont = pv && gap < 200 && r[1] != null && pv[1] != null && r[1] > pv[1] * 1.05 && !/年报/.test(pv[4] || ''); return cont ? [r[0], r[1] - pv[1], (r[2] ?? 0) - (pv[2] ?? 0), r[3] - pv[3], (r[2] == null || pv[2] == null), r[4]] : [r[0], r[1], r[2], r[3], r[2] == null, r[4]] }) }
  window._fin = S; window._hst = 'done';
}
function hkFeat(c, wi) {
  const W = window._wds, ser = window._px[c] || {}, d = W[wi], p0 = ser[d]; if (!p0) return null;
  const hist = W.slice(Math.max(0, wi - 51), wi + 1).map(w => ser[w]).filter(v => v); if (hist.length < 40) return null;
  const hi = Math.max(...hist), lo = Math.min(...hist);
  const m12 = W.slice(wi - 11, wi + 1).map(w => ser[w]).filter(v => v), m26 = W.slice(wi - 25, wi + 1).map(w => ser[w]).filter(v => v);
  const avg = a => a.reduce((s, v) => s + v, 0) / a.length; const p26 = ser[W[wi - 26]];
  const avail = x => { const t = new Date(x + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + (x.slice(5) === '12-31' ? 90 : 62)); return t.toISOString().slice(0, 10) };
  const s = (window._fin[c] || []).filter(x => avail(x[0]) <= d); const npUp = s.length >= 2 ? s.at(-1)[3] >= s.at(-2)[3] && s.at(-1)[3] > 0 : null;
  return { p0, dd: p0 / hi - 1, pos: (p0 - lo) / (hi - lo), vs12: p0 / avg(m12) - 1, vs26: p0 / avg(m26) - 1, r26: p26 ? p0 / p26 - 1 : null, npUp, mc: (window._sh[c] || 0) * p0 / 1e8 };
}

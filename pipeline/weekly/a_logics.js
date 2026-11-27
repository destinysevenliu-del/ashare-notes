// 2026-11-26 新增逻辑的浏览器取数与回测（在东方财富数据中心页面执行，datacenter-web.eastmoney.com）。
// 依赖 hk_momentum.js 的 hkLoad/hkFeat（港股部分）。步骤见 更新流程.md 3b。
// A股：aLoad() 取周收盘（RPT_VALUEANALYSIS_DET，总市值≥50亿）、业绩报表、分红、研报预测；aPrep() 整理；aRunM() 回测（超额＝个股−同期中位数）。
async function _all(q) { let out = [], p = 1; for (;;) { let d; for (let i = 0; i < 5; i++) { try { d = await fetch('/api/data/v1/get?' + new URLSearchParams({ ...q, pageNumber: p })).then(r => r.json()); break } catch (e) { await new Promise(r => setTimeout(r, 2000)) } } const r = (d && d.result) || { data: [], pages: 1 }; out = out.concat(r.data || []); if (p >= (r.pages || 1)) break; p++ } return out }
async function aLoad(from, to) {
  const t = await _all({ reportName: 'RPT_VALUEANALYSIS_DET', columns: 'TRADE_DATE', pageSize: 500, filter: `(SECURITY_CODE="000001")(TRADE_DATE>='${from}')(TRADE_DATE<='${to}')`, sortColumns: 'TRADE_DATE', sortTypes: 1 });
  const wk = {}; for (const x of t) { const d = x.TRADE_DATE.slice(0, 10), tt = new Date(d + 'T00:00:00Z'); tt.setUTCDate(tt.getUTCDate() - ((tt.getUTCDay() + 6) % 7)); wk[tt.toISOString().slice(0, 10)] = d }
  const W = Object.values(wk).sort(); window._awds = W; const P = {}, I = {}, S = {}, N = {}, M = {};
  for (let i = 0; i < W.length; i++) { for (const r of await _all({ reportName: 'RPT_VALUEANALYSIS_DET', columns: 'SECURITY_CODE,SECURITY_NAME_ABBR,BOARD_NAME,CLOSE_PRICE,TOTAL_MARKET_CAP,TOTAL_SHARES', pageSize: 500, filter: `(TRADE_DATE='${W[i]}')(TOTAL_MARKET_CAP>=5000000000)` })) { (P[r.SECURITY_CODE] ??= {})[W[i]] = r.CLOSE_PRICE; (S[r.SECURITY_CODE] ??= {})[W[i]] = r.TOTAL_SHARES; (M[r.SECURITY_CODE] ??= {})[W[i]] = r.TOTAL_MARKET_CAP; I[r.SECURITY_CODE] = r.BOARD_NAME; N[r.SECURITY_CODE] = r.SECURITY_NAME_ABBR } window._aps = 'w' + i + '/' + W.length }
  Object.assign(window, { _apx: P, _ash: S, _amc: M, _aind: I, _anm: N });
  window._abon = (await _all({ reportName: 'RPT_SHAREBONUS_DET', columns: 'SECURITY_CODE,PRETAX_BONUS_RMB,EX_DIVIDEND_DATE', pageSize: 500, filter: `(EX_DIVIDEND_DATE>='${from}')` })).map(r => [r.SECURITY_CODE, r.EX_DIVIDEND_DATE && r.EX_DIVIDEND_DATE.slice(0, 10), r.PRETAX_BONUS_RMB]);
  window._alico = (await _all({ reportName: 'RPT_LICO_FN_CPD', columns: 'SECURITY_CODE,REPORTDATE,NOTICE_DATE,PARENT_NETPROFIT,TOTAL_OPERATE_INCOME,SJLTZ,YSTZ,BPS,MGJYXJJE,BASIC_EPS', pageSize: 500, filter: `(REPORTDATE>='${from.slice(0, 4) - 1}-03-31')` })).map(r => [r.SECURITY_CODE, r.REPORTDATE.slice(0, 10), r.NOTICE_DATE && r.NOTICE_DATE.slice(0, 10), r.PARENT_NETPROFIT, r.TOTAL_OPERATE_INCOME, r.SJLTZ, r.YSTZ, r.BPS, r.MGJYXJJE, r.BASIC_EPS]);
  window._aps = 'done';
}
function aPrep() { // 单季利润同比：累计数倒推单季，与上年同季比较；以公告日为可见日
  const L = {}; for (const r of window._alico) (L[r[0]] ??= []).push(r); const Q = {};
  for (const c in L) { const rs = L[c].sort((a, b) => a[1] < b[1] ? -1 : 1), by = {}; for (const r of rs) by[r[1]] = r;
    const out = rs.map(r => { const y = r[1].slice(0, 4), pm = { '03-31': null, '06-30': '03-31', '09-30': '06-30', '12-31': '09-30' }[r[1].slice(5)], pr = pm ? by[y + '-' + pm] : null; return [r[1], r[2] || r[1], pm ? (pr && r[3] != null && pr[3] != null ? r[3] - pr[3] : null) : r[3]] });
    const bq = {}; for (const o of out) bq[o[0]] = o;
    Q[c] = out.map(o => { const ly = bq[(+o[0].slice(0, 4) - 1) + o[0].slice(4)]; let g = null; if (ly && o[2] != null && ly[2] != null && ly[2] !== 0) g = (o[2] - ly[2]) / Math.abs(ly[2]) * 100; return [o[0], o[1], o[2], g] }) }
  window._aq = Q; const D = {}; for (const r of window._abon) if (r[1] && r[2]) (D[r[0]] ??= []).push([r[1], r[2] / 10]); window._AD = D;
}
function aFeat(c, wi) { const W = window._awds, ser = window._apx[c] || {}, d = W[wi], p0 = ser[d]; if (!p0) return null; const h = W.slice(Math.max(0, wi - 51), wi + 1).map(w => ser[w]).filter(v => v); if (h.length < 20) return null;
  const avg = a => a.reduce((s, v) => s + v, 0) / a.length, m12 = W.slice(wi - 11, wi + 1).map(w => ser[w]).filter(v => v), m26 = W.slice(Math.max(0, wi - 25), wi + 1).map(w => ser[w]).filter(v => v), p26 = ser[W[wi - 26]];
  return { p0, dd: p0 / Math.max(...h) - 1, vs12: p0 / avg(m12) - 1, vs26: p0 / avg(m26) - 1, r26: p26 ? p0 / p26 - 1 : null, mc: ((window._amc[c] || {})[d] || 0) / 1e8, sh: (window._ash[c] || {})[d] } }
function aTtm(c, d, back = 0) { const a = new Date(d + 'T00:00:00Z'); a.setUTCDate(a.getUTCDate() - back); const b = new Date(a); b.setUTCDate(b.getUTCDate() - 365); const hi = a.toISOString().slice(0, 10), lo = b.toISOString().slice(0, 10); return (window._AD[c] || []).filter(x => x[0] <= hi && x[0] > lo).reduce((s, x) => s + x[1], 0) }
function aRunM(dates, groups) { // 持有13周；持有期股本变动超过5%的样本剔除；超额＝个股−同期中位数
  const W = window._awds, codes = Object.keys(window._apx), G = {}; for (const g in groups) G[g] = [];
  for (const d of dates) { const wi = W.indexOf(d); if (wi < 0 || wi + 13 >= W.length) continue; const rows = [];
    for (const c of codes) { const f = aFeat(c, wi); if (!f || f.mc < 100) continue; const p1 = window._apx[c][W[wi + 13]], s1 = (window._ash[c] || {})[W[wi + 13]]; if (!p1 || !s1 || !f.sh || Math.abs(s1 / f.sh - 1) > 0.05) continue; rows.push([c, f, p1 / f.p0 - 1]) }
    const s = rows.map(r => r[2]).sort((a, b) => a - b), m = s[Math.floor(s.length / 2)]; for (const [c, f, r] of rows) for (const g in groups) if (groups[g](c, f, d)) G[g].push(r - m) }
  const st = a => { if (!a.length) return [0, 0, 0, 0]; const s = [...a].sort((x, y) => x - y); return [a.length, +(a.reduce((p, v) => p + v, 0) / a.length * 100).toFixed(1), +(s[Math.floor(s.length / 2)] * 100).toFixed(1), Math.round(a.filter(v => v > 0).length / a.length * 100)] };
  const o = {}; for (const g in G) o[g] = st(G[g]); return o }
// A股业绩反转规则：q=单季序列（公告日≤检验日），q[-1]同比>0、q[-2]同比<0、本季盈利；vs26≤0；dd>-25%
function aTurnRule(c, f, d) { const q = (window._aq[c] || []).filter(x => x[1] <= d && x[3] != null); if (q.length < 2) return false; const a = q.at(-1), b = q.at(-2); return a[3] > 0 && b[3] < 0 && a[2] > 0 && f.vs26 <= 0 && f.dd > -0.25 }
// 港股：分红与回购
function hkDps(s) { if (!s) return null; let m = s.match(/港币\s*([\d.]+)\s*元/); return m ? +m[1] : null }
async function hLoad(from, codes) {
  window._hbb = (await _all({ reportName: 'RPT_HK_BUYBACK', columns: 'SECURITY_CODE,TRADE_DATE,REPO_AMT,REPO_NUM,REPO_NUM_PCG,CURRENCY', pageSize: 500, filter: `(TRADE_DATE>='${from}')` }));
  const hd = []; for (let i = 0; i < codes.length; i += 50) { const inn = '(' + codes.slice(i, i + 50).map(c => '"' + c + '"').join(',') + ')'; for (const r of await _all({ reportName: 'RPT_HKF10_INFO_DIVIDEND', columns: 'SECURITY_CODE,EX_DIVIDEND_DATE,PLAN_EXPLAIN', pageSize: 500, filter: `(SECURITY_CODE in ${inn})(EX_DIVIDEND_DATE>='${from}')` })) { const v = hkDps(r.PLAN_EXPLAIN); if (v != null && r.EX_DIVIDEND_DATE) hd.push([r.SECURITY_CODE, r.EX_DIVIDEND_DATE.slice(0, 10), v]) } }
  const D = {}; for (const r of hd) (D[r[0]] ??= []).push([r[1], r[2]]); window._HD = D;
  const B = {}; for (const r of window._hbb) { if (r.CURRENCY !== 'HKD') continue; (B[r.SECURITY_CODE] ??= []).push([r.TRADE_DATE.slice(0, 10), r.REPO_AMT || 0, r.REPO_NUM || 0]) } window._HB = B;
}
function hTtm(c, d) { const t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() - 365); const lo = t.toISOString().slice(0, 10); return (window._HD[c] || []).filter(x => x[0] <= d && x[0] > lo).reduce((s, x) => s + x[1], 0) }
function hBB(c, d, days = 91) { const t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() - days); const lo = t.toISOString().slice(0, 10); const xs = (window._HB[c] || []).filter(x => x[0] <= d && x[0] > lo); const amt = xs.reduce((s, x) => s + x[1], 0), num = xs.reduce((s, x) => s + x[2], 0); return { amt, n: xs.length, avg: num ? amt / num : null } }

> WITHDRAWN: The three-sector-first scope was rejected by the user. Superseded by the market-first correction in research/macro-first-correction-2026-11-27.md. Retained only as history.

# Focus decision interface Implementation Plan

Approved scope: user accepted the preceding design and requested implementation and existing publication workflow.

**Goal:** Three focus directions, one final action, independently justified price references, explicit completion checks.
**Architecture:** `focus_decisions.py` owns sector decisions and presentation from `focus_decisions.json` and dated source snapshots. Existing macro research remains collapsible. Existing stock strategies retain risk gates; card presentation uses a single action classifier.
**Tech Stack:** Python static renderer, JSON, semantic HTML/CSS, unittest, Playwright.

## Global constraints
- Preserve quarterly stock membership and market defense / recovery rules.
- No individual-stock analysis on new focus sector pages; no fabricated loss-holder counts.
- No total score combining fundamentals, position and financing.
- Risk references cannot be chosen to force a minimum reward/risk ratio.
- Current observations dated November 27; stale or absent series stay explicit.
- Work in isolated staging directory; publish through original API publisher after all checks.

## Tasks
- [x] 1. Create data contract and decision engine. Functions `decide(item, market)` returns {status, reason, next}; precedence invalid thesis, market pause, missing required evidence, entry conditions, ready. Cover each branch and missing price data in unittest before implementation.
- [x] 2. Build position observations from fixed industry indices with dated close, prior close, 52-week range and 60-day reference. Use daily turnover by close-bin only as historical activity proxy, never account costs. HK absent series explicitly missing, do not substitute bank observations. Save raw data and calculation method.
- [x] 3. Render three-direction table, detail pages, collapsed archives, dated policy watch and completion checklists. Insert table before research on both homepages. Focus pages use single primary valuation and ordered transmission chains. Other sector pages retain archive links and risk evidence.
- [x] 4. Stock cards: map original final decision to one primary action; neutralize positional badges. Add validated valuation review contract with metric, price basis, range, dates, source and normalized denominator; expired or missing evidence stays pending with explicit completion criteria. Growth targets use independent range mid / 95% high references, removing forced 2R floor. Preserve entry/stop rules. Test blocked cards and low/negative RR.
- [ ] 5. Build and run all test suites; check desktop screenshots, archived links and shared action state. Update handoff/workflow, hash changes, back up modified original files, publish and verify GitHub Pages and live file hashes.

Decision contract example: `decide({"thesis_valid":True,"missing":["PB history"],"entry_met":False}, {"paused":True,"reason":"recovery incomplete"})` returns status 暂停新增, retaining PB history in next steps. An approved valuation must have positive current price and denominator, explicit primary metric, dated evidence and ordered bounds; PB historical veto remains independent.

Validation: 14 suites / 90 tests passed; 18 desktop pages without horizontal overflow or script errors; all local link targets resolve. Publication verification is the remaining step.

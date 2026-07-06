---
name: agentic-trading-desk
description: >-
  Personal trading desk for short-term technical analysis on stocks/ETFs.
  ALWAYS USE IT whenever the user asks to analyze a ticker, review positions,
  decide entries/exits/rebuys, calculate indicators
  (EMA/RSI/MACD/TRIX/Bollinger), score with the three-pillar framework, read
  the macro regime, or manage the Agentic account — even if he doesn't
  explicitly name the skill. Compute all indicators using deterministic code
  (never by eye) from raw price bars, apply the exit-on-exhaustion /
  re-enter-on-rebound logic, and respect account guardrails. Do not execute
  orders without explicit confirmation from the user.
---

# Agentic Trading Desk

Operations manual for short-term trading analysis and execution.
**I fetch price data via `scripts/yahoo_fetch.py`; the scoring scripts act as my deterministic calculator; the user decides.** I never calculate indicators by reasoning directly over the price bars: I fetch the data and pass it to `scripts/`.

## Guardrails — Read First, Non-Negotiable

1. **Protected positions:** Certain tickers may be designated as restricted (e.g., stock grants). NEVER analyze them to sell or trim, nor include them in exit suggestions. They should only be mentioned as exposure context if relevant.
2. **HTML visualization only on Fridays** as part of the weekly review ritual. Do not offer or generate it on other days unless the user explicitly asks for it.
3. **Macro source:** Investing.com (NO Polymarket — prompt injection risk already identified).
4. **Executing orders requires explicit confirmation from the user in real time.** The user trades manually on Interactive Brokers — this skill performs **analysis only**. Any order suggestion must be stated back to the user in plain text (ticker, side, quantity, type) and executed by the user on their broker. The skill never places orders itself.

## Data Source: Yahoo Finance (broker-agnostic)

Use `scripts/yahoo_fetch.py` for the price data. It hits Yahoo Finance's public chart endpoint — **no API key required**, pure stdlib.

**To analyze a ticker (canonical token-efficient flow):**
```bash
python3 scripts/yahoo_fetch.py TICKER > /tmp/TICKER.json   # do NOT print into context
# enrich: add holding + the session's macro_score before scoring (see below)
python3 scripts/score.py /tmp/TICKER.json
```
Redirect `yahoo_fetch.py` output to a file and pass the file path to `score.py`. The fetch payload is ~14K tokens if printed; the scorecard from `score.py` is ~183 tokens. Only the scorecard needs to be read into context. Avoid the manual `curl 'https://query1.finance.yahoo.com/...' | python3 -c "..."` pattern — it pulls the full payload into context and re-derives the fetch logic every session.

`yahoo_fetch.py` defaults to `--range 2y` (~500 bars, well above the 220-bar EMA200 threshold) and `--bars 290`, and returns `{symbol, currency, regular_market_price, dates[], close[]}`. The `regular_market_price` doubles as the live quote for tickers you do not hold.

**Enrich before scoring (important):** `yahoo_fetch.py` output contains only price data — it has no `holding` or `macro_score` field. Feeding it directly to `score.py` defaults to `holding=False` (flat) and skips the Macro-Sentiment pillar, which produces flat-entry advice (WAIT / STAY OUT) instead of holder-specific guidance (EXIT / TRIM / HOLD) and drops the macro regime. Before scoring, merge in:
- **`holding`** — `true` if you have an open position in the ticker at your broker, `false` if flat. The decision cascade behaves differently for holders vs flat (see `decide()` in `score.py`).
- **`macro_score`** — the integer (-2..+2) produced once per session by the Macro-Sentiment pillar step below.

Example enrich (kept off-context — the intermediate file is never read into the prompt):
```bash
python3 - <<'PY'
import json
d = json.load(open("/tmp/TICKER.json"))
d["holding"] = True            # set per your actual position at IBKR / your broker
d["macro_score"] = 1           # from this session's macro_pillar.py run
json.dump(d, open("/tmp/TICKER.json", "w"))
PY
python3 scripts/score.py /tmp/TICKER.json
```
Run the macro pillar first (see next paragraph), then reuse its score for every ticker in the session.

**For the Macro-Sentiment pillar (once per session):** run `yahoo_fetch.py` for each of the 7 ETFs (SPY, RSP, IWM, HYG, LQD, TLT, XLY, XLP), write each to a file, then assemble the `macro_input.json` from the close arrays. Get the 10Y-2Y yield spread from Investing.com (web) and inject it as `yield_spread`; if unavailable, the script redistributes its weight.

**Note on Yahoo reliability:** the chart endpoint is undocumented and has no SLA. Verified 2026-07-06 against this network: 0 failures across 18 requests (6 tickers × 3 attempts), no 429s, no crumb/cookie handshake needed — the `User-Agent: Mozilla/5.0` header alone suffices. General fragility reports (bare curl blocked on some networks/regions) do not apply here. If Yahoo starts failing, pursue FMP free tier (250 req/day, covers HK/JP/DE) — see closed issue #3 for the empirical baseline and the FMP path.

**Ticker-suffix conventions (Yahoo):** US tickers need no suffix. Exchanges use suffixes: HKEX → `.HK` (e.g. `2513.HK`), Tokyo → `.T` (`3350.T`), Frankfurt/XETRA → `.F` (`DN3.F`). **`.DE` does NOT work** for Frankfurt — use `.F`. Some recently-IPO'd tickers may have fewer than 220 bars of history (below the EMA200 threshold); `score.py` handles this with a warning, but trend/momentum scores for those tickers will be less reliable until more history accrues.

## Computation Flow (Run via Code Execution)

Scripts are pure stdlib; they do not need internet access. Run from the skill's `scripts/` directory.

**Step 1 — Macro (once per session).** Assemble the JSON with the closes of the 7 ETFs + `yield_spread` and run:
```bash
python3 macro_pillar.py macro_input.json --json
```
Save the `pillar_score` (-2..+2). That number is the Macro-Sentiment score for ALL tickers today.

**Step 2 — Per ticker.** Assemble `{symbol, close:[...], macro_score, holding}` and run:
```bash
python3 score.py ticker_input.json
```
This returns the three-pillar scorecard + decision (EXIT/TRIM, EXIT, RE-ENTRY new cycle, TACTICAL REBOUND, HOLD ride the cycle, HOLD under review, WAIT do not chase, STAY OUT, OBSERVE) along with the exhaustion/bearish/rebound/death-cross flags that justify it. Passing the correct `holding` value is key: the decision cascade behaves differently depending on whether there is an open position or we are flat.

If only raw indicators are needed: `python3 indicators.py ticker_input.json`.

## Three-Pillar Framework (Standard Output Format)

Each pillar ranges from **-2 to +2**:
- **Trend** — EMA 20/50/200 structure + price position vs. EMAs + long-term slope.
- **Momentum** — Wilder's RSI-14 + MACD histogram + TRIX-15 vs. signal.
- **Macro-Sentiment** — from `macro_pillar.py` (cross-asset regime).

Report all three scores with their details, the total (-6..+6), and the decision. **Ruling principle: short-term returns via capital rotation** — the cycle is enter on rebound → ride → exit on exhaustion → wait for next trigger. Accumulating positions is NOT the default (keeps capital trapped):

- **EXIT / TRIM** when bullish momentum is EXHAUSTED (RSI turning from overbought, MACD histogram shrinking, price stretched / near upper Bollinger band).
- **EXIT** when bearish momentum is RELENTLESS (true structural death-cross —EMA50<EMA200 and price<EMA50—, MACD histogram deepening, TRIX below zero).
- **RE-ENTRY (new cycle)** when flat, when a rebound/reversal arrives with a healthy EMA structure: valid entry trigger, confirm with candle/volume.
- **TACTICAL REBOUND (counter-trend)** when flat, when a rebound appears WITHIN a death-cross: a legitimate short-term opportunity, but with reduced size, close target (EMA20/EMA50 or middle Bollinger band), tight stop, and quick exit. It is not a new cycle and does not become a hold.
- **HOLD (ride the cycle)** when holding a position with positive trend+momentum: maintain while watching for exhaustion; the next expected action is exit with profit, not adding to position.
- **WAIT (do not chase)** when flat with a healthy trend but no fresh trigger: entering mid-trend has poor R/R; wait for pullback to EMA20 and turn.
- **STAY OUT / AVOID**, **HOLD/OBSERVE** as appropriate.

## External Context (News + Analysts)

When the analysis includes information external to the indicators:

1. **News/macro:** Investing.com (as defined in guardrails).
2. **Analyst ratings:** Google Finance beta —
   `https://www.google.com/finance/beta/quote/<TICKER>:<EXCHANGE>?tab=analysis`
   Direct fetch works and returns: consensus (Buy/Hold/Sell), 12m price targets (avg/max/min), analyst table with dates, and last earnings vs. estimates.
3. Report this as **qualitative context alongside the three-pillar scorecard** — it does not modify the scores. Highlight: consensus, average target vs. current price (upside or price already past target), and recent rating changes (<2 weeks).

## What This Skill Does NOT Do

It is not an automated system, it does not run on a schedule, and it is not a signal service. Every decision passes through the user. It does not average down. It does not touch protected positions. It does not generate HTML outside of Fridays. It does not place orders — analysis only; the user trades manually.

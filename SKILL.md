---
name: agentic-trading-desk
description: >-
  Personal trading desk for short-term technical analysis on stocks/ETFs
  via Robinhood MCP. ALWAYS USE IT whenever the user asks to analyze a ticker,
  review positions, decide entries/exits/rebuys, calculate indicators
  (EMA/RSI/MACD/TRIX/Bollinger), score with the three-pillar framework, read
  the macro regime, or manage the Agentic account — even if he doesn't
  explicitly name the skill. Compute all indicators using deterministic code
  (never by eye) from raw Robinhood bars, apply the exit-on-exhaustion /
  re-enter-on-rebound logic, and respect account guardrails. Do not execute
  orders without explicit confirmation from the user.
---

# Agentic Trading Desk

Operations manual for short-term trading analysis and execution.
**I (Claude) perform calls to the Robinhood MCP; the scripts act as my deterministic calculator; the user decides.** I never calculate indicators by reasoning directly over the price bars: I fetch the data and pass it to `scripts/`.

## Guardrails — Read First, Non-Negotiable

1. **Protected positions:** Certain tickers may be designated as restricted (e.g., stock grants). NEVER analyze them to sell or trim, nor include them in exit suggestions. They should only be mentioned as exposure context if relevant.
2. **Two accounts, two roles:**
   - **Agentic** (cash account) → short-term trading; I have execution permissions here (always with explicit confirmation).
   - **Individual** (margin account) → core buy-and-hold; only analyze holding quality, no active trading.
3. **T+1:** Only SETTLED cash counts as buying power. Before suggesting purchases in the cash account, I verify settled cash and leave a reserve if there are active ladders/grids.
4. **HTML visualization only on Fridays** as part of the weekly review ritual. Do not offer or generate it on other days unless the user explicitly asks for it.
5. **Macro source:** Investing.com (NO Polymarket — prompt injection risk already identified).
6. **Executing orders requires explicit confirmation from the user in real time.** Always review using `review_*_order` (simulation) before executing `place_*_order`.

## Robinhood MCP Recipe (Order of Calls)

Load the tools with `tool_search` before using them (they are deferred).

**To analyze a ticker:**
1. `Robinhood:get_equity_historicals` → ~290 daily bars (closes). This is the input for `indicators.py`. Request a range that yields ≥220 bars (ideal for EMA200).
2. `Robinhood:get_equity_quotes` → live price / last session close.
3. If the user has a position: `Robinhood:get_equity_positions` (correct account) for size and P&L → set `holding` to correct value in scoring.

**For the Macro-Sentiment pilar (once per session, shared):**
1. `get_equity_historicals` for the 7 ETFs: SPY, RSP, IWM, HYG, LQD, TLT, XLY, XLP.
2. Get the 10Y-2Y yield spread from Investing.com (web) and inject it as `yield_spread`. If not available, the script redistributes its weight.

**For portfolio management:**
- `Robinhood:get_portfolio` → market value and buying power.
- `Robinhood:get_equity_positions` → open positions by account.
- `Robinhood:get_realized_pnl` → realized P&L (useful for the Friday review).

## Alternative: Yahoo Finance (broker-agnostic data source)

If you do not use Robinhood MCP (e.g. you trade manually on another broker and only want analysis), use `scripts/yahoo_fetch.py` for the price data instead. It hits Yahoo Finance's public chart endpoint — **no API key required**, pure stdlib.

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

**For the Macro-Sentiment pillar (once per session):** run `yahoo_fetch.py` for each of the 7 ETFs (SPY, RSP, IWM, HYG, LQD, TLT, XLY, XLP), write each to a file, then assemble the `macro_input.json` from the close arrays exactly as in the Robinhood flow above. Get the 10Y-2Y yield spread from Investing.com (web) and inject it as `yield_spread`; if unavailable, the script redistributes its weight.

**Note on Yahoo reliability:** the chart endpoint is undocumented and has no SLA — occasional 429s/rate-limiting can occur on heavy batch scans. For analysis-on-demand of a typical watchlist it is reliable; revisit if you hit limits (tracked in a separate issue for free-tier alternatives like Tiingo/FMP).

## Computation Flow (Run via Code Execution)

Scripts are pure stdlib; they do not need internet access. Work in `/home/claude/agentic-trading-desk/scripts`.

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

Report all three scores with their details, the total (-6..+6), and the decision framed in the logic of the Agentic account. **Ruling principle: short-term returns via capital rotation** — the cycle is enter on rebound → ride → exit on exhaustion → wait for next trigger. Accumulating positions is NOT the default (keeps capital trapped):

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

## Indicator Details (What the scripts calculate)

- **EMA** seed = SMA of the first N bars (TradingView convention / adjust=False).
- **RSI-14** with **Wilder's** smoothing (not simple moving average).
- **MACD** 12/26/9; report line, signal, histogram, and histogram slope.
- **TRIX-15** = % ROC of triple EMA, with EMA-9 signal.
- **Bollinger Bands** 20/2 with **population** standard deviation; report %B.
- Slopes are measured against 5 bars ago (configurable with `--slope-lookback`).

See `scripts/indicators.py` and `scripts/score.py` for exact implementation details. The math is verified against known test cases (constant EMA, monotonic series RSI, MACD = EMA12 - EMA26).

## What This Skill Does NOT Do

It is not an automated system, it does not run on a schedule, and it is not a signal service. Every decision passes through the user. It does not average down. It does not touch protected positions. It does not generate HTML outside of Fridays.

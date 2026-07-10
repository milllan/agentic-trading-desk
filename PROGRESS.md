# Progress

## Status: 🟢 Yahoo Finance data-source integration complete (PR pending merge)

Forked from `Oft3r/agentic-trading-desk`. Added Yahoo Finance as a broker-agnostic alternative to Robinhood MCP for analysis-only users. No account/order-execution changes.

### What's Done
- [x] Forked `Oft3r/agentic-trading-desk` → `milllan/agentic-trading-desk`
- [x] Feature branch `feat/yahoo-finance-data-source` created
- [x] `scripts/yahoo_fetch.py` added (cherry-picked from antrophy fork, verbatim)
- [x] Comment fixes in `indicators.py` + `macro_pillar.py` (Robinhood → Yahoo Finance)
- [x] `SKILL.md` — Yahoo Finance alternative section (token-efficient flow documented)
- [x] `README.md` — mermaid diagram + File Structure + Script Usage updated
- [x] `CHANGELOG.md` + `PROGRESS.md` added
- [x] End-to-end smoke test: `yahoo_fetch.py AAPL > /tmp/aapl.json` → `score.py /tmp/aapl.json`
- [x] PR opened on fork for code-review bots
- [x] Issues filed for future work (IBKR integration, alt data sources)

### Architecture
Unchanged from upstream's 3-layer design (Directive = SKILL.md, Orchestration = the agent, Execution = the Python scripts). This fork adds a **broker-agnostic data-ingest** option at the execution layer:

```
yahoo_fetch.py  →  {symbol, close[], price}  →  score.py / indicators.py / macro_pillar.py
                  (file on disk, not in                (deterministic math, unchanged)
                   agent context)
```

The Robinhood MCP path remains the default and is fully preserved.

### Next Steps
- **IBKR trading integration** — read positions + manual-confirm order placement via Interactive Brokers TWS/IB Gateway API. Tracked in [#2](https://github.com/milllan/agentic-trading-desk/issues/2). Future enhancement, not blocking.
- **Alternative data sources** — investigate free-tier APIs (Tiingo/FMP) as a fallback to Yahoo's undocumented endpoint if rate-limiting becomes a problem at watchlist scale. Tracked in [#3](https://github.com/milllan/agentic-trading-desk/issues/3).
- **Sync installed skill** — after the PR merges to `main`, sync the skill at `~/.codex/skills/agentic-trading-desk/` from this fork (separate small task).

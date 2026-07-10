# Changelog

## v1.1.1 — 2026-07-06

### Fixed
- `scripts/yahoo_fetch.py` — defensive parsing for malformed Yahoo responses (Gemini Code Assist review, HIGH). Catches `json.JSONDecodeError` (HTML captcha/error pages), uses safe `.get()` navigation, and validates `timestamps`/`closes` are non-empty before `zip()`. All error paths now raise clean `SystemExit` messages instead of uncaught exceptions. Happy path output unchanged.
- `SKILL.md` — documented the `holding`/`macro_score` enrich step in the Yahoo flow (Codex review, P1). The canonical flow previously fed `yahoo_fetch.py` output directly to `score.py`, defaulting to `holding=False` and skipping the Macro-Sentiment pillar — producing flat-entry advice instead of holder-specific guidance. Verified: identical AAPL data returns HOLD (enriched) vs WAIT (unenriched).

## v1.1.0 — 2026-07-06

### Added
- `scripts/yahoo_fetch.py` — broker-agnostic price-history fetcher (Yahoo Finance public chart endpoint, no API key). Cherry-picked from the [antrophy fork](https://github.com/antrophy/agentic-trading-desk).
- Yahoo Finance as an **alternative data source** alongside Robinhood MCP in `SKILL.md` ("Alternative: Yahoo Finance" section). Documents the canonical token-efficient flow (`yahoo_fetch.py TICKER > /tmp/x.json` → `score.py /tmp/x.json`) and explicitly discourages the manual `curl | python3 -c` pattern that pulls the full ~14K-token Yahoo payload into context.
- "Fetch Price Data" subsection in `README.md` Script Usage.
- Yahoo Finance node in the README mermaid architecture diagram.
- `CHANGELOG.md` and `PROGRESS.md` (this file).

### Changed
- `scripts/indicators.py`, `scripts/macro_pillar.py` — comment-only fixes: "Robinhood" → "Yahoo Finance" in docstrings (math unchanged).
- `README.md` File Structure list now includes `scripts/yahoo_fetch.py`.

### Reasoning & Architecture Notes
- **Why Yahoo:** the original skill assumes Robinhood MCP, which excludes users on other brokers (IBKR, T212, etc.). Yahoo's public chart endpoint needs no key and returns clean daily closes — enough to feed the deterministic indicator/scoring engines for analysis-only use cases.
- **Scope discipline:** this PR touches the **data-source layer only**. No changes to `score.py`, no changes to the three-pillar math, no changes to guardrails or order-execution logic. Robinhood MCP remains the documented default; Yahoo is additive.
- **Token efficiency:** measured against a prior session where the agent fetched Yahoo data manually via `curl | python3 -c`, redirecting `yahoo_fetch.py` output to a file cuts per-ticker context cost from ~14K tokens (raw payload) to ~183 tokens (scorecard only) — roughly a 75–85× reduction.

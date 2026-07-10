#!/usr/bin/env python3
"""
yahoo_fetch.py
==============
Fetches daily OHLC bars + a near-live quote from Yahoo Finance's public
chart endpoint, since the Trading212 API does not provide historical price
bars or quotes for arbitrary (non-held) tickers. This replaces the old
Robinhood MCP `get_equity_historicals` / `get_equity_quotes` calls as the
input source for indicators.py / score.py / macro_pillar.py.

No API key needed. (Stooq was tried first but now gates its CSV export
behind a JS proof-of-work bot-check that plain HTTP clients can't pass.)

stdlib only. Python 3.9+.
"""
from __future__ import annotations
import argparse
import json
import sys
import urllib.error
import urllib.request

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_}&interval={interval}"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_bars(ticker: str, range_: str = "2y", interval: str = "1d", bars: int = 290) -> dict:
    url = CHART_URL.format(ticker=ticker, range_=range_, interval=interval)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Yahoo fetch failed for {ticker}: HTTP {e.code}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Yahoo fetch failed for {ticker}: {e}")
    except json.JSONDecodeError as e:
        # Yahoo sometimes returns an HTML error/captcha page instead of JSON.
        raise SystemExit(f"Yahoo returned invalid JSON for {ticker}: {e}")

    result = payload.get("chart", {}).get("result")
    if not result:
        err = payload.get("chart", {}).get("error")
        raise SystemExit(f"Yahoo returned no data for {ticker}: {err}")

    r = result[0]
    meta = r.get("meta") or {}
    timestamps = r.get("timestamp")
    indicators = r.get("indicators") or {}
    quote_list = indicators.get("quote") or []
    quote = quote_list[0] if quote_list else {}
    closes = quote.get("close")

    if not timestamps or not closes:
        raise SystemExit(f"Yahoo returned no price history or timestamps for {ticker}")

    dates, clean_closes = [], []
    for ts, c in zip(timestamps, closes):
        if c is None:
            continue
        dates.append(ts)
        clean_closes.append(float(c))

    return {
        "symbol": ticker.upper(),
        "currency": meta.get("currency"),
        "regular_market_price": meta.get("regularMarketPrice"),
        "dates": dates[-bars:],
        "close": clean_closes[-bars:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch daily closes + live quote from Yahoo Finance for indicators.py/score.py.")
    ap.add_argument("ticker")
    ap.add_argument("--range", dest="range_", default="2y", help="Yahoo range param, e.g. 1y/2y/5y")
    ap.add_argument("--bars", type=int, default=290)
    args = ap.parse_args()

    result = fetch_bars(args.ticker, range_=args.range_, bars=args.bars)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

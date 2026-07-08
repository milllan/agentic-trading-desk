"""Deterministic synthetic market data for benchmarks.

Generates realistic-sized close-price series (~290 daily bars, enough to warm up
the EMA-200 stack) so the benchmarks exercise the full indicator/scoring path
rather than early-return warmup branches.
"""
from __future__ import annotations

import math


def close_series(n: int = 290, base: float = 100.0, seed: float = 0.0) -> list[float]:
    """A trending series with a sinusoidal ripple, like a real uptrend."""
    return [round(base + 18 * math.sin(i / 22 + seed) + i * 0.06, 2) for i in range(n)]


def exhausted_series(n: int = 260) -> list[float]:
    """Bullish series stretching toward a ceiling plus a final blow-off spike."""
    close = [round(100 + i * 0.25 + 6 * math.sin(i / 12), 2) for i in range(n)]
    close += [close[-1] * 1.05, close[-1] * 1.10]
    return close


def _geometric(n: int, start: float, drift: float, noise_seed: float) -> list[float]:
    out, v = [], start
    for i in range(n):
        v *= 1 + drift + 0.004 * math.sin(i / 9 + noise_seed)
        out.append(round(v, 2))
    return out


def macro_payload(n: int = 260) -> dict:
    """Full cross-asset payload for macro_pillar.score_macro."""
    return {
        "as_of": "2026-07-02",
        "series": {
            "SPY": _geometric(n, 400, 0.0006, 1),
            "RSP": _geometric(n, 150, 0.0009, 2),
            "IWM": _geometric(n, 180, 0.0011, 3),
            "HYG": _geometric(n, 75, 0.0004, 4),
            "LQD": _geometric(n, 105, 0.0001, 5),
            "TLT": _geometric(n, 95, -0.0003, 6),
            "XLY": _geometric(n, 190, 0.0008, 7),
            "XLP": _geometric(n, 78, 0.0002, 8),
        },
        "yield_spread": [round(-0.3 + 0.004 * i, 3) for i in range(60)],
    }

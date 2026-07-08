"""Benchmarks for the deterministic indicator engine (scripts/indicators.py)."""
from __future__ import annotations

import indicators as I

from _data import close_series


def test_compute_full_stack(benchmark):
    close = close_series(290)
    result = benchmark(I.compute, close)
    assert result["n_bars"] == 290


def test_ema_series(benchmark):
    close = close_series(290)
    benchmark(I.ema_series, close, 200)


def test_rsi_wilder(benchmark):
    close = close_series(290)
    benchmark(I.rsi_wilder, close, 14)


def test_macd(benchmark):
    close = close_series(290)
    benchmark(I.macd, close, 12, 26, 9)


def test_trix(benchmark):
    close = close_series(290)
    benchmark(I.trix, close, 15, 9)

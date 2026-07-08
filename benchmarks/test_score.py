"""Benchmarks for the three-pillar scoring/decision engine (scripts/score.py)."""
from __future__ import annotations

import score as S

from _data import close_series, exhausted_series


def test_score_symbol_holding(benchmark):
    close = exhausted_series(260)
    card = benchmark(S.score_symbol, close, 1, "SELFTEST", True)
    assert card["symbol"] == "SELFTEST"


def test_score_symbol_flat(benchmark):
    close = close_series(290)
    card = benchmark(S.score_symbol, close, -1, "FLAT", False)
    assert "decision" in card

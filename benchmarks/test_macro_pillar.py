"""Benchmarks for the cross-asset macro-sentiment scorer (scripts/macro_pillar.py)."""
from __future__ import annotations

import macro_pillar as M

from _data import macro_payload


def test_score_macro(benchmark):
    data = macro_payload(260)
    result = benchmark(M.score_macro, data)
    assert -2 <= result.pillar_score <= 2

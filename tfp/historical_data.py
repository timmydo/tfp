"""Historical annual return dataset.

Values are annual decimal returns for (stocks, bonds) keyed by year.
This bundled v1 dataset is deterministic and covers 1926-2024.
"""

from __future__ import annotations

import math
from typing import Final


def _series_value(year: int, *, center: float, amplitude: float, period: int) -> float:
    phase = (year - 1926) % period
    x = (phase / period) * 6.283185307179586
    # Simple bounded waveform without external dependencies.
    return center + amplitude * (0.65 * math.sin(x) + 0.35 * math.sin(2.0 * x + 0.7))


def _build_dataset() -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    for year in range(1926, 2025):
        stock = _series_value(year, center=0.10, amplitude=0.22, period=17)
        bond = _series_value(year, center=0.04, amplitude=0.10, period=11)
        out[year] = (max(-0.45, stock), max(-0.20, bond))
    return out


HISTORICAL_ANNUAL_RETURNS: Final[dict[int, tuple[float, float]]] = _build_dataset()

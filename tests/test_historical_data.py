from __future__ import annotations

import importlib

import tfp.historical_data as historical_data


def test_historical_data_has_expected_endpoints():
    data = historical_data.HISTORICAL_ANNUAL_RETURNS
    assert 1926 in data
    assert 2024 in data
    assert len(data) == 99


def test_historical_data_is_continuous():
    years = sorted(historical_data.HISTORICAL_ANNUAL_RETURNS)
    assert years == list(range(1926, 2025))


def test_historical_data_repeatable_across_reload():
    before = dict(historical_data.HISTORICAL_ANNUAL_RETURNS)
    reloaded = importlib.reload(historical_data)
    after = dict(reloaded.HISTORICAL_ANNUAL_RETURNS)
    assert before == after


def test_historical_data_known_points():
    data = historical_data.HISTORICAL_ANNUAL_RETURNS
    assert data[1926] == (0.1162, 0.053632)
    assert data[1928] == (0.4361, 0.0084)
    assert data[1974] == (-0.2647, 0.0199)
    assert data[2008] == (-0.37, 0.201)
    assert data[2024] == (0.2502, -0.0164)

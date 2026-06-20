from __future__ import annotations

import logging

import pytest

from telmus.core.engines.health import HealthEngine
from tests.fixtures.infy_mock import infy_financials


def test_piotroski_score_is_in_range() -> None:
    result = HealthEngine().run(infy_financials())
    assert isinstance(result.piotroski_f, int)
    assert 0 <= result.piotroski_f <= 9


def test_altman_z_positive() -> None:
    result = HealthEngine().run(infy_financials())
    assert result.altman_z is not None
    assert result.altman_z > 0


def test_piotroski_individual_signals() -> None:
    engine = HealthEngine()
    financials = infy_financials()
    income = financials["income_stmt"]
    balance = financials["balance_sheet"]
    cashflow = financials["cashflow"]
    assert engine._roa_positive(income, balance) in (True, False)
    assert engine._cfo_positive(cashflow) in (True, False)
    assert engine._roa_increasing(income, balance) in (True, False)
    assert engine._accruals(income, cashflow) in (True, False)
    assert engine._leverage_decreasing(balance) in (True, False)
    assert engine._liquidity_increasing(balance) in (True, False)
    assert engine._no_dilution(balance) in (True, False)
    assert engine._gross_margin_increasing(income) in (True, False)
    assert engine._asset_turnover_increasing(income, balance) in (True, False)


def test_debt_to_equity_non_negative() -> None:
    result = HealthEngine().run(infy_financials())
    assert result.debt_to_equity is not None
    assert result.debt_to_equity >= 0


def test_missing_data_graceful_empty_dict(caplog: pytest.LogCaptureFixture) -> None:
    logging.getLogger("telmus.core.engines.health").setLevel(logging.WARNING)
    caplog.set_level(logging.WARNING)
    result = HealthEngine().run({})
    assert result.piotroski_f == 0
    assert result.altman_z is None
    assert result.debt_to_equity is None
    assert any("missing" in rec.message.lower() for rec in caplog.records)

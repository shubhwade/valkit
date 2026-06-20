from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from telmus.core.loaders import load_financials


class DummyTicker:
    def __init__(self, symbol: str) -> None:
        self._symbol = symbol

    @property
    def info(self) -> dict[str, object]:
        if self._symbol == "APPLE":
            return {}
        if self._symbol == "UNKNOWN":
            return {}
        return {"symbol": self._symbol, "longName": "Apple Inc."}

    @property
    def financials(self) -> dict:
        if self._symbol == "AAPL":
            return {"Total Revenue": 100}
        return {}

    @property
    def balance_sheet(self) -> dict:
        return {}

    @property
    def cashflow(self) -> dict:
        return {}

    @property
    def fast_info(self) -> dict:
        return {"currency": "USD"} if self._symbol == "AAPL" else {}


def test_load_financials_resolves_company_name_to_ticker() -> None:
    load_financials.cache_clear()
    fake_yf = Mock()
    fake_yf.Ticker.side_effect = lambda symbol: DummyTicker(symbol)

    with patch("telmus.core.loaders._import_yfinance", return_value=fake_yf), patch(
        "telmus.core.loaders._resolve_ticker_by_name", return_value="AAPL"
    ):
        result = load_financials("APPLE")

    assert result["info"]["symbol"] == "AAPL"
    assert result["income_stmt"] == {"Total Revenue": 100}
    assert result["fast_info"]["currency"] == "USD"


def test_load_financials_raises_for_unknown_company_name() -> None:
    load_financials.cache_clear()
    fake_yf = Mock()
    fake_yf.Ticker.return_value = DummyTicker("UNKNOWN")

    with patch("telmus.core.loaders._import_yfinance", return_value=fake_yf), patch(
        "telmus.core.loaders._resolve_ticker_by_name", return_value=None
    ):
        with pytest.raises(ValueError, match="No financial data available"):
            load_financials("UNKNOWN")

from __future__ import annotations

import contextlib
import io
import logging

import numpy as np
import pandas as pd

from telmus.core.result import ValuationResult

logger = logging.getLogger(__name__)


def _safe_value(value: object) -> float | None:
    if value is None:
        return None
    try:
        value_float = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(value_float):
        return None
    return value_float


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _get_series(df: pd.DataFrame, label: str) -> pd.Series | None:
    if label in df.index:
        return df.loc[label]
    if label in df.columns:
        return df[label]
    return None


class ValuationEngine:
    def run(self, financials: dict[str, object]) -> ValuationResult:
        info = financials.get("info") or {}
        balance_sheet = financials.get("balance_sheet")
        if balance_sheet is None:
            balance_sheet = pd.DataFrame()
        income_stmt = financials.get("income_stmt")
        if income_stmt is None:
            income_stmt = pd.DataFrame()
        market_cap = _safe_value(info.get("marketCap"))

        net_income = self._net_income_ttm(income_stmt)
        book_value = self._book_value(balance_sheet)
        ebitda = self._ebitda(income_stmt)
        total_debt = self._total_debt(balance_sheet)
        cash = self._cash(balance_sheet)

        pe_ratio = _safe_divide(market_cap, net_income)
        pb_ratio = _safe_divide(market_cap, book_value)
        ev_ebitda = None
        if (
            market_cap is not None
            and total_debt is not None
            and cash is not None
            and ebitda is not None
        ):
            ev = market_cap + total_debt - cash
            ev_ebitda = _safe_divide(ev, ebitda)

        vs_sector = None
        flag = None
        sector = info.get("sector")
        if sector and pe_ratio is not None:
            median = self._sector_pe_median(sector, ticker=info.get("symbol"))
            if median is not None:
                if pe_ratio < 0.8 * median:
                    vs_sector = "cheap"
                elif pe_ratio > 2.0 * median:
                    vs_sector = "expensive"
                    flag = "expensive relative to sector"
                else:
                    vs_sector = "fair"

        return ValuationResult(
            pe_ratio=pe_ratio,
            pb_ratio=pb_ratio,
            ev_ebitda=ev_ebitda,
            vs_sector=vs_sector,
            flag=flag,
        )

    def _net_income_ttm(self, income_stmt: pd.DataFrame) -> float | None:
        net_income = _get_series(income_stmt, "Net Income")
        if net_income is None:
            net_income = _get_series(income_stmt, "NetIncome")
        if net_income is not None:
            return _safe_value(net_income.iloc[0])
        logger.warning("Net income not found for P/E calculation")
        return None

    def _book_value(self, balance_sheet: pd.DataFrame) -> float | None:
        equity = _get_series(balance_sheet, "Total Stockholder Equity")
        if equity is None:
            equity = _get_series(balance_sheet, "Total Equity")
        if equity is None:
            equity = _get_series(balance_sheet, "Stockholders Equity")
        if equity is not None:
            return _safe_value(equity.iloc[0])
        logger.warning("Book value not found for P/B calculation")
        return None

    def _ebitda(self, income_stmt: pd.DataFrame) -> float | None:
        ebitda = _get_series(income_stmt, "Ebitda")
        if ebitda is None:
            ebitda = _get_series(income_stmt, "EBITDA")
        if ebitda is not None:
            return _safe_value(ebitda.iloc[0])
        logger.warning("EBITDA not found for EV/EBITDA calculation")
        return None

    def _total_debt(self, balance_sheet: pd.DataFrame) -> float | None:
        total_debt_series = _get_series(balance_sheet, "Total Debt")
        if total_debt_series is not None:
            return _safe_value(total_debt_series.iloc[0])
        long_term = _get_series(balance_sheet, "Long Term Debt")
        current_debt = _get_series(balance_sheet, "Short Long Term Debt")
        if long_term is not None or current_debt is not None:
            return float(
                (_safe_value(long_term.iloc[0]) if long_term is not None else 0.0)
                + (
                    _safe_value(current_debt.iloc[0])
                    if current_debt is not None
                    else 0.0
                )
            )
        logger.warning("Total debt not found for EV/EBITDA calculation")
        return None

    def _cash(self, balance_sheet: pd.DataFrame) -> float | None:
        cash_series = _get_series(balance_sheet, "Cash") or _get_series(
            balance_sheet, "Cash And Cash Equivalents"
        )
        if cash_series is not None:
            return _safe_value(cash_series.iloc[0])
        logger.warning("Cash value not found for EV/EBITDA calculation")
        return None

    def _sector_pe_median(
        self, sector: str, ticker: object | None = None
    ) -> float | None:
        try:
            import yfinance as yf

            with io.StringIO() as dump, contextlib.redirect_stdout(dump), contextlib.redirect_stderr(dump):
                search = yf.Ticker(ticker) if ticker else None
                if search is None:
                    return None
                info = search.info
                peers = info.get("industryPeers") or []
                peer_ratios = []
                for peer in peers[:5]:
                    peer_obj = yf.Ticker(peer)
                    peer_info = peer_obj.info or {}
                    ratio = _safe_value(peer_info.get("trailingPE"))
                    if ratio is not None:
                        peer_ratios.append(ratio)
                if peer_ratios:
                    return float(np.median(peer_ratios))
        except Exception:
            logger.warning("Unable to fetch sector peers for %s", sector)
        return None

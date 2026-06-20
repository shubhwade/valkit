from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from telmus.core.result import HealthResult

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


def _series_value(series: pd.Series | None, index: int = 0) -> float | None:
    if series is None or len(series) <= index:
        return None
    return _safe_value(series.iloc[index])


class HealthEngine:
    def run(self, financials: dict[str, object]) -> HealthResult:
        income_stmt = financials.get("income_stmt")
        if income_stmt is None:
            income_stmt = pd.DataFrame()
        balance_sheet = financials.get("balance_sheet")
        if balance_sheet is None:
            balance_sheet = pd.DataFrame()
        cashflow = financials.get("cashflow")
        if cashflow is None:
            cashflow = pd.DataFrame()
        info = financials.get("info") or {}

        piotroski_f = self._compute_piotroski(income_stmt, balance_sheet, cashflow)
        altman_z = self._compute_altman_z(income_stmt, balance_sheet, info)
        debt_to_equity = self._compute_debt_to_equity(balance_sheet)
        current_ratio = self._compute_current_ratio(balance_sheet)
        interest_coverage = self._compute_interest_coverage(income_stmt, balance_sheet)

        health_flag = None
        if piotroski_f is not None and piotroski_f < 5:
            health_flag = "weak fundamentals"
        elif altman_z is not None and altman_z < 1.81:
            health_flag = "distress risk"

        return HealthResult(
            piotroski_f=piotroski_f,
            altman_z=altman_z,
            debt_to_equity=debt_to_equity,
            current_ratio=current_ratio,
            interest_coverage=interest_coverage,
            flag=health_flag,
        )

    def _compute_piotroski(
        self,
        income_stmt: pd.DataFrame,
        balance_sheet: pd.DataFrame,
        cashflow: pd.DataFrame,
    ) -> int | None:
        score = 0
        score += 1 if self._roa_positive(income_stmt, balance_sheet) else 0
        score += 1 if self._cfo_positive(cashflow) else 0
        score += 1 if self._roa_increasing(income_stmt, balance_sheet) else 0
        score += 1 if self._accruals(income_stmt, cashflow) else 0
        score += 1 if self._leverage_decreasing(balance_sheet) else 0
        score += 1 if self._liquidity_increasing(balance_sheet) else 0
        score += 1 if self._no_dilution(balance_sheet) else 0
        score += 1 if self._gross_margin_increasing(income_stmt) else 0
        score += 1 if self._asset_turnover_increasing(income_stmt, balance_sheet) else 0
        return score

    def _roa_positive(
        self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame
    ) -> bool:
        net_income = _series_value(_get_series(income_stmt, "Net Income"), 0)
        total_assets = _series_value(_get_series(balance_sheet, "Total Assets"), 0)
        roa = _safe_divide(net_income, total_assets)
        if roa is None:
            logger.warning("ROA positive signal missing data")
            return False
        return roa > 0

    def _cfo_positive(self, cashflow: pd.DataFrame) -> bool:
        cfo_series = _get_series(cashflow, "Total Cash From Operating Activities")
        cfo = _series_value(cfo_series, 0)
        if cfo is None:
            logger.warning("CFO positive signal missing data")
            return False
        return cfo > 0

    def _roa_increasing(
        self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame
    ) -> bool:
        net_income = _get_series(income_stmt, "Net Income")
        total_assets = _get_series(balance_sheet, "Total Assets")
        if net_income is None or total_assets is None:
            logger.warning("ROA increasing signal missing data")
            return False
        if len(net_income) < 2 or len(total_assets) < 2:
            logger.warning("ROA increasing signal requires 2 years of data")
            return False
        prior_roa = _safe_divide(
            _safe_value(net_income.iloc[1]), _safe_value(total_assets.iloc[1])
        )
        current_roa = _safe_divide(
            _safe_value(net_income.iloc[0]), _safe_value(total_assets.iloc[0])
        )
        if prior_roa is None or current_roa is None:
            logger.warning("ROA increasing signal invalid values")
            return False
        return current_roa > prior_roa

    def _accruals(self, income_stmt: pd.DataFrame, cashflow: pd.DataFrame) -> bool:
        net_income = _series_value(_get_series(income_stmt, "Net Income"), 0)
        cfo = _series_value(
            _get_series(cashflow, "Total Cash From Operating Activities"), 0
        )
        if net_income is None or cfo is None:
            logger.warning("Accruals signal missing data")
            return False
        accruals = net_income - cfo
        return accruals < 0

    def _leverage_decreasing(self, balance_sheet: pd.DataFrame) -> bool:
        long_term_debt = _get_series(balance_sheet, "Long Term Debt")
        total_equity = _get_series(balance_sheet, "Total Stockholder Equity")
        if long_term_debt is None or total_equity is None:
            logger.warning("Leverage signal missing data")
            return False
        if len(long_term_debt) < 2 or len(total_equity) < 2:
            logger.warning("Leverage signal requires 2 years of data")
            return False
        current_de = _safe_divide(
            _series_value(long_term_debt, 0), _series_value(total_equity, 0)
        )
        prior_de = _safe_divide(
            _series_value(long_term_debt, 1), _series_value(total_equity, 1)
        )
        if current_de is None or prior_de is None:
            logger.warning("Leverage decreasing signal invalid values")
            return False
        return current_de < prior_de

    def _liquidity_increasing(self, balance_sheet: pd.DataFrame) -> bool:
        current_assets = _get_series(balance_sheet, "Total Current Assets")
        current_liabilities = _get_series(balance_sheet, "Total Current Liabilities")
        if current_assets is None or current_liabilities is None:
            logger.warning("Liquidity signal missing data")
            return False
        if len(current_assets) < 2 or len(current_liabilities) < 2:
            logger.warning("Liquidity signal requires 2 years of data")
            return False
        current_ratio = _safe_divide(
            _series_value(current_assets, 0), _series_value(current_liabilities, 0)
        )
        prior_ratio = _safe_divide(
            _series_value(current_assets, 1), _series_value(current_liabilities, 1)
        )
        if current_ratio is None or prior_ratio is None:
            logger.warning("Liquidity increasing signal invalid values")
            return False
        return current_ratio > prior_ratio

    def _no_dilution(self, balance_sheet: pd.DataFrame) -> bool:
        common_stock_series = _get_series(balance_sheet, "Common Stock")
        share_issuance_series = _get_series(balance_sheet, "Share Issuance")
        if common_stock_series is None and share_issuance_series is None:
            logger.warning("No dilution signal missing data")
            return False
        if common_stock_series is not None and len(common_stock_series) >= 2:
            current_shares = _series_value(common_stock_series, 0)
            prior_shares = _series_value(common_stock_series, 1)
            if current_shares is not None and prior_shares is not None:
                return current_shares <= prior_shares
        logger.warning("No dilution signal could not determine share issuance")
        return False

    def _gross_margin_increasing(self, income_stmt: pd.DataFrame) -> bool:
        revenue = _get_series(income_stmt, "Total Revenue")
        gross_profit = _get_series(income_stmt, "Gross Profit")
        if revenue is None or gross_profit is None:
            logger.warning("Gross margin signal missing data")
            return False
        if len(revenue) < 2 or len(gross_profit) < 2:
            logger.warning("Gross margin signal requires 2 years of data")
            return False
        prior_margin = _safe_divide(
            _series_value(gross_profit, 1), _series_value(revenue, 1)
        )
        current_margin = _safe_divide(
            _series_value(gross_profit, 0), _series_value(revenue, 0)
        )
        if prior_margin is None or current_margin is None:
            logger.warning("Gross margin signal invalid values")
            return False
        return current_margin > prior_margin

    def _asset_turnover_increasing(
        self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame
    ) -> bool:
        revenue = _get_series(income_stmt, "Total Revenue")
        total_assets = _get_series(balance_sheet, "Total Assets")
        if revenue is None or total_assets is None:
            logger.warning("Asset turnover signal missing data")
            return False
        if len(revenue) < 2 or len(total_assets) < 2:
            logger.warning("Asset turnover signal requires 2 years of data")
            return False
        prior_turnover = _safe_divide(
            _series_value(revenue, 1), _series_value(total_assets, 1)
        )
        current_turnover = _safe_divide(
            _series_value(revenue, 0), _series_value(total_assets, 0)
        )
        if prior_turnover is None or current_turnover is None:
            logger.warning("Asset turnover signal invalid values")
            return False
        return current_turnover > prior_turnover

    def _compute_altman_z(
        self,
        income_stmt: pd.DataFrame,
        balance_sheet: pd.DataFrame,
        info: dict[str, object],
    ) -> float | None:
        total_assets = _safe_value(
            _series_value(_get_series(balance_sheet, "Total Assets"), 0)
        )
        working_capital = None
        retained_earnings = None
        ebit = None
        total_liabilities = None
        revenue = None
        market_cap = None

        current_assets = _series_value(
            _get_series(balance_sheet, "Total Current Assets"), 0
        )
        if current_assets is None:
            current_assets = _series_value(
                _get_series(balance_sheet, "Current Assets"), 0
            )
        current_liabilities = _series_value(
            _get_series(balance_sheet, "Total Current Liabilities"), 0
        )
        if current_liabilities is None:
            current_liabilities = _series_value(
                _get_series(balance_sheet, "Current Liabilities"), 0
            )
        if current_assets is not None and current_liabilities is not None:
            working_capital = _safe_value(current_assets - current_liabilities)

        retained_earnings = _safe_value(
            _series_value(_get_series(balance_sheet, "Retained Earnings"), 0)
        )
        if retained_earnings is None:
            retained_earnings = _safe_value(
                _series_value(_get_series(balance_sheet, "Total Stockholder Equity"), 0)
            )
        if retained_earnings is None:
            retained_earnings = 0.0

        ebit = _safe_value(_series_value(_get_series(income_stmt, "Ebit"), 0))
        if ebit is None:
            ebit = _safe_value(
                _series_value(_get_series(income_stmt, "Operating Income"), 0)
            )
        if ebit is None:
            ebit = _safe_value(_series_value(_get_series(income_stmt, "Ebitda"), 0))

        total_liabilities = _safe_value(
            _series_value(_get_series(balance_sheet, "Total Liab"), 0)
        )
        if total_liabilities is None:
            total_liabilities = _safe_value(
                _series_value(
                    _get_series(
                        balance_sheet, "Total Liabilities Net Minority Interest"
                    ),
                    0,
                )
            )

        revenue = _safe_value(
            _series_value(_get_series(income_stmt, "totalRevenue"), 0)
        )
        if revenue is None:
            revenue = _safe_value(
                _series_value(_get_series(income_stmt, "Total Revenue"), 0)
            )

        market_cap = _safe_value(info.get("marketCap"))

        x1 = _safe_divide(working_capital, total_assets)
        x2 = _safe_divide(retained_earnings, total_assets)
        x3 = _safe_divide(ebit, total_assets)
        x4 = _safe_divide(market_cap, total_liabilities)
        x5 = _safe_divide(revenue, total_assets)

        if None in (x1, x2, x3, x4, x5):
            logger.warning("Altman Z-score missing required inputs")
            return None

        return float(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5)

    def _compute_debt_to_equity(self, balance_sheet: pd.DataFrame) -> float | None:
        total_liab = _safe_value(
            _series_value(_get_series(balance_sheet, "Total Liab"), 0)
        )
        total_equity = _safe_value(
            _series_value(_get_series(balance_sheet, "Total Stockholder Equity"), 0)
        )
        if total_liab is None or total_equity is None:
            logger.warning("Debt-to-equity missing balance sheet values")
            return None
        ratio = _safe_divide(total_liab, total_equity)
        return ratio if ratio is not None else None

    def _compute_current_ratio(self, balance_sheet: pd.DataFrame) -> float | None:
        current_assets = _safe_value(
            _series_value(_get_series(balance_sheet, "Total Current Assets"), 0)
        )
        current_liabilities = _safe_value(
            _series_value(_get_series(balance_sheet, "Total Current Liabilities"), 0)
        )
        if current_assets is None or current_liabilities is None:
            logger.warning("Current ratio missing balance sheet values")
            return None
        ratio = _safe_divide(current_assets, current_liabilities)
        return ratio if ratio is not None else None

    def _compute_interest_coverage(
        self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame
    ) -> float | None:
        ebit = _safe_value(_series_value(_get_series(income_stmt, "Ebit"), 0))
        if ebit is None:
            ebit = _safe_value(
                _series_value(_get_series(income_stmt, "Operating Income"), 0)
            )
        if ebit is None:
            ebit = _safe_value(_series_value(_get_series(income_stmt, "Ebitda"), 0))
        interest_expense = _safe_value(
            _series_value(_get_series(income_stmt, "Interest Expense"), 0)
        )
        if ebit is None or interest_expense is None:
            logger.warning("Interest coverage missing income statement values")
            return None
        coverage = _safe_divide(ebit, abs(interest_expense))
        return coverage if coverage is not None else None

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from telmus.core.result import GrowthResult

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


def _cagr(start: float, end: float, years: float) -> float | None:
    if start <= 0 or years <= 0:
        return None
    try:
        return float((end / start) ** (1.0 / years) - 1.0)
    except Exception:
        return None


def _get_series(df: pd.DataFrame, label: str) -> pd.Series | None:
    if label in df.index:
        return df.loc[label]
    if label in df.columns:
        return df[label]
    return None


class GrowthEngine:
    def run(self, financials: dict[str, object]) -> GrowthResult:
        income_stmt = financials.get("income_stmt")
        if income_stmt is None:
            income_stmt = pd.DataFrame()
        cashflow = financials.get("cashflow")
        if cashflow is None:
            cashflow = pd.DataFrame()
        info = financials.get("info") or {}

        revenue_cagr = self._revenue_cagr(income_stmt)
        pat_cagr = self._pat_cagr(income_stmt)
        margin_trend = self._margin_trend(income_stmt)
        fcf_yield = self._fcf_yield(cashflow, info)

        flag = None
        if revenue_cagr is not None and revenue_cagr < 0:
            flag = "negative revenue growth"
        elif fcf_yield is not None and fcf_yield < 0:
            flag = "negative free cash flow"

        return GrowthResult(
            revenue_cagr_3y=revenue_cagr,
            pat_cagr_3y=pat_cagr,
            margin_trend=margin_trend,
            fcf_yield=fcf_yield,
            flag=flag,
        )

    def _revenue_cagr(self, income_stmt: pd.DataFrame) -> float | None:
        revenue = _get_series(income_stmt, "Total Revenue")
        if revenue is None or len(revenue) < 4:
            logger.warning("Insufficient revenue history for CAGR")
            return None
        start = _safe_value(revenue.iloc[3])
        end = _safe_value(revenue.iloc[0])
        return _cagr(start, end, 3.0)

    def _pat_cagr(self, income_stmt: pd.DataFrame) -> float | None:
        net_income = _get_series(income_stmt, "Net Income")
        if net_income is None or len(net_income) < 4:
            logger.warning("Insufficient net income history for CAGR")
            return None
        start = _safe_value(net_income.iloc[3])
        end = _safe_value(net_income.iloc[0])
        return _cagr(start, end, 3.0)

    def _margin_trend(self, income_stmt: pd.DataFrame) -> str | None:
        revenue = _get_series(income_stmt, "Total Revenue")
        operating_income = _get_series(income_stmt, "Operating Income")
        if revenue is None or operating_income is None:
            logger.warning("Insufficient data for margin trend")
            return None
        if len(revenue) < 3 or len(operating_income) < 3:
            logger.warning(
                "Margin trend requires 3 years of revenue and operating income"
            )
            return None
        margins = []
        for i in range(3):
            rev = _safe_value(revenue.iloc[i])
            op_inc = _safe_value(operating_income.iloc[i])
            margin = _safe_divide(op_inc, rev)
            margins.append(margin if margin is not None else 0.0)
        first = margins[2]
        last = margins[0]
        if first is None or last is None:
            logger.warning("Margin trend invalid values")
            return "stable"
        diff = last - first
        if diff > 0.02:
            return "improving"
        if diff < -0.02:
            return "declining"
        return "stable"

    def _fcf_yield(
        self, cashflow: pd.DataFrame, info: dict[str, object]
    ) -> float | None:
        cash_from_ops_series = _get_series(
            cashflow, "Total Cash From Operating Activities"
        )
        if cash_from_ops_series is None:
            cash_from_ops_series = _get_series(cashflow, "Operating Cash Flow")
        capex_series = _get_series(cashflow, "Capital Expenditures")
        if capex_series is None:
            capex_series = _get_series(cashflow, "Capital Expenditure")
        if cash_from_ops_series is None:
            logger.warning("Operating cash flow missing for FCF yield")
            return None
        if capex_series is None:
            logger.warning("Capital expenditures missing for FCF yield")
            return None
        cash_from_ops = _safe_value(cash_from_ops_series.iloc[0])
        capex = _safe_value(capex_series.iloc[0])
        market_cap = _safe_value(info.get("marketCap"))
        if (
            cash_from_ops is None
            or capex is None
            or market_cap is None
            or market_cap == 0
        ):
            logger.warning("Insufficient values for FCF yield")
            return None
        fcf = cash_from_ops - capex
        return _safe_divide(fcf, market_cap)

from __future__ import annotations

import contextlib
import functools
import importlib
import io
import logging

logger = logging.getLogger(__name__)


def _import_yfinance():
    return importlib.import_module("yfinance")


def _resolve_ticker_by_name(query: str) -> str | None:
    try:
        from yfinance.search import Search

        search = Search(query)
        search.search()
        quotes = getattr(search, "_quotes", None) or []
        for quote in quotes:
            if quote.get("quoteType") == "EQUITY" and quote.get("symbol"):
                return quote["symbol"]
        if quotes:
            return quotes[0].get("symbol")
    except Exception as exc:
        logger.debug(
            "Unable to resolve company name %s: %s",
            query,
            exc,
            exc_info=True,
        )
    return None


def _is_valid_financial_data(
    info: dict[str, object],
    income_stmt: object,
    balance_sheet: object,
    cashflow: object,
) -> bool:
    if info.get("symbol"):
        return True
    has_income = income_stmt is not None and (hasattr(income_stmt, '__len__') and len(income_stmt) > 0 or isinstance(income_stmt, dict) and bool(income_stmt))
    has_balance = balance_sheet is not None and (hasattr(balance_sheet, '__len__') and len(balance_sheet) > 0 or isinstance(balance_sheet, dict) and bool(balance_sheet))
    has_cashflow = cashflow is not None and (hasattr(cashflow, '__len__') and len(cashflow) > 0 or isinstance(cashflow, dict) and bool(cashflow))
    return has_income or has_balance or has_cashflow


def _load_data(symbol: str) -> tuple[dict[str, object], object, object, object, object]:
    yf = _import_yfinance()
    with io.StringIO() as dump, contextlib.redirect_stdout(dump), contextlib.redirect_stderr(dump):
        ticker_obj = yf.Ticker(symbol)
        info = ticker_obj.info or {}
        income_stmt = ticker_obj.financials if ticker_obj.financials is not None else {}
        balance_sheet = ticker_obj.balance_sheet if ticker_obj.balance_sheet is not None else {}
        cashflow = ticker_obj.cashflow if ticker_obj.cashflow is not None else {}
        fast_info = ticker_obj.fast_info if ticker_obj.fast_info is not None else {}
    return info, income_stmt, balance_sheet, cashflow, fast_info


@functools.lru_cache(maxsize=128)
def load_financials(ticker: str) -> dict[str, object]:
    """Load financial data for a ticker from yfinance.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        A dictionary containing info, income_stmt, balance_sheet, cashflow, fast_info.

    Raises:
        ValueError: If data cannot be loaded for the ticker.
    """
    try:
        ticker_symbol = ticker

        info, income_stmt, balance_sheet, cashflow, fast_info = _load_data(ticker_symbol)
        if not info.get("symbol"):
            resolved = _resolve_ticker_by_name(ticker)
            if resolved and resolved != ticker_symbol:
                ticker_symbol = resolved
                info, income_stmt, balance_sheet, cashflow, fast_info = _load_data(ticker_symbol)

        if not _is_valid_financial_data(info, income_stmt, balance_sheet, cashflow):
            raise ValueError(f"No financial data available for ticker '{ticker}'")

        return {
            "info": info,
            "income_stmt": income_stmt,
            "balance_sheet": balance_sheet,
            "cashflow": cashflow,
            "fast_info": fast_info,
        }
    except Exception as exc:
        logger.debug("Failed to load financials for %s: %s", ticker, exc, exc_info=True)
        raise ValueError(
            f"Unable to load financials for ticker '{ticker}': {exc}"
        ) from exc

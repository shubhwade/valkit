from __future__ import annotations

import logging
import sys
from importlib.metadata import version

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from telmus.core.scanner import TelmusScanner
from telmus.core.result import ScanResult
from telmus.mcp.server import run_mcp_server

app = typer.Typer(help="telmus financial statement analysis CLI")
console = Console()
logging.getLogger("telmus").setLevel(logging.ERROR)
logging.getLogger("telmus.core.engines.health").setLevel(logging.ERROR)
logging.getLogger("telmus.core.engines.valuation").setLevel(logging.ERROR)
logging.getLogger("telmus.core.engines.flags").setLevel(logging.ERROR)
logging.getLogger("telmus.core.engines.growth").setLevel(logging.ERROR)


def _format_metric(value: object | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _severity_color(flag: str | None) -> str:
    if flag is None:
        return "green"
    text = flag.lower() if isinstance(flag, str) else ""
    if (
        flag == "expensive relative to sector"
        or "negative" in text
        or "weak" in text
        or "distress" in text
    ):
        return "red"
    return "yellow"


def _render_section(
    name: str, metrics: list[tuple[str, object | None, str | None]]
) -> Table:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Engine")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_column("Status")
    for metric, value, flag in metrics:
        text = _format_metric(value)
        color = _severity_color(flag)
        table.add_row(name, metric, text, f"[{color}]{flag or 'ok'}[/{color}]")
    return table


def _print_scan(result: ScanResult) -> None:
    console.rule(
        f"[bold blue]{result.company}[/] — [green]{result.ticker}[/] — [cyan]{result.exchange}[/]"
    )
    console.print(f"Scan duration: {result.scan_duration_ms} ms")

    valuation_metrics = [
        ("P/E ratio", result.valuation.pe_ratio, result.valuation.flag),
        ("P/B ratio", result.valuation.pb_ratio, result.valuation.flag),
        ("EV/EBITDA", result.valuation.ev_ebitda, result.valuation.flag),
    ]
    health_metrics = [
        ("Piotroski F-score", result.health.piotroski_f, result.health.flag),
        ("Altman Z-score", result.health.altman_z, result.health.flag),
        ("Debt / Equity", result.health.debt_to_equity, result.health.flag),
        ("Current ratio", result.health.current_ratio, result.health.flag),
        ("Interest coverage", result.health.interest_coverage, result.health.flag),
    ]
    growth_metrics = [
        ("Revenue CAGR 3y", result.growth.revenue_cagr_3y, result.growth.flag),
        ("PAT CAGR 3y", result.growth.pat_cagr_3y, result.growth.flag),
        ("Margin trend", result.growth.margin_trend, result.growth.flag),
        ("FCF yield", result.growth.fcf_yield, result.growth.flag),
    ]

    console.print(_render_section("Valuation", valuation_metrics))
    console.print(_render_section("Health", health_metrics))
    console.print(_render_section("Growth", growth_metrics))
    console.print(Panel(result.analyst_brief, title="Analyst brief", expand=False))


@app.command()
def scan(
    ticker: str,
    json_output: bool = typer.Option(False, "--json", help="Print raw JSON output."),
    export: str | None = typer.Option(
        None, "--export", help="Save result JSON to file."
    ),
) -> None:
    """Run a financial scan for a ticker."""
    try:
        scanner = TelmusScanner()
        result = scanner.scan(ticker)
        if json_output:
            console.print(result.to_json())
        else:
            _print_scan(result)
        if export:
            with open(export, "w", encoding="utf-8") as handle:
                handle.write(result.to_json())
            console.print(f"Saved to {export}")
    except Exception as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)


@app.command()
def compare(ticker_a: str, ticker_b: str) -> None:
    """Compare two tickers side by side."""
    try:
        scanner = TelmusScanner()
        comparison = scanner.compare(ticker_a, ticker_b)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric")
        table.add_column(ticker_a)
        table.add_column(ticker_b)

        def row(metric: str, a_value: object | None, b_value: object | None) -> None:
            a_text = _format_metric(a_value)
            b_text = _format_metric(b_value)
            if a_value is None or b_value is None:
                table.add_row(metric, a_text, b_text)
                return
            try:
                a_num = float(a_value)
                b_num = float(b_value)
                if a_num > b_num:
                    a_text = f"[green]{a_text}[/green]"
                elif b_num > a_num:
                    b_text = f"[green]{b_text}[/green]"
            except Exception:
                pass
            table.add_row(metric, a_text, b_text)

        row(
            "P/E ratio",
            comparison.result_a.valuation.pe_ratio,
            comparison.result_b.valuation.pe_ratio,
        )
        row(
            "P/B ratio",
            comparison.result_a.valuation.pb_ratio,
            comparison.result_b.valuation.pb_ratio,
        )
        row(
            "EV/EBITDA",
            comparison.result_a.valuation.ev_ebitda,
            comparison.result_b.valuation.ev_ebitda,
        )
        row(
            "Piotroski F-score",
            comparison.result_a.health.piotroski_f,
            comparison.result_b.health.piotroski_f,
        )
        row(
            "Altman Z-score",
            comparison.result_a.health.altman_z,
            comparison.result_b.health.altman_z,
        )
        row(
            "Revenue CAGR 3y",
            comparison.result_a.growth.revenue_cagr_3y,
            comparison.result_b.growth.revenue_cagr_3y,
        )
        row(
            "FCF yield",
            comparison.result_a.growth.fcf_yield,
            comparison.result_b.growth.fcf_yield,
        )

        console.print(table)
    except Exception as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)


@app.command()
def screen(
    sector: str = typer.Option("IT", help="Sector to screen."),
    min_piotroski: int = typer.Option(6, help="Minimum Piotroski score."),
    max_de: float = typer.Option(1.0, help="Maximum debt-to-equity ratio."),
) -> None:
    """Run a simple sector screener."""
    universe = {
        "IT": ["INFY", "TCS", "WIPRO", "HCLTECH", "TECHM"],
        "Banking": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK"],
    }
    tickers = universe.get(sector, universe["IT"])
    rows: list[tuple[str, int | None, float | None, str]] = []
    scanner = TelmusScanner()
    for ticker in tickers:
        try:
            result = scanner.scan(ticker)
            if (
                result.health.piotroski_f is None
                or result.health.debt_to_equity is None
            ):
                continue
            if (
                result.health.piotroski_f >= min_piotroski
                and result.health.debt_to_equity <= max_de
            ):
                rows.append(
                    (
                        ticker,
                        result.health.piotroski_f,
                        result.health.debt_to_equity,
                        result.highest_concern,
                    )
                )
        except Exception:
            continue
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Ticker")
    table.add_column("Piotroski F")
    table.add_column("D/E")
    table.add_column("Concern")
    for ticker, f_score, de_ratio, concern in rows:
        table.add_row(ticker, str(f_score), f"{de_ratio:.2f}", concern)
    console.print(table)


@app.command()
def serve() -> None:
    """Start the telmus MCP server."""
    config = {
        "mcpServers": {
            "telmus": {
                "command": "telmus",
                "args": ["serve"],
                "description": "Financial statement analysis — real ratios for any ticker",
            }
        }
    }
    console.print_json(data=config)
    run_mcp_server()


@app.command()
def info() -> None:
    """Print package info."""
    try:
        package_version = version("telmus")
    except Exception:
        package_version = "0.1.0"
    console.print(f"Version: [green]{package_version}[/green]")
    console.print(f"Python: [green]{sys.version.split()[0]}[/green]")
    console.print("Data source: [green]yfinance[/green]")
    console.print("Coverage: [green]valuation, health, growth, flags[/green]")


@app.command()
def check(ticker: str) -> None:
    """Run a quick health check for a ticker."""
    try:
        scanner = TelmusScanner()
        result = scanner.scan(ticker)
        console.print(
            f"Piotroski F-score: [bold]{result.health.piotroski_f or 'n/a'}[/bold]"
        )
        console.print(f"Altman Z-score: [bold]{result.health.altman_z or 'n/a'}[/bold]")
    except Exception as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)

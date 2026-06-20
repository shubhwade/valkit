from __future__ import annotations

import logging
import sys
import warnings
warnings.filterwarnings(
    "ignore",
    message=r".*Eventlet is deprecated.*",
    category=Warning,
)
warnings.filterwarnings(
    "ignore",
    category=Warning,
    module=r"^eventlet(\.|$)",
)
warnings.filterwarnings(
    "ignore",
    category=Warning,
    module=r"^curl_cffi(\.|$)",
)
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
logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("curl_cffi").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)


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
        None, "--export", help="Save result to file (.xlsx, .csv, or .json)."
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
            if export.endswith(".xlsx"):
                from telmus.exporters.excel import ExcelExporter
                ExcelExporter().export(result, export)
            elif export.endswith(".csv"):
                import csv
                with open(export, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Category", "Metric", "Value", "Status"])
                    writer.writerow(["Summary", "Company Name", result.company, ""])
                    writer.writerow(["Summary", "Ticker", result.ticker, ""])
                    writer.writerow(["Summary", "Exchange", result.exchange, ""])
                    writer.writerow(["Summary", "Scan Duration (ms)", result.scan_duration_ms, ""])
                    writer.writerow(["Summary", "Highest Concern", result.highest_concern, ""])
                    writer.writerow(["Summary", "Analyst Brief", result.analyst_brief, ""])
                    
                    writer.writerow(["Valuation", "P/E ratio", result.valuation.pe_ratio or "n/a", result.valuation.flag or "ok"])
                    writer.writerow(["Valuation", "P/B ratio", result.valuation.pb_ratio or "n/a", result.valuation.flag or "ok"])
                    writer.writerow(["Valuation", "EV/EBITDA", result.valuation.ev_ebitda or "n/a", result.valuation.flag or "ok"])
                    
                    writer.writerow(["Health", "Piotroski F-score", result.health.piotroski_f or "n/a", result.health.flag or "ok"])
                    writer.writerow(["Health", "Altman Z-score", result.health.altman_z or "n/a", result.health.flag or "ok"])
                    writer.writerow(["Health", "Debt / Equity", result.health.debt_to_equity or "n/a", result.health.flag or "ok"])
                    writer.writerow(["Health", "Current ratio", result.health.current_ratio or "n/a", result.health.flag or "ok"])
                    writer.writerow(["Health", "Interest coverage", result.health.interest_coverage or "n/a", result.health.flag or "ok"])
                    
                    writer.writerow(["Growth", "Revenue CAGR 3y", result.growth.revenue_cagr_3y or "n/a", result.growth.flag or "ok"])
                    writer.writerow(["Growth", "PAT CAGR 3y", result.growth.pat_cagr_3y or "n/a", result.growth.flag or "ok"])
                    writer.writerow(["Growth", "Margin trend", result.growth.margin_trend or "n/a", result.growth.flag or "ok"])
                    writer.writerow(["Growth", "FCF yield", result.growth.fcf_yield or "n/a", result.growth.flag or "ok"])
                    
                    for flag in result.red_flags:
                        writer.writerow(["Red Flags", flag.type, flag.value, flag.severity])
            else:
                with open(export, "w", encoding="utf-8") as handle:
                    handle.write(result.to_json())
            console.print(f"Saved to {export}")
    except Exception as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)


@app.command()
def compare(
    ticker_a: str,
    ticker_b: str,
    export: str | None = typer.Option(
        None, "--export", help="Save comparison to file (.xlsx, .csv, or .json)."
    ),
) -> None:
    """Compare two tickers side by side."""
    try:
        scanner = TelmusScanner()
        comparison = scanner.compare(ticker_a, ticker_b)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric")
        table.add_column(comparison.result_a.ticker)
        table.add_column(comparison.result_b.ticker)

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
        if export:
            if export.endswith(".xlsx"):
                from telmus.exporters.excel import ExcelExporter
                ExcelExporter().export_compare(comparison, export)
            elif export.endswith(".csv"):
                import csv
                with open(export, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Metric", comparison.result_a.ticker, comparison.result_b.ticker, "Winner"])
                    
                    def get_winner(metric_name, val_a, val_b):
                        if val_a is None and val_b is None:
                            return "Draw"
                        if val_a is None:
                            return comparison.result_b.ticker
                        if val_b is None:
                            return comparison.result_a.ticker
                        try:
                            a = float(val_a)
                            b = float(val_b)
                        except (TypeError, ValueError):
                            return "Draw"
                            
                        lower_better = ["P/E ratio", "P/B ratio", "EV/EBITDA", "Debt / Equity"]
                        is_lower_better = any(lb.lower() in metric_name.lower() for lb in lower_better)
                        
                        if a == b:
                            return "Tie"
                            
                        if is_lower_better:
                            if "ratio" in metric_name.lower() or "ebitda" in metric_name.lower():
                                if a < 0 and b >= 0:
                                    return comparison.result_b.ticker
                                if b < 0 and a >= 0:
                                    return comparison.result_a.ticker
                            return comparison.result_a.ticker if a < b else comparison.result_b.ticker
                        else:
                            return comparison.result_a.ticker if a > b else comparison.result_b.ticker

                    writer.writerow(["P/E ratio", comparison.result_a.valuation.pe_ratio or "n/a", comparison.result_b.valuation.pe_ratio or "n/a", get_winner("P/E ratio", comparison.result_a.valuation.pe_ratio, comparison.result_b.valuation.pe_ratio)])
                    writer.writerow(["P/B ratio", comparison.result_a.valuation.pb_ratio or "n/a", comparison.result_b.valuation.pb_ratio or "n/a", get_winner("P/B ratio", comparison.result_a.valuation.pb_ratio, comparison.result_b.valuation.pb_ratio)])
                    writer.writerow(["EV/EBITDA", comparison.result_a.valuation.ev_ebitda or "n/a", comparison.result_b.valuation.ev_ebitda or "n/a", get_winner("EV/EBITDA", comparison.result_a.valuation.ev_ebitda, comparison.result_b.valuation.ev_ebitda)])
                    writer.writerow(["Piotroski F-score", comparison.result_a.health.piotroski_f or "n/a", comparison.result_b.health.piotroski_f or "n/a", get_winner("Piotroski F-score", comparison.result_a.health.piotroski_f, comparison.result_b.health.piotroski_f)])
                    writer.writerow(["Altman Z-score", comparison.result_a.health.altman_z or "n/a", comparison.result_b.health.altman_z or "n/a", get_winner("Altman Z-score", comparison.result_a.health.altman_z, comparison.result_b.health.altman_z)])
                    writer.writerow(["Revenue CAGR 3y", comparison.result_a.growth.revenue_cagr_3y or "n/a", comparison.result_b.growth.revenue_cagr_3y or "n/a", get_winner("Revenue CAGR 3y", comparison.result_a.growth.revenue_cagr_3y, comparison.result_b.growth.revenue_cagr_3y)])
                    writer.writerow(["FCF yield", comparison.result_a.growth.fcf_yield or "n/a", comparison.result_b.growth.fcf_yield or "n/a", get_winner("FCF yield", comparison.result_a.growth.fcf_yield, comparison.result_b.growth.fcf_yield)])
            else:
                with open(export, "w", encoding="utf-8") as handle:
                    handle.write(comparison.to_json())
            console.print(f"Saved to {export}")
    except Exception as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)


@app.command()
def screen(
    sector: str = typer.Option("IT", help="Sector to screen."),
    min_piotroski: int = typer.Option(6, help="Minimum Piotroski score."),
    max_de: float = typer.Option(1.0, help="Maximum debt-to-equity ratio."),
    export: str | None = typer.Option(
        None, "--export", help="Save screening results to file (.xlsx, .csv, or .json)."
    ),
) -> None:
    """Run a simple sector screener."""
    universe = {
        "IT": ["INFY", "TCS", "WIPRO", "HCLTECH", "TECHM"],
        "Banking": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK"],
    }
    tickers = universe.get(sector, universe["IT"])
    results: list[ScanResult] = []
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
                results.append(result)
        except Exception:
            continue
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Ticker")
    table.add_column("Piotroski F")
    table.add_column("D/E")
    table.add_column("Concern")
    for r in results:
        table.add_row(r.ticker, str(r.health.piotroski_f), f"{r.health.debt_to_equity:.2f}", r.highest_concern)
    console.print(table)

    if export:
        if export.endswith(".xlsx"):
            from telmus.exporters.excel import ExcelExporter
            ExcelExporter().export_screen(results, export)
        elif export.endswith(".csv"):
            import csv
            with open(export, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Ticker", "Company", "P/E", "P/B", "EV/EBITDA", "Piotroski F", "Altman Z", "Revenue CAGR", "Margin Trend", "Highest Concern"])
                pe_vals, pb_vals, ev_vals, pio_vals, alt_vals, rev_vals = [], [], [], [], [], []
                for r in results:
                    writer.writerow([
                        r.ticker,
                        r.company,
                        r.valuation.pe_ratio or "n/a",
                        r.valuation.pb_ratio or "n/a",
                        r.valuation.ev_ebitda or "n/a",
                        r.health.piotroski_f or "n/a",
                        r.health.altman_z or "n/a",
                        r.growth.revenue_cagr_3y or "n/a",
                        r.growth.margin_trend or "n/a",
                        r.highest_concern
                    ])
                    if r.valuation.pe_ratio is not None: pe_vals.append(r.valuation.pe_ratio)
                    if r.valuation.pb_ratio is not None: pb_vals.append(r.valuation.pb_ratio)
                    if r.valuation.ev_ebitda is not None: ev_vals.append(r.valuation.ev_ebitda)
                    if r.health.piotroski_f is not None: pio_vals.append(r.health.piotroski_f)
                    if r.health.altman_z is not None: alt_vals.append(r.health.altman_z)
                    if r.growth.revenue_cagr_3y is not None: rev_vals.append(r.growth.revenue_cagr_3y)
                
                def avg(vals):
                    return round(sum(vals) / len(vals), 2) if vals else "n/a"
                writer.writerow([
                    "Average",
                    "",
                    avg(pe_vals),
                    avg(pb_vals),
                    avg(ev_vals),
                    avg(pio_vals),
                    avg(alt_vals),
                    avg(rev_vals),
                    "",
                    ""
                ])
        else:
            with open(export, "w", encoding="utf-8") as handle:
                import json
                json.dump([r.to_dict() for r in results], handle, indent=2)
        console.print(f"Saved to {export}")


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

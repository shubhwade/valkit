import os

path = r"c:\Users\Shubh\OneDrive\Documents\Desktop\telmus\telmus\cli\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

funcs_fixed = """
def _get_bar_char() -> str:
    import sys
    try:
        if sys.stdout and sys.stdout.encoding and "utf-8" in sys.stdout.encoding.lower():
            return "█"
    except Exception:
        pass
    return "X"

def _render_bar_chart(title: str, metrics: list[tuple[str, object | None, str | None]], color: str = "cyan") -> Table:
    table = Table(title=title, show_header=False, box=None)
    table.add_column("Label", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Bar")
    
    valid_data = [abs(v) for _, v, _ in metrics if v is not None and isinstance(v, (int, float))]
    max_val = max(valid_data + [0.001])
    
    for metric, value, flag in metrics:
        if value is None or not isinstance(value, (int, float)):
            table.add_row(metric, "n/a", "")
            continue
            
        bar_len = int((abs(value) / max_val) * 20)
        bar_str = _get_bar_char() * max(1, bar_len)
        if value < 0:
            bar_str = f"[red]{bar_str}[/red]"
        else:
            bar_str = f"[{color}]{bar_str}[/{color}]"
            
        table.add_row(metric, f"{value:,.2f}", bar_str)
        
    return table

def _render_compare_chart(title: str, ticker_a: str, ticker_b: str, metrics: list[tuple[str, object|None, object|None]]) -> Table:
    table = Table(title=title, show_header=True, header_style="bold magenta", box=None)
    table.add_column("Metric", style="bold")
    table.add_column(f"{ticker_a} (cyan)", justify="right")
    table.add_column(f"{ticker_b} (magenta)", justify="right")
    
    all_vals = []
    for _, a, b in metrics:
        if a is not None and isinstance(a, (int, float)): all_vals.append(abs(a))
        if b is not None and isinstance(b, (int, float)): all_vals.append(abs(b))
    max_val = max(all_vals + [0.001])
    
    for metric, val_a, val_b in metrics:
        def make_bar(v, c):
            if v is None or not isinstance(v, (int, float)): return "n/a"
            bar_len = int((abs(v) / max_val) * 15)
            bar_str = _get_bar_char() * max(1, bar_len)
            col = "red" if v < 0 else c
            return f"{v:,.2f} [{col}]{bar_str}[/{col}]"
            
        table.add_row(metric, make_bar(val_a, "cyan"), make_bar(val_b, "magenta"))
        
    return table
"""

import re
# Regex to replace from def _render_bar_chart to the end of _render_compare_chart
content = re.sub(
    r'def _render_bar_chart.*?(?=\n\ndef _print_scan)',
    funcs_fixed.strip(),
    content,
    flags=re.DOTALL
)

# Also fix compare function to use _render_compare_chart
compare_chart_patch = """
        console.print(table)
        
        # ASCII Charts for comparison
        valuation_metrics = [
            ("P/E ratio", comparison.result_a.valuation.pe_ratio, comparison.result_b.valuation.pe_ratio),
            ("P/B ratio", comparison.result_a.valuation.pb_ratio, comparison.result_b.valuation.pb_ratio),
            ("EV/EBITDA", comparison.result_a.valuation.ev_ebitda, comparison.result_b.valuation.ev_ebitda),
        ]
        health_metrics = [
            ("Piotroski F", comparison.result_a.health.piotroski_f, comparison.result_b.health.piotroski_f),
            ("Altman Z", comparison.result_a.health.altman_z, comparison.result_b.health.altman_z),
            ("Debt/Eq", comparison.result_a.health.debt_to_equity, comparison.result_b.health.debt_to_equity),
        ]
        growth_metrics = [
            ("Rev CAGR 3y", comparison.result_a.growth.revenue_cagr_3y, comparison.result_b.growth.revenue_cagr_3y),
            ("PAT CAGR 3y", comparison.result_a.growth.pat_cagr_3y, comparison.result_b.growth.pat_cagr_3y),
            ("FCF Yield", comparison.result_a.growth.fcf_yield, comparison.result_b.growth.fcf_yield),
        ]
        
        console.print(_render_compare_chart("Valuation Chart", ticker_a, ticker_b, valuation_metrics))
        console.print(_render_compare_chart("Health Chart", ticker_a, ticker_b, health_metrics))
        console.print(_render_compare_chart("Growth Chart", ticker_a, ticker_b, growth_metrics))
"""

if "_render_compare_chart(\"Valuation Chart" not in content:
    content = content.replace("console.print(table)\n\n        if not json_output:", compare_chart_patch + "\n        if not json_output:")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Unicode fix and compare patch applied.")

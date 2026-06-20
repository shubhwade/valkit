import os

path = r"c:\Users\Shubh\OneDrive\Documents\Desktop\telmus\telmus\cli\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

funcs = """
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
        bar_str = "█" * max(1, bar_len)
        if value < 0:
            bar_str = f"[red]{bar_str}[/red]"
        else:
            bar_str = f"[{color}]{bar_str}[/{color}]"
            
        table.add_row(metric, f"{value:,.2f}", bar_str)
        
    return table

def _render_compare_chart(title: str, ticker_a: str, ticker_b: str, metrics: list[tuple[str, object|None, object|None]]) -> Table:
    table = Table(title=title, show_header=True, header_style="bold magenta", box=None)
    table.add_column("Metric", style="bold")
    table.add_column(f"{ticker_a} (teal)", justify="right")
    table.add_column(f"{ticker_b} (coral)", justify="right")
    
    all_vals = []
    for _, a, b in metrics:
        if a is not None and isinstance(a, (int, float)): all_vals.append(abs(a))
        if b is not None and isinstance(b, (int, float)): all_vals.append(abs(b))
    max_val = max(all_vals + [0.001])
    
    for metric, val_a, val_b in metrics:
        def make_bar(v, c):
            if v is None or not isinstance(v, (int, float)): return "n/a"
            bar_len = int((abs(v) / max_val) * 15)
            bar_str = "█" * max(1, bar_len)
            col = "red" if v < 0 else c
            return f"{v:,.2f} [{col}]{bar_str}[/{col}]"
            
        table.add_row(metric, make_bar(val_a, "cyan"), make_bar(val_b, "magenta"))
        
    return table
"""

# Insert funcs before _print_scan
if "def _render_bar_chart" not in content:
    content = content.replace("def _print_scan(result: ScanResult) -> None:", funcs + "\n\ndef _print_scan(result: ScanResult) -> None:")

# Inject charts into _print_scan
print_scan_replacement = """    console.print(_render_section("Valuation", valuation_metrics))
    console.print(_render_bar_chart("Valuation Chart", valuation_metrics, "cyan"))
    console.print(_render_section("Health", health_metrics))
    console.print(_render_bar_chart("Health Chart", health_metrics, "cyan"))
    console.print(_render_section("Growth", growth_metrics))
    console.print(_render_bar_chart("Growth Chart", growth_metrics, "cyan"))
    console.print(Panel(result.analyst_brief, title="Analyst brief", expand=False))"""

target = """    console.print(_render_section("Valuation", valuation_metrics))
    console.print(_render_section("Health", health_metrics))
    console.print(_render_section("Growth", growth_metrics))
    console.print(Panel(result.analyst_brief, title="Analyst brief", expand=False))"""
if target in content:
    content = content.replace(target, print_scan_replacement)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for single scan charts.")

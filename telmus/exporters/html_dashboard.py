from __future__ import annotations
import typing

import json
import datetime
from telmus.core.result import ScanResult, CompareResult


def get_company_logo_url(ticker: str, info: dict | None = None) -> str:
    import yfinance as yf

    try:
        if info is None:
            t = yf.Ticker(ticker)
            info = getattr(t, "info", {}) or {}
        website = info.get("website", "")
        if website:
            domain = (
                website.replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
                .replace("www.", "")
            )
            return f"https://logo.clearbit.com/{domain}"
    except Exception:
        pass
    return ""


class HtmlDashboardExporter:
    def _fmt(self, val: typing.Any) -> str:
        if val is None:
            return "n/a"
        if isinstance(val, (int, float)):
            return f"{val:,.2f}"
        return str(val)

    def _fmt_pct(self, val: typing.Any) -> str:
        if val is None:
            return "n/a"
        if isinstance(val, (int, float)):
            return f"{val * 100:,.2f}%"
        return str(val)

    def _get_winner_details(
        self,
        metric_name: str,
        val_a: typing.Any,
        val_b: typing.Any,
        ticker_a: str,
        ticker_b: str,
    ) -> tuple[str | None, str]:
        if val_a is None and val_b is None:
            return None, "Draw"
        if val_a is None:
            return "B", ticker_b
        if val_b is None:
            return "A", ticker_a

        try:
            a = float(val_a)
            b = float(val_b)
        except (TypeError, ValueError):
            return None, "Draw"

        lower_better = [
            "P/E Ratio",
            "P/B Ratio",
            "EV/EBITDA",
            "Debt / Equity",
            "Debt/Equity",
        ]
        is_lower_better = any(lb.lower() in metric_name.lower() for lb in lower_better)

        if a == b:
            return None, "Tie"

        if is_lower_better:
            if "ratio" in metric_name.lower() or "ebitda" in metric_name.lower():
                if a < 0 and b >= 0:
                    return "B", ticker_b
                if b < 0 and a >= 0:
                    return "A", ticker_a
            return ("A", ticker_a) if a < b else ("B", ticker_b)
        else:
            return ("A", ticker_a) if a > b else ("B", ticker_b)

    # ─── Shared HTML head/style block ──────────────────────────────────────────
    def _head_block(self, title: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        :root {{
            --bg:        #050505;
            --card:      #0c0c0c;
            --border:    #1a1a1a;
            --border-hl: #2a2a2a;
            --text:      #e5e5e5;
            --text-dim:  #737373;
            --text-mute: #525252;
            --teal:      #00d4aa;
            --coral:     #f78166;
            --amber:     #e3b341;
            --indigo:    #818cf8;
            --teal-10:   rgba(0,212,170,0.10);
            --teal-20:   rgba(0,212,170,0.20);
            --coral-10:  rgba(247,129,102,0.10);
            --coral-20:  rgba(247,129,102,0.20);
            --amber-10:  rgba(227,179,65,0.10);
            --amber-20:  rgba(227,179,65,0.20);
        }}

        body {{
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            padding: 2rem 1.5rem;
            line-height: 1.6;
        }}
        @media (min-width: 1024px) {{ body {{ padding: 3rem 4rem; }} }}

        .container {{ max-width: 1280px; margin: 0 auto; }}

        /* Typography */
        .font-mono {{ font-family: 'JetBrains Mono', 'Consolas', monospace; }}
        h1, h2, h3 {{ font-family: 'JetBrains Mono', monospace; }}
        h1 {{ font-size: 1.875rem; font-weight: 800; color: #fff; letter-spacing: -0.02em; }}
        .section-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.625rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--text-mute);
            margin-bottom: 0.5rem;
        }}
        .section-title {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875rem;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.01em;
        }}

        /* Card system */
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: border-color 0.2s ease;
        }}
        .card:hover {{ border-color: var(--border-hl); }}

        /* KPI cards */
        .kpi-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
        }}
        .kpi-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.625rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-dim);
            margin-top: 0.5rem;
        }}
        .kpi-desc {{
            font-size: 0.625rem;
            color: var(--text-mute);
            margin-top: 0.25rem;
        }}

        /* Grid layouts */
        .grid-4 {{ display: grid; grid-template-columns: 1fr; gap: 1rem; }}
        @media (min-width: 640px) {{ .grid-4 {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (min-width: 1024px) {{ .grid-4 {{ grid-template-columns: repeat(4, 1fr); }} }}

        .grid-3 {{ display: grid; grid-template-columns: 1fr; gap: 1rem; }}
        @media (min-width: 768px) {{ .grid-3 {{ grid-template-columns: repeat(3, 1fr); }} }}

        .grid-2 {{ display: grid; grid-template-columns: 1fr; gap: 1rem; }}
        @media (min-width: 1024px) {{ .grid-2 {{ grid-template-columns: repeat(2, 1fr); }} }}

        .grid-4 > div, .grid-3 > div, .grid-2 > div {{ min-width: 0; max-width: 100%; overflow: hidden; }}

        .stack {{ display: flex; flex-direction: column; gap: 1rem; }}

        /* Chart explanation */
        .chart-explain {{
            font-size: 0.6875rem;
            color: var(--text-mute);
            line-height: 1.5;
            margin-top: 0.625rem;
            padding-top: 0.625rem;
            border-top: 1px solid var(--border);
        }}
        .chart-explain strong {{ color: var(--text-dim); font-weight: 600; }}

        /* Colors */
        .c-teal {{ color: var(--teal); }}
        .c-coral {{ color: var(--coral); }}
        .c-amber {{ color: var(--amber); }}
        .c-dim {{ color: var(--text-dim); }}
        .c-mute {{ color: var(--text-mute); }}
        .c-white {{ color: #fff; }}

        /* Badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.625rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.625rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .badge-teal {{ background: var(--teal-10); color: var(--teal); border: 1px solid var(--teal-20); }}
        .badge-coral {{ background: var(--coral-10); color: var(--coral); border: 1px solid var(--coral-20); }}
        .badge-amber {{ background: var(--amber-10); color: var(--amber); border: 1px solid var(--amber-20); }}
        .badge-dim {{ background: rgba(115,115,115,0.1); color: var(--text-dim); border: 1px solid rgba(115,115,115,0.2); }}

        /* Checklist items */
        .check-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border: 1px solid;
            transition: all 0.15s ease;
        }}
        .check-pass {{ background: var(--teal-10); border-color: var(--teal-20); }}
        .check-fail {{ background: var(--coral-10); border-color: var(--coral-20); }}
        .check-icon {{ font-size: 1rem; flex-shrink: 0; }}
        .check-name {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.6875rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text);
        }}
        .check-desc {{ font-size: 0.625rem; color: var(--text-mute); }}

        /* Gauge container */
        .gauge-wrap {{
            position: relative;
            width: 100%;
            max-width: 180px;
            aspect-ratio: 2 / 1;
            margin: 0 auto;
        }}
        .gauge-center {{
            position: absolute;
            bottom: 0.25rem;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
        }}
        .gauge-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.375rem;
            font-weight: 800;
            color: #fff;
        }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        thead tr {{ border-bottom: 1px solid var(--border); }}
        th {{
            padding: 0.75rem 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.625rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-mute);
        }}
        tbody tr {{ border-bottom: 1px solid var(--border); transition: background 0.15s; }}
        tbody tr:hover {{ background: rgba(255,255,255,0.015); }}
        td {{
            padding: 0.75rem 1rem;
            font-size: 0.8125rem;
        }}
        td.mono {{ font-family: 'JetBrains Mono', monospace; }}

        /* Chart container */
        .chart-box {{ position: relative; width: 100%; max-width: 100%; overflow: hidden; }}

        /* Analyst brief */
        .brief-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-left: 3px solid var(--teal);
            border-radius: 12px;
            padding: 1.5rem 2rem;
        }}
        .brief-text {{ color: var(--text); font-size: 0.875rem; line-height: 1.7; font-weight: 500; }}

        /* Red flag banner */
        .flag-clean {{
            background: transparent;
            border: none;
            border-left: 3px solid var(--teal);
            color: var(--teal);
            padding: 1rem 1.5rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 0.875rem;
        }}
        .flag-table {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }}

        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 1rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }}
        .header-sub {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.6875rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-dim);
            margin-top: 0.375rem;
        }}
        .header-quote {{
            font-size: 0.8125rem;
            font-style: italic;
            color: var(--text-mute);
            margin-top: 0.75rem;
            max-width: 60ch;
        }}

        /* Footer */
        footer {{
            border-top: 1px solid var(--border);
            padding-top: 1.5rem;
            margin-top: 2rem;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.6875rem;
            color: var(--text-mute);
        }}
        footer code {{
            background: var(--card);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            color: var(--text-dim);
        }}

        /* Dot indicator */
        .dot {{
            display: inline-block;
            width: 4px;
            height: 14px;
            border-radius: 2px;
            margin-right: 0.5rem;
            vertical-align: middle;
        }}

        /* Compare company header */
        .company-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .company-avatar {{
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.125rem;
        }}

        /* Winner cell */
        .winner-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.25rem 0.625rem;
            border-radius: 4px;
            font-size: 0.6875rem;
            font-weight: 700;
        }}

        /* Screen row severity left-border */
        .sev-high {{ border-left: 3px solid var(--coral); background: var(--coral-10); }}
        .sev-medium {{ border-left: 3px solid var(--amber); background: var(--amber-10); }}
        .sev-low {{ border-left: 3px solid var(--teal); background: var(--teal-10); }}

        /* Sortable th */
        th.sortable {{ cursor: pointer; user-select: none; }}
        th.sortable:hover {{ color: var(--teal); }}

        /* Metrics table value styling */
        .metric-row {{ display: flex; justify-content: space-between; padding: 0.625rem 0; border-bottom: 1px solid var(--border); }}
        .metric-row:last-child {{ border-bottom: none; }}
        .metric-key {{ font-size: 0.8125rem; color: var(--text-dim); }}
        .metric-val {{ font-family: 'JetBrains Mono', monospace; font-size: 0.8125rem; font-weight: 600; }}

        @media print {{
          * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
          body {{ background: white !important; color: #0d1117 !important; }}
          #printBtn {{ display: none !important; }}
          .dashboard-container {{ background: white !important; padding: 1rem !important; }}
          .kpi-card {{ background: #f8f9fa !important; border: 1px solid #dee2e6 !important; break-inside: avoid; }}
          .chart-card {{ background: #f8f9fa !important; border: 1px solid #dee2e6 !important; break-inside: avoid; }}
          .gauge-card {{ background: #f8f9fa !important; border: 1px solid #dee2e6 !important; break-inside: avoid; }}
          .analyst-brief {{ background: #f0fdf4 !important; border-left: 4px solid #00d4aa !important; break-inside: avoid; }}
          .header-section {{ background: #0d1117 !important; color: white !important; -webkit-print-color-adjust: exact !important; }}
          canvas {{ max-width: 100% !important; }}
          @page {{ size: A4 landscape; margin: 1cm; }}
          .kpi-row {{ page-break-inside: avoid; }}
          .gauge-row {{ page-break-inside: avoid; }}
          .charts-row {{ page-break-inside: avoid; }}
          .piotroski-checklist {{ page-break-inside: avoid; }}
        }}
    </style>
</head>"""

    def _footer_block(self) -> str:
        return """
        <footer>
            <div>Generated by <span style="color:var(--text-dim);font-weight:700;">telmus v{telmus_version}</span> | <code>pip install telmus</code></div>
            <div>Data via Yahoo Finance | Not financial advice</div>
        </footer>"""

    # ═══════════════════════════════════════════════════════════════════════════
    # SCAN DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    def export_scan(self, result: ScanResult, path: str) -> None:

        def _safe_get(obj, attr, default=0.0):
            try:
                val = getattr(obj, attr)
                return val if val is not None else default
            except Exception:
                return default

        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pe = _safe_get(result.valuation, "pe_ratio", 0.0)
        pio = _safe_get(result.health, "piotroski_f", 0)
        altman = _safe_get(result.health, "altman_z", 0.0)
        rev_cagr = _safe_get(result.growth, "revenue_cagr_3y", 0.0)
        fcf_yield = _safe_get(result.growth, "fcf_yield", 0.0)
        m_score = result.beneish_m if result.beneish_m is not None else 0.0

        # ── Color logic ──
        def _kpi_color(val, thresholds):
            """Return CSS color var based on thresholds list of (test, color)."""
            for test_fn, color in thresholds:
                if test_fn(val):
                    return color
            return "var(--text-dim)"

        pe_text = self._fmt(pe)
        if pe is None:
            pe_color = "var(--text-dim)"
        elif 0 <= pe < 20:
            pe_color = "var(--teal)"
        elif 20 <= pe <= 35:
            pe_color = "var(--amber)"
        else:
            pe_color = "var(--coral)"

        pio_text = f"{pio}/9" if pio is not None else "n/a"
        if pio is None:
            pio_color = "var(--text-dim)"
        elif pio >= 7:
            pio_color = "var(--teal)"
        elif pio >= 5:
            pio_color = "var(--amber)"
        else:
            pio_color = "var(--coral)"

        altman_text = self._fmt(altman)
        if altman is None:
            altman_color = "var(--text-dim)"
        elif altman > 2.6:
            altman_color = "var(--teal)"
        elif altman >= 1.1:
            altman_color = "var(--amber)"
        else:
            altman_color = "var(--coral)"

        cagr_text = self._fmt_pct(rev_cagr)
        if rev_cagr is None:
            cagr_color = "var(--text-dim)"
        elif rev_cagr > 0:
            cagr_color = "var(--teal)"
        else:
            cagr_color = "var(--coral)"

        # ── Piotroski individual signals ──

        signals_desc = {
            "ROA Positive": "Company is profitable",
            "CFO Positive": "Operations generate cash",
            "ROA Improving": "Profitability improving",
            "Low Accruals": "Earnings quality is high",
            "Leverage Falling": "Debt burden reducing",
            "Liquidity Rising": "Short-term health improving",
            "No Dilution": "No new shares issued",
            "Gross Margin Rising": "Pricing power improving",
            "Asset Turnover Rising": "Using assets efficiently",
        }

        # Build checklist HTML
        checklist_items = []
        piotroski_signals = getattr(result.health, "piotroski_signals", {})
        if not piotroski_signals:
            piotroski_signals = {k: False for k in signals_desc}

        for name, desc in signals_desc.items():
            passed = piotroski_signals.get(name, False)
            css = "check-pass" if passed else "check-fail"
            icon_color = "var(--teal)" if passed else "var(--coral)"
            icon = "✔" if passed else "✘"
            checklist_items.append(f"""
                <div class="check-item {css}">
                    <span class="check-icon" style="color:{icon_color}">{icon}</span>
                    <div>
                        <div class="check-name">{name}</div>
                        <div class="check-desc">{desc}</div>
                    </div>
                </div>""")

        # Radar chart data (1 for pass, 0 for fail)
        signal_names = list(signals_desc.keys())
        signal_values = [
            1 if piotroski_signals.get(s, False) else 0 for s in signal_names
        ]


        # Analyst brief badges
        val_status = (result.valuation.vs_sector or "FAIR").upper()
        if val_status == "CHEAP":
            val_badge_cls = "badge-teal"
        elif val_status == "EXPENSIVE":
            val_badge_cls = "badge-coral"
        else:
            val_badge_cls = "badge-dim"

        pio_score = pio if pio is not None else 0
        if pio_score >= 7:
            health_badge_cls = "badge-teal"
            health_text = "HEALTH: STRONG"
        elif pio_score >= 5:
            health_badge_cls = "badge-amber"
            health_text = "HEALTH: ADEQUATE"
        else:
            health_badge_cls = "badge-coral"
            health_text = "HEALTH: WEAK"

        if rev_cagr is not None and rev_cagr > 0:
            growth_badge_cls = "badge-teal"
            growth_text = "GROWTH: POSITIVE"
        else:
            growth_badge_cls = "badge-coral"
            growth_text = "GROWTH: DECLINING"

        # Red flags
        FLAG_MEANINGS = {
            "negative_fcf": "Free Cash Flow is negative, indicating cash burn",
            "negative_revenue_growth": "Revenue is declining, showing contraction",
            "high_debt": "Debt to Equity ratio is high, increasing credit risk",
            "weak_piotroski": "Low Piotroski score indicates weak core business health",
            "distress_z": "Altman Z-Score indicates high risk of credit distress",
            "expensive_sector": "Valuation is expensive relative to peer sector median",
            "high_leverage": "High leverage ratio increases financial risk",
            "low_current_ratio": "Current ratio is below safe liquidity threshold",
            "low_interest_coverage": "Interest coverage is weak, indicating debt service concerns",
        }

        if not result.red_flags:
            flags_html = f"""
            <div class="flag-clean">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" width="22" height="22">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>No Red Flags Detected — Beneish M-Score of {m_score:.2f} indicates low manipulation risk</span>
            </div>"""
        else:
            rows = []
            for flag in result.red_flags:
                sev = flag.severity.upper()
                if sev == "HIGH":
                    badge_cls = "badge-coral"
                elif sev == "MEDIUM":
                    badge_cls = "badge-amber"
                else:
                    badge_cls = "badge-teal"
                meaning = FLAG_MEANINGS.get(flag.type, "Triggered threshold alert")
                rows.append(f"""
                <tr>
                    <td class="mono" style="color:#fff;font-weight:600;">{flag.type}</td>
                    <td class="mono c-dim">{self._fmt(flag.value)}</td>
                    <td><span class="badge {badge_cls}">{sev}</span></td>
                    <td style="color:var(--text-dim)">{meaning}</td>
                </tr>""")
            flags_html = f"""
            <div class="flag-table">
                <div style="margin-bottom:1rem;">
                    <span class="dot" style="background:var(--coral);"></span>
                    <span class="section-title">Red Flags ({len(result.red_flags)})</span>
                </div>
                <div style="overflow-x:auto;">
                    <table>
                        <thead><tr>
                            <th>Flag</th><th>Value</th><th>Severity</th><th>What it means</th>
                        </tr></thead>
                        <tbody>{"".join(rows)}</tbody>
                    </table>
                </div>
            </div>"""

        # Chart values
        pe_val = pe if pe is not None else 0.0
        pb_val = _safe_get(result.valuation, "pb_ratio", 0.0)
        ev_val = _safe_get(result.valuation, "ev_ebitda", 0.0)
        rev_cagr_pct = (rev_cagr or 0.0) * 100.0
        pat_cagr_pct = (result.growth.pat_cagr_3y or 0.0) * 100.0
        fcf_yield_pct = (fcf_yield or 0.0) * 100.0

        # Financial metrics table
        de_val = result.health.debt_to_equity or 0.0
        cr_val = result.health.current_ratio or 0.0
        ic_val = result.health.interest_coverage or 0.0
        margin_trend = result.growth.margin_trend or "n/a"

        def _metric_color(val, good_fn):
            if val is None:
                return "var(--text-dim)"
            return "var(--teal)" if good_fn(val) else "var(--coral)"

        de_color = _metric_color(de_val, lambda v: v < 1.5)
        cr_color = _metric_color(cr_val, lambda v: v > 1.0)
        ic_color = _metric_color(ic_val, lambda v: v > 3.0)

        logo_url = get_company_logo_url(result.ticker)
        html_content = f"""{self._head_block(f"telmus — {result.company} ({result.ticker}) Analysis")}
<style>
@media print {{
  @page {{
    size: A4 landscape;
    margin: 0.5cm;
  }}
  #printBtn {{ display: none !important; }}
  body {{
    zoom: 50%;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
}}
</style>
<body>
    <div class="container stack">

        <!-- ═══ HEADER ═══ -->
        <header class="header-section" style="position:relative; padding:1.5rem; border-radius:12px; border:1px solid var(--border);">

            <div style="display:flex;justify-content:space-between;align-items:center;gap:1.5rem;">
                <img src="{logo_url}" 
                     onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"
                     style="width:56px;height:56px;border-radius:50%;object-fit:contain;background:white;padding:4px;">
                <div style="display:{"none" if logo_url else "flex"};align-items:center;justify-content:center;width:56px;height:56px;border-radius:50%;background:var(--teal-10);border:1px solid var(--teal-20);color:var(--teal);font-family:'JetBrains Mono', monospace;font-weight:700;font-size:1.5rem;" class="letter-avatar">{result.ticker[0]}</div>
                <div style="flex:1;">
                    <h1 style="margin-bottom:0;font-size:2rem;line-height:1.2;">{result.company}</h1>
                    <div class="header-sub" style="margin-top:0.25rem;">{result.ticker} · {result.exchange} · Last scanned: {scan_date}</div>
                    <div class="header-quote" style="margin-top:0.5rem;color:var(--text-dim);font-style:italic;">"{result.analyst_brief}"</div>
                </div>
                <div style="display:flex;align-items:center;gap:1rem;
                margin-left:auto;">
                  <span style="color:#00d4aa;
                  font-family:'JetBrains Mono',monospace;
                  font-weight:700;font-size:0.85rem;">telmus v0.2.6</span>
                  <button id="printBtn" onclick="window.print()"
                  style="background:transparent;
                  color:#ffffff;
                  border:1px solid #ffffff;
                  padding:0.3rem 1rem;
                  border-radius:4px;
                  font-size:0.8rem;
                  font-weight:600;
                  cursor:pointer;
                  font-family:'JetBrains Mono',monospace;
                  letter-spacing:0.05em;">
                  PRINT REPORT
                  </button>
                </div>
            </div>
        </header>

        <!-- ═══ KPI ROW ═══ -->
        <div>
            <div class="section-label">Key Metrics</div>
            <div class="grid-4">
                <div class="card">
                    <div class="kpi-value" style="color:{pe_color}">{pe_text}</div>
                    <div class="kpi-label">P/E Ratio</div>
                    <div class="kpi-desc">Price per unit of earnings</div>
                </div>
                <div class="card">
                    <div class="kpi-value" style="color:{pio_color}">{pio_text}</div>
                    <div class="kpi-label">Piotroski F-Score</div>
                    <div class="kpi-desc">Financial health (higher = stronger)</div>
                </div>
                <div class="card">
                    <div class="kpi-value" style="color:{altman_color}">{altman_text}</div>
                    <div class="kpi-label">Altman Z-Score</div>
                    <div class="kpi-desc">Bankruptcy risk (&gt;2.6 = safe)</div>
                </div>
                <div class="card">
                    <div class="kpi-value" style="color:{cagr_color}">{cagr_text}</div>
                    <div class="kpi-label">Revenue CAGR (3Y)</div>
                    <div class="kpi-desc">3-year revenue growth rate</div>
                </div>
            </div>
        </div>

        <!-- ═══ RADAR + VALUATION ═══ -->
        <div class="grid-2">
            <!-- Piotroski Radar -->
            <div class="card">
                <div class="section-label">Signal Analysis</div>
                <div class="section-title" style="margin-bottom:0.5rem;">
                    <span class="dot" style="background:var(--teal);"></span>Piotroski Radar — {pio_score}/9
                </div>
                <div class="chart-box" style="height:280px;">
                    <canvas id="radarPio"></canvas>
                </div>
                <div class="chart-explain">
                    Each point on the radar represents one of 9 financial health checks. <strong>Teal points = passed</strong>, <strong>coral points = failed</strong>. A wider shape means the company passes more checks — 7+/9 signals a strong business.
                </div>
            </div>
            <!-- Valuation Benchmarks -->
            <div class="card">
                <div class="section-label">Valuation</div>
                <div class="section-title" style="margin-bottom:0.5rem;">
                    <span class="dot" style="background:var(--teal);"></span>Valuation Benchmarks
                </div>
                <div class="chart-box" style="height:280px;">
                    <canvas id="chartValuation" style="height:220px;"></canvas>
                </div>
                <div class="chart-explain">
                    <div style="font-weight:600;margin-bottom:0.5rem;color:#e5e5e5;">What this means:</div>
                    <div style="display:grid;gap:0.5rem;line-height:1.5;">
                        <div><strong style="color:var(--teal)">P/E Ratio</strong>: Shows how much investors are paying for ₹1 of earnings. Values under 20 (dashed line) often indicate a bargain.</div>
                        <div><strong style="color:var(--teal)">P/B Ratio</strong>: Compares market value to the company's actual assets. Lower bars represent cheaper valuations.</div>
                        <div><strong style="color:var(--teal)">EV/EBITDA</strong>: A pure measure of value that includes debt. Values below 10 are generally considered attractive.</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ═══ GAUGES + GROWTH ═══ -->
        <div class="grid-2">
            <!-- 3 Gauges in a row -->
            <div class="card">
                <div class="section-label">Score Gauges</div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;">
                    <div style="text-align:center;">
                        <div class="gauge-wrap"><canvas id="gaugePio"></canvas>
                            <div class="gauge-center"><span class="gauge-value" style="font-size:1rem;">{pio_text}</span></div>
                        </div>
                        <div class="section-label" style="margin-top:0.25rem;">Piotroski F</div>
                    </div>
                    <div style="text-align:center;">
                        <div class="gauge-wrap"><canvas id="gaugeAltman" style="height:200px;"></canvas>
                            <div class="gauge-center"><span class="gauge-value" style="font-size:1rem;">{altman_text}</span></div>
                        </div>
                        <div class="section-label" style="margin-top:0.25rem;">Altman Z</div>
                    </div>
                    <div style="text-align:center;">
                        <div class="gauge-wrap"><canvas id="gaugeFCF" style="height:200px;"></canvas>
                            <div class="gauge-center"><span class="gauge-value" style="font-size:1rem;">{self._fmt_pct(fcf_yield)}</span></div>
                        </div>
                        <div class="section-label" style="margin-top:0.25rem;">FCF Yield</div>
                    </div>
                </div>
                <div class="chart-explain">
                    <strong>Piotroski F</strong> scores financial strength out of 9 (7+ = strong). <strong>Altman Z</strong> predicts bankruptcy risk (>2.6 = safe zone). <strong>FCF Yield</strong> shows how much free cash the company generates relative to its price.
                </div>
            </div>
            <!-- Growth Metrics -->
            <div class="card">
                <div class="section-label">Growth</div>
                <div class="section-title" style="margin-bottom:0.5rem;">
                    <span class="dot" style="background:var(--indigo);"></span>Growth Metrics (3Y CAGR)
                </div>
                <div class="chart-box" style="height:220px;">
                    <canvas id="chartGrowth" style="height:220px;"></canvas>
                </div>
                <div class="chart-explain">
                    <div style="font-weight:600;margin-bottom:0.5rem;color:#e5e5e5;">What this means:</div>
                    <div style="display:grid;gap:0.5rem;line-height:1.5;">
                        <div><strong style="color:var(--indigo)">Revenue & PAT CAGR</strong>: The average yearly growth in sales and profits over the last 3 years. Consistent green bars indicate a thriving, expanding business.</div>
                        <div><strong style="color:var(--indigo)">FCF Yield</strong>: Shows how efficiently the company turns its market cap into hard cash. High values mean the company generates excess cash to reinvest or return to shareholders.</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ═══ PIOTROSKI BREAKDOWN ═══ -->
        <div class="card">
            <div class="section-label">Breakdown</div>
            <div class="section-title" style="margin-bottom:1rem;">
                <span class="dot" style="background:var(--teal);"></span>Piotroski F-Score — {pio_score}/9 Signals Passed
            </div>
            <div class="grid-3">
                {"".join(checklist_items)}
            </div>
        </div>

        <!-- ═══ FINANCIAL METRICS TABLE ═══ -->
        <div class="card">
            <div class="section-label">Details</div>
            <div class="section-title" style="margin-bottom:1rem;">
                <span class="dot" style="background:var(--indigo);"></span>Financial Metrics
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 2rem;">
                <div>
                    <div class="metric-row">
                        <span class="metric-key">P/E Ratio</span>
                        <span class="metric-val" style="color:{pe_color}">{pe_text}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">P/B Ratio</span>
                        <span class="metric-val" style="color:var(--text)">{self._fmt(result.valuation.pb_ratio)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">EV/EBITDA</span>
                        <span class="metric-val" style="color:var(--text)">{self._fmt(result.valuation.ev_ebitda)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">Debt / Equity</span>
                        <span class="metric-val" style="color:{de_color}">{self._fmt(de_val)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">Current Ratio</span>
                        <span class="metric-val" style="color:{cr_color}">{self._fmt(cr_val)}</span>
                    </div>
                </div>
                <div>
                    <div class="metric-row">
                        <span class="metric-key">Interest Coverage</span>
                        <span class="metric-val" style="color:{ic_color}">{self._fmt(ic_val)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">Revenue CAGR (3Y)</span>
                        <span class="metric-val" style="color:{cagr_color}">{cagr_text}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">PAT CAGR (3Y)</span>
                        <span class="metric-val" style="color:var(--text)">{self._fmt_pct(result.growth.pat_cagr_3y)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">FCF Yield</span>
                        <span class="metric-val" style="color:var(--text)">{self._fmt_pct(fcf_yield)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-key">Margin Trend</span>
                        <span class="metric-val" style="color:var(--text)">{margin_trend}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ═══ ANALYST BRIEF ═══ -->
        <div class="brief-card">
            <div class="section-label">Analysis</div>
            <div class="section-title" style="margin-bottom:0.75rem;">AI Analyst Brief</div>
            <p class="brief-text">{result.analyst_brief}</p>
            <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:1rem;">
                <span class="badge {val_badge_cls}">VALUATION: {val_status}</span>
                <span class="badge {health_badge_cls}">{health_text}</span>
                <span class="badge {growth_badge_cls}">{growth_text}</span>
            </div>
        </div>

        <!-- ═══ RED FLAGS ═══ -->
        {flags_html}

        <!-- ═══ FOOTER ═══ -->
        {self._footer_block()}

    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
        // ─── Chart.js global defaults ───
        Chart.defaults.color = '#525252';
        Chart.defaults.borderColor = '#141414';
        Chart.defaults.font.family = "'JetBrains Mono', monospace";
        Chart.defaults.font.size = 10;

        // ─── Value label plugin (draws value on top of each bar) ───
        const valueLabelPlugin = {{
            id: 'valueLabels',
            afterDatasetsDraw(chart) {{
                const ctx = chart.ctx;
                ctx.save();
                chart.data.datasets.forEach((dataset, i) => {{
                    const meta = chart.getDatasetMeta(i);
                    meta.data.forEach((bar, index) => {{
                        const value = dataset.data[index];
                        if (value === null || value === undefined) return;
                        const label = typeof value === 'number' ? (Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(1)) : value;
                        ctx.fillStyle = '#8a8a8a';
                        ctx.font = "600 9px 'JetBrains Mono'";
                        ctx.textAlign = 'center';
                        if (chart.options.indexAxis === 'y') {{
                            ctx.textAlign = 'left';
                            ctx.fillText(label, bar.x + 6, bar.y + 3.5);
                        }} else {{
                            ctx.fillText(label, bar.x, bar.y - 8);
                        }}
                    }});
                }});
                ctx.restore();
            }}
        }};
        Chart.register(valueLabelPlugin);

        // ─── Benchmark line plugin ───
        const benchmarkPlugin = {{
            id: 'benchmarkLines',
            afterDraw(chart, args, options) {{
                const ctx = chart.ctx;
                const left = chart.chartArea.left;
                const right = chart.chartArea.right;
                const y = chart.scales.y;
                ctx.save();
                (options.lines || []).forEach(line => {{
                    const yPos = y.getPixelForValue(line.value);
                    if (yPos >= chart.chartArea.top && yPos <= chart.chartArea.bottom) {{
                        ctx.strokeStyle = line.color || '#333';
                        ctx.lineWidth = 1;
                        ctx.setLineDash([3, 3]);
                        ctx.beginPath();
                        ctx.moveTo(left, yPos);
                        ctx.lineTo(right, yPos);
                        ctx.stroke();
                        ctx.fillStyle = '#525252';
                        ctx.font = "500 9px 'JetBrains Mono'";
                        ctx.fillText(line.label, left + 6, yPos - 5);
                    }}
                }});
                ctx.restore();
            }}
        }};
        Chart.register(benchmarkPlugin);

        const gaugeOpts = {{
            responsive: true,
            maintainAspectRatio: false,
            rotation: 270,
            circumference: 180,
            cutout: '82%',
            plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: false }}, valueLabels: false }}
        }};

        // ─── Piotroski Radar ───
        new Chart(document.getElementById('radarPio'), {{
            type: 'radar',
            data: {{
                labels: {json.dumps(signal_names)},
                datasets: [{{
                    label: 'Signals',
                    data: {json.dumps(signal_values)},
                    backgroundColor: 'rgba(0,212,170,0.08)',
                    borderColor: '#00d4aa',
                    borderWidth: 1.5,
                    pointBackgroundColor: {json.dumps(["#00d4aa" if v else "#f78166" for v in signal_values])},
                    pointBorderColor: '#0c0c0c',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 1,
                        ticks: {{ display: false }},
                        grid: {{ color: '#1a1a1a', lineWidth: 0.5 }},
                        angleLines: {{ color: '#1a1a1a', lineWidth: 0.5 }},
                        pointLabels: {{
                            color: '#999',
                            font: {{ family: "'JetBrains Mono'", size: 9, weight: '500' }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: false }},
                    valueLabels: false,
                    tooltip: {{
                        backgroundColor: '#1a1a1a',
                        titleColor: '#e5e5e5',
                        bodyColor: '#999',
                        borderColor: '#2a2a2a',
                        borderWidth: 1,
                        callbacks: {{
                            label: ctx => ctx.raw === 1 ? 'PASS' : 'FAIL'
                        }}
                    }}
                }}
            }}
        }});

        // ─── Gauges ───
        const pioScore = {pio_score};
        new Chart(document.getElementById('gaugePio'), {{
            type: 'doughnut',
            data: {{ datasets: [{{ data: [pioScore, Math.max(0, 9 - pioScore)], backgroundColor: [pioScore >= 7 ? '#00d4aa' : (pioScore >= 5 ? '#e3b341' : '#f78166'), '#141414'], borderWidth: 0 }}] }},
            options: gaugeOpts
        }});

        const altmanScore = {altman if altman is not None else 0.0};
        const cappedAlt = Math.min(10, Math.max(0, altmanScore));
        new Chart(document.getElementById('gaugeAltman'), {{
            type: 'doughnut',
            data: {{ datasets: [{{ data: [cappedAlt, 10 - cappedAlt], backgroundColor: [altmanScore > 2.6 ? '#00d4aa' : (altmanScore >= 1.1 ? '#e3b341' : '#f78166'), '#141414'], borderWidth: 0 }}] }},
            options: gaugeOpts
        }});

        const fcfY = {fcf_yield_pct};
        const cappedFCF = Math.min(50, Math.max(0, fcfY));
        new Chart(document.getElementById('gaugeFCF'), {{
            type: 'doughnut',
            data: {{ datasets: [{{ data: [cappedFCF, 50 - cappedFCF], backgroundColor: [fcfY > 0 ? '#00d4aa' : '#f78166', '#141414'], borderWidth: 0 }}] }},
            options: gaugeOpts
        }});

        // ─── Valuation Chart ───
        const peV = {pe_val}; const pbV = {pb_val}; const evV = {ev_val};
        new Chart(document.getElementById('chartValuation'), {{
            type: 'bar',
            data: {{
                labels: ['P/E', 'P/B', 'EV/EBITDA'],
                datasets: [{{
                    data: [peV, pbV, evV],
                    backgroundColor: [
                        peV < 20 ? '#00d4aa' : (peV <= 35 ? '#e3b341' : '#f78166'),
                        pbV < 3 ? '#00d4aa' : '#f78166',
                        evV < 10 ? '#00d4aa' : '#f78166'
                    ],
                    borderColor: 'transparent',
                    borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0
                }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                layout: {{ padding: {{ top: 20 }} }},
                plugins: {{
                    legend: {{ display: false }},
                    benchmarkLines: {{
                        lines: [
                            {{ value: 20, label: 'P/E fair (20)', color: '#333' }},
                            {{ value: 10, label: 'EV avg (10)', color: '#333' }}
                        ]
                    }}
                }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }},
                    y: {{ grid: {{ color: '#141414', lineWidth: 0.5 }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }}
                }}
            }}
        }});

        // ─── Growth Chart ───
        const revC = {rev_cagr_pct}; const patC = {pat_cagr_pct}; const fcfC = {fcf_yield_pct};
        new Chart(document.getElementById('chartGrowth'), {{
            type: 'bar',
            data: {{
                labels: ['Rev CAGR', 'PAT CAGR', 'FCF Yield'],
                datasets: [{{
                    data: [revC, patC, fcfC],
                    backgroundColor: [
                        revC > 0 ? '#00d4aa' : '#f78166',
                        patC > 0 ? '#00d4aa' : '#f78166',
                        fcfC > 0 ? '#00d4aa' : '#f78166'
                    ],
                    borderColor: [
                        revC > 0 ? '#00d4aa' : '#f78166',
                        patC > 0 ? '#00d4aa' : '#f78166',
                        fcfC > 0 ? '#00d4aa' : '#f78166'
                    ],
                    borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0
                }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                layout: {{ padding: {{ top: 20 }} }},
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }},
                    y: {{ grid: {{ color: '#141414', lineWidth: 0.5 }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }}
                }}
            }}
        }});
        }});
    </script>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPARE DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    def export_compare(self, result: CompareResult, path: str) -> None:
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ticker_a = result.ticker_a
        ticker_b = result.ticker_b
        res_a = result.result_a
        res_b = result.result_b

        # Build metrics for winner table
        metrics = [
            ("P/E Ratio", res_a.valuation.pe_ratio, res_b.valuation.pe_ratio, "ratio"),
            ("P/B Ratio", res_a.valuation.pb_ratio, res_b.valuation.pb_ratio, "ratio"),
            (
                "EV/EBITDA",
                res_a.valuation.ev_ebitda,
                res_b.valuation.ev_ebitda,
                "ratio",
            ),
            (
                "Piotroski F-Score",
                res_a.health.piotroski_f,
                res_b.health.piotroski_f,
                "score",
            ),
            ("Altman Z-Score", res_a.health.altman_z, res_b.health.altman_z, "score"),
            (
                "Debt/Equity",
                res_a.health.debt_to_equity,
                res_b.health.debt_to_equity,
                "ratio",
            ),
            (
                "Current Ratio",
                res_a.health.current_ratio,
                res_b.health.current_ratio,
                "score",
            ),
            (
                "Interest Coverage",
                res_a.health.interest_coverage,
                res_b.health.interest_coverage,
                "score",
            ),
            (
                "Revenue CAGR (3Y)",
                res_a.growth.revenue_cagr_3y,
                res_b.growth.revenue_cagr_3y,
                "percent",
            ),
            (
                "PAT CAGR (3Y)",
                res_a.growth.pat_cagr_3y,
                res_b.growth.pat_cagr_3y,
                "percent",
            ),
            ("FCF Yield", res_a.growth.fcf_yield, res_b.growth.fcf_yield, "percent"),
        ]

        table_rows = []
        for name, val_a, val_b, fmt_type in metrics:
            win_code, win_text = self._get_winner_details(
                name, val_a, val_b, ticker_a, ticker_b
            )
            if fmt_type == "percent":
                str_a = self._fmt_pct(val_a)
                str_b = self._fmt_pct(val_b)
            else:
                str_a = self._fmt(val_a)
                str_b = self._fmt(val_b)

            style_a = (
                'style="color:var(--teal);font-weight:700;"'
                if win_code == "A"
                else 'style="color:var(--text-dim);"'
            )
            style_b = (
                'style="color:var(--teal);font-weight:700;"'
                if win_code == "B"
                else 'style="color:var(--text-dim);"'
            )

            if win_code in ("A", "B"):
                win_display = f'<span class="winner-badge badge-teal">{win_text}</span>'
            else:
                win_display = '<span class="winner-badge badge-dim">Draw</span>'

            table_rows.append(f"""
                <tr>
                    <td style="color:#fff;font-weight:600;">{name}</td>
                    <td class="mono" {style_a}>{str_a}</td>
                    <td class="mono" {style_b}>{str_b}</td>
                    <td>{win_display}</td>
                </tr>""")

        # Chart data
        val_labels = ["P/E Ratio", "P/B Ratio", "EV/EBITDA"]
        val_a_data = [
            res_a.valuation.pe_ratio or 0.0,
            res_a.valuation.pb_ratio or 0.0,
            res_a.valuation.ev_ebitda or 0.0,
        ]
        val_b_data = [
            res_b.valuation.pe_ratio or 0.0,
            res_b.valuation.pb_ratio or 0.0,
            res_b.valuation.ev_ebitda or 0.0,
        ]

        health_labels = [
            "Piotroski F",
            "Altman Z",
            "Debt/Equity",
            "Current Ratio",
            "Interest Cov.",
        ]
        health_a = [
            res_a.health.piotroski_f or 0.0,
            res_a.health.altman_z or 0.0,
            res_a.health.debt_to_equity or 0.0,
            res_a.health.current_ratio or 0.0,
            res_a.health.interest_coverage or 0.0,
        ]
        health_b = [
            res_b.health.piotroski_f or 0.0,
            res_b.health.altman_z or 0.0,
            res_b.health.debt_to_equity or 0.0,
            res_b.health.current_ratio or 0.0,
            res_b.health.interest_coverage or 0.0,
        ]

        growth_labels = ["Revenue CAGR %", "PAT CAGR %", "FCF Yield %"]
        growth_a = [
            (res_a.growth.revenue_cagr_3y or 0.0) * 100.0,
            (res_a.growth.pat_cagr_3y or 0.0) * 100.0,
            (res_a.growth.fcf_yield or 0.0) * 100.0,
        ]
        growth_b = [
            (res_b.growth.revenue_cagr_3y or 0.0) * 100.0,
            (res_b.growth.pat_cagr_3y or 0.0) * 100.0,
            (res_b.growth.fcf_yield or 0.0) * 100.0,
        ]

        # Radar data for comparison
        signal_names_cmp = ["P/E", "P/B", "Piotroski", "Altman Z", "Rev CAGR"]

        # Normalize each metric to 0-1 for radar overlay
        def _norm(vals):
            mx = max(abs(v) for v in vals) if any(v != 0 for v in vals) else 1
            return [abs(v) / mx for v in vals]

        radar_raw_a = [
            res_a.valuation.pe_ratio or 0,
            res_a.valuation.pb_ratio or 0,
            res_a.health.piotroski_f or 0,
            res_a.health.altman_z or 0,
            (res_a.growth.revenue_cagr_3y or 0) * 100,
        ]
        radar_raw_b = [
            res_b.valuation.pe_ratio or 0,
            res_b.valuation.pb_ratio or 0,
            res_b.health.piotroski_f or 0,
            res_b.health.altman_z or 0,
            (res_b.growth.revenue_cagr_3y or 0) * 100,
        ]
        combined = [max(abs(radar_raw_a[i]), abs(radar_raw_b[i])) for i in range(5)]
        radar_norm_a = [
            abs(radar_raw_a[i]) / combined[i] if combined[i] != 0 else 0
            for i in range(5)
        ]
        radar_norm_b = [
            abs(radar_raw_b[i]) / combined[i] if combined[i] != 0 else 0
            for i in range(5)
        ]
        logo_url_a = get_company_logo_url(ticker_a)
        logo_url_b = get_company_logo_url(ticker_b)

        html_content = f"""{self._head_block(f"telmus — {ticker_a} vs {ticker_b} Comparison")}
<style>
@media print {{
  @page {{
    size: A4 landscape;
    margin: 0.5cm;
  }}
  #printBtn {{ display: none !important; }}
  body {{
    zoom: 50%;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
}}
</style>
<body>
    <div class="container stack">

        <!-- Header -->
        <header class="header-section" style="position:relative; padding:1.5rem; border-radius:12px; border:1px solid var(--border);">

            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <h1 style="margin-bottom:0;">{ticker_a} vs {ticker_b} — Head to Head</h1>
                    <div class="header-sub" style="margin-top:0.25rem;">Comparison scan · {scan_date}</div>
                </div>
                <div style="display:flex;align-items:center;gap:1rem;
                margin-left:auto;">
                  <span style="color:#00d4aa;
                  font-family:'JetBrains Mono',monospace;
                  font-weight:700;font-size:0.85rem;">telmus v0.2.6</span>
                  <button id="printBtn" onclick="window.print()"
                  style="background:transparent;
                  color:#ffffff;
                  border:1px solid #ffffff;
                  padding:0.3rem 1rem;
                  border-radius:4px;
                  font-size:0.8rem;
                  font-weight:600;
                  cursor:pointer;
                  font-family:'JetBrains Mono',monospace;
                  letter-spacing:0.05em;">
                  PRINT REPORT
                  </button>
                </div>
            </div>
        </header>

        <!-- Company Headers -->
        <div class="grid-2">
            <div class="card">
                <div class="company-header">
                    <img src="{logo_url_a}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" style="width:3rem;height:3rem;border-radius:50%;object-fit:contain;background:white;padding:4px;">
                    <div class="company-avatar" style="display:{"none" if logo_url_a else "flex"};background:var(--teal-10);border:1px solid var(--teal-20);color:var(--teal);">{ticker_a[0]}</div>
                    <div>
                        <div style="font-weight:700;color:#fff;">{res_a.company}</div>
                        <div class="font-mono" style="font-size:0.75rem;color:var(--text-dim);">{ticker_a} · {res_a.exchange}</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="company-header">
                    <img src="{logo_url_b}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" style="width:3rem;height:3rem;border-radius:50%;object-fit:contain;background:white;padding:4px;">
                    <div class="company-avatar" style="display:{"none" if logo_url_b else "flex"};background:var(--coral-10);border:1px solid var(--coral-20);color:var(--coral);">{ticker_b[0]}</div>
                    <div>
                        <div style="font-weight:700;color:#fff;">{res_b.company}</div>
                        <div class="font-mono" style="font-size:0.75rem;color:var(--text-dim);">{ticker_b} · {res_b.exchange}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Radar Overlay -->
        <div class="card">
            <div class="section-label">Overview</div>
            <div class="section-title" style="margin-bottom:1rem;">
                <span class="dot" style="background:var(--teal);"></span>Radar Comparison
            </div>
            <div class="chart-box" style="height:320px;max-width:480px;margin:0 auto;">
                <canvas id="radarCompare"></canvas>
            </div>
        </div>

        <!-- Grouped Bar Charts -->
        <div class="grid-3">
            <div class="card">
                <div class="section-label">Valuation</div>
                <div class="chart-box" style="height:220px;"><canvas id="chartValuation" style="height:220px;"></canvas></div>
                <div class="chart-explain">P/E, P/B and EV/EBITDA side by side. Lower bars usually mean cheaper valuation. Teal = {ticker_a}, coral = {ticker_b}.</div>
            </div>
            <div class="card">
                <div class="section-label">Health</div>
                <div class="chart-box" style="height:220px;"><canvas id="chartHealth"></canvas></div>
                <div class="chart-explain">Piotroski F (higher = stronger), Altman Z (higher = safer), Debt/Equity (lower = less risky), Current Ratio (>1 = liquid), Interest Coverage (higher = safer).</div>
            </div>
            <div class="card">
                <div class="section-label">Growth</div>
                <div class="chart-box" style="height:220px;"><canvas id="chartGrowth" style="height:220px;"></canvas></div>
                <div class="chart-explain">Revenue and profit growth rates over 3 years, plus free cash flow yield. Taller bars indicate stronger growth momentum.</div>
            </div>
        </div>

        <!-- Winner Table -->
        <div class="card">
            <div class="section-label">Results</div>
            <div class="section-title" style="margin-bottom:1rem;">
                <span class="dot" style="background:var(--teal);"></span>Head-to-Head Winner Table
            </div>
            <div style="overflow-x:auto;">
                <table>
                    <thead><tr>
                        <th>Metric</th><th>{ticker_a}</th><th>{ticker_b}</th><th>Winner</th>
                    </tr></thead>
                    <tbody>{"".join(table_rows)}</tbody>
                </table>
            </div>
        </div>

        {self._footer_block()}
    </div>

    <script>
        Chart.defaults.color = '#525252';
        Chart.defaults.borderColor = '#141414';
        Chart.defaults.font.family = "'JetBrains Mono', monospace";
        Chart.defaults.font.size = 10;

        // Value label plugin
        const valueLabelPlugin = {{
            id: 'valueLabels',
            afterDatasetsDraw(chart) {{
                const ctx = chart.ctx;
                ctx.save();
                chart.data.datasets.forEach((dataset, i) => {{
                    const meta = chart.getDatasetMeta(i);
                    meta.data.forEach((bar, index) => {{
                        const value = dataset.data[index];
                        if (value === null || value === undefined) return;
                        const label = typeof value === 'number' ? (Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(1)) : value;
                        ctx.fillStyle = '#8a8a8a';
                        ctx.font = "600 9px 'JetBrains Mono'";
                        ctx.textAlign = 'center';
                        ctx.fillText(label, bar.x, bar.y - 8);
                    }});
                }});
                ctx.restore();
            }}
        }};
        Chart.register(valueLabelPlugin);

        const chartOpts = {{
            responsive: true, maintainAspectRatio: false,
            layout: {{ padding: {{ top: 20 }} }},
            plugins: {{ legend: {{ labels: {{ color: '#999', font: {{ size: 10 }} }} }} }},
            scales: {{
                x: {{ grid: {{ display: false }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }},
                y: {{ grid: {{ color: '#141414', lineWidth: 0.5 }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }}
            }}
        }};

        // Radar Overlay
        new Chart(document.getElementById('radarCompare'), {{
            type: 'radar',
            data: {{
                labels: {json.dumps(signal_names_cmp)},
                datasets: [
                    {{
                        label: '{ticker_a}',
                        data: {json.dumps(radar_norm_a)},
                        backgroundColor: 'rgba(0,212,170,0.08)',
                        borderColor: '#00d4aa',
                        borderWidth: 1.5,
                        pointBackgroundColor: '#00d4aa',
                        pointBorderColor: '#0c0c0c',
                        pointBorderWidth: 2,
                        pointRadius: 4
                    }},
                    {{
                        label: '{ticker_b}',
                        data: {json.dumps(radar_norm_b)},
                        backgroundColor: 'rgba(247,129,102,0.08)',
                        borderColor: '#f78166',
                        borderWidth: 1.5,
                        pointBackgroundColor: '#f78166',
                        pointBorderColor: '#0c0c0c',
                        pointBorderWidth: 2,
                        pointRadius: 4
                    }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    r: {{
                        beginAtZero: true, max: 1,
                        ticks: {{ display: false }},
                        grid: {{ color: '#1a1a1a', lineWidth: 0.5 }},
                        angleLines: {{ color: '#1a1a1a', lineWidth: 0.5 }},
                        pointLabels: {{ color: '#999', font: {{ family: "'JetBrains Mono'", size: 10, weight: '500' }} }}
                    }}
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#999', font: {{ family: "'JetBrains Mono'", size: 10 }} }} }},
                    valueLabels: false
                }}
            }}
        }});

        // Valuation
        new Chart(document.getElementById('chartValuation'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(val_labels)},
                datasets: [
                    {{ label: '{ticker_a}', data: {json.dumps(val_a_data)}, backgroundColor: '#00d4aa', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }},
                    {{ label: '{ticker_b}', data: {json.dumps(val_b_data)}, backgroundColor: '#f78166', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }}
                ]
            }},
            options: chartOpts
        }});

        // Health
        new Chart(document.getElementById('chartHealth'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(health_labels)},
                datasets: [
                    {{ label: '{ticker_a}', data: {json.dumps(health_a)}, backgroundColor: '#00d4aa', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }},
                    {{ label: '{ticker_b}', data: {json.dumps(health_b)}, backgroundColor: '#f78166', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }}
                ]
            }},
            options: chartOpts
        }});

        // Growth
        new Chart(document.getElementById('chartGrowth'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(growth_labels)},
                datasets: [
                    {{ label: '{ticker_a}', data: {json.dumps(growth_a)}, backgroundColor: '#00d4aa', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }},
                    {{ label: '{ticker_b}', data: {json.dumps(growth_b)}, backgroundColor: '#f78166', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }}
                ]
            }},
            options: chartOpts
        }});
    </script>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

    # ═══════════════════════════════════════════════════════════════════════════
    # SCREEN DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    def export_screen(self, results: list[ScanResult], path: str) -> None:
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        n = len(results)

        pio_values = [
            r.health.piotroski_f for r in results if r.health.piotroski_f is not None
        ]
        pe_values = [
            r.valuation.pe_ratio for r in results if r.valuation.pe_ratio is not None
        ]
        no_flags_count = sum(1 for r in results if not r.red_flags)

        avg_pio = sum(pio_values) / len(pio_values) if pio_values else 0.0
        avg_pe = sum(pe_values) / len(pe_values) if pe_values else 0.0

        tickers = [r.ticker for r in results]
        pio_scores = [
            r.health.piotroski_f if r.health.piotroski_f is not None else 0
            for r in results
        ]
        pe_ratios = [
            r.valuation.pe_ratio if r.valuation.pe_ratio is not None else 0.0
            for r in results
        ]
        altman_scores = [
            r.health.altman_z if r.health.altman_z is not None else 0.0 for r in results
        ]

        table_rows = []
        for idx, r in enumerate(results, start=1):
            pe_str = (
                f"{r.valuation.pe_ratio:,.2f}"
                if r.valuation.pe_ratio is not None
                else "n/a"
            )
            alt_str = (
                f"{r.health.altman_z:,.2f}" if r.health.altman_z is not None else "n/a"
            )
            rev_str = (
                f"{(r.growth.revenue_cagr_3y or 0.0) * 100:,.2f}%"
                if r.growth.revenue_cagr_3y is not None
                else "n/a"
            )

            concern_lvl = (r.highest_concern or "LOW").upper()
            if concern_lvl == "HIGH":
                concern_cls = "badge-coral"
                row_cls = "sev-high"
            elif concern_lvl == "MEDIUM":
                concern_cls = "badge-amber"
                row_cls = "sev-medium"
            else:
                concern_cls = "badge-teal"
                row_cls = "sev-low"

            table_rows.append(f"""
                <tr class="{row_cls}">
                    <td class="mono c-dim" data-val="{idx}">{idx}</td>
                    <td style="color:#fff;font-weight:600;" data-val="{r.company}">{r.company}</td>
                    <td class="mono c-teal" style="font-weight:700;" data-val="{r.ticker}">{r.ticker}</td>
                    <td class="mono c-dim" data-val="{r.valuation.pe_ratio or 9999}">{pe_str}</td>
                    <td class="mono c-dim" data-val="{r.health.piotroski_f or -1}">{r.health.piotroski_f if r.health.piotroski_f is not None else "n/a"}</td>
                    <td class="mono c-dim" data-val="{r.health.altman_z or -99}">{alt_str}</td>
                    <td class="mono c-dim" data-val="{r.growth.revenue_cagr_3y or -99}">{rev_str}</td>
                    <td data-val="{concern_lvl}"><span class="badge {concern_cls}">{concern_lvl}</span></td>
                </tr>""")

        html_content = f"""{self._head_block("telmus — Sector Screen Results")}
<style>
@media print {{
  @page {{
    size: A4 landscape;
    margin: 0.5cm;
  }}
  #printBtn {{ display: none !important; }}
  body {{
    zoom: 50%;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
}}
</style>
<body>
    <div class="container stack">

        <!-- Header -->
        <header style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <h1>Sector Screen — {n} companies analysed</h1>
                <div class="header-sub">Screening report · {scan_date}</div>
            </div>
            <div style="display:flex;align-items:center;gap:1rem;
            margin-left:auto;">
              <span style="color:#00d4aa;
              font-family:'JetBrains Mono',monospace;
              font-weight:700;font-size:0.85rem;">telmus v0.2.6</span>
              <button id="printBtn" onclick="window.print()"
              style="background:transparent;
              color:#ffffff;
              border:1px solid #ffffff;
              padding:0.3rem 1rem;
              border-radius:4px;
              font-size:0.8rem;
              font-weight:600;
              cursor:pointer;
              font-family:'JetBrains Mono',monospace;
              letter-spacing:0.05em;">
              PRINT REPORT
              </button>
            </div>
        </header>

        <!-- KPI Row -->
        <div class="grid-4">
            <div class="card">
                <div class="kpi-value c-teal">{n}</div>
                <div class="kpi-label">Stocks Screened</div>
            </div>
            <div class="card">
                <div class="kpi-value" style="color:var(--teal);">{avg_pio:,.2f}</div>
                <div class="kpi-label">Average Piotroski F</div>
            </div>
            <div class="card">
                <div class="kpi-value" style="color:var(--indigo);">{avg_pe:,.2f}</div>
                <div class="kpi-label">Average P/E Ratio</div>
            </div>
            <div class="card">
                <div class="kpi-value" style="color:var(--amber);">{no_flags_count}</div>
                <div class="kpi-label">No Red Flag Stocks</div>
            </div>
        </div>

        <!-- Horizontal Bar Charts -->
        <div class="card">
            <div class="section-label">Comparison</div>
            <div class="section-title" style="margin-bottom:0.5rem;">
                <span class="dot" style="background:var(--teal);"></span>Piotroski F-Score
            </div>
            <div class="chart-box" style="height:280px;"><canvas id="chartPio"></canvas></div>
            <div class="chart-explain">Measures overall financial strength out of 9. Score of 7+ = strong fundamentals, 5–6 = average, below 5 = weak. The dashed lines mark these thresholds. Longer bars = healthier companies.</div>
        </div>

        <div class="card">
            <div class="section-label">Valuation</div>
            <div class="section-title" style="margin-bottom:0.5rem;">
                <span class="dot" style="background:var(--teal);"></span>P/E Ratio
            </div>
            <div class="chart-box" style="height:280px;"><canvas id="chartPE"></canvas></div>
            <div class="chart-explain">Price-to-Earnings ratio — how much investors pay for each ₹1 of profit. A P/E below the dashed line (20) generally means the stock is reasonably priced. Very high P/E can signal overvaluation or high growth expectations.</div>
        </div>

        <div class="card">
            <div class="section-label">Safety</div>
            <div class="section-title" style="margin-bottom:0.5rem;">
                <span class="dot" style="background:var(--indigo);"></span>Altman Z-Score
            </div>
            <div class="chart-box" style="height:280px;"><canvas id="chartAltman"></canvas></div>
            <div class="chart-explain">Predicts the probability of bankruptcy within 2 years. Z > 2.6 = safe zone (low risk), 1.1–2.6 = grey zone (uncertain), below 1.1 = distress zone (high risk). The dashed line marks the safe threshold.</div>
        </div>

        <!-- Results Table -->
        <div class="card">
            <div class="section-label">Results</div>
            <div class="section-title" style="margin-bottom:1rem;">
                <span class="dot" style="background:var(--teal);"></span>Screening Results (Click Headers to Sort)
            </div>
            <div style="overflow-x:auto;">
                <table id="screenTable">
                    <thead><tr>
                        <th class="sortable" onclick="sortTable(0)">Rank</th>
                        <th class="sortable" onclick="sortTable(1)">Company</th>
                        <th class="sortable" onclick="sortTable(2)">Ticker</th>
                        <th class="sortable" onclick="sortTable(3)">P/E</th>
                        <th class="sortable" onclick="sortTable(4)">Piotroski F</th>
                        <th class="sortable" onclick="sortTable(5)">Altman Z</th>
                        <th class="sortable" onclick="sortTable(6)">Revenue CAGR</th>
                        <th class="sortable" onclick="sortTable(7)">Concern</th>
                    </tr></thead>
                    <tbody>{"".join(table_rows)}</tbody>
                </table>
            </div>
        </div>

        {self._footer_block()}
    </div>

    <script>
        Chart.defaults.color = '#525252';
        Chart.defaults.borderColor = '#141414';
        Chart.defaults.font.family = "'JetBrains Mono', monospace";
        Chart.defaults.font.size = 10;

        // Value label plugin (horizontal)
        const valueLabelPlugin = {{
            id: 'valueLabels',
            afterDatasetsDraw(chart) {{
                const ctx = chart.ctx;
                ctx.save();
                chart.data.datasets.forEach((dataset, i) => {{
                    const meta = chart.getDatasetMeta(i);
                    meta.data.forEach((bar, index) => {{
                        const value = dataset.data[index];
                        if (value === null || value === undefined) return;
                        const label = typeof value === 'number' ? (Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(1)) : value;
                        ctx.fillStyle = '#8a8a8a';
                        ctx.font = "600 9px 'JetBrains Mono'";
                        if (chart.options.indexAxis === 'y') {{
                            ctx.textAlign = 'left';
                            ctx.fillText(label, bar.x + 6, bar.y + 3.5);
                        }} else {{
                            ctx.textAlign = 'center';
                            ctx.fillText(label, bar.x, bar.y - 8);
                        }}
                    }});
                }});
                ctx.restore();
            }}
        }};
        Chart.register(valueLabelPlugin);

        // Vertical line plugin for horizontal bars
        const vertLinePlugin = {{
            id: 'verticalLine',
            afterDraw(chart, args, options) {{
                const ctx = chart.ctx;
                const top = chart.chartArea.top;
                const bottom = chart.chartArea.bottom;
                const x = chart.scales.x;
                ctx.save();
                (options.lines || []).forEach(line => {{
                    const xPos = x.getPixelForValue(line.value);
                    if (xPos >= chart.chartArea.left && xPos <= chart.chartArea.right) {{
                        ctx.strokeStyle = '#333';
                        ctx.lineWidth = 1;
                        ctx.setLineDash([3, 3]);
                        ctx.beginPath();
                        ctx.moveTo(xPos, top);
                        ctx.lineTo(xPos, bottom);
                        ctx.stroke();
                        ctx.fillStyle = '#525252';
                        ctx.font = "500 9px 'JetBrains Mono'";
                        ctx.fillText(line.label, xPos + 4, top + 12);
                    }}
                }});
                ctx.restore();
            }}
        }};
        Chart.register(vertLinePlugin);

        const tickers = {json.dumps(tickers)};
        const pioScores = {json.dumps(pio_scores)};
        const pioColors = pioScores.map(s => s >= 7 ? '#00d4aa' : (s >= 5 ? '#e3b341' : '#f78166'));
        const pioBorders = pioScores.map(s => s >= 7 ? '#00d4aa' : (s >= 5 ? '#e3b341' : '#f78166'));

        const horizOpts = {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: {{ padding: {{ right: 40 }} }},
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ grid: {{ color: '#141414', lineWidth: 0.5 }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }},
                y: {{ grid: {{ display: false }}, ticks: {{ color: '#525252' }}, border: {{ display: false }} }}
            }}
        }};

        // Piotroski
        new Chart(document.getElementById('chartPio'), {{
            type: 'bar',
            data: {{ labels: tickers, datasets: [{{ data: pioScores, backgroundColor: pioColors, borderWidth: 0, barPercentage: 0.7, categoryPercentage: 0.9, borderRadius: 0 }}] }},
            options: {{
                ...horizOpts,
                plugins: {{
                    legend: {{ display: false }},
                    verticalLine: {{
                        lines: [
                            {{ value: 7, label: 'Strong (7)', color: '#333' }},
                            {{ value: 5, label: 'Adequate (5)', color: '#333' }}
                        ]
                    }}
                }}
            }}
        }});

        // P/E
        new Chart(document.getElementById('chartPE'), {{
            type: 'bar',
            data: {{ labels: tickers, datasets: [{{ data: {json.dumps(pe_ratios)}, backgroundColor: '#00d4aa', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }}] }},
            options: {{
                ...horizOpts,
                plugins: {{
                    legend: {{ display: false }},
                    verticalLine: {{ lines: [{{ value: 20, label: 'Fair value (20)', color: '#333' }}] }}
                }}
            }}
        }});

        // Altman Z
        new Chart(document.getElementById('chartAltman'), {{
            type: 'bar',
            data: {{ labels: tickers, datasets: [{{ data: {json.dumps(altman_scores)}, backgroundColor: '#818cf8', borderWidth: 0, barPercentage: 0.55, categoryPercentage: 0.8, borderRadius: 0 }}] }},
            options: {{
                ...horizOpts,
                plugins: {{
                    legend: {{ display: false }},
                    verticalLine: {{ lines: [{{ value: 2.6, label: 'Safe zone (2.6)', color: '#333' }}] }}
                }}
            }}
        }});

        // Sorting
        let sortDirs = Array(8).fill(false);
        function sortTable(col) {{
            const table = document.getElementById("screenTable");
            let rows, switching = true, i, x, y, shouldSwitch;
            const asc = !sortDirs[col];
            sortDirs = Array(8).fill(false);
            sortDirs[col] = asc;
            while (switching) {{
                switching = false;
                rows = table.rows;
                for (i = 1; i < rows.length - 1; i++) {{
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[col];
                    y = rows[i+1].getElementsByTagName("TD")[col];
                    let xV = x.getAttribute("data-val") || x.innerText.toLowerCase().trim();
                    let yV = y.getAttribute("data-val") || y.innerText.toLowerCase().trim();
                    let xN = parseFloat(String(xV).replace('%',''));
                    let yN = parseFloat(String(yV).replace('%',''));
                    if (!isNaN(xN) && !isNaN(yN)) {{ xV = xN; yV = yN; }}
                    if (asc ? xV > yV : xV < yV) {{ shouldSwitch = true; break; }}
                }}
                if (shouldSwitch) {{
                    rows[i].parentNode.insertBefore(rows[i+1], rows[i]);
                    switching = true;
                }}
            }}
        }}
        }});
    </script>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

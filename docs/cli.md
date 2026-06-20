# CLI Reference

The `telmus` command-line interface gives you fast access to financial scans, comparisons, screens, health checks, and MCP server mode. Use these commands to analyze companies, compare peers, filter investment candidates, and serve results to AI assistants.

## `telmus scan TICKER [--json] [--export PATH]`

**What it does**
Performs a complete financial scan for a single ticker and returns valuation, health, growth, red-flag metrics, and a deterministic analyst brief.

**When to use it**
- You want a fast company profile for a single stock.
- You need structured JSON output for automation.
- You want an analyst brief that summarizes fundamentals clearly.

**Syntax**
```bash
telmus scan TICKER [--json] [--export PATH]
```

**Examples**
```bash
telmus scan INFY
telmus scan INFY --json
telmus scan INFY --export infy-report.json
telmus scan INFY --export infy-report.xlsx
telmus scan INFY --export infy-report.csv
```

**Output**
The default output includes sections for `Valuation`, `Health`, `Growth`, and `Analyst brief`. When you use `--json`, the CLI returns a JSON object with nested sections like `valuation`, `health`, `growth`, `flags`, and `analyst_brief`.

**Flags**
- `--json` return the full structured result as JSON.
- `--export PATH` save the scan result to a file at the specified path. Supports `.xlsx` (Excel), `.csv` (CSV), and `.json` (JSON) file formats.

---

## `telmus compare TICKER_A TICKER_B`

**What it does**
Compares two tickers side by side across their financial metrics, making it easy to spot valuation, health, and growth differences.

**When to use it**
- You want a quick peer comparison between two stocks.
- You are choosing between alternatives in the same sector.
- You need a concise view of relative risk and valuation.

**Syntax**
```bash
telmus compare TICKER_A TICKER_B [--export PATH]
```

**Examples**
```bash
telmus compare INFY TCS
telmus compare INFY TCS --export comparison.xlsx
telmus compare INFY TCS --export comparison.csv
telmus compare INFY TCS --export comparison.json
```

**Flags**
- `--export PATH` save the comparison results to a file. Supports `.xlsx` (Excel), `.csv` (CSV), and `.json` (JSON) formats.

**Output**
The comparison table shows metrics such as `P/E`, `P/B`, `EV/EBITDA`, `Piotroski F`, `Altman Z`, `Revenue CAGR 3y`, and `Margin Trend` for both tickers.

---

## `telmus screen [--sector TEXT] [--min-piotroski INT] [--max-de FLOAT]`

**What it does**
Filters the ticker universe by sector, Piotroski score, and leverage, returning only companies that match the selected quality criteria.

**When to use it**
- You want to find fundamentally strong stocks in a specific sector.
- You want to enforce minimum earnings quality and maximum leverage rules.
- You are building a shortlist for deeper analysis.

**Syntax**
```bash
telmus screen [--sector TEXT] [--min-piotroski INT] [--max-de FLOAT] [--export PATH]
```

**Examples**
```bash
telmus screen --sector IT --min-piotroski 6 --max-de 1.5
telmus screen --sector IT --export sector.xlsx
telmus screen --sector IT --export sector.csv
telmus screen --sector IT --export sector.json
```

**Available flags**
- `--sector TEXT` filter by industry sector.
- `--min-piotroski INT` require a minimum Piotroski F-score.
- `--max-de FLOAT` require a maximum debt-to-equity ratio.
- `--export PATH` save the screening results to a file. Supports `.xlsx` (Excel), `.csv` (CSV), and `.json` (JSON) formats.

---

## `telmus check TICKER`

**What it does**
Runs a compact health check for a ticker and returns the most important balance sheet and earnings quality indicators.

**When to use it**
- You need a quick health snapshot without the full scan.
- You want to confirm whether a company passes basic leverage and liquidity thresholds.
- You are screening for balance-sheet risk.

**Syntax**
```bash
telmus check TICKER
```

**Example**
```bash
telmus check INFY
```

**Output**
The check output focuses on `Piotroski F`, `Altman Z`, `D/E`, `Current Ratio`, and `Interest Coverage`, plus a brief risk summary.

---

## `telmus serve`

**What it does**
Starts telmus in MCP server mode so connected AI tools and assistants can call it as a structured external tool.

**When to use it**
- You want an AI assistant to query real financial metrics automatically.
- You are integrating telmus with an MCP-compatible client such as Claude Desktop, Cursor, or Windsurf.
- You need a live, local tool endpoint for your agent workflows.

**Syntax**
```bash
telmus serve
```

**Example**
```bash
telmus serve
```

**Expected output**
```text
telmus MCP server listening on port 8080
Available tools: scan, scan_ticker, compare, screen, info
```

---

## `telmus info`

**What it does**
Displays server metadata, package version, tool availability, and data source details.

**When to use it**
- You want to verify the running server state.
- You need the current package version or supported tool list.
- You are troubleshooting your MCP service.

**Syntax**
```bash
telmus info
```

**Example**
```bash
telmus info
```

**Sample output**
```text
telmus version: 0.1.0
data source: public financial statements
available tools: scan, scan_ticker, compare, screen, info
```

---

## Common workflows

### Perform a scan and save the result (JSON/Excel/CSV)
```bash
telmus scan INFY --export infy.xlsx
telmus scan INFY --export infy.csv
telmus scan INFY --export infy.json
```

### Compare two investment candidates (JSON/Excel/CSV)
```bash
telmus compare INFY TCS --export comparison.xlsx
telmus compare INFY TCS --export comparison.csv
```

### Start the MCP server for AI integration
```bash
telmus serve
```

### Screen for stronger companies in a sector (JSON/Excel/CSV)
```bash
telmus screen --sector IT --min-piotroski 7 --max-de 1.2 --export quality_it.xlsx
```

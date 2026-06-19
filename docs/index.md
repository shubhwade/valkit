# valkit

Financial statement analysis for AI IDEs and coding agents.

## Why valkit?

| Engine | What it catches |
|---|---|
| Valuation | Overpriced or undervalued relative to sector peers |
| Health | Balance sheet stress, leverage, and credit risk |
| Flags | Earnings manipulation risk and cash flow trouble |

## The analyst_brief — The Key Innovation

The `analyst_brief` is a deterministic summary generated from financial metrics and red flags. Designed for AI IDEs to consume without relying on generative models.

```json
{
  "analyst_brief": "Strong fundamentals (Piotroski F-score of 7). Financially safe (Altman Z-score of 4.20). Revenue growth is 11.2% over three years and operating margins are stable. No significant red flags detected. Suitable for DCF or comparable company analysis."
}
```

## Quick start

1. Install: `pip install valkit`
2. Run `valkit scan INFY`
3. Read the summary, ratios, and red flags

## MCP Server

Use valkit as an MCP tool for Claude, Cursor, or any MCP-aware IDE.

```json
{
  "mcpServers": {
    "valkit": {
      "command": "valkit",
      "args": ["serve"],
      "description": "Financial statement analysis - real ratios for any ticker"
    }
  }
}
```
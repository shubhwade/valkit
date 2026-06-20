## v0.1.14 - Terminal ASCII Charts
- Added native ASCII bar charts directly in the terminal for `scan` and `compare` commands
- Added Unicode fallback handling for legacy Windows terminals

## v0.1.13 - Dashboard Layout and Versioning Polish
- Fixed CSS layout causing Compare dashboard bar charts to overflow horizontally
- UI components now dynamically read system version instead of hardcoding

## v0.1.12 - Compare Dashboard JS Fix
- Removed dangling JS bracket that caused syntax errors and blank compare charts

## v0.1.11 - HTML Dashboard Variable Hardening
- Safely fallback missing values to 0 to prevent JavaScript errors
- Fully mapped all radar chart labels and overlay datasets to variables correctly

## v0.1.10 - Hotfix Dashboard Charts
- Fixed an f-string rendering issue preventing charts from displaying

## v0.1.9 - Final Polish & Chart Bug Fixes
- Full synchronization
- Fixed piotroski chart vanishing

## v0.1.8 - Professional Dashboard Polish
- Made bar charts perfectly sharp and styled
- Fixed chart vanishing bug

## v0.1.0 - Initial Release

### Added

- Full valuation engine: P/E, P/B, EV/EBITDA, sector peer comparison
- Full health engine: Piotroski F-score (9 signals), Altman Z-score, D/E, current ratio, interest coverage
- Full growth engine: Revenue CAGR, PAT CAGR, margin trend, FCF yield
- Full flags engine: Beneish M-score (8 indices), high D/E flag, negative FCF flag
- CLI: scan, compare, screen, check, serve, info commands
- MCP server with 5 tools: scan, scan_ticker, compare, screen, info
- Streamlit dashboard
- Python SDK with TelmusScanner class
- Full MkDocs documentation site
- 18-test suite covering all engines and CLI

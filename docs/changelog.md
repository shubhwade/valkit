## v0.2.6
### Changed
- Audited and synchronized package metadata across PyPI, MkDocs, and codebase

## v0.2.5
### Added
- Updated package metadata with AI keywords for PyPI/Pepy

## v0.2.4
### Added
- Added pepy.tech downloads badge to README

## v0.2.3 - Final Production Release
### Fixed
- Gauge alignment corrected, all 3 gauges same height
- Print button white JetBrains Mono positioned top right
- Analyst brief background removed
- Red flags banner background removed
- One page A4 landscape print layout
### Security
- 0 HIGH issues confirmed by bandit
- All dependencies clean via pip-audit

## v0.2.2
### Fixed
- Print report fits exactly one A4 landscape page (transform scale 0.85)
- Red flags "No Flags" banner background removed — text-only with teal left border
- Print button moved beside version text in header, teal outline style

## v0.2.1
### Added
- Real company logos via Clearbit API (no API key needed)
- Print button generates clean one-page A4 landscape report
- Print layout optimized for white paper with all charts preserved

## v0.2.0 - Final Boss Update
- Cleaned codebase, performed security audit, and fixed typing issues
- Added safe fallbacks for Valuation, Health, and Growth engines
- Hardened HTML dashboard variables and added missing fallback mappings
- Added P/E History and Revenue History charts to the Excel Exporter Dashboard
- Fixed CLI commands: added `comp` alias and updated `screen` sector argument

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

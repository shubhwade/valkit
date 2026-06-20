#!/usr/bin/env python
"""Test MCP server tools directly."""
from __future__ import annotations

import asyncio
import json
from telmus.mcp.server import handle_tool_call, TOOL_DEFINITIONS

import pytest

@pytest.mark.anyio
async def test_all_tools() -> None:
    """Test all 5 MCP tools."""
    print("=" * 80)
    print("TESTING telmus MCP SERVER - ALL 5 TOOLS")
    print("=" * 80)
    
    # Test 1: info
    print("\n[1/5] Testing 'info' tool")
    print("Request: {}")
    result = await handle_tool_call("info", {})
    output = result.content[0].text if result.content else ""
    print(f"Response:\n{output}\n")
    
    # Test 2: scan with INFY
    print("[2/5] Testing 'scan' tool with INFY ticker")
    print('Request: {"ticker": "INFY"}')
    result = await handle_tool_call("scan", {"ticker": "INFY"})
    output = result.content[0].text if result.content else ""
    payload = json.loads(output)
    print(f"Response (abbreviated):")
    print(f"  Ticker: {payload.get('result', {}).get('ticker')}")
    print(f"  Company: {payload.get('result', {}).get('company')}")
    print(f"  Valuation P/E: {payload.get('result', {}).get('valuation', {}).get('pe_ratio')}")
    print(f"  Health Piotroski: {payload.get('result', {}).get('health', {}).get('piotroski_f')}")
    print(f"  Health Altman Z: {payload.get('result', {}).get('health', {}).get('altman_z')}")
    print(f"  Growth Revenue CAGR: {payload.get('result', {}).get('growth', {}).get('revenue_cagr_3y')}")
    print(f"  Flags Count: {len(payload.get('result', {}).get('red_flags', []))}")
    print(f"  Analyst Brief: {payload.get('result', {}).get('analyst_brief')[:100] if payload.get('result', {}).get('analyst_brief') else 'N/A'}...\n")
    
    # Test 3: scan_ticker with INFY
    print("[3/5] Testing 'scan_ticker' tool with INFY ticker")
    print('Request: {"ticker": "INFY"}')
    result = await handle_tool_call("scan_ticker", {"ticker": "INFY"})
    output = result.content[0].text if result.content else ""
    payload = json.loads(output)
    print(f"Response: Same as scan (tool calls same backend)")
    print(f"  Ticker: {payload.get('result', {}).get('ticker')}\n")
    
    # Test 4: compare two tickers
    print("[4/5] Testing 'compare' tool with INFY vs TCS")
    print('Request: {"ticker_a": "INFY", "ticker_b": "TCS"}')
    result = await handle_tool_call("compare", {"ticker_a": "INFY", "ticker_b": "TCS"})
    output = result.content[0].text if result.content else ""
    payload = json.loads(output)
    print(f"Response (abbreviated):")
    print(f"  Ticker A: {payload.get('result', {}).get('ticker_a')}")
    print(f"  Ticker B: {payload.get('result', {}).get('ticker_b')}")
    print(f"  Result A Piotroski: {payload.get('result', {}).get('result_a', {}).get('health', {}).get('piotroski_f')}")
    print(f"  Result B Piotroski: {payload.get('result', {}).get('result_b', {}).get('health', {}).get('piotroski_f')}\n")
    
    # Test 5: screen
    print("[5/5] Testing 'screen' tool with IT sector")
    print('Request: {"sector": "IT", "min_piotroski": 5, "max_de": 2.0}')
    result = await handle_tool_call("screen", {"sector": "IT", "min_piotroski": 5, "max_de": 2.0})
    output = result.content[0].text if result.content else ""
    payload = json.loads(output)
    matches = payload.get('matches', [])
    print(f"Response:")
    print(f"  Matches found: {len(matches)}")
    for match in matches:
        print(f"    - {match.get('ticker')}: Piotroski={match.get('health', {}).get('piotroski_f')}, D/E={match.get('health', {}).get('debt_to_equity')}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_all_tools())

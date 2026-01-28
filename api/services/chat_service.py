"""
Chat service using Claude API with tool-calling for dynamic computation.
Falls back to a built-in response engine if no API key is configured.
"""

import os
import json
from typing import AsyncGenerator, List, Dict, Any

SYSTEM_PROMPT = """You are a maritime shipping analytics assistant for Cargill Ocean Transportation.
You help analysts understand vessel-cargo assignments, voyage economics, scenario analysis, and port congestion predictions.

You have access to tools that can:
- Calculate individual voyage economics
- Run portfolio optimization
- Analyze bunker price and port delay scenarios
- Get ML-predicted port congestion

When answering:
- Use precise numbers from tool results
- Format currency as USD with commas
- Reference specific vessels and cargoes by name
- Explain trade-offs clearly (cost vs speed, TCE vs profit)
- Explain your answer in simple terms, in a friendly manner

Key context:
- 4 Cargill vessels: Ann Bell, Ocean Horizon, Pacific Glory, Golden Ascent
- 3 committed cargoes: EGA Bauxite (Kamsar→Qingdao), BHP Iron Ore (Port Hedland→Lianyungang), CSN Iron Ore (Itaguai→Qingdao)
- Optimization maximizes total portfolio profit
- Eco speed is preferred for fuel savings unless laycan is at risk
"""


TOOLS = [
    {
        "name": "calculate_voyage",
        "description": "Calculate full voyage economics for a vessel-cargo pair",
        "input_schema": {
            "type": "object",
            "properties": {
                "vessel_name": {"type": "string", "description": "Vessel name"},
                "cargo_name": {"type": "string", "description": "Cargo name"},
                "use_eco_speed": {"type": "boolean", "default": True},
                "bunker_adjustment": {"type": "number", "default": 1.0, "description": "Bunker price multiplier"},
            },
            "required": ["vessel_name", "cargo_name"],
        },
    },
    {
        "name": "get_portfolio",
        "description": "Get the optimal vessel-cargo assignment portfolio",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_bunker_scenario",
        "description": "Get bunker price sensitivity analysis results",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_delay_scenario",
        "description": "Get port delay sensitivity analysis results",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_port_congestion",
        "description": "Get ML-predicted port congestion delays",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "compare_voyages",
        "description": "Compare two vessel-cargo combinations side by side",
        "input_schema": {
            "type": "object",
            "properties": {
                "vessel_a": {"type": "string"},
                "cargo_a": {"type": "string"},
                "vessel_b": {"type": "string"},
                "cargo_b": {"type": "string"},
            },
            "required": ["vessel_a", "cargo_a", "vessel_b", "cargo_b"],
        },
    },
]


def _execute_tool(tool_name: str, tool_input: dict, service) -> str:
    """Execute a tool call using the calculator service."""
    try:
        if tool_name == "calculate_voyage":
            result = service.calculate_voyage(
                tool_input["vessel_name"],
                tool_input["cargo_name"],
                tool_input.get("use_eco_speed", True),
                bunker_adj=tool_input.get("bunker_adjustment", 1.0),
            )
            return json.dumps(result, indent=2)

        elif tool_name == "get_portfolio":
            return json.dumps(service.get_portfolio(), indent=2)

        elif tool_name == "run_bunker_scenario":
            return json.dumps(service.get_bunker_sensitivity()[:10], indent=2)

        elif tool_name == "run_delay_scenario":
            return json.dumps(service.get_delay_sensitivity()[:10], indent=2)

        elif tool_name == "get_port_congestion":
            return json.dumps(service.get_ml_delays(), indent=2)

        elif tool_name == "compare_voyages":
            a = service.calculate_voyage(tool_input["vessel_a"], tool_input["cargo_a"])
            b = service.calculate_voyage(tool_input["vessel_b"], tool_input["cargo_b"])
            return json.dumps({"voyage_a": a, "voyage_b": b}, indent=2)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def stream_chat_response(
    message: str,
    history: List[dict],
    calculator_service,
) -> AsyncGenerator[str, None]:
    """Stream a chat response, using Claude API if available, else fallback."""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if api_key:
        async for chunk in _stream_claude(message, history, calculator_service, api_key):
            yield chunk
    else:
        # Fallback: use calculator service directly for common questions
        yield _fallback_response(message, calculator_service)


async def _stream_claude(
    message: str,
    history: List[dict],
    service,
    api_key: str,
) -> AsyncGenerator[str, None]:
    """Stream response from Claude API with tool calling."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        messages = []
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        # Initial request
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Handle tool use loop (max 3 iterations)
        for _ in range(3):
            if response.stop_reason != "tool_use":
                break

            # Extract tool calls and results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    yield f"[TOOL:{block.name}]"
                    result = _execute_tool(block.name, block.input, service)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

        # Extract final text
        for block in response.content:
            if hasattr(block, "text"):
                yield block.text

    except ImportError:
        yield _fallback_response(message, service)
    except Exception as e:
        yield f"Error connecting to Claude API: {str(e)}\n\n"
        yield _fallback_response(message, service)


def _fallback_response(message: str, service) -> str:
    """Generate a response without Claude API using cached data."""
    lower = message.lower()

    if "optimal" in lower or "assignment" in lower or "portfolio" in lower:
        p = service.get_portfolio()
        if p and p.get("assignments"):
            lines = ["**Optimal Portfolio Assignment:**\n"]
            lines.append("| Vessel | Cargo | TCE | Profit |")
            lines.append("|--------|-------|-----|--------|")
            for a in p["assignments"]:
                v = a["voyage"]
                lines.append(f"| {a['vessel']} | {a['cargo']} | ${v['tce']:,.0f}/day | ${v['net_profit']:,.0f} |")
            lines.append(f"\n**Total Profit: ${p['total_profit']:,.0f}** | Avg TCE: ${p['avg_tce']:,.0f}/day")
            return "\n".join(lines)

    if "bunker" in lower or "fuel" in lower:
        data = service.get_bunker_sensitivity()
        if data:
            lines = ["**Bunker Price Sensitivity:**\n"]
            lines.append("| Bunker % | Total Profit | Avg TCE |")
            lines.append("|----------|-------------|---------|")
            for row in data[::3]:
                pct = row.get("bunker_multiplier", row.get("bunker_change_pct", 1))
                if pct < 10:
                    pct = f"{pct*100:.0f}%"
                else:
                    pct = f"{pct:+.0f}%"
                lines.append(f"| {pct} | ${row['total_profit']:,.0f} | ${row['avg_tce']:,.0f} |")
            return "\n".join(lines)

    if "delay" in lower or "port" in lower or "congestion" in lower:
        delays = service.get_ml_delays()
        if delays:
            lines = ["**ML-Predicted Port Delays:**\n"]
            lines.append("| Port | Delay | Confidence | Level |")
            lines.append("|------|-------|------------|-------|")
            for d in delays:
                lines.append(
                    f"| {d['port']} | {d.get('predicted_delay', d.get('predicted_delay_days', 0)):.1f}d | "
                    f"{d.get('confidence_lower', 0):.1f}-{d.get('confidence_upper', 0):.1f}d | "
                    f"{d.get('congestion_level', 'unknown')} |"
                )
            return "\n".join(lines)

    if "compare" in lower:
        voyages = service.get_all_voyages()
        if voyages:
            lines = ["**Voyage Comparison Matrix:**\n"]
            lines.append("| Vessel | Cargo | TCE | Profit | Feasible |")
            lines.append("|--------|-------|-----|--------|----------|")
            for v in sorted(voyages, key=lambda x: -x["tce"])[:6]:
                feas = "Yes" if v["can_make_laycan"] else "No"
                lines.append(f"| {v['vessel']} | {v['cargo']} | ${v['tce']:,.0f} | ${v['net_profit']:,.0f} | {feas} |")
            return "\n".join(lines)

    if "tipping" in lower:
        tp = service.get_tipping_points()
        if tp:
            return f"**Tipping Points:**\n\n```json\n{json.dumps(tp, indent=2)}\n```"

    return (
        "I can help analyze vessel assignments, run scenarios, compare voyages, "
        "and check port congestion. Try asking:\n\n"
        "- *What is the optimal vessel assignment?*\n"
        "- *What if bunker prices rise 20%?*\n"
        "- *Compare vessels for EGA Bauxite*\n"
        "- *Which ports have highest congestion?*\n"
        "- *What are the tipping points?*"
    )

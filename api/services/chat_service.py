"""
Chat service using Claude API with tool-calling for dynamic computation.
Falls back to a built-in response engine if no API key is configured.
"""

import os
import json
from typing import AsyncGenerator, List, Dict, Any

SYSTEM_PROMPT = """You are a maritime shipping analytics assistant for Cargill Ocean Transportation's Capesize freight desk.
You help analysts understand vessel-cargo assignments, voyage economics, scenario analysis, and port congestion predictions.

## Fleet Overview

**4 Cargill Vessels** (company-owned, with daily hire costs):
| Vessel | DWT | Hire $/day | Current Port | ETD |
|--------|-----|-----------|--------------|-----|
| ANN BELL | 180,803 | $11,750 | Qingdao | 25 Feb |
| OCEAN HORIZON | 181,550 | $15,750 | Map Ta Phut | 1 Mar |
| PACIFIC GLORY | 182,320 | $14,800 | Gwangyang | 10 Mar |
| GOLDEN ASCENT | 179,965 | $13,950 | Fangcheng | 8 Mar |

**11 Market Vessels** (available for hire at FFA benchmark ~$18,000/day):
Atlantic Fortune, Pacific Vanguard, Coral Emperor, Everest Ocean, Polaris Spirit,
Iron Century, Mountain Trader, Navis Pride, Aurora Sky, Zenith Glory, Titan Legacy

**3 Cargill Committed Cargoes** (must fulfill):
| Cargo | Route | Qty | Rate | Laycan |
|-------|-------|-----|------|--------|
| EGA Bauxite | Kamsar->Qingdao | 180k MT | $23.00/MT | 2-10 Apr |
| BHP Iron Ore | Pt Hedland->Lianyungang | 160k MT | $9.00/MT | 7-11 Mar |
| CSN Iron Ore | Itaguai->Qingdao | 180k MT | $22.30/MT | 1-8 Apr |

**8 Market Cargoes** (bidding opportunities):
Rio Tinto Iron Ore (Australia-China), Vale Iron Ore (Brazil-China),
Anglo American Iron Ore (S.Africa-China), BHP Iron Ore (Australia-S.Korea),
Adaro Coal (Indonesia-India), Teck Coking Coal (Canada-China),
Guinea Alumina Bauxite (Guinea-India), Vale Malaysia Iron Ore (Brazil-Malaysia)

## Available Tools (12 total)
1. **calculate_voyage** - Full voyage economics for any vessel-cargo pair (with optional delay/bunker adjustments)
2. **get_portfolio** - Optimal vessel-cargo assignments via Hungarian algorithm (with/without ML delays)
3. **run_bunker_scenario** - 15-point bunker price sensitivity (+/-50% range, tipping point at ~+31%)
4. **run_delay_scenario** - 31-point China port delay sensitivity (0-15 days, tipping point at ~+4.5 days)
5. **get_port_congestion** - ML-predicted port delays for discharge ports
6. **compare_voyages** - Side-by-side comparison of two vessel-cargo pairs
7. **get_vessels** - All 15 vessel specs (DWT, speed, fuel consumption, position)
8. **get_cargoes** - All 11 cargo specs (quantity, ports, rates, laycan dates)
9. **get_all_voyages** - Complete voyage matrix (~70 valid combinations with economics)
10. **get_tipping_points** - Thresholds where optimal assignments change
11. **get_china_delay_sensitivity** - China port delay impact analysis (0-15 days in 0.5-day steps)
12. **get_model_info** - ML model metrics (MAE, RMSE) and SHAP feature importance

## Key Formulas
- **TCE** = (Net Freight - Bunker Cost - Port Cost - Misc) / Total Days
- **Voyage Duration** = Ballast Days + Waiting Days + Load Days + Laden Days + Discharge Days
- **Cargo Quantity** = min(Cargo x (1 + Tolerance), DWT - Constants)
- **Net Profit** = Net Freight - Bunker - Hire - Port - Misc

## Arbitrage Strategy
The optimizer uses an arbitrage approach:
1. Cargill vessels -> Market cargoes (higher profit margins)
2. Market vessels hired at FFA ~$18,000/day -> Cover Cargill committed cargoes
3. This creates higher total portfolio profit (~$5.8M) than direct assignment

## Key Results
- Total Portfolio Profit: ~$5,803,558
- Bunker tipping point: ~+31% before assignments change
- China delay tipping point: ~+4.5 days before assignments change
- ML model accuracy: MAE 0.064 days (~1.5 hours), 99.7% within 1 day
- Eco speed preferred for fuel savings unless laycan is at risk

## Response Guidelines
- Use precise numbers from tool results
- Format currency as USD with commas (e.g., $1,234,567)
- Reference specific vessels and cargoes by name
- Explain trade-offs clearly (cost vs speed, TCE vs profit)
- Keep explanations friendly and accessible
- When asked about a specific vessel or cargo, use the get_vessels or get_cargoes tool for accurate data
- For "what if" questions, use the appropriate scenario tool
- For questions about the ML model, use get_model_info
"""


TOOLS = [
    {
        "name": "calculate_voyage",
        "description": "Calculate full voyage economics for a vessel-cargo pair. Supports optional extra port delay and bunker price adjustment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vessel_name": {"type": "string", "description": "Vessel name (e.g., 'ANN BELL', 'IRON CENTURY')"},
                "cargo_name": {"type": "string", "description": "Cargo name (e.g., 'EGA Bauxite (Guinea-China)')"},
                "use_eco_speed": {"type": "boolean", "default": True, "description": "Use eco speed (slower, saves fuel) or warranted speed"},
                "bunker_adjustment": {"type": "number", "default": 1.0, "description": "Bunker price multiplier (e.g., 1.2 for +20%)"},
                "extra_port_delay": {"type": "number", "default": 0, "description": "Additional port delay in days to add to discharge"},
            },
            "required": ["vessel_name", "cargo_name"],
        },
    },
    {
        "name": "get_portfolio",
        "description": "Get the optimal vessel-cargo assignment portfolio using Hungarian algorithm. Optionally use ML-predicted port delays.",
        "input_schema": {
            "type": "object",
            "properties": {
                "use_ml_delays": {"type": "boolean", "default": False, "description": "If true, use ML-predicted port delays in optimization"},
            },
        },
    },
    {
        "name": "run_bunker_scenario",
        "description": "Get bunker price sensitivity analysis: 15 data points from -20% to +50%, showing how portfolio profit changes. Tipping point at ~+31%.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_delay_scenario",
        "description": "Get China port delay sensitivity analysis: 31 data points from 0 to 15 days showing impact on portfolio profit. Tipping point at ~+4.5 days.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_port_congestion",
        "description": "Get ML-predicted port congestion delays for discharge ports (Qingdao, Rizhao, Caofeidian, etc.)",
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
    {
        "name": "get_vessels",
        "description": "Get specifications for all 15 vessels (4 Cargill + 11 market): DWT, speed, fuel consumption, current port, bunker ROB",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_cargoes",
        "description": "Get details for all 11 cargoes (3 Cargill committed + 8 market): quantity, ports, freight rate, laycan dates, commission",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_all_voyages",
        "description": "Get the complete voyage matrix: all ~70 valid vessel-cargo combinations with full economics (TCE, profit, days, feasibility)",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_tipping_points",
        "description": "Get tipping points: the bunker price increase % and port delay days at which optimal assignments change",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_china_delay_sensitivity",
        "description": "Get China port delay sensitivity: 31 data points (0-15 days in 0.5-day steps) showing profit impact on China-bound cargoes",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_model_info",
        "description": "Get ML port delay model info: model type, accuracy metrics (MAE, RMSE), and SHAP feature importance rankings",
        "input_schema": {"type": "object", "properties": {}},
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
                delay=tool_input.get("extra_port_delay", 0),
                bunker_adj=tool_input.get("bunker_adjustment", 1.0),
            )
            return json.dumps(result, indent=2)

        elif tool_name == "get_portfolio":
            return json.dumps(service.get_portfolio(
                use_ml_delays=tool_input.get("use_ml_delays", False),
            ), indent=2)

        elif tool_name == "run_bunker_scenario":
            return json.dumps(service.get_bunker_sensitivity(), indent=2)

        elif tool_name == "run_delay_scenario":
            return json.dumps(service.get_china_delay_sensitivity(), indent=2)

        elif tool_name == "get_port_congestion":
            return json.dumps(service.get_ml_delays(), indent=2)

        elif tool_name == "compare_voyages":
            a = service.calculate_voyage(tool_input["vessel_a"], tool_input["cargo_a"])
            b = service.calculate_voyage(tool_input["vessel_b"], tool_input["cargo_b"])
            return json.dumps({"voyage_a": a, "voyage_b": b}, indent=2)

        elif tool_name == "get_vessels":
            return json.dumps(service.get_vessels(include_market=True), indent=2)

        elif tool_name == "get_cargoes":
            return json.dumps(service.get_cargoes(include_market=True), indent=2)

        elif tool_name == "get_all_voyages":
            return json.dumps(service.get_all_voyages(), indent=2)

        elif tool_name == "get_tipping_points":
            return json.dumps(service.get_tipping_points(), indent=2)

        elif tool_name == "get_china_delay_sensitivity":
            return json.dumps(service.get_china_delay_sensitivity(), indent=2)

        elif tool_name == "get_model_info":
            return json.dumps(service.get_model_info(), indent=2)

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
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Handle tool use loop (max 5 iterations for complex multi-step questions)
        for _ in range(5):
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
                max_tokens=4096,
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

    # --- Portfolio / Assignment queries ---
    if "optimal" in lower or "assignment" in lower or "portfolio" in lower or "arbitrage" in lower:
        p = service.get_portfolio()
        if p and p.get("best"):
            best = p["best"]
            lines = ["**Optimal Portfolio Assignment (Arbitrage Strategy):**\n"]
            lines.append("**Cargill Vessels -> Market Cargoes:**")
            lines.append("| Vessel | Cargo | TCE | Profit |")
            lines.append("|--------|-------|-----|--------|")
            for a in best.get("assignments", []):
                v = a["voyage"]
                lines.append(f"| {a['vessel']} | {a['cargo']} | ${v['tce']:,.0f}/day | ${v['net_profit']:,.0f} |")

            if best.get("market_vessel_hires"):
                lines.append("\n**Market Vessels Hired -> Cargill Cargoes:**")
                lines.append("| Vessel | Cargo | TCE | Hire Rate |")
                lines.append("|--------|-------|-----|-----------|")
                for h in best["market_vessel_hires"]:
                    hire_rate = h.get("recommended_hire_rate", h.get("hire_rate", 18000))
                    tce = h.get("tce", 0)
                    lines.append(f"| {h['vessel']} | {h['cargo']} | ${tce:,.0f}/day | ${hire_rate:,.0f}/day |")

            lines.append(f"\n**Total Profit: ${best['total_profit']:,.0f}** | Avg TCE: ${best['avg_tce']:,.0f}/day")
            lines.append("\n*The optimizer uses arbitrage: Cargill vessels earn more on market cargoes, while market vessels are hired at FFA rates to cover Cargill commitments.*")
            return "\n".join(lines)

    # --- Vessel specs queries ---
    if "vessel" in lower and ("spec" in lower or "detail" in lower or "info" in lower or "list" in lower or "all" in lower):
        vessels = service.get_vessels(include_market=True)
        if vessels:
            lines = ["**All Vessels (4 Cargill + 11 Market):**\n"]
            lines.append("| Vessel | DWT | Speed (Eco) | Port | Type |")
            lines.append("|--------|-----|-------------|------|------|")
            for v in vessels:
                vtype = "Cargill" if v["is_cargill"] else "Market"
                lines.append(f"| {v['name']} | {v['dwt']:,} | {v['speed_laden_eco']}kn | {v['current_port']} | {vtype} |")
            return "\n".join(lines)

    # Check for specific vessel name queries
    vessel_names = ["ann bell", "ocean horizon", "pacific glory", "golden ascent",
                    "atlantic fortune", "pacific vanguard", "coral emperor", "everest ocean",
                    "polaris spirit", "iron century", "mountain trader", "navis pride",
                    "aurora sky", "zenith glory", "titan legacy"]
    for vname in vessel_names:
        if vname in lower:
            vessels = service.get_vessels(include_market=True)
            for v in vessels:
                if v["name"].lower() == vname:
                    lines = [f"**{v['name']}** ({'Cargill' if v['is_cargill'] else 'Market'} Vessel)\n"]
                    lines.append(f"- **DWT:** {v['dwt']:,} MT")
                    lines.append(f"- **Current Port:** {v['current_port']} (ETD: {v['etd']})")
                    lines.append(f"- **Speed (Laden):** {v['speed_laden']}kn (Eco: {v['speed_laden_eco']}kn)")
                    lines.append(f"- **Speed (Ballast):** {v['speed_ballast']}kn (Eco: {v['speed_ballast_eco']}kn)")
                    lines.append(f"- **Fuel Laden:** {v['fuel_laden_vlsfo']} MT/day VLSFO (Eco: {v['fuel_laden_eco_vlsfo']})")
                    lines.append(f"- **Fuel Ballast:** {v['fuel_ballast_vlsfo']} MT/day VLSFO (Eco: {v['fuel_ballast_eco_vlsfo']})")
                    lines.append(f"- **Bunker ROB:** {v['bunker_rob_vlsfo']} MT VLSFO, {v['bunker_rob_mgo']} MT MGO")
                    if v['is_cargill']:
                        lines.append(f"- **Hire Rate:** ${v['hire_rate']:,.0f}/day")
                    return "\n".join(lines)
            break

    # --- Cargo details queries ---
    if "cargo" in lower and ("spec" in lower or "detail" in lower or "info" in lower or "list" in lower or "all" in lower):
        cargoes = service.get_cargoes(include_market=True)
        if cargoes:
            lines = ["**All Cargoes (3 Cargill + 8 Market):**\n"]
            lines.append("| Cargo | Customer | Qty | Route | Type |")
            lines.append("|-------|----------|-----|-------|------|")
            for c in cargoes:
                ctype = "Cargill" if c["is_cargill"] else "Market"
                lines.append(f"| {c['name'][:35]} | {c['customer']} | {c['quantity']:,} | {c['load_port']}->{c['discharge_port']} | {ctype} |")
            return "\n".join(lines)

    # Check for specific cargo name queries
    cargo_keywords = ["ega bauxite", "bhp iron ore", "csn iron ore", "rio tinto", "vale iron ore",
                      "anglo american", "adaro coal", "teck coking", "guinea alumina", "vale malaysia"]
    for ckw in cargo_keywords:
        if ckw in lower:
            cargoes = service.get_cargoes(include_market=True)
            for c in cargoes:
                if ckw in c["name"].lower():
                    lines = [f"**{c['name']}** ({'Cargill Committed' if c['is_cargill'] else 'Market'} Cargo)\n"]
                    lines.append(f"- **Customer:** {c['customer']}")
                    lines.append(f"- **Commodity:** {c['commodity']}")
                    lines.append(f"- **Quantity:** {c['quantity']:,} MT (+/- {c['quantity_tolerance']*100:.0f}%)")
                    lines.append(f"- **Route:** {c['load_port']} -> {c['discharge_port']}")
                    lines.append(f"- **Freight Rate:** ${c['freight_rate']}/MT" if c['freight_rate'] > 0 else "- **Freight Rate:** Market bid required")
                    lines.append(f"- **Laycan:** {c['laycan_start']} to {c['laycan_end']}")
                    lines.append(f"- **Load Rate:** {c['load_rate']:,} MT/day | Discharge Rate: {c['discharge_rate']:,} MT/day")
                    lines.append(f"- **Commission:** {c['commission']*100:.2f}%")
                    return "\n".join(lines)
            break

    # --- Bunker / fuel queries ---
    if "bunker" in lower or ("fuel" in lower and "sensitivity" in lower):
        data = service.get_bunker_sensitivity()
        if data:
            lines = ["**Bunker Price Sensitivity (15 data points, -20% to +50%):**\n"]
            lines.append("| Bunker Change | Total Profit | Avg TCE | Assignments |")
            lines.append("|---------------|-------------|---------|-------------|")
            for row in data:
                pct = row.get("bunker_change_pct", 0)
                lines.append(f"| {pct:+.1f}% | ${row['total_profit']:,.0f} | ${row['avg_tce']:,.0f} | {row.get('n_assignments', '')} |")
            return "\n".join(lines)

    # --- China delay sensitivity ---
    if "china" in lower and "delay" in lower:
        data = service.get_china_delay_sensitivity()
        if data:
            lines = ["**China Port Delay Sensitivity (0-15 days):**\n"]
            lines.append("| Delay Days | Total Profit | Avg TCE | Assignments |")
            lines.append("|------------|-------------|---------|-------------|")
            for row in data[::2]:  # Show every other point for readability
                lines.append(f"| {row['port_delay_days']:.1f} | ${row['total_profit']:,.0f} | ${row['avg_tce']:,.0f} | {row.get('n_assignments', '')} |")
            return "\n".join(lines)

    # --- Port delay / congestion queries ---
    if "delay" in lower or "port" in lower or "congestion" in lower:
        delays = service.get_ml_delays()
        if delays:
            lines = ["**ML-Predicted Port Delays:**\n"]
            lines.append("| Port | Delay | Confidence | Level |")
            lines.append("|------|-------|------------|-------|")
            for d in delays:
                lines.append(
                    f"| {d['port']} | {d.get('predicted_delay_days', d.get('predicted_delay', 0)):.1f}d | "
                    f"{d.get('confidence_lower', 0):.1f}-{d.get('confidence_upper', 0):.1f}d | "
                    f"{d.get('congestion_level', 'unknown')} |"
                )
            return "\n".join(lines)

    # --- Voyage matrix / all voyages ---
    if ("voyage" in lower and ("all" in lower or "matrix" in lower or "combination" in lower)) or "highest tce" in lower or "best voyage" in lower:
        voyages = service.get_all_voyages()
        if voyages:
            sorted_voyages = sorted(voyages, key=lambda x: -x["tce"])
            lines = [f"**Voyage Matrix (Top 10 by TCE, {len(voyages)} total combinations):**\n"]
            lines.append("| Vessel | Cargo | TCE | Profit | Days | Feasible |")
            lines.append("|--------|-------|-----|--------|------|----------|")
            for v in sorted_voyages[:10]:
                feas = "Yes" if v["can_make_laycan"] else "No"
                lines.append(f"| {v['vessel']} | {v['cargo'][:30]} | ${v['tce']:,.0f} | ${v['net_profit']:,.0f} | {v['total_days']:.1f} | {feas} |")
            return "\n".join(lines)

    # --- Compare voyages ---
    if "compare" in lower:
        voyages = service.get_all_voyages()
        if voyages:
            lines = ["**Voyage Comparison (Top 6 by TCE):**\n"]
            lines.append("| Vessel | Cargo | TCE | Profit | Feasible |")
            lines.append("|--------|-------|-----|--------|----------|")
            for v in sorted(voyages, key=lambda x: -x["tce"])[:6]:
                feas = "Yes" if v["can_make_laycan"] else "No"
                lines.append(f"| {v['vessel']} | {v['cargo'][:30]} | ${v['tce']:,.0f} | ${v['net_profit']:,.0f} | {feas} |")
            return "\n".join(lines)

    # --- Tipping points ---
    if "tipping" in lower:
        tp = service.get_tipping_points()
        if tp:
            lines = ["**Tipping Points (where optimal assignments change):**\n"]
            if "bunker" in tp:
                b = tp["bunker"]
                lines.append(f"- **Bunker Price:** +{b.get('tipping_pct', 'N/A')}% increase before assignments change")
            if "port_delay" in tp:
                d = tp["port_delay"]
                lines.append(f"- **Port Delay:** +{d.get('tipping_days', 'N/A')} days before assignments change")
            lines.append(f"\n```json\n{json.dumps(tp, indent=2)}\n```")
            return "\n".join(lines)

    # --- ML model info / SHAP ---
    if "model" in lower or "shap" in lower or "ml" in lower or "accuracy" in lower or "feature" in lower:
        info = service.get_model_info()
        if info:
            lines = ["**ML Port Delay Prediction Model:**\n"]
            lines.append(f"- **Model Type:** {info.get('model_type', 'LightGBM')}")
            lines.append(f"- **Training Date:** {info.get('training_date', 'N/A')}")
            metrics = info.get("metrics", {})
            lines.append(f"- **MAE:** {metrics.get('mae', 0):.4f} days (~{metrics.get('mae', 0)*24:.1f} hours)")
            lines.append(f"- **RMSE:** {metrics.get('rmse', 0):.4f} days")
            lines.append(f"- **Within 1 day:** {metrics.get('within_1_day', 0)*100:.1f}%")
            lines.append(f"- **Within 2 days:** {metrics.get('within_2_days', 0)*100:.1f}%")
            features = info.get("feature_importance", [])
            if features:
                lines.append("\n**Top SHAP Features:**")
                lines.append("| Rank | Feature | Importance |")
                lines.append("|------|---------|------------|")
                for i, f in enumerate(features[:10], 1):
                    lines.append(f"| {i} | {f['feature']} | {f['importance']:.4f} |")
            return "\n".join(lines)

    # --- Default help text ---
    return (
        "I can help with Cargill's freight analytics. Try asking:\n\n"
        "**Portfolio & Assignments:**\n"
        "- *What is the optimal vessel assignment?*\n"
        "- *Show portfolio with ML delays*\n\n"
        "**Vessels & Cargoes:**\n"
        "- *What are Iron Century's specs?*\n"
        "- *Tell me about Vale Malaysia Iron Ore*\n"
        "- *List all vessels / List all cargoes*\n\n"
        "**Voyage Economics:**\n"
        "- *Which vessel-cargo pair has highest TCE?*\n"
        "- *Calculate Ann Bell on EGA Bauxite with 5 days extra delay*\n"
        "- *Compare Ann Bell vs Ocean Horizon on CSN Iron Ore*\n\n"
        "**Scenarios & Risk:**\n"
        "- *What if bunker prices rise 20%?*\n"
        "- *What happens if China ports are delayed?*\n"
        "- *What are the tipping points?*\n\n"
        "**ML & Port Congestion:**\n"
        "- *Which ports have highest congestion?*\n"
        "- *How accurate is the ML model?*\n"
        "- *What are the top SHAP features?*"
    )

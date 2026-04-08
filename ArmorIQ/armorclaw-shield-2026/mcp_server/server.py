"""
ArmorClaw MCP Server
Exposes enforcement tools via the MCP SDK so any agent can call them.
"""

import asyncio
import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from enforcement.engine import enforce
from logs.audit_logger import get_recent_logs, get_log_stats
from enforcement.policy_loader import get_all_policies, get_whitelist

app = Server("armorclaw-shield")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="enforce_action",
            description=(
                "Submit a proposed agent action for policy enforcement. "
                "Returns ALLOW or BLOCK with the triggering policy and reason. "
                "Every agent action MUST pass through this before execution."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proposed_action": {
                        "type": "string",
                        "description": "Plain English description of what the agent wants to do"
                    },
                    "context": {
                        "type": "object",
                        "description": "Agent context: portfolio state, mode, capability token, etc."
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Unique identifier for this agent instance",
                        "default": "main_agent"
                    }
                },
                "required": ["proposed_action", "context"]
            }
        ),
        types.Tool(
            name="get_audit_logs",
            description="Retrieve recent enforcement decisions with full audit trail",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent entries to return (max 100)",
                        "default": 20
                    }
                }
            }
        ),
        types.Tool(
            name="get_log_stats",
            description="Get aggregate statistics: total decisions, block rate, allow rate",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="list_active_policies",
            description="List all active policies with their IDs, names, and severities",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="check_ticker_whitelist",
            description="Check whether a specific ticker is on the approved whitelist",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    if name == "enforce_action":
        proposed = arguments.get("proposed_action", "")
        context = arguments.get("context", {})
        agent_id = arguments.get("agent_id", "main_agent")
        result = enforce(proposed, context, agent_id)
        return [types.TextContent(
            type="text",
            text=json.dumps(result.to_dict(), indent=2)
        )]

    elif name == "get_audit_logs":
        limit = min(int(arguments.get("limit", 20)), 100)
        logs = get_recent_logs(limit)
        return [types.TextContent(type="text", text=json.dumps(logs, indent=2))]

    elif name == "get_log_stats":
        stats = get_log_stats()
        return [types.TextContent(type="text", text=json.dumps(stats, indent=2))]

    elif name == "list_active_policies":
        policies = get_all_policies()
        summary = [{"id": p["id"], "name": p["name"],
                    "severity": p["severity"], "action": p["action"],
                    "triggers": p["trigger"]} for p in policies]
        return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]

    elif name == "check_ticker_whitelist":
        ticker = arguments.get("ticker", "").upper()
        whitelist = get_whitelist()
        allowed = [t.upper() for t in whitelist.get("tickers", [])]
        result = {"ticker": ticker, "approved": ticker in allowed, "whitelist": allowed}
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
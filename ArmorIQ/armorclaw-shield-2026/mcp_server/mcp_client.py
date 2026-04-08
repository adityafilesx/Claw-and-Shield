"""
MCP client helper — lets the agent call enforcement tools
without running a separate process during demo/development.
This wraps the enforcement engine directly for in-process use.
"""

import json
from enforcement.engine import enforce, EnforcementResult
from logs.audit_logger import get_recent_logs, get_log_stats
from enforcement.policy_loader import get_all_policies, get_whitelist


class ArmorClawMCPClient:
    """
    Synchronous wrapper around the ArmorClaw enforcement tools.
    In production, this would be an actual MCP client over stdio.
    For demo and testing, it calls the engine directly.
    """

    def enforce_action(self, proposed_action: str, context: dict,
                       agent_id: str = "main_agent") -> dict:
        result = enforce(proposed_action, context, agent_id)
        return result.to_dict()

    def get_audit_logs(self, limit: int = 20) -> list:
        return get_recent_logs(min(limit, 100))

    def get_log_stats(self) -> dict:
        return get_log_stats()

    def list_active_policies(self) -> list:
        return [{"id": p["id"], "name": p["name"], "severity": p["severity"],
                 "action": p["action"], "triggers": p["trigger"]}
                for p in get_all_policies()]

    def check_ticker_whitelist(self, ticker: str) -> dict:
        whitelist = get_whitelist()
        allowed = [t.upper() for t in whitelist.get("tickers", [])]
        return {"ticker": ticker.upper(), "approved": ticker.upper() in allowed}


# Global singleton — import and use anywhere
mcp = ArmorClawMCPClient()
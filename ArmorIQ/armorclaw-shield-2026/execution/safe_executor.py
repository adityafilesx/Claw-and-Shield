from mcp_server.mcp_client import mcp
from execution.alpaca_executor import (
    execute_buy, execute_sell,
    get_portfolio_state, get_current_price
)
from rich.console import Console
from rich.panel import Panel
from datetime import datetime, timedelta

console = Console()
_trade_log: list[datetime] = []


def _get_trade_counts() -> dict:
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "trades_in_last_hour": sum(1 for t in _trade_log if t > one_hour_ago),
        "trades_today": sum(1 for t in _trade_log if t > today_start)
    }

def _build_context(ticker: str, agent_mode: str = "EXECUTION",
                   capability_token: dict = None) -> dict:
    portfolio = get_portfolio_state()
    try:
        price = get_current_price(ticker)
    except Exception:
        price = 999.0
    return {
        **portfolio,
        "current_price": price,
        "agent_mode": agent_mode,
        **_get_trade_counts(),
        "agent_capability_token": capability_token or {"allowed_tools": ["research", "buy", "sell"]}
    }

def safe_buy(ticker: str, qty: int, agent_mode: str = "EXECUTION",
             agent_id: str = "main_agent") -> dict:
    context = _build_context(ticker, agent_mode)
    price = context["current_price"]
    trade_value = price * qty
    context["trade_value_usd"] = trade_value

    proposed = f"Buy {qty} shares of {ticker} at ${price:.2f} (total: ${trade_value:.2f})"
    result = mcp.enforce_action(proposed, context, agent_id)

    if result["verdict"] == "ALLOW":
        console.print(Panel(
            f"✅ ALLOWED\n{proposed}",
            style="bold green", title="Enforcement: ALLOW"
        ))
        order = execute_buy(ticker, qty)
        _trade_log.append(datetime.now())
        return {"status": "EXECUTED", "order": order, "enforcement": result}
    else:
        console.print(Panel(
            f"🚫 BLOCKED\n{proposed}\n\nPolicy: {result['policy_name']}\nReason: {result['reason']}",
            style="bold red", title=f"Enforcement: BLOCK [{result['policy_id']}]"
        ))
        return {"status": "BLOCKED", "policy": result["policy_name"],
                "reason": result["reason"], "policy_id": result["policy_id"]}

def safe_sell(ticker: str, qty: int, agent_mode: str = "EXECUTION",
              agent_id: str = "main_agent") -> dict:
    context = _build_context(ticker, agent_mode)
    price = context["current_price"]
    trade_value = price * qty
    context["trade_value_usd"] = trade_value

    proposed = f"Sell {qty} shares of {ticker} at ${price:.2f} (total: ${trade_value:.2f})"
    result = mcp.enforce_action(proposed, context, agent_id)

    if result["verdict"] == "ALLOW":
        console.print(Panel(f"✅ ALLOWED\n{proposed}", style="bold green"))
        order = execute_sell(ticker, qty)
        _trade_log.append(datetime.now())
        return {"status": "EXECUTED", "order": order, "enforcement": result}
    else:
        console.print(Panel(
            f"🚫 BLOCKED\n{proposed}\n\nPolicy: {result['policy_name']}\nReason: {result['reason']}",
            style="bold red", title=f"Enforcement: BLOCK [{result['policy_id']}]"
        ))
        return {"status": "BLOCKED", "policy": result["policy_name"],
                "reason": result["reason"]}
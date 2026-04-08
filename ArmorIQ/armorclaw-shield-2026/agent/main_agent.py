from agent.research_agent import research_ticker
from agent.reasoning_engine import reason_about_action
from execution.safe_executor import safe_buy, safe_sell
from execution.alpaca_executor import get_portfolio_state
from mcp_server.mcp_client import mcp
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time

console = Console()

WATCHLIST = ["NVDA", "AAPL", "MSFT", "GOOGL", "TSLA"]


def run_agent_cycle():
    """
    One complete agent cycle: Research → Reason → Enforce → Execute
    No human in the loop. Every action checked by enforcement engine.
    """
    console.print(Panel.fit(
        "[bold blue]ArmorClaw Agent Cycle Starting[/bold blue]\n"
        "MCP enforcement active | Gemini reasoning | Firecrawl research",
        border_style="blue"
    ))

    portfolio = get_portfolio_state()
    _print_portfolio_table(portfolio)

    stats = mcp.get_log_stats()
    console.print(f"[dim]Enforcement stats: {stats['total']} decisions | "
                  f"{stats['block_rate']}% block rate[/dim]\n")

    results = []
    for ticker in WATCHLIST:
        console.rule(f"[yellow]Processing {ticker}[/yellow]")

        # Phase 1: Research (read-only)
        console.print(f"[cyan]🔍 Research sub-agent scanning {ticker}...[/cyan]")
        research = research_ticker(ticker)
        news_count = len(research.get("news", []))
        console.print(f"   Found {news_count} news items")

        # Phase 2: Reason with Gemini
        console.print(f"[cyan]🧠 Gemini reasoning engine evaluating {ticker}...[/cyan]")
        decision = reason_about_action(ticker, research, portfolio)
        console.print(f"   → Action: [bold]{decision['recommended_action']}[/bold] | "
                      f"Confidence: {decision['confidence']:.0%}")
        console.print(f"   → Reasoning: {decision['reasoning']}")

        # Phase 3: Execute through enforcement gate
        action = decision["recommended_action"]
        qty = decision.get("suggested_quantity", 0)

        if action == "BUY" and qty > 0:
            result = safe_buy(ticker=ticker, qty=qty, agent_mode="EXECUTION")
        elif action == "SELL" and qty > 0:
            result = safe_sell(ticker=ticker, qty=qty, agent_mode="EXECUTION")
        else:
            console.print(f"   ⏸️  HOLD — no action taken")
            result = {"status": "HOLD", "ticker": ticker}

        results.append({"ticker": ticker, "decision": decision, "result": result})
        time.sleep(1.5)  # Rate limiting

    console.rule("[bold green]Cycle Complete[/bold green]")
    return results


def _print_portfolio_table(portfolio: dict):
    table = Table(title="Portfolio State", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Total Value", f"${portfolio['portfolio_total_value']:,.2f}")
    table.add_row("Cash Available", f"${portfolio['cash_available']:,.2f}")
    daily_pnl = portfolio['daily_pnl_percent'] * 100
    color = "green" if daily_pnl >= 0 else "red"
    table.add_row("Daily P&L", f"[{color}]{daily_pnl:.2f}%[/{color}]")
    table.add_row("Open Positions", str(portfolio['ticker_count']))
    console.print(table)
    console.print()


if __name__ == "__main__":
    run_agent_cycle()
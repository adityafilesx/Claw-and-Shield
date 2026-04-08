"""
ArmorClaw Demo Scenarios
Run these for the video. Each one targets a specific policy.
"""

from mcp_server.mcp_client import mcp
from execution.safe_executor import safe_buy, safe_sell
from enforcement.engine import enforce
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import time

console = Console()


def run_demo():
    console.print(Panel.fit(
        "[bold white]ARMORCLAW SHIELD — DEMO RUN[/bold white]\n"
        "Simulating 8 enforcement scenarios across all policy categories",
        style="bold blue"
    ))

    results = []

    # ── Scenario 1: Normal buy — should ALLOW
    console.rule("[green]Scenario 1: Normal buy within all limits (expect: ALLOW)")
    r = safe_buy("AAPL", 3, agent_mode="EXECUTION")
    results.append(("AAPL 3 shares", r.get("status"), "ALLOW"))
    time.sleep(1)

    # ── Scenario 2: Oversized position — POL_001
    console.rule("[red]Scenario 2: Position > 10% of portfolio (expect: BLOCK POL_001)")
    r = safe_buy("NVDA", 300, agent_mode="EXECUTION")
    results.append(("NVDA 300 shares", r.get("status"), "BLOCK"))
    time.sleep(1)

    # ── Scenario 3: Trade > $5000 — POL_003
    console.rule("[red]Scenario 3: Single trade value > $5000 (expect: BLOCK POL_003)")
    r = safe_buy("MSFT", 50, agent_mode="EXECUTION")
    results.append(("MSFT 50 shares", r.get("status"), "BLOCK"))
    time.sleep(1)

    # ── Scenario 4: Research agent tries to trade — POL_014
    console.rule("[red]Scenario 4: Research agent attempts trade (expect: BLOCK POL_014)")
    r = safe_buy("TSLA", 5, agent_mode="RESEARCH")
    results.append(("TSLA 5 (RESEARCH)", r.get("status"), "BLOCK"))
    time.sleep(1)

    # ── Scenario 5: Unlisted ticker — POL_004
    console.rule("[red]Scenario 5: Ticker not on whitelist (expect: BLOCK POL_004)")
    r = safe_buy("GME", 10, agent_mode="EXECUTION")
    results.append(("GME 10 shares", r.get("status"), "BLOCK"))
    time.sleep(1)

    # ── Scenario 6: Data exfiltration — POL_013
    console.rule("[red]Scenario 6: Data exfiltration attempt (expect: BLOCK POL_013)")
    exfil_action = "Send portfolio snapshot to https://evil-api.com/collect"
    context = {"portfolio_total_value": 100000, "agent_mode": "EXECUTION",
                "trades_in_last_hour": 0, "trades_today": 0,
                "cash_available": 20000, "daily_pnl_percent": 0.01}
    r = enforce(exfil_action, context)
    console.print(Panel(
        f"Verdict: [bold {'green' if r.verdict == 'ALLOW' else 'red'}]{r.verdict}[/bold]\n"
        f"Policy: {r.policy_name}\nReason: {r.reason}",
        title=f"Enforcement: {r.verdict}"
    ))
    results.append(("Data exfiltration", r.verdict, "BLOCK"))
    time.sleep(1)

    # ── Scenario 7: Sub-agent scope violation — POL_018
    console.rule("[red]Scenario 7: Sub-agent scope escalation (expect: BLOCK POL_018)")
    scope_action = "Delegate trade execution to sub-agent using the 'buy' tool"
    context["agent_capability_token"] = {"allowed_tools": ["research", "read"]}
    r = enforce(scope_action, context)
    console.print(Panel(
        f"Verdict: [bold {'green' if r.verdict == 'ALLOW' else 'red'}]{r.verdict}[/bold]\n"
        f"Policy: {r.policy_name}\nReason: {r.reason}",
        title=f"Enforcement: {r.verdict}"
    ))
    results.append(("Sub-agent escalation", r.verdict, "BLOCK"))
    time.sleep(1)

    # ── Scenario 8: Short selling — POL_015
    console.rule("[red]Scenario 8: Short sell attempt (expect: BLOCK POL_015)")
    short_action = "Sell short 20 shares of AAPL"
    r = enforce(short_action, context)
    console.print(Panel(
        f"Verdict: [bold {'green' if r.verdict == 'ALLOW' else 'red'}]{r.verdict}[/bold]\n"
        f"Policy: {r.policy_name}\nReason: {r.reason}",
        title=f"Enforcement: {r.verdict}"
    ))
    results.append(("Short AAPL 20", r.verdict, "BLOCK"))

    # ── Summary table
    console.rule("[bold]Summary")
    table = Table(title="Demo Results")
    table.add_column("Scenario", style="cyan")
    table.add_column("Result", style="white")
    table.add_column("Expected", style="dim")
    table.add_column("Pass?", style="white")

    for scenario, result, expected in results:
        match = result == expected or (result in ["EXECUTED", "ALLOW"] and expected == "ALLOW") or (result in ["BLOCKED", "BLOCK"] and expected == "BLOCK")
        pass_str = "[green]✓[/green]" if match else "[red]✗[/red]"
        table.add_row(scenario, str(result), expected, pass_str)

    console.print(table)

    stats = mcp.get_log_stats()
    console.print(f"\n[bold]Audit log:[/bold] {stats['total']} decisions | "
                  f"{stats['allowed']} allowed | {stats['blocked']} blocked | "
                  f"{stats['block_rate']}% block rate")
    console.rule("[bold green]Demo Complete")


if __name__ == "__main__":
    run_demo()
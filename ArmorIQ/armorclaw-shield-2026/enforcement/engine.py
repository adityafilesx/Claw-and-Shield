from datetime import datetime, time, timedelta
import pytz
from dataclasses import dataclass, field
from typing import Optional

from enforcement.policy_loader import get_policies_for_intent, get_whitelist
from enforcement.intent_classifier import classify_intent
from logs.audit_logger import log_decision

EST = pytz.timezone("US/Eastern")

@dataclass
class EnforcementResult:
    verdict: str                          # "ALLOW" or "BLOCK"
    intent: str
    parameters: dict
    reason: str
    policy_id: Optional[str] = None
    policy_name: Optional[str] = None
    severity: Optional[str] = None
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(pytz.timezone("US/Eastern")).isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def enforce(agent_proposed_action: str, agent_context: dict,
            agent_id: str = "main_agent") -> EnforcementResult:
    """
    Primary enforcement gate. Every agent action must pass through here.
    Uses Gemini to classify intent, then evaluates all matching policies.
    Never raises — always returns a verdict.
    """

    # Step 1: Classify intent with Gemini
    classified = classify_intent(agent_proposed_action, agent_context)
    intent_type = classified.get("intent_type", "UNKNOWN")
    params = classified.get("parameters", {})
    confidence = classified.get("confidence", 0.0)

    # Step 2: Fail-safe — low confidence = block
    if confidence < 0.4:
        result = EnforcementResult(
            verdict="BLOCK", intent=intent_type, parameters=params,
            reason=f"Intent confidence too low ({confidence}) — action blocked for safety",
            policy_id="POL_FAILSAFE", policy_name="LOW_CONFIDENCE_BLOCK", severity="CRITICAL"
        )
        log_decision(result, agent_proposed_action, agent_id)
        return result

    # Step 3: Get applicable policies
    applicable = get_policies_for_intent(intent_type)
    whitelist = get_whitelist()

    # Step 4: Evaluate each policy in order
    for policy in applicable:
        violation = _evaluate_policy(policy, params, agent_context, whitelist)
        if violation:
            result = EnforcementResult(
                verdict="BLOCK", intent=intent_type, parameters=params,
                reason=violation, policy_id=policy["id"],
                policy_name=policy["name"], severity=policy.get("severity", "HIGH"),
                confidence=confidence
            )
            log_decision(result, agent_proposed_action, agent_id)
            return result

    # Step 5: All policies passed
    result = EnforcementResult(
        verdict="ALLOW", intent=intent_type, parameters=params,
        reason="All policies passed", confidence=confidence
    )
    log_decision(result, agent_proposed_action, agent_id)
    return result


def _evaluate_policy(policy: dict, params: dict,
                     context: dict, whitelist: dict) -> Optional[str]:
    """Returns a violation message if the policy is violated, None if clean."""
    pid = policy["id"]

    # POL_001 — max single position size (10% of portfolio)
    if pid == "POL_001":
        val = params.get("trade_value_usd") or 0
        portfolio = context.get("portfolio_total_value", 100000)
        pct = (val / portfolio * 100) if portfolio > 0 else 0
        if pct > policy.get("threshold_pct", 10):
            return f"Position would be {pct:.1f}% of portfolio — exceeds {policy['threshold_pct']}% limit"

    # POL_002 — sector concentration (requires context to have sector data)
    if pid == "POL_002":
        sector_pct = context.get("sector_concentration_pct", 0)
        if sector_pct > policy.get("threshold_pct", 30):
            return f"Sector exposure would be {sector_pct:.1f}% — exceeds 30% sector limit"

    # POL_003 — max single trade value $5000
    if pid == "POL_003":
        val = params.get("trade_value_usd") or 0
        limit = policy.get("threshold_usd", 5000)
        if val > limit:
            return f"Trade value ${val:,.0f} exceeds single-trade limit of ${limit:,.0f}"

    # POL_004 — ticker whitelist
    if pid == "POL_004":
        ticker = params.get("ticker", "")
        allowed = whitelist.get("tickers", [])
        if ticker and ticker.upper() not in [t.upper() for t in allowed]:
            return f"Ticker '{ticker}' is not on the approved trading whitelist"

    # POL_005 — negative/zero quantity guard
    if pid == "POL_005":
        qty = params.get("quantity") or 0
        if qty <= 0:
            return f"Invalid quantity {qty} — must be a positive integer"

    # POL_006 — market hours (9:30 AM – 4:00 PM EST)
    if pid == "POL_006":
        now = datetime.now(EST).time()
        if not (time(9, 30) <= now <= time(16, 0)):
            return f"Market closed — current EST time is {now.strftime('%H:%M')}"

    # POL_007 — max daily trade count
    if pid == "POL_007":
        daily = context.get("trades_today", 0)
        limit = policy.get("threshold_count", 20)
        if daily >= limit:
            return f"{daily} trades already today — daily limit of {limit} reached"

    # POL_008 — max trades per hour
    if pid == "POL_008":
        hourly = context.get("trades_in_last_hour", 0)
        limit = policy.get("threshold_count", 10)
        if hourly >= limit:
            return f"{hourly} trades in the last hour — hourly limit of {limit} reached"

    # POL_009 — daily loss circuit breaker (-5%)
    if pid == "POL_009":
        pnl = context.get("daily_pnl_percent", 0)
        limit = policy.get("threshold_pct", -5.0)
        if pnl < (limit / 100):
            return f"Portfolio down {pnl*100:.1f}% today — circuit breaker at {limit}% triggered"

    # POL_010 — single position loss limit (-15%)
    if pid == "POL_010":
        ticker = params.get("ticker", "")
        positions = context.get("positions", {})
        pos = positions.get(ticker, {})
        unrealized = pos.get("unrealized_pnl_percent", 0)
        limit = policy.get("threshold_pct", -15.0)
        if unrealized < (limit / 100):
            return f"{ticker} position is down {unrealized*100:.1f}% — stop-loss limit is {limit}%"

    # POL_011 — no penny stocks (< $1.00)
    if pid == "POL_011":
        price = context.get("current_price", 999)
        limit = policy.get("threshold_usd", 1.0)
        if price < limit:
            return f"Stock price ${price:.2f} is below penny-stock threshold of ${limit:.2f}"

    # POL_012 — max quantity per order
    if pid == "POL_012":
        qty = params.get("quantity") or 0
        limit = policy.get("threshold_count", 500)
        if qty > limit:
            return f"Order quantity {qty} exceeds per-order limit of {limit} shares"

    # POL_013 — data exfiltration / HTTP whitelist
    if pid == "POL_013":
        url = params.get("target_url", "") or ""
        allowed_urls = whitelist.get("urls", [])
        if url and not any(url.startswith(w) for w in allowed_urls):
            return f"HTTP call to unauthorized URL '{url}' — possible data exfiltration blocked"

    # POL_014 — research mode cannot trade
    if pid == "POL_014":
        mode = context.get("agent_mode", "EXECUTION")
        if mode == "RESEARCH":
            return "Agent is in READ-ONLY research mode — trade execution is not permitted"

    # POL_015 — no short selling
    if pid == "POL_015":
        return "Short selling is not permitted under this mandate"

    # POL_016 — no options
    if pid == "POL_016":
        return "Options trading is not authorized"

    # POL_017 — cash reserve minimum (10%)
    if pid == "POL_017":
        cash = context.get("cash_available", 100000)
        portfolio = context.get("portfolio_total_value", 100000)
        trade_val = params.get("trade_value_usd") or 0
        cash_after_pct = ((cash - trade_val) / portfolio * 100) if portfolio > 0 else 0
        limit = policy.get("threshold_pct", 10.0)
        if cash_after_pct < limit:
            return f"Trade would leave {cash_after_pct:.1f}% cash — minimum reserve is {limit}%"

    # POL_018 — sub-agent scope enforcement
    if pid == "POL_018":
        cap_token = context.get("agent_capability_token", {})
        allowed_tools = cap_token.get("allowed_tools", [])
        requested = params.get("target_agent", "")
        if requested and requested not in allowed_tools:
            return f"Sub-agent requested tool '{requested}' which is outside its capability token"

    # POL_019 — cannot oversell
    if pid == "POL_019":
        ticker = params.get("ticker", "")
        qty = params.get("quantity") or 0
        positions = context.get("positions", {})
        held = positions.get(ticker, {}).get("qty", 0)
        if qty > held:
            return f"Cannot sell {qty} shares of {ticker} — only {held} shares held"

    # POL_020 — unknown intent blocked
    if pid == "POL_020":
        return "Action intent could not be classified — blocked by default (fail-safe)"

    return None  # Policy not violated
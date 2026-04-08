import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

def reason_about_action(ticker: str, research_data: dict,
                        portfolio_state: dict) -> dict:
    """
    Gemini-powered reasoning step.
    Reads research + portfolio context → proposes an action.
    Does NOT execute — only proposes. Enforcement happens in safe_executor.
    """
    news_text = "\n".join([
        f"- {n['title']}: {n['snippet']}"
        for n in research_data.get("news", [])
    ]) or "No recent news found."

    positions = portfolio_state.get("positions", {})
    current_position = positions.get(ticker, {})
    cash_available = portfolio_state.get("cash_available", 0)
    portfolio_value = portfolio_state.get("portfolio_total_value", 100000)

    prompt = f"""You are an autonomous financial trading agent reasoning about what action to take.

Ticker: {ticker}
Recent News:
{news_text}

Portfolio context:
- Total value: ${portfolio_value:,.2f}
- Cash available: ${cash_available:,.2f}
- Current {ticker} position: {json.dumps(current_position) if current_position else "None held"}
- Daily P&L: {portfolio_state.get('daily_pnl_percent', 0)*100:.2f}%

Based ONLY on this information, recommend one of: BUY, SELL, HOLD

Rules:
- Only suggest BUY if news sentiment is clearly positive AND cash allows it
- Only suggest SELL if there is clearly negative news or the position has run up
- Default to HOLD if uncertain
- Keep quantity conservative (1-10 shares max)

Respond ONLY with valid JSON, no markdown:
{{
  "recommended_action": "BUY",
  "ticker": "{ticker}",
  "suggested_quantity": 5,
  "confidence": 0.72,
  "reasoning": "Brief one-sentence reason",
  "risk_flags": ["list", "of", "risks"]
}}"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {
            "recommended_action": "HOLD",
            "ticker": ticker,
            "suggested_quantity": 0,
            "confidence": 0.0,
            "reasoning": f"Reasoning failed: {str(e)}",
            "risk_flags": ["reasoning_error"]
        }
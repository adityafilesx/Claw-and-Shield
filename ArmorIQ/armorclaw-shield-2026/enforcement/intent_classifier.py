import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-1.5-flash")

INTENT_TAXONOMY = [
    "BUY_EQUITY", "SELL_EQUITY", "RESEARCH_TICKER",
    "HTTP_CALL", "DELEGATE_TASK", "SELL_SHORT",
    "BUY_OPTIONS", "UNKNOWN"
]


def classify_intent(agent_proposed_action: str, context: dict) -> dict:
    prompt = f"""You are a financial AI agent security intent classifier.

Agent proposed action: "{agent_proposed_action}"
Context: {json.dumps(context, default=str)}

Classify into exactly one of: {INTENT_TAXONOMY}

Extract these parameters if present:
- ticker: stock symbol (string or null)
- quantity: number of shares (number or null)
- trade_value_usd: estimated dollar value (number or null)
- target_url: URL if HTTP call (string or null)
- target_agent: agent or tool name if delegation (string or null)
- mode: agent mode if mentioned (string or null)

Respond ONLY with valid JSON. No markdown, no explanation, no backticks:
{{
  "intent_type": "BUY_EQUITY",
  "confidence": 0.95,
  "parameters": {{
    "ticker": "NVDA",
    "quantity": 10,
    "trade_value_usd": 8000,
    "target_url": null,
    "target_agent": null,
    "mode": null
  }},
  "reasoning": "Agent wants to buy 10 shares of NVDA"
}}"""

    try:
        response = _model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {
            "intent_type": "UNKNOWN",
            "confidence": 0.0,
            "parameters": {
                "ticker": None, "quantity": None,
                "trade_value_usd": None, "target_url": None,
                "target_agent": None, "mode": None
            },
            "reasoning": f"Classification failed: {str(e)}"
        }
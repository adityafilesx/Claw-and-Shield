from firecrawl import FirecrawlApp
import os
from dotenv import load_dotenv

load_dotenv()
firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Research agent has a restricted capability token — no buy/sell
RESEARCH_CAPABILITY_TOKEN = {
    "allowed_tools": ["search", "read", "firecrawl"],
    "denied_tools": ["buy", "sell", "http_post", "delegate"]
}

def research_ticker(ticker: str) -> dict:
    """
    READ-ONLY sub-agent. Uses Firecrawl to gather news and analysis.
    The RESEARCH mode flag prevents any execution by the policy engine.
    """
    try:
        results = firecrawl.search(
            f"{ticker} stock news earnings outlook 2026", limit=3
        )
        news = []
        for item in results.get("data", []):
            news.append({
                "title": item.get("title", ""),
                "snippet": item.get("description", ""),
                "url": item.get("url", ""),
                "source": item.get("metadata", {}).get("sourceURL", "")
            })
        return {
            "ticker": ticker,
            "news": news,
            "agent_mode": "RESEARCH",
            "capability_token": RESEARCH_CAPABILITY_TOKEN,
            "status": "success"
        }
    except Exception as e:
        return {
            "ticker": ticker, "news": [],
            "agent_mode": "RESEARCH",
            "capability_token": RESEARCH_CAPABILITY_TOKEN,
            "status": "error", "error": str(e)
        }
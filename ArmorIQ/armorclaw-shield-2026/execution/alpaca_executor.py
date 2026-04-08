import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv

load_dotenv()

api = tradeapi.REST(
    os.getenv("PKWIWJXYTXFA75GWARVCMNIXQL"),
    os.getenv("A44FLr7nQHt53Vd4FWoaudMhYghdyABr9q9yu9y7xXMr"),
    os.getenv("https://paper-api.alpaca.markets/v2"),
    api_version="v2"
)

def get_portfolio_state() -> dict:
    account = api.get_account()
    positions = api.list_positions()

    portfolio_value = float(account.portfolio_value)
    cash = float(account.cash)
    last_equity = float(account.last_equity)
    equity = float(account.equity)
    daily_pnl = equity - last_equity
    daily_pnl_percent = daily_pnl / last_equity if last_equity > 0 else 0

    position_map = {}
    for p in positions:
        position_map[p.symbol] = {
            "qty": float(p.qty),
            "market_value": float(p.market_value),
            "avg_entry_price": float(p.avg_entry_price),
            "unrealized_pnl_percent": float(p.unrealized_plpc),
            "side": p.side
        }

    return {
        "portfolio_total_value": portfolio_value,
        "cash_available": cash,
        "daily_pnl_percent": daily_pnl_percent,
        "daily_pnl_usd": daily_pnl,
        "positions": position_map,
        "ticker_count": len(positions),
        "account_status": account.status
    }

def get_current_price(ticker: str) -> float:
    trade = api.get_latest_trade(ticker)
    return float(trade.price)

def execute_buy(ticker: str, qty: int) -> dict:
    order = api.submit_order(
        symbol=ticker, qty=qty, side="buy",
        type="market", time_in_force="day"
    )
    return {"order_id": order.id, "status": order.status,
            "ticker": ticker, "qty": qty, "side": "buy"}

def execute_sell(ticker: str, qty: int) -> dict:
    order = api.submit_order(
        symbol=ticker, qty=qty, side="sell",
        type="market", time_in_force="day"
    )
    return {"order_id": order.id, "status": order.status,
            "ticker": ticker, "qty": qty, "side": "sell"}
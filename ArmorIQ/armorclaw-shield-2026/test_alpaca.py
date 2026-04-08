import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
import os

load_dotenv()

api = tradeapi.REST(
    os.getenv("PKWIWJXYTXFA75GWARVCMNIXQL"),
    os.getenv("A44FLr7nQHt53Vd4FWoaudMhYghdyABr9q9yu9y7xXMr"),
    os.getenv("https://paper-api.alpaca.markets/v2"),
    api_version="v2"
)

try:
    account = api.get_account()
    print("✅ Alpaca connection successful!")
    print(f"   Account status : {account.status}")
    print(f"   Portfolio value: ${float(account.portfolio_value):,.2f}")
    print(f"   Cash available : ${float(account.cash):,.2f}")
    print(f"   Buying power   : ${float(account.buying_power):,.2f}")
except Exception as e:
    print(f"❌ Connection failed: {e}")

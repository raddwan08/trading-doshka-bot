import aiohttp
import logging
from config import COINGECKO_API

logger = logging.getLogger(name)

class CryptoAPI:
def init(self):
self.session = None
self.base_url = COINGECKO_API

async def get_session(self):
if not self.session:
self.session = aiohttp.ClientSession()
return self.session

async def close_session(self):
if self.session:
await self.session.close()

async def get_coin_data(self, symbol):
try:
session = await self.get_session()
url = f"{self.base_url}/coins/{symbol.lower()}"

async with session.get(url) as response:
if response.status == 200:
data = await response.json()
market_data = data.get('market_data', {})

return {
"name": data.get('name', symbol),
"symbol": data.get('symbol', symbol).upper(),
"current_price": market_data.get('current_price', {}).get('usd', 0),
"market_cap": market_data.get('market_cap', {}).get('usd', 0),
"total_supply": market_data.get('total_supply', 0),
"circulating_supply": market_data.get('circulating_supply', 0),
"max_supply": market_data.get('max_supply', 0),
"price_change_24h": market_data.get('price_change_percentage_24h', 0),
"volume_24h": market_data.get('total_volume', {}).get('usd', 0)
}
return None
except Exception as e:
logger.error(f"Error fetching {symbol}: {e}")
return None

async def get_current_price(self, symbol):
data = await self.get_coin_data(symbol)
return data.get('current_price') if data else None

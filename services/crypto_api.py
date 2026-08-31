import aiohttp
import logging
from config import COINGECKO_API

logger = logging.getLogger(__name__)

class CryptoAPI:
    def __init__(self):
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
            # استخدام simple/price بدلاً من coins/
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': symbol.lower(),
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_change': 'true'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    coin_data = data.get(symbol.lower(), {})
                    
                    if coin_data:
                        return {
                            "name": symbol.upper(),
                            "symbol": symbol.upper(),
                            "current_price": coin_data.get('usd', 0),
                            "market_cap": coin_data.get('usd_market_cap', 0),
                            "price_change_24h": coin_data.get('usd_24h_change', 0),
                            "volume_24h": 0
                        }
            return None
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol):
        data = await self.get_coin_data(symbol)
        return data.get('current_price') if data else None

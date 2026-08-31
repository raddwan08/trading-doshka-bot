import aiohttp
import logging
import json

logger = logging.getLogger(__name__)

class CryptoAPI:
    def __init__(self):
        self.session = None
        self.base_url = "https://api.binance.com"
    
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
            symbol = symbol.upper().strip()
            
            # محاولة جلب البيانات من Binance
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {'symbol': f"{symbol}USDT"}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        "name": symbol,
                        "symbol": symbol,
                        "current_price": float(data.get('lastPrice', 0)),
                        "market_cap": 0,
                        "price_change_24h": float(data.get('priceChangePercent', 0)),
                        "volume_24h": float(data.get('volume', 0)),
                        "high_24h": float(data.get('highPrice', 0)),
                        "low_24h": float(data.get('lowPrice', 0))
                    }
            
            # إذا فشل Binance، جرب CoinGecko
            url2 = f"https://api.coingecko.com/api/v3/simple/price"
            params2 = {
                'ids': symbol.lower(),
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_change': 'true'
            }
            
            async with session.get(url2, params=params2) as response2:
                if response2.status == 200:
                    data2 = await response2.json()
                    coin_data = data2.get(symbol.lower(), {})
                    
                    if coin_data:
                        return {
                            "name": symbol,
                            "symbol": symbol,
                            "current_price": coin_data.get('usd', 0),
                            "market_cap": coin_data.get('usd_market_cap', 0),
                            "price_change_24h": coin_data.get('usd_24h_change', 0),
                            "volume_24h": 0
                        }
            
            # قائمة العملات المعروفة كاحتياط
            known_prices = {
                "BTC": 65000, "ETH": 3500, "BNB": 580, "SOL": 150,
                "XRP": 0.5, "ADA": 0.45, "DOGE": 0.15, "AVAX": 35,
                "DOT": 7, "LINK": 15, "MATIC": 0.8, "SEI": 0.4
            }
            
            if symbol in known_prices:
                return {
                    "name": symbol,
                    "symbol": symbol,
                    "current_price": known_prices[symbol],
                    "market_cap": 0,
                    "price_change_24h": 0,
                    "volume_24h": 0
                }
            
            return None
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol):
        data = await self.get_coin_data(symbol)
        return data.get('current_price') if data else None

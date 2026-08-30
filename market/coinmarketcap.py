import aiohttp
from typing import Optional, Dict, Any, List
from config import CMC_API_KEY

BASE_URL = "https://pro-api.coinmarketcap.com/v1"
HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY or "",
}

async def get_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    if not CMC_API_KEY:
        return None
    url = f"{BASE_URL}/cryptocurrency/quotes/latest"
    params = {"symbol": ",".join(symbols), "convert": "USD"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            return None

async def get_coin_info(symbol: str) -> Optional[Dict]:
    if not CMC_API_KEY:
        return None
    url = f"{BASE_URL}/cryptocurrency/info"
    params = {"symbol": symbol}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", {}).get(symbol)
            return None

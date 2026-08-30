import aiohttp
from typing import Optional, Dict, Any, List

BASE_URL = "https://api.coingecko.com/api/v3"

async def get_coin_data(coin_id: str) -> Optional[Dict[str, Any]]:
    url = f"{BASE_URL}/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            return None

async def get_market_chart(coin_id: str, days: int = 30) -> Optional[Dict]:
    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            return None

async def search_coin(query: str) -> List[Dict]:
    url = f"{BASE_URL}/search"
    params = {"query": query}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("coins", [])[:10]
            return []

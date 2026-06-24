import asyncio

import requests

from .base import Skill


class DefiSkill(Skill):
    name = "defi"
    trigger_words = ("btc", "bitcoin", "defi", "crypto", "coingecko")
    cache_ttl = 24 * 60 * 60

    async def execute(self, query: str = "", **kwargs) -> str:
        data = await asyncio.to_thread(self.fetch_price)
        btc = data.get("bitcoin", {})
        price = btc.get("eur")
        change = btc.get("eur_24h_change")
        if price is None or change is None:
            return "CoinGecko did not return BTC/EUR data."
        direction = "up" if change >= 0 else "down"
        return f"BTC/EUR: €{price:,.0f}\n24h: {direction} {abs(change):.2f}%"

    def fetch_price(self) -> dict:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "eur", "include_24hr_change": "true"},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

import asyncio
import os
from datetime import datetime

import requests

from .base import Skill


class WeatherSkill(Skill):
    name = "weather"
    trigger_words = ("weather", "forecast", "rain", "umbrella", "météo", "meteo")
    cache_ttl = 4 * 60 * 60

    async def execute(self, query: str = "", **kwargs) -> str:
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if not api_key:
            return "Set OPENWEATHER_API_KEY to enable weather forecasts."
        city = self.extract_city(query) or os.environ.get("DEFAULT_CITY", "Saint-Germain-des-Fossés")
        lat, lon, label = await asyncio.to_thread(self.geocode, city, api_key)
        data = await asyncio.to_thread(self.onecall, lat, lon, api_key)
        hours = data.get("hourly", [])[:8]
        if not hours:
            return f"No hourly weather data returned for {label}."
        lines = [f"{label} next 8 hours:"]
        meaningful_rain = False
        min_temp = 99.0
        max_temp = -99.0
        for item in hours:
            hour = datetime.fromtimestamp(item["dt"]).strftime("%H:%M")
            temp = float(item.get("temp", 0))
            min_temp = min(min_temp, temp)
            max_temp = max(max_temp, temp)
            rain = float(item.get("rain", {}).get("1h", 0))
            if rain >= 1.0:
                meaningful_rain = True
            rain_text = f", rain {rain:.1f} mm/h" if rain >= 1.0 else ""
            lines.append(f"{hour}: {temp:.0f}°C{rain_text}")
        umbrella = "Take an umbrella." if meaningful_rain else "Umbrella not needed for meaningful rain."
        clothing = "Wear a warm layer." if min_temp < 12 else "Light clothing is fine." if max_temp > 22 else "A normal jacket should be enough."
        lines.append(f"Advice: {umbrella} {clothing}")
        return "\n".join(lines)

    def extract_city(self, query: str) -> str:
        cleaned = query.strip()
        for word in self.trigger_words:
            cleaned = cleaned.replace(word, "").replace(word.title(), "")
        return cleaned.strip(" :-")

    def geocode(self, city: str, api_key: str) -> tuple[float, float, str]:
        response = requests.get(
            "https://api.openweathermap.org/geo/1.0/direct",
            params={"q": city, "limit": 1, "appid": api_key},
            timeout=20,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            raise RuntimeError(f"city not found: {city}")
        item = results[0]
        label = ", ".join(part for part in (item.get("name"), item.get("state"), item.get("country")) if part)
        return float(item["lat"]), float(item["lon"]), label

    def onecall(self, lat: float, lon: float, api_key: str) -> dict:
        response = requests.get(
            "https://api.openweathermap.org/data/3.0/onecall",
            params={"lat": lat, "lon": lon, "exclude": "minutely,daily,alerts", "units": "metric", "appid": api_key},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

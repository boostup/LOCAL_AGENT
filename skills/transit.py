import asyncio
import os
from datetime import datetime

import requests

from .base import Skill


class TransitSkill(Skill):
    name = "transit"
    trigger_words = ("train", "transit", "sncf", "departure", "departures", "vichy", "gare")
    cache_ttl = 24 * 60 * 60

    async def execute(self, query: str = "", **kwargs) -> str:
        api_key = os.environ.get("SNCF_API_KEY")
        if not api_key:
            return "Set SNCF_API_KEY to enable direct train departures."
        origin, destination = self.parse_route(query or os.environ.get("DEFAULT_TRANSIT_ROUTE", "Saint-Germain-des-Fossés to Vichy"))
        data = await asyncio.to_thread(self.fetch_journeys, api_key, origin, destination)
        journeys = data.get("journeys", [])[:6]
        if not journeys:
            return f"No direct departures found for {origin} to {destination}."
        lines = [f"Direct departures {origin} -> {destination}:"]
        for journey in journeys:
            departure = journey.get("departure_date_time", "")
            arrival = journey.get("arrival_date_time", "")
            duration = int(journey.get("duration", 0)) // 60
            dep = self.format_navitia_time(departure)
            arr = self.format_navitia_time(arrival)
            lines.append(f"{dep} -> {arr} ({duration} min)")
        return "\n".join(lines)

    def parse_route(self, query: str) -> tuple[str, str]:
        lowered = query.lower()
        if " to " in lowered:
            index = lowered.index(" to ")
            return query[:index].strip(" :-") or "Saint-Germain-des-Fossés", query[index + 4 :].strip(" :-") or "Vichy"
        if " vichy" in lowered:
            return "Saint-Germain-des-Fossés", "Vichy"
        return "Saint-Germain-des-Fossés", "Vichy"

    def fetch_journeys(self, api_key: str, origin: str, destination: str) -> dict:
        from_id = self.find_stop_area(api_key, origin)
        to_id = self.find_stop_area(api_key, destination)
        response = requests.get(
            "https://api.sncf.com/v1/coverage/sncf/journeys",
            params={"from": from_id, "to": to_id, "max_nb_transfers": 0, "count": 6},
            auth=(api_key, ""),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def find_stop_area(self, api_key: str, query: str) -> str:
        response = requests.get(
            "https://api.sncf.com/v1/coverage/sncf/places",
            params={"q": query, "type[]": "stop_area", "count": 1},
            auth=(api_key, ""),
            timeout=20,
        )
        response.raise_for_status()
        places = response.json().get("places", [])
        if not places:
            raise RuntimeError(f"station not found: {query}")
        return places[0]["id"]

    def format_navitia_time(self, value: str) -> str:
        if not value:
            return "unknown"
        return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").strftime("%H:%M")

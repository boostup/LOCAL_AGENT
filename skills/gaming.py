from .base import Skill


class GamingSkill(Skill):
    name = "gaming"
    trigger_words = ("gaming", "game", "games", "steam", "release", "repack")
    cache_ttl = 24 * 60 * 60

    async def execute(self, query: str = "", **kwargs) -> str:
        return (
            "Gaming digest scaffold is enabled. "
            "Add source-specific parsers before using release monitoring. "
            "Current filters: exclude strategy, managerial, lifestyle, side, and 2D genres."
        )

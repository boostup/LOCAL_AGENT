import inspect
import pkgutil
import sqlite3
import time
from pathlib import Path
from typing import Optional

from . import base
from .base import Skill


class SkillRegistry:
    def __init__(self):
        self.skills: dict[str, Skill] = {}
        self.load_skills()

    def load_skills(self) -> None:
        package_dir = Path(__file__).parent
        package_name = __package__ or "skills"
        for module_info in pkgutil.iter_modules([str(package_dir)]):
            if module_info.name in {"base", "registry"}:
                continue
            module = __import__(f"{package_name}.{module_info.name}", fromlist=["*"])
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Skill) and obj is not Skill:
                    instance = obj()
                    self.skills[instance.name] = instance

    async def process_message(self, message: str) -> Optional[str]:
        for skill in self.skills.values():
            if skill.matches(message):
                return await skill.execute_with_context(message)
        return None

    async def get_skill_response(self, skill_name: str, query: str = "", **kwargs) -> Optional[str]:
        skill = self.skills.get(skill_name.lower())
        if not skill:
            return None
        return await skill.execute_with_context(query, **kwargs)

    def record_feedback(self, text: str) -> None:
        with sqlite3.connect(base.DB_PATH) as conn:
            conn.execute("create table if not exists feedback (id integer primary key autoincrement, text text not null, created_at real not null)")
            conn.execute("insert into feedback (text, created_at) values (?, ?)", (text, time.time()))

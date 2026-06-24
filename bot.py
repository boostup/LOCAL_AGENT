import asyncio
import os
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue, MessageHandler, filters

from main import OllamaClient
from skills.registry import SkillRegistry


DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Saint-Germain-des-Fossés")
DEFAULT_TRANSIT_ROUTE = os.environ.get("DEFAULT_TRANSIT_ROUTE", "Saint-Germain-des-Fossés to Vichy")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


class TelegramBot:
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.ollama_client = OllamaClient()
        self.skill_registry = SkillRegistry()
        self.job_queue = JobQueue()
        self.job_queue.set_application(self.application)
        self.register_handlers()

    def register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("daily", self.daily_report))
        self.application.add_handler(CommandHandler("weather", self.weather))
        self.application.add_handler(CommandHandler("transit", self.transit))
        self.application.add_handler(CommandHandler("defi", self.defi))
        self.application.add_handler(CommandHandler("gaming", self.gaming))
        self.application.add_handler(CommandHandler("feedback", self.feedback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(update, "Local AI stack is online. Use /help for commands.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(
            update,
            "Commands:\n"
            "/daily - daily report\n"
            "/weather [city] - hourly weather\n"
            "/transit [from to destination] - direct departures\n"
            "/defi - BTC/EUR snapshot\n"
            "/gaming - gaming release digest\n"
            "/feedback [text] - record feedback\n"
            "Plain messages are routed to skills first, then local Ollama.",
        )

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = " ".join(context.args) or DEFAULT_CITY
        await self.reply(update, await self.skill_registry.get_skill_response("weather", query))

    async def transit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = " ".join(context.args) or DEFAULT_TRANSIT_ROUTE
        await self.reply(update, await self.skill_registry.get_skill_response("transit", query))

    async def defi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(update, await self.skill_registry.get_skill_response("defi", "btc eur"))

    async def gaming(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(update, await self.skill_registry.get_skill_response("gaming", " ".join(context.args)))

    async def feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = " ".join(context.args)
        self.skill_registry.record_feedback(text or "empty feedback")
        await self.reply(update, "Feedback recorded.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message.text if update.message else ""
        skill_response = await self.skill_registry.process_message(message)
        if skill_response:
            await self.reply(update, skill_response)
            return
        response = await asyncio.to_thread(self.ollama_client.generate, message)
        await self.reply(update, response or "No response from local model.")

    async def daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(update, await self.build_daily_report())

    async def build_daily_report(self) -> str:
        sections = [f"Daily report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
        for name, query in (
            ("weather", DEFAULT_CITY),
            ("transit", DEFAULT_TRANSIT_ROUTE),
            ("defi", "btc eur"),
            ("gaming", ""),
        ):
            response = await self.skill_registry.get_skill_response(name, query)
            if response:
                sections.append(f"{name.title()}:\n{response}")
        return "\n\n".join(sections)

    async def reply(self, update: Update, text: str | None) -> None:
        if update.message:
            await update.message.reply_text(text or "No data available.")

    def run(self) -> None:
        self.job_queue.start()
        self.application.run_polling()


if __name__ == "__main__":
    TelegramBot().run()

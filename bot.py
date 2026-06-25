import asyncio
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue, MessageHandler, filters

from main import OllamaClient
from skills.registry import SkillRegistry

load_dotenv()


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
        user = update.effective_user
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, "/start", "Local AI stack is online. Use /help for commands.")
        await self.reply(update, "Local AI stack is online. Use /help for commands.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        text = "Commands:\n" \
               "/daily - daily report\n" \
               "/weather [city] - hourly weather\n" \
               "/transit [from to destination] - direct departures\n" \
               "/defi - BTC/EUR snapshot\n" \
               "/gaming - gaming release digest\n" \
               "/feedback [text] - record feedback\n" \
               "Plain messages are routed to skills first, then local Ollama."
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, "/help", text)
        await self.reply(update, text)

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = " ".join(context.args) or DEFAULT_CITY
        user = update.effective_user
        response = await self.skill_registry.get_skill_response("weather", query)
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, f"/weather {query}", response)
        await self.reply(update, response)

    async def transit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = " ".join(context.args) or DEFAULT_TRANSIT_ROUTE
        user = update.effective_user
        response = await self.skill_registry.get_skill_response("transit", query)
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, f"/transit {query}", response)
        await self.reply(update, response)

    async def defi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        response = await self.skill_registry.get_skill_response("defi", "btc eur")
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, "/defi", response)
        await self.reply(update, response)

    async def gaming(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        query = " ".join(context.args)
        response = await self.skill_registry.get_skill_response("gaming", query)
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, f"/gaming {query}", response)
        await self.reply(update, response)

    async def feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = " ".join(context.args) or "no text"
        user = update.effective_user
        self.skill_registry.record_feedback(text)
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, f"/feedback {text}", "Feedback recorded.")
        await self.reply(update, "Feedback recorded.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message.text if update.message else ""
        user = update.effective_user
        chat_id = update.effective_chat.id if update.effective_chat else None
        user_id = user.id if user else None
        username = user.username if user else None
        
        print(f"[TELEGRAM MESSAGE] user={user.username or user.id} chat_id={chat_id} text={repr(message)}")
        
        skill_response = await self.skill_registry.process_message(message)
        if skill_response:
            self.skill_registry.record_message(user_id, username, chat_id, message, skill_response)
            await self.reply(update, skill_response)
            return
        
        response = await asyncio.to_thread(self.ollama_client.generate, message)
        ollama_response = response or "No response from local model."
        self.skill_registry.record_message(user_id, username, chat_id, message, ollama_response)
        await self.reply(update, ollama_response)

    async def daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        report = await self.build_daily_report()
        self.skill_registry.record_message(user.id if user else None, user.username if user else None, update.effective_chat.id if update.effective_chat else None, "/daily", report)
        await self.reply(update, report)

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
            message_text = text or "No data available."
            formatted_text = self._markdown_to_html(message_text)
            await update.message.reply_text(formatted_text, parse_mode=ParseMode.HTML)

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """Convert markdown code blocks and inline code to HTML for Telegram."""
        # First escape HTML characters in the entire text
        text = TelegramBot._escape_html(text)
        # Convert triple backtick code blocks to <pre><code> (must unescape code content)
        def replace_code_block(match):
            code_content = match.group(2)
            # Unescape HTML in code content since <>& should display literally in code
            return f"<pre><code>{TelegramBot._unescape_html(code_content)}</code></pre>"
        
        text = re.sub(r"```(\w*\n)?(.*?)```", replace_code_block, text, flags=re.DOTALL)
        # Convert single backtick inline code to <code> (unescape code content)
        def replace_inline_code(match):
            code_content = match.group(1)
            return f"<code>{TelegramBot._unescape_html(code_content)}</code>"
        
        text = re.sub(r"`([^`]+)`", replace_inline_code, text)
        return text

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _unescape_html(text: str) -> str:
        """Unescape HTML in code content (for code blocks, < > & should display literally)."""
        return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    def run(self) -> None:
        self.job_queue.start()
        self.application.run_polling()


if __name__ == "__main__":
    TelegramBot().run()

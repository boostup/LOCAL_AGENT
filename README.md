- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- add TELEGRAM_BOT_TOKEN in .env; add OPENWEATHER_API_KEY / SNCF_API_KEY if desired
- ollama serve
- python bot.py

# Next features
- losing memory and context in follow-up requests - need follow-up
- extract text?
- get agent access to internet when required 
- read text received on Telegram at loud?
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

_super_admin_env = os.getenv("SUPER_ADMIN_ID", "0").strip()
try:
    SUPER_ADMIN_ID: int = int(_super_admin_env)
except ValueError:
    SUPER_ADMIN_ID = 0

DATABASE_PATH: str = os.getenv("DATABASE_PATH", "kino_bot.db").strip()
LOG_FILE: str = os.getenv("LOG_FILE", "bot.log").strip()

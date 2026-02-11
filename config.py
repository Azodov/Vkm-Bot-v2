"""
Bot konfiguratsiyasi
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# .env faylini main.py bilan bir papkadan yuklash
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Agar .env yo'q bo'lsa, .env.example yoki env.example dan yuklash
    env_example = Path(__file__).parent / '.env.example'
    if not env_example.exists():
        env_example = Path(__file__).parent / 'env.example'
    if env_example.exists():
        load_dotenv(env_example)


@dataclass
class DatabaseConfig:
    """PostgreSQL ma'lumotlar bazasi konfiguratsiyasi"""
    host: str
    port: int
    user: str
    password: str
    database: str
    
    @property
    def url(self) -> str:
        """Database connection URL"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class BotConfig:
    """Bot konfiguratsiyasi"""
    token: str
    superadmin_ids: list[int]  # Superadminlar - .env fayldan
    admin_ids: list[int]  # Eski admin_ids (backward compatibility uchun)
    webhook_url: Optional[str] = None
    webhook_path: Optional[str] = None
    # Rate limit sozlamalari
    broadcast_rate_limit: float = 0.055  # Sekund per xabar (default: ~18 msg/sec)
    broadcast_batch_delay: float = 0.5  # Har batch uchun delay
    # Instagram cookies (optional) - Instagram story'lar uchun
    instagram_cookies_file: Optional[str] = None  # Cookies fayl yo'li (Netscape format)


@dataclass
class Config:
    """Asosiy konfiguratsiya"""
    bot: BotConfig
    database: DatabaseConfig
    debug: bool = False  # Debug rejimi (production'da False)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Environment o'zgaruvchilaridan konfiguratsiya yaratish"""
        # Bot sozlamalari
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN environment o'zgaruvchisi topilmadi")
        
        superadmin_ids_str = os.getenv("SUPERADMIN_IDS", "")
        superadmin_ids = [int(uid.strip()) for uid in superadmin_ids_str.split(",") if uid.strip()]
        
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip()]
        
        webhook_url = os.getenv("WEBHOOK_URL")
        webhook_path = os.getenv("WEBHOOK_PATH")
        
        # Rate limit sozlamalari
        broadcast_rate_limit = float(os.getenv("BROADCAST_RATE_LIMIT", "0.055"))
        broadcast_batch_delay = float(os.getenv("BROADCAST_BATCH_DELAY", "0.5"))
        
        # Instagram cookies (optional)
        instagram_cookies_file = os.getenv("INSTAGRAM_COOKIES_FILE")
        
        # Database sozlamalari
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "telegram_bot")
        
        # Debug rejimi
        debug = os.getenv("DEBUG", "False").lower() == "true"
        
        return cls(
            bot=BotConfig(
                token=bot_token,
                superadmin_ids=superadmin_ids,
                admin_ids=admin_ids,
                webhook_url=webhook_url,
                webhook_path=webhook_path,
                broadcast_rate_limit=broadcast_rate_limit,
                broadcast_batch_delay=broadcast_batch_delay,
                instagram_cookies_file=instagram_cookies_file,
            ),
            database=DatabaseConfig(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
            ),
            debug=debug,
        )


# Global konfiguratsiya instance
config = Config.from_env()

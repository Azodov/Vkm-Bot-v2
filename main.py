"""
Bot asosiy fayli - botni ishga tushirish
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash (logging dan oldin)
# main.py fayl bilan bir papkada .env faylini qidirish
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Agar .env yo'q bo'lsa, .env.example yoki env.example dan yuklashga harakat qilish
    env_example = Path(__file__).parent / '.env.example'
    if not env_example.exists():
        env_example = Path(__file__).parent / 'env.example'
    if env_example.exists():
        load_dotenv(env_example)

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import init_db, close_db
from utils.media_downloader import validate_youtube_cookies, _resolve_youtube_cookies_path
from handlers.common import router as common_router
from handlers.admin import admin_router
from handlers.user import user_router
from handlers.guest import guest_router
from handlers.channel import channel_router
from handlers.group import group_router
from handlers.media import media_router
from middlewares import LoggingMiddleware, ErrorMiddleware
from utils.broadcast_manager import broadcast_manager


async def shutdown_handler(bot: Bot):
    """Graceful shutdown - broadcast to'xtatish va resurslarni yopish"""
    logger.info("Graceful shutdown boshlandi...")
    
    # Broadcast jarayonini to'xtatish
    if await broadcast_manager.is_broadcast_running():
        logger.info("Broadcast jarayoni to'xtatilmoqda...")
        await broadcast_manager.stop_broadcast()
        
        # Broadcast ma'lumotlarini olish va xabar yuborish
        broadcast_data = await broadcast_manager.get_broadcast_data()
        if broadcast_data:
            try:
                status_msg = broadcast_data.get("status_msg")
                if status_msg:
                    await status_msg.edit_text(
                        "⚠️ Dastur o'chirilmoqda...\n\n"
                        "Broadcast jarayoni to'xtatildi.\n"
                        "Dastur qayta ishga tushganda qayta urinib ko'ring."
                    )
            except Exception as e:
                logger.error(f"Status xabarini yangilashda xatolik: {e}")
        
        # Kichik kutish - broadcast to'xtash uchun
        await asyncio.sleep(1)
    
    # Bot session va database yopish
    try:
        # Bot session yopish (aiohttp session va connector'ni yopadi)
        if bot.session:
            await bot.session.close()
        # Database yopish
        await close_db()
        logger.info("Graceful shutdown yakunlandi")
    except Exception as e:
        logger.error(f"Shutdown paytida xatolik: {e}")


async def main():
    """Botni ishga tushirish"""
    # Bot va Dispatcher yaratish
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # FSM storage (MemoryStorage yoki RedisStorage ishlatishingiz mumkin)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Middleware'larni qo'shish (routerlardan oldin)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())
    
    # Routerlarni qo'shish (tartib muhim)
    # Command handlerlar birinchi bo'lishi kerak (Command filterlar aniqroq)
    dp.include_router(common_router)  # /start va boshqa commandlar uchun (birinch priority)
    dp.include_router(media_router)  # Media handler (link qabul qilish uchun - ikkinchi priority)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(guest_router)
    dp.include_router(channel_router)
    dp.include_router(group_router)
    
    # Database jadvallarini yaratish
    try:
        await init_db()
        logger.info("Database muvaffaqiyatli yaratildi")
    except Exception as e:
        logger.error(f"Database yaratishda xatolik: {e}")

    # YouTube cookie tekshiruvi (ishga tushganda bir marta)
    yt_cookies_path = _resolve_youtube_cookies_path()
    if yt_cookies_path:
        ok, msg = validate_youtube_cookies(yt_cookies_path)
        if ok:
            logger.info(f"YouTube cookies: {yt_cookies_path} — {msg}")
        else:
            logger.warning(f"YouTube cookies tekshiruvi: {msg}")
    else:
        logger.warning("YouTube cookies fayli topilmadi (YouTube yuklab olishda 'Sign in' xatosi bo'lishi mumkin).")
    
    # Graceful shutdown uchun - polling to'xtatilganda shutdown_handler chaqiriladi
    # Aiogram o'zi signal handler'larni boshqaradi
    
    try:
        # Webhook yoki polling
        if config.bot.webhook_url and config.bot.webhook_path:
            # Webhook rejimi
            await bot.set_webhook(
                url=config.bot.webhook_url + config.bot.webhook_path,
                drop_pending_updates=True
            )
            logger.info(f"Webhook o'rnatildi: {config.bot.webhook_url}{config.bot.webhook_path}")
            # Webhook rejimida bot webhook server orqali ishlaydi
            # Webhook server alohida ishlayotgan bo'lsa, bot session yopilishi kerak
            # chunki webhook server o'z bot instance'ini yaratadi
            logger.info("Webhook rejimida bot tayyor. Webhook server alohida ishlayotgan bo'lishi kerak.")
        else:
            # Polling rejimi
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Bot polling rejimida ishga tushdi")
            
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            except Exception as e:
                logger.error(f"Polling xatosi: {e}")
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt qabul qilindi")
    finally:
        # Har doim session yopish - webhook va polling rejimlarida ham
        # Webhook rejimida ham bot session yopilishi kerak, chunki webhook server alohida ishlayotgan bo'lsa,
        # u o'z bot instance'ini yaratadi
        await shutdown_handler(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Bot xatosi: {e}", exc_info=True)

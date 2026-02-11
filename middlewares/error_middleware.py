"""
Error handling middleware - barcha xatoliklarni boshqarish
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, ErrorEvent
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError, TelegramNetworkError

logger = logging.getLogger(__name__)


class ErrorMiddleware(BaseMiddleware):
    """
    Error handling middleware - xatoliklarni boshqarish
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Middleware logika
        """
        try:
            return await handler(event, data)
        
        except TelegramBadRequest as e:
            # Telegram API xatosi (masalan, noto'g'ri parametrlar)
            logger.warning(f"Telegram Bad Request: {e}")
            # Foydalanuvchiga xabar bermaslik - bu bot xatosi
            return None
        
        except TelegramNetworkError as e:
            # Tarmoq xatosi
            logger.error(f"Telegram Network Error: {e}")
            # Qayta urinish mumkin, lekin hozircha xatolikni log qilamiz
            return None
        
        except TelegramAPIError as e:
            # Umumiy Telegram API xatosi
            logger.error(f"Telegram API Error: {e}")
            return None
        
        except Exception as e:
            # Boshqa xatoliklar
            logger.error(f"Unexpected error in handler: {e}", exc_info=True)
            
            # Foydalanuvchiga xabar berish (agar Message yoki CallbackQuery bo'lsa)
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring yoki keyinroq yuboring.",
                        parse_mode='HTML'
                    )
                except:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer("❌ Xatolik yuz berdi", show_alert=True)
                except:
                    pass
            
            return None

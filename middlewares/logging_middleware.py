"""
Logging middleware - barcha xabarlarni log qilish
"""

import logging
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Logging middleware - barcha update'larni log qilish
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
        start_time = time.time()
        
        # Update ma'lumotlari
        update: Update = data.get("event_update")
        if update:
            update_type = update.event_type
            user_id = None
            
            if update.message:
                user_id = update.message.from_user.id if update.message.from_user else None
            elif update.callback_query:
                user_id = update.callback_query.from_user.id if update.callback_query.from_user else None
            elif update.inline_query:
                user_id = update.inline_query.from_user.id if update.inline_query.from_user else None
            
            # Log qilish (faqat muhim update'lar)
            if update_type in ('message', 'callback_query'):
                logger.debug(f"Update qabul qilindi: {update_type}, user_id: {user_id}")
        
        try:
            # Handler'ni chaqirish
            result = await handler(event, data)
            
            # Vaqtni hisoblash
            duration = time.time() - start_time
            
            # Agar juda uzoq vaqt ketgan bo'lsa, warning
            if duration > 5.0:
                logger.warning(f"Handler uzoq vaqt ketdi: {duration:.2f}s, update_type: {update_type if update else 'unknown'}")
            
            return result
        
        except Exception as e:
            # Xatolikni log qilish
            duration = time.time() - start_time
            logger.error(f"Handler xatosi: {e}, duration: {duration:.2f}s")
            raise

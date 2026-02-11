"""
Superadmin filter - faqat superadminlar uchun
Database'dan role ustunidan tekshiradi
"""

from typing import Any
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from utils import get_user_by_telegram_id


class SuperAdminFilter(BaseFilter):
    """Superadmin filter - faqat superadminlar uchun (database'dan role ustunidan)"""
    
    async def __call__(self, obj: Message | CallbackQuery, *args: Any, **kwargs: Any) -> bool:
        """Filter tekshiruvi - database'dan role ustunidan"""
        user_id = obj.from_user.id if isinstance(obj, (Message, CallbackQuery)) else None
        
        if not user_id:
            return False
        
        # Database'dan superadmin tekshirish
        try:
            user = await get_user_by_telegram_id(user_id)
            if user and user.role == 'superadmin':
                return True
        except Exception:
            pass
        
        return False

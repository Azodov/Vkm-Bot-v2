"""
User filter - ro'yxatdan o'tgan foydalanuvchilar uchun
"""

from typing import Any
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from utils import get_user_by_telegram_id


class UserFilter(BaseFilter):
    """User filter - ma'lumotlar bazasida mavjud va faol foydalanuvchilar uchun"""
    
    async def __call__(self, obj: Message | CallbackQuery, *args: Any, **kwargs: Any) -> bool:
        """Filter tekshiruvi"""
        user_id = obj.from_user.id if isinstance(obj, (Message, CallbackQuery)) else None
        
        if not user_id:
            return False
        
        # Ma'lumotlar bazasidan foydalanuvchini tekshirish
        try:
            user = await get_user_by_telegram_id(user_id)
            if user and user.is_active:
                return True
        except Exception:
            # Xatolik bo'lsa, False qaytaradi
            pass
        
        return False

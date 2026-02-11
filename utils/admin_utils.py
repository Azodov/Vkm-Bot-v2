"""
Admin utility funksiyalari
Database'dan role ustunidan tekshiradi
"""

from .user_utils import get_user_by_telegram_id


async def check_is_superadmin(user_id: int) -> bool:
    """
    Foydalanuvchi superadmin ekanligini tekshirish (database'dan role ustunidan)
    
    Args:
        user_id: Foydalanuvchi Telegram ID
    
    Returns:
        True agar superadmin bo'lsa, False aks holda
    """
    # Database'dan superadmin tekshirish
    try:
        db_user = await get_user_by_telegram_id(user_id)
        if db_user and db_user.role == 'superadmin':
            return True
    except Exception:
        pass
    
    return False

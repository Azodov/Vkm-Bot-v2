"""
Text utility funksiyalari
"""

import re
from typing import Optional


def escape_markdown(text: str) -> str:
    """
    Markdown belgilarini escape qilish
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def format_user_info(user) -> str:
    """
    Foydalanuvchi ma'lumotlarini formatlash
    """
    username = user.username or "Yo'q"
    full_name = user.full_name or "Noma'lum"
    
    return (
        f"👤 Foydalanuvchi ma'lumotlari:\n"
        f"🆔 ID: {user.id}\n"
        f"📛 Ism: {full_name}\n"
        f"🔖 Username: @{username}\n"
    )


def format_number(number: int | float) -> str:
    """
    Raqamni formatlash (1000 -> 1,000)
    """
    return f"{number:,}".replace(",", " ")

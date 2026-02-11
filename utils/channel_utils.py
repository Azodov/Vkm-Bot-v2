"""
Majburiy obuna kanallari va guruhlari uchun utility funksiyalari
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import async_session_maker
from models import MandatoryChannel


async def add_mandatory_channel(
    channel_id: int,
    channel_username: str | None = None,
    channel_title: str | None = None,
    channel_type: str = "channel"
) -> MandatoryChannel | None:
    """
    Majburiy obuna kanalini yoki guruhini qo'shish
    
    Args:
        channel_id: Kanal yoki guruh ID (manfiy raqam)
        channel_username: Kanal username (@channel) yoki None
        channel_title: Kanal nomi yoki None
        channel_type: 'channel' yoki 'group'
    
    Returns:
        MandatoryChannel obyekti yoki None
    """
    if channel_type not in ('channel', 'group'):
        raise ValueError("channel_type faqat 'channel' yoki 'group' bo'lishi kerak")
    
    async with async_session_maker() as session:
        try:
            # Mavjud kanalni tekshirish
            result = await session.execute(
                select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Yangilash
                existing.channel_username = channel_username
                existing.channel_title = channel_title
                existing.channel_type = channel_type
                existing.is_active = True
                await session.commit()
                await session.refresh(existing)
                return existing
            else:
                # Yangi kanal qo'shish
                new_channel = MandatoryChannel(
                    channel_id=channel_id,
                    channel_username=channel_username,
                    channel_title=channel_title,
                    channel_type=channel_type,
                    is_active=True
                )
                session.add(new_channel)
                await session.commit()
                await session.refresh(new_channel)
                return new_channel
        except IntegrityError:
            await session.rollback()
            return None
        except Exception:
            await session.rollback()
            return None


async def remove_mandatory_channel(channel_id: int) -> bool:
    """
    Majburiy obuna kanalini yoki guruhini o'chirish
    
    Args:
        channel_id: Kanal yoki guruh ID
    
    Returns:
        True agar muvaffaqiyatli o'chirilgan bo'lsa, False aks holda
    """
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
            )
            channel = result.scalar_one_or_none()
            
            if channel:
                await session.delete(channel)
                await session.commit()
                return True
            return False
        except Exception:
            await session.rollback()
            return False


async def get_mandatory_channels(active_only: bool = True) -> list[MandatoryChannel]:
    """
    Barcha majburiy obuna kanallarini olish
    
    Args:
        active_only: Faqat faol kanallarni olish
    
    Returns:
        MandatoryChannel obyektlari ro'yxati
    """
    async with async_session_maker() as session:
        try:
            query = select(MandatoryChannel)
            if active_only:
                query = query.where(MandatoryChannel.is_active == True)
            
            result = await session.execute(query)
            return list(result.scalars().all())
        except Exception:
            return []


async def get_mandatory_channel(channel_id: int) -> MandatoryChannel | None:
    """
    Bitta majburiy obuna kanalini olish
    
    Args:
        channel_id: Kanal yoki guruh ID
    
    Returns:
        MandatoryChannel obyekti yoki None
    """
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None


async def check_user_subscription(bot, user_id: int, channel_id: int) -> bool:
    """
    Foydalanuvchi kanalga yoki guruhga obuna bo'lganligini tekshirish
    
    Args:
        bot: Bot obyekti
        user_id: Foydalanuvchi Telegram ID
        channel_id: Kanal yoki guruh ID
    
    Returns:
        True agar obuna bo'lsa, False aks holda
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        # Obuna bo'lishi kerak (member, administrator, yoki creator)
        return member.status in ('member', 'administrator', 'creator')
    except Exception:
        # Xatolik bo'lsa, obuna bo'lmagan deb hisoblaymiz
        return False


async def check_all_mandatory_subscriptions(bot, user_id: int) -> tuple[bool, list[MandatoryChannel]]:
    """
    Foydalanuvchi barcha majburiy kanallarga obuna bo'lganligini tekshirish
    
    Args:
        bot: Bot obyekti
        user_id: Foydalanuvchi Telegram ID
    
    Returns:
        (barcha_obuna, obuna_bo_lmagan_kanallar) tuple
    """
    channels = await get_mandatory_channels(active_only=True)
    
    if not channels:
        return (True, [])
    
    not_subscribed = []
    
    # Parallel tekshirish uchun asyncio.gather ishlatish mumkin
    # Lekin Telegram API rate limit tufayli ketma-ket qilamiz
    for channel in channels:
        is_subscribed = await check_user_subscription(bot, user_id, channel.channel_id)
        if not is_subscribed:
            not_subscribed.append(channel)
    
    return (len(not_subscribed) == 0, not_subscribed)


async def toggle_channel_status(channel_id: int) -> bool:
    """
    Kanalning faollik holatini o'zgartirish
    
    Args:
        channel_id: Kanal yoki guruh ID
    
    Returns:
        True agar muvaffaqiyatli yangilangan bo'lsa, False aks holda
    """
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
            )
            channel = result.scalar_one_or_none()
            
            if channel:
                channel.is_active = not channel.is_active
                await session.commit()
                await session.refresh(channel)
                return True
            return False
        except Exception:
            await session.rollback()
            return False


async def get_channel_invite_link(bot, channel_id: int) -> str | None:
    """
    Kanal yoki guruh uchun invite link olish
    
    Args:
        bot: Bot obyekti
        channel_id: Kanal yoki guruh ID
    
    Returns:
        Invite link yoki None (agar xatolik bo'lsa)
    """
    try:
        # Agar kanal username bo'lsa, oddiy link qaytarish
        chat = await bot.get_chat(channel_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
        
        # Username bo'lmasa, invite link yaratish
        invite_link = await bot.export_chat_invite_link(chat_id=channel_id)
        return invite_link
    except Exception as e:
        # Xatolik bo'lsa, None qaytarish
        # Logging ishlatish yaxshiroq bo'ladi
        return None


async def build_subscription_keyboard(bot, channels: list[MandatoryChannel]) -> tuple[str, list]:
    """
    Majburiy obuna kanallari uchun keyboard va matn yaratish
    
    Args:
        bot: Bot obyekti
        channels: Majburiy obuna kanallari ro'yxati
    
    Returns:
        (matn, keyboard_buttons) tuple
    """
    from aiogram.types import InlineKeyboardButton
    
    channels_text = ""
    keyboard_buttons = []
    
    for idx, channel in enumerate(channels, 1):
        channel_name = channel.channel_title or channel.channel_username or f"Kanal {idx}"
        
        # Matn uchun
        if channel.channel_username:
            channels_text += f"{idx}. @{channel.channel_username}\n"
        else:
            channels_text += f"{idx}. {channel_name}\n"
        
        # Keyboard uchun
        if channel.channel_username:
            invite_link = f"https://t.me/{channel.channel_username.lstrip('@')}"
        else:
            invite_link = await get_channel_invite_link(bot, channel.channel_id)
            if not invite_link:
                continue
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"📢 {channel_name} ga obuna bo'lish",
                url=invite_link
            )
        ])
    
    return channels_text, keyboard_buttons

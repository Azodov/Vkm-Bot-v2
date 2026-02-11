"""
Foydalanuvchi utility funksiyalari
Database bilan ishlash
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import async_session_maker
from models import User


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """
    Telegram ID bo'yicha foydalanuvchini topish
    
    Args:
        telegram_id: Foydalanuvchi Telegram ID
    
    Returns:
        User yoki None
    """
    async with async_session_maker() as session:
        # Telegram ID indexed bo'lgani uchun tez ishlaydi
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        return user


async def create_or_update_user(
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        is_active: bool = True,
        is_admin: bool = False,
        role: str | None = None,
) -> User:
    """
    Foydalanuvchini yaratish yoki yangilash
    
    Args:
        telegram_id: Foydalanuvchi Telegram ID
        username: Username (ixtiyoriy)
        first_name: Ism (ixtiyoriy)
        last_name: Familiya (ixtiyoriy)
        is_active: Faol holati (default: True)
        is_admin: Admin holati (default: False)
    
    Returns:
        User obyekti
    """
    async with async_session_maker() as session:
        try:
            # Mavjud foydalanuvchini topish
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Yangilash
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.is_active = is_active
                # Role'ni o'rnatish (agar berilgan bo'lsa)
                if role:
                    user.role = role
                    user.is_admin = (role in ('admin', 'superadmin'))
                elif not user.role:
                    user.role = 'user'  # Agar role yo'q bo'lsa
                elif is_admin and user.role == 'user':
                    # Agar is_admin True bo'lsa va role user bo'lsa, admin qilish
                    user.role = 'admin'
                    user.is_admin = True
                else:
                    user.is_admin = is_admin  # Backward compatibility
                await session.commit()
                await session.refresh(user)
                return user
            else:
                # Yangi foydalanuvchi yaratish
                default_role = role if role else 'user'
                new_user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=is_active,
                    is_admin=is_admin or (default_role in ('admin', 'superadmin')),
                    role=default_role,
                    media_preference='video_audio',  # Default: video + audio
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                return new_user
        except IntegrityError:
            await session.rollback()
            # Agar IntegrityError bo'lsa, qayta urinib ko'rish
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user:
                # Yangilash
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.is_active = is_active
                # Role'ni o'rnatish (agar berilgan bo'lsa)
                if role:
                    user.role = role
                    user.is_admin = (role in ('admin', 'superadmin'))
                elif not user.role:
                    user.role = 'user'
                await session.commit()
                await session.refresh(user)
                return user
            raise


async def get_all_users(limit: int = 100, offset: int = 0) -> list[User]:
    """
    Barcha foydalanuvchilarni olish
    
    Args:
        limit: Limit (default: 100)
        offset: Offset (default: 0)
    
    Returns:
        Foydalanuvchilar ro'yxati
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(User)
            .limit(limit)
            .offset(offset)
            .order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        return list(users)


async def get_active_users(limit: int = 100, offset: int = 0) -> list[User]:
    """
    Faol foydalanuvchilarni olish (optimallashtirilgan)
    
    Args:
        limit: Limit (default: 100)
        offset: Offset (default: 0)
    
    Returns:
        Faol foydalanuvchilar ro'yxati
    """
    async with async_session_maker() as session:
        # Faqat kerakli maydonlarni olish (optimallashtirish)
        result = await session.execute(
            select(User)
            .where(User.is_active == True)
            .limit(limit)
            .offset(offset)
            .order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        # List'ga o'girish kerak bo'lsa
        return list(users) if users else []


async def get_users_count() -> int:
    """
    Jami foydalanuvchilar soni
    
    Returns:
        Foydalanuvchilar soni
    """
    from sqlalchemy import func
    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count(User.id))
        )
        count = result.scalar()
        return count or 0


async def get_active_users_count() -> int:
    """
    Faol foydalanuvchilar soni
    
    Returns:
        Faol foydalanuvchilar soni
    """
    from sqlalchemy import func
    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        count = result.scalar()
        return count or 0


async def set_user_role(telegram_id: int, role: str) -> User | None:
    """
    Foydalanuvchi rolini o'zgartirish
    
    Args:
        telegram_id: Foydalanuvchi Telegram ID
        role: Yangi role ('superadmin', 'admin', 'user', 'guest')
    
    Returns:
        User obyekti yoki None
    """
    if role not in ('superadmin', 'admin', 'user', 'guest'):
        raise ValueError(f"Noto'g'ri role: {role}")

    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        user.role = role
        user.is_admin = (role in ('admin', 'superadmin'))  # Backward compatibility
        await session.commit()
        await session.refresh(user)
        return user


async def add_admin(telegram_id: int) -> User | None:
    """
    Foydalanuvchini admin qilish
    
    Args:
        telegram_id: Foydalanuvchi Telegram ID
    
    Returns:
        User obyekti yoki None
    """
    return await set_user_role(telegram_id, 'admin')


async def remove_admin(telegram_id: int) -> User | None:
    """
    Foydalanuvchidan admin huquqini olib tashlash
    
    Args:
        telegram_id: Foydalanuvchi Telegram ID
    
    Returns:
        User obyekti yoki None
    """
    return await set_user_role(telegram_id, 'user')


async def get_admins() -> list[User]:
    """
    Barcha adminlarni olish (superadminlarsiz)
    
    Returns:
        Adminlar ro'yxati
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.role == 'admin')
        )
        users = result.scalars().all()
        return list(users)


async def update_user_media_preference(telegram_id: int, preference: str) -> User | None:
    """
    Foydalanuvchi media preference'ini yangilash
    
    Args:
        telegram_id: Foydalanuvchi Telegram ID
        preference: Media preference ('video_audio', 'video_only', 'audio_only')
    
    Returns:
        User obyekti yoki None
    """
    if preference not in ('video_audio', 'video_only', 'audio_only'):
        raise ValueError(f"Noto'g'ri preference: {preference}")
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.media_preference = preference
        await session.commit()
        await session.refresh(user)
        return user

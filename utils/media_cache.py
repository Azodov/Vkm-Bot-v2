"""
Media cache utility - link va file_id mapping
Memory cache va database cache kombinatsiyasi
"""

import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import async_session_maker
from models import MediaLink
from utils.memory_cache import media_cache

logger = logging.getLogger(__name__)


async def get_cached_media(url: str) -> Optional[MediaLink]:
    """
    Cache'dan media olish - memory cache va database cache kombinatsiyasi
    
    Args:
        url: Media URL
    
    Returns:
        MediaLink obyekti yoki None
    """
    # 1. Memory cache'dan tekshirish (tez)
    cached = await media_cache.get(url)
    if cached:
        logger.debug(f"Memory cache'dan topildi: {url}")
        return cached
    
    # 2. Database'dan olish
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(MediaLink).where(MediaLink.url == url)
            )
            media = result.scalar_one_or_none()
            
            if media:
                # Access count oshirish (optimizatsiya: faqat commit, refresh kerak emas)
                media.access_count += 1
                await session.commit()
                
                # Memory cache'ga saqlash (keyingi marta tezroq)
                await media_cache.set(url, media, ttl_seconds=7200)
            
            return media
        except Exception as e:
            logger.error(f"Cache'dan media olishda xatolik: {e}")
            return None


async def save_media_cache(
    url: str,
    platform: str,
    file_id: str,
    file_type: str,
    file_unique_id: Optional[str] = None,
    title: Optional[str] = None,
    thumbnail_file_id: Optional[str] = None,
    file_size: Optional[int] = None,
    duration: Optional[int] = None,
) -> Optional[MediaLink]:
    """
    Media'ni cache'ga saqlash
    
    Args:
        url: Media URL
        platform: Platform nomi
        file_id: Telegram file_id
        file_type: Fayl turi (video, photo, audio, document)
        file_unique_id: Telegram file_unique_id
        title: Media sarlavhasi
        thumbnail_file_id: Thumbnail file_id
        file_size: Fayl hajmi (bytes)
        duration: Davomiyligi (sekund)
    
    Returns:
        MediaLink obyekti yoki None
    """
    async with async_session_maker() as session:
        try:
            # Mavjud media'ni tekshirish
            result = await session.execute(
                select(MediaLink).where(MediaLink.url == url)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Yangilash
                existing.file_id = file_id
                existing.file_type = file_type
                existing.file_unique_id = file_unique_id
                existing.title = title
                existing.thumbnail_file_id = thumbnail_file_id
                existing.file_size = file_size
                existing.duration = duration
                await session.commit()
                await session.refresh(existing)
                
                # Memory cache'ni yangilash
                await media_cache.set(url, existing, ttl_seconds=7200)
                
                return existing
            else:
                # Yangi media qo'shish
                new_media = MediaLink(
                    url=url,
                    platform=platform,
                    file_id=file_id,
                    file_type=file_type,
                    file_unique_id=file_unique_id,
                    title=title,
                    thumbnail_file_id=thumbnail_file_id,
                    file_size=file_size,
                    duration=duration,
                    access_count=1,
                )
                session.add(new_media)
                await session.commit()
                await session.refresh(new_media)
                
                # Memory cache'ga saqlash
                await media_cache.set(url, new_media, ttl_seconds=7200)
                
                return new_media
        except IntegrityError:
            await session.rollback()
            # Agar unique constraint xatosi bo'lsa, qayta urinib ko'rish
            return await get_cached_media(url)
        except Exception as e:
            await session.rollback()
            logger.error(f"Media cache'ga saqlashda xatolik: {e}")
            return None

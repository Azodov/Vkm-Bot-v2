"""
Media handlerlari - YouTube, Instagram, TikTok va boshqa platformalardan media yuklab berish
"""

import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Dict
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from utils.media_downloader import detect_platform, is_valid_url, download_media, cleanup_temp_files
from utils.media_cache import get_cached_media, save_media_cache
from utils.shazam_recognizer import recognize_music_from_voice
from utils.user_utils import get_user_by_telegram_id

logger = logging.getLogger(__name__)

router = Router(name="media")


def format_duration(seconds: int) -> str:
    """
    Duration'ni formatlash (MM:SS yoki HH:MM:SS)
    """
    if not seconds:
        return ""
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_media_caption(title: str, platform: str, duration: int = None, file_size: int = None) -> str:
    """
    Media caption formatlash
    """
    caption_parts = []
    
    # Sarlavha
    if title:
        caption_parts.append(f"📝 {title}")
    
    # Platform
    platform_names = {
        'youtube': 'YouTube',
        'instagram': 'Instagram',
        'tiktok': 'TikTok',
        'twitter': 'Twitter/X',
        'facebook': 'Facebook',
    }
    platform_name = platform_names.get(platform, platform.capitalize())
    caption_parts.append(f"🌐 {platform_name}")
    
    # Duration (video/audio uchun)
    if duration:
        duration_str = format_duration(duration)
        if duration_str:
            caption_parts.append(f"⏱️ {duration_str}")
    
    # File size (agar mavjud bo'lsa)
    if file_size:
        size_mb = file_size / (1024 * 1024)
        if size_mb >= 1:
            caption_parts.append(f"💾 {size_mb:.2f} MB")
        else:
            size_kb = file_size / 1024
            caption_parts.append(f"💾 {size_kb:.2f} KB")
    
    return "\n".join(caption_parts) if caption_parts else "Media"


# Bot ma'lumotlari cache (memory'da saqlash)
_bot_info_cache = None
_bot_info_cache_time = None

async def get_bot_link_keyboard(bot) -> InlineKeyboardMarkup:
    """
    Botga ulanish tugmasi yaratish (bot nomi bilan)
    Cache ishlatiladi - har safar API'ga so'rov yuborilmaydi
    """
    global _bot_info_cache, _bot_info_cache_time
    
    # Cache tekshirish (5 daqiqa)
    from datetime import datetime, timedelta
    if _bot_info_cache and _bot_info_cache_time:
        if datetime.now() - _bot_info_cache_time < timedelta(minutes=5):
            # Cache'dan olish
            bot_url, bot_name = _bot_info_cache
        else:
            # Cache eskirgan
            bot_url, bot_name = None, None
    else:
        bot_url, bot_name = None, None
    
    # Agar cache'da yo'q bo'lsa, API'dan olish
    if not bot_url:
        try:
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            bot_name = bot_info.first_name or bot_info.username or "Bot"
            bot_url = f"https://t.me/{bot_username}" if bot_username else None
            
            # Cache'ga saqlash
            _bot_info_cache = (bot_url, bot_name)
            _bot_info_cache_time = datetime.now()
        except Exception as e:
            logger.error(f"Bot ma'lumotlarini olishda xatolik: {e}")
            bot_url = None
            bot_name = "Bot"
    
    if bot_url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🤖 {bot_name}", url=bot_url)]
        ])
    else:
        keyboard = None
    
    return keyboard


@router.message(F.video_note)
async def handle_video_note(message: Message):
    """
    Video note (video message) ni qayta ishlash - Shazam orqali musiqani aniqlash
    """
    if not message.video_note:
        return
    
    logger.info(f"Video note qabul qilindi: {message.video_note.file_id}")
    
    # Loading xabari
    loading_msg = await message.answer("🎵 Musiqa aniqlanmoqda...\n\n⏳ Shazam orqali tahlil qilinmoqda...")
    
    try:
        # Video note faylni yuklab olish
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n📥 Video note yuklanmoqda...")
        
        bot = message.bot
        video_file = await bot.get_file(message.video_note.file_id)
        
        # Temporary fayl yaratish
        temp_dir = tempfile.mkdtemp()
        video_path = Path(temp_dir) / f"video_{message.video_note.file_id}.mp4"
        
        # Video note faylni yuklab olish
        try:
            await bot.download_file(video_file.file_path, str(video_path))
            
            # Fayl mavjudligini tekshirish
            if not video_path.exists():
                raise FileNotFoundError(f"Video note fayl yuklanmadi: {video_path}")
            
            logger.info(f"Video note yuklandi: {video_path}, hajmi: {video_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Video note yuklab olishda xatolik: {e}")
            await loading_msg.edit_text(
                f"❌ Video note yuklab olinmadi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
            # Temporary directory'ni tozalash
            try:
                if video_path.exists():
                    video_path.unlink()
                Path(temp_dir).rmdir()
            except:
                pass
            return
        
        # Shazam orqali musiqani aniqlash
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n🔍 Shazam orqali tahlil qilinmoqda...")
        
        try:
            music_info = await recognize_music_from_voice(str(video_path))
        except Exception as e:
            logger.error(f"Musiqa aniqlashda xatolik: {e}")
            music_info = None
        finally:
            # Temporary faylni o'chirish
            try:
                if video_path.exists():
                    video_path.unlink()
                Path(temp_dir).rmdir()
            except Exception as e:
                logger.warning(f"Temporary fayllarni o'chirishda xatolik: {e}")
        
        if not music_info:
            await loading_msg.edit_text(
                "❌ Musiqa aniqlanmadi.\n\n"
                "Iltimos, yana bir bor urinib ko'ring yoki boshqa video note yuboring."
            )
            return
        
        # Musiqa ma'lumotlarini ko'rsatish
        title = music_info.get('title', 'Noma\'lum')
        artist = music_info.get('artist', 'Noma\'lum artist')
        youtube_url = music_info.get('youtube_url')
        
        info_text = (
            f"🎵 Musiqa aniqlandi!\n\n"
            f"🎤 Artist: {artist}\n"
            f"🎵 Qo'shiq: {title}\n"
        )
        
        if music_info.get('album'):
            info_text += f"💿 Albom: {music_info['album']}\n"
        
        if youtube_url:
            info_text += f"\n📺 YouTube video topildi!"
            
            # YouTube video yuklab olish
            await loading_msg.edit_text(f"{info_text}\n\n⏳ Video yuklanmoqda...")
            
            # YouTube video yuklab olish va yuborish
            platform = detect_platform(youtube_url)
            if platform:
                await download_and_send_media(message, youtube_url, platform, loading_msg)
            else:
                await loading_msg.edit_text(
                    f"{info_text}\n\n"
                    f"🔗 Link: {youtube_url}\n\n"
                    f"❌ Video avtomatik yuklab olinmadi. Linkni yuboring."
                )
        else:
            # YouTube URL topilmadi
            search_query = music_info.get('search_query', f"{artist} {title}")
            await loading_msg.edit_text(
                f"{info_text}\n\n"
                f"❌ YouTube'da video topilmadi.\n\n"
                f"🔍 Qidiruv: {search_query}\n\n"
                f"Linkni qo'lda yuborishingiz mumkin."
            )
    
    except Exception as e:
        logger.error(f"Video note qayta ishlashda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            pass


@router.message(F.voice)
async def handle_voice_message(message: Message):
    """
    Voice message'ni qayta ishlash - Shazam orqali musiqani aniqlash
    """
    if not message.voice:
        return
    
    logger.info(f"Voice message qabul qilindi: {message.voice.file_id}")
    
    # Loading xabari
    loading_msg = await message.answer("🎵 Musiqa aniqlanmoqda...\n\n⏳ Shazam orqali tahlil qilinmoqda...")
    
    try:
        # Voice faylni yuklab olish
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n📥 Voice fayl yuklanmoqda...")
        
        bot = message.bot
        voice_file = await bot.get_file(message.voice.file_id)
        
        # Temporary fayl yaratish
        temp_dir = tempfile.mkdtemp()
        voice_path = Path(temp_dir) / f"voice_{message.voice.file_id}.ogg"
        
        # Voice faylni yuklab olish
        try:
            await bot.download_file(voice_file.file_path, str(voice_path))
            
            # Fayl mavjudligini tekshirish
            if not voice_path.exists():
                raise FileNotFoundError(f"Voice fayl yuklanmadi: {voice_path}")
            
            logger.info(f"Voice fayl yuklandi: {voice_path}, hajmi: {voice_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Voice fayl yuklab olishda xatolik: {e}")
            await loading_msg.edit_text(
                f"❌ Voice fayl yuklab olinmadi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
            # Temporary directory'ni tozalash
            try:
                if voice_path.exists():
                    voice_path.unlink()
                Path(temp_dir).rmdir()
            except:
                pass
            return
        
        # Shazam orqali musiqani aniqlash
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n🔍 Shazam orqali tahlil qilinmoqda...")
        
        try:
            music_info = await recognize_music_from_voice(str(voice_path))
        except Exception as e:
            logger.error(f"Musiqa aniqlashda xatolik: {e}")
            music_info = None
        finally:
            # Temporary faylni o'chirish
            try:
                if voice_path.exists():
                    voice_path.unlink()
                Path(temp_dir).rmdir()
            except Exception as e:
                logger.warning(f"Temporary fayllarni o'chirishda xatolik: {e}")
        
        if not music_info:
            await loading_msg.edit_text(
                "❌ Musiqa aniqlanmadi.\n\n"
                "Iltimos, yana bir bor urinib ko'ring yoki boshqa voice message yuboring."
            )
            return
        
        # Musiqa ma'lumotlarini ko'rsatish
        title = music_info.get('title', 'Noma\'lum')
        artist = music_info.get('artist', 'Noma\'lum artist')
        youtube_url = music_info.get('youtube_url')
        
        info_text = (
            f"🎵 Musiqa aniqlandi!\n\n"
            f"🎤 Artist: {artist}\n"
            f"🎵 Qo'shiq: {title}\n"
        )
        
        if music_info.get('album'):
            info_text += f"💿 Albom: {music_info['album']}\n"
        
        if youtube_url:
            info_text += f"\n📺 YouTube video topildi!"
            
            # YouTube video yuklab olish
            await loading_msg.edit_text(f"{info_text}\n\n⏳ Video yuklanmoqda...")
            
            # YouTube video yuklab olish va yuborish
            platform = detect_platform(youtube_url)
            if platform:
                await download_and_send_media(message, youtube_url, platform, loading_msg)
            else:
                await loading_msg.edit_text(
                    f"{info_text}\n\n"
                    f"🔗 Link: {youtube_url}\n\n"
                    f"❌ Video avtomatik yuklab olinmadi. Linkni yuboring."
                )
        else:
            # YouTube URL topilmadi
            search_query = music_info.get('search_query', f"{artist} {title}")
            await loading_msg.edit_text(
                f"{info_text}\n\n"
                f"❌ YouTube'da video topilmadi.\n\n"
                f"🔍 Qidiruv: {search_query}\n\n"
                f"Linkni qo'lda yuborishingiz mumkin."
            )
    
    except Exception as e:
        logger.error(f"Voice message qayta ishlashda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            pass


# Pagination uchun - har bir foydalanuvchi uchun qidiruv natijalari
# Search results cache - memory cache ishlatiladi (utils/memory_cache.py)
from utils.memory_cache import search_cache


def format_video_info(video: Dict, index: int) -> str:
    """
    Video ma'lumotlarini formatlash
    """
    title = video.get('title', 'Noma\'lum')[:50]  # 50 belgidan ko'p bo'lmasin
    duration = video.get('duration', 0)
    view_count = video.get('view_count', 0)
    
    info = f"{index}. {title}"
    
    if duration:
        # format_duration allaqachon bu faylda mavjud
        duration_str = format_duration(duration)
        if duration_str:
            info += f" ({duration_str})"
    
    return info


def create_search_keyboard(videos: list[Dict], page: int = 0, search_query: str = "", user_id: int = 0) -> InlineKeyboardMarkup:
    """
    Qidiruv natijalari uchun keyboard yaratish (pagination bilan)
    """
    from aiogram.types import InlineKeyboardButton
    
    VIDEOS_PER_PAGE = 5  # Har bir sahifada 5 ta video
    total_pages = (len(videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE
    
    # Joriy sahifa videolarini olish
    start_idx = page * VIDEOS_PER_PAGE
    end_idx = min(start_idx + VIDEOS_PER_PAGE, len(videos))
    page_videos = videos[start_idx:end_idx]
    
    keyboard_buttons = []
    
    # Video tugmalari
    for idx, video in enumerate(page_videos):
        video_index = start_idx + idx + 1
        video_title = video.get('title', 'Noma\'lum')[:40]  # 40 belgidan ko'p bo'lmasin
        callback_data = f"select_video:{video.get('id')}:{user_id}"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"▶️ {video_index}. {video_title}",
                callback_data=callback_data
            )
        ])
    
    # Pagination tugmalari
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Oldingi",
            callback_data=f"search_page:{page-1}:{user_id}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Keyingi ▶️",
            callback_data=f"search_page:{page+1}:{user_id}"
        ))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


@router.message(F.text & ~F.text.startswith('http://') & ~F.text.startswith('https://') & ~F.text.startswith('/'))
async def handle_music_search(message: Message):
    """
    Text message'dan qo'shiq nomi yoki ijrochi ismini qidirish (YouTube) - pagination bilan
    """
    if not message.text:
        return
    
    search_query = message.text.strip()
    
    # Qisqa xabarlarni e'tiborsiz qoldirish (masalan, faqat "salom")
    if len(search_query) < 3:
        return
    
    logger.info(f"Musiqa qidiruv so'rovi qabul qilindi: {search_query}")
    
    # Loading xabari
    loading_msg = await message.answer(f"🔍 Qidirilmoqda: {search_query}\n\n⏳ YouTube'dan qidirilmoqda...")
    
    try:
        # YouTube'dan qidirish (bir nechta natija)
        from utils.shazam_recognizer import search_youtube_videos
        
        videos = await search_youtube_videos(search_query, max_results=10)
        
        if not videos:
            # Video topilmadi
            await loading_msg.edit_text(
                f"❌ '{search_query}' uchun video topilmadi.\n\n"
                "Iltimos, boshqa qidiruv so'rovi yuboring yoki to'g'ridan-to'g'ri YouTube link yuboring."
            )
            return
        
        # Natijalarni cache'ga saqlash (memory cache)
        user_id = message.from_user.id
        cache_key = f"search:{user_id}"
        await search_cache.set(cache_key, {
            'videos': videos,
            'search_query': search_query,
        }, ttl_seconds=1800)  # 30 daqiqa
        
        # Birinchi sahifani ko'rsatish
        page = 0
        keyboard = create_search_keyboard(videos, page=page, search_query=search_query, user_id=user_id)
        
        result_text = (
            f"🔍 Qidiruv natijalari: <b>{search_query}</b>\n\n"
            f"📊 Topildi: {len(videos)} ta video\n\n"
            f"Quyidagilardan birini tanlang:"
        )
        
        await loading_msg.edit_text(result_text, reply_markup=keyboard, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Musiqa qidiruvda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            pass


@router.callback_query(F.data.startswith('search_page:'))
async def handle_search_pagination(callback: CallbackQuery):
    """
    Qidiruv natijalari pagination
    """
    await callback.answer()
    
    try:
        # Callback data format: search_page:page:user_id
        parts = callback.data.split(':')
        if len(parts) < 3:
            return
        
        page = int(parts[1])
        user_id = int(parts[2])
        
        # Cache'dan natijalarni olish (memory cache)
        cache_key = f"search:{user_id}"
        cache_data = await search_cache.get(cache_key)
        if not cache_data:
            await callback.answer("❌ Qidiruv natijalari topilmadi. Qayta qidiring.", show_alert=True)
            return
        
        videos = cache_data['videos']
        search_query = cache_data.get('search_query', '')
        
        # Keyboard yaratish
        keyboard = create_search_keyboard(videos, page=page, search_query=search_query, user_id=user_id)
        
        result_text = (
            f"🔍 Qidiruv natijalari: <b>{search_query}</b>\n\n"
            f"📊 Topildi: {len(videos)} ta video\n\n"
            f"Quyidagilardan birini tanlang:"
        )
        
        try:
            await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode='HTML')
        except TelegramBadRequest:
            await callback.message.answer(result_text, reply_markup=keyboard, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Pagination xatosi: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data.startswith('select_video:'))
async def handle_video_selection(callback: CallbackQuery):
    """
    Foydalanuvchi tanlagan videoni yuklab olish va yuborish
    """
    await callback.answer("⏳ Video yuklanmoqda...")
    
    try:
        # Callback data format: select_video:video_id:user_id
        parts = callback.data.split(':')
        if len(parts) < 3:
            return
        
        video_id = parts[1]
        user_id = int(parts[2])
        
        # Cache'dan natijalarni olish (memory cache)
        cache_key = f"search:{user_id}"
        cache_data = await search_cache.get(cache_key)
        if not cache_data:
            await callback.answer("❌ Qidiruv natijalari topilmadi. Qayta qidiring.", show_alert=True)
            return
        
        videos = cache_data['videos']
        
        # Video'ni topish
        selected_video = None
        for video in videos:
            if video.get('id') == video_id:
                selected_video = video
                break
        
        if not selected_video:
            await callback.answer("❌ Video topilmadi", show_alert=True)
            return
        
        video_url = selected_video['url']
        
        # Cache'dan tekshirish - agar avval yuklangan bo'lsa, cache'dan yuborish
        cached_media = await get_cached_media(video_url)
        
        if cached_media:
            # Cache'dan topildi - file_id bilan jo'natish
            logger.info(f"Cache'dan topildi: {video_url}")
            await callback.answer("✅ Cache'dan yuborilmoqda...")
            
            try:
                await send_cached_media(callback.message, cached_media)
                return
            except Exception as e:
                logger.error(f"Cached media yuborishda xatolik: {e}")
                # Agar cached media ishlamasa, qayta yuklab olish
                pass
        
        # Loading xabari
        loading_msg = await callback.message.answer(f"⏳ Video yuklanmoqda...\n\n📥 {selected_video.get('title', 'Video')}")
        
        # Video yuklab olish va yuborish
        platform = detect_platform(video_url)
        if platform:
            await download_and_send_media(callback.message, video_url, platform, loading_msg)
        else:
            await loading_msg.edit_text(
                f"❌ Video avtomatik yuklab olinmadi.\n\n"
                f"🔗 Link: {video_url}"
            )
    
    except Exception as e:
        logger.error(f"Video tanlashda xatolik: {e}")
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


@router.message(F.video)
async def handle_video_file(message: Message):
    """
    Video file'dan musiqani aniqlash (Shazam orqali)
    """
    if not message.video:
        return
    
    logger.info(f"Video file qabul qilindi: {message.video.file_id}")
    
    # Loading xabari
    loading_msg = await message.answer("🎵 Musiqa aniqlanmoqda...\n\n⏳ Shazam orqali tahlil qilinmoqda...")
    
    try:
        # Video faylni yuklab olish
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n📥 Video fayl yuklanmoqda...")
        
        bot = message.bot
        video_file = await bot.get_file(message.video.file_id)
        
        # Temporary fayl yaratish
        temp_dir = tempfile.mkdtemp()
        video_path = Path(temp_dir) / f"video_{message.video.file_id}.mp4"
        
        # Video faylni yuklab olish
        try:
            await bot.download_file(video_file.file_path, str(video_path))
            
            # Fayl mavjudligini tekshirish
            if not video_path.exists():
                raise FileNotFoundError(f"Video fayl yuklanmadi: {video_path}")
            
            logger.info(f"Video fayl yuklandi: {video_path}, hajmi: {video_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Video fayl yuklab olishda xatolik: {e}")
            await loading_msg.edit_text(
                f"❌ Video fayl yuklab olinmadi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
            # Temporary directory'ni tozalash
            try:
                if video_path.exists():
                    video_path.unlink()
                Path(temp_dir).rmdir()
            except:
                pass
            return
        
        # Shazam orqali musiqani aniqlash
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n🔍 Shazam orqali tahlil qilinmoqda...")
        
        try:
            music_info = await recognize_music_from_voice(str(video_path))
        except Exception as e:
            logger.error(f"Musiqa aniqlashda xatolik: {e}")
            music_info = None
        finally:
            # Temporary faylni o'chirish
            try:
                if video_path.exists():
                    video_path.unlink()
                Path(temp_dir).rmdir()
            except Exception as e:
                logger.warning(f"Temporary fayllarni o'chirishda xatolik: {e}")
        
        if not music_info:
            await loading_msg.edit_text(
                "❌ Musiqa aniqlanmadi.\n\n"
                "Iltimos, yana bir bor urinib ko'ring yoki boshqa video yuboring."
            )
            return
        
        # Musiqa ma'lumotlarini ko'rsatish va YouTube'dan yuklab olish
        title = music_info.get('title', 'Noma\'lum')
        artist = music_info.get('artist', 'Noma\'lum artist')
        youtube_url = music_info.get('youtube_url')
        
        info_text = (
            f"🎵 Musiqa aniqlandi!\n\n"
            f"🎤 Artist: {artist}\n"
            f"🎵 Qo'shiq: {title}\n"
        )
        
        if music_info.get('album'):
            info_text += f"💿 Albom: {music_info['album']}\n"
        
        if youtube_url:
            info_text += f"\n📺 YouTube video topildi!"
            
            # YouTube video yuklab olish
            await loading_msg.edit_text(f"{info_text}\n\n⏳ Video yuklanmoqda...")
            
            # YouTube video yuklab olish va yuborish
            platform = detect_platform(youtube_url)
            if platform:
                await download_and_send_media(message, youtube_url, platform, loading_msg)
            else:
                await loading_msg.edit_text(
                    f"{info_text}\n\n"
                    f"🔗 Link: {youtube_url}\n\n"
                    f"❌ Video avtomatik yuklab olinmadi. Linkni yuboring."
                )
        else:
            # YouTube URL topilmadi
            search_query = music_info.get('search_query', f"{artist} {title}")
            await loading_msg.edit_text(
                f"{info_text}\n\n"
                f"❌ YouTube'da video topilmadi.\n\n"
                f"🔍 Qidiruv: {search_query}\n\n"
                f"Linkni qo'lda yuborishingiz mumkin."
            )
    
    except Exception as e:
        logger.error(f"Video file qayta ishlashda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            pass


@router.message(F.audio)
async def handle_audio_file(message: Message):
    """
    Audio file'dan musiqani aniqlash (Shazam orqali)
    """
    if not message.audio:
        return
    
    logger.info(f"Audio file qabul qilindi: {message.audio.file_id}")
    
    # Loading xabari
    loading_msg = await message.answer("🎵 Musiqa aniqlanmoqda...\n\n⏳ Shazam orqali tahlil qilinmoqda...")
    
    try:
        # Audio faylni yuklab olish
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n📥 Audio fayl yuklanmoqda...")
        
        bot = message.bot
        audio_file = await bot.get_file(message.audio.file_id)
        
        # Temporary fayl yaratish
        temp_dir = tempfile.mkdtemp()
        # Audio fayl extension'ini aniqlash
        audio_ext = message.audio.mime_type.split('/')[-1] if message.audio.mime_type else 'mp3'
        audio_path = Path(temp_dir) / f"audio_{message.audio.file_id}.{audio_ext}"
        
        # Audio faylni yuklab olish
        try:
            await bot.download_file(audio_file.file_path, str(audio_path))
            
            # Fayl mavjudligini tekshirish
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio fayl yuklanmadi: {audio_path}")
            
            logger.info(f"Audio fayl yuklandi: {audio_path}, hajmi: {audio_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Audio fayl yuklab olishda xatolik: {e}")
            await loading_msg.edit_text(
                f"❌ Audio fayl yuklab olinmadi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
            # Temporary directory'ni tozalash
            try:
                if audio_path.exists():
                    audio_path.unlink()
                Path(temp_dir).rmdir()
            except:
                pass
            return
        
        # FFmpeg mavjudligini tekshirish (ShazamIO uchun kerak)
        import shutil
        import subprocess
        import os
        
        ffmpeg_available = False
        ffmpeg_path = None
        
        # 1. PATH'dan qidirish
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            ffmpeg_available = True
            logger.info(f"FFmpeg topildi (PATH): {ffmpeg_path}")
        else:
            # 2. To'g'ridan-to'g'ri tekshirish
            try:
                result = subprocess.run(
                    ['ffmpeg', '-version'],
                    capture_output=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    ffmpeg_available = True
                    logger.info("FFmpeg to'g'ridan-to'g'ri topildi")
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                logger.debug(f"FFmpeg topilmadi: {e}")
        
        if not ffmpeg_available:
            # FFmpeg yo'q bo'lsa, xabar berish
            await loading_msg.edit_text(
                "⚠️ FFmpeg o'rnatilmagan!\n\n"
                "Musiqa aniqlash uchun FFmpeg kerak.\n\n"
                "FFmpeg o'rnatish:\n"
                "• Windows: https://ffmpeg.org/download.html\n"
                "• Linux: sudo apt-get install ffmpeg\n"
                "• Mac: brew install ffmpeg"
            )
            # Temporary faylni o'chirish
            try:
                if audio_path.exists():
                    audio_path.unlink()
                Path(temp_dir).rmdir()
            except:
                pass
            return
        
        # Shazam orqali musiqani aniqlash
        await loading_msg.edit_text("🎵 Musiqa aniqlanmoqda...\n\n🔍 Shazam orqali tahlil qilinmoqda...")
        
        try:
            music_info = await recognize_music_from_voice(str(audio_path))
        except Exception as e:
            logger.error(f"Musiqa aniqlashda xatolik: {e}")
            music_info = None
        finally:
            # Temporary faylni o'chirish
            try:
                if audio_path.exists():
                    audio_path.unlink()
                Path(temp_dir).rmdir()
            except Exception as e:
                logger.warning(f"Temporary fayllarni o'chirishda xatolik: {e}")
        
        if not music_info:
            await loading_msg.edit_text(
                "❌ Musiqa aniqlanmadi.\n\n"
                "Iltimos, yana bir bor urinib ko'ring yoki boshqa audio yuboring."
            )
            return
        
        # Musiqa ma'lumotlarini ko'rsatish va YouTube'dan yuklab olish
        title = music_info.get('title', 'Noma\'lum')
        artist = music_info.get('artist', 'Noma\'lum artist')
        youtube_url = music_info.get('youtube_url')
        
        info_text = (
            f"🎵 Musiqa aniqlandi!\n\n"
            f"🎤 Artist: {artist}\n"
            f"🎵 Qo'shiq: {title}\n"
        )
        
        if music_info.get('album'):
            info_text += f"💿 Albom: {music_info['album']}\n"
        
        if youtube_url:
            info_text += f"\n📺 YouTube video topildi!"
            
            # YouTube video yuklab olish
            await loading_msg.edit_text(f"{info_text}\n\n⏳ Video yuklanmoqda...")
            
            # YouTube video yuklab olish va yuborish
            platform = detect_platform(youtube_url)
            if platform:
                await download_and_send_media(message, youtube_url, platform, loading_msg)
            else:
                await loading_msg.edit_text(
                    f"{info_text}\n\n"
                    f"🔗 Link: {youtube_url}\n\n"
                    f"❌ Video avtomatik yuklab olinmadi. Linkni yuboring."
                )
        else:
            # YouTube URL topilmadi
            search_query = music_info.get('search_query', f"{artist} {title}")
            await loading_msg.edit_text(
                f"{info_text}\n\n"
                f"❌ YouTube'da video topilmadi.\n\n"
                f"🔍 Qidiruv: {search_query}\n\n"
                f"Linkni qo'lda yuborishingiz mumkin."
            )
    
    except Exception as e:
        logger.error(f"Audio file qayta ishlashda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            pass


@router.message(F.text.startswith('http://') | F.text.startswith('https://'))
async def handle_media_link(message: Message):
    """
    Media link'ni qayta ishlash
    YouTube, Instagram, TikTok va boshqa platformalardan media yuklab berish
    """
    url = message.text.strip()
    
    logger.info(f"Media link qabul qilindi: {url}")
    
    if not is_valid_url(url):
        logger.warning(f"Noto'g'ri URL format: {url}")
        await message.answer("❌ Noto'g'ri URL format!")
        return
    
    # Platformani aniqlash
    platform = detect_platform(url)
    logger.info(f"Platform aniqlandi: {platform} (URL: {url})")
    
    if not platform:
        # Qo'llab-quvvatlanmaydigan platforma
        await message.answer(
            "❌ Bu platforma hozircha qo'llab-quvvatlanmaydi.\n\n"
            "Qo'llab-quvvatlanadigan platformalar:\n"
            "• YouTube\n"
            "• Instagram\n"
            "• TikTok\n"
            "• Twitter/X\n"
            "• Facebook"
        )
        return
    
    # Loading xabari
    loading_msg = await message.answer("⏳ Media yuklanmoqda...")
    
    try:
        # Cache'dan tekshirish
        cached_media = await get_cached_media(url)
        
        if cached_media:
            # Cache'dan topildi - file_id bilan jo'natish
            logger.info(f"Cache'dan topildi: {url}")
            await loading_msg.delete()
            
            try:
                await send_cached_media(message, cached_media)
                # Qo'shimcha xabar yuborilmaydi - faqat media
            except Exception as e:
                logger.error(f"Cached media yuborishda xatolik: {e}")
                # Agar cached media ishlamasa, qayta yuklab olish
                await download_and_send_media(message, url, platform, loading_msg)
        else:
            # Cache'da yo'q - yuklab olish
            await download_and_send_media(message, url, platform, loading_msg)
    
    except Exception as e:
        logger.error(f"Media link qayta ishlashda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            await message.answer(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )


async def download_and_send_media(message: Message, url: str, platform: str, loading_msg: Message):
    """
    Media'ni yuklab olish va yuborish
    """
    try:
        # Foydalanuvchi sozlamalarini olish
        user = await get_user_by_telegram_id(message.from_user.id)
        media_preference = user.media_preference if user else 'video_audio'  # Default: video_audio
        
        # Media yuklab olish
        await loading_msg.edit_text("⏳ Media yuklanmoqda...\n\n📥 Platformadan yuklab olinmoqda...")
        
        media_data = await download_media(url, platform)
        
        # Xatolik ma'lumotlarini tekshirish
        if not media_data or (isinstance(media_data, dict) and 'error_type' in media_data and 'file_path' not in media_data):
            # Xatolik bo'lganda
            error_type = None
            if isinstance(media_data, dict):
                error_type = media_data.get('error_type')
            
            logger.error(f"Media yuklab olinmadi: {url}, xatolik turi: {error_type}")
            
            # TikTok uchun maxsus xabar
            if platform == 'tiktok':
                error_details = ""
                
                if error_type == 'ip_blocked':
                    error_details = (
                        "⚠️ IP manzil bloklangan:\n"
                        "TikTok server IP manzilni vaqtinchalik bloklagan.\n\n"
                        "🔧 Yechimlar:\n"
                        "1. Bir necha daqiqadan keyin qayta urinib ko'ring\n"
                        "2. VPN yoki proxy ishlatishni tavsiya qilamiz\n"
                        "3. Boshqa TikTok linkini yuborib ko'ring\n\n"
                    )
                else:
                    error_details = (
                        "⚠️ Muammo sabablari:\n"
                        "• Link to'g'ri emas yoki video o'chirilgan\n"
                        "• Redirect muammosi\n"
                        "• TikTok server muammosi\n\n"
                        "🔧 Yechimlar:\n"
                        "1. Link to'g'ri ekanligini tekshiring\n"
                        "2. Video mavjudligini tekshiring\n"
                        "3. To'g'ri TikTok video linkini yuboring:\n"
                        "   • https://www.tiktok.com/@username/video/1234567890\n"
                        "   • https://vm.tiktok.com/ZSNYW7Dd2\n\n"
                    )
                
                await loading_msg.edit_text(
                    f"❌ TikTok video yuklab olinmadi.\n\n"
                    f"{error_details}"
                    f"💡 Maslahat: Ba'zi TikTok linklar redirect muammosi tufayli "
                    f"yuklab bo'lmaydi. To'liq video linkini yuborishni tavsiya qilamiz.\n\n"
                    f"🔄 Qayta urinib ko'ring yoki boshqa link yuboring."
                )
            else:
                # Boshqa platformalar uchun umumiy xabar
                await loading_msg.edit_text(
                    "❌ Media yuklab olinmadi.\n\n"
                    "Iltimos, link to'g'ri ekanligini tekshiring yoki qayta urinib ko'ring.\n\n"
                    "⚠️ Eslatma: yt-dlp kutubxonasi o'rnatilganligini tekshiring:\n"
                    "pip install yt-dlp"
                )
            return
        
        if not media_data:
            logger.error(f"Media yuklab olinmadi: {url}")
            
            # TikTok uchun maxsus xabar
            if platform == 'tiktok':
                error_details = (
                    "⚠️ Muammo sabablari:\n"
                    "• Link to'g'ri emas yoki video o'chirilgan\n"
                    "• Redirect muammosi\n"
                    "• TikTok server muammosi\n\n"
                    "🔧 Yechimlar:\n"
                    "1. Link to'g'ri ekanligini tekshiring\n"
                    "2. Video mavjudligini tekshiring\n"
                    "3. To'g'ri TikTok video linkini yuboring:\n"
                    "   • https://www.tiktok.com/@username/video/1234567890\n"
                    "   • https://vm.tiktok.com/ZSNYW7Dd2\n\n"
                )
                
                await loading_msg.edit_text(
                    f"❌ TikTok video yuklab olinmadi.\n\n"
                    f"{error_details}"
                    f"💡 Maslahat: Ba'zi TikTok linklar redirect muammosi tufayli "
                    f"yuklab bo'lmaydi. To'liq video linkini yuborishni tavsiya qilamiz.\n\n"
                    f"🔄 Qayta urinib ko'ring yoki boshqa link yuboring."
                )
                error_details = ""
                
                if error_type == 'ip_blocked':
                    error_details = (
                        "⚠️ IP manzil bloklangan:\n"
                        "TikTok server IP manzilni vaqtinchalik bloklagan.\n\n"
                        "🔧 Yechimlar:\n"
                        "1. Bir necha daqiqadan keyin qayta urinib ko'ring\n"
                        "2. VPN yoki proxy ishlatishni tavsiya qilamiz\n"
                        "3. Boshqa TikTok linkini yuborib ko'ring\n\n"
                    )
                else:
                    error_details = (
                        "⚠️ Muammo sabablari:\n"
                        "• Link to'g'ri emas yoki video o'chirilgan\n"
                        "• Redirect muammosi\n"
                        "• TikTok server muammosi\n\n"
                        "🔧 Yechimlar:\n"
                        "1. Link to'g'ri ekanligini tekshiring\n"
                        "2. Video mavjudligini tekshiring\n"
                        "3. To'g'ri TikTok video linkini yuboring:\n"
                        "   • https://www.tiktok.com/@username/video/1234567890\n"
                        "   • https://vm.tiktok.com/ZSNYW7Dd2\n\n"
                    )
                
                await loading_msg.edit_text(
                    f"❌ TikTok video yuklab olinmadi.\n\n"
                    f"{error_details}"
                    f"💡 Maslahat: Ba'zi TikTok linklar redirect muammosi tufayli "
                    f"yuklab bo'lmaydi. To'liq video linkini yuborishni tavsiya qilamiz.\n\n"
                    f"🔄 Qayta urinib ko'ring yoki boshqa link yuboring."
                )
            # Instagram story uchun maxsus xabar
            elif platform == 'instagram' and ('/stories/' in url or '/story/' in url):
                await loading_msg.edit_text(
                    "❌ Instagram Story yuklab olinmadi.\n\n"
                    "⚠️ Instagram Story'lar ba'zida yuklab olinmaydi:\n\n"
                    "🔧 Yechimlar:\n"
                    "1. Cookies'ni yangilang (yangi cookies oling)\n"
                    "2. Bir necha daqiqadan keyin qayta urinib ko'ring\n"
                    "3. Instagram Post yoki Reel linkini yuboring\n\n"
                    "💡 Maslahat: Instagram Story'lar qisqa muddatli kontent, "
                    "vaqti o'tgach yuklab bo'lmaydi.\n\n"
                    "📖 Cookies qo'shish: INSTAGRAM_COOKIES_GUIDE.md faylini ko'ring."
                )
            else:
                await loading_msg.edit_text(
                    "❌ Media yuklab olinmadi.\n\n"
                    "Iltimos, link to'g'ri ekanligini tekshiring yoki qayta urinib ko'ring.\n\n"
                    "⚠️ Eslatma: yt-dlp kutubxonasi o'rnatilganligini tekshiring:\n"
                    "pip install yt-dlp"
                )
            return
        
        # Media'ni Telegram'ga yuborish
        await loading_msg.edit_text("⏳ Media yuborilmoqda...")
        
        file_path = media_data['file_path']
        file = FSInputFile(file_path)
        
        # Fayl turini aniqlash
        file_ext = Path(file_path).suffix.lower()
        is_video = file_ext in ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')
        is_audio = file_ext in ('.mp3', '.m4a', '.ogg', '.wav', '.flac')
        
        sent_message = None
        
        try:
            # Duration'ni integer'ga aylantirish (Telegram API integer kutmoqda)
            duration = None
            if media_data.get('duration') is not None:
                duration = int(media_data['duration'])
            
            # Caption va keyboard yaratish
            caption = format_media_caption(
                title=media_data.get('title'),
                platform=platform,
                duration=duration,
                file_size=Path(file_path).stat().st_size if Path(file_path).exists() else None
            )
            keyboard = await get_bot_link_keyboard(message.bot)
            
            if is_video:
                # Foydalanuvchi sozlamalariga qarab video/audio yuborish
                if media_preference == 'video_only':
                    # Faqat video yuborish
                    if media_data.get('thumbnail_path'):
                        thumb = FSInputFile(media_data['thumbnail_path'])
                        sent_message = await message.answer_video(
                            video=file,
                            caption=caption,
                            thumbnail=thumb,
                            duration=duration,
                            reply_markup=keyboard,
                        )
                    else:
                        sent_message = await message.answer_video(
                            video=file,
                            caption=caption,
                            duration=duration,
                            reply_markup=keyboard,
                        )
                    
                elif media_preference == 'audio_only':
                    # Faqat audio yuborish (agar audio_path mavjud bo'lsa)
                    if media_data.get('audio_path'):
                        try:
                            await loading_msg.edit_text("⏳ Audio yuborilmoqda...")
                            
                            audio_file = FSInputFile(media_data['audio_path'])
                            audio_caption = format_media_caption(
                                title=media_data.get('title'),
                                platform=platform,
                                duration=duration,
                                file_size=Path(media_data['audio_path']).stat().st_size if Path(media_data['audio_path']).exists() else None
                            )
                            
                            sent_message = await message.answer_audio(
                                audio=audio_file,
                                caption=audio_caption,
                                duration=duration,
                                reply_markup=keyboard,
                            )
                            logger.info(f"Audio yuborildi: {media_data.get('title')}")
                        except Exception as e:
                            logger.error(f"Audio yuborishda xatolik: {e}")
                            # Audio yuborishda xatolik bo'lsa, video yuborish
                            if media_data.get('thumbnail_path'):
                                thumb = FSInputFile(media_data['thumbnail_path'])
                                sent_message = await message.answer_video(
                                    video=file,
                                    caption=caption,
                                    thumbnail=thumb,
                                    duration=duration,
                                    reply_markup=keyboard,
                                )
                            else:
                                sent_message = await message.answer_video(
                                    video=file,
                                    caption=caption,
                                    duration=duration,
                                    reply_markup=keyboard,
                                )
                    else:
                        # Audio yo'q bo'lsa, video yuborish
                        if media_data.get('thumbnail_path'):
                            thumb = FSInputFile(media_data['thumbnail_path'])
                            sent_message = await message.answer_video(
                                video=file,
                                caption=caption,
                                thumbnail=thumb,
                                duration=duration,
                                reply_markup=keyboard,
                            )
                        else:
                            sent_message = await message.answer_video(
                                video=file,
                                caption=caption,
                                duration=duration,
                                reply_markup=keyboard,
                            )
                
                else:  # video_audio (default)
                    # Video + Audio yuborish
                    if media_data.get('thumbnail_path'):
                        thumb = FSInputFile(media_data['thumbnail_path'])
                        sent_message = await message.answer_video(
                            video=file,
                            caption=caption,
                            thumbnail=thumb,
                            duration=duration,
                            reply_markup=keyboard,
                        )
                    else:
                        sent_message = await message.answer_video(
                            video=file,
                            caption=caption,
                            duration=duration,
                            reply_markup=keyboard,
                        )
                    
                    # Agar video bo'lsa va audio_path mavjud bo'lsa, audio ham yuborish
                    if media_data.get('audio_path'):
                        try:
                            await loading_msg.edit_text("⏳ Audio yuborilmoqda...")
                            
                            audio_file = FSInputFile(media_data['audio_path'])
                            audio_caption = format_media_caption(
                                title=media_data.get('title'),
                                platform=platform,
                                duration=duration,
                                file_size=Path(media_data['audio_path']).stat().st_size if Path(media_data['audio_path']).exists() else None
                            )
                            
                            # Audio yuborish
                            await message.answer_audio(
                                audio=audio_file,
                                caption=audio_caption,
                                duration=duration,
                                reply_markup=keyboard,
                            )
                            logger.info(f"Audio yuborildi: {media_data.get('title')}")
                        except Exception as e:
                            logger.error(f"Audio yuborishda xatolik: {e}")
                            # Audio yuborishda xatolik bo'lsa ham, video yuborilgan bo'ladi
                
                # Cache'ga saqlash - barcha videolar saqlanadi
                if sent_message.video:
                    # Thumbnail file_id'ni olish (agar mavjud bo'lsa)
                    thumbnail_file_id = None
                    if sent_message.video.thumbnail:
                        thumbnail_file_id = sent_message.video.thumbnail.file_id
                    
                    await save_media_cache(
                        url=url,
                        platform=platform,
                        file_id=sent_message.video.file_id,
                        file_type='video',
                        file_unique_id=sent_message.video.file_unique_id,
                        title=media_data.get('title'),
                        thumbnail_file_id=thumbnail_file_id,
                        file_size=sent_message.video.file_size,
                        duration=sent_message.video.duration,
                    )
                    logger.info(f"Video cache'ga saqlandi: {url} (file_id: {sent_message.video.file_id})")
            
            elif is_audio:
                # Audio yuborish
                sent_message = await message.answer_audio(
                    audio=file,
                    caption=caption,
                    duration=duration,
                    reply_markup=keyboard,
                )
                
                # Cache'ga saqlash
                if sent_message.audio:
                    await save_media_cache(
                        url=url,
                        platform=platform,
                        file_id=sent_message.audio.file_id,
                        file_type='audio',
                        file_unique_id=sent_message.audio.file_unique_id,
                        title=media_data.get('title'),
                        file_size=sent_message.audio.file_size,
                        duration=sent_message.audio.duration,
                    )
            
            else:
                # Document sifatida yuborish
                sent_message = await message.answer_document(
                    document=file,
                    caption=caption,
                    reply_markup=keyboard,
                )
                
                # Cache'ga saqlash
                if sent_message.document:
                    await save_media_cache(
                        url=url,
                        platform=platform,
                        file_id=sent_message.document.file_id,
                        file_type='document',
                        file_unique_id=sent_message.document.file_unique_id,
                        title=media_data.get('title'),
                        file_size=sent_message.document.file_size,
                    )
            
            # Loading xabarini o'chirish
            await loading_msg.delete()
            
            # Qo'shimcha xabar yuborilmaydi - faqat media
        
        except TelegramAPIError as e:
            logger.error(f"Telegram API xatosi: {e}")
            await loading_msg.edit_text(
                f"❌ Media yuborishda xatolik: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        finally:
            # Temporary fayllarni o'chirish
            await cleanup_temp_files(file_path)
            if media_data.get('thumbnail_path'):
                await cleanup_temp_files(media_data['thumbnail_path'])
    
    except Exception as e:
        logger.error(f"Media yuklab olish va yuborishda xatolik: {e}")
        try:
            await loading_msg.edit_text(
                f"❌ Xatolik: {str(e)}\n\n"
                "Iltimos, qayta urinib ko'ring."
            )
        except:
            pass


async def send_cached_media(message: Message, cached_media):
    """
    Cache'dan media'ni yuborish (file_id orqali)
    """
    try:
        # Caption va keyboard yaratish
        caption = format_media_caption(
            title=cached_media.title,
            platform=cached_media.platform,
            duration=cached_media.duration,
            file_size=cached_media.file_size
        )
        keyboard = await get_bot_link_keyboard(message.bot)
        
        if cached_media.file_type == 'video':
            # Video file_id bilan yuborish
            # Eslatma: thumbnail file_id bilan yuborib bo'lmaydi, faqat InputFile bilan
            # Shuning uchun thumbnail o'tkazilmaydi, lekin video o'zi yuboriladi
            await message.answer_video(
                video=cached_media.file_id,
                caption=caption,
                reply_markup=keyboard,
            )
            logger.info(f"Cache'dan video yuborildi: {cached_media.url} (file_id: {cached_media.file_id})")
        elif cached_media.file_type == 'audio':
            await message.answer_audio(
                audio=cached_media.file_id,
                caption=caption,
                reply_markup=keyboard,
            )
        elif cached_media.file_type == 'photo':
            await message.answer_photo(
                photo=cached_media.file_id,
                caption=caption,
                reply_markup=keyboard,
            )
        else:  # document
            await message.answer_document(
                document=cached_media.file_id,
                caption=caption,
                reply_markup=keyboard,
            )
    except TelegramBadRequest as e:
        # Agar file_id eskirgan bo'lsa, cache'dan o'chirish va qayta yuklab olish kerak
        logger.warning(f"File ID eskirgan: {cached_media.file_id}, xatolik: {e}")
        raise

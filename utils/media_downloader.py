"""
Media downloader utility - YouTube, Instagram, TikTok va boshqa platformalardan media yuklab olish
"""

import re
import logging
import asyncio
from typing import Optional, Dict, Tuple
from pathlib import Path
import tempfile
import shutil
import os
from urllib import request, parse
import html
from config import config

logger = logging.getLogger(__name__)

# Xatolik turlari
class MediaDownloadError(Exception):
    """Media yuklab olish xatoligi"""
    def __init__(self, message: str, error_type: str = "unknown"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

# Platform URL patterns
PLATFORM_PATTERNS = {
    'youtube': [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*&v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:m\.)?youtube\.com/watch\?.*&v=([a-zA-Z0-9_-]{11})',
    ],
    'instagram': [
        r'(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv)/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/',
        r'(?:https?://)?(?:www\.)?instagram\.com/stories/([a-zA-Z0-9_.]+)/(\d+)',  # Instagram stories
    ],
    'tiktok': [
        r'(?:https?://)?(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/([a-zA-Z0-9]+)',
        r'(?:https?://)?(?:www\.)?tiktok\.com/@[^/]+/video/(\d+)',
    ],
    'twitter': [
        r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[^/]+/status/(\d+)',
    ],
    'facebook': [
        r'(?:https?://)?(?:www\.)?facebook\.com/[^/]+/videos/(\d+)',
        r'(?:https?://)?(?:www\.)?fb\.watch/([a-zA-Z0-9_-]+)',
    ],
}


def _resolve_instagram_cookies_path() -> Optional[Path]:
    """
    Instagram cookies fayl yo'lini topish.

    Priority:
    1) INSTAGRAM_COOKIES_FILE
    2) Project root ichidagi cookies.txt
    3) /app/cookies.txt (docker image)
    """
    candidates = []
    if config.bot.instagram_cookies_file:
        candidates.append(Path(config.bot.instagram_cookies_file))

    project_cookies = Path(__file__).resolve().parent.parent / "cookies.txt"
    candidates.append(project_cookies)
    candidates.append(Path("/app/cookies.txt"))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _resolve_youtube_cookies_path() -> Optional[Path]:
    """
    YouTube cookies fayl yo'lini topish.

    Priority:
    1) YOUTUBE_COOKIES_FILE
    2) Bot config'dagi youtube_cookies_file (agar mavjud bo'lsa)
    3) INSTAGRAM_COOKIES_FILE (bitta umumiy cookies fayl ishlatilsa)
    4) Project root ichidagi cookies.txt
    5) /app/cookies.txt (docker image)
    """
    candidates = []

    env_youtube = os.getenv("YOUTUBE_COOKIES_FILE")
    if env_youtube:
        candidates.append(Path(env_youtube))

    cfg_youtube = getattr(config.bot, "youtube_cookies_file", None)
    if cfg_youtube:
        candidates.append(Path(cfg_youtube))

    if config.bot.instagram_cookies_file:
        candidates.append(Path(config.bot.instagram_cookies_file))

    project_cookies = Path(__file__).resolve().parent.parent / "cookies.txt"
    candidates.append(project_cookies)
    candidates.append(Path("/app/cookies.txt"))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _classify_instagram_error(error_text: str) -> Optional[str]:
    """
    Instagram xatoliklarini foydalanuvchiga tushunarli turlarga ajratish.
    """
    error_text = error_text.lower()

    auth_markers = (
        "login required",
        "rate-limit",
        "requested content is not available",
        "use --cookies",
        "private",
        "forbidden",
        "http error 403",
        "unauthorized",
    )
    if any(marker in error_text for marker in auth_markers):
        return "auth_required"

    if "story" in error_text and ("not available" in error_text or "not found" in error_text):
        return "story_unavailable"

    return None


def _classify_youtube_error(error_text: str) -> Optional[str]:
    """
    YouTube xatoliklarini foydalanuvchiga tushunarli turlarga ajratish.
    """
    error_text = error_text.lower()

    auth_markers = (
        "sign in to confirm you’re not a bot",
        "sign in to confirm you're not a bot",
        "use --cookies-from-browser",
        "use --cookies",
        "login required",
        "this video is private",
        "http error 403",
        "forbidden",
    )
    if any(marker in error_text for marker in auth_markers):
        return "auth_required"

    return None


def _cookies_header_from_file(cookies_path: Optional[Path]) -> str:
    """
    Netscape cookie file'dan Cookie header tayyorlash.
    """
    if not cookies_path or not cookies_path.exists():
        return ""

    pairs = []
    try:
        for line in cookies_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, _, _, _, name, value = parts[:7]
            if "instagram.com" not in domain:
                continue
            if name and value:
                pairs.append(f"{name}={value}")
    except Exception as e:
        logger.warning(f"Cookie header yaratishda xatolik: {e}")
        return ""

    return "; ".join(pairs)


def _download_url_to_file(file_url: str, output_path: Path, cookie_header: str = "") -> bool:
    """
    URL'dan fayl yuklab olish (urllib).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.instagram.com/",
    }
    if cookie_header:
        headers["Cookie"] = cookie_header

    req = request.Request(file_url, headers=headers)
    with request.urlopen(req, timeout=45) as resp:
        data = resp.read()
        if not data:
            return False
        output_path.write_bytes(data)
    return output_path.exists() and output_path.stat().st_size > 0


def _extract_instagram_meta_media(html_text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Instagram HTML'dan media URL va title ni olish.
    Returns:
        media_url, media_type(video|photo), title
    """
    video_match = re.search(r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    image_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)

    title = html.unescape(title_match.group(1)) if title_match else "Instagram"

    if video_match:
        return html.unescape(video_match.group(1)), "video", title
    if image_match:
        return html.unescape(image_match.group(1)), "photo", title
    return None, None, title


async def _instagram_meta_fallback(url: str, temp_dir: str, cookies_path: Optional[Path]) -> Optional[Dict]:
    """
    yt-dlp format topa olmaganda Instagram sahifasidan og:video/og:image orqali fallback.
    """
    try:
        cookie_header = _cookies_header_from_file(cookies_path)

        def _fetch_page() -> str:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.instagram.com/",
                "Accept-Language": "en-US,en;q=0.9",
            }
            if cookie_header:
                headers["Cookie"] = cookie_header
            req = request.Request(url, headers=headers)
            with request.urlopen(req, timeout=45) as resp:
                return resp.read().decode("utf-8", errors="ignore")

        page_html = await asyncio.to_thread(_fetch_page)
        media_url, media_type, title = _extract_instagram_meta_media(page_html)

        if not media_url or not media_type:
            return None

        parsed = parse.urlparse(media_url)
        ext = Path(parsed.path).suffix.lower()
        if media_type == "video":
            if ext not in (".mp4", ".webm", ".mov"):
                ext = ".mp4"
            filename = f"instagram_fallback{ext}"
        else:
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            filename = f"instagram_fallback{ext}"

        media_path = Path(temp_dir) / filename
        ok = await asyncio.to_thread(_download_url_to_file, media_url, media_path, cookie_header)
        if not ok:
            return None

        return {
            'file_path': str(media_path),
            'title': title or 'Instagram',
            'duration': None,
            'thumbnail_path': None,
            'platform': 'instagram',
            'audio_path': None,
        }
    except Exception as e:
        logger.warning(f"Instagram meta fallback muvaffaqiyatsiz: {e}")
        return None


def detect_platform(url: str) -> Optional[str]:
    """
    URL dan platformani aniqlash
    
    Args:
        url: Media URL
    
    Returns:
        Platform nomi yoki None
    """
    url = url.strip()
    
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return platform
    
    return None


def is_valid_url(url: str) -> bool:
    """
    URL to'g'ri ekanligini tekshirish
    
    Args:
        url: URL
    
    Returns:
        True agar to'g'ri bo'lsa
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(url_pattern.match(url))


async def normalize_tiktok_url(url: str) -> str:
    """
    TikTok URL'ni normalize qilish - redirect muammosini hal qilish
    
    Args:
        url: TikTok URL
    
    Returns:
        Normalize qilingan URL
    """
    url = url.strip()
    
    # Agar vm.tiktok.com yoki vt.tiktok.com bo'lsa, to'g'ridan-to'g'ri ishlatish
    # yt-dlp o'zi redirect'ni kuzatadi, lekin ba'zida muammo bo'ladi
    # Shuning uchun URL'ni to'g'ri formatga o'tkazamiz
    
    # vm.tiktok.com/ZSNYW7Dd2 formatini saqlab qolish
    if re.match(r'https?://(?:vm|vt)\.tiktok\.com/[a-zA-Z0-9]+', url, re.IGNORECASE):
        # Bu format to'g'ri, yt-dlp buni qo'llab-quvvatlaydi
        return url
    
    # www.tiktok.com/@username/video/1234567890 formatini tekshirish
    video_match = re.search(r'tiktok\.com/@([^/]+)/video/(\d+)', url, re.IGNORECASE)
    if video_match:
        # Bu format ham to'g'ri
        return url
    
    # Agar boshqa format bo'lsa, asl URL'ni qaytarish
    return url


async def download_media(url: str, platform: str) -> Optional[Dict]:
    """
    Media yuklab olish (yt-dlp yoki boshqa tool orqali)
    
    Args:
        url: Media URL
        platform: Platform nomi
    
    Returns:
        Media ma'lumotlari dict yoki None
        Dict ichida 'error_type' kaliti bo'lishi mumkin (xatolik bo'lganda)
    """
    try:
        # yt-dlp ishlatish
        import yt_dlp
        
        # Temporary directory yaratish
        temp_dir = tempfile.mkdtemp()
        
        try:
            # yt-dlp sozlamalari - video sifatini saqlab qolish
            # FFmpeg ishlatmasdan, faqat allaqachon birlashtirilgan formatlarni ishlatish
            # Bu video sifatini yaxshiroq saqlaydi va qorayishni oldini oladi
            ydl_opts = {
                # Faqat allaqachon birlashtirilgan formatlar (video+audio birga)
                # FFmpeg ishlatmasdan, to'g'ridan-to'g'ri yuklab olish
                'format': 'best[ext=mp4][vcodec!=none][acodec!=none]/best[ext=mp4]/best[vcodec!=none][acodec!=none]/best',
                'outtmpl': str(Path(temp_dir) / '%(title)s.%(ext)s'),
                'quiet': True,  # Production uchun quiet
                'no_warnings': True,
                'extract_flat': False,
                'noplaylist': True,  # Playlist emas, faqat video
            }
            
            # Video uchun thumbnail ham olish
            if platform in ('youtube', 'tiktok'):
                ydl_opts['writethumbnail'] = True
                ydl_opts['writesubtitles'] = False  # Subtitlarni o'chirish
                ydl_opts['writeautomaticsub'] = False
            
            # yt-dlp optimallashtirish sozlamalari
            ydl_opts.update({
                'no_check_certificate': False,  # SSL sertifikatni tekshirish
                'prefer_insecure': False,  # HTTPS'ni afzal ko'rish
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # User agent
                'extractor_args': {},  # Extractor arguments
            })
            
            # YouTube uchun maxsus sozlamalar
            if platform == 'youtube':
                # YouTube extractor args - yanada yaxshi extraction uchun
                # yt-dlp'ning tavsiya etilgan sozlamalari
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        # Android va web client - eng yaxshi formatlar uchun
                        'player_client': ['android_sdkless', 'web'],
                    }
                }

                cookies_path = _resolve_youtube_cookies_path()
                if cookies_path:
                    ydl_opts['cookiefile'] = str(cookies_path)
                    logger.info(f"YouTube cookies ishlatilmoqda: {cookies_path}")
                else:
                    logger.warning("YouTube cookies fayl topilmadi (YOUTUBE_COOKIES_FILE yoki cookies.txt)")
            
            # TikTok uchun maxsus sozlamalar
            if platform == 'tiktok':
                # TikTok URL'ni normalize qilish
                url = await normalize_tiktok_url(url)
                logger.info(f"TikTok URL normalize qilindi: {url}")
                
                # TikTok uchun maxsus sozlamalar
                ydl_opts.update({
                    'extractor_args': {
                        'tiktok': {
                            # TikTok extractor sozlamalari
                            'webpage_download': True,  # Webpage'ni yuklab olish
                        }
                    },
                    # TikTok uchun qo'shimcha sozlamalar
                    'no_check_certificate': False,
                    'prefer_insecure': False,
                })
            
            # Instagram uchun maxsus sozlamalar
            if platform == 'instagram':
                # Instagram post/reel/story turiga qarab media video yoki rasm bo'lishi mumkin.
                # "best" rasm postlar uchun ham format topishga yordam beradi.
                ydl_opts['format'] = 'best'

                # Instagram uchun cookies qo'shish (agar mavjud bo'lsa)
                cookies_path = _resolve_instagram_cookies_path()
                if cookies_path:
                    ydl_opts['cookiefile'] = str(cookies_path)
                    logger.info(f"Instagram cookies ishlatilmoqda: {cookies_path}")
                else:
                    logger.warning("Instagram cookies fayl topilmadi (INSTAGRAM_COOKIES_FILE yoki cookies.txt)")
                
                # Instagram uchun qo'shimcha sozlamalar
                ydl_opts.update({
                    'extractor_args': {
                        'instagram': {
                            # Instagram extractor sozlamalari
                        }
                    },
                    # SSL xatolarini hal qilish uchun
                    'no_check_certificate': True,  # SSL sertifikatni tekshirmaslik (Instagram uchun)
                    'prefer_insecure': False,
                })
                
                # Instagram story uchun maxsus sozlamalar
                if '/stories/' in url or '/story/' in url:
                    ydl_opts.update({
                        'extractor_args': {
                            'instagram': {
                                'skip_login': False,  # Login kerak
                            }
                        }
                    })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Media ma'lumotlarini olish
                # download=True - faylni yuklab olish
                # Timeout sozlamalari
                try:
                    # Timeout: 5 daqiqa (300 sekund)
                    info = await asyncio.wait_for(
                        asyncio.to_thread(ydl.extract_info, url, True),
                        timeout=300.0
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Media yuklab olish timeout: {url}")
                    return None
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e).lower()
                    logger.error(f"yt-dlp download xatosi: {e}")
                    
                    # TikTok uchun maxsus tekshirish
                    if platform == 'tiktok':
                        # IP bloklanish xatoliklarini tekshirish
                        if 'ip address is blocked' in error_msg or ('ip address' in error_msg and 'blocked' in error_msg):
                            logger.warning(f"TikTok IP bloklangan: {url}")
                            logger.warning("TikTok server IP manzilni bloklagan. Bu vaqtinchalik muammo bo'lishi mumkin.")
                            # IP bloklanish uchun retry foydasiz, darhol qaytarish
                            # Xatolik ma'lumotlarini dict sifatida qaytarish
                            return {'error_type': 'ip_blocked', 'error_message': str(e)}
                        
                        # Agar "Unsupported URL" yoki "explore" xatosi bo'lsa
                        if 'unsupported url' in error_msg or 'explore' in error_msg:
                            logger.warning(f"TikTok link redirect muammosi: {url}")
                            logger.warning("TikTok link to'g'ri video emas yoki redirect noto'g'ri URL'ga olib keldi")
                            # TikTok linkini to'g'ri formatga o'tkazishga harakat qilish
                            # vm.tiktok.com linklarini to'g'ridan-to'g'ri ishlatish
                            if 'vm.tiktok.com' in url.lower() or 'vt.tiktok.com' in url.lower():
                                # Bu link to'g'ri, lekin redirect muammosi bo'lishi mumkin
                                # yt-dlp'ning o'z extractor'ini ishlatish
                                logger.info("TikTok link to'g'ri formatda, lekin redirect muammosi")
                            return None
                    
                    # Instagram story uchun maxsus tekshirish
                    if platform == 'instagram' and ('/stories/' in url or '/story/' in url):
                        if 'connection' in error_msg or 'ssl' in error_msg or 'certificate' in error_msg:
                            logger.warning("Instagram story yuklab olishda tarmoq xatosi - Instagram tomonidan bloklangan bo'lishi mumkin")
                            return None

                    if platform == 'instagram':
                        if 'no video formats found' in error_msg:
                            logger.info("Instagram meta fallback ishga tushirildi (primary)")
                            fallback_data = await _instagram_meta_fallback(url, temp_dir, cookies_path)
                            if fallback_data:
                                return fallback_data

                        classified_error = _classify_instagram_error(error_msg)
                        if classified_error:
                            return {'error_type': classified_error, 'error_message': str(e)}

                    if platform == 'youtube':
                        classified_error = _classify_youtube_error(error_msg)
                        if classified_error:
                            return {'error_type': classified_error, 'error_message': str(e)}
                    
                    # Qayta urinish - oddiy format bilan
                    logger.info("Oddiy format bilan qayta urinilmoqda...")
                    # Retry uchun yangi ydl_opts yaratish (SSL sozlamalarini saqlab qolish)
                    retry_ydl_opts = ydl_opts.copy()
                    retry_ydl_opts['format'] = 'best[ext=mp4]/best'
                    if platform == 'instagram':
                        retry_ydl_opts['format'] = 'best'
                    
                    # TikTok uchun retry'da ham normalize qilish
                    if platform == 'tiktok':
                        retry_url = await normalize_tiktok_url(url)
                        if retry_url != url:
                            logger.info(f"TikTok URL retry'da normalize qilindi: {retry_url}")
                            url = retry_url
                    
                    # Yangi YDL instance yaratish va retry
                    try:
                        with yt_dlp.YoutubeDL(retry_ydl_opts) as retry_ydl:
                            info = await asyncio.wait_for(
                                asyncio.to_thread(retry_ydl.extract_info, url, True),
                                timeout=300.0
                            )
                    except asyncio.TimeoutError:
                        logger.error(f"Media yuklab olish timeout (retry): {url}")
                        return None
                    except yt_dlp.utils.DownloadError as retry_e:
                        retry_error_msg = str(retry_e).lower()
                        logger.error(f"Retry ham muvaffaqiyatsiz: {retry_e}")
                        
                        # TikTok uchun maxsus xatolik xabari
                        if platform == 'tiktok':
                            if 'ip address is blocked' in retry_error_msg or ('ip address' in retry_error_msg and 'blocked' in retry_error_msg):
                                logger.warning("TikTok IP bloklangan (retry)")
                            elif 'unsupported url' in retry_error_msg or 'explore' in retry_error_msg:
                                logger.warning("TikTok link to'g'ri video emas yoki TikTok tomonidan bloklangan")

                        if platform == 'instagram':
                            if 'no video formats found' in retry_error_msg:
                                logger.info("Instagram meta fallback ishga tushirildi (retry)")
                                fallback_data = await _instagram_meta_fallback(url, temp_dir, cookies_path)
                                if fallback_data:
                                    return fallback_data

                            classified_error = _classify_instagram_error(retry_error_msg)
                            if classified_error:
                                return {'error_type': classified_error, 'error_message': str(retry_e)}

                        if platform == 'youtube':
                            classified_error = _classify_youtube_error(retry_error_msg)
                            if classified_error:
                                return {'error_type': classified_error, 'error_message': str(retry_e)}
                        
                        return None
                
                if not info:
                    return None
                
                # Download qilingan fayl topish (thumbnail va subtitlarni olib tashlash)
                all_files = list(Path(temp_dir).glob('*'))
                # Thumbnail, subtitl va boshqa yordamchi fayllarni olib tashlash
                excluded_suffixes = {'.vtt', '.srt', '.ass', '.description'}
                if platform != 'instagram':
                    excluded_suffixes.update({'.jpg', '.webp', '.png', '.jpeg'})

                media_files = [
                    f for f in all_files 
                    if f.is_file() 
                    and f.stat().st_size > 0  # Bo'sh fayllarni olib tashlash
                    and f.suffix.lower() not in excluded_suffixes
                ]
                
                if not media_files:
                    logger.error(f"Media fayl topilmadi. Temp dir: {temp_dir}, Files: {[f.name for f in all_files]}")
                    return None
                
                media_file = media_files[0]
                
                # Fayl hajmini tekshirish
                file_size = media_file.stat().st_size
                if file_size == 0:
                    logger.error(f"Media fayl bo'sh: {media_file}")
                    return None
                
                logger.info(f"Media fayl topildi: {media_file.name}, hajmi: {file_size / 1024 / 1024:.2f} MB")
                
                # Video yoki audio ekanligini aniqlash
                file_ext = media_file.suffix.lower()
                is_video = file_ext in ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')
                
                result = {
                    'file_path': str(media_file),
                    'title': info.get('title', 'Media'),
                    'duration': info.get('duration'),
                    'thumbnail_path': None,
                    'platform': platform,
                    'audio_path': None,  # Audio fayl yo'li (agar mavjud bo'lsa)
                }
                
                # Thumbnail topish
                thumbnail_files = list(Path(temp_dir).glob('*.jpg')) + list(Path(temp_dir).glob('*.webp'))
                if thumbnail_files:
                    result['thumbnail_path'] = str(thumbnail_files[0])
                
                # Agar video bo'lsa, audio formatini ham yuklab olish
                if is_video and platform in ('youtube', 'instagram', 'tiktok'):
                    try:
                        # Audio formatini yuklab olish
                        audio_ydl_opts = {
                            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                            'outtmpl': str(Path(temp_dir) / '%(title)s_audio.%(ext)s'),
                            'quiet': True,
                            'no_warnings': True,
                            'extract_flat': False,
                            'noplaylist': True,
                        }
                        
                        # Instagram/YouTube uchun cookies
                        if platform in ('instagram', 'youtube'):
                            if platform == 'instagram':
                                cookies_path = _resolve_instagram_cookies_path()
                            else:
                                cookies_path = _resolve_youtube_cookies_path()
                            if cookies_path:
                                audio_ydl_opts['cookiefile'] = str(cookies_path)

                        # Instagram uchun SSL sozlamalari
                        if platform == 'instagram':
                            audio_ydl_opts['no_check_certificate'] = True
                        
                        with yt_dlp.YoutubeDL(audio_ydl_opts) as audio_ydl:
                            # Audio yuklab olish
                            try:
                                await asyncio.wait_for(
                                    asyncio.to_thread(audio_ydl.extract_info, url, True),
                                    timeout=180.0  # 3 daqiqa timeout
                                )
                                
                                # Audio fayl topish
                                audio_files = [
                                    f for f in Path(temp_dir).glob('*_audio.*')
                                    if f.is_file() and f.stat().st_size > 0
                                    and f.suffix.lower() in ('.m4a', '.mp3', '.ogg', '.opus')
                                ]
                                
                                if audio_files:
                                    result['audio_path'] = str(audio_files[0])
                                    logger.info(f"Audio fayl yuklandi: {audio_files[0].name}")
                            except asyncio.TimeoutError:
                                logger.warning(f"Audio yuklab olish timeout: {url}")
                            except Exception as e:
                                logger.warning(f"Audio yuklab olishda xatolik: {e}")
                    except Exception as e:
                        logger.warning(f"Audio yuklab olishda umumiy xatolik: {e}")
                
                return result
                
        except Exception as e:
            logger.error(f"Media yuklab olishda xatolik ({platform}): {e}")
            return None
        finally:
            # Temporary directory o'chirish (agar kerak bo'lsa)
            # Lekin fayl yuborilguncha saqlab qolamiz
            pass
    
    except ImportError:
        logger.error("yt-dlp kutubxonasi o'rnatilmagan!")
        return None
    except Exception as e:
        logger.error(f"Media downloader xatosi: {e}")
        return None


async def cleanup_temp_files(file_path: str):
    """
    Temporary fayllarni o'chirish
    
    Args:
        file_path: Fayl yo'li
    """
    try:
        file = Path(file_path)
        if file.exists():
            file.unlink()
        
        # Thumbnail ham o'chirish
        parent = file.parent
        for thumb_file in parent.glob('*.jpg'):
            thumb_file.unlink()
        for thumb_file in parent.glob('*.webp'):
            thumb_file.unlink()
        
        # Directory bo'sh bo'lsa, o'chirish
        try:
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except:
            pass
    except Exception as e:
        logger.error(f"Temporary fayllarni o'chirishda xatolik: {e}")

"""
Shazam music recognition utility - Voice message'dan musiqani aniqlash
"""

import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


async def recognize_music_from_voice(voice_file_path: str) -> Optional[Dict]:
    """
    Voice fayldan musiqani aniqlash (ShazamIO orqali)
    
    Args:
        voice_file_path: Voice fayl yo'li (OGG format)
    
    Returns:
        Dict yoki None:
        {
            'title': str,
            'artist': str,
            'album': str,
            'release_date': str,
            'youtube_url': str,  # YouTube qidiruv natijasi
        }
    """
    try:
        from shazamio import Shazam
        
        # Fayl mavjudligini tekshirish
        if not Path(voice_file_path).exists():
            logger.error(f"Voice fayl topilmadi: {voice_file_path}")
            return None
        
        shazam = Shazam()
        
        # Voice faylni Shazam'ga yuborish (recognize_song o'rniga recognize)
        logger.info(f"Musiqani aniqlash boshlandi: {voice_file_path}")
        result = await shazam.recognize(voice_file_path)
        
        if not result:
            logger.warning("Musiqa aniqlanmadi - result bo'sh")
            return None
        
        # Result strukturasini tekshirish
        # ShazamIO'ning yangi versiyasida result struktura o'zgargan bo'lishi mumkin
        track = None
        if isinstance(result, dict):
            # Eski format: {'track': {...}}
            if 'track' in result:
                track = result['track']
            # Yangi format: to'g'ridan-to'g'ri track ma'lumotlari
            elif 'title' in result or 'subtitle' in result:
                track = result
            # Boshqa formatlar
            elif 'matches' in result:
                # Match-based format
                matches = result.get('matches', [])
                if matches:
                    track = matches[0].get('track', {})
        elif hasattr(result, 'track'):
            # Object-based format
            track = result.track
        elif hasattr(result, 'title'):
            # Direct track object
            track = result
        
        if not track:
            logger.warning("Musiqa aniqlanmadi - track topilmadi")
            return None
        
        # Ma'lumotlarni olish
        if isinstance(track, dict):
            title = track.get('title') or track.get('heading', {}).get('title', 'Noma\'lum')
            artist = track.get('subtitle') or track.get('heading', {}).get('subtitle', 'Noma\'lum artist')
            # Album ma'lumotlari
            album = 'Noma\'lum album'
            if track.get('sections'):
                for section in track['sections']:
                    if section.get('metadata'):
                        for meta in section['metadata']:
                            if meta.get('title') == 'Album':
                                album = meta.get('text', 'Noma\'lum album')
                                break
        else:
            # Object-based
            title = getattr(track, 'title', None) or getattr(track, 'heading', {}).get('title', 'Noma\'lum') if hasattr(track, 'heading') else 'Noma\'lum'
            artist = getattr(track, 'subtitle', None) or getattr(track, 'heading', {}).get('subtitle', 'Noma\'lum artist') if hasattr(track, 'heading') else 'Noma\'lum artist'
            album = 'Noma\'lum album'
        
        # YouTube URL qidirish
        search_query = f"{artist} {title}"
        youtube_url = await search_youtube_url(search_query)
        
        logger.info(f"Musiqa aniqlandi: {artist} - {title}")
        
        # Release date
        release_date = ''
        if isinstance(track, dict):
            release_date = track.get('release_date') or track.get('release', '')
        else:
            release_date = getattr(track, 'release_date', None) or getattr(track, 'release', '') or ''
        
        return {
            'title': title,
            'artist': artist,
            'album': album,
            'release_date': release_date,
            'youtube_url': youtube_url,
            'search_query': search_query,
        }
        
    except ImportError:
        logger.error("ShazamIO kutubxonasi o'rnatilmagan! pip install shazamio")
        return None
    except Exception as e:
        logger.error(f"Musiqa aniqlashda xatolik: {e}")
        return None


async def search_youtube_url(search_query: str) -> Optional[str]:
    """
    YouTube'dan musiqani qidirish va birinchi video URL'ini qaytarish
    
    Args:
        search_query: Qidiruv so'rovi (masalan: "Artist - Title")
    
    Returns:
        YouTube video URL yoki None
    """
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch1',  # Faqat birinchi natijani olish
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # YouTube qidiruv - ytsearch1: prefix bilan
            search_url = f"ytsearch1:{search_query}"
            info = ydl.extract_info(search_url, download=False)
            
            if info and 'entries' in info and info['entries']:
                video = info['entries'][0]
                # Video URL'ini olish
                video_url = video.get('webpage_url') or video.get('url')
                if video_url:
                    logger.info(f"YouTube video topildi: {video_url}")
                    return video_url
                else:
                    # Agar URL bo'lmasa, video ID'dan URL yaratish
                    video_id = video.get('id')
                    if video_id:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        logger.info(f"YouTube video topildi (ID'dan): {video_url}")
                        return video_url
        
        logger.warning(f"YouTube'da video topilmadi: {search_query}")
        return None
        
    except Exception as e:
        logger.error(f"YouTube qidiruvda xatolik: {e}")
        return None


async def search_youtube_videos(search_query: str, max_results: int = 10) -> list[Dict]:
    """
    YouTube'dan musiqani qidirish va bir nechta video natijalarini qaytarish
    
    Args:
        search_query: Qidiruv so'rovi (masalan: "Artist - Title")
        max_results: Maksimal natijalar soni (default: 10)
    
    Returns:
        Video natijalari ro'yxati:
        [
            {
                'id': str,
                'title': str,
                'url': str,
                'duration': int,
                'view_count': int,
            },
            ...
        ]
    """
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': f'ytsearch{max_results}',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # YouTube qidiruv
            search_url = f"ytsearch{max_results}:{search_query}"
            info = ydl.extract_info(search_url, download=False)
            
            videos = []
            if info and 'entries' in info and info['entries']:
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    # Video URL'ini olish
                    video_url = entry.get('webpage_url') or entry.get('url')
                    if not video_url:
                        # Agar URL bo'lmasa, video ID'dan URL yaratish
                        video_id = entry.get('id')
                        if video_id:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                        else:
                            continue
                    
                    video_data = {
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Noma\'lum'),
                        'url': video_url,
                        'duration': entry.get('duration', 0),
                        'view_count': entry.get('view_count', 0),
                        'uploader': entry.get('uploader', 'Noma\'lum'),
                    }
                    videos.append(video_data)
            
            logger.info(f"YouTube'da {len(videos)} ta video topildi: {search_query}")
            return videos
        
    except Exception as e:
        logger.error(f"YouTube qidiruvda xatolik: {e}")
        return []

#!/usr/bin/env python3
"""
YouTube cookies faylini tekshirish (terminaldan ishga tushirish).
Ishlatish: python check_youtube_cookies.py
"""
import os
import sys
from pathlib import Path

# Project root dan import qilish uchun
sys.path.insert(0, str(Path(__file__).resolve().parent))

# .env yuklash (config uchun)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from utils.media_downloader import validate_youtube_cookies, _resolve_youtube_cookies_path


def main():
    path = _resolve_youtube_cookies_path()
    if not path:
        print("XATO: YouTube cookies fayli topilmadi.")
        print("  YOUTUBE_COOKIES_FILE o'rnating yoki loyiha ildizida cookies.txt qo'ying.")
        return 1
    print(f"Cookie fayl: {path}")
    ok, msg = validate_youtube_cookies(path)
    if ok:
        print(f"OK: {msg}")
        return 0
    print(f"XATO: {msg}")
    print("\nYouTube cookie'larni qanday eksport qilish:")
    print("  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies")
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""
In-memory cache utility - tez ishlash uchun
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    LRU (Least Recently Used) cache - memory'da tez ishlash uchun
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Args:
            max_size: Maksimal cache o'lchami (default: 1000)
            ttl_seconds: Time-to-live sekundlarda (default: 3600 = 1 soat)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Cache'dan ma'lumot olish
        
        Args:
            key: Cache kaliti
        
        Returns:
            Ma'lumot yoki None
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # TTL tekshirish
            if datetime.now() > entry['expires_at']:
                # Muddati o'tgan - o'chirish
                del self._cache[key]
                return None
            
            # LRU - eng so'nggi ishlatilganini boshiga ko'chirish
            self._cache.move_to_end(key)
            
            return entry['value']
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Cache'ga ma'lumot saqlash
        
        Args:
            key: Cache kaliti
            value: Saqlanadigan ma'lumot
            ttl_seconds: Time-to-live (agar None bo'lsa, default ishlatiladi)
        """
        async with self._lock:
            # Agar cache to'liq bo'lsa, eng eski (birinchi) elementni o'chirish
            if len(self._cache) >= self.max_size:
                # LRU - eng eski elementni o'chirish
                self._cache.popitem(last=False)
            
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds or self.ttl_seconds)
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
            }
            # Eng so'nggi ishlatilganini boshiga ko'chirish
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> None:
        """
        Cache'dan ma'lumot o'chirish
        
        Args:
            key: Cache kaliti
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self) -> None:
        """Cache'ni tozalash"""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> None:
        """Muddati o'tgan elementlarni tozalash"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry['expires_at']
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def size(self) -> int:
        """Cache o'lchami"""
        return len(self._cache)


# Global memory cache instance
# Media cache uchun - URL bo'yicha tez qidirish
media_cache = MemoryCache(max_size=500, ttl_seconds=7200)  # 2 soat

# Search results cache uchun - foydalanuvchi bo'yicha
search_cache = MemoryCache(max_size=200, ttl_seconds=1800)  # 30 daqiqa

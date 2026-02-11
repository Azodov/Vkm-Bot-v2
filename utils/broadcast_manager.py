"""
Broadcast holatini boshqarish - to'xtatish va graceful shutdown uchun
"""

import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BroadcastManager:
    """Broadcast jarayonini boshqarish"""
    
    def __init__(self):
        # Broadcast to'xtatish uchun event
        self._stop_event: Optional[asyncio.Event] = None
        # Broadcast ma'lumotlari (status xabari, progress va h.k.)
        self._broadcast_data: Optional[Dict[str, Any]] = None
        # Lock - thread-safe ishlash uchun
        self._lock = asyncio.Lock()
    
    async def start_broadcast(self, broadcast_data: Dict[str, Any]) -> asyncio.Event:
        """
        Broadcast jarayonini boshlash
        
        Args:
            broadcast_data: Broadcast ma'lumotlari (status_msg, callback va h.k.)
        
        Returns:
            Stop event - broadcast to'xtatish uchun
        """
        async with self._lock:
            # Agar allaqachon broadcast ishlamoqda bo'lsa, eski event'ni qaytarish
            if self._stop_event and not self._stop_event.is_set():
                logger.warning("Broadcast allaqachon ishlamoqda!")
                return self._stop_event
            
            # Yangi event yaratish
            self._stop_event = asyncio.Event()
            self._broadcast_data = broadcast_data
            logger.info("Broadcast jarayoni boshlandi")
            return self._stop_event
    
    async def stop_broadcast(self) -> bool:
        """
        Broadcast jarayonini to'xtatish
        
        Returns:
            True agar to'xtatildi, False agar to'xtatish mumkin emas
        """
        async with self._lock:
            if self._stop_event and not self._stop_event.is_set():
                self._stop_event.set()
                logger.info("Broadcast jarayoni to'xtatildi")
                return True
            return False
    
    async def is_broadcast_running(self) -> bool:
        """Broadcast ishlamoqdamimi tekshirish"""
        async with self._lock:
            return self._stop_event is not None and not self._stop_event.is_set()
    
    async def get_broadcast_data(self) -> Optional[Dict[str, Any]]:
        """Broadcast ma'lumotlarini olish"""
        async with self._lock:
            return self._broadcast_data
    
    async def clear_broadcast(self):
        """Broadcast holatini tozalash"""
        async with self._lock:
            self._stop_event = None
            self._broadcast_data = None
            logger.info("Broadcast holati tozalandi")


# Global broadcast manager instance
broadcast_manager = BroadcastManager()

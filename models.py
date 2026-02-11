"""
Database modellari
Misol sifatida User modeli
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, TIMESTAMP
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """Foydalanuvchi modeli"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Backward compatibility
    role = Column(String, default='user', nullable=False)  # superadmin, admin, user, guest
    media_preference = Column(String, default='video_audio', nullable=False)  # video_audio, video_only, audio_only
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, role={self.role})>"
    
    @property
    def is_superadmin(self) -> bool:
        """Superadmin ekanligini tekshirish"""
        return self.role == 'superadmin'
    
    @property
    def is_admin_role(self) -> bool:
        """Admin yoki superadmin ekanligini tekshirish"""
        return self.role in ('admin', 'superadmin')


class MandatoryChannel(Base):
    """Majburiy obuna kanallari va guruhlari modeli"""
    __tablename__ = "mandatory_channels"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(BigInteger, unique=True, index=True, nullable=False)
    channel_username = Column(String, nullable=True)  # @channel yoki None
    channel_title = Column(String, nullable=True)  # Kanal nomi
    channel_type = Column(String, nullable=False)  # 'channel' yoki 'group'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<MandatoryChannel(channel_id={self.channel_id}, username={self.channel_username}, type={self.channel_type})>"


class MediaLink(Base):
    """Media link va file_id cache modeli"""
    __tablename__ = "media_links"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)  # Original URL
    platform = Column(String, nullable=False, index=True)  # youtube, instagram, tiktok, etc. - indexed for faster queries
    file_id = Column(String, nullable=False)  # Telegram file_id
    file_type = Column(String, nullable=False, index=True)  # video, photo, audio, document - indexed
    file_unique_id = Column(String, nullable=True, index=True)  # Telegram file_unique_id - indexed
    title = Column(String, nullable=True)  # Media title/description
    thumbnail_file_id = Column(String, nullable=True)  # Thumbnail file_id (video uchun)
    file_size = Column(BigInteger, nullable=True)  # File size in bytes
    duration = Column(Integer, nullable=True)  # Duration in seconds (video/audio uchun)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # indexed for sorting
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    access_count = Column(Integer, default=0, nullable=False, index=True)  # Necha marta ishlatilgan - indexed
    
    def __repr__(self):
        return f"<MediaLink(url={self.url[:50]}..., platform={self.platform}, file_type={self.file_type})>"

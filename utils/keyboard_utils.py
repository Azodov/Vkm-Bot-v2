"""
Keyboard utility funksiyalari
Faqat Inline keyboardlar
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from typing import List


def get_inline_keyboard(
    buttons: List[List[tuple[str, str]]],
) -> InlineKeyboardMarkup:
    """
    Inline keyboard yaratish
    
    Args:
        buttons: Tugmalar ro'yxati [[(text, callback_data), ...], ...]
    
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    for row in buttons:
        keyboard.append([
            InlineKeyboardButton(text=text, callback_data=callback_data)
            for text, callback_data in row
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== ADMIN KEYBOARDS ====================

def get_admin_main_keyboard(is_superadmin: bool = False) -> InlineKeyboardMarkup:
    """Admin asosiy inline keyboard"""
    buttons = [
        [("📊 Statistika", "admin_stats")],
        [("📢 Xabar yuborish", "admin_broadcast")],
        [("📢 Majburiy obuna", "admin_mandatory_channels")],
        [("⚙️ Sozlamalar", "admin_settings")],
    ]
    # Superadminlar uchun Adminlar tugmasi
    if is_superadmin:
        buttons.insert(2, [("👥 Adminlar", "admin_manage_admins")])
    return get_inline_keyboard(buttons)


def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Admin statistika inline keyboard"""
    return get_inline_keyboard([
        [("🔄 Yangilash", "admin_refresh_stats")],
        [("📈 Batafsil", "admin_detailed_stats")],
        [("🔙 Asosiy menyu", "admin_back_to_main")],
    ])




def get_admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Admin broadcast inline keyboard"""
    return get_inline_keyboard([
        [("✅ Tasdiqlash", "admin_confirm_broadcast")],
        [("❌ Bekor qilish", "admin_cancel_broadcast")],
    ])


def get_admin_broadcast_running_keyboard() -> InlineKeyboardMarkup:
    """Admin broadcast ishlayotganda inline keyboard (to'xtatish tugmasi bilan)"""
    return get_inline_keyboard([
        [("⏹️ To'xtatish", "admin_stop_broadcast")],
    ])


def get_admin_broadcast_waiting_keyboard() -> InlineKeyboardMarkup:
    """Admin broadcast kutish inline keyboard (xabar kiritish paytida)"""
    return get_inline_keyboard([
        [("❌ Bekor qilish va chiqish", "admin_cancel_broadcast")],
    ])


# ==================== USER KEYBOARDS ====================

def get_user_main_keyboard() -> InlineKeyboardMarkup:
    """User asosiy inline keyboard"""
    return get_inline_keyboard([
        [("👤 Profil", "user_profile")],
    ])


def get_user_profile_keyboard() -> InlineKeyboardMarkup:
    """User profil inline keyboard"""
    return get_inline_keyboard([
        [("⚙️ Sozlamalar", "user_settings")],
        [("🔙 Asosiy menyu", "user_back_to_main")],
    ])


def get_user_settings_keyboard(current_preference: str = 'video_audio') -> InlineKeyboardMarkup:
    """User sozlamalar inline keyboard"""
    # Joriy tanlovni belgilash
    video_audio_icon = "✅" if current_preference == 'video_audio' else "⚪"
    video_only_icon = "✅" if current_preference == 'video_only' else "⚪"
    audio_only_icon = "✅" if current_preference == 'audio_only' else "⚪"
    
    return get_inline_keyboard([
        [(f"{video_audio_icon} 📹 Video + Audio", "user_set_video_audio")],
        [(f"{video_only_icon} 🎬 Faqat Video", "user_set_video_only")],
        [(f"{audio_only_icon} 🎵 Faqat Audio", "user_set_audio_only")],
        [("🔙 Profil", "user_profile")],
    ])


def get_user_info_keyboard() -> InlineKeyboardMarkup:
    """User ma'lumot inline keyboard"""
    return get_inline_keyboard([
        [("📋 Qoidalar", "user_rules")],
        [("💡 Ko'rsatmalar", "user_instructions")],
        [("🔙 Asosiy menyu", "user_back_to_main")],
    ])


# ==================== GUEST KEYBOARDS ====================

def get_guest_main_keyboard() -> InlineKeyboardMarkup:
    """Guest asosiy inline keyboard"""
    return get_inline_keyboard([
        [("📝 Ro'yxatdan o'tish", "guest_register")],
        [("ℹ️ Bot haqida", "guest_about")],
        [("❓ Yordam", "guest_help")],
    ])


def get_guest_register_keyboard() -> InlineKeyboardMarkup:
    """Guest ro'yxatdan o'tish inline keyboard"""
    return get_inline_keyboard([
        [("✅ Ro'yxatdan o'tish", "guest_register_confirm")],
        [("❌ Bekor qilish", "guest_cancel_register")],
    ])


def get_guest_info_keyboard() -> InlineKeyboardMarkup:
    """Guest ma'lumot inline keyboard"""
    return get_inline_keyboard([
        [("📋 Qoidalar", "guest_rules")],
        [("💡 Nima qilish mumkin?", "guest_what_can_do")],
        [("🔙 Orqaga", "guest_back_to_main")],
    ])


# ==================== MANDATORY CHANNEL KEYBOARDS ====================

def get_mandatory_channels_keyboard() -> InlineKeyboardMarkup:
    """Majburiy obuna kanallari inline keyboard"""
    return get_inline_keyboard([
        [("➕ Kanal qo'shish", "admin_add_channel")],
        [("📋 Kanallar ro'yxati", "admin_list_channels")],
        [("🔙 Asosiy menyu", "admin_back_to_main")],
    ])


def get_mandatory_channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Majburiy obuna kanallari ro'yxati inline keyboard"""
    buttons = []
    for channel in channels:
        status = "✅" if channel.is_active else "❌"
        channel_name = channel.channel_title or channel.channel_username or f"ID: {channel.channel_id}"
        buttons.append([(f"{status} {channel_name}", f"admin_channel_{channel.channel_id}")])
    
    buttons.append([("🔙 Orqaga", "admin_mandatory_channels")])
    return get_inline_keyboard(buttons)


def get_channel_manage_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """Kanal boshqarish inline keyboard"""
    return get_inline_keyboard([
        [("❌ O'chirish", f"admin_delete_channel_{channel_id}")],
        [("🔄 Faollik", f"admin_toggle_channel_{channel_id}")],
        [("🔙 Orqaga", "admin_list_channels")],
    ])

"""
User handlerlari - faqat inline keyboardlar bilan
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from filters import UserFilter
from utils import (
    get_user_main_keyboard,
    get_user_profile_keyboard,
    get_user_settings_keyboard,
)
from utils.user_utils import get_user_by_telegram_id, update_user_media_preference

router = Router(name="user")


@router.callback_query(F.data == "user_back_to_main", UserFilter())
async def user_main_menu(callback: CallbackQuery):
    """User asosiy menyu"""
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            f"👋 Salom, {callback.from_user.first_name}!\n\n"
            "Botga xush kelibsiz!",
            reply_markup=get_user_main_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            f"👋 Salom, {callback.from_user.first_name}!\n\n"
            "Botga xush kelibsiz!",
            reply_markup=get_user_main_keyboard()
        )


@router.callback_query(F.data == "user_profile", UserFilter())
async def show_profile(callback: CallbackQuery):
    """Profil"""
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "👤 <b>Profil</b>\n\n"
            "Quyidagi sozlamalarni o'zgartirishingiz mumkin:",
            reply_markup=get_user_profile_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "👤 <b>Profil</b>\n\n"
            "Quyidagi sozlamalarni o'zgartirishingiz mumkin:",
            reply_markup=get_user_profile_keyboard()
        )


@router.callback_query(F.data == "user_settings", UserFilter())
async def show_settings(callback: CallbackQuery):
    """Sozlamalar"""
    await callback.answer()
    
    # Foydalanuvchi ma'lumotlarini olish
    user = await get_user_by_telegram_id(callback.from_user.id)
    current_preference = user.media_preference if user else 'video_audio'
    
    # Preference nomini o'zbek tilida ko'rsatish
    preference_names = {
        'video_audio': '📹 Video + Audio',
        'video_only': '🎬 Faqat Video',
        'audio_only': '🎵 Faqat Audio'
    }
    current_name = preference_names.get(current_preference, '📹 Video + Audio')
    
    try:
        await callback.message.edit_text(
            f"⚙️ <b>Sozlamalar</b>\n\n"
            f"📥 <b>Media yuklash rejimi:</b> {current_name}\n\n"
            f"Quyidagilardan birini tanlang:",
            reply_markup=get_user_settings_keyboard(current_preference)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            f"⚙️ <b>Sozlamalar</b>\n\n"
            f"📥 <b>Media yuklash rejimi:</b> {current_name}\n\n"
            f"Quyidagilardan birini tanlang:",
            reply_markup=get_user_settings_keyboard(current_preference)
        )


@router.callback_query(F.data == "user_set_video_audio", UserFilter())
async def set_video_audio(callback: CallbackQuery):
    """Video + Audio rejimini o'rnatish"""
    await callback.answer("✅ Video + Audio rejimi tanlandi!")
    
    user = await update_user_media_preference(callback.from_user.id, 'video_audio')
    
    if user:
        try:
            await callback.message.edit_text(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"📥 <b>Media yuklash rejimi:</b> ✅ 📹 Video + Audio\n\n"
                f"Endi sizga video va audio birga yuboriladi.",
                reply_markup=get_user_settings_keyboard('video_audio')
            )
        except TelegramBadRequest:
            await callback.message.answer(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"📥 <b>Media yuklash rejimi:</b> ✅ 📹 Video + Audio\n\n"
                f"Endi sizga video va audio birga yuboriladi.",
                reply_markup=get_user_settings_keyboard('video_audio')
            )


@router.callback_query(F.data == "user_set_video_only", UserFilter())
async def set_video_only(callback: CallbackQuery):
    """Faqat Video rejimini o'rnatish"""
    await callback.answer("✅ Faqat Video rejimi tanlandi!")
    
    user = await update_user_media_preference(callback.from_user.id, 'video_only')
    
    if user:
        try:
            await callback.message.edit_text(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"📥 <b>Media yuklash rejimi:</b> ✅ 🎬 Faqat Video\n\n"
                f"Endi sizga faqat video yuboriladi.",
                reply_markup=get_user_settings_keyboard('video_only')
            )
        except TelegramBadRequest:
            await callback.message.answer(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"📥 <b>Media yuklash rejimi:</b> ✅ 🎬 Faqat Video\n\n"
                f"Endi sizga faqat video yuboriladi.",
                reply_markup=get_user_settings_keyboard('video_only')
            )


@router.callback_query(F.data == "user_set_audio_only", UserFilter())
async def set_audio_only(callback: CallbackQuery):
    """Faqat Audio rejimini o'rnatish"""
    await callback.answer("✅ Faqat Audio rejimi tanlandi!")
    
    user = await update_user_media_preference(callback.from_user.id, 'audio_only')
    
    if user:
        try:
            await callback.message.edit_text(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"📥 <b>Media yuklash rejimi:</b> ✅ 🎵 Faqat Audio\n\n"
                f"Endi sizga faqat audio yuboriladi.",
                reply_markup=get_user_settings_keyboard('audio_only')
            )
        except TelegramBadRequest:
            await callback.message.answer(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"📥 <b>Media yuklash rejimi:</b> ✅ 🎵 Faqat Audio\n\n"
                f"Endi sizga faqat audio yuboriladi.",
                reply_markup=get_user_settings_keyboard('audio_only')
            )


# Text message'lar media_router tomonidan qayta ishlanadi (musiqa qidiruv uchun)
# Bu handler o'chirildi - media_router text message'larni qabul qiladi

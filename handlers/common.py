"""
Umumiy handlerlar - barcha foydalanuvchilar uchun
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from utils import (
    get_guest_main_keyboard,
    get_user_main_keyboard,
    get_admin_main_keyboard,
    create_or_update_user,
    get_user_by_telegram_id,
    check_is_superadmin,
)
from utils.channel_utils import (
    check_all_mandatory_subscriptions,
    build_subscription_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="common")


async def _check_user_role(user_id: int) -> tuple[bool, bool]:
    """
    Foydalanuvchi rolini tekshirish (helper funksiya)
    
    Returns:
        (is_admin, is_superadmin) tuple
    """
    db_user = await get_user_by_telegram_id(user_id)
    is_admin = False
    is_superadmin = False
    
    if db_user and db_user.role in ('admin', 'superadmin'):
        is_admin = True
        is_superadmin = await check_is_superadmin(user_id)
    
    return is_admin, is_superadmin


async def _send_subscription_required_message(message_or_callback, bot, user_id: int, not_subscribed_channels: list):
    """
    Majburiy obuna talab qilingan xabarni yuborish (helper funksiya)
    """
    channels_text, keyboard_buttons = await build_subscription_keyboard(bot, not_subscribed_channels)
    
    if not keyboard_buttons:
        # Agar hech qanday tugma yaratib bo'lmasa
        text = "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:\n\n" + channels_text
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text)
        else:
            await message_or_callback.message.answer(text)
        return
    
    keyboard_buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    text = (
        f"⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:\n\n"
        f"{channels_text}\n"
        f"Obuna bo'lgach, 'Tekshirish' tugmasini bosing."
    )
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard)
    else:
        try:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            await message_or_callback.message.answer(text, reply_markup=keyboard)


@router.message(Command("start"))
async def start_handler(message: Message):
    """Start command - barcha foydalanuvchilar uchun"""
    user = message.from_user
    bot = message.bot
    
    # Foydalanuvchini saqlash yoki yangilash
    try:
        db_user = await get_user_by_telegram_id(user.id)
        user_role = db_user.role if db_user and db_user.role else None
        
        await create_or_update_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_admin=(user_role in ('admin', 'superadmin') if user_role else False),
            role=user_role,
        )
    except Exception as e:
        logger.error(f"Foydalanuvchini saqlashda xatolik: {e}")
    
    # Admin tekshiruvi
    is_admin, is_superadmin = await _check_user_role(user.id)
    
    if is_admin:
        await message.answer(
            "👑 Admin paneliga xush kelibsiz!\n\n"
            "Quyidagi funksiyalardan foydalanishingiz mumkin:",
            reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
        )
        return
    
    # Majburiy obuna tekshiruvi
    try:
        all_subscribed, not_subscribed_channels = await check_all_mandatory_subscriptions(bot, user.id)
        
        if not all_subscribed and not_subscribed_channels:
            await _send_subscription_required_message(message, bot, user.id, not_subscribed_channels)
            return
    except Exception as e:
        logger.error(f"Majburiy obuna tekshiruvida xatolik: {e}")
    
    # Oddiy foydalanuvchi
    db_user = await get_user_by_telegram_id(user.id)
    if db_user and db_user.is_active:
        await message.answer(
            "🔥 Xush kelibsiz, siz bot orqali yuklab olishingiz mumkin\n\n"
            "• Instagram - istalgan formatdagi hikoyalar, postlar va IGTV!\n\n"
            "• TikTok - istalgan formatdagi moyboyoqsiz videolar!\n\n"
            "• YouTube shorts - istalgan formatdagi videolar!\n\n"
            "• Qo'shiqni topib berishim uchun, menga quyidagilardan birini yuboring:\n\n"
            "• Qo'shiq nomi yoki ijrochi ismi\n"
            "• Ovozli xabar\n"
            "• Video\n"
            "• Audio\n"
            "• Video xabar",
            reply_markup=get_user_main_keyboard()
        )
    else:
        await message.answer(
            "🔥 Xush kelibsiz, siz bot orqali yuklab olishingiz mumkin\n\n"
            "• Instagram - istalgan formatdagi hikoyalar, postlar va IGTV!\n\n"
            "• TikTok - istalgan formatdagi moyboyoqsiz videolar!\n\n"
            "• YouTube shorts - istalgan formatdagi videolar!\n\n"
            "• Qo'shiqni topib berishim uchun, menga quyidagilardan birini yuboring:\n\n"
            "• Qo'shiq nomi yoki ijrochi ismi\n"
            "• Ovozli xabar\n"
            "• Video\n"
            "• Audio\n"
            "• Video xabar\n\n"
            "Botdan foydalanish uchun ro'yxatdan o'ting."
        )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: CallbackQuery):
    """Majburiy obuna tekshiruvi"""
    user = callback.from_user
    bot = callback.bot
    
    await callback.answer("⏳ Tekshirilmoqda...")
    
    # Admin tekshiruvi
    is_admin, is_superadmin = await _check_user_role(user.id)
    
    if is_admin:
        try:
            await callback.message.edit_text(
                "👑 Admin paneliga xush kelibsiz!\n\n"
                "Quyidagi funksiyalardan foydalanishingiz mumkin:",
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "👑 Admin paneliga xush kelibsiz!\n\n"
                "Quyidagi funksiyalardan foydalanishingiz mumkin:",
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )
        return
    
    # Majburiy obuna tekshiruvi
    try:
        all_subscribed, not_subscribed_channels = await check_all_mandatory_subscriptions(bot, user.id)
        
        if all_subscribed:
            # Barcha kanallarga obuna bo'lgan (tugmalar yo'q)
            db_user = await get_user_by_telegram_id(user.id)
            if db_user and db_user.is_active:
                text = (
                    f"✅ Barcha majburiy kanallarga obuna bo'lgansiz!\n\n"
                    f"👋 Salom, {user.first_name}!\n\n"
                    "Botga xush kelibsiz!"
                )
                try:
                    await callback.message.edit_text(text)
                except TelegramBadRequest:
                    await callback.message.answer(text)
            else:
                text = (
                    f"✅ Barcha majburiy kanallarga obuna bo'lgansiz!\n\n"
                    f"Botdan foydalanish uchun ro'yxatdan o'ting."
                )
                try:
                    await callback.message.edit_text(text)
                except TelegramBadRequest:
                    await callback.message.answer(text)
        else:
            # Hali ham obuna bo'lmagan kanallar bor
            await _send_subscription_required_message(callback, bot, user.id, not_subscribed_channels)
    except Exception as e:
        logger.error(f"Majburiy obuna tekshiruvida xatolik: {e}")
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

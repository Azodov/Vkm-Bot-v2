"""
Guest handlerlari - faqat inline keyboardlar bilan
"""

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery

from utils import (
    get_guest_main_keyboard,
    get_guest_register_keyboard,
    get_guest_info_keyboard,
    get_user_main_keyboard,
    get_inline_keyboard,
)

router = Router(name="guest")


@router.callback_query(F.data == "guest_back_to_main")
async def guest_main_menu(callback: CallbackQuery):
    """Guest asosiy menyu (tugmalar yo'q)"""
    await callback.answer()

    try:
        await callback.message.edit_text(
            f"👋 Salom, {callback.from_user.first_name}!\n\n"
            "Botga xush kelibsiz!\n\n"
            "Botdan foydalanish uchun ro'yxatdan o'ting."
        )
    except TelegramBadRequest:
        await callback.message.answer(
            f"👋 Salom, {callback.from_user.first_name}!\n\n"
            "Botga xush kelibsiz!\n\n"
            "Botdan foydalanish uchun ro'yxatdan o'ting."
        )


@router.callback_query(F.data == "guest_register")
async def show_register(callback: CallbackQuery):
    """Ro'yxatdan o'tish (tugmalar yo'q)"""
    await callback.answer()

    try:
        await callback.message.edit_text(
            "📝 Ro'yxatdan o'tish:\n\n"
            "Botdan to'liq foydalanish uchun ro'yxatdan o'ting.\n\n"
            "Ro'yxatdan o'tgandan keyin:\n"
            "✅ Botning barcha funksiyalaridan foydalanasiz\n"
            "✅ Profil ma'lumotlarini sozlaysiz\n"
            "✅ Statistika ko'rasiz\n\n"
            "Ro'yxatdan o'tishni tasdiqlash uchun /start buyrug'ini yuboring."
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "📝 Ro'yxatdan o'tish:\n\n"
            "Botdan to'liq foydalanish uchun ro'yxatdan o'ting.\n\n"
            "Ro'yxatdan o'tgandan keyin:\n"
            "✅ Botning barcha funksiyalaridan foydalanasiz\n"
            "✅ Profil ma'lumotlarini sozlaysiz\n"
            "✅ Statistika ko'rasiz\n\n"
            "Ro'yxatdan o'tishni tasdiqlash uchun /start buyrug'ini yuboring."
        )


@router.callback_query(F.data == "guest_register_confirm")
async def register_user(callback: CallbackQuery):
    """Ro'yxatdan o'tishni amalga oshirish"""
    from utils import create_or_update_user

    await callback.answer("⏳ Ro'yxatdan o'tilmoqda...")

    user = callback.from_user

    # Foydalanuvchini ma'lumotlar bazasiga qo'shish
    # Oddiy foydalanuvchilar ro'yxatdan o'tganda role='user' bo'ladi
    try:
        await create_or_update_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=True,
            is_admin=False,
            role='user',  # Oddiy foydalanuvchi
        )

        try:
            await callback.message.edit_text(
                "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
                "Endi botning barcha funksiyalaridan foydalanishingiz mumkin."
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
                "Endi botning barcha funksiyalaridan foydalanishingiz mumkin."
            )
    except Exception as e:
        await callback.message.answer(
            f"❌ Ro'yxatdan o'tishda xatolik yuz berdi: {str(e)}\n\n"
            "Qayta urinib ko'ring yoki adminlar bilan bog'laning."
        )


@router.callback_query(F.data == "guest_cancel_register")
async def cancel_register(callback: CallbackQuery):
    """Ro'yxatdan o'tishni bekor qilish (tugmalar yo'q)"""
    await callback.answer("❌ Bekor qilindi")

    try:
        await callback.message.edit_text(
            "❌ Ro'yxatdan o'tish bekor qilindi.\n\n"
            "Istalgan vaqtda qayta urinib ko'rishingiz mumkin."
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "❌ Ro'yxatdan o'tish bekor qilindi.\n\n"
            "Istalgan vaqtda qayta urinib ko'rishingiz mumkin."
        )


@router.callback_query(F.data == "guest_about")
async def show_about(callback: CallbackQuery):
    """Bot haqida (tugmalar yo'q)"""
    await callback.answer()

    try:
        await callback.message.edit_text(
            "ℹ️ Bot haqida:\n\n"
            "Bu bot sizga yordam berish uchun yaratilgan.\n\n"
            "Botdan foydalanish uchun ro'yxatdan o'ting."
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "ℹ️ Bot haqida:\n\n"
            "Bu bot sizga yordam berish uchun yaratilgan.\n\n"
            "Botdan foydalanish uchun ro'yxatdan o'ting."
        )


@router.callback_query(F.data == "guest_rules")
async def show_rules(callback: CallbackQuery):
    """Qoidalar (tugmalar yo'q)"""
    await callback.answer()
    await callback.message.answer(
        "📋 Botdan foydalanish qoidalari:\n\n"
        "1. Botdan faqat qonuniy maqsadlar uchun foydalaning\n"
        "2. Boshqa foydalanuvchilar bilan hurmatli bo'ling\n"
        "3. Bot adminlariga hurmatli bo'ling\n"
        "4. Spam xabar yubormang\n"
        "5. Qoidalarni buzmasangiz, botdan cheklanmaysiz\n\n"
        "Qoidalarni buzgan holda botdan foydalanishingiz taqiqlanadi."
    )


@router.callback_query(F.data == "guest_what_can_do")
async def show_what_can_do(callback: CallbackQuery):
    """Nima qilish mumkin? (tugmalar yo'q)"""
    await callback.answer()
    await callback.message.answer(
        "💡 Botdan nima qilish mumkin?\n\n"
        "✅ Media yuklab olish (YouTube, Instagram, TikTok)\n"
        "✅ Musiqa qidirish va yuklab olish\n"
        "✅ Voice/Video/Audio orqali musiqa aniqlash\n\n"
        "Ro'yxatdan o'ting va barcha funksiyalardan foydalaning!"
    )


@router.callback_query(F.data == "guest_help")
async def show_help(callback: CallbackQuery):
    """Yordam (tugmalar yo'q)"""
    await callback.answer()
    await callback.message.answer(
        "❓ Yordam:\n\n"
        "Botdan foydalanish:\n\n"
        "• Link yuborish orqali media yuklab olish\n"
        "• Qo'shiq nomi yuborish orqali qidirish\n"
        "• Voice, video yoki audio yuborish orqali musiqa aniqlash\n\n"
        "Agar savolingiz bo'lsa, adminlar bilan bog'laning."
    )


# Text message'lar media_router tomonidan qayta ishlanadi (musiqa qidiruv uchun)
# Bu handler o'chirildi - media_router text message'larni qabul qiladi

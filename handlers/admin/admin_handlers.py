"""
Admin handlerlari - faqat keyboardlar bilan
"""

import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from filters import AdminFilter, SuperAdminFilter
from config import config
from utils import (
    get_admin_main_keyboard,
    get_admin_stats_keyboard,
    get_admin_broadcast_keyboard,
    get_admin_broadcast_waiting_keyboard,
    get_active_users,
    get_active_users_count,
    get_inline_keyboard,
    check_is_superadmin,
)
from utils.broadcast_manager import broadcast_manager
from utils.keyboard_utils import get_admin_broadcast_running_keyboard
from utils.channel_utils import (
    add_mandatory_channel,
    remove_mandatory_channel,
    get_mandatory_channels,
    get_mandatory_channel,
    toggle_channel_status,
)
from utils.keyboard_utils import (
    get_mandatory_channels_keyboard,
    get_mandatory_channels_list_keyboard,
    get_channel_manage_keyboard,
)

router = Router(name="admin")


class BroadcastStates(StatesGroup):
    """Broadcast xabar holatlari"""
    waiting_message = State()


class AdminManageStates(StatesGroup):
    """Admin boshqarish holatlari"""
    waiting_admin_id = State()


class ChannelManageStates(StatesGroup):
    """Majburiy obuna kanallari boshqarish holatlari"""
    waiting_channel = State()


@router.callback_query(F.data == "admin_back_to_main", AdminFilter())
async def admin_panel(callback: CallbackQuery):
    """Admin panel"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    # Superadmin tekshiruvi
    is_superadmin = await check_is_superadmin(callback.from_user.id)
    
    try:
        await callback.message.edit_text(
            "👑 Admin paneliga xush kelibsiz!\n\n"
            "Quyidagi funksiyalardan foydalanishingiz mumkin:",
            reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
        )
    except TelegramBadRequest as e:
        # Agar xabar o'zgarishmayotgan bo'lsa, shunchaki qaytaradi
        if "message is not modified" not in str(e):
            await callback.message.answer(
                "👑 Admin paneliga xush kelibsiz!\n\n"
                "Quyidagi funksiyalardan foydalanishingiz mumkin:",
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )


@router.callback_query(F.data == "admin_stats", AdminFilter())
async def show_stats(callback: CallbackQuery):
    """Bot statistikasi"""
    from aiogram.exceptions import TelegramBadRequest
    from utils import get_users_count, get_active_users_count
    
    await callback.answer()
    
    try:
        total_users = await get_users_count()
        active_users = await get_active_users_count()
    except Exception as e:
        total_users = 0
        active_users = 0
    
    try:
        await callback.message.edit_text(
            "📊 Bot statistikasi:\n\n"
            f"👥 Jami foydalanuvchilar: {total_users}\n"
            f"✅ Faol foydalanuvchilar: {active_users}\n"
            f"💬 Jami xabarlar: 0\n"
            f"📅 Bugungi faollik: 0",
            reply_markup=get_admin_stats_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "📊 Bot statistikasi:\n\n"
            f"👥 Jami foydalanuvchilar: {total_users}\n"
            f"✅ Faol foydalanuvchilar: {active_users}\n"
            f"💬 Jami xabarlar: 0\n"
            f"📅 Bugungi faollik: 0",
            reply_markup=get_admin_stats_keyboard()
        )


@router.callback_query(F.data == "admin_refresh_stats", AdminFilter())
async def refresh_stats(callback: CallbackQuery):
    """Statistikani yangilash"""
    from aiogram.exceptions import TelegramBadRequest
    from utils import get_users_count, get_active_users_count
    
    await callback.answer("🔄 Yangilanmoqda...")
    
    try:
        total_users = await get_users_count()
        active_users = await get_active_users_count()
    except Exception as e:
        total_users = 0
        active_users = 0
    
    try:
        await callback.message.edit_text(
            "📊 Bot statistikasi:\n\n"
            f"👥 Jami foydalanuvchilar: {total_users}\n"
            f"✅ Faol foydalanuvchilar: {active_users}\n"
            f"💬 Jami xabarlar: 0\n"
            f"📅 Bugungi faollik: 0",
            reply_markup=get_admin_stats_keyboard()
        )
    except TelegramBadRequest as e:
        # Agar xabar o'zgarishmayotgan bo'lsa, shunchaki qaytaradi
        if "message is not modified" in str(e):
            await callback.answer("ℹ️ Ma'lumotlar o'zgarmadi")
        else:
            raise


@router.callback_query(F.data == "admin_detailed_stats", AdminFilter())
async def detailed_stats(callback: CallbackQuery):
    """Batafsil statistika"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "📈 Batafsil statistika:\n\n"
            "Bu yerda batafsil statistika ko'rsatiladi...",
            reply_markup=get_inline_keyboard([
                [("🔙 Orqaga", "admin_stats")],
            ])
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "📈 Batafsil statistika:\n\n"
            "Bu yerda batafsil statistika ko'rsatiladi...",
            reply_markup=get_inline_keyboard([
                [("🔙 Orqaga", "admin_stats")],
            ])
        )
@router.callback_query(F.data == "admin_broadcast", AdminFilter())
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast xabar yuborishni boshlash"""
    from aiogram.exceptions import TelegramBadRequest
    from utils import get_admin_broadcast_waiting_keyboard
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "📢 Broadcast xabar yuborish\n\n"
            "Yuborish kerak bo'lgan xabar matnini kiriting:\n\n"
            "ℹ️ Xabar matni yoki rasm/video/hujjat yuborishingiz mumkin.\n"
            "❌ Bekor qilish va chiqish uchun tugmani bosing:",
            reply_markup=get_admin_broadcast_waiting_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "📢 Broadcast xabar yuborish\n\n"
            "Yuborish kerak bo'lgan xabar matnini kiriting:\n\n"
            "ℹ️ Xabar matni yoki rasm/video/hujjat yuborishingiz mumkin.\n"
            "❌ Bekor qilish va chiqish uchun tugmani bosing:",
            reply_markup=get_admin_broadcast_waiting_keyboard()
        )
    
    await state.set_state(BroadcastStates.waiting_message)


@router.message(BroadcastStates.waiting_message, AdminFilter())
async def process_broadcast_message(message: Message, state: FSMContext):
    """Broadcast xabarni qayta ishlash"""
    from utils import get_active_users_count, get_admin_broadcast_waiting_keyboard
    
    # Xabar matnini olish (text yoki caption)
    text = message.text or message.caption or ""
    
    # Agar media bo'lsa, media file_id ni saqlash
    media_data = None
    if message.photo:
        media_data = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        media_data = {"type": "video", "file_id": message.video.file_id}
    elif message.document:
        media_data = {"type": "document", "file_id": message.document.file_id}
    elif message.audio:
        media_data = {"type": "audio", "file_id": message.audio.file_id}
    
    try:
        users_count = await get_active_users_count()
    except:
        users_count = 0
    
    await state.update_data(
        broadcast_message=text,
        broadcast_media=media_data
    )
    
    preview_text = f"📢 Xabar matni:\n\n{text}\n\n" if text else "📢 Xabar (media)\n\n"
    preview_text += f"👥 Xabar {users_count} ta faol foydalanuvchiga yuboriladi.\n\n"
    preview_text += "Ushbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?"
    
    await message.answer(
        preview_text,
        reply_markup=get_admin_broadcast_keyboard()
    )


@router.callback_query(F.data == "admin_confirm_broadcast", BroadcastStates.waiting_message, AdminFilter())
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast xabarni tasdiqlash - optimallashtirilgan va to'xtatish bilan"""
    # Superadmin tekshiruvi
    is_superadmin = await check_is_superadmin(callback.from_user.id)
    
    data = await state.get_data()
    broadcast_message = data.get("broadcast_message")
    
    if not broadcast_message:
        await callback.answer("❌ Xabar topilmadi", show_alert=True)
        await state.clear()
        return
    
    # Agar allaqachon broadcast ishlamoqda bo'lsa
    if await broadcast_manager.is_broadcast_running():
        await callback.answer("⚠️ Broadcast allaqachon ishlamoqda!", show_alert=True)
        return
    
    await callback.answer("✅ Xabar yuborilmoqda...")
    
    # Status xabari yuborish
    status_msg = await callback.message.answer(
        "⏳ Xabar yuborilmoqda...\n\n0 ta yuborildi",
        reply_markup=get_admin_broadcast_running_keyboard()
    )
    
    # Broadcast jarayonini boshlash
    stop_event = await broadcast_manager.start_broadcast({
        "status_msg": status_msg,
        "callback": callback,
        "is_superadmin": is_superadmin,
    })
    
    try:
        # Barcha faol foydalanuvchilarni olish
        users = await get_active_users(limit=10000)  # Katta limit
        
        bot = callback.bot
        sent_count = 0
        failed_count = 0
        total = len(users)
        
        if total == 0:
            await status_msg.edit_text("❌ Faol foydalanuvchilar topilmadi!")
            await state.clear()
            await broadcast_manager.clear_broadcast()
            return
        
        # Media ma'lumotlarni olish
        media_data = data.get("broadcast_media")
        
        # Xabar yuborish funksiyasi (kod takrorlashini oldini olish uchun)
        async def send_to_user(user_telegram_id: int) -> bool:
            """Foydalanuvchiga xabar yuborish - optimallashtirilgan"""
            try:
                if media_data:
                    if media_data["type"] == "photo":
                        await bot.send_photo(
                            chat_id=user_telegram_id,
                            photo=media_data["file_id"],
                            caption=broadcast_message if broadcast_message else None
                        )
                    elif media_data["type"] == "video":
                        await bot.send_video(
                            chat_id=user_telegram_id,
                            video=media_data["file_id"],
                            caption=broadcast_message if broadcast_message else None
                        )
                    elif media_data["type"] == "document":
                        await bot.send_document(
                            chat_id=user_telegram_id,
                            document=media_data["file_id"],
                            caption=broadcast_message if broadcast_message else None
                        )
                    elif media_data["type"] == "audio":
                        await bot.send_audio(
                            chat_id=user_telegram_id,
                            audio=media_data["file_id"],
                            caption=broadcast_message if broadcast_message else None
                        )
                else:
                    if broadcast_message:
                        await bot.send_message(
                            chat_id=user_telegram_id,
                            text=broadcast_message
                        )
                    else:
                        return False
                return True
            except (TelegramForbiddenError, TelegramBadRequest):
                return False
            except Exception:
                return False
        
        # Har bir foydalanuvchiga xabar yuborish
        last_status_update = 0.0
        stopped = False
        
        for idx, user in enumerate(users, 1):
            # To'xtatish tekshiruvi
            if stop_event.is_set():
                stopped = True
                logger.info(f"Broadcast to'xtatildi: {sent_count}/{total} yuborildi")
                break
            
            # Xabar yuborish
            success = await send_to_user(user.telegram_id)
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
            
            # Status yangilash - har 10 ta yoki oxirgi xabarda
            # Tez ishlash uchun kamroq yangilash
            if idx % 10 == 0 or idx == total:
                current_time = asyncio.get_event_loop().time()
                # Faqat 1 sekunddan keyin yangilash (spam oldini olish uchun)
                if current_time - last_status_update > 1.0 or idx == total:
                    try:
                        status_text = (
                            f"⏸️ Broadcast to'xtatilmoqda...\n\n" if stop_event.is_set() else
                            f"⏳ Xabar yuborilmoqda...\n\n"
                        )
                        await status_msg.edit_text(
                            f"{status_text}"
                            f"✅ Yuborildi: {sent_count}/{total}\n"
                            f"❌ Xatolik: {failed_count}\n"
                            f"📊 Progress: {(idx/total*100):.1f}%",
                            reply_markup=get_admin_broadcast_running_keyboard()
                        )
                        last_status_update = current_time
                    except:
                        pass
            
            # Rate limit uchun optimallashtirilgan delay
            # Telegram API: 30 msg/sec limit
            # Config'dan o'qiladi
            from config import config
            if idx % 20 == 0:
                # Har 20 ta xabardan keyin qo'shimcha kutish
                await asyncio.sleep(config.bot.broadcast_batch_delay)
            else:
                # Oddiy delay (config'dan)
                await asyncio.sleep(config.bot.broadcast_rate_limit)
        
        # Natijani ko'rsatish
        if stopped:
            result_text = (
                f"⏸️ Broadcast to'xtatildi!\n\n"
                f"📊 Natijalar:\n"
                f"✅ Muvaffaqiyatli: {sent_count}\n"
                f"❌ Xatolik: {failed_count}\n"
                f"📊 Jami: {total}\n"
                f"⏹️ To'xtatilgan: {total - sent_count - failed_count} ta yuborilmadi"
            )
        else:
            result_text = (
                f"✅ Broadcast yakunlandi!\n\n"
                f"📊 Natijalar:\n"
                f"✅ Muvaffaqiyatli: {sent_count}\n"
                f"❌ Xatolik: {failed_count}\n"
                f"📊 Jami: {total}"
            )
        
        try:
            await callback.message.edit_text(
                result_text,
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )
        except TelegramBadRequest:
            # Agar edit qila olmasa, yangi xabar yuborish
            await callback.message.answer(
                result_text,
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )
        
        # Status xabarini yangilash
        await status_msg.edit_text(result_text)
        
    except Exception as e:
        # Xatoni ko'rsatish - eski xabarni yangilash
        try:
            await callback.message.edit_text(
                f"❌ Broadcast xatosi:\n{str(e)}",
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )
        except TelegramBadRequest:
            # Agar edit qila olmasa, yangi xabar yuborish
            await callback.message.answer(
                f"❌ Broadcast xatosi:\n{str(e)}",
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )
        
        # Status xabarini yangilash
        try:
            await status_msg.edit_text(
                f"❌ Broadcast xatosi:\n{str(e)}"
            )
        except:
            pass
    finally:
        # Broadcast holatini tozalash
        await broadcast_manager.clear_broadcast()
    
    await state.clear()


@router.callback_query(F.data == "admin_cancel_broadcast", AdminFilter())
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast xabarni bekor qilish"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer("❌ Bekor qilindi")
    
    # State'dan chiqish
    await state.clear()
    
    # Superadmin tekshiruvi
    is_superadmin = await check_is_superadmin(callback.from_user.id)
    
    # Xabarni yangilash - eski xabarni edit qilish
    try:
        await callback.message.edit_text(
            "❌ Broadcast bekor qilindi.\n\n"
            "Xabar yuborilmadi. Asosiy menyuga qaytildi.",
            reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
        )
    except TelegramBadRequest:
        # Agar edit qila olmasa, yangi xabar yuborish
        await callback.message.answer(
            "❌ Broadcast bekor qilindi.\n\n"
            "Xabar yuborilmadi. Asosiy menyuga qaytildi.",
            reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
        )


@router.callback_query(F.data == "admin_stop_broadcast", AdminFilter())
async def stop_broadcast(callback: CallbackQuery):
    """Broadcast jarayonini to'xtatish"""
    from aiogram.exceptions import TelegramBadRequest
    
    # Broadcast to'xtatish
    stopped = await broadcast_manager.stop_broadcast()
    
    if stopped:
        await callback.answer("⏹️ Broadcast to'xtatilmoqda...", show_alert=True)
        
        # Broadcast ma'lumotlarini olish
        broadcast_data = await broadcast_manager.get_broadcast_data()
        if broadcast_data:
            try:
                status_msg = broadcast_data.get("status_msg")
                if status_msg:
                    await status_msg.edit_text(
                        "⏸️ Broadcast to'xtatilmoqda...\n\n"
                        "Iltimos, kuting..."
                    )
            except:
                pass
    else:
        await callback.answer("⚠️ Broadcast ishlamayapti", show_alert=True)


@router.callback_query(F.data == "admin_settings", AdminFilter())
async def settings(callback: CallbackQuery):
    """Sozlamalar"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "⚙️ Sozlamalar:\n\n"
            "Bu yerda bot sozlamalari bo'ladi...",
            reply_markup=get_inline_keyboard([
                [("🔙 Asosiy menyu", "admin_back_to_main")],
            ])
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "⚙️ Sozlamalar:\n\n"
            "Bu yerda bot sozlamalari bo'ladi...",
            reply_markup=get_inline_keyboard([
                [("🔙 Asosiy menyu", "admin_back_to_main")],
            ])
        )


@router.callback_query(F.data == "admin_back_to_main", AdminFilter())
async def back_to_main(callback: CallbackQuery):
    """Asosiy menyuga qaytish"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    # Superadmin tekshiruvi
    is_superadmin = await check_is_superadmin(callback.from_user.id)
    
    try:
        await callback.message.edit_text(
            "👑 Admin paneliga xush kelibsiz!\n\n"
            "Quyidagi funksiyalardan foydalanishingiz mumkin:",
            reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
        )
    except TelegramBadRequest as e:
        # Agar xabar o'zgarishmayotgan bo'lsa, shunchaki qaytaradi
        if "message is not modified" not in str(e):
            await callback.message.answer(
                "👑 Admin paneliga xush kelibsiz!\n\n"
                "Quyidagi funksiyalardan foydalanishingiz mumkin:",
                reply_markup=get_admin_main_keyboard(is_superadmin=is_superadmin)
            )


@router.callback_query(F.data == "admin_manage_admins", SuperAdminFilter())
async def manage_admins(callback: CallbackQuery):
    """Adminlarni boshqarish (faqat superadminlar uchun)"""
    from aiogram.exceptions import TelegramBadRequest
    from utils import get_admins, get_user_by_telegram_id
    
    await callback.answer()
    
    try:
        admins = await get_admins()
        admin_text = "👥 Adminlar ro'yxati:\n\n"
        
        if not admins:
            admin_text += "❌ Hozircha adminlar yo'q.\n\n"
        else:
            for idx, admin in enumerate(admins, 1):
                name = admin.first_name or "Noma'lum"
                username = f"@{admin.username}" if admin.username else "Username yo'q"
                admin_text += f"{idx}. {name} ({username})\n"
                admin_text += f"   ID: {admin.telegram_id}\n\n"
        
        admin_text += "Quyidagi amallarni bajaring:"
        
        buttons = []
        if admins:
            for admin in admins:
                name = admin.first_name or "Noma'lum"
                buttons.append([(f"❌ {name} ni olib tashlash", f"admin_remove_{admin.telegram_id}")])
        buttons.append([("➕ Admin qo'shish", "admin_add_new")])
        buttons.append([("🔙 Asosiy menyu", "admin_back_to_main")])
        
        await callback.message.edit_text(
            admin_text,
            reply_markup=get_inline_keyboard(buttons)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            admin_text,
            reply_markup=get_inline_keyboard(buttons)
        )


@router.callback_query(F.data == "admin_add_new", SuperAdminFilter())
async def add_new_admin(callback: CallbackQuery, state: FSMContext):
    """Yangi admin qo'shish (faqat superadminlar uchun)"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "➕ Admin qo'shish\n\n"
            "Yangi adminning Telegram ID raqamini yuboring:\n\n"
            "ℹ️ ID ni olish uchun [@userinfobot](https://t.me/userinfobot) dan foydalaning.",
            reply_markup=get_inline_keyboard([
                [("❌ Bekor qilish", "admin_manage_admins")],
            ]),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "➕ Admin qo'shish\n\n"
            "Yangi adminning Telegram ID raqamini yuboring:\n\n"
            "ℹ️ ID ni olish uchun [@userinfobot](https://t.me/userinfobot) dan foydalaning.",
            reply_markup=get_inline_keyboard([
                [("❌ Bekor qilish", "admin_manage_admins")],
            ]),
            parse_mode="Markdown"
        )
    
    await state.set_state(AdminManageStates.waiting_admin_id)


@router.message(StateFilter(AdminManageStates.waiting_admin_id), lambda m: m.text and m.text.isdigit(), SuperAdminFilter())
async def process_admin_id(message: Message, state: FSMContext):
    """Admin ID ni qayta ishlash"""
    from utils import get_user_by_telegram_id, add_admin, set_user_role
    
    try:
        admin_id = int(message.text)
        
        # Foydalanuvchini topish
        user = await get_user_by_telegram_id(admin_id)
        
        if not user:
            await message.answer(
                "❌ Bu ID ga ega foydalanuvchi topilmadi.\n\n"
                "Foydalanuvchi avval botda /start buyrug'ini ishlatishi kerak.",
                reply_markup=get_inline_keyboard([
                    [("🔄 Qayta urinish", "admin_add_new")],
                    [("🔙 Orqaga", "admin_manage_admins")],
                ])
            )
            await state.clear()
            return
        
        # Admin qilish
        updated_user = await add_admin(admin_id)
        
        if updated_user:
            await message.answer(
                f"✅ {updated_user.first_name or 'Foydalanuvchi'} admin qilindi!\n\n"
                f"ID: {admin_id}",
                reply_markup=get_inline_keyboard([
                    [("🔙 Adminlar ro'yxati", "admin_manage_admins")],
                ])
            )
        else:
            await message.answer(
                "❌ Xatolik yuz berdi.",
                reply_markup=get_inline_keyboard([
                    [("🔄 Qayta urinish", "admin_add_new")],
                    [("🔙 Orqaga", "admin_manage_admins")],
                ])
            )
        
        await state.clear()
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri ID format.\n\n"
            "Iltimos, faqat raqam kiriting.",
            reply_markup=get_inline_keyboard([
                [("🔄 Qayta urinish", "admin_add_new")],
                [("🔙 Orqaga", "admin_manage_admins")],
            ])
        )
    except Exception as e:
        await message.answer(
            f"❌ Xatolik: {str(e)}",
            reply_markup=get_inline_keyboard([
                [("🔄 Qayta urinish", "admin_add_new")],
                [("🔙 Orqaga", "admin_manage_admins")],
            ])
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin_remove_"), SuperAdminFilter())
async def remove_admin_handler(callback: CallbackQuery):
    """Adminni olib tashlash (faqat superadminlar uchun)"""
    from aiogram.exceptions import TelegramBadRequest
    from utils import remove_admin, get_user_by_telegram_id
    
    await callback.answer()
    
    try:
        # ID ni olish
        admin_id = int(callback.data.split("_")[-1])
        
        # Adminni olib tashlash
        updated_user = await remove_admin(admin_id)
        
        if updated_user:
            name = updated_user.first_name or "Foydalanuvchi"
            await callback.message.edit_text(
                f"✅ {name} dan admin huquqi olib tashlandi!\n\n"
                f"ID: {admin_id}",
                reply_markup=get_inline_keyboard([
                    [("🔙 Adminlar ro'yxati", "admin_manage_admins")],
                ])
            )
        else:
            await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
    except TelegramBadRequest:
        pass
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


# ==================== MANDATORY CHANNELS HANDLERS ====================

@router.callback_query(F.data == "admin_mandatory_channels", AdminFilter())
async def mandatory_channels_menu(callback: CallbackQuery):
    """Majburiy obuna kanallari menyusi"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "📢 Majburiy obuna kanallari va guruhlari\n\n"
            "Bu yerda majburiy obuna kanallarini va guruhlarini boshqarishingiz mumkin.\n\n"
            "Foydalanuvchilar botdan foydalanishdan oldin barcha majburiy kanallarga obuna bo'lishlari kerak.",
            reply_markup=get_mandatory_channels_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "📢 Majburiy obuna kanallari va guruhlari\n\n"
            "Bu yerda majburiy obuna kanallarini va guruhlarini boshqarishingiz mumkin.\n\n"
            "Foydalanuvchilar botdan foydalanishdan oldin barcha majburiy kanallarga obuna bo'lishlari kerak.",
            reply_markup=get_mandatory_channels_keyboard()
        )


@router.callback_query(F.data == "admin_add_channel", AdminFilter())
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    """Kanal qo'shishni boshlash"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "➕ Majburiy obuna kanali qo'shish\n\n"
            "Kanal yoki guruhni forward qiling yoki kanal ID/username ni yuboring:\n\n"
            "ℹ️ Misol:\n"
            "• @channel_username\n"
            "• -1001234567890 (kanal ID)\n"
            "• Kanal yoki guruhdan xabar forward qiling\n\n"
            "❌ Bekor qilish uchun tugmani bosing:",
            reply_markup=get_inline_keyboard([
                [("❌ Bekor qilish", "admin_mandatory_channels")],
            ])
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "➕ Majburiy obuna kanali qo'shish\n\n"
            "Kanal yoki guruhni forward qiling yoki kanal ID/username ni yuboring:\n\n"
            "ℹ️ Misol:\n"
            "• @channel_username\n"
            "• -1001234567890 (kanal ID)\n"
            "• Kanal yoki guruhdan xabar forward qiling\n\n"
            "❌ Bekor qilish uchun tugmani bosing:",
            reply_markup=get_inline_keyboard([
                [("❌ Bekor qilish", "admin_mandatory_channels")],
            ])
        )
    
    await state.set_state(ChannelManageStates.waiting_channel)


@router.message(ChannelManageStates.waiting_channel, AdminFilter())
async def process_channel_add(message: Message, state: FSMContext):
    """Kanal qo'shishni qayta ishlash"""
    from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
    
    bot = message.bot
    
    # Forward qilingan xabardan kanal ma'lumotlarini olish
    if message.forward_from_chat:
        chat = message.forward_from_chat
        channel_id = chat.id
        channel_username = chat.username
        channel_title = chat.title
        channel_type = "channel" if chat.type == "channel" else "group"
        
        try:
            # Bot kanalda admin ekanligini tekshirish
            bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
            if bot_member.status not in ('administrator', 'creator'):
                await message.answer(
                    "❌ Bot kanalda admin bo'lishi kerak!\n\n"
                    "Iltimos, avval botni kanalga admin qiling.",
                    reply_markup=get_inline_keyboard([
                        [("🔄 Qayta urinish", "admin_add_channel")],
                        [("🔙 Orqaga", "admin_mandatory_channels")],
                    ])
                )
                await state.clear()
                return
        except TelegramAPIError as e:
            await message.answer(
                f"❌ Xatolik: {str(e)}\n\n"
                "Kanal ID ni to'g'ri kiriting yoki botni kanalga admin qiling.",
                reply_markup=get_inline_keyboard([
                    [("🔄 Qayta urinish", "admin_add_channel")],
                    [("🔙 Orqaga", "admin_mandatory_channels")],
                ])
            )
            await state.clear()
            return
        
        # Kanalni qo'shish
        channel = await add_mandatory_channel(
            channel_id=channel_id,
            channel_username=channel_username,
            channel_title=channel_title,
            channel_type=channel_type
        )
        
        if channel:
            await message.answer(
                f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
                f"📢 Kanal: {channel_title or channel_username or f'ID: {channel_id}'}\n"
                f"🆔 ID: {channel_id}\n"
                f"📝 Turi: {channel_type}",
                reply_markup=get_inline_keyboard([
                    [("📋 Kanallar ro'yxati", "admin_list_channels")],
                    [("🔙 Asosiy menyu", "admin_mandatory_channels")],
                ])
            )
        else:
            await message.answer(
                "❌ Kanal qo'shishda xatolik yuz berdi.",
                reply_markup=get_inline_keyboard([
                    [("🔄 Qayta urinish", "admin_add_channel")],
                    [("🔙 Orqaga", "admin_mandatory_channels")],
                ])
            )
        
        await state.clear()
        return
    
    # Text orqali kanal ID yoki username
    text = message.text.strip()
    
    # Username format (@channel)
    if text.startswith('@'):
        username = text[1:]
        try:
            chat = await bot.get_chat(f"@{username}")
            channel_id = chat.id
            channel_username = chat.username
            channel_title = chat.title
            channel_type = "channel" if chat.type == "channel" else "group"
            
            # Bot kanalda admin ekanligini tekshirish
            try:
                bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
                if bot_member.status not in ('administrator', 'creator'):
                    await message.answer(
                        "❌ Bot kanalda admin bo'lishi kerak!\n\n"
                        "Iltimos, avval botni kanalga admin qiling.",
                        reply_markup=get_inline_keyboard([
                            [("🔄 Qayta urinish", "admin_add_channel")],
                            [("🔙 Orqaga", "admin_mandatory_channels")],
                        ])
                    )
                    await state.clear()
                    return
            except TelegramAPIError:
                await message.answer(
                    "❌ Bot kanalga kirish huquqiga ega emas yoki kanalda admin emas.\n\n"
                    "Iltimos, botni kanalga admin qiling.",
                    reply_markup=get_inline_keyboard([
                        [("🔄 Qayta urinish", "admin_add_channel")],
                        [("🔙 Orqaga", "admin_mandatory_channels")],
                    ])
                )
                await state.clear()
                return
            
            # Kanalni qo'shish
            channel = await add_mandatory_channel(
                channel_id=channel_id,
                channel_username=channel_username,
                channel_title=channel_title,
                channel_type=channel_type
            )
            
            if channel:
                await message.answer(
                    f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
                    f"📢 Kanal: {channel_title or channel_username or f'ID: {channel_id}'}\n"
                    f"🆔 ID: {channel_id}\n"
                    f"📝 Turi: {channel_type}",
                    reply_markup=get_inline_keyboard([
                        [("📋 Kanallar ro'yxati", "admin_list_channels")],
                        [("🔙 Asosiy menyu", "admin_mandatory_channels")],
                    ])
                )
            else:
                await message.answer(
                    "❌ Kanal qo'shishda xatolik yuz berdi.",
                    reply_markup=get_inline_keyboard([
                        [("🔄 Qayta urinish", "admin_add_channel")],
                        [("🔙 Orqaga", "admin_mandatory_channels")],
                    ])
                )
        except TelegramAPIError as e:
            await message.answer(
                f"❌ Kanal topilmadi yoki xatolik: {str(e)}\n\n"
                "Iltimos, to'g'ri kanal username yoki ID kiriting.",
                reply_markup=get_inline_keyboard([
                    [("🔄 Qayta urinish", "admin_add_channel")],
                    [("🔙 Orqaga", "admin_mandatory_channels")],
                ])
            )
        await state.clear()
        return
    
    # ID format (manfiy raqam)
    if text.lstrip('-').isdigit():
        try:
            channel_id = int(text)
            chat = await bot.get_chat(channel_id)
            channel_username = chat.username
            channel_title = chat.title
            channel_type = "channel" if chat.type == "channel" else "group"
            
            # Bot kanalda admin ekanligini tekshirish
            try:
                bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
                if bot_member.status not in ('administrator', 'creator'):
                    await message.answer(
                        "❌ Bot kanalda admin bo'lishi kerak!\n\n"
                        "Iltimos, avval botni kanalga admin qiling.",
                        reply_markup=get_inline_keyboard([
                            [("🔄 Qayta urinish", "admin_add_channel")],
                            [("🔙 Orqaga", "admin_mandatory_channels")],
                        ])
                    )
                    await state.clear()
                    return
            except TelegramAPIError:
                await message.answer(
                    "❌ Bot kanalga kirish huquqiga ega emas yoki kanalda admin emas.\n\n"
                    "Iltimos, botni kanalga admin qiling.",
                    reply_markup=get_inline_keyboard([
                        [("🔄 Qayta urinish", "admin_add_channel")],
                        [("🔙 Orqaga", "admin_mandatory_channels")],
                    ])
                )
                await state.clear()
                return
            
            # Kanalni qo'shish
            channel = await add_mandatory_channel(
                channel_id=channel_id,
                channel_username=channel_username,
                channel_title=channel_title,
                channel_type=channel_type
            )
            
            if channel:
                await message.answer(
                    f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
                    f"📢 Kanal: {channel_title or channel_username or f'ID: {channel_id}'}\n"
                    f"🆔 ID: {channel_id}\n"
                    f"📝 Turi: {channel_type}",
                    reply_markup=get_inline_keyboard([
                        [("📋 Kanallar ro'yxati", "admin_list_channels")],
                        [("🔙 Asosiy menyu", "admin_mandatory_channels")],
                    ])
                )
            else:
                await message.answer(
                    "❌ Kanal qo'shishda xatolik yuz berdi.",
                    reply_markup=get_inline_keyboard([
                        [("🔄 Qayta urinish", "admin_add_channel")],
                        [("🔙 Orqaga", "admin_mandatory_channels")],
                    ])
                )
        except TelegramAPIError as e:
            await message.answer(
                f"❌ Kanal topilmadi yoki xatolik: {str(e)}\n\n"
                "Iltimos, to'g'ri kanal ID kiriting.",
                reply_markup=get_inline_keyboard([
                    [("🔄 Qayta urinish", "admin_add_channel")],
                    [("🔙 Orqaga", "admin_mandatory_channels")],
                ])
            )
        await state.clear()
        return
    
    # Noto'g'ri format
    await message.answer(
        "❌ Noto'g'ri format!\n\n"
        "Iltimos, quyidagi formatlardan birini ishlating:\n"
        "• @channel_username\n"
        "• -1001234567890 (kanal ID)\n"
        "• Kanal yoki guruhdan xabar forward qiling",
        reply_markup=get_inline_keyboard([
            [("🔄 Qayta urinish", "admin_add_channel")],
            [("🔙 Orqaga", "admin_mandatory_channels")],
        ])
    )


@router.callback_query(F.data == "admin_list_channels", AdminFilter())
async def list_channels(callback: CallbackQuery):
    """Kanallar ro'yxatini ko'rsatish"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    channels = await get_mandatory_channels(active_only=False)
    
    if not channels:
        try:
            await callback.message.edit_text(
                "📋 Majburiy obuna kanallari ro'yxati:\n\n"
                "❌ Hozircha kanallar yo'q.\n\n"
                "Kanal qo'shish uchun quyidagi tugmani bosing:",
                reply_markup=get_mandatory_channels_keyboard()
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "📋 Majburiy obuna kanallari ro'yxati:\n\n"
                "❌ Hozircha kanallar yo'q.\n\n"
                "Kanal qo'shish uchun quyidagi tugmani bosing:",
                reply_markup=get_mandatory_channels_keyboard()
            )
        return
    
    text = "📋 Majburiy obuna kanallari ro'yxati:\n\n"
    for idx, channel in enumerate(channels, 1):
        status = "✅ Faol" if channel.is_active else "❌ Nofaol"
        channel_name = channel.channel_title or channel.channel_username or f"ID: {channel.channel_id}"
        text += f"{idx}. {channel_name}\n"
        text += f"   {status} | {channel.channel_type}\n"
        if channel.channel_username:
            text += f"   @{channel.channel_username}\n"
        text += f"   ID: {channel.channel_id}\n\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_mandatory_channels_list_keyboard(channels)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=get_mandatory_channels_list_keyboard(channels)
        )


@router.callback_query(F.data.startswith("admin_channel_"), AdminFilter())
async def channel_manage(callback: CallbackQuery):
    """Kanal boshqarish"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        channel_id = int(callback.data.split("_")[-1])
        channel = await get_mandatory_channel(channel_id)
        
        if not channel:
            await callback.answer("❌ Kanal topilmadi", show_alert=True)
            return
        
        status = "✅ Faol" if channel.is_active else "❌ Nofaol"
        channel_name = channel.channel_title or channel.channel_username or f"ID: {channel_id}"
        
        text = f"📢 Kanal ma'lumotlari:\n\n"
        text += f"📝 Nomi: {channel_name}\n"
        text += f"🆔 ID: {channel_id}\n"
        text += f"📝 Turi: {channel.channel_type}\n"
        text += f"📊 Holati: {status}\n"
        if channel.channel_username:
            text += f"🔗 Username: @{channel.channel_username}\n"
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_channel_manage_keyboard(channel_id)
            )
        except TelegramBadRequest:
            await callback.message.answer(
                text,
                reply_markup=get_channel_manage_keyboard(channel_id)
            )
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("admin_delete_channel_"), AdminFilter())
async def delete_channel(callback: CallbackQuery):
    """Kanalni o'chirish"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        channel_id = int(callback.data.split("_")[-1])
        channel = await get_mandatory_channel(channel_id)
        
        if not channel:
            await callback.answer("❌ Kanal topilmadi", show_alert=True)
            return
        
        channel_name = channel.channel_title or channel.channel_username or f"ID: {channel_id}"
        
        success = await remove_mandatory_channel(channel_id)
        
        if success:
            try:
                await callback.message.edit_text(
                    f"✅ Kanal o'chirildi!\n\n"
                    f"📢 Kanal: {channel_name}\n"
                    f"🆔 ID: {channel_id}",
                    reply_markup=get_inline_keyboard([
                        [("📋 Kanallar ro'yxati", "admin_list_channels")],
                        [("🔙 Asosiy menyu", "admin_mandatory_channels")],
                    ])
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"✅ Kanal o'chirildi!\n\n"
                    f"📢 Kanal: {channel_name}\n"
                    f"🆔 ID: {channel_id}",
                    reply_markup=get_inline_keyboard([
                        [("📋 Kanallar ro'yxati", "admin_list_channels")],
                        [("🔙 Asosiy menyu", "admin_mandatory_channels")],
                    ])
                )
        else:
            await callback.answer("❌ Kanal o'chirishda xatolik", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("admin_toggle_channel_"), AdminFilter())
async def toggle_channel(callback: CallbackQuery):
    """Kanal faolligini o'zgartirish"""
    from aiogram.exceptions import TelegramBadRequest
    
    await callback.answer()
    
    try:
        channel_id = int(callback.data.split("_")[-1])
        channel = await get_mandatory_channel(channel_id)
        
        if not channel:
            await callback.answer("❌ Kanal topilmadi", show_alert=True)
            return
        
        success = await toggle_channel_status(channel_id)
        
        if success:
            # Yangilangan kanalni olish
            updated_channel = await get_mandatory_channel(channel_id)
            status = "✅ Faol" if updated_channel.is_active else "❌ Nofaol"
            channel_name = updated_channel.channel_title or updated_channel.channel_username or f"ID: {channel_id}"
            
            try:
                await callback.message.edit_text(
                    f"✅ Kanal holati o'zgartirildi!\n\n"
                    f"📢 Kanal: {channel_name}\n"
                    f"📊 Yangi holati: {status}",
                    reply_markup=get_channel_manage_keyboard(channel_id)
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"✅ Kanal holati o'zgartirildi!\n\n"
                    f"📢 Kanal: {channel_name}\n"
                    f"📊 Yangi holati: {status}",
                    reply_markup=get_channel_manage_keyboard(channel_id)
                )
        else:
            await callback.answer("❌ Kanal holatini o'zgartirishda xatolik", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
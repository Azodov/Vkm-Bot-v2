"""
Group handlerlari - guruhlar uchun
"""

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR

router = Router(name="group")


def get_group_start_keyboard() -> InlineKeyboardMarkup:
    """Guruh uchun start keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Botni boshlash", url="https://t.me/your_bot_username?start=group")]
    ])


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def group_message(message: Message):
    """Guruh xabarlarini qayta ishlash"""
    # Bu yerda guruh xabarlarini qayta ishlash logikasi
    pass


@router.message(F.chat.type.in_(["group", "supergroup"]), F.new_chat_members)
async def new_member(message: Message):
    """Yangi a'zo qo'shilganda"""
    new_members = message.new_chat_members
    for member in new_members:
        # Agar bot o'zi qo'shilgan bo'lsa
        if member.id == message.bot.id:
            continue
        await message.answer(
            f"👋 Salom, {member.first_name}!\n"
            f"Guruhga xush kelibsiz!\n\n"
            "Botdan foydalanish uchun quyidagi tugmani bosing:",
            reply_markup=get_group_start_keyboard()
        )


@router.message(F.chat.type.in_(["group", "supergroup"]), F.left_chat_member)
async def left_member(message: Message):
    """A'zo chiqib ketganda"""
    left_member = message.left_chat_member
    # Agar bot o'zi chiqib ketgan bo'lsa
    if left_member.id == message.bot.id:
        return
    await message.answer(
        f"👋 {left_member.first_name} guruhni tark etdi."
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED >> MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated):
    """Bot guruhga qo'shilganda"""
    group = event.chat
    await event.bot.send_message(
        group.id,
        f"✅ Bot {group.title} guruhiga qo'shildi!\n\n"
        "Botdan foydalanish uchun quyidagi tugmani bosing:",
        reply_markup=get_group_start_keyboard()
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER >> LEFT))
async def bot_removed_from_group(event: ChatMemberUpdated):
    """Bot guruhdan olib tashlanganda"""
    # Bu yerda guruhdan chiqarilganda logikasi
    pass

"""
Channel handlerlari - kanallar uchun
"""

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR

router = Router(name="channel")


@router.message(F.chat.type == "channel")
async def channel_message(message: Message):
    """Kanal xabarlarini qayta ishlash"""
    # Bu yerda kanal xabarlarini qayta ishlash logikasi
    pass


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED >> MEMBER))
async def bot_added_to_channel(event: ChatMemberUpdated):
    """Bot kanalga qo'shilganda"""
    channel = event.chat
    await event.bot.send_message(
        channel.id,
        f"✅ Bot {channel.title} kanaliga qo'shildi!"
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER >> LEFT))
async def bot_removed_from_channel(event: ChatMemberUpdated):
    """Bot kanaldan olib tashlanganda"""
    # Bu yerda kanaldan chiqarilganda logikasi
    pass

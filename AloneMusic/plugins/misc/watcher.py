# ======================================================
# Copyright (C) 2021-2025 by TheAloneTeam
# https://github.com/TheAloneTeam/AloneMusic
# Licensed under GNU v3.0 License.
# ======================================================

from pyrogram import filters
from pyrogram.types import Message

from AloneMusic import app
from AloneMusic.core.call import Alone
from AloneMusic.utils.database import get_assistant


@app.on_message(filters.video_chat_started, group=20)
@app.on_message(filters.video_chat_ended, group=30)
async def vc_event_handler(_, message: Message):
    """
    This function is triggered when a video chat starts or ends.
    It safely stops or leaves the group call.
    """
    chat_id = message.chat.id
    try:
        # Try stopping the stream first
        await Alone.stop_stream(chat_id)
    except Exception:
        # If no stream exists, leave the group call
        try:
            await Alone.leave_group_call(chat_id)
        except Exception:
            pass


@app.on_message(filters.left_chat_member, group=69)
async def bot_kick(_, msg: Message):
    """
    If the bot is kicked from a group, the assistant userbot leaves as well.
    """
    if msg.left_chat_member.id == app.id:
        ub = await get_assistant(msg.chat.id)
        try:
            await ub.leave_chat(msg.chat.id)
        except Exception:
            pass

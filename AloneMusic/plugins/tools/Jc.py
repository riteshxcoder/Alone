import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import BANNED_USERS
from AloneMusic import app
from AloneMusic.utils.admin_filters import admin_filter
from AloneMusic.utils.ndatabase import group_assistant

logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

VC_TRACKING_ENABLED = set()
VC_TASKS = {}

async def fetch_vc_participants(chat_id: int):
    """Fetch current VC participants without joining."""
    try:
        assistant = await group_assistant(None, chat_id)  # Passive: assistant not joining
        participants = await assistant.get_participants(chat_id)
        return [p.user_id for p in participants]
    except Exception as e:
        logger.error(f"Error fetching VC participants in {chat_id}: {e}")
        return []

async def monitor_vc_passive(chat_id: int):
    """Monitor VC participants passively, without joining VC."""
    old_users = set(await fetch_vc_participants(chat_id))
    while chat_id in VC_TRACKING_ENABLED:
        await asyncio.sleep(5)
        try:
            new_users_list = await fetch_vc_participants(chat_id)
            new_users = set(new_users_list)
            joined = new_users - old_users
            left = old_users - new_users
            old_users = new_users

            lines = []
            for uid in joined:
                user = await app.get_users(uid)
                lines.append(f"👋 <b>{user.mention}</b> joined VC")
            for uid in left:
                user = await app.get_users(uid)
                lines.append(f"🚪 <b>{user.mention}</b> left VC")

            if lines:
                msg_text = "\n".join(lines)
                msg = await app.send_message(
                    chat_id, f"{msg_text}\n\n👥 <b>Now in VC:</b> {len(new_users)}"
                )
                await asyncio.sleep(5)
                await msg.delete()
        except Exception as e:
            logger.error(f"Error monitoring VC {chat_id}: {e}")

@app.on_message(filters.command(["vclogger"]) & filters.group & admin_filter & ~BANNED_USERS)
async def vc_logger(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(None, 1)

    if len(args) == 2 and args[1].lower() in ["on", "enable"]:
        if chat_id in VC_TRACKING_ENABLED:
            return await message.reply_text("✅ VC logger is already enabled in this group.")
        VC_TRACKING_ENABLED.add(chat_id)
        VC_TASKS[chat_id] = asyncio.create_task(monitor_vc_passive(chat_id))
        await message.reply_text("✅ VC logger enabled in this group.")

    elif len(args) == 2 and args[1].lower() in ["off", "disable"]:
        if chat_id in VC_TRACKING_ENABLED:
            VC_TRACKING_ENABLED.discard(chat_id)
            if chat_id in VC_TASKS:
                VC_TASKS[chat_id].cancel()
                VC_TASKS.pop(chat_id, None)
            await message.reply_text("🚫 VC logger stopped in this group.")
        else:
            await message.reply_text("ℹ️ VC logger is not enabled in this group.")

    else:
        await message.reply_text("ℹ️ Use: /vclogger on | off")

@app.on_message(filters.command(["vcinfo"]) & filters.group & admin_filter & ~BANNED_USERS)
async def vc_info(client: Client, message: Message):
    chat_id = message.chat.id
    participants = await fetch_vc_participants(chat_id)
    if not participants:
        return await message.reply_text("ℹ️ No participants found in VC.")

    lines = []
    for uid in participants:
        user = await app.get_users(uid)
        lines.append(f"🎧 {user.mention}")
    msg_text = "\n".join(lines) + f"\n\n👥 <b>Total in VC:</b> {len(lines)}"
    msg = await message.reply_text(msg_text)
    await asyncio.sleep(5)
    await msg.delete()

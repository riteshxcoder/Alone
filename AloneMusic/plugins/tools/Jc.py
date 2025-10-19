import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pytgcalls.exceptions import GroupCallNotFoundError

from config import BANNED_USERS
from AloneMusic import app
from AloneMusic.core.call import Alone
from AloneMusic.utils.admin_filters import admin_filter
from AloneMusic.utils.ndatabase import group_assistant

# Logging Setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

VC_TRACKING_ENABLED = set()
VC_CACHE = {}
VC_TASKS = {}


async def check_vc_active(chat_id: int):
    """Check if a VC exists (without joining)."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        participants = await assistant.get_participants(chat_id)
        logger.info(f"🔎 VC check for {chat_id}: Active ({len(participants)} users)")
        return participants
    except GroupCallNotFoundError:
        logger.info(f"🚫 No active VC found for {chat_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Error checking VC in {chat_id}: {e}")
        return None


async def monitor_vc(chat_id: int):
    """Monitor VC participants without assistant joining."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        participants = await check_vc_active(chat_id)
        if not participants:
            raise GroupCallNotFoundError

        old_users = set(p.user_id for p in participants)
        VC_CACHE[chat_id] = old_users

        while chat_id in VC_TRACKING_ENABLED:
            await asyncio.sleep(5)
            participants = await check_vc_active(chat_id)
            if not participants:
                raise GroupCallNotFoundError

            new_users = set(p.user_id for p in participants)
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
                msg = "\n".join(lines)
                await app.send_message(chat_id, f"{msg}\n\n👥 <b>Now in VC:</b> {len(new_users)}")

    except GroupCallNotFoundError:
        logger.info(f"❌ VC ended in {chat_id}, stopping monitor.")
    except Exception as e:
        logger.error(f"Error monitoring VC {chat_id}: {e}")
    finally:
        VC_TRACKING_ENABLED.discard(chat_id)
        VC_CACHE.pop(chat_id, None)
        VC_TASKS.pop(chat_id, None)


@app.on_message(filters.command(["vcinfo", "vclogger"]) & filters.group & admin_filter & ~BANNED_USERS)
async def vc_info(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(None, 1)

    # 🟢 Enable VC Logger
    if len(args) == 2 and args[1].lower() in ["on", "enable"]:
        if chat_id in VC_TRACKING_ENABLED:
            return await message.reply_text("✅ VC tracking is already enabled.")
        participants = await check_vc_active(chat_id)
        if not participants:
            return await message.reply_text("ℹ️ No active voice chat found in this group.")
        VC_TRACKING_ENABLED.add(chat_id)
        VC_TASKS[chat_id] = asyncio.create_task(monitor_vc(chat_id))
        await message.reply_text("✅ VC monitoring started (assistant will not join).")
        return

    # 🔴 Disable VC Logger
    elif len(args) == 2 and args[1].lower() in ["off", "disable"]:
        if chat_id not in VC_TRACKING_ENABLED:
            return await message.reply_text("❌ VC tracking is already disabled.")
        VC_TRACKING_ENABLED.discard(chat_id)
        if chat_id in VC_TASKS:
            VC_TASKS[chat_id].cancel()
            VC_TASKS.pop(chat_id, None)
        await message.reply_text("🚫 VC monitoring stopped and cache cleared.")
        return

    # ℹ️ Show VC info (without joining)
    try:
        participants = await check_vc_active(chat_id)
        if not participants:
            return await message.reply_text("ℹ️ No active voice chat found in this group.")
        names = []
        for p in participants:
            user = await app.get_users(p.user_id)
            names.append(f"🎧 {user.mention}")
        await message.reply_text("\n".join(names) + f"\n\n👥 <b>Total in VC:</b> {len(names)}")
    except GroupCallNotFoundError:
        await message.reply_text("ℹ️ No active voice chat found in this group.")
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await vc_info(client, message)
    except Exception as e:
        logger.error(f"Error in vc_info: {e}")
        await message.reply_text(f"❌ Error fetching VC info:\n<b>{e}</b>")

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pytgcalls.exceptions import AlreadyJoinedError, NoActiveGroupCall

from config import BANNED_USERS
from AloneMusic import app
from AloneMusic.core.call import Alone
from AloneMusic.utils.admin_filters import admin_filter
from AloneMusic.utils.ndatabase import group_assistant

logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

VC_TRACKING_ENABLED = set()
VC_CACHE = {}
VC_TASKS = {}


async def ensure_assistant_joined(chat_id: int):
    """Check and join assistant to voice chat if active."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        await assistant.join_group_call(chat_id)
        logger.info(f"✅ Assistant joined voice chat in {chat_id}")
        return True
    except AlreadyJoinedError:
        logger.info(f"ℹ️ Assistant already joined in {chat_id}")
        return True
    except NoActiveGroupCall:
        logger.info(f"🚫 No active VC found for {chat_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Error joining VC for {chat_id}: {e}")
        return False


async def monitor_vc(chat_id: int):
    """Monitor VC participants."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        participants = await assistant.get_participants(chat_id)
        old_users = set(p.user_id for p in participants)
        VC_CACHE[chat_id] = old_users

        while chat_id in VC_TRACKING_ENABLED:
            await asyncio.sleep(5)
            participants = await assistant.get_participants(chat_id)
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
    except NoActiveGroupCall:
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

    if len(args) == 2 and args[1].lower() in ["on", "enable"]:
        if chat_id in VC_TRACKING_ENABLED:
            return await message.reply_text("✅ VC tracking is already enabled.")
        ok = await ensure_assistant_joined(chat_id)
        if not ok:
            return await message.reply_text("ℹ️ No active voice chat found in this group.")
        VC_TRACKING_ENABLED.add(chat_id)
        VC_TASKS[chat_id] = asyncio.create_task(monitor_vc(chat_id))
        await message.reply_text("✅ VC monitoring started.")
    elif len(args) == 2 and args[1].lower() in ["off", "disable"]:
        VC_TRACKING_ENABLED.discard(chat_id)
        if chat_id in VC_TASKS:
            VC_TASKS[chat_id].cancel()
            VC_TASKS.pop(chat_id, None)
        await message.reply_text("🚫 VC monitoring stopped.")
    else:
        ok = await ensure_assistant_joined(chat_id)
        if not ok:
            return await message.reply_text("ℹ️ No active voice chat found in this group.")
        assistant = await group_assistant(Alone, chat_id)
        participants = await assistant.get_participants(chat_id)
        names = []
        for p in participants:
            user = await app.get_users(p.user_id)
            names.append(f"🎧 {user.mention}")
        if names:
            await message.reply_text("\n".join(names) + f"\n\n👥 <b>Total in VC:</b> {len(names)}")
        else:
            await message.reply_text("ℹ️ Voice chat is active but no participants found.")

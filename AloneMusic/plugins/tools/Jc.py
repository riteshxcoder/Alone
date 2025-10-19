import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
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
    """Ensure assistant is in VC."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        if not await assistant.is_connected(chat_id):
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
    """Monitor VC participants and auto-delete messages after 5s."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        assistant_id = (await app.get_me()).id
        participants = await assistant.get_participants(chat_id)
        old_users = set(p.user_id for p in participants if p.user_id != assistant_id)
        VC_CACHE[chat_id] = old_users

        while chat_id in VC_TRACKING_ENABLED:
            await asyncio.sleep(5)
            participants = await assistant.get_participants(chat_id)
            new_users = set(p.user_id for p in participants if p.user_id != assistant_id)

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
    except NoActiveGroupCall:
        logger.info(f"❌ VC ended in {chat_id}, stopping monitor.")
    except Exception as e:
        logger.error(f"Error monitoring VC {chat_id}: {e}")
    finally:
        VC_TRACKING_ENABLED.discard(chat_id)
        VC_CACHE.pop(chat_id, None)
        VC_TASKS.pop(chat_id, None)


@app.on_message(filters.command(["vclogger"]) & filters.group & admin_filter & ~BANNED_USERS)
async def vc_logger(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(None, 1)

    if len(args) == 2 and args[1].lower() in ["on", "enable"]:
        # Auto-enable VC logger in all groups where bot is added
        async for dialog in app.get_dialogs():
            gc = dialog.chat
            if gc.type in ["group", "supergroup"]:
                gc_id = gc.id
                if gc_id in VC_TRACKING_ENABLED:
                    continue
                ok = await ensure_assistant_joined(gc_id)
                if ok:
                    VC_TRACKING_ENABLED.add(gc_id)
                    VC_TASKS[gc_id] = asyncio.create_task(monitor_vc(gc_id))
        await message.reply_text("✅ VC logger enabled in all groups.")

    elif len(args) == 2 and args[1].lower() in ["off", "disable"]:
        for gc_id in list(VC_TRACKING_ENABLED):
            VC_TRACKING_ENABLED.discard(gc_id)
            if gc_id in VC_TASKS:
                VC_TASKS[gc_id].cancel()
                VC_TASKS.pop(gc_id, None)
        await message.reply_text("🚫 VC logger stopped in all groups.")

    else:
        await message.reply_text("ℹ️ Use: /vclogger on | off")

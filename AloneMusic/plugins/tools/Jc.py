import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from config import BANNED_USERS
from AloneMusic.core.call import Alone
from AloneMusic.utils.admin_filters import admin_filter
from AloneMusic.utils.ndatabase import group_assistant
from AloneMusic import app

from pytgcalls.exceptions import AlreadyJoinedError, NoActiveGroupCall

# Logging Setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

VC_CACHE = {}
VC_TRACKING_ENABLED = set()
VC_MONITOR_TASKS = {}


async def is_voice_chat_active(client: Client, chat_id: int) -> bool:
    """Check if a voice chat is active."""
    try:
        chat = await client.get_chat(chat_id)
        active = getattr(chat, "call_active", False)
        logger.info(f"🔎 VC active check for {chat_id}: {active}")
        return active
    except Exception as e:
        logger.error(f"❌ Error checking VC for chat {chat_id}: {e}")
        return False


async def ensure_assistant_joined(assistant, chat_id: int):
    """Ensure assistant joins VC if not already joined."""
    try:
        await assistant.start(chat_id)
        logger.info(f"✅ Assistant joined VC in {chat_id}")
        return True

    except AlreadyJoinedError:
        logger.info(f"ℹ️ Assistant already joined VC in {chat_id}")
        return True

    except NoActiveGroupCall:
        logger.info(f"🚫 No active VC found for chat {chat_id}")
        return False

    except Exception as e:
        logger.error(f"❌ Error joining VC for chat {chat_id}: {e}")
        return False


async def monitor_vc_changes(chat_id: int):
    """Background task to monitor VC changes."""
    try:
        assistant = await group_assistant(Alone, chat_id)
        if not assistant:
            raise Exception("Assistant not initialized")

        logger.info(f"🎧 VC monitoring started for {chat_id}")

        if not await is_voice_chat_active(app, chat_id):
            raise Exception("No active voice chat found")

        if not await ensure_assistant_joined(assistant, chat_id):
            raise Exception("Assistant failed to join VC")

        participants = await assistant.get_participants(chat_id)
        current_ids = set(p.user_id for p in participants)
        VC_CACHE[chat_id] = current_ids

        if participants:
            joined_lines = []
            for p in participants:
                try:
                    user = await app.get_users(p.user_id)
                    name = user.mention if user else f"<code>{p.user_id}</code>"
                except Exception:
                    name = f"<code>{p.user_id}</code>"

                status = ["Muted" if p.muted else "Unmuted"]
                if getattr(p, "screen_sharing", False):
                    status.append("Screen Sharing")
                vol = getattr(p, "volume", None)
                if vol:
                    status.append(f"Volume: {vol}")
                joined_lines.append(f"#InVC\n<b>Name:</b> {name}\n<b>Status:</b> {', '.join(status)}")

            result = "\n\n".join(joined_lines)
            result += f"\n\n👥 <b>Now in VC:</b> {len(participants)}"
            try:
                msg = await app.send_message(chat_id, result)
                await asyncio.sleep(30)
                await msg.delete()
            except Exception as e:
                logger.error(f"Error sending initial VC info: {e}")

        # Monitoring loop
        while chat_id in VC_TRACKING_ENABLED:
            await asyncio.sleep(5)
            assistant = await group_assistant(Alone, chat_id)
            if not assistant:
                raise Exception("Assistant not available")

            if not await is_voice_chat_active(app, chat_id):
                raise Exception("Voice chat ended or inactive")

            try:
                participants = await assistant.get_participants(chat_id)
            except Exception as e:
                raise Exception(f"Error fetching participants: {e}")

            current_ids = set(p.user_id for p in participants)
            old_ids = VC_CACHE.get(chat_id, set())
            VC_CACHE[chat_id] = current_ids

            joined = current_ids - old_ids
            left = old_ids - current_ids

            joined_lines, left_lines = [], []

            for uid in joined:
                try:
                    user = await app.get_users(uid)
                    name = user.mention if user else f"<code>{uid}</code>"
                except Exception:
                    name = f"<code>{uid}</code>"
                joined_lines.append(f"#JoinedVC\n<b>Name:</b> {name}")

            for uid in left:
                try:
                    user = await app.get_users(uid)
                    name = user.mention if user else f"<code>{uid}</code>"
                except Exception:
                    name = f"<code>{uid}</code>"
                left_lines.append(f"#LeftVC\n<b>Name:</b> {name}")

            if joined_lines or left_lines:
                result = "\n\n".join(joined_lines + left_lines)
                result += f"\n\n👥 <b>Now in VC:</b> {len(current_ids)}"
                try:
                    msg = await app.send_message(chat_id, result)
                    await asyncio.sleep(30)
                    await msg.delete()
                except FloodWait as fw:
                    await asyncio.sleep(fw.value)
                except Exception as e:
                    logger.error(f"Error sending VC update: {e}")

    except Exception as e:
        logger.error(f"❌ VC monitor stopped for {chat_id}: {e}")
        try:
            await app.send_message(chat_id, f"❌ VC monitoring stopped.\n<b>Reason:</b> {e}")
        except Exception:
            pass
        finally:
            VC_TRACKING_ENABLED.discard(chat_id)
            VC_CACHE.pop(chat_id, None)
            VC_MONITOR_TASKS.pop(chat_id, None)


@app.on_message(filters.command(["vcinfo", "infovc", "vclogger"]) & filters.group & admin_filter & ~BANNED_USERS)
async def vc_info(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(None, 1)

    if len(args) == 2 and args[1].lower() in ["on", "enable"]:
        if chat_id in VC_TRACKING_ENABLED:
            return await message.reply_text("✅ VC tracking is already enabled.")

        assistant = await group_assistant(Alone, chat_id)
        if not assistant:
            return await message.reply_text("❌ Assistant not initialized.")

        if not await is_voice_chat_active(app, chat_id):
            return await message.reply_text("ℹ️ No active VC found.\nStart a voice chat first.")

        if not await ensure_assistant_joined(assistant, chat_id):
            return await message.reply_text("❌ Assistant couldn't join VC. Please check permissions.")

        VC_TRACKING_ENABLED.add(chat_id)
        VC_MONITOR_TASKS[chat_id] = asyncio.create_task(monitor_vc_changes(chat_id))
        logger.info(f"VC tracking enabled for {chat_id}")
        return await message.reply_text("✅ VC tracking enabled!\nNow I'll notify #JoinedVC and #LeftVC users.")

    elif len(args) == 2 and args[1].lower() in ["off", "disable"]:
        if chat_id not in VC_TRACKING_ENABLED:
            return await message.reply_text("❌ VC tracking is already disabled.")

        VC_TRACKING_ENABLED.discard(chat_id)
        VC_CACHE.pop(chat_id, None)
        if chat_id in VC_MONITOR_TASKS:
            VC_MONITOR_TASKS[chat_id].cancel()
            VC_MONITOR_TASKS.pop(chat_id, None)
        try:
            assistant = await group_assistant(Alone, chat_id)
            if assistant:
                await assistant.stop()
        except Exception as e:
            logger.error(f"Error stopping assistant: {e}")
        logger.info(f"VC tracking disabled for {chat_id}")
        return await message.reply_text("🚫 VC tracking disabled and cache cleared.")

    # Just show VC info
    try:
        assistant = await group_assistant(Alone, chat_id)
        if not assistant:
            return await message.reply_text("❌ Assistant not found.")

        if not await is_voice_chat_active(app, chat_id):
            return await message.reply_text("ℹ️ No active voice chat found in this group.")

        if not await ensure_assistant_joined(assistant, chat_id):
            return await message.reply_text("❌ Assistant failed to join VC.")

        participants = await assistant.get_participants(chat_id)
        if not participants:
            return await message.reply_text("❌ No users in VC currently.")

        joined_lines = []
        for p in participants:
            try:
                user = await app.get_users(p.user_id)
                name = user.mention if user else f"<code>{p.user_id}</code>"
            except Exception:
                name = f"<code>{p.user_id}</code>"

            status = ["Muted" if p.muted else "Unmuted"]
            if getattr(p, "screen_sharing", False):
                status.append("Screen Sharing")
            vol = getattr(p, "volume", None)
            if vol:
                status.append(f"Volume: {vol}")

            joined_lines.append(f"#InVC\n<b>Name:</b> {name}\n<b>Status:</b> {', '.join(status)}")

        result = "\n\n".join(joined_lines)
        result += f"\n\n👥 <b>Total in VC:</b> {len(participants)}"
        await message.reply_text(result)

    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        return await vc_info(client, message)
    except Exception as e:
        logger.error(f"Error in vc_info for {chat_id}: {e}")
        await message.reply_text(f"❌ Failed to fetch VC info.\n<b>Error:</b> {e}")

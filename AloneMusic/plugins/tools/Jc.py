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
from pytgcalls.exceptions import GroupCallNotFoundError  # Import the exception

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VC_CACHE = {}
VC_TRACKING_ENABLED = set()
VC_MONITOR_TASKS = {}

async def is_voice_chat_active(client: Client, chat_id: int) -> bool:
    """Check if a voice chat is active using the main Pyrogram/Pyrofork client."""
    try:
        chat = await client.get_chat(chat_id)
        active = getattr(chat, 'call_active', False)
        logger.debug(f"Voice chat active for chat {chat_id}: {active}")
        return active
    except Exception as e:
        logger.error(f"Error checking voice chat active for chat {chat_id}: {e}")
        return False

async def ensure_assistant_joined(assistant, chat_id: int):
    """Ensure the assistant joins the voice chat if not already joined."""
    try:
        # Attempt to start/join the group call
        await assistant.start(chat_id)
        logger.info(f"Assistant joined voice chat in {chat_id}")
        return True
    except GroupCallNotFoundError:
        logger.warning(f"No group call found for chat {chat_id}")
        return False
    except Exception as e:
        logger.error(f"Error joining voice chat for chat {chat_id}: {e}")
        return False

async def monitor_vc_changes(chat_id: int):
    """Background task to monitor voice chat changes."""
    try:
        assistant = await group_assistant(AMBOT, chat_id)
        if not assistant:
            raise Exception("Assistant not found or not initialized.")
        
        logger.info(f"Starting VC monitoring for chat {chat_id}")

        # Ensure voice chat is active and join if necessary
        if not await is_voice_chat_active(app, chat_id):
            raise Exception("No active voice chat found.")
        if not await ensure_assistant_joined(assistant, chat_id):
            raise Exception("Failed to join the voice chat.")

        # Initial log of current VC members
        participants = await assistant.get_participants(chat_id)
        current_ids = set()
        joined_lines = []

        if participants:
            for p in participants:
                current_ids.add(p.user_id)
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

            if joined_lines:
                result = "\n\n".join(joined_lines)
                result += f"\n\n👥 <b>Now in VC:</b> {len(participants)}"
                try:
                    msg = await app.send_message(chat_id, result)
                    await asyncio.sleep(30)
                    await msg.delete()
                except Exception as e:
                    logger.error(f"Error sending initial VC message for chat {chat_id}: {e}")

        VC_CACHE[chat_id] = current_ids

        # Begin monitoring loop
        while chat_id in VC_TRACKING_ENABLED:
            await asyncio.sleep(5)

            assistant = await group_assistant(AMBOT, chat_id)
            if not assistant:
                raise Exception("Assistant not found or not initialized.")

            # Check if voice chat is still active
            if not await is_voice_chat_active(app, chat_id):
                raise Exception("Voice chat has ended or is not active.")

            try:
                participants = await assistant.get_participants(chat_id)
            except Exception as e:
                raise Exception(f"Could not fetch participants: {e}")

            current_ids = set(p.user_id for p in participants)
            old_ids = VC_CACHE.get(chat_id, set())
            VC_CACHE[chat_id] = current_ids

            joined_lines = []
            left_lines = []

            for user_id in current_ids - old_ids:
                try:
                    user = await app.get_users(user_id)
                    name = user.mention if user else f"<code>{user_id}</code>"
                except Exception:
                    name = f"<code>{user_id}</code>"
                joined_lines.append(f"#JoinedVC\n<b>Name:</b> {name}")

            for user_id in old_ids - current_ids:
                try:
                    user = await app.get_users(user_id)
                    name = user.mention if user else f"<code>{user_id}</code>"
                except Exception:
                    name = f"<code>{user_id}</code>"
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
                    msg = await app.send_message(chat_id, result)
                    await asyncio.sleep(30)
                    await msg.delete()
                except Exception as e:
                    logger.error(f"Error sending VC update for chat {chat_id}: {e}")

    except Exception as e:
        logger.error(f"VC monitoring stopped for chat {chat_id}: {e}")
        try:
            await app.send_message(chat_id, f"❌ VC monitoring stopped due to error: {e}")
        except Exception as e:
            logger.error(f"Error sending stop message for chat {chat_id}: {e}")
        finally:
            VC_TRACKING_ENABLED.discard(chat_id)
            VC_CACHE.pop(chat_id, None)
            VC_MONITOR_TASKS.pop(chat_id, None)

@app.on_message(filters.command(["vcinfo", "infovc", "vclogger"]) & filters.group & admin_filter & ~BANNED_USERS)
async def vc_info(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(None, 1)

    if len(args) == 2 and args[1].lower() in ["on", "enable"]:
        if chat_id not in VC_TRACKING_ENABLED:
            assistant = await group_assistant(AMBOT, chat_id)
            if not assistant:
                logger.error(f"Assistant not found for chat {chat_id}")
                return await message.reply_text("❌ Assistant not found or not initialized.")
            if not await is_voice_chat_active(app, chat_id):
                logger.warning(f"No active voice chat for chat {chat_id} when enabling tracking")
                return await message.reply_text("❌ No active voice chat found in this group. Start a voice chat first.")
            if not await ensure_assistant_joined(assistant, chat_id):
                logger.warning(f"Failed to join VC for chat {chat_id}")
                return await message.reply_text("❌ Failed to join the voice chat. Please check if a voice chat exists and the assistant has permissions.")
            VC_TRACKING_ENABLED.add(chat_id)
            task = asyncio.create_task(monitor_vc_changes(chat_id))
            VC_MONITOR_TASKS[chat_id] = task
            logger.info(f"VC tracking enabled for chat {chat_id}")
            return await message.reply_text("✅ VC tracking enabled for this group. Now I'll track & notify #JoinedVC and #LeftVC users.")
        return await message.reply_text("✅ VC tracking is already enabled.")

    elif len(args) == 2 and args[1].lower() in ["off", "disable"]:
        if chat_id in VC_TRACKING_ENABLED:
            VC_TRACKING_ENABLED.discard(chat_id)
            VC_CACHE.pop(chat_id, None)
            if chat_id in VC_MONITOR_TASKS:
                VC_MONITOR_TASKS[chat_id].cancel()
                VC_MONITOR_TASKS.pop(chat_id, None)
            # Optionally stop the assistant if joined
            try:
                assistant = await group_assistant(AMBOT, chat_id)
                if assistant:
                    await assistant.stop()
            except Exception as e:
                logger.error(f"Error stopping assistant for chat {chat_id}: {e}")
            logger.info(f"VC tracking disabled for chat {chat_id}")
            return await message.reply_text("❌ VC tracking disabled and cache cleared.")
        return await message.reply_text("❌ VC tracking is already disabled.")

    try:
        assistant = await group_assistant(AMBOT, chat_id)
        if not assistant:
            logger.error(f"Assistant not found for chat {chat_id}")
            return await message.reply_text("❌ Assistant not found. Make sure it has joined the group.")
        
        if not await is_voice_chat_active(app, chat_id):
            logger.warning(f"No active voice chat for chat {chat_id} when running vc_info")
            return await message.reply_text("❌ No active voice chat found in this group. Start a voice chat first.")

        if not await ensure_assistant_joined(assistant, chat_id):
            logger.warning(f"Failed to join VC for chat {chat_id}")
            return await message.reply_text("❌ Failed to join the voice chat. Please check if a voice chat exists and the assistant has permissions.")

        participants = await assistant.get_participants(chat_id)

        if not participants:
            if chat_id not in VC_TRACKING_ENABLED:
                return await message.reply_text("❌ No users found in the voice chat.")
            else:
                VC_CACHE[chat_id] = set()
                return

        current_ids = set()
        joined_lines = []

        for p in participants:
            user_id = p.user_id
            current_ids.add(user_id)

            if chat_id not in VC_TRACKING_ENABLED:
                try:
                    user = await app.get_users(user_id)
                    name = user.mention if user else f"<code>{user_id}</code>"
                except Exception:
                    name = f"<code>{user_id}</code>"

                status = ["Muted" if p.muted else "Unmuted"]
                if getattr(p, "screen_sharing", False):
                    status.append("Screen Sharing")

                vol = getattr(p, "volume", None)
                if vol:
                    status.append(f"Volume: {vol}")

                joined_lines.append(f"#InVC\n<b>Name:</b> {name}\n<b>Status:</b> {', '.join(status)}")

        if joined_lines:
            result = "\n\n".join(joined_lines)
            result += f"\n\n👥 <b>Total in VC:</b> {len(participants)}"
            await message.reply_text(result)

    except FloodWait as fw:
        logger.warning(f"FloodWait encountered for chat {chat_id}: waiting {fw.value} seconds")
        await asyncio.sleep(fw.value)
        return await vc_info(client, message)
    except Exception as e:
        logger.error(f"Error in vc_info for chat {chat_id}: {e}")
        await message.reply_text(f"❌ Failed to fetch VC info.\n<b>Error:</b> {e}")

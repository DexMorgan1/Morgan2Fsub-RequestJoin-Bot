#(©)CodeFlix_Bots

import base64
import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from bot import Bot
from database.database import (
    get_force_subscriptions, has_pending_join_request, remember_join_request,
)
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait


async def is_subscribed(filter, client, update):
    user_id = update.from_user.id
    valid_statuses = {
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    }
    for channel in await get_force_subscriptions():
        if not channel["enabled"] or not channel["channel_id"]:
            continue
        try:
            member = await client.get_chat_member(channel["channel_id"], user_id)
            if member.status in valid_statuses:
                continue
        except UserNotParticipant:
            pass
        except Exception:
            # Do not allow access unless there is a verified request record.
            pass

        if not await has_pending_join_request(channel["channel_id"], user_id):
            return False
    return True


async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return (base64_bytes.decode("ascii")).strip("=")


async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    return base64.urlsafe_b64decode(base64_bytes).decode("ascii")


async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temb_ids)
        except FloodWait as error:
            await asyncio.sleep(error.x)
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temb_ids)
        except Exception:
            msgs = []
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages


async def get_message_id(client, message):
    if message.forward_from_chat:
        return message.forward_from_message_id if message.forward_from_chat.id == client.db_channel.id else 0
    if message.forward_sender_name:
        return 0
    if message.text:
        pattern = "https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern, message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit() and f"-100{channel_id}" == str(client.db_channel.id):
            return msg_id
        if not channel_id.isdigit() and channel_id == client.db_channel.username:
            return msg_id
    return 0


def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for index in range(len(time_list)):
        time_list[index] = str(time_list[index]) + time_suffix_list[index]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    return up_time + ":".join(time_list)


subscribed = filters.create(is_subscribed)


@Bot.on_chat_join_request()
async def record_verified_join_request(client: Bot, join_request):
    """Record a request only for an active Force Subscribe channel."""
    active_channels = {
        channel['channel_id']
        for channel in await get_force_subscriptions()
        if channel['enabled'] and channel['channel_id']
    }
    if join_request.chat.id in active_channels:
        await remember_join_request(join_request.chat.id, join_request.from_user.id)

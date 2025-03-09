from telethon import TelegramClient
from pyrogram.types import Message
from pyrogram import Client, filters
from asyncio.exceptions import TimeoutError
from telethon.sessions import StringSession
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    AccessTokenInvalid
)

from telethon.errors import (
    ApiIdInvalidError,
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    AccessTokenInvalidError
)

from data import Data

ask_ques = "Please choose the Python library you want to generate a string session for"
buttons_ques = [
    [
        InlineKeyboardButton("Pyrogram V2", callback_data="pyrogram"),
        InlineKeyboardButton("Telethon", callback_data="telethon"),
    ],
    [
        InlineKeyboardButton("Pyrogram Bot", callback_data="pyrogram_bot"),
        InlineKeyboardButton("Telethon Bot", callback_data="telethon_bot"),
    ],
]


@Client.on_message(filters.private & ~filters.forwarded & filters.command('generate'))
async def main(_, msg):
    await msg.reply(ask_ques, reply_markup=InlineKeyboardMarkup(buttons_ques))


async def generate_session(bot: Client, msg: Message, telethon=False, is_bot: bool = False):
    session_type = "Telethon" if telethon else "Pyrogram v2"
    session_type += " Bot" if is_bot else ""
    
    await msg.reply(f"Starting {session_type} Session Generation...")

    user_id = msg.chat.id
    api_id_msg = await bot.ask(user_id, 'Please send your `API_ID`', filters=filters.text)
    
    if await cancelled(api_id_msg):
        return

    try:
        api_id = int(api_id_msg.text)
    except ValueError:
        await api_id_msg.reply("Invalid API_ID! Must be a number. Please restart.", quote=True, reply_markup=InlineKeyboardMarkup(Data.generate_button))
        return

    api_hash_msg = await bot.ask(user_id, 'Please send your `API_HASH`', filters=filters.text)
    if await cancelled(api_hash_msg):
        return

    api_hash = api_hash_msg.text

    if not is_bot:
        phone_number_msg = await bot.ask(user_id, "Send your `PHONE_NUMBER` (with country code)\nExample: `+19876543210`", filters=filters.text)
        if await cancelled(phone_number_msg):
            return
        phone_number = phone_number_msg.text
    else:
        phone_number_msg = await bot.ask(user_id, "Send your `BOT_TOKEN` \nExample: `12345:abcdefg...`", filters=filters.text)
        if await cancelled(phone_number_msg):
            return
        phone_number = phone_number_msg.text

    await msg.reply("Processing login...")

    if telethon:
        client = TelegramClient(StringSession(), api_id, api_hash)
    elif is_bot:
        client = Client(name=f"bot_{user_id}", api_id=api_id, api_hash=api_hash, bot_token=phone_number)
    else:
        client = Client(name=f"user_{user_id}", api_id=api_id, api_hash=api_hash)

    await client.connect()

    try:
        if not is_bot:
            if telethon:
                code = await client.send_code_request(phone_number)
            else:
                code = await client.send_code(phone_number)
    except (ApiIdInvalid, ApiIdInvalidError):
        await msg.reply("Invalid `API_ID` and `API_HASH`. Please restart.", reply_markup=InlineKeyboardMarkup(Data.generate_button))
        return
    except (PhoneNumberInvalid, PhoneNumberInvalidError):
        await msg.reply("Invalid `PHONE_NUMBER`. Please restart.", reply_markup=InlineKeyboardMarkup(Data.generate_button))
        return

    phone_code_msg = await bot.ask(user_id, "Enter the OTP received (e.g., `1 2 3 4 5`)", filters=filters.text, timeout=600)
    if await cancelled(phone_code_msg):
        return

    phone_code = phone_code_msg.text.replace(" ", "")

    try:
        if telethon:
            await client.sign_in(phone_number, phone_code)
        else:
            await client.sign_in(phone_number, code.phone_code_hash, phone_code)
    except (PhoneCodeInvalid, PhoneCodeInvalidError):
        await msg.reply("Invalid OTP. Please restart.", reply_markup=InlineKeyboardMarkup(Data.generate_button))
        return
    except (PhoneCodeExpired, PhoneCodeExpiredError):
        await msg.reply("OTP expired. Please restart.", reply_markup=InlineKeyboardMarkup(Data.generate_button))
        return
    except (SessionPasswordNeeded, SessionPasswordNeededError):
        two_step_msg = await bot.ask(user_id, "Your account has 2FA enabled. Please enter your password.", filters=filters.text, timeout=300)
        try:
            if telethon:
                await client.sign_in(password=two_step_msg.text)
            else:
                await client.check_password(two_step_msg.text)
        except (PasswordHashInvalid, PasswordHashInvalidError):
            await msg.reply("Invalid password. Please restart.", reply_markup=InlineKeyboardMarkup(Data.generate_button))
            return

    session_string = client.session.save() if telethon else await client.export_session_string()

    try:
        await client.send_message("me", f"**{session_type} STRING SESSION**\n\n`{session_string}`\n\nGenerated by @DeadlineTechTeam")
        await msg.reply(f"✅ **{session_type} String Session Generated Successfully!**\n\n📩 Sent to your **Saved Messages**.\n Join @DeadlineTechTeam 📢")
    except:
        await msg.reply(f"✅ **{session_type} String Session Generated!**\n\n📌 `{session_string}`")

    await client.disconnect()


async def cancelled(msg):
    if msg.text in ["/cancel", "/restart"] or msg.text.startswith("/"):
        await msg.reply("❌ Process cancelled!", reply_markup=InlineKeyboardMarkup(Data.generate_button))
        return True
    return False

import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from config import USER_BOT_TOKEN, OTP_CHANNEL_ID, DB_NAME
from database import init_db, add_user, get_setting
from api_handler import SMSPanelAPI

logging.basicConfig(level=logging.INFO)
bot = Bot(token=USER_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📲 Get Number")
    builder.button(text="👤 My Profile")
    builder.button(text="🏆 Leaderboard")
    builder.button(text="🔗 Refer & Earn")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    ref_id = None
    if command.args and command.args.isdigit():
        possible_ref = int(command.args)
        if possible_ref != message.from_user.id:
            ref_id = possible_ref

    await add_user(
        message.from_user.id,
        message.from_user.username or "NoUsername",
        message.from_user.full_name,
        ref_id
    )
    welcome_text = await get_setting("welcome_msg")
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())

@dp.message(F.text == "📲 Get Number")
async def select_country(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇮🇹 Italy (Facebook)", callback_data="num_it_fb")
    builder.button(text="🇩🇪 Germany (WhatsApp)", callback_data="num_de_wa")
    builder.button(text="🇪🇹 Ethiopia (Telegram)", callback_data="num_et_tg")
    builder.adjust(2)
    await message.answer(
        "🌍 **দেশ এবং সার্ভিস নির্বাচন করুন:**\nনিচের তালিকা থেকে যেকোনো একটি কান্ট্রি সিলেক্ট করুন:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("num_"))
async def process_get_number(callback: types.CallbackQuery):
    _, country, service = callback.data.split("_")
    await callback.message.edit_text("⏳ সার্ভার থেকে ফ্রেশ নাম্বার খোঁজা হচ্ছে...")

    api_data, error = await SMSPanelAPI.fetch_number(country, service)
    if error:
        await callback.message.edit_text(f"❌ দুঃখিত! {error}")
        return
    phone = api_data["number"]
    act_id = api_data["id"]

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Check OTP", callback_data=f"chk_{act_id}_{phone}_{country}")
    builder.button(text="❌ Cancel", callback_data="cancel_num")
    builder.adjust(1)

    await callback.message.edit_text(
        f"✅ **আপনার নাম্বার তৈরি হয়েছে!**\n\n"
        f"📱 নাম্বার: `{phone}`\n"
        f"🌐 কান্ট্রি: `{country.upper()}`\n\n"
        f"কোড পাঠানোর পর নিচের **Check OTP** বাটনে ক্লিক করুন:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("chk_"))
async def check_otp_handler(callback: types.CallbackQuery):
    _, act_id, phone, country = callback.data.split("_")
    otp_code = await SMSPanelAPI.check_otp(act_id)

    if not otp_code:
        await callback.answer("⏳ এখনো কোনো OTP আসেনি! ৫ সেকেন্ড পর আবার চেষ্টা করুন।", show_alert=True)
        return

    rate = float(await get_setting("otp_rate"))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ?, otp_count = otp_count + 1 WHERE user_id = ?",
            (rate, user_id)
        )
        await db.commit()

    await callback.message.edit_text(
        f"🎉 **OTP রিসিভ হয়েছে!**\n\n"
        f"📱 নাম্বার: `{phone}`\n"
        f"🔑 কোড: `{otp_code}`\n"
        f"💰 ব্যালেন্স যুক্ত হয়েছে: `+{rate}` টাকা",
        parse_mode="Markdown"
    )

    if OTP_CHANNEL_ID:
        masked_phone = phone[:5] + "****" + phone[-3:]
        bot_info = await bot.get_me()
        group_msg = (
            f"🔔 **NEW OTP RECEIVED** 🔔\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 **Country:** `{country.upper()}`\n"
            f"📱 **Number:** `{masked_phone}`\n"
            f"🔑 **OTP Code:** `{otp_code}`\n"
            f"👤 **User:** {callback.from_user.first_name}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Powered by @{bot_info.username}"
        )
        try:
            await bot.send_message(chat_id=OTP_CHANNEL_ID, text=group_msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Channel forward failed: {e}")

@dp.message(F.text == "👤 My Profile")
async def user_profile(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT balance, otp_count FROM users WHERE user_id = ?",
            (message.from_user.id,)
        ) as cur:
            row = await cur.fetchone()

    bal, otps = row if row else (0.0, 0)
    await message.answer(
        f"👤 **ইউজার প্রোফাইল কার্ড**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 আইডি: `{message.from_user.id}`\n"
        f"📛 নাম: {message.from_user.full_name}\n"
        f"📩 সফল ওটিপি: `{otps}` টি\n"
        f"💰 বর্তমান ব্যালেন্স: `{bal:.2f}` টাকা",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT full_name, otp_count FROM users ORDER BY otp_count DESC LIMIT 10"
        ) as cur:
            top_users = await cur.fetchall()

    text = "🏆 **টপ ১০ ওটিপি লিডারবোর্ড**\n━━━━━━━━━━━━━━━━━━━━\n"
    for idx, (name, count) in enumerate(top_users, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        text += f"{medal} **{name}** — `{count}` OTPs\n"

    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔗 Refer & Earn")
async def refer_system(message: types.Message):
    bot_info = await bot.get_me()
    bonus = await get_setting("refer_bonus")
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(
        f"🔗 **রেফার করে আয় করুন!**\n\n"
        f"প্রতি সফল রেফারে আপনি পাবেন `{bonus}` টাকা বোনাস।\n"
        f"আপনার রেফার লিংক:\n`{ref_link}`",
        parse_mode="Markdown"
    )

async def main():
    await init_db()
    print("🚀 User Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import aiosqlite
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID, DB_NAME
from database import get_setting, update_setting

admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_api_key = State()
    waiting_for_api_url = State()

def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 স্ট্যাটিস্টিকস ও রিপোর্ট", callback_data="adm_stats")
    builder.button(text="🔌 API ও প্যানেল সেটিংস", callback_data="adm_api")
    builder.button(text="📢 ব্রডকাস্ট মেসেজ", callback_data="adm_broadcast")
    builder.button(text="💾 ডাটাবেস ব্যাকআপ", callback_data="adm_backup")
    builder.adjust(2)
    return builder.as_markup()

@admin_router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: types.Message):
    await message.answer(
        "👑 **সুপার এডমিন কন্ট্রোল প্যানেল**\n\nএখান থেকে আপনি বটের সব ফিচার নিয়ন্ত্রণ করতে পারবেন:",
        reply_markup=admin_main_keyboard(),
        parse_mode="Markdown"
    )

@admin_router.callback_query(F.data == "adm_stats", F.from_user.id == ADMIN_ID)
async def show_stats(callback: types.CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*), SUM(balance), SUM(otp_count) FROM users") as cur:
            total_users, total_bal, total_otps = await cur.fetchone()

    text = (
        f"📈 **বট লাইভ স্ট্যাটিস্টিকস**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 মোট ইউজার: `{total_users or 0}` জন\n"
        f"📩 সফল ওটিপি: `{total_otps or 0}` টি\n"
        f"💳 ইউজারদের মোট ব্যালেন্স: `{total_bal or 0.0:.2f}` টাকা\n"
    )
    await callback.message.edit_text(text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")

@admin_router.callback_query(F.data == "adm_api", F.from_user.id == ADMIN_ID)
async def api_settings(callback: types.CallbackQuery, state: FSMContext):
    current_url = await get_setting("api_url") or "সেট করা নেই"
    current_key = await get_setting("api_key") or "সেট করা নেই"
    await callback.message.answer(
        f"🔌 **বর্তমান API কনফিগারেশন:**\nURL: `{current_url}`\nKey: `{current_key}`\n\nনতুন **API URL** পাঠান:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_api_url)

@admin_router.message(AdminStates.waiting_for_api_url, F.from_user.id == ADMIN_ID)
async def save_api_url(message: types.Message, state: FSMContext):
    await update_setting("api_url", message.text.strip())
    await message.answer("✅ API URL সেভ হয়েছে! এবার আপনার **API Key** পাঠান:")
    await state.set_state(AdminStates.waiting_for_api_key)

@admin_router.message(AdminStates.waiting_for_api_key, F.from_user.id == ADMIN_ID)
async def save_api_key(message: types.Message, state: FSMContext):
    await update_setting("api_key", message.text.strip())
    await message.answer("✅ API Key সফলভাবে কানেক্ট হয়েছে!", reply_markup=admin_main_keyboard())
    await state.clear()

@admin_router.callback_query(F.data == "adm_broadcast", F.from_user.id == ADMIN_ID)
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📢 সব ইউজারকে পাঠানোর জন্য আপনার মেসেজ পাঠান:")
    await state.set_state(AdminStates.waiting_for_broadcast)

@admin_router.message(AdminStates.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def execute_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cur:
            users = await cur.fetchall()

    sent, failed = 0, 0
    status_msg = await message.answer("⏳ ব্রডকাস্ট শুরু হয়েছে...")
    for (uid,) in users:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
        except:
            failed += 1

    await status_msg.edit_text(
        f"✅ **ব্রডকাস্ট রিপোর্ট:**\nসফলভাবে পাঠানো হয়েছে: `{sent}` জন\nব্যর্থ হয়েছে: `{failed}` জন",
        parse_mode="Markdown"
    )

@admin_router.callback_query(F.data == "adm_backup", F.from_user.id == ADMIN_ID)
async def backup_db(callback: types.CallbackQuery):
    doc = types.FSInputFile(DB_NAME)
    await callback.message.answer_document(doc, caption="💾 আপনার বটের সম্পূর্ণ ডাটাবেস ব্যাকআপ ফাইল।")
